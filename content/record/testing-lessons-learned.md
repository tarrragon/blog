---
title: "測試全過但有 Bug"
date: 2026-03-12
draft: false
description: "從多廚房印表機功能開發經驗，歸納測試設計的三大陷阱與檢查清單，避免測試全過但線上有 Bug"
tags: ["測試", "方法論", "Dart", "整合測試", "除錯"]
---

源自 2026-03 線上點單多廚房印表機功能開發過程中的除錯經驗。
33 個測試全部通過，但實際執行卻有 2 個 Bug。

<!--more-->

## 案例背景

開發「多廚房印表機列印」功能，核心流程：

```text
OnlineOrderPrintHandler.printAppendedOrder
  → _buildItemPrinterMapping       (品項分派到印表機)
  → _receiptBuilder.buildReceiptLines (組裝收據)
  → _printCenter.printReceiptLines    (列印)
    → printer.init()                  (初始化 generator)
    → printer.printText()             (用 generator 產生 ESC/POS 指令)
    → printer.sendBytes()             (傳送到印表機)
```

兩個在測試中未被發現的 Bug：

| Bug | 根因 | 現象 |
|-----|------|------|
| FakePrinter generator 未初始化 | `init()` 跳過了 `Generator` 的建立 | `printText` 拋出 `LateInitializationError`，被 try-catch 吞掉，回傳 `false` |
| 所有品項都分配到同一台印表機 | fallback 邏輯找到第一台空 mapping 的印表機就用了 | 2 台印表機只有 1 台在工作 |

---

## 遺漏測試的三個原因

### 1. 測試「自己寫的答案」而非「實際行為」

**問題程式碼：**

```dart
// ❌ 手動構造預期結果，沒有走過真正的分派邏輯
test('品名長度奇數分配到第一台，偶數分配到第二台', () {
  final result = OnlineOrderPrintResult(
    itemPrinterMapping: {
      'item-1': 'kitchen-2', // 手動寫死「偶數→第二台」
      'item-2': 'kitchen-1', // 手動寫死「奇數→第一台」
    },
    // ...
  );
  record.applyPrintResult(result);
  expect(record.kitchenItemPrintJobs['item-1']!.printerId, 'kitchen-2');
});
```

這個測試的名稱叫「品項分派邏輯」，但實際上測的是 `applyPrintResult` 能不能正確儲存資料——分派邏輯（`_buildItemPrinterMapping`）根本沒被執行過。

**修正後：**

```dart
//  透過 printAppendedOrder 驅動，讓真正的分派邏輯跑一遍
test('2 台空 productNames 印表機：品名奇偶分配到不同印表機', () async {
  PrintCenter.to.initFakeKitchenPrinters(); // 真實的 setUp
  final result = await handler.printAppendedOrder(payload, printMain: false);
  expect(result.itemPrinterMapping['item-1'], 'kitchen-2'); // 驗證實際分派結果
  expect(result.kitchenResults['kitchen-1'], isTrue);       // 驗證列印成功
});
```

> **教訓：測試應該驅動被測程式碼的真實路徑，而非用手動構造的資料驗證資料搬運是否正確。**

---

### 2. 只測「覆寫的方法」，沒測「繼承的方法」

**問題程式碼：**

```dart
// ❌ 只測了 FakePrinter 自己覆寫的方法
test('sendBytes 不報錯', () async {
  final printer = FakePrinterAdapter('test-printer');
  await printer.init();
  await printer.sendBytes([1, 2, 3]); // sendBytes 是 FakePrinter 覆寫的 no-op
});
```

但實際列印路徑呼叫的是 `printText()`——這是從 `GeneralPrinterAdapter` 繼承的方法，內部依賴 `generator`。`sendBytes` 不用 `generator`，所以永遠不會觸發 Bug。

**修正後：**

```dart
//  測試實際列印路徑會用到的方法
test('init 後 printText 不報錯（驗證 generator 已初始化）', () async {
  final printer = FakePrinterAdapter('test-printer');
  await printer.init();
  await printer.printText('測試文字'); // 走 generator.text() → sendBytes
});

//  反向驗證：確認未初始化的行為
test('未 init 就呼叫 printText 會拋出錯誤', () async {
  final printer = FakePrinterAdapter('test-printer');
  expect(() => printer.printText('測試文字'), throwsA(isA<Error>()));
});
```

> **教訓：覆寫子類別時，要測試「上層呼叫者實際會用到的方法」，而非只測「你覆寫了什麼」。**

---

### 3. 驗證「有沒有」但不驗證「對不對」

**問題程式碼：**

```dart
// ❌ 只檢查 key 存在，不檢查 value
expect(result.kitchenResults.containsKey('kitchen-1'), isTrue);
expect(result.kitchenResults.containsKey('kitchen-2'), isTrue);
```

因為缺少 `ReceiptBuilderService`，列印路徑在 `buildReceiptLines` 就斷了，try-catch 回傳 `false`。但測試只檢查 `containsKey`，不管是 `true` 還是 `false`，都會通過。

**修正後：**

```dart
//  驗證列印結果的值
expect(result.kitchenResults['kitchen-1'], isTrue,
    reason: '廚房1 列印應成功');
expect(result.kitchenResults['kitchen-2'], isTrue,
    reason: '廚房2 列印應成功');
```

而要讓值為 `true`，就必須讓完整路徑跑通——這迫使我們補上 `FakeReceiptBuilderService`：

