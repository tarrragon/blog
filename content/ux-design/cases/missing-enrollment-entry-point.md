---
title: "U.C4 首頁缺配對入口按鈕、導航流未完整列出"
date: 2026-06-19
description: "Flutter app 首頁只有 Connect Terminal 按鈕、沒有 Enroll Device 入口 — 使用者首次使用時找不到配對功能。根因是導航流設計只考慮了日常操作（UC-02 連線）、遺漏了首次操作（UC-01 配對）的入口"
weight: 4
tags: ["ux-design", "case-study", "navigation", "entry-point", "onboarding", "flutter"]
---

這個案例的核心責任是說明導航流設計必須覆蓋所有操作情境的入口，不只是最常用的那個。

## 觀察

app_tunnel 首頁在 W2-001 修復前只有一個按鈕：Connect Terminal（對應 UC-02 日常連線）。配對功能（UC-01 首次配對）沒有入口 — `EnrollmentScreen` 和 `QrScannerScreen` 都存在且可運作，但首頁沒有按鈕導航過去。

Router 定義了三條路由，全部可存取：

```dart
GoRouter(routes: [
  GoRoute(path: '/', builder: ... HomeScreen()),
  GoRoute(path: '/enrollment', builder: ... EnrollmentScreen()),
  GoRoute(path: '/terminal', builder: ... TerminalScreen()),
]);
```

但 HomeScreen 只有一個 `context.go('/terminal')` 按鈕，`/enrollment` 路由存在但從 UI 無法到達。

W2-001 修復加入 `OutlinedButton.icon` 連結到 `/enrollment`，並用 `context.push`（非 `context.go`）讓配對完成後能返回首頁。

| 指標 | 值                                                      |
| ---- | ------------------------------------------------------- |
| 影響 | 首次使用者無法配對（功能存在但入口缺失）                |
| 修復 | 加一個 `OutlinedButton` + `context.push('/enrollment')` |
| 根因 | 導航流只設計了「日常連線」入口，遺漏「首次配對」入口    |

## 判讀

1. **操作盤點有四個操作，首頁只有一個入口**。操作盤點段列出四個操作：配對、連線、輪替、啟停。首頁應該是這四個操作的導航 hub，至少要有「配對」和「連線」兩個入口（輪替和啟停是主機端操作，不需要 app 入口）。只放 Connect Terminal 等於假設「使用者已經配對過」。

2. **路由存在但 UI 不可達 = 死程式碼的 UX 版本**。`/enrollment` 路由在 router 裡定義了，`EnrollmentScreen` 也完整實作了，但使用者從 UI 無法觸及。這跟寫了函式但沒有呼叫者一樣 — 功能正確但不可存取。

3. **`go` vs `push` 的語意差異影響 UX**。W2 修復用 `context.push('/enrollment')` 而非 `context.go('/enrollment')` — `push` 保留返回堆疊讓使用者配對後按 back 回首頁；`go` 替換整個路由堆疊、沒有 back。這個決策影響使用者的導航體驗，但也是事後才想到的。

## 策略

1. **導航流從操作盤點反推**：每個 UC（用例）的主入口在哪？首頁應該是哪些 UC 的 hub？列出來，確認每個 UC 至少有一條從首頁可達的路徑。
2. **路由可達性檢查**：router 定義的每個路由都應該從 UI 可達。不可達的路由要嘛是遺漏入口（本案例），要嘛是應該刪除的死路由。可以寫一個 lint 檢查。
3. **首次 vs 日常使用者的 UX 區分**：首次使用者需要 onboarding 流程（配對 → 連線），日常使用者只需要連線。兩種入口都要在首頁可見，但可以用視覺層級區分主要/次要。

## 下一步路由

- 想設計完整導航流 → [模組五：導航模式](/ux-design/05-navigation-patterns/)
- 想檢查畫面狀態矩陣的退出路徑 → [U.C1 五狀態零退出](/ux-design/cases/five-states-zero-exits/)
- 想做路由可達性自動化檢查 → 待補：Flutter GoRouter 路由可達性 lint
