---
title: "0.18 服務拆分與邊界判讀"
date: 2026-05-27
description: "整理 monolith vs microservice 取捨、服務邊界判讀訊號、拆分時機與回退路徑"
weight: 18
tags: ["backend", "service-selection", "microservice", "architecture"]
---

Monolith 與 microservice 是兩種耦合策略、各自承擔代價：monolith 用單一程式碼庫換低協作成本、microservice 用獨立邊界換團隊與部署彈性。本章處理「演進速度跟組織能力對齊」這個決策邊界 — 起點是辨識當下壓力來源、再選擇拆分軸、流行度與堅持習慣都是次要訊號。

## Monolith 與 Microservice 的責任差異

Monolith 用「同一個程式碼庫、同一個部署單位、同一個資料庫」換取低協作成本與簡單事務語意。Microservice 用「獨立程式碼庫、獨立部署、獨立資料邊界」換取團隊獨立性、技術選型彈性與局部故障隔離。

| 維度       | Monolith                     | Microservice                                                                                                       |
| ---------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 變更速度   | 單庫改完直接上線             | 跨服務協調，需要契約對齊                                                                                           |
| 事務一致性 | 本地 transaction 就解決      | 跨服務需要 [saga](/backend/knowledge-cards/saga/)、[outbox](/backend/knowledge-cards/outbox-pattern/) 或最終一致性 |
| 故障隔離   | 單點失敗會整個服務掛掉       | 一個服務掛了，其他可能還能服務                                                                                     |
| 部署單位   | 整個應用一次部署             | 各服務獨立部署，發布節奏不互相阻擋                                                                                 |
| 運維複雜度 | 一組基礎設施                 | N 組基礎設施 + 服務間通訊監控                                                                                      |
| Debug 路徑 | 同一個 stack trace 看到底    | 跨服務 trace context、log 聚合不可省                                                                               |
| 適合規模   | 早期、單一團隊、業務尚未分化 | 多團隊、業務已分化、可獨立演進                                                                                     |

讀者要從這張表反推自己的真實壓力來源。如果痛點是「部署互相卡住、發布頻率被別人拖慢」，拆分能解決；如果痛點是「程式碼太亂、新人看不懂」，拆服務只會把亂的範圍擴大成跨服務契約混亂。

這張表是兩端對比、實際系統常落在中間。常見折衷形態：

- **[Modular monolith](/backend/knowledge-cards/modular-monolith/)**（單一部署 + 模組化邊界）：保留 monolith 的部署簡單、用模組邊界防止程式碼互相穿透。Shopify、Basecamp、Stack Overflow 是大規模長期維持的代表 — monolith 不是進化中段、是 valid endgame。
- **Macro-services**（少量大服務、5-15 個）：避免 microservice 的極端碎片化、保留拆分帶來的部署獨立性。是多數中型團隊的實際終點、不是過渡形態。
- **[Cell-based architecture](/backend/knowledge-cards/cell-based-architecture/)**（多 cell 各自獨立、跨 cell 共用標準介面）：AWS、Slack、DoorDash 用來控制 blast radius — 把整個系統複製成多個 isolated cell、每個 cell 內可以是 monolith 或 microservice。

拆分不是進化方向、是壓力應對工具。維持 monolith 在某些情境（極小團隊、PMF 前期、無 DevOps 能力）是更負責任的選擇。

## 拆分軸的判讀

服務邊界不只一條軸。常見的四條軸對應不同的壓力來源，正確的拆法是「壓力在哪裡、就沿那條軸拆」，不是同時動四條軸。

### 資料邊界

當兩塊業務的資料**生命週期不同、一致性需求不同、查詢模式不同**時，資料邊界已經形成。例如訂單資料需要強一致性與長期保留，瀏覽紀錄可以最終一致性、定期清理。把這兩類資料放同一個 schema 會讓 backup、migration、index 策略互相干擾。

判讀訊號：同一張表上不同欄位的 read/write QPS 差三個數量級、同一個 transaction 同時寫入多種業務概念、schema migration 一動就要鎖住整個業務的寫入。

### 團隊邊界

當兩塊業務由不同團隊維護、發布節奏不同、技術棧偏好不同時，團隊邊界已經形成。Conway's Law 反過來操作：用服務邊界保護團隊邊界，避免一隊改動觸發另一隊重 review。

