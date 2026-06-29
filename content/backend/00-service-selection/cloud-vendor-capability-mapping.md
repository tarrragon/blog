---
title: "0.19 雲端服務對照地圖（AWS / GCP / Azure）"
date: 2026-05-27
description: "把後端能力分類對照到 AWS / GCP / Azure 的具體服務名稱、保留跨雲遷移與選型差異的判讀重點"
weight: 19
tags: ["backend", "service-selection", "cloud", "vendor-mapping"]
---

面對「我該選 AWS 還是 GCP？」這類問題、第一步是把後端能力分類對應到三家雲廠商的具體服務名稱、技術細節放後面。本章提供這份對照地圖、同時警告一件事：AWS、GCP、Azure 在大部分能力上都有對應產品，但「對應」不等於「等價」— 同樣是 managed SQL、AWS RDS、GCP Cloud SQL、Azure SQL 在備份頻率、replica 行為、failover 時間、跨區複製成本上都有差異。對照表是入口、不是決策本身。

## 為什麼需要這張對照地圖

兩種使用情境會需要這張表。第一是初次選型時，讀者已經選定主要雲廠商，要對照各能力分類找出 vendor 名稱。第二是跨雲遷移評估，讀者要對照源端跟目標端的能力 gap。沒有這張表，每次都要重新查文件、容易漏掉某個能力。

但這張表不能取代深入評估。每個 vendor 都有不在表格內的差異，例如配額、區域可用性、跨服務整合、計價模型。表格是路由起點，後續判讀要進到該 vendor 的 deep article。

## 能力 × 雲廠商對照表

| 能力分類          | AWS                                  | GCP                         | Azure                                   | 對照判讀重點                                  |
| ----------------- | ------------------------------------ | --------------------------- | --------------------------------------- | --------------------------------------------- |
| 關聯式 DB（OLTP） | RDS / Aurora                         | Cloud SQL / AlloyDB         | Azure SQL / Azure Database for Postgres | failover 時間、跨區 replica、IOPS 計價        |
| 全球分散式 DB     | Aurora DSQL / DynamoDB Global Tables | Spanner                     | Cosmos DB                               | 一致性模型、寫入延遲、計價單位                |
| KV / Document DB  | DynamoDB                             | Firestore / Bigtable        | Cosmos DB                               | partition key 設計、capacity mode、跨區一致性 |
| 快取              | ElastiCache（Redis / Memcached）     | Memorystore                 | Azure Cache for Redis                   | 跨區複製、persistence、容量上限               |
| 訊息佇列          | SQS / SNS / Kinesis                  | Pub/Sub                     | Service Bus / Event Hubs                | delivery guarantee、ordering、retention 期    |
| 事件流（Kafka）   | MSK / Kinesis                        | Pub/Sub                     | Event Hubs (Kafka compatibility)        | Kafka 相容性、partition 數量、跨區複製        |
| 物件儲存          | S3                                   | Cloud Storage               | Blob Storage                            | 一致性模型、跨區複製、lifecycle policy        |
| 容器執行平台      | ECS / EKS / Fargate                  | GKE / Cloud Run             | AKS / Container Apps                    | managed 程度、cold start、計價單位            |
| Serverless 函式   | Lambda                               | Cloud Functions / Cloud Run | Azure Functions                         | 最大執行時間、cold start、整合方式            |
| Load Balancer     | ELB（ALB / NLB / CLB）               | Cloud Load Balancing        | Azure Load Balancer / App Gateway       | L4 vs L7、跨區 LB、TLS termination            |
| API Gateway       | API Gateway                          | API Gateway / Apigee        | API Management                          | rate limit、auth 整合、計價                   |
| CDN / 邊緣        | CloudFront                           | Cloud CDN / Media CDN       | Azure Front Door / CDN                  | edge POP 數、purge API、cache key 彈性        |
| 監控              | CloudWatch                           | Cloud Monitoring            | Azure Monitor                           | metric retention、dashboard 表達力、整合範圍  |
| Log 聚合          | CloudWatch Logs                      | Cloud Logging               | Log Analytics                           | ingestion 成本、query 語言、retention         |
| Tracing           | X-Ray                                | Cloud Trace                 | Application Insights                    | sampling 策略、跨服務 trace、整合 SDK         |
| Secret Management | Secrets Manager / SSM Parameter      | Secret Manager              | Key Vault                               | 旋轉支援、整合 IAM、稽核 log                  |
| Identity / IAM    | IAM                                  | IAM                         | Entra ID（前 AAD） + Azure RBAC         | 跨服務 policy、token lifetime、federation     |
| CI/CD             | CodePipeline / CodeBuild             | Cloud Build / Cloud Deploy  | Azure Pipelines                         | 整合 Git 平台、執行環境彈性、計價單位         |

