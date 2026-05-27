# Round 5-B：Reader Simulation 旅程審查

> Frame: Round 2-B reader simulation 旅程審查（multi-round-review skill §Round 2）。Audit scope: DB3 / DB4 entry articles + per-vendor 32 deep articles. 走 4 種讀者類型、看入口判讀 / 內容門檻 / 跳出訊號 / 路由滿足 / 意外發現。報告以實際讀路徑為主、不重複前 4 輪寫作規範 / case 準確性 / 跨章一致性 / cadence 維度。

## 整體 reader journey 健康度

| 讀者類型                        | 一句結論                                                                                                                                                     |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| R1 PG connection limit → KV     | entry 路徑健康、但 KV 入口未明示「先讀 entry 再進 single-table」、容易先進 single-table 撞 4 軸前置判讀後再回頭                                              |
| R2 全球 OLTP 三家比較           | DB4 entry 健康、Path A/B/C driver path 是亮點、但七問題決策樹後段（Q6 team size / Q7 sizing）跟前段（Path 判讀）的耦合度未明示、容易跳過 Path 0 直接看七問題 |
| R3 DBA 找 Aurora fleet 治理     | read-replica-scaling 是 fleet 治理 SSoT、但 title 沒寫「fleet 治理」、DBA 從 vendors/_index.md 點進去看不出這篇承擔 fleet 議題                               |
| R4 partition key 跨 vendor 比較 | 3 篇都有可逆性對照表、但「可逆性 frame」在 3 篇都是 *章內合成段落*、entry 沒承擔跨 vendor frame 索引、讀者必須 3 篇都讀完才發現 frame 對齊                   |

**跳出訊號 top 3**：

1. **Entry article 開頭密度過高**：DB3 entry / DB4 entry 開頭段都試圖一次承擔（problem statement + driver path + 不展開 mechanism）— DB4 entry 連續 4 段 case anchor + driver path 標題、讀者在「我屬於哪條 path」識別完成前已看完 250 行。對「我只想知道該選哪個」的讀者來說、Path 0 前置門檻偏高。
2. **Per-vendor article 開頭的「適用度前置判讀」block-quote 模式同質化**：4 篇 DynamoDB / 4 篇 Cosmos DB / 2 篇 MongoDB 都用「本篇假設 workload 已通過適用度 N 軸 — 詳見 X — 本篇不重複」block quote。讀者連續讀 3 篇後對這段 banner 麻痺、第一次進來的讀者可能跳過、結果撞到「為什麼這個前提沒講」。
3. **跨 vendor 共寫 frame 的 cross-link 不對稱**：Frame 8 event-driven scaling 5 模式 SSoT 在 dynamodb/on-demand-vs-provisioned、Aurora read-replica-scaling 對齊提到、但 Spanner / CockroachDB 的 burst 議題章節（survival-goals / hlc-raft-consensus）沒有對應 cross-link 回 Frame 8 SSoT、讀者從 distributed SQL 想理解 burst 模式時找不到 anchor。

**路由滿足度評分**：B+（4 條讀者路徑都能完成 round-trip、但 R3 跟 R4 需要讀者「猜對」入口點才能順暢、不是被引導）

## 讀者 1（PG connection limit → KV）simulation

**模擬路徑**：搜尋「PostgreSQL connection limit」進來、Google 點進 db3-vendor-selection.md（Hugo SEO 應該排前）

