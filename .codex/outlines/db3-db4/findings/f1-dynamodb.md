# F1：DynamoDB Case Audit Findings

## Audit 範圍跟邊際遞減判讀

讀完 9 個 DynamoDB case 全文（不只 frontmatter / description）、抽 finding 來校準 db3-db4/dynamodb/ 5 篇 L5 outline。

**Case 類型分類**：

| Case            | 類型   | 判讀依據                                                                                                                                                 |
| --------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 9.C5 Amazon Ads | rich   | 具體數字（90M reads/sec、5M writes/sec、99.999%、讀寫比 18:1）+ 判讀「為什麼可以這樣設計」三條 + 警惕段（容量規劃三口徑）                                |
| 9.C15 Tixcraft  | rich   | 完整數字表（20→135K IOPS、6→800 servers、$4200、0.26%）+ 完整架構描述 + 三個非直覺判讀 + 限流盲點警惕                                                    |
| 9.C18 Zoom      | medium | 一個核心數字（10M→300M、30x）+ 結構性 vs 暫時性 frame、無 partition / latency 具體數字                                                                   |
| 9.C19 Capcom    | medium | single-digit ms + 30% cost + billions（無單位）、multi-IP 平台共用 frame、DAX 是 case 策略段提到但非觀察事實                                             |
| 9.C20 Zomato    | rich   | 完整對照表（2K→8K RPM、-90%、-50%、10M events/day、350K 餐廳）+ TiDB over-provision 動機 + 警惕段（p50 vs p99）                                          |
| 9.C24 Genesys   | rich   | 完整數字表（15+5 region、99.999%、8000+ orgs、12 個月滾動）+「DynamoDB by default」治理引言 + 警惕段（滾動指標非永久）                                   |
| 9.C26 PayPay    | medium | 一個核心數字（3 億 / 天 ≈ 3500/sec 平均）+ 通知 vs 訊息分類、TTL、下游 APNs frame、無 partition / latency 數字                                           |
| 9.C27 Disney+   | medium | 「billions of actions daily」無單位、5:1 讀寫比是判讀層推估非 case 事實 + 新片發布 predictable-peak frame + cross-device sync frame                      |
| 9.C29 Lemino    | rich   | 完整數字表（5M MAU / 3 個月、30 channels、tens of thousands req/sec、90% 工時下降、AWS Media Services 完整 stack）+ connection limit 動機引言 + DAX 策略 |

**邊際遞減判讀**：

- Case 1-5（C5、C15、C18、C19、C20）：每 case 平均 2.5-3 個純新議題、純新議題 ~85%
- Case 6-7（C24、C26）：純新議題降到 ~70%、出現重複 frame（multi-region active-active、TTL / idempotency 跟 C26 / C29 重疊）
- Case 8-9（C27、C28）：純新議題降到 ~50%、predictable-peak / cross-device sync / connection-limit / DAX 都在前面 case 已出現過或可合成
- **Stop signal 觸發**：C29（第 9 個 case）— 純新議題 < 1 個（只揭露「connection limit 是 RDB 隱性 bottleneck」一個新議題）、重複 frame > 50%（control plane vs data plane、multi-region active-active、TTL、DAX 全是 C18 / C24 / C26 / C19 已揭露）
- 預計再讀更多 DynamoDB case 邊際效益低、應停止本輪

## Findings 列表

### Finding F1.1：Hot partition 的 *表現形式* 隨 capacity mode 變化

- **來源**：9.C15 Tixcraft「策略」段第 5 條 + 警惕段、9.C5 Amazon Ads「判讀」段第 2 條（partition 容量是「每 partition 上限 × partition 數量」、最熱 partition saturation）
- **Case 類型**：rich (C15) + rich (C5)
- **揭露內容**：partition key 不均勻時、provisioned 模式表現為 throttle event 立即可見、on-demand 模式表現為 latency spike（「DynamoDB 寫入排隊本身就是隱性限流」、C15 講限流不一定看得到 component）。Hot partition 不是 capacity mode 的問題、是 schema 的問題、mode 切換不解決。
- **Outline mapping**：
  - 已覆蓋於：`partition-key-antipatterns.md` 失敗 Case 5「on-demand 模式以為不會 hot partition」、`on-demand-vs-provisioned.md` 失敗 Case 3「on-demand hot partition 隱藏」
  - 該補但漏了：兩篇都沒互引「同一現象在兩種 mode 下的不同表現」、應在 sibling 段把這條 frame 列為主要交叉議題
  - Outline 缺口：無新主題、但兩篇 outline 該強化 mode × partition 設計的交叉判讀（不是各寫各的）

### Finding F1.2：Partition key 設計是 KV 容量的 *第一決策*、不是補救項

