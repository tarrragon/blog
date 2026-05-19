---
title: "Sibling Coverage Asymmetry Blindspot：Priority 評估漏掉的「對稱性維度」"
date: 2026-05-19
description: "當批量 A 跟批量 B 是 sibling（同類 vendor / 同類角色）、A 後寫超過 B、心智模型容易 collapse 到「A 是 reference / B 是 baseline」、忽略 *B 才應該 ≥ A coverage* 的對稱性 priority。Case：MySQL 18 篇 / PG 11 篇後、推薦下一步把 PG 排除、列 DynamoDB / Aurora / SQLite 等「新領域擴張」、user 自己 catch 才發現 PG 還沒對齊。機制：sequential point-in-time coverage 評估 vs cross-sectional sibling symmetry 評估、後者預設不在 priority 列表維度。修法：priority candidate list 必須跑 sibling symmetry audit。"
weight: 135
tags: ["report", "事後檢討", "工程方法論", "priority", "audit-dimension", "寫作"]
---

## 核心：Priority 評估的 sibling 對稱性盲點

當批量 A 跟批量 B 是 *sibling*（同類 vendor / 同類角色 / 應有對等 coverage）、但 A 後寫卻超過 B、心智模型容易 collapse 到「A 是 reference template / B 是 baseline」的角色分配、忽略 *B 才該 ≥ A coverage 的對稱性 priority*。Priority 列表往往跳過 B、列其他「新領域擴張」選項。

問題不在 *推某個 vendor*、在 *priority 評估維度漏掉 sibling symmetry*。

## Case：MySQL 18 篇 vs PG 11 篇後的 priority 列表

時間線：

1. PG 11 篇先寫完（autovacuum-tuning / declarative-partitioning / patroni-ha / pgbouncer-config / pitr-wal-archiving / logical-replication-debezium + 5 migration playbook）
2. MySQL 從 0 開始、user 要求「第一個示範服務、儘量都寫」、寫到 17 篇 deep article + migration playbook + 既有 migrate-to-postgresql = 18 篇 / 5715 行
3. 推薦下一步 priority 時、列「DynamoDB / Aurora / SQLite / MongoDB / CockroachDB / Spanner / Cosmos DB」、PG **不在列表**
4. User 問：「為什麼這裡列的選項沒有 PG？我們做完了嗎？」

實際盤點：

- PG 11 篇 vs MySQL 18 篇、PG 缺 **7 個 MySQL sibling deep article**（replication-topology / online-schema-change-tools / query-optimization / lock-contention / vitess-sharding 對應 Citus / group-replication 對應 BDR / modern-sql-features 反向視角）
- PG 還缺 **4 個 PG-only 議題**（JSONB deep dive / Extension ecosystem / Full-text search / Replication slot management）

User 直覺 catch 到 *coverage asymmetry*、但我 priority 列表沒提供這個視角。

## 機制：為什麼會忽略

至少 5 個 priority bias 共同貢獻：

### 1. 「先存在就 mature」隱性假設

PG 11 篇先存在 → 直覺映射「PG 已 mature」。沒做 *cross-sectional 對比*：

- PG 11 篇 vs MySQL 18 篇、絕對量比較
- 議題覆蓋對應：MySQL 有哪些 deep article、PG 對應的是否都有

「11 篇」這個絕對數字 *看起來合理*、但跟 MySQL 18 篇對比後 *結構性不足*。心智模型把「合理」當成「mature」、跳過了相對性 audit。

### 2. 「新領域擴張」優於「既有領域對齊」的 progress bias

Priority 列表時、DynamoDB / Aurora / SQLite 等 vendor *看起來進度感強* — 從 0 推到 N、新領域擴張。PG 補齊看起來 *重複勞動* — 從 11 推到 18、改善舊領域。

實際上：

- 新領域擴張 *增加 surface area*、但不改善既有結構
- 既有領域對齊 *修補 baseline*、是 reference template 成立的前提

當 baseline 跟 reference template 不對稱時、後者作為 *示範服務* 的價值打折扣 — 「MySQL 怎麼寫 vendor article」沒法 fully 套到 PG、因為 PG 本身不對稱。

### 3. Priority 評估維度漏 sibling symmetry

我用的 priority 評估維度：

- T1 vs T2 vendor 分類
- 領域重要度
- 已有量
- 新領域 vs 既有領域

**漏掉的維度**：

- Sibling vendor 對稱性（A 跟 B 同類、A 寫完後 B coverage 是否對齊）
- Reference template 跟 baseline 的關係（後寫的 reference template 應 ≤ baseline）

