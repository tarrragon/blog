---
title: "5.6 Platform Lifecycle Contract"
date: 2026-05-11
description: "說明 runtime、startup、readiness、liveness、shutdown 與 drain 如何組成平台生命週期合約。"
weight: 6
tags: ["backend", "deployment", "platform", "lifecycle"]
---

Platform lifecycle contract 的核心責任是讓服務和部署平台對同一組生命週期訊號有共同解讀。進入 Kubernetes、systemd、Docker、ELB 或 Envoy 前，讀者需要先理解「服務啟動」和「服務可接流量」是不同狀態。

## Lifecycle Contract

Lifecycle contract 定義平台如何啟動、檢查、接流量、停止與回收服務實例。它包含 runtime、startup、readiness、liveness、shutdown 與 drain。

| 狀態      | 服務責任                                   | 平台責任                    |
| --------- | ------------------------------------------ | --------------------------- |
| runtime   | 固定 image、entrypoint、config 與 resource | 提供可預期執行環境          |
| startup   | 初始化依賴與內部狀態                       | 避免過早重啟慢啟動服務      |
| readiness | 宣告可安全接流量                           | 只把流量導向 ready instance |
| liveness  | 宣告基本運作能力                           | 在不可恢復時重建 instance   |
| shutdown  | 停接新工作並釋放資源                       | 給予 termination window     |
| drain     | 完成在途請求或連線退場                     | 從路由集合摘除 instance     |

這些狀態分開後，部署事故才能定位是啟動、接流量、退場還是平台判讀問題。

runtime 與 startup 決定服務能否形成可運行實例。readiness 與 liveness 決定平台何時導入流量與何時重建實例。shutdown 與 drain 決定版本退場時是否能保護在途工作。這些狀態都屬於生命週期合約，卻對應不同的事故處理路徑。

## Startup 與 Readiness

startup 的責任是確認服務初始化完成。[readiness](/backend/knowledge-cards/readiness/) 的責任是確認服務可承接實際流量。啟動完成不代表依賴已就緒，也不代表背景任務、config、secret 或 connection pool 都可用。

慢啟動服務需要 startup gate，避免 liveness 在初始化期間反覆重啟。依賴敏感服務需要 readiness gate，避免尚未連上資料庫、cache 或 queue 時就接收請求。

## Liveness 與 Restart

liveness 的責任是偵測無法自我恢復的狀態。短暫下游故障適合交給 readiness、circuit breaker 或 fallback 處理，否則平台會用重啟放大故障。

liveness 太敏感會造成 restart loop；liveness 太寬鬆會讓壞實例長期留在線上。設計時要先定義哪些錯誤可由服務內部恢復，哪些才需要平台重建。

## Shutdown 與 Drain

shutdown 的責任是讓服務停止接新工作並完成資源釋放。[draining](/backend/knowledge-cards/draining/) 的責任是讓平台在移除實例前，讓 [in-flight](/backend/knowledge-cards/in-flight/) request、長連線或背景工作有時間收束。

短 request API、長連線服務與 background worker 的 drain 條件不同。短 API 主要看在途請求歸零；長連線看 reconnect 節奏；worker 看已領取工作能否完成或重新排隊。tunnel 入口的 startup / readiness / drain 對齊見 [5.10 Outbound Tunnel 入口](/backend/05-deployment-platform/outbound-tunnel-entry/)。

## 選型前判準

部署平台選型前要先回答：

1. 服務啟動需要多久，哪些依賴是 readiness 條件。
2. 服務失敗時應由自己恢復，還是由平台重建。
3. 服務停止時有哪些 in-flight request、connection 或 job。
4. 平台是否能表達 startup、readiness、liveness 與 drain 的差異。

這些問題決定後續要比較 Kubernetes probe、systemd restart policy、load balancer health check 或 service mesh drain 能力。

## 實體服務討論承接點

實體部署平台文章要承接本篇的 lifecycle contract。Kubernetes、systemd、Docker、ECS、Nomad 或其他平台的比較，應先問它們如何表達 startup、readiness、liveness、shutdown 與 drain，再進入 YAML、unit file 或平台操作。

若服務是短 request API，後續文章要比較 readiness、rolling update 與 load balancer health check。若服務是長連線或 worker，後續文章要比較 graceful shutdown、drain window、job handoff 與 restart policy。若服務啟動慢或依賴多，後續文章要比較 startup gate、init sequence 與 rollout pacing。

## 下一步路由

要看 Kubernetes 如何承接這組生命週期，接著讀 [5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。要看流量退場如何和 LB 對齊，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。
