# Round 6-A：字句層 Final Verification

Scope：DB3 / DB4 模組 31 篇 deep article + DB3 entry `vendors/db3-vendor-selection.md`。Verify Polish 4 commit `f863de6` + `9652a9c` 對 Round 5-A 抓的 12 必修 + cadence + self-duplication 的修正。Frame：5 grep regression check + per-item before/after diff confirm。

---

## 評分變化軌跡

- Round 1: A- (4.5)
- Round 4: A+ (4.85)
- Round 5-A: identified 12 必修字句層 + 3 篇 DynamoDB cadence + 1 處 self-duplication
- **Round 6-A：A+ (4.95)** — 12 必修全 ✓、cadence 3 篇變體就位、L295 self-dup 改 cross-link、5 grep 殘留均為 R5-A 已標保留組

---

## 5 grep 殘留統計（對比 R5-A baseline）

| Bank      | R5-A baseline           | R6 殘留                                          | Verdict                   |
| --------- | ----------------------- | ------------------------------------------------ | ------------------------- |
| 地區用語  | 2 處（默認 1 / 集群 1） | 0 in target set；mongodb/migrate-to-atlas 2 處   | ✓ 必修 0 殘留、既存項保留 |
| 廢話前綴  | 3 處                    | 0                                                | ✓ 全清                    |
| 口語修辭  | 19 hit（9 必修）        | 14 hit（其實 2 / 實務上 5 / 真的 7、均為保留組） | ✓ 9 必修已修              |
| 裝飾符號  | 0                       | 0                                                | ✓ 維持                    |
| 負向句 #1 | cosmosdb/mongodb-api 37 | 36（−1）                                         | ✓ 必修 1 處連帶 −1        |

**口語修辭殘留逐條核對**：7 處「真的」均為 R5-A `narrative hook / reader symptom` 保留組（aurora/global-database-multi-region L144、cosmosdb/partition-key-design L206、dynamodb/gsi-lsi-design L203、spanner/schema-migration-interleaved-tables L15 讀者徵兆引用、spanner/migrate-from-cloud-sql-pg L60、mongodb/schema-design-pattern L54、cosmosdb/multi-region-write-conflict L17 讀者徵兆）— 全部在 R5-A 列為「case-by-case 保留」、沒有 regression。「實務上」5 處屬 R5-A `evidence 橋接` 保留組。「其實」2 處（cosmosdb/multi-region-write-conflict L206 anti-pattern 描述、cosmosdb/_index L260 路由表達）也都是 narrative hook、非機制 / 決策段落。

**負向句 top 5 R6 結構**：cosmosdb/mongodb-api 36（−1）、aurora/read-replica 33、aurora/migrate 32、cockroachdb/aurora-dsql 28、aurora/storage-architecture 26（取代 db3-entry 進入 top 5、新增是因為 Polish 4-C scope warning 段帶入 1 處「不能 auto-scale」+ 1 處「不直接套通用比例」、屬合理 anti-pattern 語氣、非主導句型）。

---

## Polish 4-A 12 條 verify

| #   | File / line                                                  | Verdict | 備註                                                                                                                          |
| --- | ------------------------------------------------------------ | ------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 1   | cosmosdb/mongodb-api-vs-sql-api L168 默認→預設               | ✓       | L168 確認「預設 ObjectId」                                                                                                    |
| 2   | mongodb/connection-management L142 集群→叢集                 | ✓       | L142 確認「proxy 叢集」                                                                                                       |
| 3   | cosmosdb/multi-region-write-conflict L200 實際上→底層        | ✓       | 改為「底層是設計 incompatibility」                                                                                            |
| 4   | spanner/schema-migration-interleaved-tables L148 基本上→刪除 | ✓       | 「這個流程是 mini-migration」                                                                                                 |
| 5   | cosmosdb/mongodb-api-vs-sql-api L108 實際上→刪除             | ✓       | 「『升級』是 export → recreate ...」                                                                                          |
| 6   | cosmosdb/consistency-levels-engineering L165 其實→改寫       | ✓       | 「互動式產品 Session 即足夠」（用「即足夠」替「就夠」、語氣升級）                                                             |
| 7   | cockroachdb/aurora-dsql-spanner-decision-tree L24 真的→刪除  | ✓       | 「跨雲是硬需求還是被 fear 推的？」                                                                                            |
| 8   | cockroachdb/aurora-dsql-spanner-decision-tree L171 改寫      | ✓       | 「多數公司實際走 single-cloud、跨雲 portability premium 卻沒實際 multi-cloud 部署」、刪「90%」改「多數」、加 scope warning 段 |
| 9   | cosmosdb/mongodb-api-vs-sql-api L86 不是真的跑→改寫          | ✓       | 「實際跑 Cosmos DB 自身 engine、不執行 MongoDB engine」（替方案 — 比 R5-A 建議再精化）                                        |
| 10  | cockroachdb/hlc-raft-consensus L21 真的大會發生→改寫         | ✓       | 「HLC clock skew 超出容忍區間時會發生什麼？」、用 R5-A 建議的可反推屬性                                                       |
| 11  | spanner/_index L122/L142/L227 真的→改寫                      | ✓       | L122-148 已改為「流量明確跨 region」「需要強一致」「需要 linearizable」、L227 改為「需要 global external consistency」        |
| 12  | aurora/storage-architecture L66 真的可用→改寫                | ✓       | 「production-grade 可用」                                                                                                     |

