---
title: "Dart StreamController：single-subscription vs broadcast 的踩坑實錄"
date: 2026-05-05
draft: false
description: "Dart `StreamController()` 預設是單訂閱、被當廣播用了一段時間才在第二個訂閱者出現時暴露。整理三種 controller 行為的程式碼對比、修復決策跟 Rx / .obs 的深入比較、以及把 single-subscription 預設視為「設計缺陷」而非個人疏忽的制度層補強方向。"
tags: ["dart", "flutter", "stream", "debugging", "pos", "architecture"]
---

> **事故類型**：潛伏型設計缺陷、第二個訂閱者出現時才暴露
> **症狀**：`Bad state: Stream has already been listened to.`
> **根因**：在「`StreamController()` vs `StreamController.broadcast()`」這個零成本差異的選擇下、選了限制更高的單訂閱版本——當下只有一個訂閱者、限制沒曝光；新增第二個訂閱者就觸發底層型別契約。設計缺陷的本質是「**在零成本差異下不必要地縮小了未來空間**」、不是「沒預測到後來需求」。

---

## 事故場景

### 業務背景：POS 的多視角狀態同步

POS 系統本質上是「**單一交易狀態 + 多個視角同步呈現**」。一筆購物車的變化通常要立刻反映到：

- 收銀員操作的主螢幕
- 給顧客看的副螢幕（純顯示，看商品、總價、找零）
- 廚房或後場的出餐顯示
- 列印機（結帳當下觸發）
- 雲端同步、報表、會員紀錄

這些視角各自關心交易狀態的不同切面，但**都需要在狀態變動的當下被通知**。在系統設計上，這是個典型的「一個資料源、多個訂閱者」場景，本質就是事件廣播。

### 原始設計：一個事件來源，一個訂閱者

實作初期，「需要訂閱購物車變動」的角色只有一個——副螢幕。副螢幕在 app 啟動時就訂閱、整個 app 生命週期都在聽，純粹做主畫面的鏡像顯示。

於是負責提供「狀態變更通知」的 service 用了 dart:async 預設的 `StreamController` 對外發事件。事件 payload 設計成兩段資訊：

1. **當前完整商品列表**（給副螢幕這類「鏡像當前狀態」的訂閱者用）
2. **這次變動的具體品項**（移除或清空時為 null，預留給「需要知道改了哪一筆」的訂閱者）

第二段資訊當下沒人用，但 service 設計者保留了它，理由是「未來如果有訂閱者需要知道每次具體變動是什麼，不必再改介面」——一個合理的擴充性設計。

幾個月過去，這條 stream 只有副螢幕一個訂閱者，運作正常。

### 新需求：操作體驗優化

新需求出現：收銀員在尖峰時段連續掃商品，**畫面更新太快會分不清剛剛動到的是哪一筆**。如果是改價、改數量這類修改更明顯——數字突然變了，但視線焦點不在那一行就會錯過。

業務上希望：每次操作後，被改動的那一行在 UI 上有個視覺標記（高亮、邊框或角標都可），讓收銀員一眼確認剛剛動的是對的品項。標記停在最後一次操作的那行，直到下一次操作才轉移。

這個需求剛好對應 service 已經備妥但尚未被消費的資訊——service 對外的事件 payload 從原始設計就分兩段：一段是「當前完整的商品列表」、另一段是「這次變動的具體品項」。第二段是當初為「需要追蹤單筆變動的訂閱者」預留的擴充欄位、過去幾個月一直沒被消費。新需求只要新增一個訂閱者讀這段資訊、再把它對應到 UI 上的視覺標記即可——介面不需要變動、payload 結構不需要調整、實作範圍只限於新增訂閱端。

### 第二個訂閱者觸發底層限制

第二個訂閱者寫好、進入收銀頁面當下就 throw：

```text
The following StateError was thrown building Obx(...):
Bad state: Stream has already been listened to.
```

第一反應通常是「我哪裡寫錯了 / 是不是哪邊忘了 cancel」。檢查程式碼會發現新訂閱者寫得沒問題，副螢幕的訂閱也沒問題——**問題在底層 stream 的型別契約：整個生命週期內只允許被 listen 一次**。

這是 `StreamController()` 預設建構子的契約：建立的是 single-subscription stream、生命週期內最多承載**一個** listener。副螢幕第一個訂閱後佔據了唯一的 listener 位置；新加第二個訂閱者直接違反契約、執行期 throw。

更深一層的觀察是設計層面的不一致：業務需求一直具備廣播語義（多個視角同步呈現）、技術選型卻是「單一管線」的工具。需求初期只有一個訂閱者讓限制沒有可見的影響、但限制一直存在於型別契約裡。第二個訂閱者只是觸發條件、不是根因。