判讀訊號：PR review 跨團隊比例過半、發版需要協調多個團隊、技術升級（語言版本、framework 升級）因為其他團隊未準備好而被擋住。

### 部署邊界

當部分功能需要**獨立的部署節奏、獨立的擴展策略、獨立的可用性等級**時，部署邊界已經形成。背景批次工作要按小時排程、API 服務要 7×24 線上、報表服務只在工作日運行，三者放同一個部署單位會讓最嚴格的可用性要求拖累其他。

判讀訊號：高峰時某個功能擴展速度跟不上、低峰時某個功能浪費資源、單一發版策略覆蓋不了所有功能的風險等級。

### 流量邊界

當不同功能的**流量形狀、失敗代價、SLO 等級不同**時，流量邊界已經形成。付款 API 一秒 100 個請求、商品搜尋一秒 10000 個請求、後台報表一天 100 個請求，三者放同一個服務會讓彼此爭資源，付款被搜尋擠掉是業務災難。

判讀訊號：高頻 endpoint 壓爆低頻 endpoint 共用的連線池、不同 endpoint 的 latency 分布同時惡化、無法針對核心交易設定獨立的 SLO 跟 alert。

### 其他常見拆分軸

上面四條是技術驅動的主要拆分軸。實務上還有其他軸常成為真實驅動力、要一併納入判讀：

- **失敗代價 / blast radius 軸**：核心交易（掛了會有業務災難）跟邊緣推薦（掛了沒人在意）的可用性等級差距大、適合拆開降低 blast radius。跟 SLO 軸高相關但不同 — 重點在「失敗時誰受影響」的範圍隔離。
- **變更頻率 / 風險軸**：high-velocity 實驗功能跟 stable 核心應拆開、降低實驗對核心穩定性的牽連。跟團隊軸高相關但獨立 — 同一團隊也可能維持兩種變更頻率的程式碼。
- **資料敏感度 / 合規邊界**：PCI / PII / 醫療資料的隔離常是合規硬要求（GDPR data residency 強制資料拆境），不是技術選擇。這類軸跟資料邊界相關但服從不同壓力。
- **組織非技術約束**：併購整合、外部合規節奏、團隊 reorg、預算切分都會強制拆分 — 比 metric 訊號更早觸發、技術上不一定最佳但無法繞過。

這些軸跟前四條可以同時生效、也可能彼此衝突（合規逼資料拆境、但流量軸建議聚合）。處理衝突時優先順序通常是「合規 > 失敗代價 > 部署 / 流量 > 團隊 > 資料 > 變更頻率」、但每個組織會有自己的權重。

## 拆分時機的判讀

拆分時機不能等到「已經痛到動不了」才開始，那時候拆分要付的代價最高。也不能在「還沒長出邊界」時提早拆，那會用 microservice 的協調成本懲罰一個還沒到規模的系統。

提早訊號（可以開始準備但不一定立刻動手）：

- 程式碼裡同一份邏輯被三個 PR 同時修改、merge conflict 增加
- 同一個 service 的不同功能開始有不同的擴展需求
- 不同團隊對同一個發版視窗的需求開始衝突

該動手訊號（再拖就要付高昂代價）：

- 任何一個功能改動需要 freeze 整個服務發版
- 局部高峰擴展時整個服務一起擴展，成本翻倍
- 一個團隊的事故會直接影響另一個團隊的營運指標
- 跨團隊 deadlock：A 等 B 改完才能上、B 等 A 改完才能上

過晚訊號（拆分要付遷移代價）：

- 已經出現過跨團隊事故、且復盤結論是「無法分離責任」
- DB 連線池在多個業務間爭搶、無法用 connection pool 隔離解決
- 部署平台跑不動：CI 太慢、build 太大、本地開發無法啟動完整環境

## 拆分代價與回退路徑

拆分不是免費操作。每多一個服務，就多一份運維成本、跨服務 trace 成本、契約治理成本。讀者要在拆分前認知這些代價，而不是事後才發現。

