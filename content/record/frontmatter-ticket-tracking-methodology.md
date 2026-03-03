---
title: "Frontmatter 式 Ticket 追蹤方法論 - 結構化任務狀態管理"
date: 2026-03-04
draft: false
description: "使用 YAML Frontmatter 作為 Ticket 狀態的唯一 Source of Truth，實現可解析、可自動化的任務追蹤"
tags: ["Frontmatter", "Ticket追蹤", "YAML", "任務管理", "自動化"]
---

在多代理人協作開發流程中，我們長期被一個問題困擾：主線程怎麼知道各代理人的執行進度？

起初讓代理人完成後回報，但每次回報都消耗 context 空間，狀態散落在對話歷史裡，根本無法可靠查詢。

後來試過 CSV 追蹤表，但 Ticket 設計文件在一個地方、狀態在另一個地方，兩者很容易出現不一致。

最終答案：把狀態放進 Ticket 文件本身的 YAML Frontmatter 裡。

<!--more-->

## 狀態與內容為什麼要分離？

一個 Ticket 天然包含兩種資訊：「要做什麼」和「做到哪裡了」。傳統做法把它們放在不同地方，製造了一個持續的維護負擔——查狀態要看兩個地方，兩個地方隨時可能不一致。

Markdown 的 YAML frontmatter 本來就是機器可解析的結構化資料，直接把狀態放進去，Ticket 就成了自給自足的單元：frontmatter 存設計決策和當前狀態，body 存執行日誌。

## 核心設計原則

### Frontmatter 是唯一的狀態來源

主線程查進度時直接讀 frontmatter，不需要問代理人。代理人更新狀態時直接改 frontmatter，不需要回報主線程。兩端獨立操作，不需要等彼此。

### 單一文件原則

每個 Ticket 只有一個文件：frontmatter 放識別資訊、5W1H 設計、驗收條件、依賴關係和當前狀態；body 放執行日誌。一個文件說清楚一切。

### 查詢輸出最小化

`summary` 產出緊湊的一行式列表，`query` 只回傳單一 Ticket 的精簡資訊。查詢不應消耗 context，只應提供答案。

## Frontmatter 的欄位設計

**識別資訊**：`ticket_id`、`version`、`wave`，確保每個 Ticket 有唯一且可解析的身份。

**單一職責定義**：`action`（有限動詞：Implement、Fix、Add、Refactor、Remove、Update）加 `target`（操作對象）。強制「動詞 + 單一目標」的格式，防止一個 Ticket 偷渡多個責任。

**5W1H 設計**：六個欄位確保 Ticket 在建立時就已經回答了誰來做、做什麼、什麼時機、在哪裡改、為什麼要做、怎麼做。

**驗收條件**：`acceptance` 列表，每個條目完成後勾選。「完成」的定義在建立時就講清楚，不留到最後才爭。

**狀態追蹤**：`status`（pending、in_progress、completed）、`assigned`（布林值）、`started_at`、`completed_at`。

## 操作流程

- `ticket create`：生成帶完整 frontmatter 的 Markdown 文件，初始狀態 `pending`、`assigned: false`
- `ticket track claim`：`status` 改為 `in_progress`、`assigned: true`、記錄 `started_at`
- `ticket track complete`：`status` 改為 `completed`、記錄 `completed_at`
- `ticket track release`：Ticket 退回 `pending`，可由其他人接手
- `ticket track summary`：輸出所有 Ticket 的緊湊一覽，幾秒掌握版本進度

## 與文件系統的整合

Ticket 是整個文件系統的最底層：CHANGELOG 的素材從 Ticket 記錄提取，版本收尾時從 Ticket 狀態確認所有任務完成。上面還有 worklog（版本目標）和 todolist（版本索引），各層各司其職，形成可追蹤的鏈條。

## 向後相容策略

遷移前已有一批 CSV 格式的舊 Ticket。策略是「新格式完整支援，舊格式唯讀查詢」：工具自動偵測，有 `tickets/` 目錄就用新格式，只有 `tickets.csv` 就唯讀讀取。舊版本的 `summary` 和 `list` 仍可運作，只是不能執行狀態變更。不需要一次性轉換所有歷史記錄。

## 實踐中的行為規範

主線程不應該問代理人「你做完了嗎」。執行查詢命令，讀 frontmatter。

代理人完成後，詳細說明寫進 Ticket body（問題分析、解決方案、測試結果），不要輸出給主線程。主線程只需要知道一件事：Ticket 是否已完成。

執行日誌要記完整——不只是最終結果，還有過程中遇到的問題、嘗試的方案、最終選擇的原因。這讓 Ticket 成為可供日後回顧的執行記錄，而不只是一個狀態標記。

## 本質上解決的問題

主線程不需要「知道」進度，它只需要「查詢」。狀態是持久化的、機器可讀的、時刻最新的。

這把進度追蹤從「溝通問題」變成了「查詢問題」。溝通依賴時機、依賴雙方都在場；查詢只依賴資料存在和工具可靠。從 CSV 到 Frontmatter，本質是從「狀態需要溝通」到「狀態需要持久化」的思維轉換。
