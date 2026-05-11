---
title: "0.14 企業選型案例圖譜"
date: 2026-05-07
description: "蒐集不同類型與不同規模企業的技術選型案例，作為後端選型判讀的跨情境補充。"
weight: 14
tags: ["backend", "service-selection"]
---

企業選型案例圖譜的核心責任是提供「跨規模、跨產業、跨階段」的選型樣本，讓讀者知道同一種技術問題在不同公司會如何被定義、取捨與落地。

## 概念定位

這一頁不是工具排行榜，也不是成功故事清單。它的責任是回答三件事：這家公司遇到什麼壓力、做了什麼選型決策、代價與回寫是什麼。

使用方式是先從你的需求壓力切入，再對照對應案例，而不是先選喜歡的公司再倒推技術。這樣可以避免「抄架構」而忽略上下文差異。

## 使用方式

1. 先回到 [0.0 後端需求分類地圖](/backend/00-service-selection/backend-demand-taxonomy/) 定位你的問題類型。
2. 用本頁找 2 到 3 個不同規模企業的對照案例。
3. 把案例中的決策壓力回寫到 [0.6 成本、風險與選型取捨](/backend/00-service-selection/cost-risk-tradeoffs/)。
4. 再進入對應模組（01-08）看實作與控制面細節。

## 案例地圖

案例按照「企業型態 × 規模階段」分組，目的是讓你先找到最接近自己情境的壓力來源，再看選型動作。

