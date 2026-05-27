# R3-R4：跨章一致性 Round 4 Final Final Verification

## 評分變化軌跡

- Round 1: 8.0/10
- Round 2: 8.7/10
- Round 3: 9.1/10
- **Round 4: 9.5/10** — 達 9.4-9.5 預估上緣

三維健康度（跨輪）：

| 維度                       | R1   | R2     | R3     | R4         |
| -------------------------- | ---- | ------ | ------ | ---------- |
| SSoT 對應紀律              | 8/10 | 9/10   | 9.5/10 | **9.7/10** |
| Cross-link 雙向 + 路徑正確 | 6/10 | 8.5/10 | 9.5/10 | **9.7/10** |
| Frame 1-8 覆蓋             | 8/10 | 8/10   | 9/10   | **9.5/10** |

Polish 3 commit `ea7ae93`（+15/-7 行、8 檔）把 R3 4 個 Low backlog 全清、Frame 1 跨 vendor 12 篇全打通、Frame 8 5 模式跨 vendor SSoT 對齊精準、零新 issue 引入。

## Polish 3 verification

### Task A: Aurora Frame 8 SSoT 對齊 — 5 模式跨 vendor 列項一致

**5 模式列項一致**：✓

DynamoDB on-demand-vs-provisioned SSoT 主寫（L259-263）：

- flash-sale spike（拓元 6750x）
- predictable peak（Disney+ 新片首發）
- sustained growth（Amazon Ads / Capcom）
- surge baseline permanent shift（Zoom 30x DAU）
- B2B sustained + 高可用（Genesys 99.999%）

Aurora read-replica-scaling cross-link 段（L229）列項：`flash-sale spike / predictable peak / sustained growth / surge baseline permanent shift / B2B sustained + 高可用` — *逐項對齊*、移除原自創 *season cycle* 標籤。

**FanDuel 季賽 cycle 對應論述清楚**：✓

新句改寫成 `FanDuel 季賽 cycle 在 5 模式分類中對應 *predictable peak* 的時間序列展開 — 事件 tier 已知（賽季 → 季後賽 → 季冠軍賽 → Super Bowl）、按 tier 預配 read replica 數量、本質是「峰值已知 + 重複出現」的 predictable peak 在多 tier 結構下的延伸`。論述清楚說明 *為什麼 FanDuel 4 tier 是 predictable peak 的延伸而非新模式*、避免讀者誤以為 Aurora 端有自己一套 6 模式分類。

**雙向 cross-link 仍成立**：✓

- Aurora → DynamoDB：L229 直接列 5 模式 + KV 層 vs SQL 層 mode 決策差異段（L231-236）明示職責分工
- DynamoDB → Aurora：on-demand-vs-provisioned L277 既有強化句不受影響、Aurora 在 5 模式 SSoT 不重複展開、Aurora 主寫議題（headroom 預留 + 雙 SLO + fleet 治理）由 Aurora 端展開

**SSoT 主寫紀律維持**：DynamoDB 端主寫 5 模式分類、Aurora 端從 read 峰視角接入 + 對應 *predictable peak* 一行對應、不展開其他 4 模式。職責分工極清楚。

### Task C: 4 dead link 全清

**grep 結果 0**：✓

```bash
grep -rn "Section B Frame\|模組 outline\|module outline\|module-outline" \
    content/backend/01-database/vendors/
# 0 output
```

R3 抓的 3 處 + Polish 3 額外發現的 1 處全部清完：

- `dynamodb/global-tables-conflict.md` L212：「跨 vendor 對照（模組 outline Section B Frame 5）」→「跨 vendor 對照」✓
- `dynamodb/single-table-design-pattern.md` L187：移除「[模組 outline Section B Frame 3](../../../_index.md)」括號 ✓
- `mongodb/replica-set-read-preference.md` L212：「跨 vendor 對照（模組 outline Section B Frame 5）」→「跨 vendor 對照」✓
- `cosmosdb/multi-region-write-conflict.md` L46（Polish 3 額外發現）：移除「依 module outline Section G」尾巴 ✓

**4 處純文字過渡自然**：✓

逐處 verify L185-200（single-table）/ L207-223（global-tables）/ L210-220（replica-set）/ L43-46（multi-region-write）— 移除括號後句子主體（「跨 vendor 共通 frame：production scale 走 *fleet of clusters*」/「跨 vendor 對照」/「本篇是 SSoT 主寫位置」）獨立成立、無斷句、無懸空指涉。Polish 3 用「移除連結保留純文字」的處理方式比改寫文字更乾淨。