- **入口判讀**：✓。db3-vendor-selection 第二段「典型啟動壓力分兩類 / 第二類、既有 PostgreSQL / MySQL workload 撞 connection limit（surge 下 1K-5K pool 是隱性天花板、F1.7）」直接打中讀者徵兆、30 秒內確認「對我有用」
- **內容門檻**：⚠。讀者繼續往下會進到「Workload shape 三軸前置判讀」、軸 1-3 設計良好。但 *軸 2 KV 適用度* 寫到「天然均勻 PK / 不均勻 PK / Access pattern 變動頻繁」三型、對「我只是要解 connection limit」的讀者來說、抽象階梯一次拉到位、找不到「connection limit 對應到 KV 的哪一型解法」的直接 anchor
- **跳出訊號**：「Workload shape 三軸前置判讀」段密度高、連續 3 個軸 + 表格 + 段落補充、讀者可能在軸 2 跳出去找「DynamoDB 怎麼解 connection」— 但本文不直接答這問題（答案在 single-table-design-pattern 的「durable queue / write buffer」段、Tixcraft case）
- **路由滿足**：⚠。下一步路由段「DynamoDB 子組」第一條指向 single-table-design-pattern、但描述寫「access pattern 設計 + 適用度前置判讀」、沒明示「connection limit 替代路徑 / durable queue 用例」— 對 R1 讀者的具體痛點 routing 不夠精準
- **意外發現**：R1 進 single-table-design-pattern 後、必須先讀 4 軸前置判讀（180 行才到 durable queue 用例）— 直接答案隱藏在 article 中段、entry article 應該明示「connection limit 訊號 → 看 single-table 的 durable queue 段」這條快速路徑

## 讀者 2（架構師評估全球 OLTP 三家比較）simulation

**模擬路徑**：搜尋「CockroachDB vs Spanner vs Aurora DSQL」→ DB4 decision tree

- **入口判讀**：✓。title 直接命中「CockroachDB vs Aurora DSQL vs Spanner」、第一段「團隊評估『全球分散式 OLTP 三選一』時最常見的源頭錯誤：先比 vendor、再回頭問『我為什麼要 distributed SQL』」抓對讀者真實壓力
- **內容門檻**：✓。「7 題本文都會回答、但先回答『你是哪條 driver path』這個前置問題 0」設計優秀、給讀者明確的閱讀順序預期
- **跳出訊號**：「撞牆訊號分型」三條 Path A/B/C 各自獨立段落清晰、但 Path A 的「DoorDash 1.636 M QPS」加 scope warning（不是 CockroachDB throughput claim）的密度偏高、初次讀者可能花 30+ 秒才消化。三軸 vendor 對比段「Managed 成熟度」直接用 case + scope warning 結構、對快速比較讀者有點重
- **路由滿足**：✓。七問題決策樹 Q1-Q7 順序清晰、每題有明確下一步。Q6 team size + Q7 sizing barrier 是亮點（多數 vendor 比較文不會講 team size）
- **意外發現**：「Cluster boundary 顆粒」段（per-app cluster vs 邏輯一個 cluster）放在七問題後、對「還沒選 vendor」的讀者來說是 post-decision 議題、但 length 不短（~70 行）— 讀者可能誤以為這也是 vendor 選擇軸而困惑。建議在該段開頭明示「本段是 *已選 CockroachDB* 後的 cluster 拓樸決策、不影響 vendor 選擇」

## 讀者 3（DBA 找 Aurora fleet 治理）simulation

**模擬路徑**：從 vendors/_index.md → Aurora 子組覆蓋表 → 看不出哪篇講 fleet 治理 → 試 read-replica-scaling

- **入口判讀**：⚠。vendors/_index.md 的 Aurora 子組列「read-replica-scaling」、但描述只在表格 cell 內提「read replica」、沒提 fleet 治理。read-replica-scaling.md title「15 replica 上限、lag profile、headroom 預留與 fleet 治理」第四個關鍵詞才出現 fleet — DBA 從覆蓋表看 title 機率漏掉
- **內容門檻**：✓（一旦進來）。article 第一段明示「本文同時展開兩個議題：(1) 單 cluster 內 read replica 怎麼用 / (2) Aurora fleet 治理的 3 條 driver」、第一句就標 fleet 治理 SSoT。進來後讀者很快認得這篇承擔 fleet 議題
- **跳出訊號**：fleet 治理 SSoT 段位於 article 的「邊界與整合」段（約 250 行後）— 對只想看 fleet 治理的讀者來說、要先讀完 read replica 機制段才到 fleet 段。article 結構是 read-replica 主軸 + fleet 邊界擴展、不是 fleet 主軸 — 跟 SSoT 角色定位有 mismatch
- **路由滿足**：✓。fleet 治理段內三條 driver（business sharding / microservice / 合規）跟 case anchor 對應清晰、案例 cross-link 完整
- **意外發現**：fleet 治理段的「何時拆 vs 加 replica 的判讀順序」6 條清單對 DBA 是黃金路徑、但被埋在 article 中段、entry article（vendors/_index.md）若能在 Aurora 覆蓋表的 read-replica-scaling cell 加註「(fleet 治理 SSoT)」、入口判讀會大幅改善

