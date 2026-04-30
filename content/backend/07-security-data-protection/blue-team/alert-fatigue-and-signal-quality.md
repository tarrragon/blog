---
title: "7.B10 Alert Fatigue and Signal Quality"
tags: ["Blue Team", "Alert Fatigue", "Signal Quality", "Detection"]
date: 2026-04-30
description: "建立告警疲勞治理方法，讓訊號品質、分級一致性與處置效率同步提升"
weight: 730
---

本篇的責任是建立 alert fatigue 治理方法。讀者讀完後，能把噪音告警轉成可分級、可交接、可調校的訊號集合。

## 核心論點

Alert fatigue 治理的核心概念是把告警品質當系統能力管理。判讀效率與決策一致性是主要目標，告警數量則作為輔助觀測指標。

## 讀者入口

本篇適合銜接 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、[7.B5 Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/) 與 [alert fatigue](/backend/knowledge-cards/alert-fatigue/)。

## 訊號品質欄位

| 欄位             | 責任               | 指標                   |
| ---------------- | ------------------ | ---------------------- |
| Precision        | 降低誤報密度       | false positive rate    |
| Recall           | 保持重要事件命中   | missed detection rate  |
| Context richness | 提供足夠判讀上下文 | triage completion rate |
| Routing quality  | 提供正確接手路由   | misrouting rate        |
| Actionability    | 提供可執行下一步   | response start time    |

## 告警分層

告警分層的責任是讓值班負載可控。分層可依風險與動作分成：

1. Informational：觀測型訊號。
2. Action-required：需值班處理。
3. Escalation-required：需跨團隊升級。

## 調校節奏

調校節奏的責任是讓告警品質持續改善。每輪調校至少記錄觸發條件、誤報來源、調整內容、影響範圍與回退條件。

## 與 triage loop 對齊

與 triage loop 對齊的責任是讓告警到回應保持一致。告警內容至少提供 signal source、impact hint、recommended owner 與下一步路由。

## 判讀訊號與路由

| 判讀訊號                     | 代表需求                     | 下一步路由   |
| ---------------------------- | ---------------------------- | ------------ |
| 值班人員持續手動排除同類告警 | 需要規則調校與分層           | 7.B10 → 7.B5 |
| 告警描述不足以支持分級       | 需要補 context 欄位          | 7.B10 → 7.B6 |
| 告警量下降但漏報上升         | 需要平衡 precision 與 recall | 7.B10 → 7.B7 |
| 告警調整缺少變更證據         | 需要補 release gate 記錄     | 7.B10 → 7.22 |

## 必連章節

- [7.B5 Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- [7.B6 Incident Triage Loop](/backend/07-security-data-protection/blue-team/incident-triage-loop/)
- [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- [7.22 資安風險如何進入 Release Gate](/backend/07-security-data-protection/security-risk-in-release-gate/)

## 完稿判準

完稿時要讓讀者能為告警系統建立品質治理循環。輸出至少包含品質欄位、分層策略、調校節奏、對齊路由與回寫位置。