這張表以全球 hyperscaler 三巨頭為主、不是市場全貌。**Oracle Cloud (OCI)** 在 enterprise / Java workload 跟金融受監管環境有顯著市佔；**Alibaba Cloud** 在亞太 / 跨境電商是主流；**IBM Cloud** 在金融 / 受監管環境仍存在；**Hetzner / DigitalOcean / Vultr** 在 cost-leader 區段提供完全不同的計價模型；**Sovereign cloud**（GDPR Schrems II 後在歐洲、JEDI / JWCC 在美國政府）是另一條獨立軸、跟資料主權合規綁定、比較對象不在這張表內。對照判讀邏輯（「對應 ≠ 等價」）可以同樣套用、但具體 vendor 名稱與差異維度要按目標廠商各自查證。

## 三家雲共同缺的能力分類

對照表覆蓋的能力都有 vendor 直接對應，但有兩類能力三家雲廠商都沒有提供等價的原生服務，要靠第三方工具補完。把這兩類獨立成段，避免在對照表中用「（無原生）」填空造成模板化。

**壓測 / 流量重放**：三家雲都沒有像 RDS 對 PostgreSQL 那樣的「managed 壓測服務」。團隊要從 k6、JMeter、Gatling、Locust、Vegeta、AWS Distributed Load Testing（這是 reference architecture 而非 managed service）這類第三方工具選擇。選型考量在於：是否支援該團隊熟悉的腳本語言（k6 用 JS / Gatling 用 Scala / Locust 用 Python）、能否分散執行、能否在 CI 整合、能否重放 production traffic（GoReplay、AWS VPC Traffic Mirroring）。各工具的選型細節見 [9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)。

**事故管理 / on-call 通知**：三家雲都沒有原生的 incident management 平台。CloudWatch / Cloud Monitoring / Azure Monitor 只到 alert 層、不負責 escalation、on-call rotation、incident timeline 與 retrospective。這層責任目前由 PagerDuty、Opsgenie、Splunk On-Call（前 VictorOps）、Grafana OnCall 等第三方平台承擔。三家雲提供的 alert 可以 webhook 到這些平台，但 incident workflow 本身不在 cloud vendor scope 內。事故管理流程見 [08 事故處理模組](/backend/08-incident-response/)。

辨識這兩類「跨雲共缺」能力的價值在於：跨雲遷移時這兩層不會增加 vendor lock-in，可以保留現有第三方工具直接接到新雲；反之，cloud-native incident management 或 cloud-native 壓測這類規劃要在採購前確認是否真實存在，避免被命名類似的工具誤導。

## 「對應 ≠ 等價」的具體差異範例

對照表只給名稱對應，實際選型要看差異細節。下面四個常見的差異維度示範如何把名稱對應翻成選型判讀。

### 失效切換時間差異（RDS vs Cloud SQL vs Azure SQL）

同樣是 managed PostgreSQL，三家 vendor 文件給的 failover 時間參考值差距明顯。下列數字以各雲廠商公開文件為基準、實測長尾可能拖到更長：

- AWS RDS Multi-AZ：vendor 文件寫「typically 60–120 seconds」、P99 實測可達數分鐘
- AWS Aurora：vendor 文件寫「typically less than 30 seconds」、實測 30–90 秒常見
- GCP Cloud SQL HA：vendor 文件寫「1–2 minutes」
- Azure SQL Business Critical：vendor 文件寫「around 30 seconds」、實測 30–60 秒

選擇關鍵不是「哪個快」、而是「業務能容忍多少 downtime」。30 秒對 banking、ticketing 是不能接受的；對內部後台是無感的。失效切換時間直接影響 SLO 設定跟業務連續性 — 數字以 vendor 公開文件為參考、實際決策時要用該 vendor 自己的 SLA 條款跟 incident report 驗證。

### 一致性模型差異（DynamoDB vs Firestore vs Cosmos DB）

三家的 NoSQL 在一致性語意上分歧：

- DynamoDB：預設 eventual consistent read、可選 strongly consistent read（成本 2 倍）
- Firestore：strongly consistent read 是預設、跨 region 用 multi-region 配置
- Cosmos DB：五種一致性等級可選（strong / bounded staleness / session / consistent prefix / eventual）

如果應用程式假設「寫完馬上能讀到」（read-after-write），在 DynamoDB 預設模式下會撞牆。在 Cosmos DB 選 session consistency 可以保證單一 client 內 read-after-write、跨 client 仍是 eventual。這類差異要在選型階段對齊，不是事後改 code。

