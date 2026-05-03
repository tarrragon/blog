---
title: "6.20 Experiment Safety Boundary"
date: 2026-05-02
description: "定義 chaos、load test、DR drill 的 blast radius、停止條件與權限約束"
weight: 20
---

## 大綱

- experiment safety boundary 的責任：讓可靠性實驗可控、可停、可回復
- 實驗類型：chaos test、load test、failover drill、rollback rehearsal、DR drill
- blast radius：服務、tenant、region、dependency、資料範圍
- 停止條件：SLO burn、error rate、latency、queue lag、customer impact、cost threshold
- 權限約束：誰能啟動、誰能停止、誰能擴大範圍
- evidence 要求：假設、步驟、觀測訊號、結果、回復時間、action item
- 跟 07 的交接：高風險演練需要權限與稽核約束
- 反模式：直接在 production 打 chaos；缺停止條件；實驗 owner 與 incident commander 不清楚

Experiment safety boundary 的價值在於讓失敗驗證可重播、可停止、可回復。實驗越接近真實失效，對團隊越有學習價值；同時也越需要清楚邊界，避免「為了驗證韌性」而產生額外事故。

## 概念定位

Experiment safety boundary 是定義可靠性實驗安全範圍的控制面，責任是讓團隊能主動驗證失敗，同時控制實驗造成的實際風險。

這一頁處理的是實驗邊界。可靠性實驗的價值來自接近真實失效，但越接近真實，越需要明確 blast radius、停止條件與回復路徑。

安全邊界是一組事前契約：誰能啟動、誰有停止權、觸發什麼門檻必須終止、終止後怎麼回復。契約存在時，團隊才能在實驗中保持速度，同時控制風險成本。

## 核心判讀

判讀 experiment safety 時，先看實驗假設是否明確，再看實驗失控時是否能立刻停止與回復。

重點訊號包括：

- experiment hypothesis 是否連到具體 failure mode
- blast radius 是否限制 service、tenant、region 或 traffic percentage
- stop condition 是否連到 SLO / customer impact / cost
- rollback / failover 是否在實驗前準備好
- observer、executor、approver 是否分工清楚

| 控制面   | 最小可用判準                              | 失控信號             |
| -------- | ----------------------------------------- | -------------------- |
| 範圍控制 | blast radius 限在服務 / 區域 / 流量百分比 | 影響擴散到非目標服務 |
| 停止條件 | stop condition 連到 SLO / impact / cost   | 超門檻仍持續實驗     |
| 權限治理 | 啟動者、停止者、核准者分離                | 需要額外查證誰在操作 |
| 回復能力 | rollback / failover 已預演                | 終止後回復時間失控   |
| 證據留存 | hypothesis 與結果可回放                   | 成功與失敗都不可重現 |

## 判讀訊號

- chaos 實驗描述只有「打掉節點」，沒有 steady state 與停止條件
- load test 影響共享 dependency，其他服務被連帶拖垮
- DR drill 的停止擴大條件需要臨場討論
- 實驗成功但沒有 evidence，可重播性不足
- 實驗權限過寬，值班人員不知道誰在操作

常見事故型場景是 load test 誤傷共享依賴，導致無關服務一起退化。若實驗前有 boundary 契約，至少會先限制流量比例、設定跨服務告警與 stop condition，讓問題停留在演練範圍內。

## 交接路由

- 04.16 observability readiness：確認實驗可被觀測
- 06.4 chaos testing：定義故障注入場景
- 06.7 DR / rollback rehearsal：定義回復路徑
- 06.22 steady state definition：定義實驗前穩態
- 07.23 shared controls：接 containment、rollback、degradation 共用控制面
- 08.6 drills / on-call readiness：把實驗轉成值班演練
