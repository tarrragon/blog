---
title: "Dart test 的跨檔案 GetX 狀態污染：flaky 真因不是 fail 訊息上的那個 test"
date: 2026-05-07
draft: false
description: "`flutter test` 整套跑會隨機 ~50% fail、但單獨跑該 file 100% 過、且每次 fail 的 test 不固定時回來看。教你別被 fail 訊息指的 test 騙、改看 `+N -1` 累計位置找真兇：根因是 dart test runner 同 process 共用 GetX state，解法是 setUp 開頭 Get.reset() 切斷跨 file 污染。"
tags: ["dart", "flutter", "test", "getx", "debugging", "flaky"]
---

> **事故類型**：cross-file 狀態污染、dart test runner 同 process 共用 GetX
> **症狀**：`flutter test` 約 50% 機率隨機失敗、每次失敗的 test 不固定；單獨跑該 test file 100% 通過
> **根因**：dart test runner 在同 process 內跑多個 test file 共用 GetX 容器；前面 file 的 setUp 留下殘留（測試 mode 旗標、未 dispose 的 controller、stream subscription）污染後面 file 的測試環境

---

## 事故場景

### 表面症狀

跑 `flutter test` 全 suite，Run 1 fail、Run 2 pass、Run 3 pass、Run 4 fail、Run 5 fail。看到的失敗訊息類似：

```text
00:27 +125: PrintCenter 廚房印表機管理 kitchenPrinter 向後兼容取第一台 - did not complete [E]
00:27 +125: PrintCenter 廚房印表機管理 重複呼叫 initFakeKitchenPrinters 會清除舊的 - did not complete [E]
00:27 +125: Some tests failed.
```

訊息直接點名 `PrintCenter 廚房印表機管理` group 的兩個 test「did not complete」。直覺反應：那兩個 test 有問題、去看那個 file。

### 第一次診斷與失敗的修法

打開 `online_order_print_handler_test.dart`，看到 `PrintCenter 廚房印表機管理` group 的 setUp 沒做 `Get.reset()`、純粹依賴 outer setUp 的 `Get.reset()`。判斷可能是 outer setUp 的 `OnlineOrderPrintHandler.onInit` 在這個 group 留下副作用（stream subscription 之類），於是給這個 group 加自己的 reset：

```dart
group('PrintCenter 廚房印表機管理', () {
  late PrintCenter printCenter;

  setUp(() {
    Get.reset();  // ← 加這行隔離 outer setUp 的副作用
    printCenter = PrintCenter(FakePrinterAdapter('main'));
    Get.put(printCenter);
  });

  tearDown(() {
    Get.reset();  // ← 加這行確保不殘留
  });
});
```

跑 5 次：Run 1 fail、Run 2 pass、Run 3 pass、Run 4 fail、Run 5 fail——**flakiness 比例沒改變**。

修錯了。

### 重新診斷：看 `+N -1` 計數的真正位置

把 fail 輸出存進檔案、仔細看 progress line 的 `+N -1` 部分：

```text
00:08 +125 -1: ... auto_service_config_test.dart: ...
00:08 +126 -1: ... settle_page_order_object_test.dart: SettlePage.orderObject reactivity searchedOrder 變更：badge 立即更新（list 與 selected 都沒命中時）
00:08 +127 -1: ... auto_service_config_test.dart: ...
```

`-1` 在第 126 個 test 才第一次出現——失敗的不是 print handler，是中間夾的 **widget test**。再看另一次 fail：

```text
00:09 +124 -1: ... settle_page_order_object_test.dart: SettlePage.orderObject reactivity orderList[i] 替換：badge 從「已完成」立即變「退貨」
```

不同 run 失敗的 test 不一樣，但都是 `settle_page_order_object_test.dart` 的不同 case。print handler 的 `did not complete` 是被牽連、不是源頭。

### 確認 root cause：單獨跑全綠

把 widget test 單獨重複跑 8 次：

```bash
for i in 1 2 3 4 5 6 7 8; do
  flutter test test/widgets/settle_page_order_object_test.dart 2>&1 | tail -1
done
```

8/8 全綠。**單獨跑沒問題、混進全 suite 跑就 flaky**——這是 cross-file pollution 的固定特徵。

---

## 為什麼 `did not complete` 訊息會誤導

dart test runner 的失敗訊息設計上有個盲點：

- `+N` 是累計通過數
- `-N` 是累計失敗數
- `did not complete` 是某個 test 還沒跑完整體就終止了（process 退出 / 超時 / 前面有未捕捉錯誤導致 runner 提前結束）

當前面有 test 失敗、後面的 test 沒機會跑、這些後面的 test 會印 `did not complete`——但**它們本身沒問題**。看到 `did not complete` 直覺會想「這個 test 卡住了」、但真實意思更接近「這個 test 還沒跑、上游已掛」。

正確的診斷流程：

1. 找 `-N` 第一次出現的位置（`-1` 表示第一個失敗）
2. 對照那一行的 test 名稱、那才是真正失敗的源頭
3. `did not complete` 出現的 test 通常只是受牽連

我第一次掉的坑：直接讀 `did not complete` 的 test 名、跳過了「往前找 `-1` 第一次出現」這步。

---

## 為什麼 cross-file 會污染：dart test runner 與 GetX 的不對齊

### dart test runner 的執行模型

`flutter test`（背後是 `dart test`）跑全 suite 時不一定 1 file = 1 isolate。預設行為：

- 多個 test file 可能共用同一個 isolate / Dart VM
- 共用 isolate 等於共用所有 process-scoped state（static field、singleton、未 GC 的全域物件）

並發策略受 `--concurrency` 與 platform 影響、行為不固定，但「共用 process」是日常常見現象。

### GetX 的 state 是 process-scoped

