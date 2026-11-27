---
title: "Flutter 書庫 APP 冷啟動時間的排查：把全部的書載入記憶體、資料庫單例的並行開檔與每次啟動的完整性檢查"
slug: "flutter-cold-start-database-open-and-integrity-check"
date: 2026-11-28
draft: false
description: "Flutter APP 的資料量變大之後冷啟動變慢、首頁要等好幾秒才出現數字，或啟動時出現資料庫被開了好幾次、database is locked 的警告時讀"
tags: ["flutter", "dart", "sqlite", "drift", "performance", "cold-start", "riverpod"]
---

事件發生在 2026 年 11 月 27 日到 28 日。環境是一個 Flutter 3.41 的書庫 APP（Riverpod 3 管狀態），Android 實機 Samsung SM-S9010（Android 16），以 profile 版量測；書庫是合成的 5 萬本、30 萬筆書與標籤的關聯。操作是在幾次程式改動之間重複量同一個指標：APP 建起來到首頁顯示出全書庫本數的時間（不含引擎本身的冷啟動），以及書載入之後記憶體（RSS）增加多少。

這篇整理讓冷啟動變慢或出錯的成因與各自的量測：首頁的本數來自一份載入記憶體的全書庫，啟動時要把 5 萬本組成物件；資料庫管理器的單例（singleton，整個 APP 只有一份的物件）在好幾個 provider 同時第一次取用時各開一份連線；以及一組只該在開發時跑的完整性檢查，在手機的每一個版本上每次啟動都跑。查詢改成在 SQLite 裡執行之後的寫入耗時在 [Flutter drift 匯入大量書籍時的寫入耗時排查：手機上 SQLite 在背景 isolate 的逐條往返、一次送出的語句記錄器，以及依提交時間調整批次大小](/work-log/flutter-drift-batch-write-isolate-round-trip/)，書單畫面的慢 frame 在 [Flutter 書單捲動與換搜尋結果時的慢 frame 拆解：timeline 分段、排版細項、中文字串的排版時間與字型實驗](/work-log/flutter-list-jank-cjk-text-layout-breakdown/)。

## 冷啟動變慢與重複開檔各自的條件

這幾個成因各自在不同的條件下出現：

- 首頁或其他常駐的畫面顯示的數字（總本數、各狀態的本數），是從一份「全部的書」的清單在記憶體裡算出來的。資料量小時算得很快，大到幾萬筆時，光是把每一筆組成物件就要秒級的時間與上百 MB 的記憶體。
- 一個應該只有一份的資源（資料庫連線）用 `x ??= await open()` 這種寫法延遲初始化（lazy initialization，第一次用到時才建立），而某次改動讓好幾個呼叫者在同一個 frame 裡第一次取用它。
- 一段「只在開發模式執行」的程式，判斷開發模式的寫法是排除某一種環境（例如「不是測試」），在手機的正式版上也成立。

## 全書庫載入記憶體時的冷啟動量測

首頁顯示總本數、借出與借入的本數、標籤數。這些數字由一個 provider 從「全部的書」的串流算出：串流先送出 `getAllBooks()` 讀到的全書庫，之後每次寫入再送一次。書單頁的篩選與各條件的本數，也是在記憶體裡對這份全書庫算。

第一次在實機上量 5 萬本：首頁顯示出 5 萬本的本數要 7.3 秒；書載入之後 RSS 從 211 MB 增加到 430 MB（+219 MB）；對 5 萬本篩選一次 89 ms、算一次各條件的本數 85 ms，都在主 isolate 上。Mac 上用 `Map` 做同樣的篩選，2 萬本只要 3.7 ms。推論手機上慢的部分是對 `Book` 物件逐本讀標籤、取作者，以及 5 萬本書加 30 萬筆標籤組成的物件本身：照比例換算，Mac 上 5 萬本 `Map` 約 9 ms，手機估計慢 3 到 5 倍是 27 到 45 ms，跟量到的 89 ms 之間的差額才歸得到 `Book` 物件上；平台、資料結構與本數三個變數同時不同，這一步沒有單變數的實驗。啟動時間與記憶體都跟全書庫的大小成正比，所以只有不把全部的書放進記憶體才降得下來。

## 首頁的本數與書單改成 SQLite 查詢

處置是讓每個畫面向資料庫要它需要的那一小部分，不再共用一份全書庫：

- 首頁的總本數與各條件的本數改成 SQL 的 `COUNT` 與 `GROUP BY`；借閱數只查有借閱中的書；書籍詳情只查那一本。
- 書單改成先向資料庫要符合條件的 id 清單，畫面上的列再依 id 一頁一頁讀出書的資料。
- 搜尋用 SQLite 的 FTS5 trigram 索引。這支手機系統內建的 SQLite（3.44.5）沒有編進 FTS5：實際建一次 FTS5 虛擬表才判斷得出來，`PRAGMA compile_options` 在這支手機回 0 列，看不出有沒有編進去。所以改由 APP 自帶 SQLite（`package:sqlite3`）。資料庫套件同時換成 drift 是另一個決定，讓資料庫跑在背景 isolate，查詢不佔主 isolate；代價是每條 SQL 多一次跨 isolate 的往返，大量寫入時的成本與修法在 [Flutter drift 匯入大量書籍時的寫入耗時排查：手機上 SQLite 在背景 isolate 的逐條往返、一次送出的語句記錄器，以及依提交時間調整批次大小](/work-log/flutter-drift-batch-write-isolate-round-trip/)。