## 讀者 4（partition key 跨 vendor 比較）simulation

**模擬路徑**：DB3 entry 看到三 vendor 對比 10 軸「Partition / shard key 可逆性」軸 → 點進 MongoDB shard-key-selection → 想找 DynamoDB / Cosmos DB 對照

- **入口判讀**：✓。DB3 entry 表格直接列「Partition / shard key 可逆性」軸、`reshardCollection 4.4+ 可改、成本高` / `可改用 backfill` / `不可改、必 export-recreate`、讀者一眼確認「跨 vendor 確實差很多」
- **內容門檻**：⚠。MongoDB shard-key-selection 文章內「Partition key 可逆性跨 vendor 對照」段是亮點（3 vendor 對照表）。但 DynamoDB partition-key-antipatterns 跟 Cosmos DB partition-key-design 也都各有獨立的「可逆性對照表」— 同 frame 在 3 篇 article 重複 3 次、且 entry article 也重複一次（4 處）— 對讀者反而造成 confusion：「到底哪篇是 SSoT」
- **跳出訊號**：3 篇 partition-key article 都在「核心機制 / 操作流程」段後才提可逆性對照、讀者比較跨 vendor 時要在 3 篇來回跳。Cosmos DB 的「不可改是設計選型的硬約束」frame 是 partition-key-design.md 內、不在 MongoDB / DynamoDB sibling — 讀者從 MongoDB 進來看不到這個 frame 警示
- **路由滿足**：⚠。MongoDB shard-key-selection 末段沒有 cross-link 到 DynamoDB / Cosmos DB partition-key article、需讀者自己回 entry article 或 vendors/_index.md 找。3 篇 article 是「自包含 + 內含對照表」而非「sibling cross-link」結構
- **意外發現**：3 篇 article 都有「跟 X / Y vendor 對照表」、但表格內容微妙不同（MongoDB 強調 ops 工時、DynamoDB 強調 backfill、Cosmos DB 強調 hard 約束）— 對「找跨 vendor frame」的讀者有 cognitive load，要自己整合 3 個視角。entry article 的「可逆性軸」可以承擔 cross-vendor partition key frame 的 SSoT、3 篇 deep article 改 cross-link 不展開

## 跨讀者 batch-wide pattern

**多種讀者都遇到的問題**（systematic issue）：

1. **Entry article 是路徑 anchor、但沒有承擔「跨 vendor frame 索引」角色**：partition key 可逆性、capacity 抽象、合規邊界處理、event-driven scaling 5 模式等跨 vendor frame 在 8 條共寫 frame（_module-outline.md Section B）裡明示、但在 entry article 內只表格化展開 1-2 句、deep article 內又重複展開 — frame 散落在多處、沒一個地方 anchor 全部跨 vendor frame
2. **「適用度前置判讀」block quote 在 12+ 篇 article 重複出現**：DynamoDB 4 篇 + Cosmos DB 4 篇 + Aurora 2 篇 + MongoDB 2 篇都用同 banner 模式。模板價值是「強制讀者先讀 entry」、但對連讀者麻痺感是真實的、初讀者跳過 banner 的機率也高
3. **Per-vendor article 的 SSoT 角色在 vendors/_index.md 覆蓋表看不出**：read-replica-scaling 是 Aurora fleet 治理 SSoT、aurora-dsql-spanner-decision-tree 是 DB4 entry SSoT、cosmosdb/multi-region-write-conflict 是 multi-region write conflict SSoT — 但覆蓋表用「服務頁 + deep article」二分結構、沒標 SSoT 角色。讀者進來找不到 SSoT 入口