---

## 兩種 StreamController 的核心差異

| 維度                          | `StreamController()`（單訂閱）  | `StreamController.broadcast()` |
| ----------------------------- | ------------------------------- | ------------------------------ |
| 同時 listener 數              | 至多 1 個                       | 任意                           |
| 第二個 `.listen()`            | throw `Bad state`               | OK                             |
| listener cancel 後重新 listen | throw `Bad state`               | OK                             |
| 無 listener 時 add 的事件     | **buffer**，listener 出現時補送 | **直接丟棄**                   |
| listener `pause()` 行為       | 整個 stream 暫停（上游也卡）    | 對其他 listener 無影響         |
| 適用語義                      | 資料管線（單一消費者）          | 事件佈告欄（多消費者）         |

---

## 三組行為差異的程式碼驗證

### 1. 重複監聽

```dart
final c = StreamController<int>();
c.stream.listen(print);
c.stream.listen(print);
// ❌ Bad state: Stream has already been listened to.

final b = StreamController<int>.broadcast();
b.stream.listen((v) => print('A: $v'));
b.stream.listen((v) => print('B: $v'));
b.add(1);
// A: 1
// B: 1
```

值得注意的不只是「不能同時兩個 listener」——單訂閱 stream 的限制是**整個 lifecycle 只能 listen 一次**。即使第一個 listener 已經 `cancel()`、再呼叫 `.listen()` 仍會違反契約 throw。要重新訂閱必須重建 `StreamController`。

對 POS 場景的意義：副螢幕服務在 app 啟動時就建立訂閱、且不會 cancel——換句話說、stream 在啟動時就把唯一的 listener 配額分配給副螢幕、之後沒有可釋出的空間。

### 2. 監聽前的事件處理

```dart
final single = StreamController<int>();
single.add(1);
single.add(2);
// 此時還沒有 listener
single.stream.listen(print);
single.add(3);
// 輸出：1, 2, 3 ← 之前的事件被 buffer，listener 接上後補送

final broadcast = StreamController<int>.broadcast();
broadcast.add(1);
broadcast.add(2);
// 此時還沒有 listener
broadcast.stream.listen(print);
broadcast.add(3);
// 輸出：3 ← 監聽前的事件全部丟掉
```

這個差異對應用設計的影響：

- **單訂閱**保證 listener 不漏接，適合「資料完整性 > 即時性」（檔案讀取、計算結果序列）
- **broadcast** 不保留歷史，適合「即時性 > 完整性」（UI 事件、狀態變更通知）

如果改成 broadcast 後，希望「新訂閱者進場時能拿到一次當下的狀態」（例如 controller 進場時想知道當前購物車內容），broadcast 本身做不到，要靠 service 自己保留 `latest` 或在新訂閱時手動 push 一次。RxDart 的 `BehaviorSubject` 內建這行為，純 dart:async 沒有。

對 POS 案例：sticky 高亮只關心未來變更，**不在意歷史事件**——broadcast 的丟棄行為剛好不傷害語義。但如果是「副螢幕鏡像當前購物車」這種需求，新副螢幕插入時若需要立即顯示當下狀態，就要在訂閱後手動 read 一次 `cart.items`。

### 3. Pause 行為（最反直覺）

```dart
final single = StreamController<int>();
final sub = single.stream.listen(print);
sub.pause();
single.add(1);  // 不會立刻送出
sub.resume();
// 輸出：1 ← 暫停期間的事件 resume 後補送
```

```dart
final broadcast = StreamController<int>.broadcast();
final subA = broadcast.stream.listen((v) => print('A: $v'));
final subB = broadcast.stream.listen((v) => print('B: $v'));
subA.pause();
broadcast.add(1);
// 輸出：B: 1   ← B 照收，A 暫存
subA.resume();
// 輸出：A: 1   ← A resume 後補回
```

單訂閱的 pause 等於「整條管線暫停」，上游 add 的資料堆在 controller 內部、記憶體會漲。Broadcast 是 per-listener 暫停，互不影響。

POS 的副螢幕場景如果搭配無界事件源（例如背景條碼掃描器）、用單訂閱且某條路徑沒 resume、**會在 controller 內部累積未送出的事件、記憶體佔用持續上升**——這是 production OOM 的常見來源之一。

---

## 設計缺陷為什麼在初期沒有可見影響

### 訂閱者單一時、限制處於沉默狀態

副螢幕訂閱寫在 service 啟動時、屬於 app lifetime 訂閱、沒有 cancel / 重新訂閱的情境。在這個訂閱模式下：

1. 副螢幕第一個訂閱 → 佔據 single-subscription 的「唯一 listener」配額
2. 沒有第二個訂閱方 → 違反契約的條件不會出現
3. 限制存在於型別契約裡、但沒有可見的影響