### 計價模型差異（Lambda vs Cloud Functions vs Azure Functions）

三家的 [serverless](/backend/knowledge-cards/serverless/) 在計價單位有差異：

- Lambda：請求數 + 執行時間 (GB-秒)
- Cloud Functions：請求數 + 執行時間 + 網路流量
- Azure Functions：執行次數 + 執行時間 + 記憶體（Consumption Plan）或固定費用（Premium / Dedicated Plan）

對於低流量服務、三家差異不大；對於高頻率短時間函式、計價差異可能放大數倍（具體倍數視 memory size / 執行時間 / 流量分布、用 vendor calculator 算）。選型時要用實際 workload 估算、不能看單位價格表面數字。

### 跨服務整合差異（消息佇列 vs 觸發器）

AWS SQS + Lambda 整合非常成熟、有 native trigger；GCP Pub/Sub + Cloud Functions 同樣 native；Azure Service Bus + Functions 也有 trigger，但細節（dead-letter 處理、retry 策略、batch size）跟前兩家有差異。

跨服務的整合成熟度通常會在事故時放大差異。同樣的事件處理流程，在 AWS 上 90% 用 native 路徑、在另一家可能需要 30% 自己寫 glue code。

## 跨雲遷移的判讀重點

把這張對照表反過來讀，就是跨雲遷移的 gap 分析起點。但實際遷移要看四類風險：

| 風險類型                      | 判讀重點                                               | 對應緩解                                               |
| ----------------------------- | ------------------------------------------------------ | ------------------------------------------------------ |
| 語意差異                      | 兩家「對應」服務的一致性 / 失效 / 順序語意是否一致     | 在抽象層（repository、queue adapter）封裝差異          |
| 配額差異                      | 限制（每秒請求數、partition 上限、batch size）是否相當 | 對照新平台配額重新設計批次大小                         |
| 計價差異                      | 計價單位不同，舊有 cost model 在新平台失準             | 用新平台計價重做 cost engineering                      |
| 生態差異                      | 周邊工具（監控、log、IAM）整合不對等                   | 預估遷移成本要含「重建 observability / IAM」           |
| Data gravity / egress lock-in | PB 級資料的 egress fee 跟一致性轉移時程                | 決定資料「同步轉移 / 漸進複製 / 保留在原雲、運算跨雲」 |

第五類風險常被低估：以 AWS S3 為例、egress 約 $0.09/GB、PB 級資料即 $90k 帶寬費；GCP / Azure 同等級。跨雲遷移最大單筆成本經常是 data gravity、需要先決策資料拓樸再算其他三類風險。

跨雲遷移不是把服務名稱換掉就完成。每一個對應都要做 deep audit，這是 [01 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 等模組的責任。

## 混合雲與多雲的情境

常見的混合或多雲組合：

- **資料留 AWS、ML 跑 GCP**：因為 BigQuery、Vertex AI 在資料分析優勢
- **主要 Azure、ML 跑 AWS**：因為 SageMaker 跟 Bedrock 提供的選項
- **DR 在另一家雲**：主要在 AWS、DR 站在 Azure 避免單一雲廠商故障

混合 / 多雲要解的核心問題是跨雲流量成本（egress）跟身分聯邦（cross-cloud IAM）。這兩個成本通常被低估，要在規劃階段就做進 cost model。

## 對照表使用的判讀順序

讀這張表時，避免以下兩種誤用：

第一是「看完表格就決定 vendor」。表格只給名稱對應，沒給選型理由。先確認自己的能力需求（容量、一致性、failover 時間、計價型態），再用表格找候選 vendor，再進該 vendor 的 deep article 驗證細節。

第二是「把『對應』當作可互換」。已經提到的失效時間、一致性語意、計價模型差異會直接影響業務。在做技術選型時不能假設「換家雲就行」，要驗證每一條差異。

正確的使用順序：能力需求 → 對照表找候選 → vendor deep article 驗證 → cost / failure / consistency 驗算 → 決策。

## 判讀訊號

| 訊號                             | 判讀重點                            | 對應動作                                   |
| -------------------------------- | ----------------------------------- | ------------------------------------------ |
| 同樣 workload 在新雲上 cost 翻倍 | 計價模型差異未被估到                | 重做 cost engineering、用實際 traffic 估算 |
| 遷移後 latency 升高              | 區域、跨服務整合或一致性模式不同    | 確認 region 選擇、跨服務整合方式           |
| 跨雲 egress 成本失控             | 流量設計沒考慮 inter-cloud transfer | 重新設計流量拓樸、考慮 cache 或聚合        |
| 跨雲 IAM 設定爆炸                | 身分聯邦設計不足、每個服務各管各的  | 引入統一身分平台或 federation              |
| 新雲服務功能對應不上             | 「對應 ≠ 等價」的 gap 出現          | 抽象層封裝差異、或評估是否值得換           |

## 常見誤區

把 vendor 對照表當「採購清單」，看完直接照表選。選型必須回到需求，不是看哪家有對應名稱就選。

把雲廠商當「commodity 商品」，假設換家就好。三家的整合生態、配額限制、計價單位都有差異、遷移成本經常被嚴重低估（特別是 data gravity / IAM / 監控重建這三類隱性成本）。

把單一雲廠商當「永遠不會變」。雲廠商會調整定價、棄用服務、改 API。設計時要有抽象邊界，避免直接綁定 vendor SDK 到業務邏輯，方便未來換家或多雲。

## 定位邊界

本章預設「自建於雲端基礎設施」已成立；讀者若在對照表看到 Firestore 而想問「乾脆整個用 Firebase？」、那是 BaaS / 託管平台層的交付形態判斷、見 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/)。

