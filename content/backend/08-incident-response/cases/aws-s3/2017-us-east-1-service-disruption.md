---
title: "AWS S3 2017 US-EAST-1 Service Disruption"
date: 2026-05-07
description: "2017-02-28 AWS S3 us-east-1 事故解析：內部操作命令、index / placement 子系統重啟、區域依賴擴散與狀態頁依賴回寫。"
weight: 1
tags: ["backend", "incident-response", "case-study", "aws-s3"]
---

2017 年 AWS S3 us-east-1 事故的核心教訓是：內部操作工具若能快速移除共享子系統容量，單一命令輸入錯誤就會變成區域級控制面事故。這類事故的第一責任是限制操作 blast radius，再把恢復順序與通訊入口從受影響依賴中拆出。

## 事故摘要

AWS 在 2017-02-28 發生 Amazon S3 Northern Virginia（US-EAST-1）服務中斷。官方摘要指出，S3 團隊當時正在排查 billing system 進度偏慢問題；9:37AM PST，一位授權 S3 團隊成員依既有 playbook 執行命令，原本只要移除少量 billing 相關子系統 server，但其中一個輸入值錯誤，導致移除的 server set 比預期大。

被移除的 server 同時支援 S3 的 index subsystem 與 placement subsystem。index subsystem 管理該 region 內所有 S3 object 的 metadata 與位置資訊，GET、LIST、PUT、DELETE 都依賴它；placement subsystem 負責新 object 的 storage allocation，PUT 還需要它才能運作。這兩個子系統被迫完整重啟，導致 S3 API 在重啟期間無法正常服務。

## 判讀訊號

| 訊號                                    | 事故中代表什麼                   | 第一波決策價值                             |
| --------------------------------------- | -------------------------------- | ------------------------------------------ |
| GET / LIST / PUT / DELETE 同時異常      | index subsystem 已成為共同故障點 | 優先判斷 metadata / index 層，而非單一 API |
| PUT 恢復晚於 GET / LIST / DELETE        | placement subsystem 仍未完成恢復 | 對外通訊要分操作類型描述恢復狀態           |
| EC2 launch、EBS snapshot、Lambda 受影響 | S3 是多服務共享依賴              | incident scope 需要擴到 dependent services |
| Service Health Dashboard 更新受阻       | 狀態頁管理入口依賴受影響服務     | 立即切到獨立通訊路徑                       |
| 重啟時間超過預期                        | 大型子系統多年未完整重啟與驗證   | 回寫 recovery rehearsal 與 cell partition  |

## 事故路徑

1. S3 團隊排查 billing system 進度偏慢問題。
2. 授權成員依既有 playbook 執行移除少量 server 的操作命令。
3. 命令輸入值錯誤，移除的 server set 比預期大。
4. 被移除容量同時支援 index subsystem 與 placement subsystem。
5. 兩個子系統需要完整重啟，S3 API 在重啟期間無法正常服務。
6. 依賴 S3 的其他 AWS 服務在 US-EAST-1 同步受影響。
7. AWS 先用 AWS Twitter feed 與 Service Health Dashboard banner text 溝通，直到 SHD individual service status 可以更新。
8. index subsystem 先恢復足夠容量，再逐步恢復 GET / LIST / DELETE；placement subsystem 完成後，PUT 才恢復正常。

這條路徑顯示：事故起點是內部操作工具缺少數量與容量下限保護，外部流量尖峰在此無關。真正放大事故的是共享子系統、區域依賴與通訊入口對同一服務的依賴。

## 可回寫控制面

| 控制面                        | 這次事故暴露的缺口                         | 回寫方向                                                               |
| ----------------------------- | ------------------------------------------ | ---------------------------------------------------------------------- |
| 操作工具安全閘門              | 單一輸入錯誤可快速移除過多容量             | 對 remove / drain 類操作加速率、數量與 minimum capacity guardrail      |
| Shared subsystem blast radius | billing 操作影響 index 與 placement        | 對共享子系統建立 dependency map 與 blast radius review                 |
| Recovery rehearsal            | 大型子系統多年未完整重啟，恢復時間超過預期 | 把 index / placement 類核心子系統納入定期 restart / restore rehearsal  |
| Cell partition                | 大型 region 子系統恢復成本過高             | 把核心子系統拆成較小 cell，降低單次恢復範圍                            |
| Status page dependency        | SHD 管理入口依賴受影響服務                 | 將 incident communication 工具跨 region 與跨依賴部署                   |
| Operation decision log        | 事中需要記錄重啟順序與 API 恢復差異        | 在 decision log 中分別記錄 index、placement 與 dependent services 狀態 |

## 下一步路由

- 觀測證據包： [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
- 實驗安全邊界： [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)
- 穩態與恢復完成： [6.22 Steady State Definition](/backend/06-reliability/steady-state-definition/)
- 事故通訊： [8.4 Incident Communication](/backend/08-incident-response/incident-communication/)
- 止血與回復： [8.3 Containment / Recovery Strategy](/backend/08-incident-response/containment-recovery-strategy/)
- 事中決策紀錄： [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 證據回寫流程： [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)

## 引用源

- [Summary of the Amazon S3 Service Disruption in the Northern Virginia (US-EAST-1) Region](https://aws.amazon.com/message/41926/)