| 企業型態與規模階段                 | 企業案例                                                                                                                                         | 主要選型問題                               | 優先回讀章節                                                                                                                           |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| SaaS（成長期，單體資料庫瓶頸）     | [Notion: Sharding Postgres](https://www.notion.com/blog/sharding-postgres-at-notion)                                                             | 單體 Postgres 何時拆分成分片架構           | [0.2](/backend/00-service-selection/state-storage-selection/)、[0.5](/backend/00-service-selection/traffic-data-scale/)                |
| DevTool（成長期，職能拆分）        | [GitLab: Splitting Main and CI DB](https://about.gitlab.com/blog/2022/06/02/splitting-database-into-main-and-ci/)                                | 功能分解如何換取容量與可靠性               | [0.2](/backend/00-service-selection/state-storage-selection/)、[0.6](/backend/00-service-selection/cost-risk-tradeoffs/)               |
| DevTool（成熟期，升級風險控制）    | [GitLab: Major PostgreSQL Upgrade](https://about.gitlab.com/blog/2020/09/11/gitlab-pg-upgrade/)                                                  | 高流量環境下升級策略與回退設計             | [0.7](/backend/00-service-selection/failure-observability-design/)、[06](/backend/06-reliability/)                                     |
| Commerce（高速成長，資料庫升級）   | [Shopify: Upgrading MySQL](https://shopify.engineering/upgrading-mysql-shopify)                                                                  | 大規模 MySQL 維運成本與可靠性治理          | [0.2](/backend/00-service-selection/state-storage-selection/)、[0.6](/backend/00-service-selection/cost-risk-tradeoffs/)               |
| Commerce（超大規模，水平擴充）     | [Shopify: Scaling with Vitess](https://shopify.engineering/blogs/engineering/horizontally-scaling-the-rails-backend-of-shop-app-with-vitess)     | 什麼時候引入 Vitess 以取得水平擴充能力     | [0.1](/backend/00-service-selection/service-capability-map/)、[0.5](/backend/00-service-selection/traffic-data-scale/)                 |
| Social / Chat（高吞吐事件流）      | [Slack: Scaling Job Queue](https://slack.engineering/scaling-slacks-job-queue/)                                                                  | 高吞吐背景工作為何改採 Kafka + Redis       | [0.3](/backend/00-service-selection/async-delivery-selection/)、[03](/backend/03-message-queue/)                                       |
| Social（超大規模，多租戶優先序）   | [Meta: FOQS Distributed Priority Queue](https://engineering.fb.com/2021/02/22/production-engineering/foqs-scaling-a-distributed-priority-queue/) | 多租戶 priority queue 如何做持久化與隔離   | [0.3](/backend/00-service-selection/async-delivery-selection/)、[0.6](/backend/00-service-selection/cost-risk-tradeoffs/)              |
| Ride-hailing（全球規模，監控平台） | [Uber: M3 Metrics Platform](https://www.uber.com/en-GB/blog/m3/)                                                                                 | 單點監控系統何時要走平台化與多租戶存儲     | [0.4](/backend/00-service-selection/operations-platform-selection/)、[04](/backend/04-observability/)                                  |
| CDN / Security（邊緣規模，可觀測） | [Cloudflare: Building Cloudflare on Cloudflare](https://blog.cloudflare.com/building-cloudflare-on-cloudflare/)                                  | logs/metrics/traces 如何一起成為操作能力   | [0.4](/backend/00-service-selection/operations-platform-selection/)、[4.20](/backend/04-observability/observability-evidence-package/) |
| Commerce（成熟期，韌性驗證）       | [Shopify: Effective Game Day Tests](https://shopify.engineering/four-steps-creating-effective-game-day-tests)                                    | 如何把演練從活動變成驗證制度               | [0.7](/backend/00-service-selection/failure-observability-design/)、[06](/backend/06-reliability/)                                     |
| Commerce（大促前容量治理）         | [Shopify: Resiliency Planning for High-Traffic Events](https://shopify.engineering/resiliency-planning-for-high-traffic-events)                  | 高峰活動前容量與風險如何建模               | [0.5](/backend/00-service-selection/traffic-data-scale/)、[6.9](/backend/06-reliability/capacity-cost/)                                |
| Cloud Platform（多租戶隔離）       | [AWS Builders’ Library: Shuffle-sharding](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)                    | 多租戶故障隔離如何影響資料與佇列設計       | [0.6](/backend/00-service-selection/cost-risk-tradeoffs/)、[0.7](/backend/00-service-selection/failure-observability-design/)          |
| Platform（組織擴張，邊界重整）     | [Uber: Domain-Oriented Microservice Architecture](https://www.uber.com/en-GB/blog/microservice-architecture/)                                    | 微服務規模變大後如何重新治理邊界與依賴     | [0.0](/backend/00-service-selection/backend-demand-taxonomy/)、[0.1](/backend/00-service-selection/service-capability-map/)            |
| Social（儲存成本壓力）             | [Meta: MyRocks](https://engineering.fb.com/2016/08/31/core-infra/myrocks-a-space-and-write-optimized-mysql-database/)                            | 何時用新 storage engine 換取成本與寫入效率 | [0.2](/backend/00-service-selection/state-storage-selection/)、[0.6](/backend/00-service-selection/cost-risk-tradeoffs/)               |
| Social（平台化分片）               | [Meta: Shard Manager](https://engineering.fb.com/2020/08/24/production-engineering/scaling-services-with-shard-manager/)                         | 分片能力何時應該平台化而不是各隊自建       | [0.1](/backend/00-service-selection/service-capability-map/)、[0.7](/backend/00-service-selection/failure-observability-design/)       |

## 類型覆蓋檢查

案例蒐集的完成條件不是篇數，而是覆蓋度。每次補案例都用這四個維度檢查缺口。

| 維度         | 已覆蓋示例                                                                  | 常見缺口                                 |
| ------------ | --------------------------------------------------------------------------- | ---------------------------------------- |
| 企業型態     | SaaS、DevTool、Commerce、Social、Ride-hailing、Cloud Platform、CDN/Security | FinTech、Gaming、Healthcare、製造業平台  |
| 規模階段     | 成長期、成熟期、超大規模                                                    | 早期產品（小團隊）與跨國多區治理         |
| 選型問題類型 | 資料分片、佇列架構、可觀測平台、容量韌性、多租戶隔離、組織邊界              | 成本治理、合規（PCI/SOX/GDPR）與資料主權 |
| 決策生命週期 | 遷移、升級、平台化、演練                                                    | 退場策略（decommission）與 vendor 轉移   |

## 第一批缺口回填清單

第一批回填先補三個目前缺口最大的產業類型，目標是讓案例圖譜從「網路平台公司視角」擴展到「高合規與高事件密度」場景。

| 缺口類型   | 優先蒐集的選型議題                                 | 回寫章節起點                                                                                                                               |
| ---------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| FinTech    | 合規壓力下的資料分區、審計留存、變更放行與風險隔離 | [0.6](/backend/00-service-selection/cost-risk-tradeoffs/)、[0.8](/backend/00-service-selection/security-data-protection-requirements/)     |
| Gaming     | 高峰事件流、低延遲路徑、規則推送風險與跨區回復     | [0.3](/backend/00-service-selection/async-delivery-selection/)、[0.5](/backend/00-service-selection/traffic-data-scale/)                   |
| Healthcare | 資料主權、存取邊界、可追溯性與災難回復流程         | [0.2](/backend/00-service-selection/state-storage-selection/)、[0.8](/backend/00-service-selection/security-data-protection-requirements/) |

這份清單的用途是定義下一輪蒐集方向。每補一個案例，至少要同步回寫一個 04 觀測章節、一個 06 驗證章節與一個 08 事故章節，避免案例只停留在選型敘事。

## 第一批案例清單（FinTech / Gaming / Healthcare）

第一批案例的責任是先補齊產業覆蓋，並建立可直接回寫到 04/06/08 的共同語言。

| 類型       | 企業案例                                                                                                      | 主要選型問題                             | 優先回讀章節                                                                                                                                    |
| ---------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| FinTech    | [Stripe: Scaling Payments APIs](https://stripe.com/blog)                                                      | 金流 API 的一致性、冪等與放行門檻        | [0.2](/backend/00-service-selection/state-storage-selection/)、[0.6](/backend/00-service-selection/cost-risk-tradeoffs/)                        |
| FinTech    | [Adyen Engineering](https://www.adyen.com/knowledge-hub)                                                      | 合規要求下的資料保留、稽核追溯與跨區部署 | [0.8](/backend/00-service-selection/security-data-protection-requirements/)、[0.7](/backend/00-service-selection/failure-observability-design/) |
| Gaming     | [Riot Games Tech Blog](https://technology.riotgames.com/)                                                     | 高峰活動期間的低延遲路徑與跨區容量治理   | [0.5](/backend/00-service-selection/traffic-data-scale/)、[0.3](/backend/00-service-selection/async-delivery-selection/)                        |
| Gaming     | [Epic Games Unreal Engine / Fortnite Scale Articles](https://dev.epicgames.com/community/)                    | 大型即時服務的事件流、匹配與故障隔離     | [0.3](/backend/00-service-selection/async-delivery-selection/)、[0.6](/backend/00-service-selection/cost-risk-tradeoffs/)                       |
| Healthcare | [Google Cloud Healthcare Architecture Guides](https://cloud.google.com/architecture/healthcare-life-sciences) | 資料主權、存取邊界與審計證據鏈           | [0.8](/backend/00-service-selection/security-data-protection-requirements/)、[0.2](/backend/00-service-selection/state-storage-selection/)      |
| Healthcare | [AWS Healthcare and Life Sciences Architecture](https://aws.amazon.com/health/)                               | 多區備援下的資料保護與恢復順序           | [0.7](/backend/00-service-selection/failure-observability-design/)、[0.8](/backend/00-service-selection/security-data-protection-requirements/) |

這批案例以「產業壓力類型」為主，不以單一公司唯一做法當標準答案。後續第二批再補製造業平台與跨國多區治理案例。

## 對應正文入口

第一批缺口已補對應正文，圖譜可直接連到可回寫文章：

| 類型       | 正文入口                                                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------------------------------------ |
| FinTech    | [0.C1 FinTech：合規壓力下的後端選型](/backend/00-service-selection/cases/fintech-compliance-and-selection-pressure/)     |
| Gaming     | [0.C2 Gaming：高峰流量與隔離邊界選型](/backend/00-service-selection/cases/gaming-peak-traffic-and-isolation/)            |
| Healthcare | [0.C3 Healthcare：資料主權與回復順序選型](/backend/00-service-selection/cases/healthcare-data-sovereignty-and-recovery/) |

營運一段時間後的語言、工具或架構轉換案例，見 [0.C4 營運後技術轉換](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/)。

## 讀法提醒

同一家公司不代表同一答案。公司不同時期的選型結論可能相反，因為負載、組織、預算與產品階段已經改變。把案例當成「決策壓力樣本」，比當成「標準答案」更可靠。

當兩個案例做出不同選擇，先檢查四件事：流量形狀、資料生命週期、失敗代價、維運能力。這四件事通常比語言與框架更能解釋選型差異。
