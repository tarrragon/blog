---
title: "服務從能跑到能撐，每一次架構調整都由一個撞牆訊號觸發"
date: 2026-09-24
description: "一個服務從一臺機器演進到多區域多服務的過程裡常見的撞牆訊號、每個訊號對應要補的能力與章節，以及入門影片常用的比喻各對應到哪一篇"
weight: 2
tags: ["backend", "scaling", "reading-path", "capacity"]
---

這篇整理一個已經能跑的服務，在流量與業務長大之後會依序撞上哪些限制、每一種限制要補哪一塊能力，以及 Backend 教材裡對應的章節。範圍從一臺機器開始，到多區域、多服務為止；還沒把服務做出來的讀者，先走[閱讀路線](/backend/reading-paths/)裡「沒部署過服務」或「API 到資料流」那兩條。

## 架構調整的時機由撞牆訊號決定

服務的架構會長出新的部分，是因為現有的形狀承受不了某一種壓力，而那種壓力在監控或使用者回報裡有一個可辨認的樣子：單一服務承載不了業務分化、單機規格撞到天花板、應用層的查詢變慢、單一資料庫成為瓶頸、源站被流量打爆、同步呼叫卡住整條交易流程、可預期的活動高峰需要事前準備。

所以這一組章節的讀法是**先認出手上是哪一種訊號，再讀那一種訊號對應的能力**，而不是照模組編號順讀。同一個訊號過早處理，付的是用不到的複雜度；過晚處理，付的是事故。

這條路線和閱讀路線裡的「API 到資料流」分工不同：那一條教怎麼把功能做出來，這一條教做出來之後怎麼撐住。兩條可以分開讀，也可以寫完第一個 MVP 之後回到這一篇盤點。MVP 如果是用託管平台或 BaaS 做的，先用 [0.21 交付形態選型：從全託管到自建的光譜與邊界](/backend/00-service-selection/delivery-mode-selection/) 的升級自建 tripwire 判斷該不該啟動自建評估；評估成立的話，遷出的執行在 [10.3 託管形態遷出：資產線盤點與並行期執行](/backend/10-system-evolution/managed-platform-exit/)，遷入之後再照下面的訊號走。

## 撞牆訊號與要補的能力

| 撞牆訊號                                 | 要補的能力                                             | 對應章節                                                                                                                                         |
| ---------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 一臺機器的 CPU 或記憶體吃滿              | 評估垂直或水平擴展，確認服務是 stateless               | [9.13 擴展軸與 Stateless 前提](/backend/09-performance-capacity/scaling-axes/)                                                                   |
| 資料庫變慢，加機器看起來只是暫時止血     | 先用查詢反模式清單收回單機容量，再考慮升級規格或換服務 | [1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)                                                                  |
| 資料庫寫入正常，但讀取把主庫壓垮         | 開 read replica，應用層配讀寫路由，並加快取            | [1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/)、[2.2 cache aside 與失效策略](/backend/02-cache-redis/cache-aside/) |
| 活動或引流時，源站被靜態資源請求打爆     | 把靜態與半靜態內容放到邊緣層，保護源站                 | [5.9 邊緣分發與靜態資源（CDN / Origin Protection）](/backend/05-deployment-platform/edge-cdn-static-distribution/)                               |
| 同步呼叫卡住交易流程，付款與通知互相阻塞 | 拆成事件、非同步化，加上冪等                           | [訊息佇列與事件傳遞模組](/backend/03-message-queue/)                                                                                             |
| 業務分化，團隊之間的發版互相阻擋         | 沿真實的邊界拆服務（資料、團隊、部署或流量）           | [10.1 服務拆分與邊界判讀](/backend/10-system-evolution/service-decomposition-boundaries/)                                                        |

表格由上往下大致是一個服務撞到這些訊號的常見先後，而先後不是固定的：有的團隊在單機容量用完之前就先拆服務，有的團隊一直不需要拆。源站被打爆之後如果還要應付可預期的活動高峰（雙 11、新片上線、推廣活動），加讀 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)；平日的容量規劃在 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。

## 從頭讀的順序

要把整條路線從頭讀一次，順序是：[0.21 交付形態選型：從全託管到自建的光譜與邊界](/backend/00-service-selection/delivery-mode-selection/)的升級 tripwire → [0.0 後端需求分類地圖](/backend/00-service-selection/backend-demand-taxonomy/) → [10.3 託管形態遷出：資產線盤點與並行期執行](/backend/10-system-evolution/managed-platform-exit/)（從託管平台出身的服務才需要）→ [10.1 服務拆分與邊界判讀](/backend/10-system-evolution/service-decomposition-boundaries/) → [9.13 擴展軸與 Stateless 前提](/backend/09-performance-capacity/scaling-axes/) → [1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/) → [1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/) → [2.2 cache aside 與失效策略](/backend/02-cache-redis/cache-aside/) → [5.9 邊緣分發與靜態資源（CDN / Origin Protection）](/backend/05-deployment-platform/edge-cdn-static-distribution/) → [訊息佇列與事件傳遞模組](/backend/03-message-queue/) → [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)。

這個順序把判斷放在動手之前：先確認要不要自建、需求屬於哪一類、邊界在哪裡，再依擴展、查詢、讀取、邊緣、非同步、高峰的次序補能力。各篇結尾的「規模成長路線下一站」指的就是這個順序裡的下一篇。

## 入門影片的比喻對應到哪一篇

講 SaaS 擴展的入門影片常用生活比喻解釋這些概念（把快取說成保溫桶、把 CDN 說成物料配送）。比喻傳達的是形狀，操作時需要的是工程術語與判斷條件，下表把常見的影片用詞接到對應的章節：

| 影片用詞                   | 對應章節                                                                                                                                                                                |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scale up / Scale out       | [9.13 擴展軸與 Stateless 前提](/backend/09-performance-capacity/scaling-axes/)                                                                                                          |
| CDN、邊緣節點、物料配送    | [5.9 邊緣分發與靜態資源（CDN / Origin Protection）](/backend/05-deployment-platform/edge-cdn-static-distribution/)                                                                      |
| 微服務、拆分               | [10.1 服務拆分與邊界判讀](/backend/10-system-evolution/service-decomposition-boundaries/)                                                                                               |
| Read replica、主從複製     | [1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/)，以及 [9.13 擴展軸與 Stateless 前提](/backend/09-performance-capacity/scaling-axes/)裡講有狀態服務的那一段 |
| 快取、保溫桶               | [快取與 Redis 模組](/backend/02-cache-redis/)                                                                                                                                           |
| Queue、Rate limiter        | [訊息佇列與事件傳遞模組](/backend/03-message-queue/)、[9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)                                                       |
| 索引、N+1、倉庫整理        | [1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)                                                                                                         |
| 雲端服務（RDS / ECS / S3） | [0.19 雲端服務對照地圖（AWS / GCP / Azure）](/backend/00-service-selection/cloud-vendor-capability-mapping/)                                                                            |
