---
title: "觀測出口的職責三分"
date: 2026-07-16
description: "repository 要補「資料變了」的推送能力、卻不確定 Stream 介面放 domain 算不算洩漏時使用。歸屬判準是介面用什麼語言表達、不是需求來自誰：契約歸 domain、變更偵測歸 infrastructure、框架訂閱歸組裝層。"
weight: 7
tags: ["ddd", "repository", "hexagonal-architecture", "reactive", "port"]
---

[觀測出口](/ddd/knowledge-cards/observation-outlet/)是 repository 對外提供的「資料變了」持續通知能力——pull 介面（`getAllBooks()` 回 `Future`）的 push 對應（`watchBooks()` 回 `Stream`）。UI 框架要 reactive 觀察 domain 資料時，這個能力橫跨三層，職責三分：**契約**（介面宣告，歸 domain）、**機制**（變更偵測，歸 infrastructure）、**組裝**（框架訂閱，歸 DI／presentation 層）。三分的判準只有一條：**每一層的產出用什麼語言表達、就歸屬表達那種語言的層**。

這條判準值得成章，因為它跟一個直覺衝突：觀測出口的需求完全來自消費端——是 UI 框架想觀察、domain 自己沒有這個需要。「誰需要就放誰那層」的直覺會把 Stream 出口做進 presentation 的某個 service，讓 domain 保持「純淨」；本章論證這個直覺用錯了判準的位置。

## 案例：六個視圖、兩種補償、一個缺口

一個書庫管理 App 的 repository 是純 `Future` pull 介面。盤點 presentation 層讀書庫資料的六個衍生視圖，只有一個有 reactive 機制（且僅涵蓋部分路徑），其餘全靠命令式載入加補償：

| 視圖         | 刷新方式                       | 過期風險                      |
| ------------ | ------------------------------ | ----------------------------- |
| 書庫清單     | 命令式 `loadBooks()`、外部觸發 | 高：跨頁加書後無自動刷新      |
| 資料統計     | EventBus 全事件監聽 + 導航補償 | 中：未發事件的寫入路徑斷鏈    |
| 待補完列表   | 衍生自一次性 `FutureProvider`  | 高：上游無失效機制            |
| 其餘三個視圖 | 各自命令式載入                 | 低到中：同頁操作後手動 reload |

根因是同一個：repository 沒有變更通知出口，六個視圖各自在圖外解「怎麼知道資料變了」這一題，解出兩種補償策略（導航返回點重載、經 EventBus——行程內的發布／訂閱事件匯流排——的 domain event 橋接）、職責交叉且涵蓋不完整。補償演進的完整記錄在 [ref.watch 觀察的是 provider 圖、不是資料庫](/work-log/flutter_riverpod_reactive_boundary_ref_watch/)；本章從這個案例抽三層歸屬的判準。

## 契約層：歸屬由介面語言決定、不由需求來源決定

契約是那一行介面宣告：

```dart
Stream<List<Book>> watchBooks();
```

它該放 domain repository 介面、還是該為了「不污染 domain」放外層？判準是逐一檢查簽名裡的型別屬於哪種語言：

| 簽名裡的型別                         | 語言歸屬            | 洩漏判定 |
| ------------------------------------ | ------------------- | -------- |
| `Stream<T>`（`dart:async`）          | 語言標準庫          | 不算洩漏 |
| `Book`（domain entity）              | domain 自有語言     | 不算洩漏 |
| `StreamProvider` / `Ref`（Riverpod） | 框架語言            | 洩漏     |
| `Database`（SQLite）                 | infrastructure 語言 | 洩漏     |

語言標準庫的非同步原語跟 domain 的關係、和 `Future` 完全等價：repository 介面回 `Future<List<Book>>` 從來沒人覺得是洩漏，`Stream` 是同一個標準庫裡「多值版的 Future」、地位等同。`watchBooks()` 全句只用標準庫加 domain entity——它說的是 domain 的語言，放 [port](/ddd/knowledge-cards/port/) 所在的 domain 介面，跟 `getAllBooks()` 形成 pull／push 對稱。

這裡就是與直覺衝突的位置。**需求從消費者出發、決定介面該不該存在；介面放哪一層、由表達語言決定**。兩個問題常被壓成一個：

- 「UI 想觀察資料」是消費端需求——它回答「要不要有 `watchBooks()`」。介面設計本來就該從消費者需求出發，port 的形狀由呼叫方的需要定義。
- 「`watchBooks()` 歸誰」是歸屬問題——它由簽名語言回答。簽名說 domain 的語言，介面就是 domain 的；哪天簽名裡出現 `AsyncValue<List<Book>>`（框架型別），才是把消費端的語言帶進了 domain、才需要擋。

用需求來源判歸屬會兩頭錯：把說 domain 語言的介面推到外層，domain 的資料能力（「我管理的資料變了、我能告訴你」）散落到 infrastructure 或 presentation 的 service 裡；或者反過來，以「需求是 domain 相關」為由把帶框架型別的介面塞進 domain。

契約層還有一個二擇：放既有 repository 介面、還是抽獨立的查詢 port？本案放既有介面——讀需求只有「完整書單流」一條、六個視圖都能從書單流投影，為一個方法抽 port 是介面碎片化。這個「何時該抽」的判準有自己的一章：[讀模型的升級判準](/ddd/read-model-upgrade-signals/)。讀 port 一旦抽出，仍屬契約層的延伸——簽名同樣只用 domain 語言，機制層與組裝層的三分模型對它同樣適用。