GetX 的 `Get.put` / `Get.find` 把 instance 放進一個 process-global 容器。`Get.reset()` 清空容器、但有些東西不會被 reset：

- `Get.testMode` 是 static field、`reset()` 不動它
- 如果 instance 在 onInit 內 subscribe 了 stream（例如 `BroadcastReceiveService.messages.listen`）、`Get.reset()` 移除 instance reference 但 **subscription 不會自動 cancel**
- StreamController / Timer / Future.delayed 在 GetX 容器外仍然活著

### 實際發生的污染鏈

跑全 suite 時，假設執行順序是：

```text
1. test/services/online_order/...      ← 最前面
2. test/widgets/settle_page_order_...   ← 中間
3. test/services/auth_service_config... ← 後面
```

第 1 個 file 的 setUp 若有 `Get.put(SomeService())`，service 在 onInit 內訂閱了 stream，就算 tearDown 跑了 `Get.reset()`、那條 stream subscription 仍 active。第 2 個 file 開始跑時：

- 它的 setUp 也呼叫 `Get.put(...)`、放進去的物件可能是 **完全不同類型** ——但 GetX 容器內可能還有上一輪殘留的物件
- 第 2 個 file 的 widget test 進入 widget tree、Obx 訂閱、各種 reactive 路徑啟動
- 上一輪殘留的 stream / timer 此時 fire、進到不該觸及的 state

整個 race 在「殘留事件何時 fire vs widget test 何時 expect」之間，所以 flakiness 是 ~50% 而不是 100%。

---

## 解法：setUp 開頭主動 reset

對任何用 GetX 的 test，setUp 最開頭就該 reset、不要依賴上一個 file 的 tearDown 跑乾淨：

```dart
setUp(() {
  // 同 process 內跑全 suite 時其他 test file 可能在 GetX 容器留殘留
  // （Get.testMode、未 dispose 的 controller、未 cancel 的 stream subscription），
  // setUp 開頭主動 reset 切斷 cross-file 污染
  Get.reset();
  Get.testMode = true;
  // ... 之後再 Get.put 自己需要的東西
});

tearDown(() {
  Get.reset();
});
```

把這個 pattern 加到所有 widget test 與 controller test 的 setUp 之後，全 suite 連跑 5 次：

```text
Run 1: All tests passed!
Run 2: All tests passed!
Run 3: All tests passed!
Run 4: All tests passed!
Run 5: All tests passed!
```

5/5 全綠，flakiness 消失。

### 為什麼 tearDown 的 reset 不夠

理論上 tearDown 已經 `Get.reset()` 了，下個 test 的 setUp 看到的應該是乾淨容器——但這個推理在「同 file 內」成立、跨 file 不成立：

- 跨 file 之間 dart test runner 在 file 邊界做的事是不確定的（可能整個 isolate 重啟、也可能只是切換 group）
- 即使前一個 file 的 tearDown 跑完，跨 file 的某個 microtask / timer callback 仍可能在後一個 file 的 setUp 之前 fire
- 用 setUp 開頭的 reset 等於再保險一次、把這個邊界內的不確定性吃掉

---

## 除錯思維：flaky test 的固定診斷流程

```bash
1. 看是不是真的 flaky
   - 連跑 5~10 次、計算成功率
   - 隨機失敗（不是 100% 也不是 0%）→ 進入 flaky 診斷

2. 找真正的失敗源頭
   - 看 progress line `+N -M`、找 -1 第一次出現位置
   - 不要直接讀 "did not complete"、那是受牽連訊息

3. 判斷是 in-file 還是 cross-file 污染
   - 失敗的 test 單獨跑：
     - 100% 通過 → cross-file 污染（其他 file 的殘留進來）
     - 也會隨機 fail → in-file 污染（同 file 的 test 之間互相污染）

4. 補對應的隔離
   - cross-file → setUp 開頭 Get.reset()
   - in-file → 看是 setUp/tearDown 沒清乾淨還是 test 之間共享 mutable state
```

---

## 教訓

1. **`did not complete` 不是失敗源、是被牽連訊息**——往前找 `-1` 第一次出現的位置才是真正失敗的 test。
2. **單獨跑通過 + 全 suite fail = cross-file pollution**——這是 flaky test 最常見的固定模式之一、有專屬的解法（setUp reset）、不要當成「資料時序的隨機性」隨便重跑。
3. **tearDown 清不夠、setUp 也要清**——任何用 GetX 的 test 應該在 setUp 開頭主動 `Get.reset()`、不要依賴上一個 file 的 tearDown。
4. **第一次診斷錯誤是常態、要回到證據**——順著 fail 訊息修是直覺反應、但訊息可能誤導；停下來看計數欄位、單獨跑驗證、才是穩定的診斷方式。

---

## 適用範圍

這個 pattern 不限於 GetX、適用於任何在 process-scoped global state 註冊東西的框架：

- `Provider` 的 `MultiProvider` / 全域 instance
- `Riverpod` 的 `ProviderContainer`（雖然 Riverpod 設計上更鼓勵 per-test container）
- 自寫的 service locator / singleton
- 任何 `static` field 累積的狀態

只要框架的 state 跨 test boundary 而 dart test runner 又在同 process 跑多 file，cross-file pollution 都可能發生。setUp 開頭主動 reset 是通用防身術。

---

## 參考資料

- [Dart `package:test` runner concurrency docs](https://github.com/dart-lang/test/blob/master/pkgs/test/doc/configuration.md#concurrency)
- [GetX `Get.reset()` source](https://github.com/jonataslaw/getx)
- [Flutter `flutter_test` binding lifecycle](https://api.flutter.dev/flutter/flutter_test/TestWidgetsFlutterBinding-class.html)
