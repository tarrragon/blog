---
title: "Spotify：平台工程與可靠性契約"
date: 2026-05-07
description: "用平台契約統一服務團隊的可靠性最低標準，降低跨團隊變更造成的隱性風險。"
weight: 71
---

Spotify 案例的核心責任是把可靠性標準平台化。當團隊自治程度高，若沒有共同契約，跨服務風險會在整合時爆發。

## 問題場景

不同團隊採用不同部署與觀測習慣，單隊看似穩定，但跨服務路徑會出現隱性斷點，導致事故時難以協同定位。

## 決策機制

| 機制                  | 核心問題               | 交付結果 |
| --------------------- | ---------------------- | -------- |
| Reliability contract  | 每個服務最低要提供什麼 | 基線能力 |
| Platform self-service | 標準如何降低導入成本   | 擴散能力 |
| Cross-team evidence   | 證據如何跨團隊共享     | 協作效率 |

## 可觀測訊號

| 訊號                                | 判讀重點               | 對應章節                                                       |
| ----------------------------------- | ---------------------- | -------------------------------------------------------------- |
| contract compliance rate            | 契約覆蓋是否足夠       | [6.10](/backend/06-reliability/contract-testing/)              |
| release dependency failures         | 依賴變更是否常破壞發布 | [6.14](/backend/06-reliability/dependency-reliability-budget/) |
| cross-team incident handoff latency | 交接是否有共同語言     | [8.2](/backend/08-incident-response/incident-command-roles/)   |

## 下一步路由

先補 [6.10](/backend/06-reliability/contract-testing/) 的契約欄位，再以 [4.18](/backend/04-observability/observability-operating-model/) 對齊 owner 與責任邊界。
