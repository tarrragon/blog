---
title: "5.2 Kubernetes 部署策略"
date: 2026-04-23
description: "整理 deployment、probe 與 rolling update"
weight: 2
tags: ["backend", "deployment", "kubernetes"]
---

Kubernetes 部署策略（Kubernetes deployment strategy）的核心責任是把服務版本切換做成可預測流程。Deployment 把副本數、健康訊號、流量承接、設定變更與回退條件組成同一條交付路徑。

## deployment、replica 與 rollout

Deployment 的責任是宣告目標狀態：期望副本數、版本、更新策略。rollout 的責任是把現況收斂到目標狀態，並在過程中維持可服務能力。這兩者分開理解後，才能在異常時判斷是目標設定問題，還是收斂過程問題。

rolling update 常用來降低單次切換風險。關鍵不是名稱，而是批次大小與節奏：每批新增多少新副本、每批回收多少舊副本、每批觀察多長時間。這些參數應以服務容量曲線與回退時間目標校準。

## probe 對齊服務生命週期

[probe](/backend/knowledge-cards/probe/) 要對齊服務生命週期，不同 probe 有不同責任：

1. startup probe：確認服務啟動完成，避免慢啟動服務被過早重啟。
2. [readiness](/backend/knowledge-cards/readiness/) probe：確認服務可安全接流量。
3. liveness probe：確認服務仍可維持基本運作，必要時觸發重建。

probe 設計若只回傳固定成功，rollout 期間會出現「容器在線但服務未就緒」的流量抖動。穩定做法是讓 readiness 反映依賴就緒條件，例如資料庫連線池、必要配置、關鍵背景任務狀態。

## config rollout 與版本相容

[Config Rollout](/backend/knowledge-cards/config-rollout/) 需要和應用版本一起治理。設定先行、版本後行，或版本先行、設定後行，都要保留相容窗口。相容窗口存在時，才有漸進 rollout 與快速回退空間。

跨版本配置遷移要先定義停止條件：錯誤率上升、延遲尖峰、關鍵路徑失敗或下游壓力超標。停止條件明確後，部署決策才能一致。

## autoscaling 與部署策略協同

[autoscaling](/backend/knowledge-cards/autoscaling/) 在部署期間扮演容量緩衝角色。部署批次若超過服務可承受變動幅度，autoscaling 會被動補償並延長收斂時間。穩定做法是讓 rollout 節奏與容量策略同時設計：先保證服務穩態，再提高切換速度。

長連線服務或有大量背景任務的 workload，通常需要比 stateless API 更保守的 rollout 策略，並額外搭配 drain 與 reconnect 設計。

## 判讀訊號

| 訊號                               | 判讀重點                     | 對應動作                              |
| ---------------------------------- | ---------------------------- | ------------------------------------- |
| rollout 卡在中段且新副本反覆重啟   | probe 與啟動路徑不匹配       | 校正 startup/readiness 探針與超時參數 |
| rollout 完成後延遲與錯誤率短期上升 | 批次切換過快或下游未對齊     | 降低批次、延長觀察窗口、回退再重試    |
| config 變更後特定路徑失敗率飆升    | 設定與版本相容窗口不足       | 啟動回退配置、補雙軌相容              |
| autoscaling 在部署期間頻繁抖動     | 容量閾值與 rollout 節奏衝突  | 分離部署窗口與擴縮窗口、調整資源策略  |
| 長連線服務切版後 reconnect storm   | drain 與連線生命週期控制不足 | 拉長 drain、分批切流、校正 timeout    |

## 常見誤區

把 Kubernetes 部署看成 YAML 套版，會忽略服務語意差異。相同 deployment 參數在不同服務上，可能代表完全不同風險。

把 probe 當成健康檢查 URL，會讓服務在邊界條件下過早接流量。probe 的工程價值在於反映服務真實可用條件。

## 案例回寫

部署切換語意可用 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) 做回寫。先看事件中的失敗是在 rollout 批次、probe 判斷、還是 drain 時序，再對照本章的 rollout 節奏與停止條件。

若版本已切換但錯誤率延遲上升，先回到 probe 與 config 相容窗口，再把證據欄位接到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 跨模組路由

Kubernetes 部署策略要和觀測、驗證、事故流程同時對齊。

1. 與 5.3 的交接：流量承接與退出落在 [load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。
2. 與 4.20 的交接：版本切換證據進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
3. 與 6.8 的交接：放行與停損條件進入 [Release Gate](/backend/06-reliability/release-gate/)。
4. 與 8.19 的交接：部署中止與回退判斷進入 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要把部署與流量切換一起治理，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。要看切換失敗與回退判讀，接著讀 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)。