裝上這些改動時先遇到〈資料庫單例的並行開檔〉那一節的錯誤；修好之後量：首頁顯示出 5 萬本的本數要 3.1 秒，RSS 增加 135 MB；一次篩選的查詢約 19 ms，在背景 isolate 上。記憶體的門檻（150 MB）過了，冷啟動的門檻（2 秒）還沒過。

## 資料庫單例的並行開檔

改成 SQLite 查詢的那批改動裝到手機上時，log 印出 drift 的警告 `It looks like you've created the database class _DriftConnection multiple times`，接著是 `SqliteException(261): database is locked`，失敗的語句是 `PRAGMA journal_mode = WAL`。同一個資料庫檔被開了好幾份連線，彼此搶鎖。drift 的警告原文寫明它只出現在 debug 版；在 profile 或正式版看 log 時，看得到的只有 `database is locked`。

資料庫管理器是單例，取用資料庫的 getter 寫成：

```dart
Future<SqlDatabase> get database async {
  _database ??= await _openDatabase();
  return _database!;
}
```

第一個呼叫者執行到 `await` 時讓出事件迴圈，這時 `_database` 還是 null；在開檔完成之前進來的每一個呼叫者都看到 null，各自開一次檔。改動之前，首頁只有一個串流在第一次取用資料庫，所以這個寫法一直沒出錯；改動之後，首頁的本數、借閱中的書、標籤名單三個 provider 在同一個 frame 裡第一次取用，並行就出現了。

發現當下先停掉 APP，把手機上的資料庫拉回電腦檢查：`PRAGMA integrity_check` 回 ok，資料跟改動前逐行相同。修法是把進行中的那一次開檔存起來，讓之後的呼叫者等同一個 Future；開檔失敗時清掉，下一次取用才會重試：

```dart
static Future<SqlDatabase>? _opening;

Future<SqlDatabase> get database async {
  final opened = _database;
  if (opened != null) return opened;
  final opening = _opening ??= _openDatabase();
  try {
    return _database = await opening;
  } catch (_) {
    if (identical(_opening, opening)) _opening = null;
    rethrow;
  }
}
```

測試讓開檔換成一個會等待的假實作，同時發出 5 次取用，斷言開檔只執行一次、5 次拿到同一個實例；換回舊寫法時，同一個測試量到開了 5 次。修完之後重裝，log 裡不再有這兩則訊息。

## 每次啟動的完整性檢查

冷啟動還要 3.1 秒。開檔的程式裡有一段「只在開發模式執行」的完整性檢查：

```dart
bool _isDevelopmentMode() {
  return !Platform.environment.containsKey('FLUTTER_TEST');
}
```

這個判斷只排除 flutter test，手機上的 debug、profile 與正式版都算開發模式，所以每一次啟動都跑 `PRAGMA integrity_check` 與 `PRAGMA foreign_key_check`，而首頁的 provider 要等它們做完才拿得到資料庫。在 Mac 上對同一份 5 萬本的資料庫（96 MB）量這兩項，`integrity_check` 0.57 秒、`foreign_key_check` 0.12 秒；手機上更久。

改成只在 debug 版執行（`kDebugMode && !Platform.environment.containsKey('FLUTTER_TEST')`）之後再量：首頁顯示出 5 萬本的本數 1.33 秒，RSS 增加 68 MB，兩項門檻都過了。debug 版仍然在每次啟動檢查，開發的人在開發期間仍然發現得了資料庫損壞。

## 判斷標準：首頁數字的來源、單例的初始化與開發模式的判斷式

首頁需要的數字由一份載入記憶體的全部資料算出時，從機制推論啟動時間與記憶體都跟資料總量成正比（這次只量了 5 萬本一個點），資料量長大，冷啟動就跟著變慢；改成向資料庫要那幾個數字（`COUNT`、`GROUP BY`、只取需要的那幾筆）時，首頁不再組出全部的物件，載入的工作不再隨資料量增加，剩下的是查詢本身隨資料量的成本（這次 5 萬本時 3.1 秒裡還含著完整性檢查）。

延遲初始化的單例寫成 `??= await` 時，只要有兩個呼叫者在初始化完成之前進來，它就開出兩份；debug 版 log 裡「建立了好幾次」的警告，或只在冷啟動出現的鎖定錯誤，是這個情形的徵兆。最近的改動讓幾個元件同時第一次用到同一個資源時，就是這個條件成立的時候。

判斷式寫成正向的「是開發版」（`kDebugMode` 這類編譯期常數）時，只該在開發時執行的程式不會在正式版執行；寫成排除某一種環境時，判斷式在預期以外的環境（profile、正式版）也成立。那段程式做的是全量工作時（完整性檢查、全表掃描），成本隨資料量加到每一次啟動上。
