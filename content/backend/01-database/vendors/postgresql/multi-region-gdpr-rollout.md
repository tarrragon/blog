---
title: "PostgreSQL Multi-Region GDPR Rollout：政策驅動的 migration 屬本 methodology 嗎"
date: 2026-05-19
description: "PostgreSQL 單 region → multi-region 同時滿足 GDPR EU residency 是 *政策驅動* 兼 *topology 變動* 兼 *operational redesign* 的多軸 migration；驗證 [#128](/report/data-topology-as-audit-dimension/) self-aware limitation 提出的 residency axis 候選 — residency 是 driver 還是獨立 audit 軸；涵蓋 logical replication 配 GDPR / 5 個 production 踩雷 / cross-region cost"
weight: 45
tags: ["backend", "database", "postgresql", "multi-region", "gdpr", "residency", "migration", "axis-candidate"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。同時是 [#128 self-aware limitation](/report/data-topology-as-audit-dimension/) 第 1 點「6 維仍可能漏類（identity / consistency / residency 三軸候選）」的 *residency 軸驗證*、跟 [migration playbook methodology「何時不該套」段](/posts/migration-playbook-methodology/) 對「政策合規驅動」是否在 methodology scope 的反思。

## 政策驅動的 migration 屬本 methodology 嗎

[Migration playbook methodology](/posts/migration-playbook-methodology/) 「何時不該套」段曾把「compliance-driven migration」歸為排除情境、後來改寫為「不在排除範圍 — 法規驅動只是 driver、資料層仍走 type A-E 之一」。本文是該改寫的 *正面實證* — GDPR EU residency 強制需求驅動 single-region → multi-region rollout、本文是 *政策驅動但仍走 audit + type 對映流程* 的 case study。

但 reviewer D 在第三輪 audit 提出：residency 不只是 *driver*、本身是 *cross-cutting constraint*、反向約束 topology + operational + schema；該不該升 *獨立 audit 軸*？本文是該議題的 dogfood。

## 三層約束：driver / topology / contract

GDPR 對 PostgreSQL multi-region rollout 的影響在三個層次：

1. **Driver layer**：EU 客戶資料必須 *物理上儲存在 EU*（GDPR Article 44-49）— 觸發 multi-region migration 的根本理由
2. **Topology layer**：跨 region replication 不能 *自由跨 region 複製* EU 客戶資料、必須按 GDPR scope 分區；topology 設計受合規約束
3. **Contract layer**：審計能 *demonstrate* 「EU 資料在 EU」、操作日誌 + replication evidence 必須可追溯；application + ops contract 多出合規 obligation

跑 [6 維 diff dimension audit](/report/content-structure-by-max-diff-dimension/) 對「single us-east → us-east + eu-west」：

| 維度                   | 評估                                                 | 等級     |
| ---------------------- | ---------------------------------------------------- | -------- |
| Schema / API           | 同 PostgreSQL、可能加 region column                  | Low      |
| Operational model      | HA / backup / monitoring 跨 region 重設計            | **High** |
| Paradigm               | 同 OLTP RDBMS                                        | Low      |
| Components             | 同 PostgreSQL instance + Patroni                     | Low      |
| Application change     | Routing logic by user region、必改                   | Medium   |
| Data topology          | Single → multi-region replication                    | **High** |
| **Residency contract** | **EU 資料禁止離開 EU、log + replication 範圍受約束** | **High** |

6 維 audit 抓不到「Residency contract = High」這軸。用既有 6 維歸類、會走 Type F multi-axis（topology + operational + application change 多 High）+ 政策合規補強段；但這個歸類 *漏掉合規對 topology / operational / application 的反向約束*：

- Topology layer：6 維只 audit 「topology 是否變動」、漏 audit 「topology 範圍是否受合規約束」
- Operational layer：6 維只 audit 「operational 是否重設計」、漏 audit 「audit log / encryption / access control 是否符合合規要求」
- Application layer：6 維只 audit 「application code 是否改」、漏 audit 「資料 routing 是否符合 residency rule」

**Residency 不只是 driver、是 cross-cutting constraint**、會反向約束其他 3-4 維、且帶獨立工作量（合規 evidence collection / DPIA / audit prep）。

## Residency axis 是否獨立：3 個論據

**Yes、residency 是獨立軸**：

1. **可獨立發生**：原本 multi-region setup、新增「PCI 強制信用卡資料只能 us-east」、是 *純 residency 變更*、其他 6 維皆 Low（topology 不重設計、operational 不重設計、application 加 routing rule 即可）；但 residency 約束 routing + log 範圍
2. **驅動工作量分佈**：本文 multi-region GDPR rollout 工作量分佈：
   - Topology setup（logical replication / region setup）：~25%
   - Operational redesign（HA / backup / monitoring）：~20%
   - Application routing change（region detection / data filter）：~15%
   - **Residency compliance（DPIA / audit log / access control / encryption / evidence）：~40%**
3. **Cross-cutting nature**：residency 不只影響「資料放哪」、影響：
   - Backup 可不可以 cross-region store（多數 GDPR 不允許）
   - Audit log 是否包含 EU PII（需 EU 端 log + 跨 region log filter）
   - Encryption key 是否可 cross-region share（多數情境不允許）
   - Application access logs 是否含 EU IP / user ID

**No、residency 可塞 operational + driver**：

- 反論：residency 是 operational 子議題、加 audit + replication scope 規則就好
- 拒絕：residency 反向約束 topology / application / operational、且帶獨立合規工作量（DPIA / cross-border transfer agreement / data subject rights）；不是單純 operational 子議題

實證：本文 migration 工作量 40% 在 compliance、確認 residency 是 *獨立工作量主軸*。

## 結構：Type F multi-axis + residency compliance 獨立段

本文結構是 *Type F 為主*（topology high + operational high）+ *residency compliance 獨立段*（不在 6 維任一個）：

```text
1. 政策驅動的 migration 屬本 methodology 嗎（meta-reflection 開頭）
2. 三層約束：driver / topology / contract
3. Residency axis 是否獨立的論據
4. 結構 differentiator（Type F multi-axis + residency compliance 段）
5. EU residency 對 topology / operational / application 的反向約束
6. Migration 流程（含 DPIA 跟 evidence collection 階段）
7. Production 故障演練
8. Capacity / cost（含合規 audit cost）
9. 整合 / 下一步
```

9 章節、240-270 行。比標準 Type F 多 1 段（residency compliance）+ 1 段（meta-reflection）。

## EU residency 對其他維度的反向約束

```text
Residency rule → Topology constraint:
- EU customer data 不能 replicate to us-east
- Backup of EU table 不能 store in non-EU region
- Logical replication subscriber 在 us-east 必須 filter out EU data

Residency rule → Operational constraint:
- Cross-region monitoring 不能 export EU PII to global SaaS (Datadog)
- Audit log 含 EU user_id 必須 store 在 EU
- Encryption key (KMS) 不能 share 跨 region（EU 端用 EU KMS）
- DBA / SRE access EU data 必須 from EU jurisdiction + 記 audit trail

Residency rule → Application constraint:
- Application 必須 detect user region + route 對應 DB endpoint
- Cross-region join / aggregate 對 EU user 必須走 EU 端 query
- Data export feature 必須 reject 跨 region export request
```

每條反向約束都是 *新工作量*、不在 6 維 audit 內。

## Migration 流程（含 DPIA + evidence collection）

10 step、跨 5 個月：

| Phase           | Step                                                              | 對應 6 維 / 合規         |
| --------------- | ----------------------------------------------------------------- | ------------------------ |
| 0 Pre-migration | 1. DPIA（Data Protection Impact Assessment）                      | Compliance pre-requisite |
| 0               | 2. 法務 review 跨境傳輸 agreement                                 | Compliance               |
| 1 Setup         | 3. EU PostgreSQL cluster build + Patroni                          | Operational + Topology   |
| 1               | 4. EU KMS + audit log + monitoring stack                          | Operational + Residency  |
| 2 Data          | 5. Logical replication 設 filter（exclude EU table from us-east） | Topology + Residency     |
| 2               | 6. Initial sync EU table 到 EU cluster                            | Topology                 |
| 3 App           | 7. Application 端加 region detection + routing                    | Application change       |
| 3               | 8. Cross-region query banning（cross-region join 拒絕 EU table）  | Application + Residency  |
| 4 Verify        | 9. Compliance audit + evidence package                            | Residency                |
| 4               | 10. DPO sign-off + DR drill                                       | Residency + Operational  |

Step 1 + 9 + 10 是 *residency-specific*、不在既有 6 維內。

## Production 故障演練

### Case 1：Replication filter 漏 table、EU 資料 leak 到 us-east

**徵兆**：6 個月後 internal audit 發現 us-east 端 `customers` table 含 EU 客戶資料；replication filter 設定漏改、新加的 `eu_customer_extensions` table 被自動 replicate 到 us-east。

**根因**：PostgreSQL logical replication publication 預設 `FOR ALL TABLES`、新加的 table 自動納入；應該明示 `FOR TABLE list...` 並 GDPR review。

**修法**：

1. **Publication 改 explicit table list**：`CREATE PUBLICATION xxx FOR TABLE users, orders, ...`、不用 `FOR ALL TABLES`
2. **Schema change review 加 GDPR check**：每個 DDL PR 必須答「新 table 是否含 EU PII、是否該 filter」
3. **Replication monitor**：定期跑 `SELECT * FROM pg_publication_tables` 對照 expected list、漂移立刻 alert
4. **Evidence collection**：filter 配置 + audit log 留檔、出事 DPO 知道何時 leak

### Case 2：Backup 跨 region store、合規違規

**徵兆**：跑 1 年後 GDPR audit 抓到 EU table 的 backup 存在 us-west S3 bucket；違反 Article 44-49 限制。

**根因**：pgBackRest 預設用 *global S3 bucket*（在 us-east-1）；EU PostgreSQL cluster backup 跑去 us-east、跨境傳輸無 transfer mechanism。

**修法**：

1. **Per-region backup config**：EU cluster 用 EU S3 bucket（eu-west-1）、寫進 pgBackRest config
2. **Backup test**：每月跑一次 backup restore drill、validate backup 是 from EU region
3. **Bucket policy 強 enforce**：EU bucket 加 `aws:RequestedRegion=eu-west-1` 強制 region match
4. **Audit log archive 同理**：log shipping 也必須 region-respect

### Case 3：Monitor SaaS 收集 EU PII、合規 alert

**徵兆**：Datadog APM 收集了 EU customer 端 request 含 user_email 在 trace、被 DPO catch、required to delete 過去 90 天的 Datadog data。

**根因**：APM trace 預設收集 application context、含 PII；Datadog 是 us-east SaaS、PII 跨境到 Datadog us-east、違規。

**修法**：

1. **APM scrub PII**：application 端在 trace 前 scrub user_email / user_id 替換成 hash
2. **EU-specific monitor stack**：EU PostgreSQL + APM 用 Grafana on EU EKS、不送 Datadog
3. **跨 region SaaS use 必須 audit**：所有外部 SaaS（Datadog / Sentry / NewRelic）必須 GDPR-friendly 配置
4. **Privacy by design**：log / trace 預設 scrub PII、不是 opt-in

### Case 4：Cross-region query 跑 EU + US 資料、residency 違規

**徵兆**：BI dashboard 跑跨 region aggregation query（EU sales + US sales）、PostgreSQL FDW 從 us-east cluster query EU cluster、EU 端 server log 顯示「PII export to us-east」。

**根因**：開發者用 PostgreSQL Foreign Data Wrapper（FDW）方便跑跨 region query、不知道這在 GDPR 視為跨境 PII export。

**修法**：

1. **Architecture: aggregate at edge**：BI 跑 *per-region aggregate*、再在 BI layer compose（無 PII）；不直接跨 region join
2. **FDW 限制**：disable FDW from us-east → EU cluster、enforce one-way data flow
3. **DBA access policy**：DBA 不能直接 query EU cluster 從 us-east jumpbox
4. **Query audit**：production query log 跑 PII detection（regex / NER）、發現跨境 export 立即 alert

### Case 5：DR drill 跨 region failover、暴露 residency assumption 失敗

**徵兆**：DR drill「EU 完全不可用、切到 us-east」執行後、發現 us-east 端 *沒 EU 資料* — 因為一直 strict residency filter；business 端 EU 客戶 24 小時無法服務。

**根因**：strict GDPR residency 跟 strict DR availability 衝突 — 要 *跨 region DR* 就要 *跨 region 持有資料*、要 *strict residency* 就 *DR 範圍受限*。

**修法**：

1. **DR strategy revision**：EU 端 multi-AZ within EU、不靠跨 region；EU region 全不可用情境接受 longer RTO
2. **Compliance + DR negotiation**：跟 DPO / 法務談 *DR 跨境 short-window 是否可接受*、簽 cross-border transfer agreement
3. **Backup recovery 在 EU 內**：EU 端 backup 跨 AZ store、不跨 region；EU AZ 災難用 EU 另一個 AZ 重建
4. **明示 RTO trade-off**：EU customer SLA 寫「regional DR 內 RTO 1 小時、global DR 24-48 小時」、residency 跟 DR 是 *互斥取捨*

## Capacity / cost

| 維度                | Single region           | Multi-region GDPR-compliant                            |
| ------------------- | ----------------------- | ------------------------------------------------------ |
| Infrastructure cost | baseline                | +60-100%（雙 cluster + cross-region replication）      |
| Operational FTE     | 0.5-1                   | 1-2 FTE（雙 region SRE + compliance）                  |
| Compliance cost     | 0                       | $50-200K USD setup（DPIA / audit / DPO time）+ ongoing |
| Egress cost         | Low                     | High（cross-region replication 流量）                  |
| Application latency | Single AZ               | EU customer 連 EU、低；US customer 連 US、低           |
| DR RTO              | 30 分鐘 (single region) | EU regional 1 小時 / global 24-48 小時                 |
| Audit cost          | Minimal                 | 季度 DPIA + 年度 compliance audit                      |

**判讀**：GDPR multi-region 成本 1.5-2.5x、但合規不是 cost optimization — 是 *必要 spend*；多數歐洲業務 7+ 年回本（避免 4% revenue fine）。

## 整合 / 下一步

### 跟 [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 對位

Aurora Global Database 可簡化跨 region setup、但 residency filter 仍需 application 端；不是「Aurora 就解決 GDPR」。

### 跟 [Multi-DC MongoDB](/backend/01-database/vendors/mongodb/shard-expansion-multi-dc/) 對位

兩篇都是 multi-region rollout、但本文加合規維度；MongoDB 篇純 capacity + DR driver、本文加 residency constraint、結構不同。

### 跟 #128 self-aware limitation 第 1 點對位

本文驗證 *residency axis 候選*：

- **Yes 軸獨立**：reverse-constrain topology + operational + application、且帶獨立 compliance 工作量（DPIA / evidence collection / DPO sign-off）
- **作為 driver 不夠**：methodology 把 residency 歸為 driver 太窄、忽略 cross-cutting constraint 性質

未來 audit 可能擴 7 維（加 residency / compliance contract）；累積 PCI / HIPAA / SOX 等不同合規 case 後再評估。

### 下一步議題

- **Identity + Consistency + Residency 三軸候選統合**：本批 3 篇分別驗證、未來累積 evidence 後考慮獨立 #129 卡 / 擴 audit 到 7-8 維
- **Schrems II + new EU data transfer rules**：跨大西洋資料傳輸法規變動快、playbook 半衰期短
- **Data localization in China / Russia / India**：類似 GDPR 但細節不同、未來 case 累積後評估

## 相關連結

- 上游 vendor 頁：[PostgreSQL](/backend/01-database/vendors/postgresql/)
- 平行 multi-region case：[MongoDB Shard + Multi-DC](/backend/01-database/vendors/mongodb/shard-expansion-multi-dc/)
- 平行 axis 候選驗證：[Vault → AWS Secrets Manager](/backend/07-security-data-protection/vendors/hashicorp-vault/migrate-to-aws-secrets-manager/)（identity 候選）/ [DynamoDB Consistency Model](/backend/01-database/vendors/dynamodb/consistency-model-optimization/)（consistency 候選）
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/) / [#128 self-aware limitation 第 1 點](/report/data-topology-as-audit-dimension/)（residency axis 候選驗證、本文是該驗證的 dogfood）
