---
title: "加書後統計不刷新 — ref.watch 觀察的是 provider 圖、不是資料庫"
date: 2026-07-16
draft: false
description: "頁面用了 Riverpod 卻在資料寫入後不更新、或發現自己在導航返回點補 loadData()、用 EventBus 事件觸發 reload 時使用。ref.watch 的 reactive 範圍是 provider 圖上的狀態變化；資料庫寫入不在圖上，補償刷新的出現就是這個缺口的訊號。"
tags: ["flutter", "dart", "riverpod", "state-management", "stream", "architecture", "debugging"]
---

> **觸發場景**：書庫管理 App 的資料管理頁顯示書庫統計（總書數、待補完書籍數）。從這頁進入搜尋或掃描流程加了書、返回後統計停在舊值；退回首頁再重新進入、數字才更新。
> **疑問來源**：ViewModel 明明用 Riverpod、`build()` 裡也有 `ref.watch`，為什麼資料變了畫面不動？

---

## 核心認知：ref.watch 的觀察範圍

`ref.watch` 建立的是「這個 provider 的**狀態**變化時、重新執行我」的依賴——它觀察的是 provider 圖上的節點，範圍到 provider 的狀態為止。provider 背後的資料庫發生了什麼，不在這張圖上。

出問題的 ViewModel 依賴長這樣：

```dart
final bookRepositoryProvider = Provider<BookRepository>((ref) {
  return SQLiteBookRepository();
});

class DataManagementViewModel extends Notifier<DataManagementState> {
  @override
  DataManagementState build() {
    // 這個 watch 只在 bookRepositoryProvider「換了一個 repository 實例」時觸發 rebuild
    final repository = ref.watch(bookRepositoryProvider);
    // ...
  }
}
```

`bookRepositoryProvider` 是單例 `Provider<BookRepository>`：它的狀態是「那個 repository 物件本身」、整個 App 生命週期不會變。所以這個 `ref.watch` 建立的依賴**永遠不會觸發**——SQLite 寫入了一百本書，provider 的狀態（物件參考）一動不動。

畫面「有用 Riverpod」跟畫面「會對資料變更反應」是兩件事。要成立後者，「資料變更」本身必須是 provider 圖上的一個節點。

## 三段補償演進

這個缺口在專案裡先後被三種方式處理過。前兩段是補償——在 reactive 邊界外面用別的機制把刷新縫回來；第三段才把缺口本身補上。

### 第一段：導航返回點補償

最直覺的修法：既然「從加書流程返回」是統計過期的時刻，就在導航返回點重新載入。

```dart
Future<void> _navigateAndRefresh(BuildContext context, String route) async {
  await Navigator.pushNamed(context, route);
  // pop 返回後重新載入統計
  await ref.read(dataManagementViewModelProvider.notifier).loadData();
}
```

它解掉了當下的 bug、也暴露了補償的形狀：**涵蓋面靠枚舉**。頁面上每個會導向「可能寫入資料的流程」的入口（匯入捷徑、搜尋、掃描）都要記得包這個 helper；漏一個入口就漏一條刷新路徑。而且它只涵蓋「本頁導航出去再回來」——資料在別的路徑變更（背景匯入、其他頁面操作）時，這頁照樣過期。

### 第二段：EventBus 橋接

第二段把既有的 domain event 系統接過來：用 `StreamProvider` 包 EventBus、ViewModel `ref.listen` 監聽，任何事件進來就 `loadData()`。

```dart
final dataManagementEventStreamProvider = StreamProvider<DomainEvent>((ref) {
  return ref.watch(eventBusProvider).on<DomainEvent>();
});

// ViewModel build() 內
ref.listen(dataManagementEventStreamProvider, (_, __) => loadData());
```

這一段看起來把「資料變更」接進 provider 圖了——但接進來的節點是**業務事件流**、不是資料狀態。兩個新問題浮出來：

1. **涵蓋面仍靠枚舉，只是枚舉對象換了**。導航補償要枚舉入口、事件橋接要枚舉「每條寫入路徑都有發事件」。實際盤點發現搜尋加書與掃描加書路徑沒有發布任何 domain event——這兩條路的刷新斷鏈，導航補償被迫保留、兩套機制並存。
2. **domain event 被借用成 UI 刷新訊號**。事件系統的設計語意是「記錄發生了什麼」（跨 domain 通知、日誌、審計）；拿它當刷新訊號後，「要不要發這個事件」開始被「某頁要不要刷新」綁架。監聽端也只能全事件監聽再考慮過濾——任何無關事件都觸發一次重新查詢。這條界線的完整推導在 [domain event 與狀態流](/ddd/domain-event-vs-state-stream/)。

