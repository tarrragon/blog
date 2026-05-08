---
title: "1.6 資料庫轉換實作：雙寫、回填、切流與回滾"
date: 2026-05-07
description: "把資料庫轉換從一次性搬遷變成可分段驗證的工程流程。"
weight: 6
tags: ["backend", "database", "migration"]
---

資料庫轉換實作的核心責任是讓 schema、資料與流量切換都可分段驗證，並在任一階段可安全回退。這一頁不討論要不要轉換，專注回答「決定要換之後怎麼做」。

## 實作流程

| 階段        | 核心動作                                     | 交付成果                         |
| ----------- | -------------------------------------------- | -------------------------------- |
| 1. 邊界定義 | 定義 source of truth、切換範圍、不可中斷路徑 | migration scope 與 rollback 邊界 |
| 2. Expand   | 新欄位/新表先上線，應用可同時讀舊寫新或雙寫  | 新舊版本相容窗口                 |
| 3. Backfill | 批次回填歷史資料，保留節流與 checkpoint      | 可追蹤的回填進度與失敗重試       |
| 4. 驗證     | shadow read、checksum、業務指標對帳          | 一致性證據包                     |
| 5. Cutover  | 逐步切讀、再切寫，保留快速回切策略           | 切流完成且可回退                 |
| 6. Contract | 移除舊欄位與舊路徑，收斂技術債               | 單一資料語意落地                 |

## 判讀訊號

| 訊號                            | 判讀重點                 | 對應動作                        |
| ------------------------------- | ------------------------ | ------------------------------- |
| 回填速度不穩、延遲飆高          | 可能與線上流量競爭 IOPS  | 降低批次大小、加節流、避開 peak |
| 雙寫成功率高但 shadow read 漂移 | 業務語意映射不一致       | 先修轉換函式，再重跑對帳        |
| 切流後 error rate 升高          | 新庫讀寫路徑與索引未對齊 | 回切舊讀路徑、補索引後再灰度    |
| rollback 時間超出 RTO           | 回退流程過度人工         | 把回退腳本化並演練              |

## 常見誤區

把資料庫轉換當成單次 DDL 任務，會讓風險集中在 cutover 當下。穩定做法是把每一階段都做成可驗證、可回退的獨立里程碑。

把 dual-write 當成最終保障也常出錯。雙寫只能保證「兩邊都有寫」，不保證「語意一致」，仍要配 shadow read 與業務對帳。

## 案例回寫

- 選型層案例： [0.C4 營運後技術轉換](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/)
- 可靠性治理： [6.11 Migration Safety](/backend/06-reliability/migration-safety/)
- 事故反饋： [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/)

這組案例主要支撐的是「分段切換與可回退驗證」判讀，不直接支撐快取 TTL 或 broker delivery 參數；若問題核心在快取新鮮度或投遞語意，應轉到 2.x 或 3.x。

## 跨模組路由

1. 與 1.2 的交接：欄位演進與命名語意回到 [schema design](/backend/01-database/schema-design/)。
2. 與 1.3 的交接：交易邊界與副作用切分回到 [transaction boundary](/backend/01-database/transaction-boundary/)。
3. 與 4.20 的交接：validation query 與一致性證據進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
4. 與 6.11/6.8 的交接：放行與停損條件進入 [Migration Safety](/backend/06-reliability/migration-safety/) 與 [Release Gate](/backend/06-reliability/release-gate/)。
5. 與 8.19 的交接：pause、rollback、fail-forward 決策記錄到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

若你還在判斷是否該轉換，先回 [0.C4](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/) 看決策訊號。若你在設計放行與演練，接著看 [6.11](/backend/06-reliability/migration-safety/) 與 [6.8](/backend/06-reliability/release-gate/)。若你在事故回溯，接著看 [8.23 Post-incident Review](/backend/08-incident-response/post-incident-review/)。
