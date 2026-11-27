---
title: "書單捲動與換搜尋結果時的慢 frame 拆解：timeline 分段、排版細項、中文字串的排版時間與字型實驗"
slug: "flutter-list-jank-cjk-text-layout-breakdown"
date: 2026-11-28
draft: false
description: "Flutter 的中文內容清單在捲動或換搜尋結果時掉幀，或資料層已經改好、畫面的效能指標仍然沒過，要找出時間花在哪一段時讀"
tags: ["flutter", "performance", "timeline", "text-layout", "cjk", "profile-mode", "android"]
---

事件發生在 2026 年 11 月 28 日。環境是一個 Flutter 3.41 的書庫 APP，在 Android 實機 Samsung SM-S9010（Android 16）上以 profile 版執行，書庫是合成的 5 萬本（書名從常用的 3,000 個漢字隨機挑，長度照真實書庫的分布）。操作是在書單的查詢搬進 SQLite 之後，量這兩項沒過的畫面指標：搜尋套用到書單更新 p90 不超過 50 ms（量到 97 ms），以及打字與捲動時主 isolate 沒有超過 16 ms 的 frame（量到 10 個）。

這篇整理怎麼把這兩項的時間拆開：在查詢流程與畫面的 provider 上打 timeline 計時點、算出搜尋套用每一段的耗時；在慢 frame 裡分出 BUILD 與 LAYOUT，再開排版的細項；用 `TextPainter` 直接量一個中文字串的排版時間；兩個直覺的成因（合成資料的隨機字、找替代字型）各用一個小實驗否證；最後是這段成本為什麼歸給書單列的元件設計，而不歸給資料層。量測腳本本身的缺陷與修正在 [Flutter 實機效能量測的排查](/work-log/flutter-integration-test-profile-measurement-pitfalls/)，下面引用的是修正之後的數字。

## 情境條件

這個拆解適用於清單一次有十幾列同時進畫面、每一列有好幾段中文文字的 APP，在換一整頁內容（換搜尋結果、快速捲動到新的區段）時掉幀的情形。它的起點是資料那一側已經不在主 isolate 上：這個 APP 的篩選與搜尋已經改成 SQLite 查詢、在背景 isolate 執行，查一次 20 ms 左右，畫面仍然沒過門檻。

## 依時間段拆搜尋套用

一次搜尋從改條件到新的一頁畫完，經過這幾個交接：搜尋條件的 provider 改變、id 清單的查詢開始、查詢前檢查有沒有待補算的書、SQL 送出與結果回來、id 清單交給畫面、第一頁的書查詢開始與結果回來、資料庫的列組成 `Book` 物件、畫面拿到第一頁、新的一頁畫完。每一個交接打一個計時點：

```dart
developer.Timeline.instantSync('q.ids.start');
await _refreshPendingDerivedColumns();
developer.Timeline.instantSync('q.ids.refreshed');
final result = await fetch(db);
developer.Timeline.instantSync('q.ids.fetched');
```

`developer` 是 `import 'dart:developer' as developer;`。沒有錄 timeline 時，這幾行幾乎沒有成本。量測用 `binding.traceAction(() async { ... }, reportKey: 'timeline_query')` 錄 12 次搜尋，再寫一段腳本以每次的「搜尋條件改變」為起點，算出每個計時點的時間差。錄 timeline 本身會讓程式變慢，所以這一次的數字只用來看比例。

12 次的典型分段：

| 段落                                                                | 耗時                                                  |
| ------------------------------------------------------------------- | ----------------------------------------------------- |
| 改條件到 id 查詢開始                                                | 約 1 ms                                               |
| 查詢前的補算檢查                                                    | 約 1 ms                                               |
| id 的 SQL（1 個字的搜尋，用不到 trigram 索引，退回 LIKE 掃 5 萬筆） | 20 到 30 ms                                           |
| 讀第一頁與第二頁的書（含組 `Book`，組 `Book` 本身不到 0.3 ms）      | 各 5 到 7 ms                                          |
| 資料到了之後畫出新的一頁                                            | 27 到 57 ms，其中 LAYOUT 23 到 50 ms，BUILD 2 到 6 ms |

工作的主題是資料層，所以拆之前懷疑的是資料那一側：補算檢查每次開一個 transaction、查詢跨好幾次 isolate。拆開之後，補算檢查只有約 1 ms；最大的一段在資料已經到了之後，畫出新的一頁的排版。

## 慢 frame 裡是排版

打字與捲動的那一段，用同樣的方式錄 timeline，在 UI 執行緒上找出 `Animator::BeginFrame` 超過 16 ms 的 frame，列出每一個 frame 裡的 BUILD、LAYOUT、PAINT 各佔多少。273 個 frame 裡 21 個超過 16 ms，每一個都是 LAYOUT 佔大部分（12 到 28 ms），BUILD 只有 1 到 3 ms；它們都連續出現在捲動、新的列進入畫面的那幾秒。

LAYOUT 裡是哪些 render object，要另外開 `debugProfileLayoutsEnabled = true` 再錄一次（它讓每個 render object 的 layout 各留一個 timeline 事件，本身會讓排版變慢）。錄到的事件裡，`RenderParagraph`（文字）佔最多，其次是 `RenderFlex`（它的時間包含子元件，跟 `RenderParagraph` 有重疊）。

## 一個中文字串排版要多久

確認成本在文字之後，用 `TextPainter` 直接量：每一種字串準備 60 個，逐一 `layout(maxWidth: 260)`（2 行、17 號字），算平均每個多久。