**Entry article 承擔度評分**：

- **DB3 entry (db3-vendor-selection.md)**：B+。問題情境 / 三軸前置判讀 / Migration path 三型 / 三 vendor 對比 10 軸結構完整、case anchor 充分。但「跨 vendor frame 索引」角色沒承擔（federated DB 視角、control plane vs data plane 都在 entry 內展開、但 deep article 內沒 cross-link 回 entry 的對應段落）
- **DB4 entry (aurora-dsql-spanner-decision-tree.md)**：A-。Path A/B/C driver path 是亮點、7 問題決策樹邊界清晰、PG 相容性 audit checklist 4 項 + team size + sizing barrier 三項深度議題承擔得當。Cluster boundary 顆粒段位置可商榷（已選 vendor 後議題不該擺七問題後）

## 必修（影響讀者體驗）

### High（critical 路徑斷裂）

1. **vendors/_index.md 覆蓋表加 SSoT 標註**：read-replica-scaling 加「(Aurora fleet 治理 SSoT)」、aurora-dsql-spanner-decision-tree 加「(DB4 entry SSoT)」、multi-region-write-conflict 加「(multi-region write 主寫)」 — 讓 DBA / 架構師類讀者能精準入口
2. **DB3 entry 在「下一步路由」段補連線替代路徑入口**：對 R1（PG connection limit → KV）讀者、明示「若主要問題是 connection limit、進 single-table-design-pattern 的 durable queue / write buffer 段（Tixcraft 9.C15 路徑）」— 給快速路徑

### Medium（開頭門檻過高、jargon 過多）

3. **3 篇 partition-key article 的「可逆性對照表」整合**：3 篇都列同 frame、entry article 應該承擔 cross-vendor partition key 可逆性 SSoT、deep article 改 cross-link「詳見 db3-vendor-selection 可逆性軸 SSoT」+ 各自只展開「本 vendor 的不可逆性具體含義」
4. **DB4 entry 的 cluster boundary 顆粒段加位置標籤**：段首補「本段是 *已選 CockroachDB 後* 的拓樸決策、不影響 vendor 選擇」— 跟 vendor 選擇路徑分流、避免讀者誤以為又是新一條 vendor 選擇軸

## 建議（可優化）

5. **「適用度前置判讀」block quote 加變異性**：12 篇 article 同模板讓讀者麻痺、可以針對不同 article 給不同 framing — 「本篇假設」 vs 「進本篇前先確認」 vs 「跳過前置判讀的後果」三種模式輪用、不全部同樣語法
6. **Frame 8 SSoT 在 Spanner / CockroachDB article 補對等 cross-link**：survival-goals / hlc-raft-consensus 在 burst / surge 議題段加「對應 event-driven scaling 5 模式分類見 dynamodb/on-demand-vs-provisioned SSoT」、讓 distributed SQL 讀者也能找到 burst frame anchor
7. **read-replica-scaling 重排序考慮**：fleet 治理段從「邊界與整合」搬到「核心機制」之後 / 「故障模式」之前、強化 fleet 治理 SSoT 主軸 — DBA 讀者進來看到 fleet 段在 article 前半就到、不需讀完 read replica 機制段才到

## 跨輪 finding 不重疊驗證

- 跟前 4 輪維度（寫作規範 / case 準確性 / 跨章一致性 / cadence / outbound impact）不重疊：本輪 finding 都是 *讀者路徑 / 入口判讀 / 路由滿足* 維度、不評具體寫作品質或 case 引用準確性
- 本輪 finding 數 7 條（high 2 + medium 2 + suggestion 3）、frame 涵蓋 4 種讀者類型、跨讀者 systematic issue 3 條
- 停止訊號評估：multi-round-review skill 七軸框架下、本輪覆蓋 *frame 切換* 的「讀者體驗 frame」軸、Round 5-A 預期承擔其他互補軸
