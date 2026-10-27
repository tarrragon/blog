---
title: "模組七：突發流量應對"
date: 2026-06-20
description: "行銷活動、新聞曝光或 error storm 讓送進 collector 的事件量暴增時：突發分類、降級策略、queue 緩衝、規模分級應對"
weight: 7
tags: ["devops", "burst-traffic", "degradation", "queue", "scaling"]
aliases: ["/operations/07-burst-traffic/"]
---

處理流量突然暴增時，collector 怎麼維持接收與不遺失資料。突發流量和穩定高流量的處理策略不同：突發有時間限制，而突發過後服務不一定會自己恢復（重試與積壓可能讓過載延續，見 [Metastable Failure](/backend/knowledge-cards/metastable-failure/)）。

## 章節

| 章節                                                                        | 回答什麼問題                                                   |
| --------------------------------------------------------------------------- | -------------------------------------------------------------- |
| [突發流量的分類](/devops/operations/07-burst-traffic/burst-classification/) | 可預期 vs 不可預期、持續時間和倍率、活動前的準備項目與前置時間 |
| [降級策略](/devops/operations/07-burst-traffic/degradation-strategy/)       | 動態取樣、事件優先級、功能降級、聚合前移                       |
| [Queue 緩衝](/devops/operations/07-burst-traffic/queue-buffering/)          | Kafka / NATS / Redis Streams 做 burst buffer                   |
| [規模分級應對表](/devops/operations/07-burst-traffic/scale-tier-response/)  | 自用 → 中型 → 大型 → 商業網站                                  |

## 跨分類引用

- ← [運維 模組三 流量管控](/devops/operations/03-traffic-management/)：背壓和 rate limit 是突發應對的基礎元件
- → [monitoring 模組四 Collector](/devops/monitoring/04-collector/)：Collector 的 ingestion scaling 是本模組的應用場景
- → [backend 非同步佇列](/backend/03-message-queue/)：Queue 的選型和操作實務
- → [運維 模組五 容量規劃](/devops/operations/05-capacity-planning/)：預期突發的容量預備
- → [端到端資料完整性](/devops/monitoring/04-collector/data-integrity/)：被自己 SDK DDoS 的三種場景

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                                                                                                                                                                                                                    | 類型 | 前置條件                                                                               | 規模 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------- | ---- |
| 〈降級策略〉動態取樣的觸發條件只有 collector 回 429 的次數與持續時間，429 在接收佇列滿了才出現、位置在膝點之後；9.11〈T-90 → T-0 準備時程〉的降級門檻從壓測的膝點推出、設在目標利用率對應的處理量。補一列以寫入延遲或接收速率為訊號、門檻取自壓測的觸發條件，429 那一列改成第二道，並寫出 N、M 從哪裡量 | 主章 | 無；inbound：〈突發流量的分類〉〈容量預備的前置時間與 collector 在活動前要準備的項目〉 | 小   |