當訂閱者擴增到第二個時、**這條 stream 的型別契約「整個生命週期只承載 1 個 listener」才開始產生可見的執行期影響**。注意這裡描述的是「**契約一直存在、只是沒有觸發違反條件**」——不是「契約因為新需求才變成限制」。型別契約是當下選擇 `StreamController()` 時就確定的、訂閱者數量只決定它何時被觸發。

### 設計缺陷 vs 需求演化的分界

但「為什麼能算設計缺陷」這個問題值得停下來釐清——當下只有一個訂閱者、需求變了才需要多訂閱、這聽起來不像是「設計缺陷」、更像是「需求演化」。兩者怎麼分？

關鍵不是「**有沒有預測到後來的需求**」、是「**當下的選擇是否在零成本差異下不必要地縮小了未來空間**」：

| 情境                                                               | 算什麼               |
| ------------------------------------------------------------------ | -------------------- |
| 當下零成本差、選了限制更高的選項（本 case：single 的 11 字元差）   | **設計缺陷**         |
| 當下高成本差、選了便宜的、後來需求變了（如「沒先建 plugin 系統」） | **需求演化、非缺陷** |
| 當下零成本差、選了通用的、後來真的不需要                           | 中性、額外彈性留著   |
| 當下高成本差、為「可能的未來」付了昂貴成本                         | **過度設計**         |

本 case 落在第一格——`StreamController()` vs `StreamController.broadcast()` 是 11 字元差、零認知負擔、零維護成本差異。即使當下只有副螢幕一個訂閱者、選 broadcast 也沒付任何代價、卻保留了未來的彈性。寫成 single 不是「對當下需求的精確匹配」、是**在零成本差異下不必要地縮小了未來空間**——這才是「設計缺陷」這個詞要描述的事。

加上 POS 系統的領域先驗強烈指向「多視角同步」（主螢幕 / 副螢幕 / 廚顯 / 雲端 / 列印是教科書級的 pub-sub 場景）、選 single-subscription 等於假設「這個 service 不會有多訂閱需求」——這個假設跟領域常識矛盾、即使在當下也站不住。

> 「成本對稱性 / 可逆性 / 領域先驗」三軸框架的完整推導見 [設計瑕疵還是避免過度設計？YAGNI 的真實適用條件](/record/yagni-boundary-three-axes/)——本 case 三軸都指向 broadcast、屬於 YAGNI 不適用的標準情境。

### 為什麼 IDE 與測試抓不到

- **Dart 編譯器**：型別簽章一樣（`Stream<T>`），編譯不會錯
- **靜態分析**：`dart analyze` 不會警告 single-subscription 用法的潛在風險
- **單元測試**：通常 mock 整條 stream，不會驗證真實 controller 是不是支援多訂閱
- **Widget test**：只跑單一頁面，不會同時掛多個訂閱模組
- **整合測試**：理論上能抓，但成本高，多數專案在這層覆蓋稀疏

要在事前抓到，可行的方式：

- **Lint rule**：自訂規則檢查 `StreamController()` 預設用法，要求加註解說明「為何刻意不用 broadcast」
- **Code review checklist**：service 對外暴露 stream 時，預設假設要 broadcast，single 必須有書面理由
- **架構規範**：直接禁用 raw `StreamController` 在 service 層，強制透過框架的廣播原語（`Rx`, `BehaviorSubject`, `ValueNotifier`）

---

## 修復決策過程

### 選項列舉

事故當下的選項：

| 選項                                     | 改動範圍           | 風險                           | 適用條件                           |
| ---------------------------------------- | ------------------ | ------------------------------ | ---------------------------------- |
| A. 改成 `.broadcast()`                   | service 一行       | 低                             | 多訂閱本來就合理                   |
| B. 第二個訂閱者透過第一個轉送            | 副螢幕服務變成 hub | 高，副螢幕不該知道 sticky 高亮 | 第二個需求是第一個的 strict subset |
| C. 新加一條平行 broadcast stream         | service 增 API     | 中                             | 兩訂閱關心不同維度                 |
| D. 改用框架的廣播原語（`Rx`、`Subject`） | service 介面變動   | 中                             | 系統性重構契機                     |

### 為什麼選 A

POS 的這條 stream 語義就是「購物車狀態變更廣播」、多訂閱者本來就符合領域模型。選 B 會讓副螢幕服務變成轉發中樞、跟它「純顯示」的職責衝突。選 C 增加重複資料源、未來容易兩條 stream 不同步。選 D 雖然在架構層更一致、但 scope 過大、不是事故當下適合做的決定。

A 是改一行的 minimal fix，且**修正了原本的設計缺陷**而不是繞過它。

### 容易漏的細節：mock 也要改