| 代價類型     | 具體表現                                          | 緩解方向                                                                                                       |
| ------------ | ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 分散事務     | 一筆業務動作跨多個服務、需要 saga 或最終一致性    | [03 message queue](/backend/03-message-queue/) 的 outbox、[idempotency](/backend/knowledge-cards/idempotency/) |
| 運維複雜度   | N 個服務 × M 個環境 × K 個版本，組合爆炸          | 收斂部署平台、用 [5.2 K8s 部署策略](/backend/05-deployment-platform/kubernetes-deployment/) 統一管理           |
| 跨服務 debug | 一個請求跨多個服務、不知道在哪一段失敗            | [04 trace context](/backend/knowledge-cards/trace-context/)、結構化 log 聚合                                   |
| 契約治理     | 服務 A 的 API 改動會影響服務 B、C、D              | [contract test](/backend/knowledge-cards/contract/)、版本化 API                                                |
| 資料一致性   | 各服務 DB 獨立，跨服務查詢需要 join 或 read model | CQRS、event-driven projection、reconciliation                                                                  |

拆分失敗的回退路徑要在拆分前設計好。常見回退策略：保留原 monolith 程式碼一段時間（雙寫期），新服務出問題可以切回；先拆**讀路徑**驗證流量，再拆寫路徑；用 feature flag 控制是否走新服務。沒有回退路徑的拆分一旦撞牆，會比不拆更難收拾。

### 拆分後的通訊優先級：事件 > 同步 RPC

拆完後跨服務通訊有兩條路：同步 RPC（gRPC、REST）跟異步事件（[message queue](/backend/03-message-queue/)、event bus）。預設應該選事件、保留 RPC 給「真的需要同步回應的查詢」。

理由：

- **失敗代價隔離**：服務 A 發事件給 B、B 掛了不影響 A — 事件留在 queue 等。同步 RPC 下、B 掛了 A 也跟著掛
- **流量解耦**：事件本身就是 buffer、能吸收 burst。同步 RPC 是 throughput 的硬上限、A 的尖峰 = B 的尖峰
- **可重放**：事件可以重放（replay）做資料修補、debug、新服務 backfill。同步 RPC 過了就過了
- **服務獨立演進**：事件 schema 可以加欄位向下相容、consumer 慢慢 adapt。RPC interface 改動是 breaking change

該用同步 RPC 的少數場景：使用者請求路徑需要立即回應（「使用者按下查詢、顯示結果」）、且兩個服務都在同一個 latency budget 內。其他都優先事件。

詳見 [03 模組訊息佇列](/backend/03-message-queue/) 跟 [0.3 非同步與事件傳遞選型](/backend/00-service-selection/async-delivery-selection/)。

## 反例：拆分過度的收回

服務拆分的反向動作是合併。當拆分後發現「服務間呼叫太頻繁、近乎同步、跨服務事務太多」時，代表這條邊界拆錯了。處理方式不是繼續增加跨服務工具，而是把這兩個服務合回去。

判讀「該合併」的訊號：服務 A 與 B 之間每秒幾百次同步呼叫且失敗會連鎖、A 改動必定觸發 B 改動且兩者由同一團隊維護、跨服務事務佔總業務動作比例過高、跨服務 latency 是 SLO 主要消耗者。

合併不是失敗。它代表團隊已經理解這條邊界不該存在，及時收回比硬撐更負責任。Modular monolith（單一部署、模組化邊界）是常見的折衷形態：保留模組邊界、避免分散事務代價、未來壓力出現時再分拆。

## 判讀訊號

| 訊號                           | 判讀重點                             | 對應動作                                                                           |
| ------------------------------ | ------------------------------------ | ---------------------------------------------------------------------------------- |
| 多團隊發版互相阻擋             | 部署邊界已形成、但服務仍綁在一起     | 從 CI/部署單位開始拆，先讓發布獨立                                                 |
| 同一服務不同功能擴展需求差距大 | 流量邊界已形成                       | 沿流量軸拆，高頻 endpoint 獨立服務 + 獨立 auto scaling                             |
| DB 寫入鎖跨業務互相影響        | 資料邊界已形成                       | 沿資料軸拆，獨立 schema 與獨立 DB instance                                         |
| 拆分後跨服務同步呼叫激增       | 邊界拆錯、實際耦合並未被服務界線解開 | 評估合併、或改用事件驅動把同步呼叫變成非同步交接                                   |
| 拆分後事故 MTTR 拉長           | 跨服務觀測能力跟不上                 | 補 [04 trace context](/backend/knowledge-cards/trace-context/) 與 service topology |
| 拆分後 dev velocity 反而下降   | 契約治理跟跨服務協作成本超過拆分收益 | 評估合併或建立 shared kernel                                                       |

