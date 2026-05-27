# 後端真實服務討論大綱

> **Status**: backend 教材 author-facing outline — 規劃各 backend 分類從共同觀念與服務路徑示範、推進到真實服務介紹、取捨與案例回寫的寫作順序。原為 `content/backend/00-service-selection/service-entity-discussion-outline.md`（weight 0.17）、2026-05-27 移到 `.codex/outlines/backend/`。
>
> **適用對象**：寫 backend 各分類 vendor / 服務實體章節時、用本檔對齊真實服務層的順序與取捨敘事。

後端真實服務討論的核心責任是把分類觀念落到具體服務能力。PostgreSQL、Redis、Kafka、Kubernetes、k6 或 PagerDuty 這些名稱本身是服務能力入口；它們各自承擔某種資料、流量、交付、驗證或協作責任，文章要先說清楚這個責任，再討論適用場景、替代方案、操作成本與案例回寫。

## 階段定位

真實服務層是後端教材的第三層。第一層是分類共同認知，回答資料庫、快取、queue、觀測、部署、可靠性、資安與事故流程分別解什麼問題；第二層是服務路徑示範，用單一業務流程串起 evidence、gate、decision log 與 write-back；第三層才討論具體服務如何承擔這些責任。

這個階段的主要風險是把服務頁寫成產品介紹。服務頁要把工具能力翻成 backend 判準：它承擔哪種狀態、怎麼觀測、什麼負載形狀會壓垮它、什麼團隊能力才維護得起、什麼條件下應該換到同類或相鄰服務。

## 撰寫判準

每篇服務實體文章都要回答同一組決策問題。固定問題提供交接語言，正文段落仍要保留該服務自己的情境語言。

| 判準       | 文章要回答的問題                                | 失焦訊號                       |
| ---------- | ----------------------------------------------- | ------------------------------ |
| 服務責任   | 這個服務承擔哪一類 backend 能力                 | 只列功能，不說解什麼服務問題   |
| 適用壓力   | 哪種流量、資料、組織或合規壓力會讓它值得引入    | 只寫「適合大規模」這類空泛描述 |
| 替代邊界   | 什麼情境下同類服務或相鄰分類更划算              | 把同一類工具寫成單一路線       |
| 操作成本   | 引入後誰負責升級、備份、容量、監控、事故與稽核  | 只比較雲端價格或效能           |
| 案例回寫   | 哪些公開案例能回寫到分類主章或服務路徑示範      | 案例停在「某公司使用 X」       |
| 下一步路由 | 讀者下一步該回到哪個主章、case、artifact 或卡片 | 文章讀完沒有決策出口           |

服務責任段要把產品名稱放回分類語言。PostgreSQL 承擔 SQL transaction、schema evolution、query boundary 與 migration safety；Kafka 承擔 event log、consumer group、replay window 與 topic governance。

適用壓力段要用真實服務訊號描述引入理由。資料量、QPS、hot key、consumer lag、connection limit、multi-region latency、compliance evidence、on-call 負擔與 vendor support 都是可判讀訊號；單純寫「效能更好」或「比較穩定」會讓讀者失去選型依據。

替代邊界段要保留機會成本。Redis 在簡單快取路徑很合理，但 durable workflow 要轉向 queue；DynamoDB 在高峰 KV workload 很合理，但複雜 ad-hoc query 要回到 SQL 或 search；Kubernetes 在多服務平台很合理，但單機服務可能由 systemd 承擔更低操作成本。

操作成本段要把服務帶來的長期責任寫出來。Managed 服務降低 patch、failover 與容量維護成本，但增加雲端約束、費用模型與 vendor 依賴；自管服務保留控制權，但要求團隊承擔升級、備援、演練與事故處理。

案例回寫段要把公開案例變成判準來源。案例的核心責任是提供流量形狀、失敗代價、組織能力與回退路徑，讓主章可以回寫更準確的服務判斷。

## LLM 教學設計移植

LLM 目錄提供的可重用設計是「先建立心智模型，再進入工具，最後才處理延伸與排錯」。Backend 服務頁要採同一種教學骨架：先說服務在分類模型裡的位置，再給讀者最短判讀路徑，接著展開日常操作、進階主題、替代路由與不收錄主題。

這個設計避免服務頁變成產品百科。Ollama、LM Studio、llama.cpp 的文章都先說它在「介面 / 伺服器 / 模型」三層架構中的位置；Backend 服務頁也要先說 PostgreSQL、Redis、Kafka、Kubernetes、Prometheus、PagerDuty 等服務在「資料 / 副本 / 交接 / 流量 / 訊號 / 驗證 / 協作」哪一層承擔責任。

### LLM-depth parity 完成標準

LLM-depth parity 的責任是把 backend 服務討論從「服務頁已存在」提升到「服務章節群可教學」。LLM 模組的深度來自三層：入口頁建立讀者路線，單篇文章承擔一個清楚概念，hands-on / deep article 把操作、排錯與延伸路由補齊。Backend 服務也要用同等層級，而非只完成 vendor overview。

