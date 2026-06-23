---
title: "Ownership"
date: 2026-06-22
description: "說明 ownership 如何把問題、決策與交接責任固定到可執行角色"
weight: 208
tags: ["backend", "observability", "incident-response"]
---

Ownership 的核心概念是「把責任固定到可執行角色」。它讓團隊在事件、變更與回寫流程中能快速判斷誰主責、誰協作、誰做決策，是 [on-call](/backend/knowledge-cards/on-call/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/) 運作的前提。

## 概念位置

Ownership 連接 [alert](/backend/knowledge-cards/alert/)（每個 alert rule 需要 owner）、[dashboard](/backend/knowledge-cards/dashboard/)（每個 dashboard 需要維護者）、[runbook](/backend/knowledge-cards/runbook/)（runbook 的更新責任跟服務 owner 一致）、[incident severity](/backend/knowledge-cards/incident-severity/) 跟 [escalation policy](/backend/knowledge-cards/escalation-policy/)。

在觀測系統中，沒有 owner 的 alert 跟 dashboard 會隨服務演進退化 — alert 變成 noise、dashboard 變成裝飾。[4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/) 的定期審視需要每個訊號都有明確 owner。[4.18 operating model](/backend/04-observability/observability-operating-model/) 定義 ownership 矩陣。

## 使用情境

系統需要 ownership 的訊號是同一事件在不同角色之間反覆轉手、或 alert 觸發後沒人知道該誰處理。Owner 離職但 alert / dashboard / runbook 沒有交接是常見的退化模式。

## 設計責任

Ownership 需要定義主責角色、協作角色、升級路由與關閉責任。Owner 變動時（離職、轉組）需要交接流程 — orphan alert / dashboard 的定期掃描是治理的一部分。每次服務邊界調整（新服務上線、服務合併）都應同步檢查 ownership 是否仍對齊。