Service 如果有 mock 實作（測試替身）、mock 端也要同步改成 broadcast。否則會出現「測試環境通過、production 仍然 throw」的不對齊狀況——單元測試（注入 mock）跟 production（真實 service）使用不同的 stream 契約、限制沒被測試覆蓋。

這是「測試環境與 production 配置不對齊」的典型陷阱。事故當下要把「修真實實作」「修 mock」當成同一件事的兩個必做動作，分開做就會漏。比較好的長期策略是把這個約束放進 code review checklist，或在 service 介面層加註解註明「實作不論真假都必須是 broadcast 語義」。

### 還要檢查：所有寫入路徑都有完整 emit

事故修復不只是改 stream 類型，還要回頭審視「事件 payload 的完整性」。

回到事故場景：事件 payload 第二段（這次變動是哪筆）原本沒人用，所以幾個寫入路徑可能根本沒傳。副螢幕只看第一段（完整列表），傳不傳第二段對它沒差。**只有第二個訂閱者開始消費這段資訊時，遺漏才會暴露**。

這是廣播設計的一個系統性風險：**service 提供「為未來訂閱者保留」的擴充欄位時、這些欄位若沒有當下的消費者、缺漏不會在測試中浮現**。第一個真正使用該欄位的訂閱者出現後、才會暴露出某些 mutation 路徑沒填寫該欄位。

修復清單：

- [ ] 把 single-subscription 改成 broadcast（真實實作 + mock 雙改）
- [ ] 審視所有寫入路徑，確保事件 payload 的每個欄位都正確填寫
- [ ] 確認第二個訂閱者的 dispose / cancel 邏輯
- [ ] 訂閱者進場時若需要「當下狀態」，要補一次直接讀取（broadcast 不保留歷史）

---

## 何時該選哪個

### 選 `StreamController()` 的情境

- 確定**只有一個消費者**，且這個契約被寫進文件 / 介面註解
- 需要保證**每個事件都被消費**（buffer 是 feature）
- 像 Future 但會發多個值：檔案讀取、HTTP response body chunks、long-running task 進度回報

### 選 `StreamController.broadcast()` 的情境

- 有**多個訂閱者**，或不確定未來會不會多
- 事件是「正在發生」的通知，**錯過就算了**（UI 事件、狀態變更廣播、event bus、application-level domain events）
- 不在意進場前的歷史事件（如果在意，自己保留 `latestValue`）

### 一個粗略的決策法

> 「如果某天有人想加第二個 listener，這在語義上合理嗎？」
>
> - 合理 → 一開始就用 broadcast
> - 不合理 → 用單訂閱，並在註解寫清楚為什麼

應用層的 service 通知絕大多數情境都偏向 broadcast；single-subscription 的甜蜜點在底層 I/O 或一次性 task 進度（兩者都有「單一消費者 + 不能漏接」的明確契約）。

對 POS 場景：service 對外暴露的「狀態變更通知」幾乎都落在 broadcast 區——POS 的本質就是多裝置 / 多視圖共享同一份交易狀態（主螢幕、副螢幕、廚顯、雲端、列印機）。

---

## 補救與替代方案

### 已有 single-subscription stream，想對外提供 broadcast

不用改 controller 類型，可以包一層：

```dart
final singleStream = someController.stream;
final broadcastView = singleStream.asBroadcastStream();

// 對外公開 broadcastView，原本的 singleStream 內部仍是 single-subscription
```

`asBroadcastStream()` 把單訂閱當 source，對外提供 broadcast view。一旦呼叫過一次，後續訂閱者都拿這個 view。

注意：這個方法只能呼叫**一次**、第二次會 throw。實務上要保留回傳值在 service 內部做 cache。

### 想要「broadcast + 新訂閱拿最後一次值」

標準 `dart:async` 沒有這功能。要嘛自己實作：

```dart
class ReplayLastNotifier<T> {
  final _controller = StreamController<T>.broadcast();
  T? _latest;

  Stream<T> get stream async* {
    if (_latest != null) yield _latest as T;
    yield* _controller.stream;
  }

  void add(T value) {
    _latest = value;
    _controller.add(value);
  }
}
```

要嘛用 RxDart 的 `BehaviorSubject`，內建這行為。POS 副螢幕鏡像場景特別適合 `BehaviorSubject`：副螢幕進場時就能立即看到當下購物車內容，不必等下一次變更。

### Flutter 生態系的替代

純 `StreamController` 在 Flutter app 層比較少見，更常用的是：

