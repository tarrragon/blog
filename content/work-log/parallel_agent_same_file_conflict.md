---
title: "並行 AI Agent 修改同一檔案的衝突模式與協調策略"
date: 2026-06-25
draft: false
description: "並行派多個開發者或 AI agent 同一批 ticket，反覆修改同一個檔案、卡在 branch protection 與 file-modified-since-read。問題在派發策略沒考慮檔案層級的衝突。"
tags: ["ai-agent", "parallel-dispatch", "git", "conflict-resolution", "retrospective"]
---

## 事件

多人（或多 agent）並行開發時，如果修改集中在同一個檔案，協調成本可能抵消並行的收益。以下是一個具體案例。

v0.3.0 的 JS SDK 開發中，五張 ticket 被並行派發給五個 AI agent：flush 邏輯、離線容錯、自動攔截、頁面生命週期、rate limiting。前四個都需要修改同一個檔案 `monitor.ts`。

結果：

- 三個 agent 回報 branch protection hook 阻擋 src 編輯
- 兩個 agent 回報 `file modified since read` 拒絕 Edit（另一個 agent 正在寫同一檔案）
- PM 花了多個回合協調 commit 策略：「你先 commit」「你等他完成」「你只 git add 你的檔案」
- 最終 PM 手動合併所有 agent 的變更，做了一個統一 commit

並行派發的目標是縮短總工時。但五個 agent 改同一檔案時，協調成本抵消了並行的收益。

## 根因：派發粒度錯在 ticket 層而非檔案層

派發決策看的是 ticket 的獨立性——五張 ticket 描述的功能確實獨立（flush、離線、攔截、生命週期各自有清楚的邊界）。但獨立的功能不等於獨立的檔案。五個功能的修改都集中在 `monitor.ts` 這一個檔案上。

ticket 獨立 =/= 檔案獨立。並行安全的判斷基準應該是後者。

## 教訓

**派發前掃描 `where.files`**：如果多張 ticket 的目標檔案有交集，序列化派發。前一張完成並 commit 後，再派下一張。

**序列的代價比衝突的代價低**：五個 agent 序列執行可能需要 5 倍時間，但每個 agent 在乾淨的工作區上操作，不需要協調。五個 agent 並行但衝突，PM 的協調時間加上 agent 的等待和重試，總成本可能更高。

**Worktree 隔離不是萬靈丹**：git worktree 讓每個 agent 有獨立的工作目錄，避免 working tree 衝突。但如果兩個 agent 修改同一檔案的不同區段，merge 時仍需人工判斷。Worktree 解決的是「同時寫同一個 working tree」的問題，不解決「同時改同一個檔案的語意衝突」。

## 適用場景

這個 pattern 不限於 AI agent。人類開發者在同一個 Sprint 中被分配修改同一個檔案的不同功能時，也會遇到 merge conflict。差異在於人類可以口頭協調（「我先改完你再改」），agent 目前缺乏這個即時溝通管道。派發者（PM 或 CI 系統）需要在派發時就做好檔案衝突預判。