- **來源**：9.C5 Amazon Ads「策略」段第 1 條 + 「判讀」段第 2 條、9.C15 Tixcraft「策略」段第 2 條（「partition key 設計是 flash-sale 的命脈」、composite key 或 write sharding）
- **Case 類型**：rich (C5 + C15)
- **揭露內容**：partition key 不只是設計選擇、是「容量上限的決定變數」。C5 揭露「容量 = 每 partition 上限 × partition 數量」（不是表面 capacity 設定）；C15 揭露「6750 倍 IOPS 彈性不是 vendor 魔法、是 partition key 均勻分散的結果」。Composite key（`event_id + user_id_hash`）或 write sharding（`event_id + random_suffix`）是針對天然 hot key（event_id、user_id 為 bot）的兩種解法。
- **Outline mapping**：
  - 已覆蓋於：`partition-key-antipatterns.md` 整篇 + `single-table-design-pattern.md` 操作流程
  - 該補但漏了：`partition-key-antipatterns.md` 提到 calculated shard（`hash(user_id) % N`）跟 random shard 的差異、但 case 沒揭露這個分歧、屬於通用工程知識（標明 fact vs derive）
  - Outline 缺口：無

### Finding F1.3：DynamoDB 作為 *durable queue* / 寫入緩衝、不是 OLTP

- **來源**：9.C15 Tixcraft「判讀」段第 1 條（「DynamoDB 作為寫入緩衝、不是 OLTP」、傳統 server 用自己能承受的速度消費）
- **Case 類型**：rich (C15)
- **揭露內容**：拓元用 DynamoDB 接「訂單」寫入、不是即時生效、是讓 traditional server（金流 / 票庫）用自己能承受的速度消費。架構上 DynamoDB 扮演 *durable queue*、不是傳統 OLTP DB。這層解耦讓「前端可以擴 130 倍、後端不用同步擴」。
- **Outline mapping**：
  - 已覆蓋於：無（5 篇 outline 都沒講「DynamoDB 當寫入緩衝 / durable queue」這個 access pattern）
  - 該補但漏了：`single-table-design-pattern.md` 失敗模式有「DynamoDB 當 RDBMS 用」、但沒對照「DynamoDB 當 durable queue」這個*正確*的非 OLTP 用法
  - Outline 缺口：應在 `single-table-design-pattern.md` 補一條 *正向* anti-recommendation — 「DynamoDB 適合作為寫入緩衝層、後端非 DynamoDB 服務按自己節奏消費；不適合作為 strongly consistent OLTP 入口」。或考慮新 outline「DynamoDB 的 non-OLTP access pattern：write-buffer、durable queue、event log」

### Finding F1.4：讀寫比 *變化* 比讀寫比本身更重要

- **來源**：9.C5 Amazon Ads「策略」段第 2 條（「read-heavy 跟 write-heavy 比例變化是容量警訊」、新增即時報表會讓讀寫比跳一個量級）
- **Case 類型**：rich (C5)
- **揭露內容**：讀寫比 18:1（C5）跟 5:1（C27 推估）這種絕對值對容量規劃不是最重要；*業務邏輯改變導致比例跳一個量級* 才是真正的容量警訊。對應觀測上要持續追蹤「比例變化」這個 metric。
- **Outline mapping**：
  - 已覆蓋於：無
  - 該補但漏了：`on-demand-vs-provisioned.md` 操作流程 Step 1 講「過去 30 天 RCU/WCU」、但只看絕對值、沒看「比例變化」這個訊號
  - Outline 缺口：`on-demand-vs-provisioned.md` 容量觀測段該補「read/write ratio trend 變化」是 capacity mode 重新評估的觸發訊號

### Finding F1.5：Sustained workload vs spike workload 的 mode 選擇

- **來源**：9.C5 Amazon Ads「策略」段第 3 條（「Amazon Ads 這種 sustained workload 通常用 provisioned + auto scaling、不用 on-demand」）+ 9.C20 Zomato「策略」段第 4 條（「突發流量適合 on-demand、可預測流量適合 provisioned」）+ 9.C18 Zoom「策略」段第 3 條（30x 永久 baseline 上移後、要重新評估 on-demand 成本）
- **Case 類型**：rich (C5 + C20) + medium (C18)
- **揭露內容**：on-demand 不是 sustained workload 的預設選擇。C5 明示「廣告量測這種 sustained 用 provisioned + auto scaling」；C18 揭露 surge *永久 baseline 上移* 後、原本 on-demand 成本會變不划算、要重新算 cross-over。C20 揭露 TiDB over-provision 痛點 → on-demand 划算只在「當下流量」、未來流量繼續成長後可能反轉。
- **Outline mapping**：
  - 已覆蓋於：`on-demand-vs-provisioned.md` 操作流程 Step 2 決策樹（peak/avg > 5x → on-demand、穩定 → provisioned + scheduled）
  - 該補但漏了：outline 講「peak/avg > 5x」這個 threshold 是 LLM 自生數字、不是 case 揭露的具體閾值。C5 / C20 都沒給具體 ratio 數字。Outline 該標明這 threshold 是經驗值、非 case 來源
  - Outline 缺口：`on-demand-vs-provisioned.md` 該補「surge 後 baseline 永久上移」這個失敗模式 — Zoom 30x 不是暫時的、原 on-demand 設計會持續燒錢、長期要 re-evaluate

