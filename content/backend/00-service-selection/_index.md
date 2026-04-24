---
title: "模組零：後端服務選型"
date: 2026-04-23
description: "從需求類型判斷資料庫、快取、訊息佇列、觀測與部署平台的選型方向"
weight: 0
---

後端服務選型的核心目標是把「需求類型」轉成「服務能力」。資料庫、快取、訊息佇列、觀測平台與部署平台都能提升系統能力，但它們解決的是不同問題；選型時要先辨識需求、流量、資料量、失敗代價與成本模型，再進入具體產品比較。

本模組先建立跨分類的選型語言。後續進入 [database](../knowledge-cards/database/)、Redis、message [queue](../knowledge-cards/queue/)、observability 或 deployment 資料夾時，每個資料夾開頭都應延續同一個形式：先說明這類服務解決什麼問題，再比較同質服務的差異，最後才進入實作細節。

閱讀本模組前，建議先把 [前置知識卡片](../knowledge-cards/) 當成共同詞彙索引。選型文章會使用 [consumer lag](../knowledge-cards/consumer-lag/)、[dead-letter queue](../knowledge-cards/dead-letter-queue/)、[replay](../knowledge-cards/replay-runbook/)、[降級](../knowledge-cards/degradation/)、[停機](../knowledge-cards/downtime/)、[readiness](../knowledge-cards/readiness/) 等概念；這些概念的完整 domain knowhow 放在卡片中，章節本文則專注於需求判讀與服務能力取捨。

## 章節列表

| 章節                                          | 主題                             | 關鍵收穫                                                             |
| --------------------------------------------- | -------------------------------- | -------------------------------------------------------------------- |
| [0.0](backend-demand-taxonomy/)               | 後端需求分類地圖                 | 先把需求分成狀態、讀取、非同步、即時、診斷、交付與可靠性             |
| [0.1](service-capability-map/)                | 後端服務能力地圖                 | 用需求類型判斷該先看資料庫、快取、queue、觀測或部署平台              |
| [0.2](state-storage-selection/)               | 狀態與資料儲存選型               | 區分 [source of truth](../knowledge-cards/source-of-truth/)、快取、搜尋索引、[event log](../knowledge-cards/event-log/) 與 [object storage](../knowledge-cards/object-storage/)    |
| [0.3](async-delivery-selection/)              | 非同步與事件傳遞選型             | 區分背景工作、[durable queue](../knowledge-cards/durable-queue/)、stream、[pub/sub](../knowledge-cards/pub-sub/) 與 outbox               |
| [0.4](operations-platform-selection/)         | 操作平台選型                     | 區分 [log](../knowledge-cards/log/)、metric、[trace](../knowledge-cards/trace/)、[dashboard](../knowledge-cards/dashboard/)、[alert](../knowledge-cards/alert/)、deployment 與 reliability |
| [0.5](traffic-data-scale/)                    | 流量與資料量評估                 | 用 QPS、burst、[hot key](../knowledge-cards/hot-key/)、資料成長與保留期限評估需求規模               |
| [0.6](cost-risk-tradeoffs/)                   | 成本、風險與選型取捨             | 用人力成本、雲端成本、操作成本與失敗代價判斷投入順序                 |
| [0.7](failure-observability-design/)          | 錯誤定位、觀測訊號與備援切換設計 | 從錯誤分類、定位線索、降級與 [failover](../knowledge-cards/failover/) 設計服務可維護性               |
| [0.8](security-data-protection-requirements/) | 資安與資料保護需求               | 從權限分級、伺服器防護、資料遮罩、傳輸保護與稽核設計安全邊界         |
| [0.9](knowledge-graph-message-flow/)          | 知識網：訊息與事件決策路徑       | 用 [broker](../knowledge-cards/broker/)、queue、[ack](../knowledge-cards/ack-nack/)、retry、DLQ、replay 串出非同步決策脈絡         |
| [0.10](knowledge-graph-operations-security/)  | 知識網：容量、觀測與資安決策路徑 | 用 [backpressure](../knowledge-cards/backpressure/)、[timeout](../knowledge-cards/timeout/)、[runbook](../knowledge-cards/runbook/)、[RTO](../knowledge-cards/rto/)/[RPO](../knowledge-cards/rpo/)、權限與憑證串出操作脈絡   |
| [0.11](red-team-cross-service-weaknesses/)    | 攻擊者視角（紅隊）：跨服務弱點判讀總表     | 用攻擊面、可觀察訊號與失敗代價建立跨分類的弱點判讀順序 |

## 需求討論順序

後端選型討論的核心順序是先問「問題長什麼樣」，再問「哪種能力能解決」。討論一開始就跳到產品名稱，容易把資料庫、快取、queue、觀測平台或部署平台當成固定答案；比較穩定的做法是先確認下列五件事。