```dart
class FakeReceiptBuilderService extends ReceiptBuilderService {
  @override
  Future<List<ReceiptLine>> buildReceiptLines(
    ReceiptData data, ReceiptTemplate template,
  ) async {
    return [ReceiptLine.singleLine(data.title)];
  }
}
```

> **教訓：斷言要驗證「結果的值」，不要只驗證「結果的存在」。特別是 Map、List 這類容器，`containsKey` / `isNotEmpty` 不等於正確。**

---

## 設計測試的方法論

### 一、從呼叫路徑出發，而非從程式碼結構出發

不要按照「這個 class 有哪些方法」來寫測試，要按照「使用者操作觸發了什麼路徑」來寫。

```text
使用者操作                    要測試的完整路徑
─────────                    ──────────────
追加點餐送出     →  handler.printAppendedOrder
                      → _buildItemPrinterMapping  ← 分派邏輯
                      → buildReceiptLines          ← 收據組裝
                      → printReceiptLines           ← 實際列印
                      → printText / printRow        ← 印表機操作

點擊重印按鈕     →  retryItemKitchenPrint
                      → printAppendedOrder(kitchenItemIds: {itemId})
```

### 二、整合測試與單元測試的分工

```text
                    單元測試                     整合測試
─────────────────────────────────────────────────────────
測什麼？          單一方法的輸入輸出             多個元件串接的結果
假設什麼？        其他元件是正確的               驗證元件之間的銜接
能抓到什麼 Bug？  演算法邏輯錯誤                 初始化遺漏、依賴缺失、
                                                介面不匹配、狀態傳遞錯誤
本案例中          KitchenPrinterConfig           printAppendedOrder +
                  .handlesProduct                PrintCenter + FakePrinter +
                  → 匹配邏輯正確                 ReceiptBuilderService
                                                → 端到端路徑正確
```

**關鍵原則：如果你的功能涉及「多個元件協作」，只寫單元測試是不夠的。**

### 三、替 try-catch 設計專門的測試

try-catch 是測試的天敵——它會把錯誤吞掉，讓測試誤以為一切正常。

```dart
// 生產程式碼中的 try-catch
Future<bool> _printKitchenReceipt(...) async {
  try {
    final lines = await _receiptBuilder.buildReceiptLines(data, template);
    await _printCenter.printReceiptLines(lines: lines, printer: config.printer);
    return true;
  } catch (e) {
    debugPrint('kitchen print failed: $e');
    return false;  // ← Bug 被吞掉，變成靜默失敗
  }
}
```

對策：
- **斷言成功路徑的值**：不要只檢查「沒拋錯」，要檢查回傳值是 `true`
- **提供完整的依賴**：讓 try 區塊能完整執行，而非依賴 catch 來「通過」測試
- **寫專門的失敗測試**：故意製造失敗條件，驗證錯誤處理行為

### 四、Fake / Mock 的設計原則

```text
                    Fake（假實作）               Mock（模擬物件）
─────────────────────────────────────────────────────────
適用場景          需要跑通完整路徑               只需驗證互動次數/參數
本案例            FakeReceiptBuilderService      不適用（我們要驗證端到端結果）
                  FakePrinterAdapter
```

設計 Fake 時的檢查清單：

- [ ] 繼承/實作的方法中，有哪些是**上層呼叫者實際會用到的**？
- [ ] 這些方法依賴哪些**內部狀態**（如 `late` 變數）？
- [ ] Fake 的 `init()` 是否正確初始化了這些內部狀態？
- [ ] Fake 回傳的資料是否足以讓下游繼續執行？

---

## 檢查清單：避免「測試全過但有 Bug」

寫完測試後，用以下問題自我檢查：

1. **路徑覆蓋**：這個測試有沒有走過被測功能的「關鍵程式碼路徑」？還是只測了資料搬運？
2. **斷言強度**：斷言是檢查「值是否正確」還是只檢查「東西存不存在」？
3. **依賴完整性**：被測程式碼的所有依賴（Service、Adapter）是否都有提供？缺少的依賴是否被 try-catch 靜默吞掉？
4. **繼承鏈**：如果用了 Fake/Mock 子類別，上層呼叫者用到的「繼承方法」是否有被測試到？
5. **反向驗證**：是否有測試「錯誤情境」來確認你理解了 Bug 的根因？

---

## 本案例的最終測試結構

```text
28 tests

無廚房印表機時的基本行為（4 tests）
  └── 基本的 handler 行為，不需要廚房印表機

OnlineOrderRecord 模型（7 tests）
  └── 單元測試：狀態管理、applyPrintResult

FakePrinterAdapter（6 tests）
  ├── init / sendBytes — 基本功能
  ├── printText after init —  驗證 generator 初始化（抓 Bug 1）
  └── printText without init —  反向驗證

KitchenPrinterConfig（2 tests）
  └── 單元測試：品名匹配邏輯

品項分派邏輯 — 整合測試（4 tests）     ← 全部重寫
  ├── 2 台空 mapping → odd/even 分配     抓 Bug 2
  ├── 1 台空 mapping → fallback
  ├── 明確 mapping 優先匹配
  └── kitchenItemIds 篩選
  （全部透過 printAppendedOrder 驅動，有 FakeReceiptBuilderService）

PrintCenter 廚房印表機管理（5 tests）
  └── 註冊、移除、初始化、向後兼容
```
