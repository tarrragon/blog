---
title: "6.7 DR 演練與 Rollback Rehearsal"
date: 2026-05-01
description: "把回復路徑變成定期可重播流程"
weight: 7
---

## 大綱

- DR 演練的目的：RTO / RPO 從紙面到肌肉記憶
- rollback rehearsal vs roll-forward only：何時可選 / 何時必選
- 演練類別：tabletop、partial failover、full region failover、data restore drill
- backup / restore 的可驗證性：restore 才算 backup
- 跟 [6.4 chaos](/backend/06-reliability/chaos-testing/) 的差異：DR 重在回復路徑、chaos 重在故障注入
- 跟 [8.6 演練](/backend/08-incident-response/drills-and-oncall-readiness/) 的分工：6.7 是事前流程、8.6 是團隊技能
- 反模式：DR plan 寫了沒演練、restore 從未驗證、failover 路徑跟 production 不同步

## 判讀訊號

- DR plan 寫在 wiki、過去 12 個月未演練
- backup 有自動排程、restore 從未 end-to-end 跑過
- failover 配置跟 production 漂移、無對齊檢查
- RTO / RPO 是估值、不是量值
- rollback 路徑需要手動 SQL 或脫離 deploy 流程

## 交接路由

- 05 部署：blue-green / region failover 實作
- 06.11 migration safety：migration rollback 演練
- 06.12 idempotency / replay：replay 是 DR 回復的前提
- 08.3 止血回復：演練結果作為事中決策素材
- 08.6 演練：DR 結果回饋到值班訓練
- 08.15 vendor 事故：多 vendor / 多區 failover 路徑
