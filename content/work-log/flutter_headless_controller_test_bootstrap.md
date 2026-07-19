---
title: "讓 UI 控制器在 headless 測試立起來：platform channel mock、no-op 子類與 postFrameCallback 的手工補位"
date: 2026-07-17
draft: false
description: "流程測試要驅動真實編排，而編排住在 UI 控制器裡——能不能在無畫面的測試環境把控制器立起來，決定整個測試套件的形態。先用 spike 驗證閘門、再逐項中和平台耦合，讓控制器在 headless 環境可建構。"
tags: ["flutter", "dart", "test", "platform-channel", "controller", "flow-test", "getx"]
---

> **核心議題**：跨服務的[流程測試](/testing/knowledge-cards/flow-test/)若只在 service 層打轉，控制器裡的編排（順序、防護動作、收尾同步）就是測不到的盲區——而實戰裡的 bug 恰好密集出現在編排層。能否直接 `Get.put(控制器)` 立起真實控制器，是套件形態的閘門問題，值得用一條最小測試先做 spike。
> **案例骨幹**：POS App 的主控制器在 `onInit` 做四件與平台耦合的事（掃碼廣播、相機偵測、外接顯示器、frame callback）。逐一拆解後發現全部可以在 headless 環境用低成本手段中和——spike 首跑即過，此後所有流程測試都能驅動真實編排、零複製漂移。

---

## 1. 為什麼非立起控制器不可

替代方案是「測試裡複製編排步驟」：service 層一步步照著控制器的順序呼叫。它能跑，但有結構性缺陷——控制器改了順序、測試不會知道，兩邊靠註解互指維持同步。這個漂移風險不是理論：同一個專案裡，一個「刷新要在列表同步之後」的順序約束，正是靠流程測試驅動真實編排才抓到的（複製版測試當時是綠的）。

所以開工前先回答閘門問題：**控制器立不立得起來？** 答案決定套件形態，用一條最小測試 spike，不要寫到一半才發現。

## 2. 四個啟動期障礙與各自的中和手段

控制器 `onInit` 的每一項平台耦合，對應一個測試側的責任：

| 啟動期動作                          | 在測試環境的行為                                                                                    | 中和手段                                                                            |
| ----------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 訂閱硬體掃碼廣播（Android channel） | `start()` 打 platform channel → 未 await 的 Future 拋 `MissingPluginException` → 測試 zone 判定失敗 | 服務**子類覆寫** `start`/`stop`/`messages` 為 no-op 與空 stream，註冊子類取代原服務 |
| 相機偵測（`availableCameras()`）    | 拋 `MissingPluginException`（有 catch，留雜訊 log）                                                 | `MethodChannel` 掛 mock 回空清單，讓偵測走正常路徑得到「無相機」                    |
| 外接顯示器 plugin                   | **建構子**就訂閱 EventChannel——物件一 new 就打 channel                                              | 建立前先為該 EventChannel 掛 mock stream handler                                    |
| `addPostFrameCallback` 裡補訂閱     | 純 `test()` 不跑 frame，callback 永不觸發                                                           | 測試裡手動呼叫同一個訂閱方法，註解說明對應關係                                      |

channel mock 的兩個 API 各對一種 channel：

```dart
// EventChannel：plugin 建構子就會 listen，必須在建立前掛好
TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
    .setMockStreamHandler(const EventChannel('channel-name'),
        MockStreamHandler.inline(onListen: (args, events) {}));

// MethodChannel：讓查詢類呼叫得到正常的空結果，而非例外
TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
    .setMockMethodCallHandler(const MethodChannel('channel-name'),
        (call) async => call.method == 'query' ? <dynamic>[] : null);
```

「建構子就訂閱 EventChannel」是其中最陰的一個——mock 掛晚了炸在 `new` 的當下，錯誤點在別人的 package 深處。判準：**引入外接硬體類 plugin 時，先看它的建構子做了什麼**。

## 3. no-op 子類 vs mock 框架

掃碼廣播服務的替換用的是手寫子類而不是 mock 框架：

```dart
class SilentBroadcastService extends BroadcastService {
  @override Stream<Message> get messages => const Stream.empty();
  @override Future<void> start() async {}
  @override Future<void> stop() async {}
}
```

理由：要中和的只有「碰平台」的三個成員，其餘行為保留真實；子類的差異一目瞭然，mock 框架在這裡只會增加閱讀成本。這與「服務鏈盡量走真實實作」的流程測試精神一致——假的東西越少，測試的證言越可信。

## 4. 立起來之後：非同步收尾的等待紀律

控制器編排常見 fire-and-forget（收尾動作不 await 就返回）。測試斷言若緊跟在呼叫後面，就是在跟背景收尾賽跑——單獨跑碰巧贏、整批跑排程不同就輸。等待紀律：

```dart
await controller.checkout();
for (var i = 0; i < 100; i++) {
  if (終態條件到達) break;      // 狀態已清除、計數已到位
  await pumpEventQueue();      // 沖刷 microtask 與已到期 timer
}
```

輪詢「可觀察的終態」而非固定 sleep——固定延遲只是把起跑線挪後，在更慢的環境照樣輸。通用層的分析見 [T.C8 fire-and-forget 編排的測試競態](/testing/cases/fire-and-forget-test-race/)。

## 5. 可複用的判準

1. 流程測試開工前，先 spike「編排的宿主立不立得起來」——答案改變整個套件的寫法。
2. 控制器啟動期的每一項平台耦合 = 測試 harness 的一項責任；逐項列表處理，不要碰到一個修一個。
3. EventChannel 的 mock 要在「任何會建構該 plugin 物件的程式」之前掛好。
4. postFrameCallback 承載的初始化，在純 test 環境要手動補跑，並在兩處註明對應。
5. harness 一旦成立就收斂為共用 bootstrap——之後每條流程測試的成本只剩劇本本身。

## 下一步

- harness 與真實網路測試的互斥約束 → [TestWidgetsFlutterBinding 會擋掉真實網路](/work-log/flutter_test_binding_blocks_real_network/)
- 這個形態的完整方法論 → [語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)