### Finding F1.6：控制面（control plane）vs 資料面（data plane）分離

- **來源**：9.C18 Zoom「判讀」段第 3 條（「媒體串流不在 DynamoDB」、DynamoDB 只承擔 control plane、影音流量是 P2P + edge servers）+ 9.C27 Disney+「策略」段第 1 條（metadata 用 DynamoDB、content 用 CDN + S3）+ 9.C19 Capcom「策略」段第 2 條（EKS 跑 game server、DynamoDB 處理持久狀態、中間 DAX）
- **Case 類型**：medium (C18) + medium (C27) + medium (C19)
- **揭露內容**：DynamoDB 是 control plane 的 KV、不是承擔大數據傳輸的 data plane。三個 case（Zoom 視訊、Disney+ 串流、Capcom 遊戲）都重複這個 frame — DynamoDB 處理 metadata / state、實際大流量走 CDN / WebRTC / game server。這個分離是 surge 能撐的前提。
- **Outline mapping**：
  - 已覆蓋於：無（5 篇 outline 都沒講「DynamoDB 是 control plane 角色」這個 anti-anti-pattern）
  - 該補但漏了：`single-table-design-pattern.md` 應在邊界段補「DynamoDB 適合 metadata / state、不適合存大型 BLOB / 影音 / 全文搜尋」、跟資料面分開
  - Outline 缺口：可能值得在某篇 outline（或 db3-db4 共用 prelude）補「DynamoDB 在系統中的角色定位」段

### Finding F1.7：RDB connection limit 是 surge 的 *第一個爆點*、不是 CPU / disk

- **來源**：9.C29 Lemino「判讀」段第 1 條（「connection limits became bottlenecks when experiencing a rapid increase in access」、PostgreSQL/MySQL 每連線吃記憶體 / process、pool 上限 1K-5K、DynamoDB HTTP API 無 connection state）+ 9.C20 Zomato 同類動機
- **Case 類型**：rich (C29) + rich (C20)
- **揭露內容**：傳統 RDB 在 surge 下、第一個爆的不是 CPU 也不是 disk、是 *連線數量*。connection pool 上限 1K-5K 是隱性的容量天花板。DynamoDB 的 HTTP API（無 long-lived connection）天然解這個問題。這是 Lemino 選 DynamoDB 而非繼續 Aurora 的判讀關鍵（雖然 Lemino 也用 Aurora）。
- **Outline mapping**：
  - 已覆蓋於：`single-table-design-pattern.md` 邊界段提到 Lemino 「connection-bound RDB → single-table DynamoDB 不只是換 vendor」、但沒展開機制
  - 該補但漏了：`single-table-design-pattern.md` 跟 `on-demand-vs-provisioned.md` 都該在「為什麼選 DynamoDB」段補 connection limit 機制
  - Outline 缺口：考慮在某篇 outline 補「DynamoDB 的 HTTP API 模型 vs RDB connection pool」對照段、揭露為何 DynamoDB 在 surge 下不會踩 RDB 的隱性 connection 天花板

### Finding F1.8：DAX 是讀峰值持續高時的標準補位、不是預設配置

- **來源**：9.C29 Lemino「策略」段第 3 條（「DAX 是 DynamoDB 讀 cache 的標準解法」、讀峰值持續高 / 熱門節目首播）+ 9.C19 Capcom「判讀」段第 2 條（single-digit ms 反推 Capcom 必須用 sub-region cache + DynamoDB DAX、不能單靠 DynamoDB）
- **Case 類型**：rich (C29) + medium (C19) — C19 的 DAX 是判讀層推論（「反推」這個詞）、不是 case fact
- **揭露內容**：DAX 不是 DynamoDB 預設配置、是「讀峰值持續高時的補位」。C29 用「當讀峰值持續高、加 DAX 減少 DynamoDB 讀次數、降低成本」這個觸發條件。C19 的 DAX 是作者從「single-digit ms」反推、不是 Capcom 公開揭露用 DAX。
- **Outline mapping**：
  - 已覆蓋於：無（5 篇 outline 都沒提 DAX）
  - 該補但漏了：`on-demand-vs-provisioned.md` 跟 `gsi-lsi-design.md` 該提 DAX 作為讀峰值補位
  - Outline 缺口：考慮加新 sibling outline「DAX / Cache 加速層：什麼時候該加、cost vs latency 取捨」、或併入既有 outline 的延伸段。引用 C19 時要標明「DAX 是作者判讀層推論、Capcom 並沒公開使用」

### Finding F1.9：「DynamoDB by default、用其他要 justify」的 *governance* frame