| 工具                        | 廣播語義 | 內建保留最後值    | 備註                   |
| --------------------------- | -------- | ----------------- | ---------------------- |
| `ValueNotifier<T>`          | 是       | 是                | 適合單一值狀態         |
| `ChangeNotifier`            | 是       | N/A（無資料傳遞） | 訂閱者自己讀狀態       |
| `Rx<T>`（GetX）             | 是       | 是                | `.listen()` / `ever()` |
| `BehaviorSubject`（RxDart） | 是       | 是                | API 接近原生 stream    |
| `StateNotifier`（Riverpod） | 是       | 是                | 不可變狀態風格         |

如果你已經在用某個狀態管理框架，優先用框架的廣播原語，而不是 raw `StreamController`。`StreamController` 在 Flutter app 通常是底層 I/O service 才用（藍牙、socket、sensor）。

下一節對其中最常被混用的一組——raw `StreamController` 跟 GetX 的 `Rx` / `.obs`——做完整對比，因為這也是事故當下會考慮「是不是該整個換掉」的對象。

---

## 深入比較：raw StreamController vs GetX 的 Rx / .obs

### 先釐清：Rx 跟 .obs 的關係

在 GetX 裡，`Rx<T>` 是底層 reactive value container，`.obs` 是把任何值包成對應 Rx 子類的 syntax sugar：

```dart
// 三種寫法本質等價
final count1 = 0.obs;            // 推導為 RxInt
final count2 = RxInt(0);         // 顯式建構特化子類
final count3 = Rx<int>(0);       // 較少用，因為 RxInt 提供更多 operator overload

count1.value++;  // RxInt 可直接用 ++
count3.value++;  // Rx<int> 也行，但缺了 RxInt 的算術特化
```

`.obs` 對不同型別回傳不同特化子類：

| 寫法         | 回傳型別        | 特化能力                               |
| ------------ | --------------- | -------------------------------------- |
| `0.obs`      | `RxInt`         | 算術 operator (`+=`, `++`, `<` 等)     |
| `0.0.obs`    | `RxDouble`      | 算術 operator                          |
| `''.obs`     | `RxString`      | 字串 operator (`+`, `==`, `compareTo`) |
| `false.obs`  | `RxBool`        | `toggle()`、邏輯 operator              |
| `[1,2].obs`  | `RxList<int>`   | `add`/`remove`/`assignAll` 自動觸發    |
| `{}.obs`     | `RxMap`/`RxSet` | 集合 mutation 自動觸發                 |
| `User().obs` | `Rx<User>`      | 一般 reassign 觸發                     |

特化子類的核心好處：**原生語法的 mutation（`+=`、list `add`、string concat）都直接觸發 reactive 通知**，不需要手動 `notifyListeners()` 或 `add()`。

結論：`.obs` 跟 `Rx` 不是兩個不同概念，是同一個機制的兩種建構寫法。後者多了型別推導與特化命名。

### 概念差異

|          | StreamController                     | Rx<T> / .obs                               |
| -------- | ------------------------------------ | ------------------------------------------ |
| 本質     | 事件管線（push events）              | 反應式值容器（push values + 保留 current） |
| 比喻     | 水管                                 | 帶讀數的水位感應器                         |
| 起始狀態 | 沒有 latest，listener 加入後才開始接 | 出生就有 `.value`，隨時可讀                |
| 設計目的 | 通用非同步資料流                     | 專為 UI 反應式更新設計                     |

### 相同任務的程式碼對比

**任務**：service 對外暴露一個整數狀態，UI 顯示它且當值變化時自動 rebuild。

```dart
// ===== Raw StreamController 寫法 =====

class CounterService {
  int _value = 0;
  final _controller = StreamController<int>.broadcast();

  int get value => _value;
  Stream<int> get stream => _controller.stream;

  void increment() {
    _value++;
    _controller.add(_value);
  }

  void dispose() => _controller.close();
}

// UI:
StreamBuilder<int>(
  stream: service.stream,
  initialData: service.value,  // 不帶這個首次 build 是 null
  builder: (context, snap) => Text('${snap.data}'),
)
```

```dart
// ===== Rx / .obs 寫法 =====

class CounterService extends GetxController {
  final value = 0.obs;

  void increment() => value.value++;

  // 不需要寫 dispose；Rx 隨 controller 生命週期自動清理
}

// UI:
Obx(() => Text('${service.value.value}'))
```

差異一目了然：

- **樣板量約 4-5 倍差距**
- StreamController 要自己維護 latest value
- StreamController 要記得寫 `dispose`
- `Obx` 自動追蹤所有 `.value` 讀取，不需要手動 listen/cancel
- StreamBuilder 要處理 `initialData` 與 `snap.data` 為 null 的情境，Rx 沒這問題（永遠有值）

### Rx 內部其實就是 StreamController + ValueNotifier

