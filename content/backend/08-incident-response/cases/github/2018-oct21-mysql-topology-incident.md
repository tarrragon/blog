---
title: "GitHub 2018 Oct21 MySQL Topology Incident"
date: 2026-05-07
description: "2018-10-21 GitHub 因 network partition 觸發跨區資料庫拓撲異常的事故解析：資料一致性優先、fail-forward 決策與長時間恢復。"
weight: 1
tags: ["backend", "incident-response", "case-study", "github"]
---

2018 年 GitHub Oct21 事故的核心教訓是：跨區資料庫在 network partition 後，最困難的是如何在可用性與資料一致性之間做出可回放的決策，切換本身只是其中一步。

## 事故摘要

GitHub 在 2018-10-21 22:52 UTC 因例行網路設備維護引發 network partition，導致跨區 MySQL replication topology 進入異常狀態。應用層在切換後持續寫入新主站，形成跨區未對齊寫入，事故最終歷時約 24 小時 11 分鐘。

官方 post-incident analysis 指出，團隊選擇 fail-forward，而不是直接切回原主站，原因是要優先保護資料完整性，避免產生更大不一致。

## 判讀訊號

| 訊號                                | 事故中代表什麼                  | 第一波決策價值                              |
| ----------------------------------- | ------------------------------- | ------------------------------------------- |
| 多個服務同時顯示資料過舊或不一致    | replication topology 已跨區失衡 | 先凍結變更與部署，避免拓撲再變化            |
| Orchestrator 顯示非預期跨區主從關係 | 自動切換已進入複雜狀態          | 轉人工決策，先保資料一致性                  |
| webhook / Pages backlog 快速累積    | 控制面與資料面都受影響          | 將積壓處理納入恢復計畫，而非只看 API 健康度 |
| status 更新頻率下降                 | 指揮資訊與恢復節奏未對齊        | 補 decision log 與分階段狀態更新            |

## 事故路徑

1. 例行網路設備維護造成 East 與主資料中心連線中斷。
2. Orchestrator 在 partition 下進行主從重新選舉與切換。
3. 連線恢復後，應用寫入已落在新主站，形成跨站寫入差異。
4. 團隊凍結部署並轉人工處理拓撲與一致性風險。
5. 選擇 fail-forward，逐步恢復服務與處理 backlog。
6. 事故結束後回寫跨資料中心設計、通訊粒度與演練策略。

## 可回寫控制面

| 控制面                             | 這次事故暴露的缺口                 | 回寫方向                                               |
| ---------------------------------- | ---------------------------------- | ------------------------------------------------------ |
| Cross-DC replication guardrail     | partition 後拓撲變更過快           | 增加拓撲變更保護與人工切換門檻                         |
| Consistency-first decision path    | 可用性與一致性取捨缺標準化準則     | 在 decision log 固定記錄 fail-forward / fail-back 判準 |
| Backlog recovery strategy          | webhook / Pages 積壓恢復節奏缺共識 | 將 backlog drain 納入 recovery completion 定義         |
| Incident communication granularity | 只用單一顏色狀態無法表達部分恢復   | 對外更新按子服務與恢復階段拆分                         |

## 下一步路由

- 事故通訊： [8.4 Incident Communication](/backend/08-incident-response/incident-communication/)
- 止血與回復： [8.3 Containment / Recovery Strategy](/backend/08-incident-response/containment-recovery-strategy/)
- 事中決策紀錄： [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 證據回寫流程： [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
- 資料庫轉換實作： [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/)
- Migration rollout evidence： [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)
- 選型決策層： [0.C4 營運後技術轉換](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/)
- 穩態與恢復完成： [6.22 Steady State Definition](/backend/06-reliability/steady-state-definition/)

## 引用源

- [October 21 post-incident analysis](https://github.blog/2018-10-30-oct21-post-incident-analysis/)
- [October 21 Incident Report](https://github.blog/news-insights/company-news/october21-incident-report/)
