---
title: "5.1 container 與 runtime"
date: 2026-04-23
description: "整理 image、resource limit 與啟動行為"
weight: 1
tags: ["backend", "deployment", "container"]
---

容器執行環境（container runtime）的核心責任是把應用執行環境做成可重現、可限制、可觀測的交付單位。它是部署可靠性的起點。

## image 與建置責任

image 的責任是固定依賴、執行入口與檔案結構，讓同一版本在不同環境行為一致。建置流程要回答三件事：基底映像是否可維護、建置產物是否可追溯、敏感資訊是否被隔離。

映像層數、套件來源、編譯參數都會影響啟動時間與安全邊界。部署策略在後面才有效，前提是 runtime 產物本身可預測。

## entrypoint 與啟動行為

entrypoint/command 的責任是定義容器如何啟動與退出。啟動流程應顯式處理初始化步驟、配置載入、依賴檢查與失敗退出。退出流程應處理信號中斷、在途請求收斂與資源釋放。

若啟動行為隱藏在 shell script 且無可觀測訊號，部署平台很難判斷 readiness 與失敗原因。

## resource limit

[Resource Limit](/backend/knowledge-cards/resource-limit/) 的責任是隔離資源競爭並保護集群穩態。CPU/memory 限制過低會導致頻繁節流與重啟，過高會壓縮同節點容量並放大鄰近工作負載風險。

限制設計要依服務流量型態與 GC/執行時特性調整，並與 autoscaling、rollout 批次策略一起評估。

## runtime config

[Runtime Config](/backend/knowledge-cards/runtime-config/) 的責任是把環境差異顯式化。配置來源、版本、更新節奏都應可追蹤。高風險設定需配合 [Config Rollout](/backend/knowledge-cards/config-rollout/) 策略，避免同批大規模變更。

runtime 配置與映像版本要保留相容窗口，讓部署與回退可分步進行。

## 判讀訊號

| 訊號                              | 判讀重點                        | 對應動作                                |
| --------------------------------- | ------------------------------- | --------------------------------------- |
| 新版本容器啟動時間顯著增加        | image 體積或初始化步驟膨脹      | 優化映像層、拆分初始化流程              |
| rollout 初期出現 OOM/CPU throttle | resource limit 與實際負載不匹配 | 重設 request/limit、調整併發與批次      |
| 配置變更後特定環境異常            | runtime config 管理不一致       | 統一配置來源、補版本追蹤與差異檢查      |
| 容器停止時請求中斷率上升          | signal/drain 協調不足           | 補 shutdown hook、對齊 termination 流程 |
| 同版本在不同節點行為差異大        | runtime 依賴未固定或環境漂移    | 收斂基底映像、鎖定依賴與建置流程        |

## 常見誤區

把 container 視為純打包步驟，會把部署風險後移到 rollout 階段。runtime 產物穩定性不足時，後續 probe、canary、rollback 都只能被動補救。

把資源限制設成平台預設值，也常造成高峰期不穩。限制應反映服務真實耗用模式，不應只追求表面資源利用率。

## 案例回寫

runtime 穩定性可用 [5.C1 Tradeshift：self-managed K8s -> EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) 回寫。先看遷移期內啟動行為與資源限制如何影響切流，再對照本章檢查 image、entrypoint、limit 與 config 相容窗口。
這個案例主要支撐的是「執行環境可重現性」判讀，不直接支撐 service discovery TTL 或 queue replay 邏輯；若根因在定位鏈路或重播流程，應轉到 5.4 或 3.4。

若同版容器在不同節點出現分歧行為，先追建置來源與 runtime config 版本鏈，確認是依賴漂移還是環境漂移，再把關鍵證據收斂到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

## 跨模組路由

1. 與 5.2 的交接：部署批次與探針策略回到 [Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。
2. 與 5.3 的交接：流量進出與連線收斂回到 [load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。
3. 與 4.20 的交接：啟動與資源證據回到 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
4. 與 6.8 的交接：放行與回退條件回到 [Release Gate](/backend/06-reliability/release-gate/)。

## 下一步路由

要把 runtime 行為接到部署收斂，接著讀 [5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。要看切流與退場條件，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。
