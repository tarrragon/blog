---
title: "模組五：部署平台與網路入口"
date: 2026-04-22
description: "整理 Kubernetes、systemd、load balancer、container 與服務生命週期合約"
weight: 5
---

部署平台模組的核心目標是說明服務如何和外部調度、網路入口與資源限制對齊。語言教材會處理 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/)、health / [readiness](/backend/knowledge-cards/readiness/) 檢查與 signal handling；本模組負責平台設定與操作語意。

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

## 跨語言適配評估

部署平台使用方式會受語言的啟動時間、process model、signal handling、thread/task lifecycle、runtime memory behavior 與 liveness 支援影響。啟動慢的 runtime 要調整 [readiness](/backend/knowledge-cards/readiness) 與 rollout 節奏；長連線或背景 worker 要支援 [draining](/backend/knowledge-cards/draining/)；使用 GC 的 runtime 要觀察 memory limit 與 pause 行為；多 process 模型要確認 signal、[log](/backend/knowledge-cards/log) 與 [metrics](/backend/knowledge-cards/metrics) 如何聚合。

## 章節列表

| 章節                                       | 主題                                                                       | 關鍵收穫                                                                                                                                                              |
| ------------------------------------------ | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [5.1](container-runtime/)                  | [container](/backend/knowledge-cards/container/) 與 runtime                | 規劃 image、資源限制與啟動行為                                                                                                                                        |
| [5.2](kubernetes-deployment/)              | Kubernetes 部署策略                                                        | 了解 deployment、[probe](/backend/knowledge-cards/probe/)、rolling update                                                                                             |
| [5.3](load-balancer-contract/)             | [Load Balancer Contract](/backend/knowledge-cards/load-balancer-contract/) | 處理 [idle timeout](/backend/knowledge-cards/idle-timeout/)、[draining](/backend/knowledge-cards/draining/) 與 [health check](/backend/knowledge-cards/health-check/) |
| [5.4](service-discovery/)                  | [service discovery](/backend/knowledge-cards/service-discovery/)           | 讓服務能穩定註冊與發現彼此                                                                                                                                            |
| [5.5](attacker-view-platform-entry-risks/) | 攻擊者視角（紅隊）：平台與入口弱點判讀                                     | 用隱藏入口、設定漂移與切換風險檢查交付平台                                                                                                                            |
