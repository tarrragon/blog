---
title: "StreamProvider 包 repository watch stream — broadcast、初始值、dispose 三個實作點"
date: 2026-07-16
draft: false
description: "repository 要補 Stream 觀測出口、接給 Riverpod 消費時使用。訂閱模型選 broadcast 還是單訂閱、新訂閱者拿不拿得到當下狀態、controller 誰負責關——三個問題各有一個會靜默失效的預設答案。"
tags: ["flutter", "dart", "riverpod", "stream", "repository", "state-management", "testing"]
---

> **觸發場景**：書庫管理 App 的 repository 原本是純 `Future` pull 介面，衍生視圖靠補償刷新（背景在 [ref.watch 觀察的是 provider 圖、不是資料庫](/work-log/flutter_riverpod_reactive_boundary_ref_watch/)）。決策定向後要落地：repository 補 `watchBooks()` Stream 出口、用 `StreamProvider` 接進 Riverpod。
> **本篇範圍**：落地時要答對的三個實作點，每一個的預設答案都會靜默失效。

---

## 分層落點

實作橫跨三層、每層只說自己那層的語言（歸屬判準的推導見 [觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)）：

| 層               | 產出                                         | 允許出現的型別               |
| ---------------- | -------------------------------------------- | ---------------------------- |
| domain 契約      | 介面方法 `Stream<List<Book>> watchBooks()`   | `dart:async` + domain entity |
| infrastructure   | `StreamController.broadcast()` + 寫入點 emit | SQLite、controller 細節      |
| DI／presentation | `watchBooksProvider`（`StreamProvider`）     | Riverpod 型別                |

契約層放介面預設實作，讓不支援觀測的實作類（測試替身、舊實作）不必立刻全部跟上：

```dart
/// 提供書單變更的 Stream 出口，取代衍生視圖各自補償刷新。
/// 約束：僅純 dart:async + domain entity，禁止框架型別進入此介面。
Stream<List<Book>> watchBooks() {
  throw UnimplementedError('watchBooks 未在此 repository 實作');
}
```

## 實作點一：訂閱模型選 broadcast

repository 的觀測出口天生多訂閱者——書庫清單、統計頁、待補完列表同時在聽。`StreamController()` 預設建構子是單訂閱、第二個訂閱者出現時直接 throw `Bad state`；這個選型的完整分析（含單訂閱在只有一個訂閱者期間完全沉默的潛伏機制）在 [StreamController single vs broadcast](/work-log/dart_stream_controller_single_vs_broadcast/)。

```dart
class SQLiteBookRepository implements BookRepository {
  /// 全部寫入方法完成後透過此 controller emit 最新完整書單。
  final StreamController<List<Book>> _booksController =
      StreamController<List<Book>>.broadcast();

  @override
  Stream<List<Book>> watchBooks() => _booksController.stream;
}
```

emit 集中在一個私有方法、掛在每個寫入方法尾端：

```dart
Future<void> _emitCurrentBooks() async {
  if (_booksController.isClosed) {
    return; // repository 已 close：靜默略過，不讓通知失敗中斷寫入流程
  }
  final books = await getAllBooks();
  if (!_booksController.isClosed) {
    _booksController.add(books);
  }
}
```

兩個容易漏的細節：

1. **委派方法不重複 emit**。介面上的相容性方法（`saveBook` 內部委派 `addBook`、`deleteBookById` 委派 `deleteBook`）走到底層寫入方法時已經 emit 過；在委派層再掛一次會讓一次寫入發兩次通知。emit 的掛載點是「實際執行寫入的方法集合」、不是「介面上所有看起來會寫入的方法」。
2. **`isClosed` 要查兩次**。`getAllBooks()` 是 async——查詢期間 repository 可能被 close，`add` 前不再確認就會對已關閉的 controller 拋例外，而且是從寫入方法的尾端拋出來、污染寫入本身的成功語意。

## 實作點二：初始值——broadcast 不補送歷史

broadcast stream 對「訂閱之前發生的事件」直接丟棄。衍生視圖訂閱 `watchBooks()` 的當下，上一次 emit 早就過去了——不處理初始值，畫面會停在空清單直到下一次寫入才有資料。

修法放在組裝層：`StreamProvider` 用 `async*` 先給當前值、再轉接後續變更。

