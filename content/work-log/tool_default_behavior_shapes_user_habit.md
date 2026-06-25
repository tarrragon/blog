---
title: "工具的預設行為決定使用者習慣 — 從版本錯置事件看 CLI 設計的 opinion 責任"
date: 2026-06-25
draft: false
description: "ticket create 不引導版本歸屬，使用者直覺用當前 active 大版本，導致改善類 ticket 錯放。version-release 不檢查前版本 status，舊版本 active 殘留。兩者都是工具沒有 opinion 的後果。好的工具應該有 opinion 並在預設行為中引導正確做法。"
tags: ["process", "cli-design", "version-management", "tool-design", "retrospective"]
---

> **觸發場景**：v0.3.0 版本檢討時建立的 reset 根因分析（ANA）和 State Registry 重構（IMP）ticket 被放進 v0.4.0（PostgreSQL scope），事後需手動遷移到 v0.3.2
> **第二觸發**：`ticket track board` 顯示 v0.2.0 有未完成任務，查證後發現 v0.2.0/0.2.1/0.2.2 三個已完成版本的 todolist status 仍為 active
> **整理目的**：記錄「工具的預設行為如何形塑使用者（含 AI agent）的決策慣性」這個 pattern
> **本文邊界**：這是一篇檢討卡片，聚焦於 CLI 工具設計的 opinion 責任，不涉及版本策略本身的對錯

---

## 事件一：改善類 ticket 錯放大版本

### 發生了什麼

v0.3.0 的 JS SDK 開發過程中，`__reset()` 方法漏重置 `retryCount`/`flushing`/`lastHeartbeat` 三個 private 欄位，導致跨 test case 狀態洩漏。v0.3.1 做了 hotfix 後，需要深入分析根因並建立系統性防護。

建立分析 ticket 時，`ticket create --version 0.4.0` 直接指定了下一個大版本。原因很直覺——v0.3.0 和 v0.3.1 都已發布，v0.4.0 是當前 active 的版本，CLI 也沒有提示「這個 ticket 的性質不適合放在大版本」。

結果：reset 根因分析（ANA）、State Registry 重構（IMP）、quality-common 規則更新（DOC）三張 ticket 全部放進 v0.4.0，和 PostgreSQL Storage Backend 混在一起。事後用戶發現錯置，需要建立 v0.3.2、遷移三張 ticket、重新發布。

### 為什麼會這樣

根本原因不是「使用者判斷錯誤」，而是**工具沒有提供判斷依據**。

`ticket create` 接受 `--version` 參數時，只做格式驗證（版本號是否存在於 todolist），不分析需求類型與版本 scope 的匹配度。對工具來說，把 bug fix 放進 v0.4.0 和把新功能放進 v0.4.0 沒有區別——兩者都是「合法操作」。

但從版本語意來看，這是兩件完全不同的事：

| 需求類型         | 版本語意         | 應歸屬 |
| ---------------- | ---------------- | ------ |
| 新功能（feat）   | minor/major bump | v0.4.0 |
| 修復（fix）      | patch bump       | v0.3.x |
| 改善（improve）  | patch bump       | v0.3.x |
| 重構（refactor） | patch bump       | v0.3.x |
| 文件（docs）     | patch bump       | v0.3.x |

工具不表達 opinion，使用者（尤其是 AI agent，傾向選擇當前 active 的最大版本）用直覺決定，版本錯置。

## 事件二：已完成版本 status 殘留

### 發生了什麼

`ticket track board` 顯示 v0.2.0 有未完成任務。查證後發現 v0.2.0（38/38 完成）、v0.2.1（7/7 完成）、v0.2.2 三個版本在 todolist.yaml 中仍標記為 `status: active`。

### 為什麼會這樣

v0.2.x 時期的版本發布可能是手動操作或早期 CLI 版本，未觸發 todolist status 同步。而 `version-release check` 的 pre-flight 檢查只看「當前版本的 ticket 是否完成」，不掃描「前版本是否遺留 active status」。

結果：已完成版本在系統中看起來像未完成，board 顯示混亂，新使用者（或新 session）看到 v0.2.0 未完成會困惑。

## 共通 pattern：工具沒有 opinion 的後果

兩個事件的共通根因是**工具在應該有 opinion 的地方保持沉默**。

### 什麼時候工具應該有 opinion？

當存在一個「多數情況下正確的預設行為」時，工具應該把它表達出來。使用者可以覆蓋，但預設路徑應該引導正確做法。

| 場景                  | 工具應有的 opinion                                  | 實際行為                     |
| --------------------- | --------------------------------------------------- | ---------------------------- |
| 建 fix/improve ticket | 「建議放 v0.3.x+1（patch bump）」                   | 無引導，接受任何 active 版本 |
| 發布版本後            | 「前版本 v0.2.x 仍為 active，是否標記 completed？」 | 只更新當前版本 status        |
| board 顯示            | 「v0.2.0 所有 ticket 已完成但 status 為 active」    | 靜默顯示為未完成             |

### Convention over Configuration

Rails 的「Convention over Configuration」原則在這裡完全適用：工具應該用約定（convention）引導使用者走正確路徑，而不是提供無限彈性讓使用者自己判斷。

「無 opinion 的工具」看起來更靈活，但實際上把判斷成本轉嫁給每次使用的人。當使用者是 AI agent 時，這個問題更嚴重——agent 沒有跨 session 記憶，每次都會用最直覺的路徑（當前 active 最大版本）。

## 改善方向

### ticket create 版本歸屬引導

CLI 在 `--version` 未指定時，根據 ticket type + action 建議版本：

```
$ ticket create --type IMP --action "修復" --target "retry test"
[建議] 此 ticket 為修復類（fix），建議放 v0.3.2（當前最新 patch）
       而非 v0.4.0（下一個 feature 版本）
       使用 --version 0.3.2 或 --version 0.4.0 覆蓋
```

### version-release check 前版本掃描

pre-flight check 加入「前版本 active 殘留偵測」：

```
$ version-release check
[WARN] v0.2.0 所有 38 ticket 已完成但 status 仍為 active
[WARN] v0.2.1 所有 7 ticket 已完成但 status 仍為 active
       建議執行: version-release cleanup-stale
```

### 設計原則提煉

> **工具的預設行為，就是團隊的實際流程。**
>
> 文件上寫的流程，和工具預設引導的流程不一致時，工具會贏。因為使用者（和 AI agent）走的是阻力最小的路徑，而阻力最小的路徑就是工具的預設行為。
>
> 所以：如果你希望使用者做 X，不要寫文件說「請做 X」——把工具的預設行為設成 X。

---

## 追蹤

| Ticket       | 內容                           | 版本   |
| ------------ | ------------------------------ | ------ |
| 0.3.3-W1-001 | ticket create 版本歸屬引導機制 | v0.3.3 |
| 0.3.3-W1-002 | 版本發布檢查遺漏根因分析       | v0.3.3 |
