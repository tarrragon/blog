---
title: "導航路徑 test"
date: 2026-06-19
description: "Back 按鈕、route 可達性、go vs push 語意 — 驗證使用者能從任何畫面回到預期的位置"
weight: 2
tags: ["testing", "navigation", "widget-test", "routing", "flutter"]
---

導航路徑 test 驗證的是使用者在畫面之間的移動是否符合設計 — 每個畫面的 back 按鈕是否導向正確的上層畫面、每個 router 定義的路由是否從 UI 可達、`go` 和 `push` 的語意是否產生正確的返回堆疊。

## Back 按鈕 test

每個有 back 按鈕的畫面需要一個 test 驗證「按下 back 後導航到哪裡」。Back 按鈕的目標畫面依導航方式而定：

- `context.push('/terminal')` 進入 → back 回到推入前的畫面（首頁）
- `context.go('/terminal')` 進入 → back 行為依 router 設定，可能沒有上一頁

```dart
testWidgets('back from terminal returns to home (pushed)', (tester) async {
  await tester.pumpWidget(app());
  // 從首頁 push 到 terminal
  await tester.tap(find.text('Connect Terminal'));
  await tester.pumpAndSettle();
  expect(find.byType(TerminalScreen), findsOneWidget);
  // 按 back
  await tester.tap(find.byKey(Key('back_button')));
  await tester.pumpAndSettle();
  expect(find.byType(HomeScreen), findsOneWidget);
});
```

## Route 可達性 test

Router 定義的每個路由都應該有從 UI 可達的路徑（[ux-design 模組一 路由可達性](/ux-design/01-screen-state-machine/route-reachability/)）。Route 可達性 test 驗證「從首頁出發，透過 UI 操作能到達每個路由」。

```dart
testWidgets('enrollment route is reachable from home', (tester) async {
  await tester.pumpWidget(app());
  // 找到配對入口按鈕
  final enrollButton = find.text('Enroll Device');
  expect(enrollButton, findsOneWidget);
  // 點擊後到達 enrollment 畫面
  await tester.tap(enrollButton);
  await tester.pumpAndSettle();
  expect(find.byType(EnrollmentScreen), findsOneWidget);
});
```

不可達的路由在 test 中表現為「找不到導航到該路由的 UI 元素」。如果 router 定義了 `/enrollment` 但首頁沒有對應按鈕，`find.text('Enroll Device')` 會找不到元素 — test 失敗暴露入口缺失。

## `go` vs `push` 語意的 test

`go` 和 `push` 對返回堆疊的影響不同（[ux-design 模組五 導航模式](/ux-design/05-navigation-patterns/)）。Test 需要驗證正確的導航方式被使用：

### Push 語意：保留返回堆疊

Push 後按系統 back 鍵應該回到推入前的畫面。

```dart
testWidgets('push preserves back stack', (tester) async {
  await tester.pumpWidget(app());
  // push to enrollment
  await tester.tap(find.text('Enroll Device'));
  await tester.pumpAndSettle();
  // 系統 back 鍵
  final backButton = find.byTooltip('Back');
  await tester.tap(backButton);
  await tester.pumpAndSettle();
  // 應該回到首頁
  expect(find.byType(HomeScreen), findsOneWidget);
});
```

### Go 語意：替換路由堆疊

Go 後按系統 back 鍵的行為依 router 設定。如果 go 到的路由是根層級，系統 back 鍵可能退出 app 而非回到前一個畫面。

Test 策略：驗證 go 後的路由堆疊狀態。如果設計意圖是「切換工作區，不保留前一個畫面」，斷言系統 back 鍵不回到前一個畫面。

## 深層連結 test

深層連結（deep link）讓使用者從 app 外部直接進入特定畫面。Deep link test 驗證「直接導航到內部路由時，畫面和導航堆疊是否正確」。

```dart
testWidgets('deep link to /terminal shows terminal', (tester) async {
  await tester.pumpWidget(app(initialRoute: '/terminal'));
  expect(find.byType(TerminalScreen), findsOneWidget);
});
```

深層連結的特殊性在於使用者跳過了正常的導航流程。從首頁到 terminal 的正常流程可能經過認證 gate，但深層連結直接到 terminal — 認證 gate 是否仍然生效需要額外的 test。

## 下一步路由

- 狀態覆蓋策略 → [Widget test 的狀態覆蓋策略](/testing/04-ui-automation/state-coverage-strategy/)
- Playwright 驗證流程 → [Playwright 瀏覽器驗證流程](/testing/04-ui-automation/playwright-verification/)
- 路由可達性的設計原則 → [ux-design 模組一 路由可達性](/ux-design/01-screen-state-machine/route-reachability/)
