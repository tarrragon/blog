---
title: "go vs push vs pushReplacement 的 UX 語意表"
date: 2026-06-19
description: "三種導航方法對堆疊、back 行為、使用者心理模型的影響 — 選擇依據是使用者的意圖而非技術方便"
weight: 5
tags: ["ux-design", "navigation", "flutter", "gorouter", "push", "go", "semantics"]
---

`go`、`push`、`pushReplacement` 三種導航方法改變導航堆疊的方式不同，直接影響使用者按 back 時的行為。選擇哪種方法的依據是使用者的操作意圖 — 使用者期望按 back 時回到哪裡。

## 語意對照表

| 方法              | 堆疊行為     | 按 back 回到   | 使用者意圖                 |
| ----------------- | ------------ | -------------- | -------------------------- |
| `go(path)`        | 替換整個堆疊 | 無（離開 app） | 切換到另一個工作區         |
| `push(path)`      | 推入堆疊頂端 | 前一個畫面     | 暫時離開，做完回來         |
| `pushReplacement` | 替換堆疊頂端 | 更早的畫面     | 流程中的下一步（不可回退） |

## go：切換工作區

`go` 把整個導航堆疊替換成新的路徑。使用者按 back 不會回到操作前的畫面，因為堆疊已經被替換。

適合場景：

- 登入成功後到首頁（使用者不應該按 back 回到登入畫面）
- 登出後到登入畫面（使用者不應該按 back 回到需要認證的畫面）
- 從 onboarding 到主畫面（onboarding 完成後不需要回去）

誤用 `go` 的後果：使用者期望按 back 回到前一個畫面但堆疊已空，按 back 直接離開 app。一個遠端終端機 app 補配對畫面入口時選擇 `push('/enrollment')` 而非 `go('/enrollment')`，讓使用者配對完成後能按 back 回首頁（[U.C4](/ux-design/cases/missing-enrollment-entry-point/)）。

## push：暫時離開，做完回來

`push` 在堆疊頂端加入新畫面。使用者按 back 回到前一個畫面。

適合場景：

- 從列表到詳細頁（看完回到列表）
- 從首頁到配對畫面（配對完回首頁）
- 從任何畫面到設定頁（改完設定回原畫面）

`push` 是最常用的導航方法，因為多數導航都是「暫時去另一個畫面做事，做完回來」的模式。

## pushReplacement：流程中前進

`pushReplacement` 用新畫面替換堆疊頂端。堆疊深度不變，按 back 回到替換前畫面的前一個畫面（跳過被替換的畫面）。

適合場景：

- 步驟式流程：步驟 1 → pushReplacement 步驟 2 → pushReplacement 步驟 3。使用者在步驟 3 按 back 回到流程開始前的畫面，不會回到步驟 2 或 1。
- 結果頁替換搜尋頁：搜尋結果替換搜尋條件頁，使用者按 back 回到搜尋前的畫面。

pushReplacement 的語意是「這一步完成後使用者不需要回到這裡」。用於不可回退的流程步驟。

## 選擇決策流程

對每個導航操作問一個問題：**使用者按 back 時，期望回到哪裡？**

- 回到前一個畫面 → `push`
- 離開 app 或回到 app 的根畫面 → `go`
- 跳過當前畫面，回到更早的畫面 → `pushReplacement`

這個決策應該在 UX 設計階段做，記錄在畫面狀態矩陣的「退出路徑」欄中。開發者實作時對照矩陣選擇正確的導航方法。

## 常見誤用

### 用 go 做應該用 push 的導航

「首頁 → 配對畫面」如果用 `go`，使用者配對完成後按 back 離開 app 而非回到首頁。使用者期望的是「配對完成回首頁」（push 行為）。

### 用 push 做應該用 go 的導航

「登入 → 首頁」如果用 `push`，使用者在首頁按 back 回到登入畫面。使用者已經登入，不應該看到登入畫面。

### 用 push 做應該用 pushReplacement 的導航

步驟式流程中「步驟 1 → 步驟 2」如果用 `push`，使用者在步驟 2 按 back 回到步驟 1。如果步驟 1 的操作不可逆（已經提交了資料），回到步驟 1 沒有意義。

## 下一步路由

- Flutter GoRouter 的完整導航 API → [Flutter GoRouter 導航設計](/ux-design/05-navigation-patterns/flutter-gorouter/)
- 導航模式分類 → [Mobile 導航模式分類](/ux-design/05-navigation-patterns/mobile-navigation-taxonomy/)
- 路由可達性檢查 → [ux-design 模組一 路由可達性](/ux-design/01-screen-state-machine/route-reachability/)
- 導航路徑的自動化測試 → [testing 模組四 自動化 UI 驗證](/testing/04-ui-automation/)