| 層級                | LLM 目錄對應形態                        | Backend 服務對應形態                                            | 完成訊號                                                 |
| ------------------- | --------------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------- |
| Module index        | 模組入口、章節列表、為什麼這個順序      | 分類入口與 vendors index                                        | 讀者知道先讀哪一篇、何時跳 deep article 或 migration     |
| Service overview    | Ollama / LM Studio / llama.cpp 等工具頁 | PostgreSQL、SQLite、Redis、Kafka、Kubernetes 等服務頁           | 讀者能完成第一輪服務定位、適用壓力、替代邊界與下一步路由 |
| Deep article        | RAG、agent、benchmarking 等單一機制篇   | WAL / backup、hot key、consumer replay、draining、alert fatigue | 單一機制有問題情境、操作流程、失敗模式、觀測訊號與反路由 |
| Hands-on / artifact | quickstart、judge harness、RAG demo     | evidence package、release gate、restore drill、replay runbook   | 讀者能產出可交接 artifact，而非只理解概念                |
| Extension route     | 延伸方向與不收錄主題                    | migration playbook、case library、相鄰 service route            | 讀者知道何時升級、遷移、停留或改走其他分類               |

這份標準把「每個服務都完成」定義成章節群完成。第一輪 vendor overview 只完成 service overview；第二輪要依 overview 暴露出的缺口補 deep article；第三輪才補 migration playbook 或 hands-on artifact。若某服務只有 overview，狀態應標為 T1 完成，而非整體完成。

### 服務章節群的最小組成

每個 backend 服務章節群至少要有三個讀者出口。第一個出口是「我是否該用它」的 overview；第二個出口是「我用了以後怎麼穩定運作」的 deep article；第三個出口是「我走錯或長大後怎麼遷移」的 migration / alternative route。

| 服務群                 | Overview 責任                            | Deep article 候選                                                | Migration / route 候選                                   |
| ---------------------- | ---------------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------- |
| SQLite                 | embedded formal state 與 writer boundary | file lifecycle / backup boundary、test fixture best practice     | SQLite → PostgreSQL、SQLite → D1 / Turso                 |
| MongoDB                | document shape 與 schema governance      | index / shard key、transaction boundary、Atlas operation         | MongoDB → Atlas、document → relational split             |
| DynamoDB               | access pattern 與 managed KV capacity    | partition key、hot partition、capacity mode、single-table design | DynamoDB → SQL / search / analytics split                |
| Aurora                 | managed SQL operation transfer           | failover、cluster endpoint、I/O cost、backup / restore           | PostgreSQL / MySQL → Aurora、Aurora → distributed SQL    |
| Spanner / CockroachDB  | distributed SQL 與 transaction retry     | multi-region topology、transaction retry、range / split          | PostgreSQL → distributed SQL、regional rollout           |
| Cosmos DB              | multi-model API 與 consistency level     | RU budgeting、partitioning、consistency level                    | API model migration、Cosmos DB → specialized store       |
| Redis / Valkey         | cache copy、data structure 與 freshness  | hot key、eviction、cache stampede、serialization migration       | Redis → Valkey / managed cache / queue split             |
| Kafka / RabbitMQ / SQS | delivery、processing、recovery 分層      | consumer replay、DLQ drain、ordering、idempotency                | Kafka → Pub/Sub、RabbitMQ → SQS、queue → workflow engine |
| Kubernetes / systemd   | lifecycle contract 與 workload runtime   | readiness / draining、resource limit、rollout evidence           | systemd → Kubernetes、Docker Swarm → Kubernetes          |
| Observability tools    | signal ownership 與 evidence route       | cardinality、trace sampling、log schema、signal quality          | SaaS → OTel / Grafana stack、vendor consolidation        |
| Incident tools         | paging、command、status 與 learning      | escalation policy、incident timeline、stakeholder update         | PagerDuty → incident.io、Statuspage → Instatus           |

這張表是 backlog 與完整性檢查工具。每個服務頁的正文仍要依自己的服務壓力寫作；表格只用來確保 LLM-depth parity 的三層出口有被照顧。

## 服務頁標準大綱

每篇真實服務頁先依下列章節建稿。章節名稱可以依分類調整，但語意責任要完整保留。

| 章節                 | 作用                                           | Backend 服務頁要回答的問題                                         |
| -------------------- | ---------------------------------------------- | ------------------------------------------------------------------ |
| 服務定位             | 對應 LLM 文章的三層架構定位                    | 這個服務屬於資料、快取、broker、平台、觀測、驗證或協作哪一層       |
| 本章目標             | 對應 LLM 文章的「讀完後你應該能」              | 讀者讀完後能做哪幾個判斷、辨識哪幾個風險                           |
| 最短判讀路徑         | 對應 LLM 文章的「5 分鐘 / 1 小時最短路徑」     | 只用一個真實服務壓力，如何快速判斷是否該考慮這個服務               |
| 日常操作與決策形狀   | 對應 LLM 文章的日常使用段                      | 服務在日常運作中有哪些固定決策：容量、備份、升級、權限、觀測       |
| 核心取捨表           | 對應 LLM 文章的工具對照表                      | 它跟同類或相鄰服務的差異，哪些情境下比較划算                       |
| 進階主題             | 對應 LLM 文章的按需閱讀段                      | cluster、multi-region、HA、managed mode、SLO、cost 等何時才需要    |
| 排錯與失敗快速判讀   | 對應 LLM 文章的排錯段                          | 出現 lag、hot key、failover、cardinality、alert fatigue 時先看哪裡 |
| 何時改走其他服務     | 對應 LLM 文章的「何時改回 Ollama / llama.cpp」 | 什麼條件下該改用 SQL、queue、managed platform、SaaS、OSS 或自建    |
| 不在本頁內的主題     | 對應 LLM 文章的 scope boundary                 | 哪些議題交給主章、案例、語言教材、資安或更專門的模組               |
| 案例回寫與下一步路由 | 對應 LLM 文章的下一章 / 模組路由               | 讀完後回到哪個主章、case、artifact、knowledge card                 |

