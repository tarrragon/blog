# Round 6-C：Scope Warning + Enumeration Final Verification

> **Frame**：verify Polish 4-C Block 3 (commit `9652a9c`) 真補完 R5-C 必修 5 處 scope warning + 3 處 enumeration 漏列、case fidelity 維持 96-97%。只 review、不修檔。

## 評分變化軌跡

- R2-R4 baseline 92-94% → R5-A/B/C 96-97% → **Round 6-C：97%（維持、無退化）**

## Polish 4-C Block 3 verify

### 5 scope warning（5 ✓ / 0 ⚠）

1. **cockroachdb/aurora-dsql-spanner-decision-tree「90% 公司 single-cloud」** ✓
   - Before：「90% 公司其實 single-cloud」（兩處皆無口徑）
   - After：第一處改「多數公司實際走 single-cloud」+ 插入 quote block「**數字口徑**：本段『多數公司 single-cloud』屬通用工程估算、case 未揭露明確比例…」；第二處 (anti-pattern 段) 重寫成「承接 *問題 1：是否硬需求跨雲* 段的 fear-driven 訊號（多數場景單雲…）」、跟前段呼應、避免重複數字。✓ fact vs derive 分層清楚。

2. **cockroachdb/aurora-dsql-spanner-decision-tree「2-5x latency」** ✓
   - Before：「distributed SQL overhead（寫入 2-5x latency、ops 複雜度）」
   - After：保留 inline 數字、後插 quote block「**數字口徑**：本段『2-5x latency』屬通用工程估算（Raft / Paxos round trip 跟 single-leader replication 的 latency ratio）、case 未直接揭露對照數字…」✓

3. **cosmosdb/mongodb-api-vs-sql-api「10-20% RU」** ✓
   - Before：「相同 query 的 Request Unit 通常比 SQL API 多 10-20%」
   - After：「…多 10-20%（屬通用工程估算、Microsoft 公開文件未列具體比例、case 也未直接量化、實際 overhead 依 query shape / driver 版本 / region 而異、應該以自家 workload benchmark 校正）」✓ inline scope warning、fact vs derive 明確。

4. **aurora/storage-architecture「3-5ms cross-AZ」** ✓
   - Before：純物理估算、無 scope warning
   - After：「原因：跨 AZ network round-trip 是 3-5ms 物理下界…」段後新增 quote block「**數字口徑**：『跨 AZ round-trip 3-5ms』屬通用工程估算（光速下界 + AWS 區內 AZ 物理距離）、case 未直接量化、實際值依 region / AZ pair / instance 類型而異…**下方 DraftKings 6ms 寫入是 case 揭露的 production reference、可作為對照基線**」✓ 巧妙跟 case fact 對照、分層清楚。

5. **dynamodb/on-demand-vs-provisioned「6-7x rate」** ✓（Polish 4-A 已加、Polish 4-C 字句層 surgical 修）
   - 第 46 行已存在 `> **Scope warning**：「peak/avg > 5x → on-demand」、「provisioned base rate × 6-7 = on-demand rate」這些具體閾值是經驗值 / 通用工程估算、9.C5 / 9.C20 case 都沒給具體 ratio 數字…` ✓ 本輪 commit 微調字句層（「6 個 production 常見踩雷」→「production 觀察到的 6 個典型 anti-pattern」），不影響 scope warning。

### 3 enumeration verify

1. **cockroachdb/transaction-retry-pattern：distributed deadlock × retry 互動** ✓
   - 新增 7th mode（從 6 → 7 enumerated mode）：列三種 corner case + 修法 4 條。明標「修法（屬通用工程議題、case 未直接揭露）」。
   - Case anchor：本篇開頭已 Scope warning 整篇是跨案合成、DoorDash/Netflix/Hard Rock case 都沒揭露 retry pattern；新 mode 沒擴寫 case 沒講的 fact。
   - 跟既有 retry storm / non-idempotent / cross-statement state / hot row / long-running transaction 不衝突、是補 distributed deadlock 跟 PG local deadlock 的差異 mode。✓

2. **cosmosdb/ru-cost-model-sizing：TTL 容量影響 (Failure 8)** ✓
   - 新增 Failure 8 完整段落（徵兆 3 條 + 修 4 條）、明標「屬通用工程議題、case 未直接量化 TTL 對 RU 的佔比」。
   - Case anchor：Microsoft 365 / Minecraft / ASOS 三 case 都未直接揭露 TTL 議題、article 自己標示為通用工程議題、fact vs derive 分層正確、屬通用工程經驗合成、不是 case 揭露升級。✓
   - 跟既有 7 個 failure mode 不衝突、是補 Cosmos DB 特有的 TTL background scan RU 議題。

