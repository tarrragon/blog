# Cosmos DB MongoDB API vs SQL API：相容性、aggregation 差異、何時用哪個

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/)（含 Migration Playbook 6 規格面）與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：團隊已用 MongoDB / 考慮從 MongoDB Atlas 遷到 Azure、Cosmos DB 提供「MongoDB API（wire protocol 相容）」跟「native SQL API」兩條路；MongoDB API 的相容範圍隨 server version 演進、aggregation pipeline / index / change stream 行為跟原生 MongoDB 有差；SQL API 是 Cosmos DB native、能力最完整但要重寫
- 讀者徵兆：「MongoDB API 我們的 aggregation pipeline 跑得起來嗎」「`$lookup` 在 Cosmos DB MongoDB API 支援嗎」「change stream 跟 Change Feed 是同一回事嗎」「為什麼有人說 MongoDB API 只是過渡、最終要遷 SQL API」
- 真實壓力：Microsoft 自家 Microsoft 365 從 MongoDB 遷到 Cosmos DB MongoDB API、planet-scale 分析；中型 SaaS 評估 Atlas vs Cosmos DB MongoDB API 的 lock-in 成本
- Case anchor: [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — MongoDB → Cosmos DB MongoDB API、planet-scale 分析、dogfood 證據

### 為何選 Cosmos DB MongoDB API：vendor selection 的四層 framing

讀者真正在比的不是「兩個 API 哪個快」、是 *vendor selection* 的四層問題：(a) 三型遷移路徑哪一型、(b) dogfood signal 怎麼讀、(c) multi-model 差異化是否真用上、(d) 跨雲 hedging 還是單雲 lock-in。

#### Framing 1：document model 三型遷移路徑對照（F2.1、本章合成）

| 遷移型             | 案例                                                                     | 風險                              | ROI                                |
| ------------------ | ------------------------------------------------------------------------ | --------------------------------- | ---------------------------------- |
| 保留 + 補周邊      | 9.C36 Coinbase（mongobetween + freshness token + ML predictive scaling） | 低風險、漸進、保留 MongoDB 自管   | 中、解 connection storm 等特定瓶頸 |
| 同 DB 換託管       | 9.C37 Forbes（自管 → Atlas、6 個月）                                     | 中、Schema 跟 access pattern 保留 | 高、釋放 ops 人力                  |
| 同 model 換 vendor | 9.C30 Microsoft 365（MongoDB → Cosmos DB MongoDB API）                   | 高、底層架構換但 driver 保留      | 高、planet-scale 擴展性            |

**三型風險跟 ROI 完全不同**：本篇 outline 處理的是第三型「同 model 換 vendor」、不是 Forbes 的「同 DB 換託管」、也不是 Coinbase 的「保留 + 補周邊」— 開頭段必須明示三型差別、避免讀者把「換託管」跟「換 vendor」混為一談。Forbes 6 個月遷移成功 *不代表* Microsoft 365 也是 6 個月、底層架構換的工程複雜度遠高。

#### Framing 2：dogfood 是高權重 selection signal、但案例數字常不公開（F2.17）

- 9.C30 Microsoft 365 dogfood Cosmos DB、跟 Amazon Prime Day 用 DynamoDB、Google 自家用 Spanner 一樣 — 雲商旗艦 DB 都會用在自家旗艦產品。讀此類 dogfood 案例的權重應該高、因為「雲商自己賭身家」
- **Scope warning（必明示）**：9.C30 case 自承「沒有提具體 throughput、latency、cost 數字。Microsoft 內部數字通常不公開、跟 AWS / GCP 案例的數字密度差很多」 — 寫稿時 *只能引用 frame*（dogfood signal / multi-model / 遷移路徑）、不能編造數字、不能把 dogfood 當 production benchmark
- 9.C30 警示「『MongoDB 不夠用』是行銷話術。實際是 *MongoDB 在某些 workload pattern 下不夠用*」— 寫稿要明示這條 caveat、避免讀者把「Microsoft 從 MongoDB 遷出」當成「MongoDB 不行」的普遍結論

#### Framing 3：multi-model 是 Cosmos DB 的差異化價值（F2.16）

- 9.C30 Microsoft 365 策略段揭露：「Multi-model 是 Cosmos DB 的差異化價值」— 同一服務支援 SQL API / MongoDB API / Cassandra API / Gremlin / Table API、避免多個 DB 服務並存
- 跨雲對照：AWS DynamoDB（KV）+ DocumentDB（MongoDB-compatible）、GCP Firestore + Spanner + Bigtable — 各家用 *多個* 產品覆蓋 multi-model、Cosmos DB 是少數「單一產品支援 5 API」
- 對 vendor selection 的意義：若團隊預期同一系統需要 document + KV + graph 混用、Cosmos DB 的 multi-model 是 *運維單一服務* 的 selection unique value、不是只看「MongoDB 替代品」
- Anti-pattern：若團隊只用 MongoDB API、不用其他 API、multi-model 差異化價值對該團隊 *不成立*、不該變成 selection 理由

#### Framing 4：跨雲 hedging vs 單雲 lock-in 的 trade-off（F2.10）

- Atlas 提供 AWS / GCP / Azure 跨雲部署（9.C37 Forbes 用 GCP、但保留跨雲彈性）；Cosmos DB Azure-only、DynamoDB AWS-only、Spanner GCP-only — 三大單雲服務都是雲商鎖定
- 對 *未來雲商策略尚未底定* 的團隊、跨雲服務的選項保留價值高 — 這是 hedging 價值、不是「當下省錢」
- 對 *已綁定 Azure 生態* 的團隊（Microsoft 365 dogfood、企業 AAD / Office / Power Platform 整合）、Cosmos DB Azure-only 是 *Azure 整合的延伸*、不是 lock-in 損失
- 寫稿時必須明示這是 *未來不確定性 vs 當下整合* 的 hedging trade-off、不是「跨雲一定比較好」

## 核心機制（Vendor-specific mechanism）

- 兩個 API 的關係：底層是同一個 Cosmos DB 分散式 KV/document store、API layer 翻譯不同 wire protocol
- MongoDB API：
  - 相容 MongoDB wire protocol（時間敏感 claim、查最新支援版本如 6.0 / 7.0）
  - Driver 不變：直接用 mongo-go-driver / pymongo / mongoose 等
  - 翻譯層：MongoDB 操作翻譯成 Cosmos DB internal、不是真的跑 MongoDB engine
- SQL API：
  - Cosmos DB native query language（SQL-like、不是標準 SQL）
  - 直接操作 JSON document、ARRAY / nested field native 支援
  - 完整 Cosmos DB feature 支援（Change Feed、stored procedure、trigger）
- 關鍵差異點：
  - `$lookup`（join）：MongoDB API 支援度有限、跨 partition 性能差；SQL API 也沒 JOIN（document model 哲學）
  - Aggregation pipeline：部分 stage 不支援或行為不同（時間敏感、查支援列表）
  - Index：MongoDB API hint / explain 行為跟 native MongoDB 不同
  - Change stream：MongoDB API 提供 change stream wire compat、但底層是 Cosmos DB Change Feed（語義 / ordering / retention 有差）
  - Transaction：MongoDB API multi-document transaction 限制 partition、SQL API 也限同 partition
- 對應 knowledge card：[database](/backend/knowledge-cards/database/)、[change-data-capture](/backend/knowledge-cards/change-data-capture/)

## 操作流程（Operations）

- 選 API：建 account 時選 API kind、*無法事後切換*
- MongoDB API 連線：mongodb connection string、跟 Atlas 一樣
- SQL API 連線：Cosmos DB SDK（C# / Java / Node / Python）、document 直接操作
- 相容性驗證：用 [Data Migration Tool](https://github.com/Azure/azure-documentdb-datamigrationtool) 或自寫 script、把 production query corpus 跑一遍、列 unsupported / behavior-different 清單
- Aggregation pipeline 驗證：每個 pipeline stage 跑單元測、量 RU 消耗、對照 native MongoDB result
- 驗證點：
  - 相容性測試覆蓋 production query 90%
  - 每個 query 的 RU < SLA budget
  - Change stream lag < SLA
- Rollback boundary：API kind 不可改、rollback 等於 export → recreate account → import；MongoDB API → SQL API 需重寫 app

## Migration Playbook 6 規格面（MongoDB → Cosmos DB MongoDB API）

### Driver

- 主要 driver：Azure 生態 *整合* / 需要更好的 global distribution / Atlas 跨雲成本不必要（單雲團隊）
- No-go condition：
  - 跨雲需求（Atlas 仍是首選、Forbes 案例證據）
  - 需要 native MongoDB latest feature（MongoDB API server version 落後 native MongoDB）
  - 未來雲商策略未定（hedging 價值喪失）
  - 純 MongoDB 投資、無 Azure 生態其他服務整合（multi-model 差異化價值對該團隊不成立）

### Diff Audit

- **Schema**：document shape 不變（wire compat）；但 `_id` 行為跟 Cosmos DB partition key 綁定方式要審
- **Operational**：自管 MongoDB → managed Cosmos DB、replica set / sharding 變成 partition + region；備份 / monitoring 全換
- **Paradigm**：不變（仍 document）
- **Components**：MongoDB driver 保留、aggregation pipeline 部分需重寫
- **Application**：connection string、authentication mechanism（SCRAM → Azure key）、read preference 對應 consistency level
- **Topology**：replica set → multi-region replication、shard key → partition key
- Type 判定：**Type B drop-in（partial）**、wire compat 但有相容性 gap

### Phase Plan

- Phase 0：相容性 audit、列 unsupported aggregation stage
- Phase 1：partition key 設計（從 shard key 翻譯）
- Phase 2：bulk export-import（mongodump → Cosmos DB Data Migration Tool）
- Phase 3：CDC sync（MongoDB oplog → Azure Data Factory / 自寫）
- Phase 4：shadow read 驗證 query 一致性
- Phase 5：read cutover（讀切 Cosmos、寫仍 MongoDB）
- Phase 6：write cutover
- Phase 7：cleanup

### Evidence

- query 一致性 diff log、aggregation result checksum、RU consumption baseline、replication lag

### Cutover

- read-only window < 10 min、aggregation result 對齊驗證、rollback 條件（query error rate > 1%）

### Cleanup

- 退役 MongoDB cluster、保留 dump 90 天、退役 oplog connector

## 失敗模式（Failure modes）

- **假設 wire compat = 100% 行為相同**（F2.9 補強）：「100% wire compat」是 vendor 行銷話術、實際是「在某些 query pattern 下相容」；aggregation pipeline 跑出不同結果、上 production 才發現。9.C30 case 警示「『MongoDB 不夠用』是行銷話術。實際是 *MongoDB 在某些 workload pattern 下不夠用*」同模型反向適用 — *相容性* 也是「在某些 query pattern 下相容」、不是普遍相容。修法：production query corpus dual-write 跑一遍、case-by-case 驗證每個 query pattern、不能假設 wire compat = 行為 100% 一致
- `_id` 當 partition key：跟 MongoDB shard key 邏輯不同、容易 hot partition
- Change stream resume token 跨 API 不可用：MongoDB API change stream 的 resume token 跟原生 MongoDB 格式不同、跨環境 resume 失敗
- 評估時只測 happy path：unsupported aggregation stage 在 dev 看不出、production 才爆
- 選 MongoDB API 後想升級 feature：MongoDB API server version 升級節奏跟 native MongoDB 不同步、新 feature 等待時間長
- 不評估 SQL API：MongoDB API 永遠落後 native、若 long-term commit 到 Cosmos DB、SQL API 是更穩的選擇
- **把 dogfood 案例數字當 benchmark**（F2.17）：9.C30 Microsoft 365 case 自承沒提具體 throughput / latency / cost 數字、不能拿 dogfood 案例的「成功」推論「我們團隊遷過去也會成功」— 規模 / workload pattern / 團隊能力都不同

## 容量與觀測（Capacity & observability）

- 必看 metric：MongoDB API 特有的 `MongoRequests`、`MongoRequestCharge`；diagnostic log 看 aggregation stage 是否被翻譯成 cross-partition query
- 容量規劃：MongoDB API 翻譯層有 overhead、相同 query SQL API 通常便宜 10-20%
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：API kind 選擇進 cost forecast

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[partition-key-design](./partition-key-design.md)（shard key → partition key）、[ru-cost-model-sizing](./ru-cost-model-sizing.md)（MongoDB API 成本差異）、[consistency-levels-engineering](./consistency-levels-engineering.md)（read preference → consistency level）
- 跟 [MongoDB vendor](/backend/01-database/vendors/mongodb/) 對照、Atlas 跨雲 vs Cosmos DB Azure-only trade-off
- 跟 1.x 章節：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)

### Cosmos DB unique selection value 整合（vendor 選型 frame 收束）

讀者讀完本篇要能回答：「我該選 Cosmos DB MongoDB API、Cosmos DB SQL API、還是留 Atlas」— 答案的四層判讀（依本篇 framing 1-4 對應）：

- **遷移路徑**：你是要保留 + 補周邊、換託管、還是換 vendor？三型風險不同
- **dogfood signal**：你能不能用 frame 借鑑 Microsoft 365、但避免拿 dogfood 數字當 benchmark
- **multi-model 是否真用上**：你的系統未來會不會用 graph / cassandra / table API？只用一個 API 時 multi-model unique value 不成立
- **跨雲 hedging vs Azure 整合**：你的雲商策略是已定還是未定？已綁 Azure 生態時 lock-in 是整合延伸、未定時 lock-in 是 hedging 損失

四層回答完、selection 才能落地、不是「Azure 上要不要用 Cosmos DB」單一問題。

### Anti-recommendation

- 純 MongoDB 投資、未來不會綁 Azure、應留在 Atlas
- MongoDB API 是「Azure 上的 MongoDB 替代品」、不是 MongoDB 升級版
- 跨雲 hedging 是 selection 主 driver 時、Cosmos DB（單雲）+ DynamoDB（單雲）+ Spanner（單雲）都不應該進候選名單
- 只用 document model、不用其他 4 個 API 時、multi-model 不該變成 selection 理由

## 寫作前置 checklist

- [ ] case anchor 確認：9.C30 Microsoft 365 dogfood 為主案例、9.C36 Coinbase + 9.C37 Forbes 做三型遷移路徑對照（cross-link、不展開）
- [ ] knowledge card 雙引用：database、change-data-capture
- [ ] sibling 對比：MongoDB Atlas、DocumentDB（AWS）
- [ ] fact vs derive 分層：
  - 9.C30「MongoDB → Cosmos DB MongoDB API、planet-scale 分析、dogfood」是 case fact
  - 9.C30 警示「沒有提具體 throughput、latency、cost 數字」+「『MongoDB 不夠用』是行銷話術」必須在引用段明示、不能編造數字
  - 「三型遷移路徑」是本章合成 frame（F2.1）、case 原文無此分類、寫稿時要標「本章合成」
  - 「multi-model 是 Cosmos DB 差異化價值」是 9.C30 case 策略段直接揭露的 fact
  - 「跨雲 hedging vs 單雲 lock-in」是 9.C37 Forbes case 揭露的 frame（跨雲彈性的價值在規避未來鎖定）、本篇引用做 frame anchor
  - 「100% wire compat 是行銷話術、實際在某些 query pattern 下相容」是 F2.9 合成、9.C30 case 直接揭露相關行銷話術 caveat、寫稿要明示分層
- [ ] Scope warning 明示清單：
  - Microsoft 365 dogfood 數字不公開、不能當 benchmark
  - 「100% wire compat」是行銷話術、必須 dual-write 驗證每個 query pattern
- [ ] 預估寫作長度：400-460 行（為何選 Cosmos DB MongoDB API 四層 framing + 兩 API 對比 + migration playbook 6 規格面 + selection value 收束、密度高）
