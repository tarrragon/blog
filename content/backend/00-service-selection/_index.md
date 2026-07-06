---
title: "模組零：後端服務選型"
date: 2026-04-23
description: "從需求類型判斷資料庫、快取、訊息佇列、觀測與部署平台的選型方向"
weight: 0
tags: ["backend", "service-selection"]
---

後端服務選型的核心目標是把「需求類型」轉成「服務能力」。資料庫、快取、訊息佇列、觀測平台與部署平台都能提升系統能力，但它們解決的是不同問題；選型時要先辨識需求、流量、資料量、失敗代價與成本模型，再進入具體產品比較。

進入需求分類之前、先確認一個更早的判斷：**這個服務值得自建嗎**。差異化在商品、內容或服務品質、需求落在 Wix / Shopify、Google Apps Script、Firebase、WordPress 這類現成平台標準域的業務、託管形態可能是成本上更誠實的起點；判讀方式與可遷出保險見 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/)、日後升級自建 tripwire 觸發的遷出執行見 [10.3 託管形態遷出](/backend/10-system-evolution/managed-platform-exit/)。本模組其餘章節預設自建已成立。

如果你連「把服務放上線」都還沒做過，這個模組的選型理論會太高——先走 [服務上線的業界常識地基](/going-live/) 建立部署、主機、域名、備份的地基，再回來做選型。

本模組先建立跨分類的選型語言。後續進入 [database](/backend/knowledge-cards/database/)、Redis、message [queue](/backend/knowledge-cards/queue/)、observability 或 deployment 資料夾時，每個資料夾開頭都應延續同一個形式：先說明這類服務解決什麼問題，再比較同質服務的差異，最後才進入實作細節。

閱讀本模組前，建議先把 [前置知識卡片](/backend/knowledge-cards/) 當成共同詞彙索引。選型文章會使用 [consumer lag](/backend/knowledge-cards/consumer-lag/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)、[replay](/backend/knowledge-cards/replay-runbook/)、[降級](/backend/knowledge-cards/degradation/)、[停機](/backend/knowledge-cards/downtime/)、[readiness](/backend/knowledge-cards/readiness/) 等概念；這些概念的完整 domain knowhow 放在卡片中，章節本文則專注於需求判讀與服務能力取捨。

## 章節列表