### Task D: Cosmos DB 4 篇 Frame 1 cross-link

**句型統一、跟 MongoDB / DynamoDB 一致**：✓

4 篇 Cosmos DB cross-link 同 blockquote 句型：

```text
> **Cosmos DB 適用度前置判讀**：本篇假設 workload 已通過 Cosmos DB 適用度四層 framing
> （API model 三型遷移路徑 / RU 思維轉換成本 / multi-model 差異化是否真用上 / 跨雲 hedging vs 單雲 lock-in）
> — 詳見 [mongodb-api-vs-sql-api 開頭四層 framing](...)、本篇不重複展開。
> <議題> 是 *已選 Cosmos DB 後* 的 <X> 決策；若 workload 不適用 Cosmos DB、<議題> 無法救回 vendor 選錯的 <Y>。
```

每篇尾段差異化（議題 + 救回 Y）但骨架統一：

- consistency-levels-engineering: read / write 語義決策 / 取捨
- partition-key-design: 硬約束議題 / 不可逆性風險
- ru-cost-model-sizing: 成本決策 / 成本結構落差
- multi-region-write-conflict: 拓樸決策 / 推 Spanner 或 Strong + 單 write region

跟 MongoDB 4 篇（`進到 X 前先確認 workload 在 MongoDB 適用區（3 軸：document shape / contract layer / 跨雲 hedging）`）+ DynamoDB 4 篇（`本篇假設 workload 已通過 4 軸（PK 均勻 / control plane / consistency / access pattern）`）骨架完全一致 — 「適用度前置判讀」+ N 軸列舉 + 詳見 SSoT + *已選 X 後* 釐清 + 不適用 fallback。

**Anchor target 命中驗證**：✓

`mongodb-api-vs-sql-api.md` L27 `## 四層 framing：vendor selection 的真實決策軸` 存在、Hugo slug `#四層-framingvendor-selection-的真實決策軸` 命中（空格 / 冒號被替成 dash 後完整對齊）。

**DB3 vendor selection 三 vendor 子組 Frame 1 平衡**：✓

12 篇全打通：

| Vendor    | SSoT 主寫                   | Sibling cross-link 數 |
| --------- | --------------------------- | --------------------- |
| MongoDB   | schema-design-pattern       | 4                     |
| DynamoDB  | single-table-design-pattern | 4                     |
| Cosmos DB | mongodb-api-vs-sql-api      | 4                     |

DB3 三 vendor 適用度判讀軸覆蓋完全均勻（4 + 4 + 4 = 12 篇統一句型）— Polish 2 + Polish 3 兩階段達成平衡狀態、無單一 vendor 子組落後。

## Frame 1-8 完備性 final audit

### Frame 1（適用度判讀）— Polish 2 + Polish 3 後跨 vendor 全覆蓋

- DB3 三 vendor 子組（MongoDB / DynamoDB / Cosmos DB）：12 篇統一句型 blockquote ✓
- DB4 三 vendor（Aurora / Spanner / CockroachDB）：開頭段含「前置閱讀建議 + vendor 頁 cross-link」+ vendor 頁本身有 *合規 driver* / sizing barrier / cluster boundary 判讀 ✓
- DB3 跟 DB4 風格差異有原因：DB3 vendor selection 走 *workload shape* 軸（schema / KV / API model）、DB4 走 *合規 + sizing + cluster 顆粒度* 軸、適用度問題本質不同、不強求同模板

### Frame 3（fleet 治理）— SSoT + 退化段全打通

- Aurora SSoT 主寫：read-replica-scaling L250-298（3 driver H3） ✓
- MongoDB SSoT：shard-key-selection ✓
- DynamoDB 退化段：single-table-design-pattern L185-200（4 vendor 對照表）✓ — Polish 3 清掉 dead link 後表結構不變
- CockroachDB cluster boundary 主寫：decision-tree L224-289（Fix3 67 行）✓

### Frame 5（合規邊界）— 4 vendor 對照完整

- Aurora fleet 吸收：global-database-multi-region + migrate-from-self-managed-pg-mysql ✓
- CockroachDB locality+placement：locality-aware-schema + decision-tree Path C ✓
- DynamoDB region-pinned Global Tables：global-tables-conflict L207-223 ✓ — Polish 3 降溫 Genesys over-inference、case fidelity 該軸拉滿
- MongoDB cluster-per-region：replica-set-read-preference L207-220 ✓ — Polish 3 清掉 dead link、4 vendor 對照表結構不變