```dart
double layoutMs(TextStyle style, List<String> texts) {
  final sw = Stopwatch()..start();
  for (final t in texts) {
    TextPainter(text: TextSpan(text: t, style: style), textDirection: TextDirection.ltr, maxLines: 2)
      ..layout(maxWidth: 260)
      ..dispose();
  }
  return sw.elapsedMicroseconds / 1000 / texts.length;
}
```

每一種用一批沒排過的字串，避開排版的快取。結果：

| 字串                     | 每次排版        |
| ------------------------ | --------------- |
| 中文（隨機漢字），第一次 | 0.74 到 1.07 ms |
| 同一批中文再排一次       | 0.016 ms        |
| 同一批中文，換成 13 號字 | 0.74 ms         |
| 英文書名                 | 0.07 ms         |

中文字串第一次排版是英文的 10 倍；同一個字串排第二次幾乎不花時間，因為排版結果有快取，而快取的鍵包含樣式，換了字號就要重排。書單的一列有 3 到 4 個中文字串：書名、封面上用另一個字號重複的書名、作者、資訊列。十幾列同時進畫面時，就是 25 到 50 ms 的排版，跟拆出來的 LAYOUT 對得上。

## 兩個直覺的成因

**合成資料的書名從 3,000 個漢字隨機挑，字形的快取吃不到，所以比真實書庫慢。** 用 30 個真實書名（大多是常用字，例如原子習慣、被討厭的勇氣）各排兩次，60 次的平均是 0.84 ms；後 30 次是同一批字串再排一次、走快取（約 0.016 ms），換算回第一次每個約 1.7 ms，比隨機字還慢。真實書庫的書名也付這個成本，這個成因不成立。

**APP 沒有指定字型，Android 用 Roboto；Roboto 沒有中文字形，每個中文字串都要在系統的替代字型裡找，所以慢。** 手機上的中文字型是 `NotoSansCJK-Regular.ttc`（32 MB）與 `SECCJK-Regular.ttc`（19 MB），在系統的 `fonts.xml` 裡是沒有家族名稱的替代字型。分兩步試：

- 用名稱指定：`fontFamily` 或 `fontFamilyFallback` 設成 `Noto Sans CJK TC`、`NotoSansCJK`、`sans-serif`，以及把 `locale` 設成 zh-Hant-TW，第一次排版都是 0.76 到 0.86 ms，跟預設相同。這些名稱對不到系統的替代字型，最後還是退回預設。
- 把 Google Fonts 的 Noto Sans TC（可變字型，12 MB）放進 APP 的 assets，在 `pubspec.yaml` 的 `fonts` 宣告後直接指定：`fontFamily` 指定它時 0.75 ms，只給中文用（`fontFamilyFallback`）時 0.84 ms；同一次執行裡預設是 1.08 到 1.22 ms。兩次執行之間預設值差約 ±30%（前一次是 0.76 ms），內附字型的值落在這個範圍裡。

換成 APP 自帶、直接指定的字型，中文第一次排版仍約 0.8 ms，所以時間花在中文字形的排版本身（字形與斷行；中文每個字之間都可以斷行），不在找替代字型。實驗用的字型量完之後從 APP 拿掉。

## 成本歸給哪一層

這段排版成本隨畫面上同時進場的列數與每一列的中文字串數變大，跟書庫有 14 本還是 5 萬本無關。這一批工作要證明的是資料層撐得住 5 萬本，而資料層的指標（冷啟動 1.33 秒、記憶體增加 68 MB、查詢在背景 isolate）都過了；排版成本不屬於這一批。

量測修正之後，使用者實際感受到的是：停手後約 270 ms 書單換好（其中 150 ms 是刻意的延遲套用），甩動全書單時 449 個 frame 裡 22 個超過 16.7 ms（4.9%），最長 39 ms。這個 APP 的處置是把排版的兩項改寫成書單列元件契約的實機驗收：停手到書單穩定 p90 不超過 300 ms、捲動全書單超過 16.7 ms 的 frame 不超過 5%、單一 frame 不超過 50 ms。現況三項都過，但沒有餘裕；中階手機比這支旗艦機慢，沒有量過。元件改版時，量測支持的方向是減少每一列要第一次排版的中文字串（封面上的書名用跟書名相同的樣式以共用快取，或不重複顯示），以及把一頁的排版分散到幾個 frame；內附中文字型這個方向被實驗排除了。

## 判斷標準

一項端到端的畫面指標沒過時，修法對不對準，看它處理的是不是拆出來最大的那一段。這次資料層的修法對搜尋套用的 97 ms 只動得到 30 到 40 ms 的資料段，排版的那一段不會變；拆段的計時點打在每一個跨層的交接上，錄一次 timeline 就分得出來。

慢 frame 是 BUILD 還是 LAYOUT 佔大部分，決定往哪裡找：BUILD 佔大部分時看重建的範圍，LAYOUT 佔大部分時開 `debugProfileLayoutsEnabled` 看是哪一種 render object。LAYOUT 裡以文字為主、內容是中文時，量一次 `TextPainter` 的第一次排版時間，乘上一列的中文字串數與一次進畫面的列數，就是換一頁內容那一個 frame 的排版時間下限。

一個成因的推論再順，在只改它一個變數的實驗之前都是假設。實驗放在同一次執行裡跟對照組一起量，因為同一支手機兩次執行之間的起伏（這次約 30%）會蓋過小於這個幅度的效果。