| 章節                                                                        | 主題                                   | 關鍵收穫                                                                                                                                                                                                                                                 |
| --------------------------------------------------------------------------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [0.0](/backend/00-service-selection/backend-demand-taxonomy/)               | 後端需求分類地圖                       | 先把需求分成狀態、讀取、非同步、即時、診斷、交付與可靠性                                                                                                                                                                                                 |
| [0.1](/backend/00-service-selection/service-capability-map/)                | 後端服務能力地圖                       | 用需求類型判斷該先看資料庫、快取、queue、觀測或部署平台                                                                                                                                                                                                  |
| [0.2](/backend/00-service-selection/state-storage-selection/)               | 狀態與資料儲存選型                     | 區分 [source of truth](/backend/knowledge-cards/source-of-truth/)、快取、搜尋索引、[event log](/backend/knowledge-cards/event-log/) 與 [object storage](/backend/knowledge-cards/object-storage/)                                                        |
| [0.3](/backend/00-service-selection/async-delivery-selection/)              | 非同步與事件傳遞選型                   | 區分背景工作、[durable queue](/backend/knowledge-cards/durable-queue/)、stream、[pub/sub](/backend/knowledge-cards/pub-sub/) 與 outbox                                                                                                                   |
| [0.4](/backend/00-service-selection/operations-platform-selection/)         | 操作平台選型                           | 區分 [log](/backend/knowledge-cards/log/)、metric、[trace](/backend/knowledge-cards/trace/)、[dashboard](/backend/knowledge-cards/dashboard/)、[alert](/backend/knowledge-cards/alert/)、deployment 與 reliability                                       |
| [0.5](/backend/00-service-selection/traffic-data-scale/)                    | 流量與資料量評估                       | 用 QPS、burst、[hot key](/backend/knowledge-cards/hot-key/)、資料成長與保留期限評估需求規模                                                                                                                                                              |
| [0.6](/backend/00-service-selection/cost-risk-tradeoffs/)                   | 成本、風險與選型取捨                   | 用人力成本、雲端成本、操作成本與失敗代價判斷投入順序                                                                                                                                                                                                     |
| [0.7](/backend/00-service-selection/failure-observability-design/)          | 錯誤定位、觀測訊號與備援切換設計       | 從錯誤分類、定位線索、降級與 [failover](/backend/knowledge-cards/failover/) 設計服務可維護性                                                                                                                                                             |
| [0.8](/backend/00-service-selection/security-data-protection-requirements/) | 資安與資料保護需求                     | 從權限分級、伺服器防護、資料遮罩、傳輸保護與稽核設計安全邊界                                                                                                                                                                                             |
| [0.9](/backend/00-service-selection/knowledge-graph-message-flow/)          | 知識網：訊息與事件決策路徑             | 用 [broker](/backend/knowledge-cards/broker/)、queue、[ack](/backend/knowledge-cards/ack-nack/)、retry、DLQ、replay 串出非同步決策脈絡                                                                                                                   |
| [0.10](/backend/00-service-selection/knowledge-graph-operations-security/)  | 知識網：容量、觀測與資安決策路徑       | 用 [backpressure](/backend/knowledge-cards/backpressure/)、[timeout](/backend/knowledge-cards/timeout/)、[runbook](/backend/knowledge-cards/runbook/)、[RTO](/backend/knowledge-cards/rto/)/[RPO](/backend/knowledge-cards/rpo/)、權限與憑證串出操作脈絡 |
| [0.11](/backend/00-service-selection/red-team-cross-service-weaknesses/)    | 攻擊者視角（紅隊）：跨服務弱點判讀總表 | 用攻擊面、可觀察訊號與失敗代價建立跨分類的弱點判讀順序                                                                                                                                                                                                   |
| [0.12](/backend/00-service-selection/operations-control-service-selection/) | 觀測、可靠性與事故服務選型             | 用訊號、驗證、響應與閉環四層能力判斷操作控制服務該如何選型                                                                                                                                                                                               |
| [0.13](/backend/00-service-selection/operations-control-vertical-slice/)    | 操作控制 vertical slice 實作入口       | 用一個服務串起 evidence package、verification handoff、decision log 與 write-back                                                                                                                                                                        |
| [0.14](/backend/00-service-selection/enterprise-selection-case-atlas/)      | 企業選型案例圖譜                       | 以企業型態與規模階段分組案例，建立跨產業、跨規模的選型壓力對照                                                                                                                                                                                           |
| [0.15](/backend/00-service-selection/cross-module-checkout-episode/)        | 跨模組 Checkout Episode                | 用一條 checkout 路徑走完 DB write → cache invalidation → event publish → observability evidence 四層串聯                                                                                                                                                 |
| [0.19](/backend/00-service-selection/cloud-vendor-capability-mapping/)      | 雲端服務對照地圖（AWS / GCP / Azure）  | 後端能力分類對照三家雲廠商、failover / 一致性 / 計價差異、跨雲遷移判讀                                                                                                                                                                                   |
| [0.21](/backend/00-service-selection/delivery-mode-selection/)              | 交付形態選型：託管平台、BaaS 與自建    | 在自建選型之前先判斷該用 Wix / Shopify、Apps Script、Firebase、WordPress 還是自建、並保留可遷出路徑與升級 tripwire                                                                                                                                       |
| [0.22](/backend/00-service-selection/capability-buy-vs-build/)              | 能力級買 vs 建：feature-as-a-service   | 自建核心成立後、逐能力判斷外包還是自建：三種外包深度、no-code 到 dev-tool 光譜、買 vs 建判準與整合接縫成本                                                                                                                                               |