### Frame 8（event-driven scaling 5 模式）— 跨 vendor SSoT 對齊精準

- DynamoDB SSoT 5 模式：on-demand-vs-provisioned L259-263 ✓
- Aurora SSoT 事件分級表：read-replica-scaling L222-227 ✓
- 雙向 cross-link：Aurora → DynamoDB（5 模式列項一致 + FanDuel = predictable peak 多 tier 延伸）+ DynamoDB → Aurora（KV vs SQL 層 mode 決策差異）✓
- Polish 3 解 5 模式 vs 6 模式不對齊問題、SSoT 5 模式紀律精準

## SSoT 7 大議題 audit（Polish 3 後）

| SSoT 議題                         | 主寫位置                                                             | Polish 3 後狀態                                                                               |
| --------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Strong + multi-region 互斥        | cosmosdb/multi-region-write-conflict                                 | ✓ 主寫 H2 不受 Polish 3 影響、新加 Frame 1 cross-link 不展開該議題                            |
| Aurora fleet 治理                 | aurora/read-replica-scaling L250-298                                 | ✓ Fleet SSoT 段（L250-298）未動、只動 L229 Frame 8 段                                         |
| CockroachDB cluster boundary 顆粒 | aurora-dsql-spanner-decision-tree L224-289                           | ✓ Polish 3 未動、SSoT 主寫不變                                                                |
| Document model 三型遷移           | cosmosdb/mongodb-api-vs-sql-api                                      | ✓ 4 篇 Cosmos DB Frame 1 cross-link 全指向 SSoT、SSoT 本身未動                                |
| Frame 1 適用度判讀 MongoDB        | mongodb/schema-design-pattern                                        | ✓ 未動                                                                                        |
| Frame 1 適用度判讀 DynamoDB       | dynamodb/single-table-design-pattern                                 | ✓ Polish 3 只清 L187 dead link、SSoT 主段（L13 `## DynamoDB 適用度前置判讀（4 軸）`）不受影響 |
| Frame 8 event-driven scaling      | dynamodb/on-demand-vs-provisioned + aurora/read-replica-scaling 共寫 | ✓ Polish 3 對齊 5 模式列項、雙向 cross-link 職責分工更清楚                                    |

**7/7 SSoT 議題 Polish 3 後全部維持紙面 + 實質主寫紀律**、零 SSoT 主寫被誤動。

## Reader journey 三層 final test

### Layer 1（entry-driven）：✓ 流暢

- `vendors/_index.md` → DB3 entry article → workload shape 3 軸 → 判定 *document-shape + 跨雲 hedging* → Cosmos DB → 任一 deep article 開頭 Frame 1 cross-link → 跳回 `mongodb-api-vs-sql-api` 四層 framing → 確認適用 / 不適用 — Polish 3 後 *任一 Cosmos DB deep article 都能 route 到 vendor selection framing*、之前只有 2 篇

### Layer 2（機制深化）：✓ 流暢

- 6 vendor `_index.md` 底部 Deep article 表全打通
- Sibling cross-link 紀律維持（4 + 4 + 4 = 12 篇 Frame 1 / 4 + 4 + 4 = 12 處 Frame 3-5-8 cross-vendor）

### Layer 3（跨層架構）：✓ 強化

Manual reader test 走法 1（DB3 entry → Cosmos DB consistency-levels-engineering）：

1. `vendors/_index` → DB3 entry → workload shape: document + multi-model + multi-region → 進 Cosmos DB
2. cosmosdb `_index` → 點 `consistency-levels-engineering`
3. **L13 Frame 1 cross-link → 跳 `mongodb-api-vs-sql-api` 四層 framing**
4. 確認 workload 通過四層 → 回 `consistency-levels-engineering` 讀 consistency level 工程選擇
5. L9 提示 Strong + multi-region 互斥 → 跳 `multi-region-write-conflict`
6. 該篇 L13 也有 Frame 1 cross-link → 已讀過、跳過、直接進 AP 取捨 H2

路徑流暢、Cosmos DB 任一 deep article 都能回 vendor selection framing — Polish 3 補完讓 DB3 整體 reader journey 跟 MongoDB / DynamoDB 完全對等。

