---
title: "Ownership"
date: 2026-06-22
description: "說明 ownership 如何把問題、決策與交接責任固定到可執行角色"
weight: 209
tags: ["backend", "observability", "incident-response"]
---

Ownership 的核心概念是「把責任固定到可執行角色」。它讓團隊在事件、變更與回寫流程中能快速判斷誰主責、誰協作、誰做決策，是 [on-call](/backend/knowledge-cards/on-call/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/) 運作的前提。

## 跟其他概念的關係

Ownership 連接 [alert](/backend/knowledge-cards/alert/)（每個 alert rule 需要 owner）、[dashboard](/backend/knowledge-cards/dashboard/)（每個 dashboard 需要維護者）、[runbook](/backend/knowledge-cards/runbook/)（runbook 的更新責任跟服務 owner 一致）、[incident severity](/backend/knowledge-cards/incident-severity/) 跟 [escalation policy](/backend/knowledge-cards/escalation-policy/)。

在觀測系統中，沒有 owner 的 alert 跟 dashboard 會隨服務演進退化 — alert 變成 noise、dashboard 變成裝飾。[4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/) 的定期審視需要每個訊號都有明確 owner。[4.18 operating model](/backend/04-observability/observability-operating-model/) 定義 ownership 矩陣。

## 使用情境

系統需要 ownership 的訊號是同一事件在不同角色之間反覆轉手、或 alert 觸發後沒人知道該誰處理。Owner 離職但 alert / dashboard / runbook 沒有交接是常見的退化模式。

## 判斷條件與後果

Ownership 是否完整，看一個訊號或服務出事時，查不查得出誰主責、誰協作、往哪裡升級、誰負責關閉。只定了主責角色時，事件需要另一個團隊協作或升級就沒有路由，同一事件在角色之間反覆轉手；沒有關閉責任時，事件處理完之後，行動項與 runbook 的更新沒有人確認。Owner 離職或轉組而沒有交接時，他名下的 alert 與 dashboard 失去 owner，隨服務演進退化成 noise 與裝飾，而這個狀態本身不會觸發任何告警，所以要靠定期掃描 orphan alert 與 dashboard 才找得到。服務邊界調整時（新服務上線、服務合併），既有的 ownership 對的是舊邊界：新服務的訊號可能沒有 owner，合併後的服務可能有兩個 owner，因此邊界調整的同時要重新對一次 ownership。