服務拆分判讀（原 0.18）與執行 Runbook（原 0.20）已移到 [模組十：系統演進與遷移](/backend/10-system-evolution/) — 設計階段的選型判讀留本模組、執行階段的高風險變更收斂到模組十。

## 需求討論順序

這個討論順序預設自建已成立；交付形態的判讀見本頁開頭的分流與 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/)。

後端選型討論的核心順序是先問「問題長什麼樣」，再問「哪種能力能解決」。討論一開始就跳到產品名稱，容易把資料庫、快取、queue、觀測平台或部署平台當成固定答案；比較穩定的做法是先確認下列事項。

1. 需求類型：這是狀態保存、讀取加速、非同步處理、即時推送、診斷、交付，還是可靠性驗證問題？
2. 流量形狀：流量是穩定、尖峰、長尾、單一 hot key，還是週期性批次？
3. [資料生命週期](/backend/knowledge-cards/data-lifecycle/)：資料是否長期存在、能否重建、是否需要 audit、保留多久？
4. 失敗代價：延遲、重複、遺失、短暫不一致、[停機](/backend/knowledge-cards/downtime/)，各自會造成什麼產品後果？
5. 成本模型：目前瓶頸來自雲端費用、人力維護、事故風險、開發速度，還是操作複雜度？
6. 定位與備援：錯誤發生時能否分類、追蹤、[降級](/backend/knowledge-cards/degradation/)、切換與恢復？
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

服務實體章節的核心要求是每個選型都要回答「值得引入的理由」與「引入後的代價」。討論 PostgreSQL、Redis、RabbitMQ、Kafka、Prometheus、Kubernetes、[WAF](/backend/knowledge-cards/waf/)、[IAM](/backend/knowledge-cards/iam/)、[Secret Management](/backend/knowledge-cards/secret-management/) 或任何具體服務時，都必須保留成本權衡段落。

這個段落要同時看五個方向：

1. **資安限制**：權限分級、資料遮罩、傳輸保護、密鑰管理、稽核與伺服器防護會增加哪些設計與操作要求。
2. **流量與穩定性**：尖峰、hot key、長連線、大量資料、重試風暴或下游失敗會讓服務承擔哪些容量壓力。
3. **伺服器與雲端成本**：儲存、運算、網路傳輸、保留期限、備援、跨區與觀測資料會如何增加成本。
4. **人力與操作成本**：維護、升級、監控、備份、演練、[on-call](/backend/knowledge-cards/on-call/)、文件與事故處理需要誰負責。
5. **機會成本**：選擇完整平台會延後哪些產品工作；選擇簡單方案會留下哪些風險；哪些條件會讓團隊需要重新評估。

## 和語言教材的關係

語言教材負責教「如何隔離外部能力」。Backend 選型模組負責教「什麼能力值得被隔離」。例如 Go 章節會說明 repository port、publisher port、cache interface 與 observability boundary；本模組則說明何時需要資料庫、Redis、broker、OpenTelemetry 或部署平台能力。

## 企業選型案例補充

模組零的案例補充重點是「企業如何說明選型取捨」。閱讀時先抓它在解什麼需求壓力，再對照本模組的需求分類與成本取捨章節。

