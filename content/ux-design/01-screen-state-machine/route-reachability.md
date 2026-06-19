---
title: "路由可達性檢查"
date: 2026-06-19
description: "Router 定義的路由 vs UI 實際可達的路由 — 路由存在但 UI 不可達等於死程式碼的 UX 版本"
weight: 3
tags: ["ux-design", "navigation", "routing", "dead-code", "reachability"]
---

路由可達性檢查比較兩個集合：router 定義的所有路由，和使用者從 UI 操作能到達的所有路由。兩個集合的差集就是問題所在 — 定義了但不可達的路由是入口缺失，可達但未定義的路由是 404 風險。

## 定義 vs 可達

### Router 定義的路由

現代前端框架（Flutter GoRouter、React Router、Vue Router）通常有一個集中的路由定義檔，列出所有可存取的路徑和對應的畫面元件。這個列表是 router 認知的「所有畫面」。

### UI 可達的路由

從首頁（或 app 的入口畫面）開始，透過 UI 上的按鈕、連結、手勢能到達的所有路由。這個集合代表使用者實際能存取的畫面。

### 差集分析

**router 有但 UI 不可達**：路由定義了、畫面元件也實作了，但沒有任何 UI 元素導航到這個路由。功能存在但使用者找不到入口。

**UI 指向但 router 沒有**：UI 上有一個按鈕 `navigateTo('/settings')`，但 router 沒有定義 `/settings` 路由。使用者點擊後會看到 404 或空白畫面。

## 路由存在但不可達的案例

app_tunnel 的 router 定義了三條路由：`/`（首頁）、`/enrollment`（配對）、`/terminal`（終端機）。首頁只有一個 Connect Terminal 按鈕導航到 `/terminal`。`/enrollment` 路由存在，`EnrollmentScreen` 完整實作，但首頁沒有任何 UI 元素導航到這個路由（[U.C4](/ux-design/cases/missing-enrollment-entry-point/)）。

從使用者視角看，配對功能不存在。從開發者視角看，配對功能完整 — 路由定義了、畫面寫好了、業務邏輯都通了。問題出在「入口」這個連接層。

這和程式碼裡寫了一個 function 但沒有任何地方呼叫它的情況結構相同。Function 本身可能正確無誤，但從系統角度看是死程式碼。路由可達性檢查是這個問題在 UX 層的對應。

## 檢查方法

### 手動檢查

列出 router 定義的所有路由，然後逐一在 UI 上找到通往該路由的操作路徑。找不到路徑的就是不可達路由。

手動檢查的成本隨畫面數量線性增長。5 個路由的 app 很快能查完；50 個路由的 app 需要系統化方法。

### 從操作盤點交叉比對

BDD 操作盤點列出了所有使用者操作（UC）。每個 UC 對應至少一個畫面。把 UC 清單和 router 定義對照：

- 每個 UC 的主要入口畫面是否有從首頁可達的路徑？
- 每個 UC 涉及的中間畫面是否都有進入和退出路徑？

app_tunnel 的操作盤點列了四個操作（配對、連線、輪替、啟停），首頁只提供了「連線」的入口。「配對」是 app 操作，應該有入口但沒有。「輪替」和「啟停」是主機端操作，不需要 app 入口。這個交叉比對能在 5 分鐘內揭露入口缺失。

### 自動化檢查

從 router 定義檔解析所有路由路徑，再從 UI 元件的程式碼中搜尋所有 `navigateTo`、`context.go`、`context.push`、`router.push` 等導航呼叫的目標路徑。兩個集合取差集。

自動化檢查能發現靜態定義的入口缺失，但無法發現動態導航（根據執行期條件決定目標路由）的可達性問題。

## `go` vs `push` 的語意影響

路由可達性確認之後，導航方式的選擇影響使用者的返回路徑。

`push` 把新畫面推入導航堆疊，使用者按 back 能回到前一個畫面。`go` 替換整個導航堆疊，使用者按 back 不會回到原來的畫面。

選擇 `go` 還是 `push` 取決於使用者的心理模型：這個導航是「暫時離開主畫面去做一件事，做完回來」（push），還是「切換到另一個主要工作區」（go）。

app_tunnel 修復時選擇 `context.push('/enrollment')` 讓使用者配對完成後按 back 回首頁 — 配對是「暫時去做一件事」，不是切換工作區（[U.C4](/ux-design/cases/missing-enrollment-entry-point/)）。

## 下一步路由

- 畫面狀態矩陣完整定義 → [畫面狀態矩陣的定義與填寫方法](/ux-design/01-screen-state-machine/state-matrix-definition/)
- 想測試導航路徑的正確性 → [testing 模組四 UI 自動化](/testing/04-ui-automation/)
- 想設計完整導航模式 → [ux-design 模組五 導航模式](/ux-design/05-navigation-patterns/)