1. 需求類型：這是狀態保存、讀取加速、非同步處理、即時推送、診斷、交付，還是可靠性驗證問題？
2. 流量形狀：流量是穩定、尖峰、長尾、單一 hot key，還是週期性批次？
3. [資料生命週期](../knowledge-cards/data-lifecycle/)：資料是否長期存在、能否重建、是否需要 audit、保留多久？
4. 失敗代價：延遲、重複、遺失、短暫不一致、[停機](../knowledge-cards/downtime/)，各自會造成什麼產品後果？
5. 成本模型：目前瓶頸來自雲端費用、人力維護、事故風險、開發速度，還是操作複雜度？
6. 定位與備援：錯誤發生時能否分類、追蹤、[降級](../knowledge-cards/degradation/)、切換與恢復？
7. 安全邊界：誰能存取哪些資料、資料如何遮罩、傳輸如何保護、操作如何稽核？

這些問題回答清楚後，服務分類才會自然出現。正式狀態通常走向資料庫；重複讀取通常走向快取；request 外的可靠工作通常走向 queue 或 outbox；看不見系統行為通常走向 observability；部署與擴容不穩通常走向 platform；失敗前驗證不足通常走向 reliability pipeline。

## 選型文章的共同格式

每篇選型文章都使用同一個閱讀路徑：

1. **核心原則**：先說明這類服務解決哪一種工程問題。
2. **可觀察訊號**：列出怎麼從產品需求、流量型態或事故症狀辨識問題。
3. **現實例子**：用接近真實網路服務的例子建立判斷錨點。
4. **候選服務類型**：列出同質服務或相近能力的差異。
5. **成本權衡**：討論資安限制、流量穩定性、伺服器成本、人力成本與機會成本。
6. **下一步路由**：指向對應 backend 模組，實作細節放在後續章節。

本模組新增的需求分析章節會更早一層：它們負責討論「該問哪些問題」。服務分類章節則負責討論「問題落到哪種後端能力」。

## 服務實體的固定討論段落

服務實體章節的核心要求是每個選型都要回答「值得引入的理由」與「引入後的代價」。討論 PostgreSQL、Redis、RabbitMQ、Kafka、Prometheus、Kubernetes、[WAF](../knowledge-cards/waf/)、[IAM](../knowledge-cards/iam/)、[Secret Management](../knowledge-cards/secret-management/) 或任何具體服務時，都必須保留成本權衡段落。

這個段落要同時看五個方向：

1. **資安限制**：權限分級、資料遮罩、傳輸保護、密鑰管理、稽核與伺服器防護會增加哪些設計與操作要求。
2. **流量與穩定性**：尖峰、hot key、長連線、大量資料、重試風暴或下游失敗會讓服務承擔哪些容量壓力。
3. **伺服器與雲端成本**：儲存、運算、網路傳輸、保留期限、備援、跨區與觀測資料會如何增加成本。
4. **人力與操作成本**：維護、升級、監控、備份、演練、[on-call](../knowledge-cards/on-call/)、文件與事故處理需要誰負責。
5. **機會成本**：選擇完整平台會延後哪些產品工作；選擇簡單方案會留下哪些風險；哪些條件會讓團隊需要重新評估。

## 和語言教材的關係

語言教材負責教「如何隔離外部能力」。Backend 選型模組負責教「什麼能力值得被隔離」。例如 Go 章節會說明 repository port、publisher port、cache interface 與 observability boundary；本模組則說明何時需要資料庫、Redis、broker、OpenTelemetry 或部署平台能力。

## 本模組不處理

本模組只處理需求分析與選型入口。具體 SQL schema、Redis command、RabbitMQ exchange、Prometheus query、Kubernetes deployment 或 [chaos test](../knowledge-cards/chaos-test/) 設計，會放在後續對應模組中。

## 大綱待辦

這一節只記錄仍需要沿著原子卡原則拆出的概念，之後補卡、拆卡或新增卡都先回到這裡確認。

### 已完成拆分

- `endpoint`：service endpoint / public API endpoint / admin endpoint / diagnostic endpoint / internal endpoint
- `gateway`：API gateway / request routing
- `contract`：boundary contract / API contract / deployment contract / queue contract / load balancer contract
- `protocol`：communication protocol / request-response protocol / message protocol / webhook protocol
- `adapter`：integration adapter / repository adapter / provider adapter / notification adapter
- `middleware`：request middleware / authentication middleware / authorization middleware / observability middleware / security middleware / validation middleware

### 需要保留為議題入口的章節

- [0.0](backend-demand-taxonomy/) 後端需求分類地圖
- [0.1](service-capability-map/) 後端服務能力地圖
- [0.2](state-storage-selection/) 狀態與資料儲存選型
- [0.3](async-delivery-selection/) 非同步與事件傳遞選型
- [0.4](operations-platform-selection/) 操作平台選型
- [0.5](traffic-data-scale/) 流量與資料量評估
- [0.6](cost-risk-tradeoffs/) 成本、風險與選型取捨
- [0.7](failure-observability-design/) 錯誤定位、觀測訊號與備援切換設計
- [0.8](security-data-protection-requirements/) 資安與資料保護需求
- [0.9](knowledge-graph-message-flow/) 知識網：訊息與事件決策路徑
- [0.10](knowledge-graph-operations-security/) 知識網：容量、觀測與資安決策路徑
- [0.11](red-team-cross-service-weaknesses/) 攻擊者視角（紅隊）：跨服務弱點判讀總表
