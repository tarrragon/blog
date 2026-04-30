---
title: "Ownership"
tags: ["責任歸屬", "Ownership"]
date: 2026-04-30
description: "說明 ownership 如何把問題、決策與交接責任固定到可執行角色"
weight: 208
---

Ownership 的核心概念是「把責任固定到可執行角色」。它讓團隊在事件、變更與回寫流程中能快速判斷誰主責、誰協作、誰做決策，並和 [runbook](/backend/knowledge-cards/runbook/) 的操作節奏保持一致。

## 概念位置

Ownership 連接 [incident severity](/backend/knowledge-cards/incident-severity/)、[runbook](/backend/knowledge-cards/runbook/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/)。分級與流程可以定義處置節奏，ownership 負責把節奏落到角色交接。

## 可觀察訊號與例子

系統需要 ownership 的訊號是同一事件在不同角色之間反覆轉手。值班告警進入 triage 後，若主責角色、協作角色與決策角色沒有明確欄位，處置速度與證據品質都會下滑。

## 設計責任

Ownership 需要定義主責角色、協作角色、升級路由與關閉責任，並在事件結束後把責任履行結果回寫到 runbook 與工作流。每次流程更新都應同步檢查 ownership 是否仍與服務邊界對齊。