- **來源**：9.C24 Genesys「觀察」段引言（Chief Architect Rob Gevers: 「Amazon DynamoDB is our primary data layer by default, and teams have to justify the use of something else.」）+「判讀」段第 2 條
- **Case 類型**：rich (C24)
- **揭露內容**：Genesys 不是「評估每個 use case 選 DB」、是 *預設一個 DB、特殊需求才 justify*。這個治理模式 vs Netflix Aurora consolidation 是同訴求不同實作。Frame 屬於組織 / 治理層、不是技術層。
- **Outline mapping**：
  - 已覆蓋於：無（5 篇 outline 都是技術視角、沒覆蓋 governance 模式）
  - 該補但漏了：可能屬 outline 範圍外（governance frame 該寫在 backend/00 服務選型模組、不是 vendor deep article）
  - Outline 缺口：finding 揭露 *outline 跟治理模組的 cross-link 機會*、不是新 outline 主題

### Finding F1.10：99.999% 是 *滾動* 指標、不是永久承諾

- **來源**：9.C24 Genesys 警惕段第 1 條（「99.999% over 12 months 是截至特定時間點的歷史值、不代表未來持續達成。可用性是滾動指標、不是恆久承諾」）+ 9.C5 Amazon Ads 警惕段（「9000 萬 reads/sec 通常是年度峰值的最高一秒、不是平均值。容量規劃要區分『最大瞬時』『99 百分位平均』『常態流量』三個不同口徑」）
- **Case 類型**：rich (C24) + rich (C5)
- **揭露內容**：vendor 案例敘述的「99.999%」「90M reads/sec」是 *滾動視窗 / 峰值* 數字、不是恆久承諾或平均值。讀 case 時要區分 latency / availability 的「最大瞬時 vs 99 百分位 vs 常態」三口徑。這也對應 C20 Zomato 警惕段「90% 延遲降可能只是 p50、p99/p999 改善幅度通常較小」。
- **Outline mapping**：
  - 已覆蓋於：無
  - 該補但漏了：`global-tables-conflict.md` 講 99.99% / 99.999% SLA、但沒明示「滾動指標 vs 永久承諾」這個讀法
  - Outline 缺口：`global-tables-conflict.md` 跟 `on-demand-vs-provisioned.md` 容量觀測段該補「指標口徑分層」這個判讀紀律 — 看 case 數字要問是哪個口徑

### Finding F1.11：多 region 是 *成本 vs 可用性的硬取捨*、不是預設

- **來源**：9.C24 Genesys「策略」段第 4 條（「15 個 region 的成本約是 1 個 region 的 15 倍 — 對 B2B SaaS 是合理投資、對 B2C 通常不划算」）+「Anti-recommendation」對應 outline 「single-region availability 已達 99.95% + RTO 可接受 1 小時 + 預算敏感 → 用 PITR + 跨 region backup 而非 Global Tables」
- **Case 類型**：rich (C24)
- **揭露內容**：Global Tables 不是預設選擇、是 B2B SaaS 跟 99.99%+ SLA 場景才划算。15 region 成本 = 15x 單 region。對 B2C 通常不划算。
- **Outline mapping**：
  - 已覆蓋於：`global-tables-conflict.md` Anti-recommendation 段（PITR + cross-region backup 替代方案）+ 容量觀測段（4 region ≈ 4.5x cost）
  - 該補但漏了：`global-tables-conflict.md` 該再強化 B2B vs B2C 業務取捨、不只是技術 cost 數字
  - Outline 缺口：無、outline 已覆蓋

### Finding F1.12：B2B SaaS 跟 B2C 的可用性目標 *質* 不同

- **來源**：9.C24 Genesys「判讀」段第 1 條（「B2C 大型網站可能接受 99.9%（年停機 8.76 小時）、B2B SaaS 經常合約規定 99.95% 或 99.99%、客服平台類甚至要 99.999%（年停機 5 分鐘）。每多一個 9、容量規劃跟運維成本指數成長」）
- **Case 類型**：rich (C24)
- **揭露內容**：可用性目標不是「越高越好」、是「業務性質決定下限」。B2B 合約義務、B2C 用戶忍受度、客服平台合約客戶停線損失。每多一個 9 成本指數成長。
- **Outline mapping**：
  - 已覆蓋於：無（5 篇 outline 都沒講「可用性目標的業務 driver」）
  - 該補但漏了：`global-tables-conflict.md` 問題情境段「B2B SaaS 跟客戶 SLA 寫 99.99%」一筆帶過、沒展開 B2B vs B2C frame
  - Outline 缺口：finding 屬於跨 outline 的 prelude / 前置論述、不是某篇 outline 的主議題

### Finding F1.13：DynamoDB Streams 是 conflict 偵測跟 reconciliation 的工程入口

