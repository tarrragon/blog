---
title: "模組五：部署平台與網路入口"
date: 2026-04-22
description: "整理 Kubernetes、systemd、load balancer、container 與服務生命週期合約"
weight: 5
tags: ["backend", "deployment", "platform"]
---

部署平台模組的核心目標是說明服務如何和外部調度、網路入口與資源限制對齊。語言教材會處理 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/)、health / [readiness](/backend/knowledge-cards/readiness/) 檢查與 signal handling；本模組負責平台設定與操作語意。

## Vendor / Platform 清單

實作時的常用選擇見 [vendors](/backend/05-deployment-platform/vendors/) — T1 收錄 Kubernetes / Docker / systemd / nginx / Envoy / AWS ELB / Terraform / Traefik / Consul，每個 vendor 有定位、適用場景、取捨與預計實作話題的骨架。

Deep article（vendor 自身的配置、故障、容量）跟 migration playbook（跨 vendor 遷移流程）的撰寫進度見 [vendors/](/backend/05-deployment-platform/vendors/) 的「內容覆蓋進度」段。

## 暫定分類

| 分類                                                             | 內容方向                                                                                                                                                                                                                   |
| ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Container](/backend/knowledge-cards/container/)                 | image build、[Runtime Config](/backend/knowledge-cards/runtime-config/)、[Resource Limit](/backend/knowledge-cards/resource-limit/)                                                                                        |
| Kubernetes                                                       | deployment、pod lifecycle、[probe](/backend/knowledge-cards/probe/)、[rolling update](/backend/knowledge-cards/rolling-update)                                                                                             |
| systemd                                                          | service unit、restart policy、signal、journal                                                                                                                                                                              |
| [Load balancer](/backend/knowledge-cards/load-balancer/)         | [idle timeout](/backend/knowledge-cards/idle-timeout/)、[draining](/backend/knowledge-cards/draining/)、[health check](/backend/knowledge-cards/health-check/)、[sticky session](/backend/knowledge-cards/sticky-session/) |
| [Service Registry](/backend/knowledge-cards/service-registry/)   | 實例如何註冊、更新與摘除                                                                                                                                                                                                   |
| [Service discovery](/backend/knowledge-cards/service-discovery/) | [Internal Endpoint](/backend/knowledge-cards/internal-endpoint/) discovery、DNS                                                                                                                                            |
| [Config rollout](/backend/knowledge-cards/config-rollout/)       | 設定如何安全下發到正在運作的服務實例                                                                                                                                                                                       |
| [Runtime Config](/backend/knowledge-cards/runtime-config/)       | environment variable、[Secret Management](/backend/knowledge-cards/secret-management/)、[Feature Flag](/backend/knowledge-cards/feature-flag/)                                                                             |
| CDN 與邊緣分發                                                   | 邊緣快取、origin protection、purge 與 invalidation、stale-while-revalidate                                                                                                                                                 |

## 選型入口

部署平台選型的核心判斷是服務如何被啟動、更新、接流量、擴容與停止。當問題集中在 container image、rolling update、health check、[load balancer](/backend/knowledge-cards/load-balancer/)、[service registry](/backend/knowledge-cards/service-registry/)、[service discovery](/backend/knowledge-cards/service-discovery/) 或 [Runtime Config](/backend/knowledge-cards/runtime-config/) 時，應先評估部署平台能力。

Container 解決服務包裝與 runtime 依賴；Kubernetes 解決多 instance 調度、[probe](/backend/knowledge-cards/probe/)、rolling update 與 [resource limit](/backend/knowledge-cards/resource-limit/)；systemd 適合單機或 VM 上的 service lifecycle；[load balancer](/backend/knowledge-cards/load-balancer/) 解決流量入口、[draining](/backend/knowledge-cards/draining/)、[idle timeout](/backend/knowledge-cards/idle-timeout/) 與 [health check](/backend/knowledge-cards/health-check/)；[service registry](/backend/knowledge-cards/service-registry/) 解決實例狀態維護；[service discovery](/backend/knowledge-cards/service-discovery/) 解決服務彼此如何找到 [Internal Endpoint](/backend/knowledge-cards/internal-endpoint/)；[Runtime Config](/backend/knowledge-cards/runtime-config/) 解決環境差異、[Secret Management](/backend/knowledge-cards/secret-management/) 與 [Feature Flag](/backend/knowledge-cards/feature-flag/)。

接近真實網路服務的例子包括發版時 request 失敗、pod 尚未 ready 就接流量、長連線 shutdown 清理不完整、服務擴容後 [Internal Endpoint](/backend/knowledge-cards/internal-endpoint/) 更新延遲。這些場景的共同問題是程式與平台合約，因此本模組會先處理生命週期、流量入口與平台訊號。