「最短判讀路徑」定位為決策教學。Backend 服務頁的最短路徑是決策路徑，例如「Redis 是否只是可重建副本」「Kafka 是否需要 replay window」「Kubernetes 是否真的需要多服務調度」「PagerDuty 是否已經有 service ownership 與 escalation policy」。這段要讓讀者在短時間內排除明顯不適合的選項。

「排錯與失敗快速判讀」定位為第一輪分流。它只列第一輪定位問題，讓讀者知道應該回到哪個主章或案例：cache 先看 hit/miss 與 origin QPS；queue 先看 lag、DLQ、redelivery；deployment 先看 readiness、drain、per-version SLI；observability 先看資料品質與 cardinality；incident 先看 alert route、incident timeline 與 stakeholder update。

## 服務頁教材合約

服務頁教材合約的責任是把服務頁完成標準從「已收錄 vendor」提升到「能獨立教會一個服務能力」。這份合約對齊 [#133 服務頁教材合約](/report/service-page-teaching-contract/)：服務頁應具備學習目標、核心概念、操作形狀、判讀訊號、替代邊界、案例回寫與下一步路由；章節順序則依服務對象、分類責任與使用情境設計。

這份合約約束教學功能，不約束章節模板。SQLite、MongoDB、PostgreSQL 都在資料庫分類，但 SQLite 服務頁可以先教 embedded / local formal state，MongoDB 服務頁可以先教 document shape 與 schema governance，PostgreSQL 服務頁可以先教 SQL baseline、transaction 與 schema evolution。它們要達到同等教學深度，段落路線可以完全不同。

| 合約面         | 服務頁必須交付的教學功能                             | 可接受形態                                         |
| -------------- | ---------------------------------------------------- | -------------------------------------------------- |
| 學習目標       | 讀者讀完後能做哪幾個服務判斷                         | 本章目標、讀法段、開場學習成果                     |
| 核心概念       | 服務承擔哪一種 backend 責任與心智模型                | 服務定位、服務對象、資料形狀、流量形狀             |
| 操作形狀       | 日常如何設定、觀測、維護與調整                       | CLI / API、schema、工作流、平台操作、治理流程      |
| 判讀訊號       | 健康、退化、失配與事故前兆要看哪些訊號               | metrics、query、audit trail、cost signal、流程訊號 |
| 替代邊界       | 何時改走同類服務或相鄰分類                           | 同類比較、相鄰分類路由、規模 / 組織能力分界        |
| Scope boundary | 哪些議題交給主章、deep article、migration 或語言教材 | 不在本頁段、下一步路由、或段內明確分流             |
| 案例回寫       | 哪些案例提供壓力、失敗代價或回退條件                 | 公開案例、反例、規模對照、checkout episode         |
| 下一步路由     | 上游概念、平行服務、下游 artifact 或 case route      | 頁尾路由、段內路由、或 index 回寫路由              |

Audit 分級採三層。A 級是教材頁，代表上述教學功能大多成立，可以進入 polish 與案例補強；B 級是內容充足但學習路線需重排，代表已有材料但服務對象、操作判讀或路由尚未對齊；C 級是服務摘要，代表目前只能作 vendor entry，需要先依服務對象設計大綱再寫正文。

## 服務頁開寫 Checklist

服務頁開寫 checklist 的責任是把標準大綱轉成開稿前的 gate。每篇服務頁開寫前，先用下列問題確認它已經有清楚的分類責任、同類對照、case route 與 artifact route。

| Gate           | 開寫前要回答的問題                                                         | 通過訊號                                    |
| -------------- | -------------------------------------------------------------------------- | ------------------------------------------- |
| 分類責任       | 這個服務承擔狀態、副本、交接、訊號、部署、驗證、控制、協作或容量哪一類責任 | 開場段能用分類語言說明服務存在理由          |
| 最小差異       | 它和同類服務的最小選型差異是什麼                                           | 讀者能在 5 分鐘內知道何時考慮或放下這個服務 |
| 服務壓力       | 哪個流量、資料、組織、合規或成本壓力讓它值得引入                           | 適用場景能用可觀測訊號描述                  |
| Checkout route | 它能接回 E1-E7 的哪一段                                                    | 至少一個 episode 能提供案例語境             |
| Artifact route | 它要把證據交給 04、gate 交給 06、決策交給 08，或 audit 交給 07 的哪一段    | 下一步路由能指到主章、artifact 或 case      |
| 成本邊界       | 導入後誰承擔升級、備份、容量、權限、事故與費用                             | 操作成本段能寫出 owner 與長期責任           |

這份 checklist 只作為開稿 gate。正文段落仍要依分類語言展開，避免所有服務頁長成同一份欄位表。

## WRAP 分類差異判斷

分類差異判斷的錨點是「服務頁教讀者做決策，而非填同一份模板」。每個分類都有自己的主要責任：資料庫處理正式狀態，快取處理可重建副本，佇列處理跨程序交接，部署處理生命週期與流量，觀測處理訊號，可靠性處理驗證，資安處理控制面，事故處理協作，效能容量處理壓力與成本。因此服務頁可以共用教學骨架，但正文結構要跟分類責任對齊。

Step 0 的資料充足度判斷是：現有主章、case、vendor index 已足以規劃大綱，但還不足以直接寫每個服務正文。下一步應先補「分類特化補充軸」，讓每篇正文開工前知道該連到哪些壓力、安全、觀測、可靠性與事故問題。

Widen Options 後的選項有三種。第一種是同一模板寫全部服務，交接成本低，但會抹平 Redis、Kafka、Kubernetes、PagerDuty 這些服務的責任差異。第二種是每個分類完全自由寫，表面彈性高，但容易漏掉資安、壓力、觀測、可靠性與事故交接。第三種是「分類主結構 + 共同護欄」，每類保留自己的教學順序，同時強制檢查 04 / 06 / 07 / 08 / 09 的交叉議題；這是後續採用的策略。

Reality Test 的反向驗證是：如果服務頁沒有明確連到 07 security、09 pressure / capacity、04 observability、06 reliability 與 08 incident response，讀者會把服務理解成單點工具；如果服務頁只列這些共同欄位，讀者會失去分類語言。因此共同護欄只作為每篇的檢查軸，分類自己的正文順序仍是主體。

Prepare to be Wrong 的回退條件是：若後續撰寫某分類時出現「每篇段落順序完全相同」或「資安 / 壓力 / 事故只出現在最後一段」兩種訊號，要先回到本節調整該分類大綱，再寫下一篇服務頁。

## 共同護欄與路由

共同護欄的核心責任是防止服務頁只停在功能介紹。每篇服務頁都要有分類自己的主結構，並至少處理下列五個交叉軸。

| 交叉軸     | 必答問題                                             | 主要路由                                                   |
| ---------- | ---------------------------------------------------- | ---------------------------------------------------------- |
| 壓力問題   | 什麼流量、資料量、併發、延遲、成本或容量形狀會壓垮它 | [09 效能與容量](/backend/09-performance-capacity/)         |
| 資安問題   | 它新增哪個身份、秘密、入口、資料、供應鏈或稽核控制面 | [07 資安與資料保護](/backend/07-security-data-protection/) |
| 可觀測性   | 讀者要看哪些訊號才能知道它健康、退化或失真           | [04 可觀測性](/backend/04-observability/)                  |
| 可靠性驗證 | 它的變更、故障模式或降級路徑要如何被驗證             | [06 可靠性驗證](/backend/06-reliability/)                  |
| 事故交接   | 它失效時誰接手、如何分級、如何記錄決策與回寫         | [08 事故處理](/backend/08-incident-response/)              |

這五軸在正文中要貼近分類語言。資料庫的壓力問題是 connection、lock、replication lag、hot partition；快取的壓力問題是 hot key、miss storm、origin QPS；佇列的壓力問題是 consumer lag、DLQ、redelivery；部署的壓力問題是 rollout batch、drain、target health；事故工具的壓力問題是 alert volume、ack time、stakeholder update freshness。

## 分類特化補充軸

每個分類要補的內容由「主責任」決定。共同護欄只提醒要連到哪些模組，真正的段落順序由下表的分類主問題決定。

| 分類             | 主結構要優先回答的問題                                      | 壓力軸                                                            | 資安軸                                                    | 04 / 06 / 08 交接軸                                                                             |
| ---------------- | ----------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 01 Database      | 正式狀態、transaction、query、schema、migration             | connection、lock、slow query、replica lag、hot partition          | 權限、資料遮罩、備份、資料駐留、稽核                      | 04 看 query / replication 訊號；06 驗證 migration / failover；08 記錄資料事故決策               |
| 02 Cache         | 可重建副本、新鮮度、回源保護、記憶體成本                    | hot key、miss storm、eviction、origin QPS、stale read             | cache poisoning、敏感資料快取、ACL、管理面                | 04 看 hit/miss / origin QPS；06 驗證 warmup / rollback；08 處理 stampede / stale incident       |
| 03 Queue         | delivery、processing、recovery、replay、DLQ                 | publish rate、consumer lag、redelivery、DLQ depth、poison message | payload 敏感資料、topic ACL、producer credential          | 04 看 lag / retry / DLQ；06 驗證 idempotency / replay；08 記錄 pause / drain / replay 決策      |
| 04 Observability | signal contract、data quality、cardinality、retention       | ingest volume、cardinality、query cost、sampling gap              | PII in logs、trace leakage、audit evidence                | 06 依賴 evidence gate；08 依賴 timeline / query link；09 依賴 saturation / cost signal          |
| 05 Deployment    | lifecycle、traffic、config、resource、rollback              | rollout batch、readiness、drain、target health、config drift      | secret delivery、TLS、management plane、image trust       | 04 看 per-version SLI；06 驗證 release gate / rollback；08 記錄 freeze / cutover / rollback     |
| 06 Reliability   | gate、experiment、fault injection、SLO governance           | runner bottleneck、false gate、blast radius、experiment load      | secret in CI、test credential、experiment permission      | 04 提供 evidence；08 接收 failed gate / unsafe experiment；09 提供 workload / capacity baseline |
| 07 Security      | identity、secret、key、entrypoint、artifact、detection      | auth spike、WAF false positive、rotation load、scan noise         | 本分類主軸：控制面、信任邊界、例外治理                    | 04 提供 audit / detection signal；06 驗證 control / release gate；08 處理 security incident     |
| 08 Incident      | alert routing、command、status、postmortem、learning        | alert storm、missed ack、timeline drift、status update freshness  | incident channel 權限、customer data、postmortem sharing  | 04 提供事件證據；06 回收 action item 到 gate；09 回收 capacity incident lessons                 |
| 09 Performance   | workload、saturation、capacity、cost、production validation | throughput plateau、latency knee、runner limit、cost curve        | replay data masking、profiler sensitive data、FinOps 權限 | 04 提供 metric / profile；06 接 regression gate；08 接 capacity incident / cost incident        |

分類特化補充軸的使用方式是先選分類主問題，再把五個交叉軸嵌入最自然的位置。資料庫服務頁的「資安」通常進入權限、備份、稽核段；快取服務頁的「資安」通常進入敏感資料與管理面段；佇列服務頁的「資安」通常進入 topic ACL 與 payload 段；事故工具頁的「可觀測性」通常進入 timeline evidence 與 query link 段。

## 主流覆蓋檢查

主流覆蓋檢查的核心責任是防止 vendor index 只列出已寫過的工具。T1 代表近期要寫成服務頁的主線選項；T2 代表主流但要等分類語言更穩後再寫；T3 代表相鄰分類或特殊場景，先保留路由，等案例需要時再升級。

| 分類             | T1 已有基線                                                                                                                                       | T2 補強方向                                                                                                                           | T3 / 相鄰路由                                             |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| 01 Database      | PostgreSQL、MySQL、SQLite、MongoDB、DynamoDB、Aurora、Spanner、Cosmos DB、CockroachDB                                                             | Oracle、SQL Server、MariaDB、Cassandra / ScyllaDB、OpenSearch / Elasticsearch、ClickHouse                                             | Snowflake / BigQuery 走 analytics；Redis 走 02 Cache      |
| 02 Cache         | Redis、Valkey、Memcached、DragonflyDB、ElastiCache                                                                                                | KeyDB、Garnet、Momento、Azure Cache、GCP Memorystore、Hazelcast、Aerospike                                                            | CDN / HTTP cache 連到 05 / edge；local cache 連到語言教材 |
| 03 Queue         | RabbitMQ、Kafka、NATS、Redis Streams、SQS、Pub/Sub                                                                                                | Pulsar、Redpanda、Kinesis、Azure Service Bus、EventBridge、SNS、Temporal                                                              | Celery / Sidekiq 走語言框架；MQTT broker 走 IoT 場景      |
| 04 Observability | OpenTelemetry、Prometheus、Grafana Stack、Datadog、Elastic、Honeycomb、CloudWatch、GCP Operations、Sentry                                         | Jaeger、OpenSearch、Fluent Bit / Fluentd、Vector、VictoriaMetrics、Thanos / Cortex、Splunk、New Relic、Dynatrace                      | Security SIEM 走 07；capacity profiling 走 09             |
| 05 Deployment    | Kubernetes、Docker、systemd、nginx、Envoy、AWS ELB、Terraform、Traefik、Consul                                                                    | Argo CD、Flux、Helm、Kustomize、ingress-nginx、Envoy Gateway、Istio、Linkerd、HAProxy、ECS / Fargate、Cloud Run                       | CI/CD gate 走 06；secret / policy control 走 07           |
| 06 Reliability   | GitHub Actions、CircleCI、k6、Gatling、JMeter、Locust、Chaos Mesh、LitmusChaos、Gremlin、Toxiproxy、Nobl9、Sloth                                  | GitLab CI、Jenkins、Buildkite、Tekton、Harness、Artillery、BlazeMeter、AWS FIS、Azure Chaos Studio、Pyrra、OpenSLO                    | capacity tool 走 09；incident tooling 走 08               |
| 07 Security      | Identity、IAM、Secrets、KMS、WAF、PKI、Supply Chain、SIEM、DLP 服務群                                                                             | Teleport、Boundary、Tailscale SSH、OPA、Kyverno、Falco、Wiz、Prisma Cloud、GitGuardian、Cloudflare Access                             | alert routing 走 08；evidence dashboard 走 04             |
| 08 Incident      | PagerDuty、Opsgenie、Grafana OnCall、incident.io、FireHydrant、Rootly、Statuspage、Instatus、Jeli                                                 | ServiceNow、Jira Service Management、Squadcast、xMatters、Splunk On-Call、Better Stack、Status.io、Cachet                             | observability source 走 04；release action 走 06          |
| 09 Performance   | k6、JMeter、Gatling、Locust、Vegeta、GoReplay、Traffic Mirroring、Datadog Profiler、Pyroscope、Parca、Akamas、Vantage、CloudHealth、Cost Explorer | Artillery、wrk、hey、Grafana k6 Cloud、AWS Distributed Load Testing、LoadRunner / BlazeMeter、Kubecost / OpenCost、CloudZero、CAST AI | release gate 走 06；FinOps ownership 走 04 / 09           |

主流覆蓋的判斷依據要保留時間戳。資料庫可以參考 DB-Engines 這類長期 popularity ranking；cloud-native 服務可參考 CNCF project / landscape 與近期技術雷達；incident tooling 要注意產品生命週期與收購 / sunset；雲端服務要以官方文件與主流 provider 分類為準。每次要把 T2 升級成 T1 前，先重新確認服務仍活躍、官方文件穩定、案例可回寫。

## 服務層缺口盤點

服務層缺口盤點的責任是把每個分類的服務頁、deep article 與 migration playbook 排成可教學的順序。現有 vendor `_index.md` 已經提供多數分類的 T1 入口；下一輪的重點是補強服務頁的學習路由，讓 deep article 與 migration playbook 在讀者理解服務責任後再展開。

| 分類             | 服務頁現況                                          | 主要缺口                                                               | 下一輪大綱順序                                                               |
| ---------------- | --------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 01 Database      | T1 服務頁已補教學路線，deep 內容偏 SQL / PostgreSQL | 跨服務對照、案例回寫密度與 deep / migration 升級條件仍要補強           | SQL baseline → embedded/local → document / KV → managed/global               |
| 02 Cache         | T1 服務頁已成形，deep 內容集中 Redis                | Valkey、Memcached、DragonflyDB 與 managed cache 的角色需要對照         | Redis / Valkey → Memcached → DragonflyDB → managed cache                     |
| 03 Queue         | T1 服務頁已成形，migration 內容集中 Kafka           | broker、managed delivery、event log、lightweight stream 的分流需要補強 | RabbitMQ → Kafka → SQS / Pub/Sub → NATS → Redis Streams                      |
| 04 Observability | T1 服務頁已成形，工具群完整                         | 服務頁要更直接連到 evidence package 與 signal quality                  | OpenTelemetry → Prometheus / Grafana → SaaS observability → cloud-native     |
| 05 Deployment    | T1 服務頁已成形，平台層完整                         | workload、traffic、infra state、discovery 的順序需要固定               | Docker / systemd → Kubernetes → nginx / ELB / Envoy → Terraform / Consul     |
| 06 Reliability   | T1 服務頁已成形，migration 範例少                   | CI gate、load test、chaos、SLO 工具混在同一層                          | CI / gate → load test → chaos / fault injection → SLO governance             |
| 07 Security      | 服務頁數量高，分類群組完整                          | 主要缺口是路由密度與控制面順序                                         | identity / IAM → secrets / KMS / PKI → edge → supply chain → detection / DLP |
| 08 Incident      | T1 服務頁已成形，deep 內容偏少                      | 工具頁需要接到 incident command、status、learning                      | paging → incident command → status page → postmortem / learning              |
| 09 Performance   | T1 服務頁已成形，case 可支撐                        | 工具選型要接回 workload、capacity、cost                                | load test → replay / mirroring → profiling → optimization → FinOps           |

這份缺口表的判斷結論是：服務頁優先於 deep article，deep article 優先於 migration playbook。服務頁負責建立該工具在 backend 能力地圖中的位置；deep article 負責展開某個服務機制或失敗模式；migration playbook 負責處理跨 vendor 或跨架構搬遷。

## Vendor Index Audit

Vendor index audit 的責任是檢查每個分類的服務入口是否已經足以支撐正文派發。這份 audit 看索引層與路由層，先整理服務頁、deep article 與 migration playbook 的結構缺口，再決定下一批正文。

| 分類             | T1 服務頁狀態 | Deep / migration 狀態              | Audit 判讀                                   | 下一步路由                                              |
| ---------------- | ------------- | ---------------------------------- | -------------------------------------------- | ------------------------------------------------------- |
| 01 Database      | 完整          | deep / migration 偏 SQL            | 服務頁足夠，跨資料模型對照要補強             | 補 SQL baseline 與 document / KV 導覽                   |
| 02 Cache         | 完整          | deep 內容集中 Redis                | 服務頁足夠，同類對照要補強                   | 補 Redis / Valkey / Memcached / managed cache 對照      |
| 03 Queue         | 完整          | migration 內容集中 Kafka           | 服務頁足夠，處理語意分流要補強               | 補 broker / managed delivery / event log 對照           |
| 04 Observability | 完整          | migration 與 pipeline 內容已有基礎 | 服務頁要更強連到 evidence package            | 補 signal quality 與 evidence route                     |
| 05 Deployment    | 完整          | migration 與平台案例已有基礎       | 服務頁要固定 workload / traffic / infra 順序 | 補 Kubernetes / systemd / ELB 分層                      |
| 06 Reliability   | 完整          | migration playbook 較少            | 工具群需分成 gate、load、chaos、SLO          | 補 CI gate、load test、SLO governance 導覽              |
| 07 Security      | 高密度        | case 與控制服務豐富                | 主要工作是重排控制面路由                     | 補 identity、secret、edge、supply chain、detection 導覽 |
| 08 Incident      | 完整          | deep article 較少                  | 服務頁需要接到 incident workflow             | 補 paging、command、status、learning 分層               |
| 09 Performance   | 完整          | case 能支撐工具路由                | 服務頁要接回 workload 與 cost                | 補 load test、replay、profiling、FinOps 導覽            |

Audit 的結論是：目前主要缺口在教學順序與服務頁對照密度，而非 T1 清單數量。下一輪應先補導覽型服務頁與同類對照，再依服務頁暴露出的機制缺口開 deep article。

## 服務層推進原則

服務層推進原則的責任是控制寫作粒度。每個分類先補「能讓讀者做第一輪判斷」的服務頁，再補需要更高背景的 cluster、multi-region、migration、cost optimization 或 incident playbook。

1. 服務頁先建立定位：每篇先說該服務承擔哪一種狀態、交接、訊號、驗證、控制或協作責任。
2. 同類對照先於深挖細節：PostgreSQL / MySQL、Redis / Memcached、Kafka / RabbitMQ、Kubernetes / systemd 這類對照先完成，讀者才有選型座標。
3. Deep article 承接明確缺口：只有當服務頁已經指出機制風險，例如 replication lag、hot key、consumer replay、draining 或 alert fatigue，才開 deep article。
4. Migration playbook 放在最後一層：跨 vendor 搬遷需要讀者先理解兩邊服務責任與操作成本，再進入差異盤點與階段切換。
5. Checkout episode 作為排序測試：若服務頁能自然接回 E1-E7 的某一段，代表它有清楚教學入口；若只能停在產品功能介紹，先回到分類大綱修正。

## Deep Article 與 Migration 升級條件

升級條件的責任是控制內容膨脹。服務頁負責第一輪判斷；deep article 負責機制深挖；migration playbook 負責跨服務或跨架構搬遷。三者的差異要在大綱階段先決定。

| 內容層級            | 升級訊號                                             | 留在服務頁的條件                   | 典型例子                                                       |
| ------------------- | ---------------------------------------------------- | ---------------------------------- | -------------------------------------------------------------- |
| 服務頁              | 讀者需要知道服務定位、適用壓力、替代邊界與操作成本   | 議題仍是第一輪選型或日常使用判斷   | PostgreSQL、Redis、Kafka、Kubernetes、PagerDuty                |
| Deep article        | 同一個失敗模式會跨多個服務頁重複出現                 | 只需補一段排錯提示或注意事項       | replication lag、hot key、consumer replay、draining            |
| Migration playbook  | 涉及雙軌、相容窗口、切流、回退、組織交接與長時間驗證 | 只是同一服務的小版本升級或設定調整 | MySQL to PostgreSQL、Kafka to Pub/Sub、self-managed to managed |
| Case / failure note | 單一事故能提供判讀訊號或反例                         | 尚未形成可重用機制                 | cache stampede rollout regression、queue semantics mismatch    |

升級判斷以可重用性為準。若內容只能服務單一產品設定，保留在服務頁；若內容能支撐多個服務頁的同一種風險判讀，升級為 deep article；若內容需要階段化搬遷、雙軌驗證與退出策略，升級為 migration playbook。

## 第一批：資料庫服務

資料庫服務討論的核心順序是先建立 SQL baseline，再處理 managed、KV/document 與全球分散式資料庫。這樣讀者會先知道 transaction、schema、query boundary 與 migration safety 如何成立，再看各服務把哪一部分能力交給平台或分散式協議。

第一批優先補強既有 vendor 頁的服務判準與案例回寫密度：

| 服務群                   | 主要頁面                                                                                                                                                          | 討論重點                                   |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| SQL baseline             | [PostgreSQL](/backend/01-database/vendors/postgresql/) / [MySQL](/backend/01-database/vendors/mysql/)                                                             | transaction、schema evolution、connection  |
| Managed SQL              | [Aurora](/backend/01-database/vendors/aurora/)                                                                                                                    | storage / compute 分離、failover、AWS 約束 |
| Embedded / local         | [SQLite](/backend/01-database/vendors/sqlite/)                                                                                                                    | 單機正式狀態、測試資料、低操作成本         |
| Document / KV            | [MongoDB](/backend/01-database/vendors/mongodb/) / [DynamoDB](/backend/01-database/vendors/dynamodb/)                                                             | access pattern、partition、資料形狀        |
| Global SQL / multi-model | [Spanner](/backend/01-database/vendors/spanner/) / [Cosmos DB](/backend/01-database/vendors/cosmosdb/) / [CockroachDB](/backend/01-database/vendors/cockroachdb/) | consistency、region、vendor lock-in        |

SQL baseline 段要把 PostgreSQL 與 MySQL 寫成比較基準。後續所有 managed SQL、distributed SQL 與 KV/document 討論，都應回到「這個 workload 為什麼離開或保留 SQL baseline」。

Managed SQL 段要保留平台責任轉移。Aurora 這類服務要同時看吞吐、storage layer、replica、failover、backup、engine compatibility 與雲端營運模型如何改變團隊責任。

Document / KV 段要先問資料形狀。DynamoDB、MongoDB 與 Cosmos DB 的差異，應從 access pattern、partition key、consistency、query model 與容量計費談起，再把 NoSQL 標籤放回分類整理。

Global SQL / multi-model 段要把 consistency 寫成產品成本。Spanner、CockroachDB 與 Cosmos DB 解決的是跨 region 的一致性與可用性取捨；文章要說明 latency、quorum、資料駐留、費用與 vendor 約束如何一起改變架構。

## 第二批：快取與事件服務

快取與事件服務討論的核心順序是先區分「副本保護」與「可靠工作交接」。Redis、Valkey、Memcached、Kafka、RabbitMQ、SQS、Pub/Sub、NATS 與 Redis Streams 都可能出現在高流量服務中，但它們承擔的資料生命週期不同。

快取頁要先回答副本語意。Redis / Valkey 適合 data structure rich cache、rate limit、leaderboard 與部分 coordination；Memcached 適合低語意、可重建、短生命週期快取；managed cache 則把 patch、failover 與 capacity 交給平台。

Queue 頁要先回答處理語意。Kafka 偏 event log、replay、partition 與 consumer group；RabbitMQ 偏 broker routing 與工作分派；SQS / Pub/Sub 偏 managed delivery；NATS 偏低延遲通訊與簡化操作；Redis Streams 適合既有 Redis 場景中的輕量 stream，但要清楚界定 durability 與治理邊界。

## 第三批：部署平台與操作服務

部署平台服務討論的核心順序是先從 service lifecycle 開始，再分到 workload、traffic、discovery、infra state 與 secret / config。Kubernetes、systemd、Docker、nginx、ELB、Envoy、Terraform 與 Consul 都能交付服務，但它們分屬不同能力層。

Workload 層要比較 Kubernetes、systemd 與 Docker。Kubernetes 適合多服務、多租戶、可觀測與 rollout 要求高的平台；systemd 適合單機或小型服務；Docker 提供 packaging 與 runtime 基礎，完整部署平台還需要 rollout、traffic、config 與觀測責任。

Traffic 層要比較 nginx、ELB、Envoy 與 Traefik。文章要從 health check、draining、idle timeout、TLS、routing rule 與 per-version traffic 訊號談起，讓讀者看懂 load balancer contract 如何影響 rollout 與事故回退。

Infra state 與 discovery 層要比較 Terraform 與 Consul。Terraform 承擔 infrastructure desired state，Consul 承擔 service registry / discovery 與部分 mesh 能力；兩者的失敗模式分別接到 change review、state drift、registry freshness 與 control plane 可用性。

## 第四批：效能與操作控制工具

效能工具服務討論的核心順序是先補 `09 vendors/`。09 主章與案例庫已經能支撐 workload model、saturation discovery、capacity planning、production validation 與 SLO coupling，下一步要把工具選型補成可引用入口。

壓測工具頁要用 workload model 當選型前提。k6、JMeter、Gatling、Locust 與 Vegeta 的差異，應從 protocol、scenario scripting、distributed load、CI integration、reporting 與團隊語言能力談起。

Production replay 與 profiling 工具頁要用風險邊界當選型前提。GoReplay、traffic mirroring、service mesh shadow、Datadog Continuous Profiler、Pyroscope 與 Parca 都能提供 production 近似訊號，但它們對資料遮罩、成本、採樣、效能開銷與事故觸發條件的要求不同。

## 第五批：資安控制服務

資安控制服務討論的核心順序是先從身份與憑證開始，再分到入口防護、供應鏈、偵測與資料保護。Okta、Auth0、Keycloak、AWS IAM、Vault、KMS、WAF、cert-manager、Snyk、Trivy、SIEM 與 DLP 服務都能改善安全控制，但它們分屬不同控制面。

Identity / IAM 頁要先回答「誰能做什麼」。人類身份、機器身份、role、policy、session、federation 與 least privilege 是選型基線；工具比較要回到身份擴散、例外權限與可稽核證據。

Secrets / KMS / PKI 頁要先回答「秘密與金鑰如何生命週期化」。Vault、Secrets Manager、KMS、cert-manager 與 SPIRE 的差異，應從 storage、lease、rotation、audit、delivery 與 workload identity 談起。

Edge / supply chain / detection 頁要先回答「控制在哪一個交接點生效」。WAF 保護入口，SCA / SBOM 保護 artifact，SIEM / detection 保護發現與交接，DLP 保護資料流；文章要說明它們如何接到 release gate、observability 與 incident response。

## 推進順序

下一輪寫作以最小可回寫批次推進。每批完成前先更新對應 vendor `_index.md` 的服務頁大綱與撰寫批次，再進入個別服務正文，避免服務頁散落成獨立產品百科。

1. 校正分類 backlog：以 `0.15` 固定分類缺口、checkout episode 與章節順序，讓正文批次有共同入口。
2. 校正服務 backlog：以本頁固定服務頁、deep article 與 migration playbook 的先後關係，讓服務頁先承擔教學定位。
3. 回掃 `01 Database vendors` 的跨服務對照與案例回寫密度，確認 SQL baseline、embedded/local、document / KV、managed/global 的讀法能支撐正文。
4. 補強 `02 Cache` 與 `03 Queue` 的服務頁順序，維持「副本語意」與「處理語意」的分流。
5. 補強 `05 Deployment`、`04 Observability`、`06 Reliability`、`08 Incident Response` 與 `09 Performance` 的服務頁，把 workload、telemetry、verification、workflow、capacity 與 cost 分層。
6. 整理 `07 Security` 的服務群路由，把 identity、IAM、secrets、KMS、WAF、PKI、supply chain、SIEM 與 DLP 連回控制面風險。
7. 依服務頁暴露出的缺口再開 deep article 與 migration playbook，並把案例回寫到對應主章、artifact 或知識卡。

## 完成判準

真實服務討論完成時，讀者應能從一個服務壓力走到具體服務取捨。看到「高峰售票」時，讀者能判斷 DynamoDB、Redis、queue、waiting room、load balancer 與 game day 各自承擔哪一段責任；看到「多租戶 SaaS 資料成長」時，讀者能判斷 PostgreSQL、MySQL sharding、Aurora、DynamoDB 或 Spanner 的機會成本。

每篇服務頁完成後要檢查三件事：第一，是否回扣分類共同認知；第二，是否引用至少一個案例或明確說明案例缺口；第三，是否提供下一步路由到主章、案例、artifact 或知識卡。