- **來源**：9.C26 PayPay「策略」段第 1 條（「通知（payment received）是 transactional、不可丟失；訊息（marketing）可以丟失部分」、區分需求）— 隱含 idempotency + retry 機制
- **Case 類型**：medium (C26)
- **揭露內容**：PayPay case 揭露「通知 vs 訊息」需求分層、隱含 DynamoDB 上要做 idempotency + retry 偵測。對應 global-tables 的 conflict 偵測機制（DynamoDB Streams + Lambda 比較 timestamp 抓 conflict）。Case 本身沒講 Streams、是 outline 從通用工程知識補的。
- **Outline mapping**：
  - 已覆蓋於：`global-tables-conflict.md` 操作流程 Step 5 + 6（DynamoDB Streams 訂閱 + Lambda 比較 timestamp + 進 SQS reconciliation）
  - 該補但漏了：outline 引用 C26 時要小心 — case 沒明示 PayPay 用 Streams。引用要標「fact vs derive」分層
  - Outline 缺口：無、但 outline 的 PayPay 引用該降溫成「揭露需求分層、Streams 為通用工程實作」

### Finding F1.14：TTL 是 storage cost 防爆的標配、特別在 message workload

- **來源**：9.C26 PayPay「策略」段第 2 條（「TTL 自動清理避免 storage 成本爆炸」、3 億 / 天 × 30 天 = 90 億筆記錄、不清理會撐死 storage 預算）
- **Case 類型**：medium (C26)
- **揭露內容**：訊息類 workload（每天大量寫入、舊資料價值快速衰減）必須用 TTL 自動清理、否則 storage cost 爆炸。3 億 / 天 × 30 天 = 90 億筆是 case 推算的具體數字。
- **Outline mapping**：
  - 已覆蓋於：無（5 篇 outline 都沒提 TTL）
  - 該補但漏了：`single-table-design-pattern.md` 跟 `on-demand-vs-provisioned.md` 容量觀測段該提 TTL 作為 storage cost 控制
  - Outline 缺口：考慮加 sibling outline「DynamoDB TTL：access pattern、storage cost 控制、跟 Streams 的互動」、或併入既有 outline

### Finding F1.15：下游 quota 是隱性瓶頸（APNs / FCM / SMS gateway）

- **來源**：9.C26 PayPay「策略」段第 3 條（「訊息推送的下游（APNs、FCM、SMS gateway）是隱性瓶頸」、DynamoDB 寫入可以撐 3K msg/sec、但 APNs 一天的 quota 是有限的）
- **Case 類型**：medium (C26)
- **揭露內容**：DynamoDB 容量規劃只看 DynamoDB 自己不夠、必須看 *下游 dependency 的 quota*。APNs 有 quota、FCM 有 quota、SMS gateway 有費率限制。整體系統的瓶頸可能在下游、不在 DynamoDB。
- **Outline mapping**：
  - 已覆蓋於：無
  - 該補但漏了：屬 9.5 瓶頸定位流程的範圍、不是 vendor deep article 主議題
  - Outline 缺口：cross-link 機會、不是新 outline 主題

### Finding F1.16：「新片發布」是 predictable-peak、跟 flash-sale 不同

- **來源**：9.C27 Disney+「判讀」段第 2 條（「Marvel / Star Wars / Disney 動畫 新片上線首日、metadata 流量可衝 3-5 倍 — 因為全平台用戶同時打開該片頁面。這比一般 Black Friday 集中、像 Hotstar IPL 的集中型流量」）+「策略」段第 2 條（「新片發布像 mini Black Friday、要 pre-scaling」、提前 1-2 天 pre-scale capacity）
- **Case 類型**：medium (C27)
- **揭露內容**：predictable-peak 跟 flash-sale 是不同負載形狀。flash-sale（C15 拓元）t=0 起跳 / t=300 結束、predictable-peak（新片發布）是有預期時段但持續較長、用戶不同步打開。Pre-scaling 1-2 天前是合理的應對。
- **Outline mapping**：
  - 已覆蓋於：`on-demand-vs-provisioned.md` 操作流程 Step 4「scheduled scaling」+ 失敗 Case 2「auto-scaling 跟不上 spike」
  - 該補但漏了：outline 區分 flash-sale 跟 predictable-peak 不夠細、scheduled scaling 跟 on-demand 在兩種負載下的選擇沒展開
  - Outline 缺口：`on-demand-vs-provisioned.md` 操作流程 Step 4 該補「predictable-peak vs flash-sale 的 scheduled scaling 策略差異」

### Finding F1.17：Cross-device 即時同步是 Global Tables 的 *正向* 用例

- **來源**：9.C27 Disney+「判讀」段第 3 條（「watchlist + 播放進度需要跨裝置即時同步。用戶在手機看到一半、晚上回家用電視繼續、進度必須跨裝置同步。這層需求對 DynamoDB Global Tables（multi-region active-active）特別適合」）
- **Case 類型**：medium (C27)
- **揭露內容**：Global Tables 不只是 DR / availability、也是 cross-device sync 的工程方案。用戶在不同 region 登入同帳號、寫入自動同步。最終一致性可接受場景。
- **Outline mapping**：
  - 已覆蓋於：`global-tables-conflict.md` 邊界段提到 Disney+ cross-device frame、操作流程 Step 1 提到 region-pinned vs global data 分類
  - 該補但漏了：outline 主軸是 conflict / LWW、cross-device sync 這個 *正向用例* 沒展開
  - Outline 缺口：`global-tables-conflict.md` 該補「Global Tables 的 *正向* access pattern：cross-device sync、global read、DR failover」一段、不只講 conflict 問題