12/12 全 ✓。Item 9 / 11 採用比 R5-A 建議更精確的替換詞、屬於正向升級。

---

## Cadence 3 篇變體 verify（DynamoDB failure mode 開頭句）

| File                        | R5-A 原句                | R6 新句                                       | Verdict |
| --------------------------- | ------------------------ | --------------------------------------------- | ------- |
| global-tables-conflict      | N 個 production 常見踩雷 | **實際部署常見的 5 種失敗**                   | ✓ 變體  |
| partition-key-antipatterns  | N 個 production 常見踩雷 | **production case 揭露的 5 個踩雷情境**       | ✓ 變體  |
| on-demand-vs-provisioned    | N 個 production 常見踩雷 | **production 觀察到的 6 個典型 anti-pattern** | ✓ 變體  |
| gsi-lsi-design              | N 個 production 常見踩雷 | 7 個 production 常見踩雷                      | ✓ 保留  |
| single-table-design-pattern | N 個 production 常見踩雷 | 5 個 production 常見踩雷                      | ✓ 保留  |

3 篇變體 + 2 篇保留模板的設計合理：3 變體確保連讀 5 篇時有 cadence 變化、2 保留維持模組內合理重複（reader 識別 batch 內 DynamoDB 統一架構）。3 變體分別走「實際部署 / production case 揭露 / production 觀察」三個 framing、無刻意感、跟段內 case 列表自然銜接。

---

## Self-duplication L295 verify

L171 保留原始 `fear-driven` listing + 加 scope warning「『多數公司 single-cloud』屬通用工程估算」、L295 改寫成「承接 *問題 1：是否硬需求跨雲* 段的 fear-driven 訊號（多數場景單雲、跨雲是想像中需求）」— 用 cross-link 引用 + 簡述、無重複 listing。句構流暢、不像硬避重複的尷尬重組。✓

---

## 新 issue

- **無系統性新 issue**。
- **aurora/storage-architecture 進入負向句 top 5**：原因是 Polish 4-C 加 2 處 scope warning 段（「不能 auto-scale」「不直接套通用比例」）、屬合理 anti-pattern 語氣、不算 regression。整篇沒「整段被否定句主導」訊號。
- **L171 scope warning 加得 ROI 高**：原本 R5-A 只標兩處重複句、Polish 4-A 順帶在 L171 加 scope warning 把「90%」改「多數公司」+ explicit 標通用工程估算、超出 R5-A 預期、加分。

---

## 預估評分

| 維度                                 | R5-A    | R6-A        |
| ------------------------------------ | ------- | ----------- |
| 地區用語 / 廢話前綴                  | A       | A+          |
| 口語修辭（機制段 / 決策段 hit 全清） | B+      | A+          |
| Cadence（DynamoDB 5 篇同骨化）       | B+      | A           |
| Self-application（L171/L295 重複）   | A−      | A+          |
| 裝飾符號 / 負向句主導                | A+      | A+          |
| **整體**                             | A+ 4.85 | **A+ 4.95** |

Round 6-A 字句層通過。剩餘 14 處口語修辭全屬 R5-A 標為「保留」的 narrative hook / reader symptom quote / evidence 橋接、無進一步 surgical fix 必要。下一輪如要再 polish、優先處理 R5-A `medium` 段 4 處「實務上」精化（aurora/read-replica L48 / L183 + cockroachdb/hlc-raft L147 + cockroachdb/locality-aware L71）+ cosmosdb/multi-region-write-conflict L188「沒事」改寫 — 但 ROI 低、屬尾段 polish、不影響 A+ 評級。
