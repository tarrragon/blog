---
title: "Widget test 的狀態覆蓋策略"
date: 2026-06-19
description: "從畫面狀態矩陣推導 widget test case — 每個狀態的顯示、操作、退出路徑都是獨立的斷言目標"
weight: 1
tags: ["testing", "widget-test", "state-machine", "coverage", "flutter"]
---

Widget test 的狀態覆蓋策略是用[畫面狀態矩陣](/ux-design/knowledge-cards/screen-state-matrix/)（[ux-design 模組一](/ux-design/01-screen-state-machine/state-matrix-definition/)）作為 test case 的來源。矩陣的每一行（一個狀態）對應至少一個 test case，矩陣的每一欄（顯示 / 可用操作 / 退出路徑）對應該 test case 中的斷言。

## 從矩陣到 test case 的轉換規則

### 每個狀態至少一個 test case

矩陣中的每一行代表畫面的一個狀態。每個狀態產生一個 test case，驗證三件事：

1. 該狀態下的顯示元素是否存在
2. 該狀態下的可用操作是否可觸發
3. 該狀態下的退出路徑是否可到達

矩陣補列的 initializing 狀態（查詢對象有獨立生命週期時、「還不知道」不等於離線 — [U.C10](/ux-design/cases/service-worker-cold-start-false-offline/)）同樣是一行、同樣產生 test case：斷言初始化窗口顯示過渡指示而非離線、timeout 後才轉入離線狀態。

以 app_tunnel Terminal 畫面為例，五個狀態產生五個 test case：

```dart
testWidgets('idle state shows blank and allows cancel', (tester) async {
  await tester.pumpWidget(terminalScreen(state: idle));
  expect(find.byType(CircularProgressIndicator), findsNothing);
  expect(find.byKey(Key('cancel_button')), findsOneWidget);
});

testWidgets('error state shows message, retry, and back', (tester) async {
  await tester.pumpWidget(terminalScreen(state: error));
  expect(find.text('連線失敗'), findsOneWidget);
  expect(find.byKey(Key('retry_button')), findsOneWidget);
  expect(find.byKey(Key('back_button')), findsOneWidget);
});
```

### 退出路徑是獨立的斷言

退出路徑驗證的是「使用者能否離開當前狀態」。斷言方式是 tap 退出按鈕後驗證導航是否發生：

```dart
testWidgets('error state back button navigates to home', (tester) async {
  await tester.pumpWidget(terminalScreen(state: error));
  await tester.tap(find.byKey(Key('back_button')));
  await tester.pumpAndSettle();
  expect(find.byType(HomeScreen), findsOneWidget);
});
```

矩陣中退出路徑為空的狀態 = 沒有退出路徑的 test case = UX 死胡同。如果在填寫 test case 時發現某個狀態沒有退出路徑可以斷言，這本身就是設計缺口的發現。

## 覆蓋率的衡量

Widget test 的狀態覆蓋率 = 有 test case 的狀態數 / 矩陣中的總狀態數。100% 代表矩陣中每個狀態都有對應的 test case。

狀態覆蓋率和 line coverage 衡量不同的東西。Line coverage 衡量「程式碼中有多少行被執行過」，狀態覆蓋率衡量「設計中有多少狀態被驗證過」。一個狀態的 test case 可能覆蓋很少的程式碼行（只驗證特定狀態下的 UI），但確認了該狀態的設計意圖被正確實作。

## 狀態轉換的 test

除了靜態狀態的驗證，狀態之間的轉換也需要 test。矩陣的「進入條件」欄定義了觸發轉換的事件。

```dart
testWidgets('connecting transitions to connected on ws success', (tester) async {
  await tester.pumpWidget(terminalScreen(state: connecting));
  // 模擬 WebSocket 連線成功
  connectionManager.emit(ConnectionState.connected);
  await tester.pumpAndSettle();
  expect(find.byType(TerminalView), findsOneWidget);
});
```

狀態轉換 test 的數量 = 矩陣中的狀態轉換邊數。五個狀態的畫面可能有 8-12 條轉換邊，每條邊一個 test case。

狀態覆蓋和轉換覆蓋確認畫面的邏輯正確性後，[導航路徑 test](/testing/04-ui-automation/navigation-path-test/) 進一步驗證 back 按鈕和 route 可達性。矩陣本身的填寫方法和四欄定義見 [ux-design 模組一 畫面狀態矩陣](/ux-design/01-screen-state-machine/state-matrix-definition/)。如果需要在視覺層面確認 UI 呈現的一致性，[螢幕截圖比對](/testing/04-ui-automation/visual-regression/)提供 visual regression 的實作方式。