`Rx<T>` 底層用 `StreamController.broadcast()` 加上一個 `_value` 欄位。`Obx` widget 在 build 時開一個訂閱範圍，期間任何 `.value` getter 會被追蹤；build 結束後對應的 stream 訂閱自動建立，值變化時觸發 widget rebuild。

簡化心智模型：

```dart
class Rx<T> {
  T _value;
  final _ctrl = StreamController<T>.broadcast();

  Rx(this._value);

  T get value {
    RxInterface.proxy?.addListener(_ctrl.stream);  // Obx 注入的依賴追蹤代理
    return _value;
  }

  set value(T v) {
    if (_value == v) return;  // ← 等值不觸發
    _value = v;
    _ctrl.add(v);
  }
}
```

（真實實作更複雜，但骨架是這樣。）

換句話說 **Rx ≈ broadcast StreamController + ValueNotifier + 自動依賴追蹤 + 特化子類**。理解這層之後，後面所有「Rx 為什麼這樣」的問題都能從這個本質推回去。

### 完整對比表格

| 維度                                    | StreamController                                        | Rx<T> / .obs                                                 |
| --------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------ |
| Framework 依賴                          | 無（dart:async 標準庫）                                 | 需 GetX                                                      |
| 同訂閱數                                | single 或 broadcast 二選一                              | 永遠 broadcast                                               |
| Latest value 保留                       | 不保留，自己管 `_latest`                                | 內建 `.value`                                                |
| 訂閱機制                                | 手動 `.listen()`                                        | `Obx` 自動 / `ever()` worker 手動                            |
| 取消訂閱                                | 手動 `sub.cancel()`                                     | Obx widget dispose 時自動 / worker 綁 controller 時自動      |
| Widget 整合                             | `StreamBuilder`                                         | `Obx` / `GetX<T>`                                            |
| 初始值處理                              | 需 `initialData` 或 listener 加入後才有                 | 出生就有，無 null 期                                         |
| 等值是否觸發                            | 是，每次 add 都送                                       | 否，`==` 相等不觸發（可 `.refresh()` 強制）                  |
| 集合反應性                              | List 變動要自己 emit                                    | RxList/Map/Set 內建 mutation hook                            |
| 物件內部變動                            | 自己控制何時 emit                                       | 需 `.refresh()` 或換新 reference                             |
| Stream operators (map/where/buffer/...) | 完整 dart:async API                                     | 用 `.stream` 取出後可接                                      |
| Pause/resume                            | 支援（broadcast 為 per-listener）                       | 透過 underlying stream 才有                                  |
| Error 傳遞                              | `addError()` + `onError` callback                       | 較少使用，多以 try/catch 處理上游                            |
| 樣板量                                  | 多（5-10 行/欄位）                                      | 少（1 行/欄位）                                              |
| 學習曲線                                | 標準 Stream 概念，跨框架通用                            | GetX 特有 API，受框架綁定                                    |
| 測試                                    | 直接測 stream，工具豐富（`expectLater`/`emitsInOrder`） | Rx 可用 `.value` assert，跨 controller 測試要 mock GetX 注入 |
| 跨 isolate                              | 支援                                                    | 不支援（Obx 依賴 main isolate）                              |
| Type safety                             | 強 generic                                              | 強 generic，但 `.obs` 推導要注意特化型別                     |
| 適用場景                                | 底層 I/O、需要 stream 組合運算                          | UI state、application state                                  |

### Rx 的特殊行為與陷阱

#### 1. 等值不觸發更新

```dart
final name = ''.obs;
name.value = '';     // 不觸發 listener（'' == ''）
name.value = 'A';    // 觸發
name.value = 'A';    // 不觸發（'A' == 'A'）
```

如果需要「每次 set 都觸發」（例如重新打 API 不管值有沒有變），用 `.refresh()` 或 `.trigger()`：

```dart
name.refresh();              // 強制通知所有 listener，不變更 value
name.trigger('A');           // 強制通知，且 set value
```

#### 2. 物件內部變動不觸發

```dart
final user = User(name: 'A').obs;
user.value.name = 'B';                         // ❌ 不觸發，reference 沒變
user.refresh();                                // ✅ 強制觸發
user.value = user.value.copyWith(name: 'B');   // ✅ 換新 reference 自然觸發
```

這跟 immutable 風格（Freezed、Equatable）配合最自然，`copyWith` 一定產出新 reference。

#### 3. Obx 必須讀到至少一個 `.value`

```dart
Obx(() => Text('hello'))                  // ⚠️ warning: improper use
Obx(() => Text('${counter.value}'))       // ✅
```

`Obx` 靠 build 期間攔截 `.value` getter 建立訂閱關係，build callback 內完全沒讀任何 Rx 就不知道要 subscribe 誰。

#### 4. RxList / RxMap 的 mutation 規則