```dart
final watchBooksProvider = StreamProvider<List<Book>>((ref) async* {
  final repository = ref.watch(bookRepositoryProvider);
  yield await repository.getAllBooks(); // 訂閱當下：先 emit 當前完整書單
  yield* repository.watchBooks();       // 之後：轉發 repository 的變更通知
});
```

這個「當前值 + 後續變更」的組合就是 RxDart `BehaviorSubject` 內建的行為；純 `dart:async` 用兩行 `yield` 補上，不必為此引依賴。把初始值放組裝層而非機制層也有語意理由：repository 的 stream 誠實地只代表「變更」，「訂閱時要不要先看到當下」是消費端的呈現需求。

## 實作點三：dispose——關閉責任跟著 controller 的持有者

controller 的持有者是 repository，關閉責任就在 repository 的生命週期方法裡：

```dart
Future<void> close() async {
  await _booksController.close(); // 與資料庫連線一起釋放，避免 controller 洩漏
  // ...既有的連線清理
}
```

配合實作點一的 `isClosed` 防護，close 之後殘留的寫入呼叫會靜默略過通知、不會炸在使用者的操作路徑上。驗收面用三個測試釘住這組行為：寫入後 stream 收到最新書單、多訂閱者同時收到、close 後不再送出事件。

## 測試替身要同步這份契約

repository 有介面就有替身；替身漏掉 `watchBooks()` 會出現「production 正常、測試環境炸 `UnimplementedError`」或反過來的錯位。這次落地同步了三類替身、依「既有測試依不依賴多次 emit」給不同深度：

| 替身                            | 實作深度                                            | 理由                              |
| ------------------------------- | --------------------------------------------------- | --------------------------------- |
| 記憶體版 repository（行為替身） | 等價的 broadcast controller + 寫入點 emit + dispose | widget 測試要驗「寫入後畫面更新」 |
| 手寫 mock                       | `Stream.value(當前快照)` 簡化實作                   | 既有用法只讀一次、不依賴推送      |
| codegen mock（Mockito）         | 重新產生、stub 回空 stream                          | `implements` 不繼承介面預設實作   |

第三列是 Dart 特有的陷阱：mock 類別 `implements` 介面時**不會**繼承介面上的預設實作，介面加了新方法、所有 codegen mock 都要重新產生，否則消費新方法的測試在執行期才爆。mock 與真實實作的 stream 契約不對齊的後果（測試綠、production throw）在 [StreamController single vs broadcast](/work-log/dart_stream_controller_single_vs_broadcast/) 的修復清單有完整展開。

## 三個必答題

把 repository stream 接給任何 reactive 框架前，三個問題各給一個明確答案：

| 問題               | 本案答案                                            | 不答的預設後果                       |
| ------------------ | --------------------------------------------------- | ------------------------------------ |
| 幾個訂閱者？       | 多個 → `broadcast()`                                | 單訂閱：第二個訂閱者執行期 throw     |
| 訂閱當下要有值嗎？ | 要 → 組裝層先 `yield` 當前值                        | broadcast 不補歷史：畫面空到下次寫入 |
| controller 誰關？  | repository 持有、`close()` 一起關 + `isClosed` 防護 | 洩漏、或 close 後寫入路徑拋例外      |

介面歸屬的提醒收在最後：`watchBooks()` 的需求來自 Riverpod 消費端，但介面簽名只用 `dart:async Stream` 加 domain entity，所以它屬於 domain repository 介面——歸屬由介面用什麼語言表達決定，需求來自誰只決定介面該不該存在。Riverpod 型別止步於 `watchBooksProvider`、SQLite 型別止步於實作類，這條線就是三層各自的邊界。

## 下一步

- 為什麼要有這個 stream、補償刷新的三段演進：[ref.watch 觀察的是 provider 圖、不是資料庫](/work-log/flutter_riverpod_reactive_boundary_ref_watch/)
- 契約／機制／組裝的歸屬判準：[觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)
- 訂閱模型的完整選型分析：[StreamController single vs broadcast](/work-log/dart_stream_controller_single_vs_broadcast/)
- 這條 stream 跟 domain event 的分工：[domain event 與狀態流](/ddd/domain-event-vs-state-stream/)