「Sibling 對稱性」這個維度不在預設 priority 評估清單、就被自動忽略。

### 4. Reference template vs Baseline 角色混淆

寫 vendor article 時、*哪個是 baseline、哪個是 reference template* 的心智模型可能反轉：

- 直覺：「先寫的 = baseline、後寫的 = reference / extension」
- 真實：「baseline 應 ≥ reference template coverage、不該倒過來」

MySQL 18 篇是 *user-driven 要求* — user 明說「第一個示範服務、儘量都寫」。所以 MySQL 寫得多不是錯。但 *PG 沒對齊到同水準* 才是漏掉的紀律。

當 MySQL 寫到 reference template 規模、PG 還在 11 篇、心智模型容易 collapse 到「MySQL 是新 baseline、PG 是 legacy partial」、其實是 *baseline 應該升級到 reference template 水準*。

### 5. Sequential vs cross-sectional coverage 評估

寫作過程是 sequential —寫 MySQL 17 篇是一段時間、寫完看 git diff stat 確認進度、然後 priority 下一步。**Coverage 評估是 point-in-time 的**：

- Point-in-time（sequential）：「我這 batch 寫了多少」
- Cross-sectional（symmetric）：「我寫的這個跟 sibling 是否對齊」

寫 MySQL 第 17 篇時 self-cross-check：「PG 對應有沒有？」是 cross-sectional 行為、不是預設行為。

Priority 列表階段沒回頭跑 cross-sectional audit、就把 PG 排除。

## 修法

### 1. Priority candidate list 必須跑 sibling symmetry audit

提 priority 列表時、強制 cross-check：

- 列出該批量影響的 *sibling vendor / sibling role*
- 對比每個 sibling 的 coverage（篇數 + 議題覆蓋 mapping）
- 若有 asymmetry、把「補齊 sibling」加進 priority 列表 *跟新領域並列*

### 2. Vendors/_index「內容覆蓋進度」表加對稱性視角

當前內容覆蓋進度只列「已寫 / 未寫」、不列 *sibling 之間相對進度*。改善：

- 加 *「跟 sibling 對應」欄*：每個 article 標 sibling vendor 是否有對應
- 加 *總計篇數 + sibling 對比* 欄：直觀看到 asymmetry

### 3. 「先 mature baseline、再擴張」紀律

寫 vendor batch 時、紀律：

- 確認 *baseline vendor 對齊到 reference template 水準*、再推下一個 vendor
- 例外：user 明確要求先擴張某 vendor 時、加註 *baseline 待對齊* 為 known limitation

### 4. Audit dimension list 加 *Coverage symmetry*

跟 [Data Topology as Audit Dimension](../data-topology-as-audit-dimension/) 同型 —audit 維度可擴張。把 *sibling coverage symmetry* 加進 priority audit 維度：

- 既有維度：T1 / 領域 / 已有量 / 新 vs 既有
- 新增維度：**sibling 對稱性**（A 跟 B 同類時、coverage 對齊度）

## 跟既有原則的關係

- [Data Topology as Audit Dimension](../data-topology-as-audit-dimension/)：本卡是 *priority 評估維度漏一個*、同型但不同 axis
- [Collapse is Implicit Default](../collapse-is-implicit-default/)：priority 評估 collapse 到「新領域擴張」維度、是其變體
- [Multi-Pass Review Frame Granularity Blindspot](../multi-pass-review-frame-granularity-blindspot/)：multi-pass review 漏 catch 的同型、但本卡是 *priority assessment 漏 catch*、不是 *review 漏 catch*

## 反向驗證

不該誤用本卡：

- *Sibling vendor 對稱性* 不等於 *每個 vendor 都該寫到同篇數*。MySQL 18 篇對 PG 合理（兩大 SQL OLTP baseline），但 SQLite / DynamoDB / Spanner 各 18 篇不合理（領域窄 / niche audience）
- 對稱性 audit 是 *對 baseline / reference template 雙方適用*、不是擴張到所有 sibling
- 真正 niche vendor（如 Spanner / Cosmos DB 對小團隊）可以 *明確 backlog 標記 minimum coverage*、不必對齊 baseline

## 觸發再評估

未來累積到以下情境、本卡應重新 review：

- 寫第二個 baseline pair（02 cache Redis vs Memcached / 03 queue Kafka vs NATS 等）時、是否同樣踩 asymmetry blindspot
- 多 reviewer audit 是否能 catch coverage asymmetry（4-reviewer 沒設計這軸、之後 batch 可加 reviewer E *coverage symmetry*）
- Sibling 對稱性 audit 進工具化（vendors/_index 自動產 asymmetry warning）後是否解決