### Finding F1.18：「DBA 工時釋放」是 managed 服務的真實成本價值

- **來源**：9.C19 Capcom「判讀」段第 3 條（「『工程資源從 DB 運維轉到遊戲品質』是 managed 服務的真實價值。Capcom 不是 IT 公司、是遊戲公司。把 DBA 時間從 Postgres patching、replication 設定、backup 排程 釋放到 遊戲機制設計、玩家行為分析、才是 30% 成本下降的本質」）+ 9.C29 Lemino「判讀」段第 3 條（90% 工程工時下降）
- **Case 類型**：medium (C19) + rich (C29)
- **揭露內容**：DynamoDB 的「成本」評估不只看 cost-per-request 或 monthly bill、要算 *DBA 工時釋放* 的人力成本工程化。Capcom 30% 成本下降、Lemino 90% 工時下降都是這個維度。
- **Outline mapping**：
  - 已覆蓋於：`on-demand-vs-provisioned.md` 問題情境段「於是省了多少 SRE 工時、又多花多少 cost」（finance 反問）— 提到但沒展開
  - 該補但漏了：`on-demand-vs-provisioned.md` 該補「總成本 = direct cost + 工程工時釋放」公式、不只看 monthly bill
  - Outline 缺口：finding 屬 outline 的策略段補強、不是新主題

### Finding F1.19：遷移評估要看 *總成本曲線*、不是 *當下 snapshot*

- **來源**：9.C20 Zomato 警惕段第 1 條（「成本降 50% 是當下流量下的對照。如果未來流量繼續成長、DynamoDB 的 cost-per-request 成長率比 TiDB 自管 cluster 高 — 達到某規模後 TiDB 反而更便宜。讀遷移案例要看『在當下流量下划算』、不等於『永遠划算』」）+「策略」段第 2 條（算未來 12-24 個月成本對照）
- **Case 類型**：rich (C20)
- **揭露內容**：DynamoDB 跟自管 cluster 的 cost crossover 隨流量規模變化。某流量下 DynamoDB 划算、流量再大反而自管 cluster 便宜。遷移評估必須算「未來 12-24 個月在預期流量下的成本對照」、不是當下 snapshot。
- **Outline mapping**：
  - 已覆蓋於：`on-demand-vs-provisioned.md` 操作流程 Step 5 + Cost gate 段
  - 該補但漏了：`on-demand-vs-provisioned.md` 沒講「DynamoDB vs 自管 cluster 的 cost crossover」這個更上層的決策
  - Outline 缺口：`on-demand-vs-provisioned.md` 該補「DynamoDB vs 自管 cluster cost crossover」一段、揭露 mode 選擇之上還有 vendor 選擇

### Finding F1.20：partition key 是否天然均勻決定 DynamoDB 適用度

- **來源**：9.C18 Zoom「判讀」段第 2 條（「DynamoDB 無限擴容對 SaaS 元資料層特別適用。Zoom 會議 metadata 是典型 KV 工作負載、partition key（meeting_id）天然均勻、不會 hot partition」）+ 9.C19 Capcom「策略」段第 1 條（partition key 用 player_id 天然均勻）+ 9.C26 PayPay「判讀」段第 2 條（每則訊息有獨立 message_id、partition key 天然均勻）+ 9.C27 Disney+「判讀」段第 1 條（partition key 通常用 user_id、天然均勻）
- **Case 類型**：medium (C18 + C19 + C26 + C27) — 跨 4 個 case 重複 frame
- **揭露內容**：四個 case 都揭露同一 frame — DynamoDB 適合「partition key 天然均勻」的 workload（meeting_id、player_id、message_id、user_id）。反之售票（event_id）、時間序（date）這種 *天然不均勻* 的 workload 需要 composite key 修補。partition key 是否天然均勻是 *DynamoDB 適用度* 的第一判讀條件。
- **Outline mapping**：
  - 已覆蓋於：`partition-key-antipatterns.md` 失敗模式 Case 1（時間序）、Case 2（bot user）
  - 該補但漏了：outline 主要從 *反* 模式切入（hot partition）、沒從 *正* 模式切入（天然均勻 PK 為什麼好）。`single-table-design-pattern.md` 的 access pattern 設計也該強調這個前置判讀
  - Outline 缺口：`single-table-design-pattern.md` 問題情境段該補「DynamoDB 適用度第一判讀：partition key 是否天然均勻」、作為 access pattern 設計的前置條件

### Finding F1.21：架構解耦讓「前端可擴 130x、後端不用同步擴」