## 與語言教材的分工

語言教材處理程式內的生命週期與訊號。Backend deployment 模組處理 Kubernetes、systemd、[load balancer](/backend/knowledge-cards/load-balancer/) 與 [container](/backend/knowledge-cards/container/) 平台如何觸發、解讀與限制這些訊號。

## 與資安概念層的交接

本模組承接 07 模組的概念判讀，並在服務實體層落地。交接基線如下：

- 來自 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)：承接入口分級、管理平面分離、修補窗口節奏。
- 來自 [7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)：承接 TLS/mTLS 與憑證佈署節奏。
- 來自 [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)：承接 runtime secret 與機器憑證交付模型。

這個交接讓部署模組聚焦實體配置與平台語意，同時保持與資安判讀一致。

## 案例驅動讀法

部署平台案例的核心讀法是先確認切換單位（服務、流量、叢集），再定義可回退邊界。

| 案例                                                                                                                  | 先看章節                                                                                                                      | 回寫目標                       |
| --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| [5.C1 Tradeshift：self-managed K8s -> EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) | [5.2](/backend/05-deployment-platform/kubernetes-deployment/)、[5.3](/backend/05-deployment-platform/load-balancer-contract/) | 把零停機遷移拆成分批切流策略   |
| [5.C2 Condé Nast：平台整併](/backend/05-deployment-platform/cases/conde-nast-platform-modernization-eks/)             | [5.2](/backend/05-deployment-platform/kubernetes-deployment/)                                                                 | 把多叢集治理收斂成單一控制面   |
| [5.C3 Orbitera：managed K8s migration](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/)  | [5.1](/backend/05-deployment-platform/container-runtime/)、[5.4](/backend/05-deployment-platform/service-discovery/)          | 把平台重置與服務連續性目標綁定 |

## 跨語言適配評估

部署平台使用方式會受語言的啟動時間、process model、signal handling、thread/task lifecycle、runtime memory behavior 與 liveness 支援影響。啟動慢的 runtime 要調整 [readiness](/backend/knowledge-cards/readiness) 與 rollout 節奏；長連線或背景 worker 要支援 [draining](/backend/knowledge-cards/draining/)；使用 GC 的 runtime 要觀察 memory limit 與 pause 行為；多 process 模型要確認 signal、[log](/backend/knowledge-cards/log) 與 [metrics](/backend/knowledge-cards/metrics) 如何聚合。

## 章節列表

| 章節                                                                          | 主題                                                                       | 關鍵收穫                                                                                                                                                              |
| ----------------------------------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [5.1](/backend/05-deployment-platform/container-runtime/)                     | [container](/backend/knowledge-cards/container/) 與 runtime                | 規劃 image、資源限制與啟動行為                                                                                                                                        |
| [5.2](/backend/05-deployment-platform/kubernetes-deployment/)                 | Kubernetes 部署策略                                                        | 了解 deployment、[probe](/backend/knowledge-cards/probe/)、rolling update                                                                                             |
| [5.3](/backend/05-deployment-platform/load-balancer-contract/)                | [Load Balancer Contract](/backend/knowledge-cards/load-balancer-contract/) | 處理 [idle timeout](/backend/knowledge-cards/idle-timeout/)、[draining](/backend/knowledge-cards/draining/) 與 [health check](/backend/knowledge-cards/health-check/) |
| [5.4](/backend/05-deployment-platform/service-discovery/)                     | [service discovery](/backend/knowledge-cards/service-discovery/)           | 讓服務能穩定註冊與發現彼此                                                                                                                                            |
| [5.5](/backend/05-deployment-platform/attacker-view-platform-entry-risks/)    | 平台與入口威脅建模（Threat Modeling）                                      | 用隱藏入口、設定漂移與切換風險盤點交付平台                                                                                                                            |
| [5.6](/backend/05-deployment-platform/platform-lifecycle-contract/)           | Platform Lifecycle Contract                                                | 分辨 startup、readiness、liveness、shutdown 與 drain 的責任                                                                                                           |
| [5.7](/backend/05-deployment-platform/traffic-config-control-plane-boundary/) | Traffic、Config 與 Control Plane Boundary                                  | 拆分流量、設定、secret、service discovery 與管理面邊界                                                                                                                |
| [5.8](/backend/05-deployment-platform/deployment-rollout-drain-rollback/)     | Deployment Rollout with Drain and Rollback 實作示範                        | 以 checkout service 示範 canary evidence、drain signal 與 rollback decision                                                                                           |
| [5.9](/backend/05-deployment-platform/edge-cdn-static-distribution/)          | 邊緣分發與靜態資源（CDN / Origin Protection）                              | 把 CDN 視為網路入口層，理解三層快取分工、origin protection、purge 操作模型                                                                                            |
| [5.10](/backend/05-deployment-platform/outbound-tunnel-entry/)                | Outbound Tunnel 入口與生命週期（cloudflared / Tailscale）                  | 把反向隧道視為一種入口形態、理解就緒對齊、network 層故障與認證疊法                                                                                                    |
| [5.C](/backend/05-deployment-platform/cases/)                                 | 轉換案例正文                                                               | 把平台遷移、整併與流量切換做成可回寫案例                                                                                                                              |