### 第三段：repository 補觀測出口

第三段修的是缺口本身：repository 介面新增 `Stream<List<Book>> watchBooks()`、實作在每個寫入方法尾端 emit 最新書單、DI 層用 `StreamProvider` 包裝成 provider 圖上的節點。

```dart
final watchBooksProvider = StreamProvider<List<Book>>((ref) async* {
  final repository = ref.watch(bookRepositoryProvider);
  yield await repository.getAllBooks(); // 初始值：訂閱當下先給完整書單
  yield* repository.watchBooks();       // 後續變更
});
```

從此「資料變更」是 provider 圖上的一級節點：任何衍生視圖 `ref.watch(watchBooksProvider)` 就取得 reactive 更新，統計頁、書庫清單、待補完列表全部走同一條觀察路徑。涵蓋面從「枚舉入口／枚舉事件」變成「寫入方法的集合」——新增加書路徑時，寫入必然經過 repository 的寫入方法，emit 自動涵蓋，沒有「記得補」這個動作。實作細節（broadcast、初始值、dispose）在 [StreamProvider 包 repository watch stream](/work-log/flutter_streamprovider_wraps_repository_watch/)。

## 判準：補償刷新是缺口訊號

三段演進收斂成一條可操作的判讀：

| 訊號                                           | 判讀                                                 |
| ---------------------------------------------- | ---------------------------------------------------- |
| 導航返回點出現 `loadData()` / `refresh()` 補償 | 「資料變更」不在 provider 圖上、有人在圖外手動縫刷新 |
| 為了讓某頁刷新而監聽 domain event              | 業務事件被借用為狀態通知、涵蓋面靠「記得發事件」維持 |
| 同一份資料有多個視圖、各自維護 load 時機       | 缺一個共同的觀測節點、每個視圖都在重複解同一題       |
| `ref.watch` 對象是單例 `Provider<Repository>`  | 這個 watch 永不觸發 rebuild、reactive 是名義上的     |

每個訊號的修法都指向同一個方向：讓資料變更成為 provider 圖上的節點（`StreamProvider` 包 repository 的 stream 出口、或 Notifier 持有狀態），視圖回到純 `ref.watch`。

## 介面歸屬：需求來自誰、不決定介面放哪

`watchBooks()` 的需求完全來自 presentation 層——是 Riverpod 想觀察資料變更、domain 自己沒有這個需要。直覺會說「誰需要就放誰那層」，把 Stream 出口做在 infrastructure 或 presentation 的某個 service 裡。

實際的歸屬判準是**介面用什麼語言表達**、不是需求來自誰：

| 介面簽名裡的型別                  | 歸屬判定                                      |
| --------------------------------- | --------------------------------------------- |
| `dart:async` 的 `Stream<T>`       | 語言標準庫、與 `Future<T>` 地位等同、不算洩漏 |
| domain entity（`Book`）           | domain 自有語言、不算洩漏                     |
| Riverpod 型別（`StreamProvider`） | 框架語言、進 domain 介面就是洩漏              |
| SQLite 型別（`Database`）         | infrastructure 語言、同上                     |

`Stream<List<Book>> watchBooks()` 全句只用語言標準庫加 domain entity——它是 `getAllBooks()` 的 push 版本、放 domain repository 介面語意自然。需求從消費者出發決定介面**該不該存在**；介面**放哪一層**由表達語言決定。這條判準的完整推導（含機制層與組裝層的歸屬）在 [觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)。

## 下一步

- 契約／機制／組裝三層歸屬的完整判準：[觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)
- 事件與狀態流的語意分界（為什麼 EventBus 橋接是越權）：[domain event 與狀態流](/ddd/domain-event-vs-state-stream/)
- watchBooks 落地的三個實作點（broadcast、初始值、dispose）：[StreamProvider 包 repository watch stream](/work-log/flutter_streamprovider_wraps_repository_watch/)
- provider 圖與容器的關係（狀態屬於容器、宣告只是配方）：[App 永遠卡在載入畫面](/work-log/flutter_riverpod_dual_container_state_desync/)
