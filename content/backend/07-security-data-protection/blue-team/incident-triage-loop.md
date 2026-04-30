---
title: "7.B6 Incident Triage Loop"
tags: ["Blue Team", "Incident Response", "Triage", "Severity"]
date: 2026-04-30
description: "把資安訊號轉成 triage、severity、owner、containment 與 evidence 的回應循環"
weight: 726
---

本篇的責任是建立 incident triage loop。讀者讀完後，能把 alert 與外部通報轉成分級、接手、處置與回寫循環。

## 核心論點

Incident triage loop 的核心概念是讓訊號推動一致決策。循環一旦固定，團隊在壓力下仍能用同一組欄位完成判讀與交接。

## 讀者入口

本篇適合銜接 [7.B2 從偵測到回應的路由](/backend/07-security-data-protection/blue-team/detection-to-response-routing/)、[7.B5 Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/) 與 [incident severity](/backend/knowledge-cards/incident-severity/)。

## Triage 循環欄位

| 欄位               | 責任               | 產出               |
| ------------------ | ------------------ | ------------------ |
| Signal intake      | 收斂初始訊號與來源 | alert record       |
| Triage question    | 建立第一輪判讀問題 | triage note        |
| Severity decision  | 對齊影響等級與節奏 | severity decision  |
| Owner assignment   | 明確主責與協作角色 | owner route        |
| Containment action | 控制影響面與擴散   | containment record |
| Evidence capture   | 保留回查證據       | evidence chain     |
| Write-back         | 回寫規則與流程     | backlog item       |

## Triage 問題設計

Triage 問題設計的責任是讓判讀聚焦。每次事件可先回答四題：

1. 目前影響面在哪些服務邊界。
2. 訊號可信度與誤報機率在哪個範圍。
3. 哪個 [ownership](/backend/knowledge-cards/ownership/) 可以先收斂風險。
4. 這輪事件的關閉條件是什麼。

## Severity 對齊

Severity 對齊的責任是把技術判讀接到業務影響。分級決策可直接綁定升級節奏、通訊節奏與處置時限，並和 [escalation policy](/backend/knowledge-cards/escalation-policy/) 對齊。

## Containment 與 Evidence

Containment 與 evidence 的責任是讓事件處置可驗證。處置動作與證據保留同步進行，常見證據包含 audit log、變更紀錄、時間線與決策紀錄。

## 回寫閉環

回寫閉環的責任是讓每次 triage 提升下次效率。建議回寫到三個位置：

1. detection rule 與 tuning 記錄。
2. runbook 與 escalation path。
3. 7.x 章節中的判讀訊號與路由。

## 判讀訊號與路由

| 判讀訊號                   | 代表需求                | 下一步路由  |
| -------------------------- | ----------------------- | ----------- |
| 分級標準頻繁改寫           | 需要固定 severity 準則  | 7.B6 → 08   |
| triage 記錄缺少影響邊界    | 需要補 triage 問題模板  | 7.B6 → 7.B2 |
| containment 完成但證據不足 | 需要補 evidence capture | 7.B6 → 7.B3 |
| 事件結束後規則未更新       | 需要 write-back 閉環    | 7.B6 → 7.B5 |

## 必連章節

- [7.B2 從偵測到回應的路由](/backend/07-security-data-protection/blue-team/detection-to-response-routing/)
- [7.B3 資安控制驗證](/backend/07-security-data-protection/blue-team/security-control-validation/)
- [7.B5 Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- [7.24 資安事故如何回寫產品與架構](/backend/07-security-data-protection/security-incident-write-back-to-product-and-architecture/)

## 完稿判準

完稿時要讓讀者能把一個 incident 訊號走完 triage loop。輸出至少包含訊號、問題、分級、接手、處置、證據與回寫。