本章專注「能力分類到 vendor 名稱的翻譯與對應差異」。當問題進入具體 vendor 配置（例如 RDS 怎麼設 backup）、跨 vendor 遷移流程（例如從 MySQL 遷到 Aurora），分別交給各模組的 `vendors/` 目錄跟 migration playbook。當問題進入需求分類（這個業務需要強一致還是最終一致？）回到 [0.0 後端需求分類地圖](/backend/00-service-selection/backend-demand-taxonomy/)。

## 案例回寫

雲端服務選型可用以下案例回寫：

- [0.14 企業選型案例圖譜](/backend/00-service-selection/enterprise-selection-case-atlas/) — 0.14 收錄不同產業、不同規模階段企業的雲端選型決策；對照本章「跨雲遷移的判讀重點」段：合規、計價、IAM 整合是三家雲決策的主要分歧軸。
- [9.C20 Zomato：TiDB 遷到 DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — Zomato 把 SQL 介面（TiDB）換成 KV 介面（DynamoDB）、用一致性語意差異換取 4 倍吞吐 + 50% 成本；對照本章「對應 ≠ 等價」段中的一致性模型差異子段。
- [9.C23 Netflix：Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — 案例是 AWS 內 DB 種類整併（多 RDB → Aurora），可對照本章「對應 ≠ 等價」段中的計價模型與整合成熟度差異。雖然不涉及跨雲，但在同一家雲廠商內整併服務、跟跨雲整併共用同一條決策邏輯：權衡 vendor lock-in 代價 vs 運維碎片化代價。
- [5.C1 Tradeshift：self-managed K8s → EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) — Tradeshift 從自管 K8s control plane 遷到 EKS managed control plane、運維責任邊界從「整套 cluster」收斂到「workload + worker node」。對照本章「容器執行平台」對照行：managed 程度是同一能力分類下的主要分歧軸。

這些案例回答的是不同問題、不是同一個問題的不同切面。對照表本身只回答「叫什麼名字」；Zomato / Tradeshift 補「換掉名字後實際差多少」（介面 / 計價 / 一致性差異）；Netflix Aurora 補「同一雲內怎麼收斂」；0.14 補「真實企業在什麼壓力下選什麼」。讀者按手邊的問題進入對應案例、不需要也不適合串成同一條 narrative。

## 跨模組路由

1. 與 [0.1 後端服務能力地圖](/backend/00-service-selection/service-capability-map/) 的交接：先確認能力分類，再用本章找 vendor 對應。
2. 與 [0.6 成本、風險與選型取捨](/backend/00-service-selection/cost-risk-tradeoffs/) 的交接：cost model 是 vendor 選型的關鍵維度。
3. 與各模組的 `vendors/` 目錄的交接：對照表只給名稱、deep article 給配置與運維。
4. 與 [01 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 的交接：跨 vendor 遷移的具體流程。

## 下一步路由

對照表是查 vendor 名稱的第一層、進入細節要走 deep article：

- 實際企業選型案例 → [0.14 企業選型案例圖譜](/backend/00-service-selection/enterprise-selection-case-atlas/)
- 資料庫 vendor 細節對比 → [01 模組 vendors/](/backend/01-database/vendors/)
- 部署平台 vendor 細節對比 → [05 模組 vendors/](/backend/05-deployment-platform/vendors/)

本章不在規模成長路線上、是 sibling 工具型入口。要進規模成長路線、從 [10.1 服務拆分](/backend/10-system-evolution/service-decomposition-boundaries/) 或 [9.13 擴展軸](/backend/09-performance-capacity/scaling-axes/) 開始。