反例與規模對照入口： [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) / [5.C10 對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)。

回退判讀寫法見 [0.C4 回退判讀寫法](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/#回退判讀寫法)，部署案例要優先保留切流批次、draining、連線生命週期與回退時間。

## 觀念網路補完方向

部署平台章節下一輪的核心責任是把平台能力寫成服務契約。現有章節已經有 container、Kubernetes、load balancer 與 service discovery，但還需要補上 runtime contract、lifecycle contract、traffic contract、rollout contract 與 control-plane contract 的關係，讓讀者知道部署是一組流量、連線、設定、資源與回退條件的連續切換。

| 補完方向               | 需要回答的問題                                                   | 主要路由                                                                                                                                      |
| ---------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Runtime contract       | image、entrypoint、runtime config 與 resource limit 是否可預期   | [container](/backend/knowledge-cards/container/)、[runtime config](/backend/knowledge-cards/runtime-config/)                                  |
| Lifecycle contract     | startup、readiness、liveness、shutdown 與 drain 是否對齊         | [readiness](/backend/knowledge-cards/readiness/)、[draining](/backend/knowledge-cards/draining/)                                              |
| Traffic contract       | load balancer、timeout、sticky session 與 routing 是否有明確邊界 | [load balancer contract](/backend/knowledge-cards/load-balancer-contract/)、[request routing](/backend/knowledge-cards/request-routing/)      |
| Rollout contract       | canary、rolling update、config rollout 與 rollback 是否可分批    | [config rollout](/backend/knowledge-cards/config-rollout/)、[6.8](/backend/06-reliability/release-gate/)                                      |
| Control-plane contract | service discovery、secret delivery 與管理面是否被保護            | [management plane](/backend/knowledge-cards/management-plane/)、[7.3](/backend/07-security-data-protection/entrypoint-and-server-protection/) |

這些方向要用部署平台自己的服務壓力展開。短 request API、長連線服務、背景 worker、[control plane](/backend/knowledge-cards/control-plane/) config push 與多租戶平台的生命週期不同，寫作時要分別處理它們的 rollout 與 drain 條件。

## 知識卡補強方向

部署模組的 knowledge card 缺口集中在「平台契約」與「切換完成訊號」。已有 [readiness](/backend/knowledge-cards/readiness/)、[draining](/backend/knowledge-cards/draining/)、[config rollout](/backend/knowledge-cards/config-rollout/) 與 [rollback strategy](/backend/knowledge-cards/rollback-strategy/) 可以作為第一批錨點。

下一批候選卡片包括 startup probe、drain completion、rollout batch、[rollback window](/backend/knowledge-cards/rollback-window/)、config freeze、environment protection 與 deployment contract。這些卡片要讓讀者能分辨「服務已啟動」和「服務可安全接流量」分屬不同責任。

## 實作探討入口

部署平台的第一條實作路徑是 [5.8 Deployment Rollout with Drain and Rollback（實作示範）](/backend/05-deployment-platform/deployment-rollout-drain-rollback/)。這篇以 checkout service rollout 為例，說明 rollout plan、canary evidence、drain signal、rollback condition 與 incident decision route 如何一起成立。

這條路徑的前置引用應該是 5.2 Kubernetes deployment、5.3 load balancer contract、[5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)、[6.8 Release Gate](/backend/06-reliability/release-gate/) 與 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。完成後可依 [Backend 學習路線](/backend/#學習路線) 進入下一條服務路徑。

部署路徑的 artifact 對齊重點是「每一批切換都能被觀測、被放行、被回退」。對 [4.20](/backend/04-observability/observability-evidence-package/) 要交 `Source/Time range/Query link/Owner/Data quality`，並覆蓋 per-version error rate、latency、drain completion 與 reconnect 訊號；對 [6.8](/backend/06-reliability/release-gate/) 要交 `Gate decision/Checks/Stop condition/Rollback window/Owner`，呈現 canary 批次與停損規則；對 [8.19](/backend/08-incident-response/incident-decision-log/) 要交 `Timestamp/Decision/Context/Evidence/Owner/Expected effect/Rollback condition`，記錄 freeze、回退與重啟切流的決策條件與時間序列。