Manual reader test 走法 2（DynamoDB 5 模式 → Aurora 對應）：

1. `dynamodb/on-demand-vs-provisioned` L259-263 5 模式分類
2. 段末「跟 Aurora 共寫」cross-link → 跳 `aurora/read-replica-scaling`
3. L229 Aurora 端 Frame 8 段 → 5 模式列項跟 DynamoDB 對齊 → FanDuel 季賽 cycle 對應 *predictable peak* 多 tier 延伸
4. 讀者不會被「season cycle」自創標籤誤導、知道 FanDuel 是 predictable peak 的多 tier 結構延伸而非新模式

Polish 3 解掉 Aurora 端列項不對齊問題、跨 vendor 視角形成更精準。

## 新 issue（Polish 3 引入）

**Polish 3 引入新 issue 數**：0

- Aurora L229 改寫後句子結構不變、`KV 層 vs SQL 層的 mode 決策差異` H3 段（L231）對接自然
- 4 個 dead link 清掉後 4 篇純文字過渡自然（已逐處 verify）
- Cosmos DB 4 篇新加 blockquote 在 Case anchor 段（L11）跟 `## 問題情境` H2（L15）之間、不打斷既有段落 flow、跟 MongoDB / DynamoDB 既有 blockquote 位置一致
- `mdtools lint vendors/` + `mdtools cards vendors/` 0 error / 0 warning / 0 broken link / 0 orphan
- No emoji / decoration char 入侵

## 剩餘 backlog

**0 個阻擋發布議題、0 個 Low backlog**。

可選 nice-to-have（不阻擋發布、不影響評分）：

1. DB4 三 vendor（Aurora / Spanner / CockroachDB）目前用 `前置閱讀建議 + vendor 頁 cross-link` 風格、跟 DB3 三 vendor 12 篇 `> **X 適用度前置判讀**` blockquote 句型不同 — 這是 *合理差異* 而非缺漏（DB4 適用度問題本質是合規 + sizing + cluster 顆粒度、不是 workload shape）。要做進一步統一可考慮在 DB4 三 vendor deep article 加類似 blockquote 句型、但屬 enhancement 而非 fix。

## 最終跨章一致性評分

**9.5/10**（從 R3 9.1/10、+0.4）— 達 9.4-9.5 預估上緣

評分 breakdown：

- ✓ Frame 1 跨 vendor 12 篇 cross-link 全打通（MongoDB 4 + DynamoDB 4 + Cosmos DB 4）、DB3 三 vendor 子組完全平衡（+0.15）
- ✓ Frame 8 5 模式 SSoT 跨 vendor 列項精準對齊（移除自創 *season cycle*、FanDuel = predictable peak 多 tier 延伸論述清楚）（+0.1）
- ✓ 4 dead link 全清、`mdtools cards` 0 broken link（+0.05）
- ✓ Genesys over-inference 降溫、case fidelity 該軸拉滿（+0.05）
- ✓ Reader journey Cosmos DB 任一 deep article → vendor selection framing 路由完備（+0.05）
- ✓ 7/7 SSoT 議題 Polish 3 後紀律全維持、無 SSoT 主寫被誤動
- ✓ 零新 issue 引入、零 Low backlog 剩餘

未達 10/10 的原因：

- -0.3 DB3 vs DB4 vendor selection framing 句型風格差異（不算缺漏、但若要 perfect 整齊可進一步統一）
- -0.2 跨 module 連接（DB1 / DB2 / DB5+ 跟 vendors/ 的 cross-link）未在本次 review 範圍、但模組外的整合留待 Stage 6

## 模組可發布性結論

**達 perfect score、可發布**。Polish 3 commit `ea7ae93` 把 Round 3 4 個 Low backlog 全清、Frame 1 跨 vendor 完整覆蓋、Frame 8 5 模式 SSoT 對齊精準、Reader journey 三層全打通、SSoT 7/7 紀律維持、零新 issue 引入。

case-first methodology batch 1 以來最高跨章一致性 baseline 達成。下一個 batch 可直接以本模組為樣板。

**三維最終評分**（預估）：

- R1 寫作規範：A+ (4.85/5) 維持
- R2 案例引用準確性：96-97%（Polish 3 Task B Genesys over-inference 降溫後）
- R3 跨章一致性：**9.5/10**

三維平均 A+ 上緣、達 perfect score 預估。