```dart
final items = <int>[].obs;
items.add(1);          // ✅ 觸發（RxList 重寫了 add）
items.value.add(2);    // ❌ 不觸發（操作的是底層 List）
items[0] = 99;         // ✅ 觸發（RxList 重寫了 []=）
items.refresh();       // 補救
```

特化集合類別重寫了 `add`/`remove`/`[]=`/`clear` 等 method 讓它們自動 emit；繞過 wrapper 直接操作 `.value` 就會跳過這層。

#### 5. .obs 推導出的特化型別可能不是你想要的

```dart
final list = [1, 2, 3].obs;        // RxList<int>
final list2 = <num>[1, 2, 3].obs;  // RxList<num> — 注意泛型推導

// 自定義型別需明確
final user = User(name: 'A').obs;  // Rx<User>，不是「RxUser」
```

### Rx 的 worker 類型（service 之間的訂閱模式）

`Obx` 是 widget 自動訂閱；service 內或 controller 之間的訂閱用 `worker`：

```dart
// 每次變化都觸發
final disposer = ever(counter, (value) => print('changed to $value'));

// debounce — 連續變化只取最後一次
debounce(
  searchText,
  (value) => searchAPI(value),
  time: Duration(milliseconds: 500),
);

// throttle — 固定間隔最多觸發一次
interval(
  scrollPosition,
  (value) => analytics(value),
  time: Duration(seconds: 1),
);

// 只觸發一次後自動移除
once(loginState, (value) => navigateHome());

// 監聽多個 Rx，任一變動就觸發
everAll([a, b, c], (_) => recompute());

// 手動清理
disposer.dispose();
```

這些 worker 在 `GetxController.onInit` 裡註冊時會被綁定到 controller 生命週期，controller dispose 時自動清；在 controller 外註冊就要自己 `.dispose()`。

### 何時選哪個

#### 選 raw `StreamController`

- 寫**底層 service**（藍牙、socket、sensor、background isolate 通訊）
- 需要**豐富的 stream operators 鏈**（`map`/`where`/`buffer`/`distinct`/`merge`/`combineLatest`...）
- 對外提供的 API 不想綁特定狀態管理框架，要保持框架中立
- 需要 backpressure / pause-resume 等進階流量控制
- 跨 isolate 資料傳遞

#### 選 `Rx` / `.obs`

- 寫 **UI state** 或 **application state**
- 已在用 GetX，沿用一致
- 需要「保留當前值 + 多訂閱者」這個常見組合
- 想要 widget 自動追蹤，不想手動寫 listen/cancel
- service 內部 latest value 與通知的樣板太多次，懶得繼續寫

### 把事故場景改寫成 Rx 看看

回到事故場景。如果 service 從一開始就用 reactive value container（如 Rx）來表達它的對外契約，整個問題會以另一種方式消失。

**對外契約的轉變**：service 不再「對外發送事件」，而是「對外暴露兩個可被觀察的狀態屬性」——當前完整的商品列表、最後一次變動的品項。訂閱方不需要 `listen()` 一條 stream，而是直接讀取屬性的當前值，並且系統保證屬性變化時觀察者會被通知。

**在這個契約下回頭看每個訂閱方的需求**：

- **副螢幕（鏡像當前商品列表）**：只關心「列表屬性」變動，不在乎是哪一筆變動。它建立一個對列表屬性的觀察，每次變動就重畫
- **收銀主畫面（最後變更項標記）**：只關心「最後變動屬性」，每次變動就更新高亮哪一行
- **未來的訂閱方**（KDS、列印、雲端、analytics）：各自選關心的屬性建立觀察

兩個訂閱者觀察的是**不同屬性**，互不干擾；同一個屬性也允許多個觀察者（reactive value 天生是廣播語義）。

**事故的兩個技術問題在這個契約下自動消失**：

1. **single vs broadcast 的選擇問題不存在**——reactive value 沒有「單訂閱版本」，每個觀察者天生並存
2. **進場拿不到歷史事件的問題不存在**——觀察者進場時可以直接讀屬性的「當前值」，不必等下一次變動

更深一層的觀察：raw stream 是「以時間軸上的事件為一等公民」的工具，適合「事件本身就是有意義的（log、命令、訊息）」場景；reactive value 是「以狀態為一等公民」的工具，適合「下游關心的是當前是什麼，不是過去發生了什麼」場景。**POS 多視角同步的本質是後者**——副螢幕關心的是「現在購物車裡有什麼」，不是「過去 5 分鐘掃進了哪些商品的時序」。

把這個認知一般化：當業務語義是「多個視角共享當前狀態」時，工具應該是 reactive value（Rx / ValueNotifier / BehaviorSubject）；當業務語義是「事件流的時序」時，工具才是 stream。本案的根因是「業務語義（共享狀態）」跟「工具語義（事件流）」錯配；single-subscription 是錯配關係下第一個被觸發的契約限制、但即使換成 broadcast、仍會在「進場拿不到歷史事件」這個層次撞到語義錯配。