語言歸屬判準處理的是「詞彙是否洩漏」這一種反對意見。DDD 文獻裡存在另一派更根本的立場：即使簽名純淨，Repository 模式在 Evans / Vernon 的原始定義裡是集合式存取，reactive 訂閱能力本質上服務查詢端、屬於讀側的關注點，不論詞彙是否純淨都不該掛在寫側 aggregate 的 repository 介面上。這個立場涉及讀寫分離的組織方式（讀 port 何時值得獨立、CQRS 階梯的升級判準），跟詞彙判準各自回答不同的問題：詞彙判準回答「語言有沒有洩漏」，讀寫分離判準回答「職責該不該分離」。本章只處理前者；後者見 [讀模型的升級判準](/ddd/read-model-upgrade-signals/)。

## 機制層：變更偵測是 adapter 的實作細節

機制層回答「怎麼知道資料變了」。這層的語言是 controller、資料庫 hook、交易——全是 infrastructure 詞彙，所以歸 [adapter](/ddd/knowledge-cards/adapter/)。本案的二擇：

| 維度         | 寫入點 emit                   | 儲存層 update hook                    |
| ------------ | ----------------------------- | ------------------------------------- |
| 確定性       | 高：明確知道哪些操作觸發通知  | 低：任何 row 變更都觸發、含 migration |
| 粒度         | 精確：只在領域寫入方法尾端    | 粗：要再過濾 table 與操作類型         |
| 平台依賴     | 無：純標準庫 controller       | 有：依賴儲存引擎的 hook API           |
| 裝飾層相容性 | 好：decorator 直接轉發 stream | 要處理快取失效與 hook 的時序          |

本案選寫入點 emit：repository 在每個實際執行寫入的方法尾端發出最新書單。它的維護成本（新增寫入方法要記得掛 emit）留在單一類別內部、被測試釘住；update hook 的 false positive 則會流出去變成消費端的雜訊。關鍵的架構事實是：**這整個表格的內容都不出現在契約層**——選哪個、換哪個，介面簽名一個字不動。這正是三分成立的證據：機制可替換、契約穩定。

## 組裝層：框架型別止步的位置

組裝層把 domain 的 `Stream` 翻譯成框架的觀察原語。本案是 Riverpod 的 `StreamProvider`：

```dart
final watchBooksProvider = StreamProvider<List<Book>>((ref) async* {
  final repository = ref.watch(bookRepositoryProvider);
  yield await repository.getAllBooks(); // 訂閱當下先給當前值
  yield* repository.watchBooks();       // 再轉接後續變更
});
```

`StreamProvider`、`Ref`、`AsyncValue` 這些框架型別在這層第一次出現、也只在這層出現。組裝層同時吸收「呈現需求」性質的行為——訂閱當下要先看到當前值，是消費端的需要、不是「變更通知」語意的一部分，所以那兩行 `yield` 住在這裡而非 repository 裡。組裝層的其他責任（誰插上誰、插上了沒有的證言）見 [組裝層的可達性](/ddd/composition-root-reachability/)；本案的 Flutter 實作細節見 [StreamProvider 包 repository watch stream](/work-log/flutter_streamprovider_wraps_repository_watch/)。

## 三分總表

| 層   | 產出                                   | 表達語言                   | 歸屬                     |
| ---- | -------------------------------------- | -------------------------- | ------------------------ |
| 契約 | `Stream<List<Book>> watchBooks()` 宣告 | 語言標準庫 + domain entity | domain repository 介面   |
| 機制 | broadcast controller + 寫入點 emit     | infrastructure 內部詞彙    | adapter（SQLite 實作類） |
| 組裝 | `StreamProvider` 包裝 + `ref.watch`    | 框架語言                   | DI／presentation 層      |

三列共用同一條判準：看那一層的產出用什麼語言說話。這條判準的機械性有明確範圍——它機械地回答「一個已寫好的簽名該歸哪一層」：打開簽名、逐型別問「這是誰的詞彙」，答案不依賴對「純淨」的品味爭論。它不回答「一段新行為該寫進哪一層」（如初始值那兩行 `yield`）——那是語意歸屬決策，要判斷行為屬於誰的語意，跟機制層選 emit 時機一樣是設計判斷、不是型別檢查。把兩者混為一談、以為整篇的歸屬都能靠型別自動判定，正是這條判準最容易被過度推廣的地方。

## 邊界

觀測出口通知的是「資料現在長什麼樣」；domain event 記錄的是「發生過什麼業務事實」。兩者正交、互不取代——本案落地觀測出口時，既有的事件發布點零改動。這個正交性有一個架構前提：狀態存在獨立的資料庫、事件只是旁支通知。event-sourced 架構下狀態由事件重建、沒有獨立持久化的當前值，機制層要生出 `watchBooks()` 只能訂閱同一條事件流做投影——那時變更偵測與 domain event 不再是兩條獨立管線、「零改動」的論證不成立。把 event 借用成刷新訊號的代價、以及兩種載體的選用判準，見 [domain event 與狀態流](/ddd/domain-event-vs-state-stream/)。

## 下一步

三分的判準確定之後，下一個問題通常是「要不要抽讀 port」——先讀 [讀模型的升級判準](/ddd/read-model-upgrade-signals/) 再做這個決策。還沒建觀測出口、仍在用事件或導航補償的話，回頭讀 [domain event 與狀態流](/ddd/domain-event-vs-state-stream/) 先確認載體選擇，確認要用狀態流再進本章。

- 補償演進與 Riverpod reactive 邊界的案例全文 → [ref.watch 觀察的是 provider 圖、不是資料庫](/work-log/flutter_riverpod_reactive_boundary_ref_watch/)
- 機制層與組裝層的實作點（broadcast、初始值、dispose）→ [StreamProvider 包 repository watch stream](/work-log/flutter_streamprovider_wraps_repository_watch/)