## 常見誤區

把「technical debt」當成拆分理由。Monolith 程式碼髒亂的解法是重構，不是拆服務。拆服務只是把髒亂從單庫變成跨服務契約混亂，問題並沒有消失。

把「跟風 microservice」當成決策。沒有業務壓力、團隊規模不到位、運維能力不夠的情況下拆服務，新的協作成本會壓垮整個團隊，這比 monolith 的痛苦更大。

把拆分當成單向操作。沒有設計回退路徑、沒有保留合併選項，拆錯了就只能硬撐。成熟的服務演進策略要把「拆」跟「合」當成雙向可逆操作。

## 定位邊界

本章專注「該不該拆、沿哪條軸拆、拆完怎麼收尾」。當問題進入具體拆分後的部署、流量、觀測責任，分別交給以下模組：

- 服務獨立部署 → [05 deployment platform](/backend/05-deployment-platform/)
- 跨服務交接與事件 → [03 message queue](/backend/03-message-queue/)
- 跨服務觀測與 trace → [04 observability](/backend/04-observability/)
- 跨服務一致性與冪等性 → [03 idempotency-replay](/backend/03-message-queue/) + outbox pattern

## 案例回寫

服務拆分判讀可用以下案例回寫：

- [9.C23 Netflix：把關聯式 DB 統一到 Aurora、效能 +75%、成本 -28%](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — 反例方向：原本各 microservice 各自 DB 造成運維碎片化、最後做 consolidation；對照本章「拆分過度的收回」段。
- [5.C2 Condé Nast：EKS 平台整併與標準化](/backend/05-deployment-platform/cases/conde-nast-platform-modernization-eks/) — Condé Nast 把多 brand 各自的 K8s cluster 整併到統一 EKS 控制面、降低跨團隊運維分歧。對照本章「拆分代價 / 運維複雜度」段：拆出去快、合回來慢、設計時就要評估這種非對稱性。
- [9.C12 Riot Games：246 個 EKS cluster 的多遊戲多地區治理](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) — Riot 的拆分軸是「遊戲 × 地區 × 環境」三維交集、246 個 cluster 是這三軸的笛卡兒積取一個 subset。對照本章「拆分軸 / 部署邊界」段：實務上的拆分常常是多軸交集、不是單軸推進。

Netflix Aurora consolidation 是反例最有教學價值的一筆 — 它證明「拆 microservice 各自 DB → consolidation 回 Aurora」是 valid endgame、拆服務不是單向操作。Condé Nast 跟 Riot Games 補充另兩條維度：碎片化的運維代價、多軸交集的設計複雜度。把這三筆放回「拆分時機判讀」框架的不同節點上、能看出拆分決策的本質是「沿哪幾條軸 + 接受哪些代價」的組合。

## 跨模組路由

1. 與 [0.1 後端服務能力地圖](/backend/00-service-selection/service-capability-map/) 的交接：拆分前要先理解每塊責任屬於哪種能力分類，避免拆出語意混亂的服務。
2. 與 [0.5 流量與資料量評估](/backend/00-service-selection/traffic-data-scale/) 的交接：流量軸拆分要先有流量基線。
3. 與 [03 message queue](/backend/03-message-queue/) 的交接：拆分後跨服務通訊優先用事件、不是同步 RPC。
4. 與 [9.13 擴展軸](/backend/09-performance-capacity/scaling-axes/) 的交接：拆分常常是水平擴展的前提（無狀態服務拆分後才能獨立水平擴展）。

## 下一步路由

**規模成長路線下一站 → [9.13 擴展軸與 Stateless 前提](/backend/09-performance-capacity/scaling-axes/)**：拆分後接著要為每個服務選擇擴展軸。

其他延伸方向：

- 實作層：服務如何獨立部署 → [5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)
- 事件層：拆分後跨服務通訊設計 → [03 模組訊息佇列](/backend/03-message-queue/)