- **來源**：9.C15 Tixcraft「判讀」段第 1 條（DynamoDB 寫入緩衝 → 「這層解耦讓前端可以擴 130 倍、後端不用同步擴、避免後端被前端拖垮」）+「策略」段第 4 條（付款層獨立、不被搶票流量影響）
- **Case 類型**：rich (C15)
- **揭露內容**：flash-sale 的核心架構不是「整體擴 130 倍」、是「前端擴 130 倍 + 後端用自己節奏消費」的解耦。這層解耦讓「短時間吸收洪峰」跟「實際處理」分離。付款層獨立又是另一層解耦。
- **Outline mapping**：
  - 已覆蓋於：無（5 篇 outline 都偏 DynamoDB 內部設計、沒講「DynamoDB 在解耦架構中的角色」）
  - 該補但漏了：屬於 03 訊息佇列模組 / 09 容量規劃模組的範圍、不是 vendor deep article 主議題
  - Outline 缺口：cross-link 機會、`single-table-design-pattern.md` 邊界段可補「DynamoDB 作為解耦層的 access pattern」cross-link

### Finding F1.22：On-demand mode 在 surge 下的「無痕」表現是工程陷阱

- **來源**：9.C18 Zoom「判讀」段警惕段（「『nearly infinitely』是行銷敘述、不是工程承諾。實務上 Zoom 在 COVID 初期確實遇到 outage 與性能問題、後續才穩定」）+ on-demand 隱藏 hot partition 議題（F1.1）合成
- **Case 類型**：medium (C18)
- **揭露內容**：vendor 案例敘述 surge 時「nearly infinitely」這種敘述要折扣讀。實際 Zoom 在 COVID 初期遇到 outage 跟性能問題、是後續才穩定。讀 case 要看 *最終狀態* 跟 *過程中的 incident*、不要只看 happy ending。
- **Outline mapping**：
  - 已覆蓋於：`on-demand-vs-provisioned.md` 失敗 Case 3「on-demand hot partition 隱藏」
  - 該補但漏了：outline 沒講「vendor case 的『無痛 surge』敘述要折扣讀」這層 meta 判讀
  - Outline 缺口：屬 vendor article 寫作方法論、非單篇 outline 主題

## Outline 校準建議

### Keep（findings 充分支撐、結構合理）

- **`partition-key-antipatterns.md`**：F1.1 / F1.2 / F1.20 充分支撐 hot partition / composite key / write sharding 主軸。Tixcraft（C15）作為主 case、Lemino（C29）作為補 case 對齊。outline 已覆蓋核心議題、無需改 framing
- **`global-tables-conflict.md`**：F1.10 / F1.11 / F1.12 / F1.13 / F1.17 支撐 conflict / LWW / multi-region cost / cross-device sync 主軸。Genesys（C24）作為主 case、PayPay（C26）作為補 case 對齊

### Rewrite（findings 揭露 framing 該改）

- **`single-table-design-pattern.md`**：當前 framing 偏「access pattern 反推 PK/SK」、但 F1.3（DynamoDB 當寫入緩衝）/ F1.6（control plane vs data plane）/ F1.7（connection limit 解放）/ F1.20（PK 天然均勻是前置判讀）揭露 outline 該在 *問題情境* 段補「DynamoDB 適用度 / 不適用度」的前置判讀、不是直接跳到 PK/SK 設計
- **`on-demand-vs-provisioned.md`**：當前 framing 偏 cost mode 選擇、但 F1.4（讀寫比變化）/ F1.5（surge 永久 baseline 上移）/ F1.16（predictable-peak vs flash-sale 的 scheduled scaling）/ F1.18（DBA 工時釋放）/ F1.19（vendor 跟自管 cost crossover）揭露 mode 選擇之上還有更多軸 — outline 該擴充決策維度、不只是 peak/avg ratio 閾值

### Add（findings 揭露但 outline 沒覆蓋的新主題）

- 考慮新 outline：**DAX / Cache 加速層**（findings F1.8）— 何時加、cost vs latency 取捨。但 case 揭露相對單薄（只 C29 明示、C19 是 derive）、可考慮併入 `on-demand-vs-provisioned.md` 或 `gsi-lsi-design.md` 延伸段、不另開
- 考慮新 outline：**DynamoDB TTL：access pattern、storage cost、跟 Streams 互動**（findings F1.14）— 在訊息類 / 事件類 workload 是標配、但 5 篇 outline 都沒提。case 揭露相對單薄（只 C26 明示）、可考慮併入 `single-table-design-pattern.md` 容量觀測段
- 考慮新 outline：**DynamoDB 的 non-OLTP access pattern：write-buffer、durable queue、event log**（findings F1.3）— C15 揭露的核心 frame、跟主流 access pattern article 互補

### Scope warning（outline *over-extrapolation* 風險）

