---
title: "模組五：部署平台與網路入口"
date: 2026-04-22
description: "整理 Kubernetes、systemd、load balancer、container 與服務生命週期合約"
weight: 5
---

部署平台模組的核心目標是說明服務如何和外部調度、網路入口與資源限制對齊。語言教材會處理 graceful shutdown、health/readiness endpoint 與 signal handling；本模組負責平台設定與操作語意。

## 暫定分類

| 分類              | 內容方向                                             |
| ----------------- | ---------------------------------------------------- |
| Container         | image build、runtime config、resource limit          |
| Kubernetes        | deployment、pod lifecycle、probe、rolling update     |
| systemd           | service unit、restart policy、signal、journal        |
| Load balancer     | idle timeout、draining、health check、sticky session |
| Service discovery | endpoint discovery、DNS、config rollout              |
| Runtime config    | environment variable、secret、feature flag           |

## 選型入口

部署平台選型的核心判斷是服務如何被啟動、更新、接流量、擴容與停止。當問題集中在 container image、rolling update、health check、load balancer、service discovery 或 runtime config 時，應先評估部署平台能力。

Container 解決服務包裝與 runtime 依賴；Kubernetes 解決多 instance 調度、probe、rolling update 與資源限制；systemd 適合單機或 VM 上的 service lifecycle；load balancer 解決流量入口、draining、idle timeout 與 health check；service discovery 解決服務彼此如何找到 endpoint；runtime config 解決環境差異、secret 與 feature gate。

接近真實網路服務的例子包括發版時 request 失敗、pod 尚未 ready 就接流量、長連線 shutdown 清理不完整、服務擴容後 endpoint 更新延遲。這些場景的共同問題是程式與平台合約，因此本模組會先處理生命週期、流量入口與平台訊號。

## 與語言教材的分工

語言教材處理程式內的生命週期與訊號。Backend deployment 模組處理 Kubernetes、systemd、load balancer 與 container 平台如何觸發、解讀與限制這些訊號。

## 跨語言適配評估

部署平台使用方式會受語言的啟動時間、process model、signal handling、thread/task lifecycle、runtime memory behavior 與 health check 支援影響。啟動慢的 runtime 要調整 readiness 與 rollout 節奏；長連線或背景 worker 要支援 draining；使用 GC 的 runtime 要觀察 memory limit 與 pause 行為；多 process 模型要確認 signal、log 與 metrics 如何聚合。

## 章節列表

| 章節                         | 主題                      | 關鍵收穫                                                     |
| ---------------------------- | ------------------------- | ------------------------------------------------------------ |
| [5.1](container-runtime/)    | container 與 runtime      | 規劃 image、資源限制與啟動行為                                |
| [5.2](kubernetes-deployment/)| Kubernetes 部署策略       | 了解 deployment、probe、rolling update                       |
| [5.3](load-balancer-contract/) | load balancer 合約      | 處理 idle timeout、draining 與 health check                  |
| [5.4](service-discovery/)    | service discovery         | 讓服務能穩定發現彼此與完成設定下發                            |
