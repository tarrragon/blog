---
title: "Flutter GoRouter 導航設計"
date: 2026-06-19
description: "GoRouter 的路由定義、導航 API（go / push / pushReplacement）、redirect 機制和 ShellRoute 的使用場景"
weight: 2
tags: ["ux-design", "navigation", "flutter", "gorouter", "routing"]
---

GoRouter 是 Flutter 官方推薦的 declarative router。路由定義集中在一個 `GoRouter` 物件中，導航操作用 URL path 表達（`context.go('/terminal')`），支援 deep link、redirect、和巢狀路由。

## 路由定義

GoRouter 的路由定義是一棵樹，每個節點是一個 `GoRoute`，指定 path 和 builder。

```dart
GoRouter(routes: [
  GoRoute(path: '/', builder: (context, state) => HomeScreen()),
  GoRoute(path: '/enrollment', builder: (context, state) => EnrollmentScreen()),
  GoRoute(path: '/terminal', builder: (context, state) => TerminalScreen()),
]);
```

路由定義是 app 所有可到達畫面的完整清單。新增畫面時先在路由定義中加入 path，再實作 builder。路由定義同時也是路由可達性檢查的 source of truth（[路由可達性](/ux-design/01-screen-state-machine/route-reachability/)）。

## 導航 API

GoRouter 提供三個主要的導航方法，語意不同，適用場景不同。

### context.go(path)

替換整個導航堆疊。`go('/terminal')` 讓使用者直接到 terminal 畫面，按 back 不會回到前一個畫面（堆疊已被替換）。

適合場景：切換主要工作區。從登入畫面到首頁（登入成功後使用者不應該按 back 回到登入畫面）。

### context.push(path)

把新畫面推入導航堆疊。`push('/enrollment')` 讓使用者到 enrollment 畫面，按 back 回到前一個畫面。

適合場景：暫時離開做一件事，做完回來。從首頁到配對畫面，配對完成後按 back 回首頁。

### context.pushReplacement(path)

替換堆疊頂端的畫面。不改變堆疊深度 — 前一個畫面被新畫面取代，按 back 回到更早的畫面。

適合場景：步驟式流程中的前進。步驟 1 → pushReplacement 步驟 2 → pushReplacement 步驟 3。使用者在步驟 3 按 back 不會回到步驟 2（已被替換），而是回到流程開始前的畫面。

## Redirect 機制

GoRouter 的 redirect 在每次導航前執行，可以根據 app 狀態（登入狀態、權限）把使用者導向不同畫面。

```dart
GoRouter(
  redirect: (context, state) {
    final isLoggedIn = authState.isLoggedIn;
    if (!isLoggedIn && state.matchedLocation != '/login') return '/login';
    if (isLoggedIn && state.matchedLocation == '/login') return '/';
    return null; // 不 redirect
  },
  routes: [...],
);
```

Redirect 集中管理「什麼條件下使用者不能到某個畫面」的邏輯。比在每個畫面的 `initState` 中各自檢查更容易維護和測試。

## ShellRoute（巢狀導航）

ShellRoute 讓多個畫面共享同一個外殼（tab bar、bottom navigation、drawer）。子路由的導航在 shell 內發生，shell 本身不變。

```dart
ShellRoute(
  builder: (context, state, child) => ScaffoldWithNavBar(child: child),
  routes: [
    GoRoute(path: '/home', builder: ...),
    GoRoute(path: '/search', builder: ...),
    GoRoute(path: '/profile', builder: ...),
  ],
)
```

ShellRoute 適合 tab bar 導航模式 — 底部的 tab bar 是 shell，每個 tab 的內容是子路由。

## 下一步路由

- go / push / pushReplacement 的 UX 語意 → [go vs push vs pushReplacement 語意表](/ux-design/05-navigation-patterns/go-push-semantics/)
- iOS 和 Android 的導航差異 → [iOS HIG vs Material Design 導航差異](/ux-design/05-navigation-patterns/ios-vs-material-navigation/)
- Deep link 設計 → [Deep link 設計](/ux-design/05-navigation-patterns/deep-link-design/)