- **`on-demand-vs-provisioned.md` 操作流程 Step 2「peak/avg > 5x → on-demand」**：5x 這個閾值是 outline 自生數字、不是 C5 / C20 揭露。寫稿時要標明「5x 為經驗值、case 沒明示 threshold」、避免讀者誤以為 case 揭露此具體閾值
- **`on-demand-vs-provisioned.md` 操作流程 Step 4「scheduled scaling 30-60 分鐘前」**：30-60 分鐘是 outline 自生、不是 case 揭露
- **`partition-key-antipatterns.md` 操作流程 Step 2「shard 數 10-100、單 logical key 峰值 WCU 除以 800」**：這些具體數字是通用工程知識、case（C15）只揭露「composite key 分散」概念、沒給 shard 數量。寫稿要標明 fact vs derive 分層
- **`gsi-lsi-design.md` 失敗模式 Case 4「LSI 數量上限 5 個」**：屬 vendor 規格事實、需 cross-verify AWS doc、case 沒揭露
- **`global-tables-conflict.md` 操作流程 Step 4「idempotency 加 request_id 或 client_timestamp」**：通用工程知識、PayPay 案例沒明示。引用 C26 時要小心 — case 揭露「通知不可丟失」需求、但沒揭露具體 idempotency 實作。對應 case-first 方法論的「medium case 實作層擴寫過頭」陷阱
- **`gsi-lsi-design.md` 容量段「GSI 多時 cost 容易超過 base table」**：通用工程知識、Disney+ / Capcom case 沒揭露 GSI 具體 cost ratio

## 跨章節 frame

讀完 9 個 case 浮現的跨章節 frame、影響整體 DB3 reader journey：

### Frame 1：DynamoDB 適用度的 *前置判讀條件*

5 篇 outline 都跳過「DynamoDB 是否適合本 workload」這個前置判讀、直接進設計細節。但 9 個 case 重複揭露同一前置判讀：

- **Partition key 是否天然均勻**（meeting_id / player_id / message_id / user_id 天然均勻、event_id / date 天然不均勻、後者要 composite key 補救）
- **Workload 是 control plane 還是 data plane**（metadata / state 適合、影音 / 大型 BLOB 不適合）
- **Consistency 需求是否可接受 eventual**（最終一致性可接受才適合、strong consistency 必要走 SQL / NewSQL）
- **Access pattern 是否穩定**（< 5 個且查詢探索期不適合、變動頻繁不適合）

建議：考慮新增「DynamoDB 適用度判讀」outline 作為 prelude、或在每篇 outline 問題情境段強化此前置判讀

### Frame 2：架構解耦讓 DynamoDB 變得能撐 surge

C15 拓元（DynamoDB 當寫入緩衝、後端慢消費）/ C18 Zoom（control plane vs data plane 解耦）/ C19 Capcom（EKS game server + DynamoDB persistent state + DAX 中間層）/ C29 Lemino（DynamoDB 解 RDB connection limit）都揭露同一 frame — DynamoDB 「能撐」surge 不是 DynamoDB 自己神奇、是 *系統架構解耦* 的結果。DynamoDB 在解耦的某一層才發揮 surge 撐量價值。

建議：跨 outline 都該補「DynamoDB 在系統中的角色」段、避免讀者誤以為 DynamoDB 是 surge 萬靈丹

### Frame 3：On-demand 不是 sustained workload 的預設選擇

C5（廣告量測 sustained 用 provisioned + auto scaling）/ C18（Zoom surge 後 baseline 永久上移、原 on-demand 不再划算）/ C19（Capcom sustained）/ C24（Genesys sustained）/ C27（Disney+ sustained）/ C29（Lemino predictable）都揭露 sustained / predictable workload 應該用 provisioned。On-demand 適用於「peak/avg 高 + 不可預測」的 spike workload（C15 拓元、C20 Zomato 過渡期）。

當前 `on-demand-vs-provisioned.md` 已涵蓋這 frame、但 framing 偏「決策樹」、可考慮改成「workload 形狀 × mode 選擇」的二維對照、把 9 個 case 分類到二維 grid

### Frame 4：vendor case 數字要分 *口徑* 讀

C5（90M reads/sec 是年度峰值最高一秒、非平均）/ C20（90% latency 降可能只 p50、p99/p999 改善幅度小）/ C24（99.999% 是 12 個月滾動歷史值、非未來承諾）/ C18（「nearly infinitely」是行銷敘述）都重複這個 meta-frame — 讀 vendor case 數字要分「最大瞬時 / 99 百分位 / 常態」三口徑、區分「滾動指標 / 永久承諾」、把行銷敘述折扣。

建議：屬 vendor article 寫作方法論、不是單篇 outline 主議題、但每篇 outline 引用 case 數字時都該明示口徑

### Frame 5：DynamoDB 真實成本 = direct cost + DBA 工時釋放

C19 Capcom 30% 成本下降 = 工時釋放、C29 Lemino 90% 工時下降是 managed 服務的真實價值。`on-demand-vs-provisioned.md` 問題情境段已點到（「於是省了多少 SRE 工時、又多花多少 cost」）、但沒展開公式跟 case 證據。

建議：`on-demand-vs-provisioned.md` 策略段補「總成本評估公式」、展開 direct cost + 工時釋放雙軸