| 企業案例                                                                                                                                                                       | 主要選型問題                             | 優先回讀章節                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| [Herding elephants: Lessons learned from sharding Postgres at Notion](https://www.notion.com/blog/sharding-postgres-at-notion)                                                 | 單體資料庫何時需要走向分片               | [0.2](/backend/00-service-selection/state-storage-selection/)、[0.5](/backend/00-service-selection/traffic-data-scale/)       |
| [Horizontally scaling the Rails backend of Shop app with Vitess](https://shopify.engineering/blogs/engineering/horizontally-scaling-the-rails-backend-of-shop-app-with-vitess) | MySQL 生態下何時改走 Vitess              | [0.1](/backend/00-service-selection/service-capability-map/)、[0.6](/backend/00-service-selection/cost-risk-tradeoffs/)       |
| [How Discord Stores Trillions of Messages](https://discord.com/blog/how-discord-stores-trillions-of-messages)                                                                  | 儲存引擎選型如何隨成長重評               | [0.2](/backend/00-service-selection/state-storage-selection/)、[0.6](/backend/00-service-selection/cost-risk-tradeoffs/)      |
| [Introducing Domain-Oriented Microservice Architecture](https://www.uber.com/en-GB/blog/microservice-architecture/)                                                            | 微服務邊界與複雜度治理如何重新切分       | [0.0](/backend/00-service-selection/backend-demand-taxonomy/)、[0.1](/backend/00-service-selection/service-capability-map/)   |
| [Workload isolation using shuffle-sharding](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)                                                | 多租戶隔離與 blast radius 如何進選型決策 | [0.6](/backend/00-service-selection/cost-risk-tradeoffs/)、[0.7](/backend/00-service-selection/failure-observability-design/) |

若要做「跨產業 × 跨規模」的系統化案例蒐集與回寫，直接使用 [0.14 企業選型案例圖譜](/backend/00-service-selection/enterprise-selection-case-atlas/)；該章節提供分組後案例地圖與覆蓋缺口檢查表，可直接當後續補強 backlog。

## 本模組不處理

本模組只處理需求分析與選型入口。具體 SQL schema、Redis command、RabbitMQ exchange、Prometheus query、Kubernetes deployment 或 [chaos test](/backend/knowledge-cards/chaos-test/) 設計，會放在後續對應模組中。

## 實作探討入口

當你準備從概念層切到實作層，建議先選一條單一業務路徑做最小切片，並同時建立三個 artifact：

1. 觀測證據： [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
2. 驗證證據： [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)
3. 事故決策： [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)

這三個 artifact 先接起來，再補該路徑的 DB、cache、queue、deployment 細節，實作討論會更穩定，也更容易做跨模組回寫。

完整撰寫順序與服務路徑選擇依 [Backend 學習路線](/backend/#學習路線) 安排。

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

- [0.0](/backend/00-service-selection/backend-demand-taxonomy/) 後端需求分類地圖
- [0.1](/backend/00-service-selection/service-capability-map/) 後端服務能力地圖
- [0.2](/backend/00-service-selection/state-storage-selection/) 狀態與資料儲存選型
- [0.3](/backend/00-service-selection/async-delivery-selection/) 非同步與事件傳遞選型
- [0.4](/backend/00-service-selection/operations-platform-selection/) 操作平台選型
- [0.5](/backend/00-service-selection/traffic-data-scale/) 流量與資料量評估
- [0.6](/backend/00-service-selection/cost-risk-tradeoffs/) 成本、風險與選型取捨
- [0.7](/backend/00-service-selection/failure-observability-design/) 錯誤定位、觀測訊號與備援切換設計
- [0.8](/backend/00-service-selection/security-data-protection-requirements/) 資安與資料保護需求
- [0.9](/backend/00-service-selection/knowledge-graph-message-flow/) 知識網：訊息與事件決策路徑
- [0.10](/backend/00-service-selection/knowledge-graph-operations-security/) 知識網：容量、觀測與資安決策路徑
- [0.11](/backend/00-service-selection/red-team-cross-service-weaknesses/) 攻擊者視角（紅隊）：跨服務弱點判讀總表
- [0.12](/backend/00-service-selection/operations-control-service-selection/) 觀測、可靠性與事故服務選型
- [0.13](/backend/00-service-selection/operations-control-vertical-slice/) 操作控制 vertical slice 實作入口
- [0.14](/backend/00-service-selection/enterprise-selection-case-atlas/) 企業選型案例圖譜
- [0.19](/backend/00-service-selection/cloud-vendor-capability-mapping/) 雲端服務對照地圖（AWS / GCP / Azure）
