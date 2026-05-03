---
title: "6.7 DR 演練與 Rollback Rehearsal"
date: 2026-05-01
description: "把回復路徑變成定期可重播流程"
weight: 7
---

## 概念定位

DR 演練與 rollback rehearsal 是把回復能力從「有計畫」變成「真的跑過」的工具。DR 關心的是系統在災難後能不能回來，rollback rehearsal 關心的是變更失敗時能不能退回安全狀態。兩者都不是紙上方案，而是把回復路徑變成可驗證流程。

這個節點先處理路徑，再處理速度。先確認資料能不能回來、服務能不能切回來、回復後會不會再掉回去，然後才談 [RTO](/backend/knowledge-cards/rto/) / [RPO](/backend/knowledge-cards/rpo/)。這樣讀，會比直接背指標更接近真實系統的恢復成本。

## 大綱

- DR 演練的目的： [RTO](/backend/knowledge-cards/rto/) / [RPO](/backend/knowledge-cards/rpo/) 從紙面到肌肉記憶
- rollback rehearsal vs roll-forward only：何時可選 / 何時必選
- 演練類別：tabletop、partial failover、full region failover、data restore drill
- backup / restore 的可驗證性：restore 才算 backup
- 跟 [6.4 chaos](/backend/06-reliability/chaos-testing/) 的差異：DR 重在回復路徑、chaos 重在故障注入
- 跟 [8.6 演練](/backend/08-incident-response/drills-and-oncall-readiness/) 的分工：6.7 是事前流程、8.6 是團隊技能
- 反模式：DR plan 寫了沒演練、restore 從未驗證、failover 路徑跟 production 不同步

## 核心判讀

DR 的責任是證明回復路徑存在，而且真的能走。只要 backup 還沒被 restore 驗證過，它就只是備份，不是復原能力。只要 failover config 沒跟 production 對齊，它就只是文件，不是操作路由。

rollback rehearsal 的責任是把失敗變更的退路先跑過。當 deployment 出現問題時，團隊需要知道自己是能回退、必須 roll forward，還是必須先止血再處理資料。這個判斷不是臨場猜的，而是平常 rehearsal 跑出來的。

## 判讀訊號

- DR plan 寫在 wiki、過去 12 個月未演練
- backup 有自動排程、restore 從未 end-to-end 跑過
- failover 配置跟 production 漂移、無對齊檢查
- [RTO](/backend/knowledge-cards/rto/) / [RPO](/backend/knowledge-cards/rpo/) 是估值、不是量值
- rollback 路徑需要手動 SQL 或脫離 deploy 流程

## 案例對照

AWS S3 適合用來看區域級控制面失效後的恢復順序，因為它把 [blast radius](/backend/knowledge-cards/blast-radius/) 和 recovery order 的成本都暴露出來。Roblox 適合用來看長尾恢復，因為 73 小時 outage 顯示 recovery 不是切回流量就結束。GitHub 和 Meta 則適合看資料一致性與跨區切換，因為它們都能說明 failover 跟一致性之間的交換成本。

Shopify 的 BFCM 準備也很適合放進這個節點，因為它把高峰前的演練、壓測與隔離單位連成一條線。這些案例放在一起時，讀者會看到 DR 不是單一備援方案，而是一組可回放、可驗證、可校準的回復路徑。

## 演練類型

| 類型                 | 目的                           | 典型輸出                                                                                   |
| -------------------- | ------------------------------ | ------------------------------------------------------------------------------------------ |
| tabletop             | 檢查決策路由與角色分工         | 角色清單、決策順序、通訊模板                                                               |
| partial failover     | 驗證局部區域或子系統能否切換   | 切換結果、回復時間、手動步驟                                                               |
| full region failover | 驗證整個區域是否能從災難中回來 | [RTO](/backend/knowledge-cards/rto/)、[RPO](/backend/knowledge-cards/rpo/)、資料一致性檢查 |
| data restore drill   | 驗證備份是否能真的還原資料     | restore log、校驗結果、缺口清單                                                            |

這些演練的共同點是：演練本身要留下證據。沒有輸出，就沒有辦法判斷回復能力到底有沒有被建立。

## 交接路由

- 05 部署：blue-green / region failover 實作
- 06.11 migration safety：migration rollback 演練
- 06.12 idempotency / replay：replay 是 DR 回復的前提
- 08.3 止血回復：演練結果作為事中決策素材
- 08.6 演練：DR 結果回饋到值班訓練
- 08.15 vendor 事故：多 vendor / 多區 failover 路徑