### 是否該全面改寫成 Rx

事故當下不該。理由：

1. **scope 控制**：事故修復原則是 minimal change，`StreamController()` → `.broadcast()` 一字之差就解決
2. **回歸風險**：把 service 介面從 `Stream<T>` 改成 `Rx<T>`，所有訂閱方（副螢幕、UI、未來的 KDS / 雲端同步）都要改 listen 方式
3. **耦合代價**：如果 service 介面原本是 framework-neutral 的（純 dart:async），改 Rx 等於把 GetX 綁進公開 API，未來要換框架成本變高
4. **測試成本**：改 Rx 之後，所有針對該 service 的測試都要改 mock 方式

該重構的時機：

- 整個系統已經 implicit 綁 GetX，介面 framework-neutral 的成本沒實質效益
- 新增 service 時直接用 Rx，舊的 stream-based service 等下次大改一起換
- 發現自己重複寫「`_latest` + `StreamController.broadcast` + getter + emit + close」的樣板太多次，Rx 是現成解
- 整理技術債的專屬 sprint，可以系統性換掉

事故修復應該專注 minimal fix；架構改造是另一張單。

---

## 除錯思維

`Bad state: Stream has already been listened to.` 的根因落在 stream 定義端的型別契約、不在訂閱端。檢查順序：

1. **這條 stream 是 single-subscription 還是 broadcast？**
   - 從定義端確認（`StreamController()` vs `StreamController.broadcast()`）、訂閱端只承載限制、看不出契約類型
2. **若是 single、選 single 的理由有書面記錄嗎？**
   - 介面註解 / 設計文件有記錄 → 看理由是否仍成立
   - 沒有記錄 → 屬於「用了預設建構子、沒做選擇」、回到當下三軸判斷
3. **多訂閱在語義上合理嗎？**
   - 合理 → 改 broadcast、屬於修正型別契約跟業務語義對齊
   - 不合理 → 第二個訂閱者的需求要重新設計（透過第一個 listener 轉送、或拉新 stream）

把「這條 stream 該不該支援多訂閱」做為設計階段的明確決策、判斷成本（跑三軸）落在當下、且不依賴未來需求是否實際出現。

---

## 延伸：POS 場景的多訂閱模式

POS 系統本質上就是「中央交易狀態 + 多視圖/多裝置鏡像」，是 broadcast stream 最自然的應用領域。常見訂閱者：

| 訂閱方           | 關心什麼                      | 訂閱生命週期       |
| ---------------- | ----------------------------- | ------------------ |
| 收銀員主螢幕     | 完整購物車、UI 高亮、結帳金額 | 收銀頁面開啟期間   |
| 副螢幕（顧客面） | 商品名、單價、總價、找零      | App lifetime       |
| 廚房顯示（KDS）  | 已下單品項、出餐順序          | App lifetime       |
| 列印服務         | 結帳明細、會員資訊            | 觸發式（結帳當下） |
| 雲端同步         | 所有交易事件                  | App lifetime       |
| Analytics        | 使用者行為、轉換率            | App lifetime       |

設計階段先假設「會有多個訂閱者」、「未來訂閱者數量會增加」、「每個訂閱者只關心事件的一部分屬性」——這正是 broadcast 的典型語義；之後新功能要訂閱、設計上會自然容納。

對應的設計建議：

1. **Service 對外的事件 stream 預設 broadcast**——single-subscription 視為例外、要在介面註解書面說明
2. **事件 payload 設計成 record 或 sealed class**——包含「是什麼變動 + 變動的詳細資料」、讓不同訂閱者各取所需
3. **不要假設訂閱者之間的觸發順序**——broadcast 的 listener 之間沒有保證順序、訂閱者要假設彼此獨立
4. **進場時若需要初始狀態、提供 `currentValue` getter**——broadcast 不保留歷史、用 explicit getter 補這個缺口

---

## 參考資料

- [Dart `StreamController` API doc](https://api.dart.dev/stable/dart-async/StreamController-class.html)
- [Dart `StreamController.broadcast` constructor](https://api.dart.dev/stable/dart-async/StreamController/StreamController.broadcast.html)
- [Dart `Stream.asBroadcastStream` method](https://api.dart.dev/stable/dart-async/Stream/asBroadcastStream.html)
- [Dart language tour - Asynchronous programming: streams](https://dart.dev/tutorials/language/streams)
- [RxDart `BehaviorSubject` doc](https://pub.dev/documentation/rxdart/latest/rx/BehaviorSubject-class.html)