3. **dynamodb/gsi-lsi-design：GSI capacity mode 跟 base table 不一致 (Case 7)** ✓
   - 標題段「6 個 production 常見踩雷」→「7 個 production 常見踩雷」、enumeration N → N+1 ✓
   - 新增 Case 7 完整段落（徵兆 3 條 + 修法 5 條 + sibling link）、明標「屬通用工程議題、case 未直接揭露具體 mode 錯配狀況」。
   - Case anchor：Amazon Ads / Genesys / Disney+ 三 case 沒揭露 capacity mode 錯配場景、article 自己標通用工程議題、fact vs derive 分層正確。✓
   - sibling link 接 on-demand-vs-provisioned、避免跟既有 mode-switch 議題重複展開。

## 8 陷阱 spot check

### Polish 4 動檔 trap 1/7/8 verify

- **Trap 1 (skeleton case 擴寫成 fact)**：3 處 enumeration 新加 mode 都明標「通用工程議題、case 未直接揭露」、未把 skeleton case 擴成 fact。✓
- **Trap 7 (通用工程估算 vs case 揭露混淆)**：5 處 scope warning 全部明示「屬通用工程估算」+ 列出依賴的工程下界（光速 / Raft round trip / vendor docs / 自家 benchmark）、未把工程估算當 case 揭露賣。✓
- **Trap 8 (跨案合成升級成 case 揭露)**：transaction-retry distributed deadlock 段明標「跨案合成 / 通用工程議題」、ru-cost-model TTL 段、gsi-lsi capacity mode 段同樣分層、未把跨案合成升級成 case 揭露。✓

## Case fidelity 評分

17 case 反向 link 全為 routing 句（「想理解 X → Aurora 儲存層架構」）、未動 case 原文 fact 段。Sample DraftKings / Netflix Aurora / Standard Chartered 三大 anchor case：

- DraftKings：新增「想理解 6 寫 / 4 讀 quorum 跟 200 cluster fleet 治理 → Aurora 儲存層架構」+「想規劃 read replica scaling → read-replica-scaling」 — *routing only*，case 原文 fact (6ms 寫 / <1ms 讀 / 200 cluster / 17K ops sec 加總) 維持 96-97% 精度。✓
- Netflix Aurora：新增 link 句「想理解 +75% 的 storage / compute 解耦根因」 — 引導讀者進 storage-architecture 主寫位、case 原文 +75% 標「workload 改善幅度 10-75% 不等、不是每個都 75%」精度維持。✓
- Standard Chartered：新增 3 個 link 句覆蓋 cross-AZ failover / global database / DSQL 決策樹 — case 原文 4000 TPS / 5x improvement 精度維持。✓

Round 4 Low backlog 2 個 (Aurora Frame 8 / Genesys 合規) 仍維持 Polish 3 修法：

- **Aurora Frame 8** (on-demand-vs-provisioned 第 255 行)：5 mode 仍標「跨 case 揭露」、Genesys 99.999% 仍標「B2B sustained + 高可用 + managed 工時釋放比 cost 重要」、未退回 over-inference。✓
- **Genesys 合規 over-inference**：article 內未出現「Genesys 合規硬需求」之類升級口徑、僅「99.999% B2B sustained + 高可用」、跟 case 揭露對齊。✓

## 新 issue

無 critical / major issue。Minor observation：

- `dynamodb/on-demand-vs-provisioned` 標題從「6 個 production 常見踩雷」改「production 觀察到的 6 個典型 anti-pattern」屬 Polish 4-A 字句層 polish、跟 gsi-lsi-design 從 6 → 7 改法不同（前者修字句、後者修數量）— 不衝突、是各自 article 內部 enumeration 邏輯獨立。

## 預估最終評分

**Round 6-C 最終評分：97%（維持 R5 baseline、無退化、enumeration 補完 + scope warning 5 處全到位）**

- Polish 4-C Block 3：5/5 scope warning ✓、3/3 enumeration ✓
- Case fidelity：96-97% 維持
- 8 陷阱 trap 1/7/8 spot check：0 違規
- 新 issue：0
