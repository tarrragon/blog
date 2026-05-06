---
title: "Incident Severity"
tags: ["事故等級", "Incident Severity"]
date: 2026-04-23
description: "說明事故分級如何把產品影響轉成對應處置節奏"
weight: 150
---


Incident severity 的核心概念是「用一致標準把事故影響分級」。分級不是描述技術細節，而是描述產品影響範圍、持續時間、資料風險與回復緊急程度。 可先對照 [Alert](/backend/knowledge-cards/alert/)。

## 概念位置

Incident severity 連接 [alert](/backend/knowledge-cards/alert/)、[runbook](/backend/knowledge-cards/runbook/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/)。同一類技術錯誤在不同業務場景可能有不同等級，因此分級要以產品後果為主。

## 可觀察訊號與例子

系統需要分級模型的訊號是事件發生後團隊對嚴重度判斷不一致。付款成功率下降與單一內部報表延遲都可能由 timeout 引起，但前者需要立即啟動高優先級處置，後者通常走一般排程修復。

## 設計責任

分級要定義等級條件、升級門檻、負責角色、通訊頻率與回顧要求。等級規則應定期和事故紀錄對照，避免長期失真。
