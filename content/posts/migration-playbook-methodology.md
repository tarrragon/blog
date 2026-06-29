---
title: "Migration Playbook 方法論的演化紀錄：Stage 0 variant 規劃把 collapse 率從 60% 降到 0%"
date: 2026-05-19
description: "跨 vendor migration playbook 需要獨立寫作方法論的依據，以及這套方法論從三輪 batch dogfood 中演化出來的驗證證據。"
tags: ["writing-methodology", "migration-playbook", "cross-vendor", "technical-writing", "retrospective"]
---

本文記錄 migration-playbook-methodology 這套寫作方法論前三輪 batch dogfood（實際寫文章驗證方法論）的演化過程（skill 已累積到六輪、本文記錄前三輪）。操作步驟維護在 `.claude/skills/migration-playbook-methodology/`，本文只保留 retrospective — 每一輪跑出來學到什麼、哪些假設被推翻。

## 為什麼 migration playbook 需要自己的方法論

Migration playbook 跟 [single feature deep article](/posts/vendor-deep-article-methodology/) 是不同 content category：

| 維度              | Deep article                                                               | Migration playbook                                               |
| ----------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 主題形狀          | Single feature（pgBouncer / Vault dynamic credential）                     | Cross-vendor process（Splunk → Elastic）                         |
| 結構              | 6-section（problem → concept → config → failure → capacity → integration） | 6 種不同 type、各對應不同結構                                    |
| 重點章節          | Step-by-step 配置 + 故障演練                                               | 視 type 不同：phased flow / parallel streams / hybrid            |
| 寫作週期 / 篇     | 1-2 小時                                                                   | 2-3 小時（diff dimension audit + 結構選擇 + 寫作）               |
| 跨篇 cadence 風險 | 中（章節 1 entry 容易 collapse）                                           | 高（migration 主題本質相似、主題語意 attractor「為什麼遷」明顯） |

關鍵差異：deep article 是 single direction implementation、migration playbook 是 bidirectional comparison + process。第一輪寫了 5 篇後發現結構完全不同；嘗試套 deep article 的固定結構都只對 1 種情境適用，於是用 diff dimension audit（寫前評估 source/target 在哪些維度差異最大）選對應的結構模板（Type A-F，依主導差異維度決定）。

## 第一輪 batch（5 篇）：Type A-E 浮現 + cadence collapse 3/5

第一輪寫了 5 篇跨 vendor migration playbook，每篇自然對映到一種 type（結構模板）：

- [Splunk → Elastic Security](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) — Type A phased translation
- [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) — Type B drop-in
- [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) — Type C operational hybrid
- [Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/) — Type D parallel streams
- [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) — Type E paradigm shift

### Cadence collapse：前 3 篇被動寫作全部同質化

Cadence collapse 指批量寫作時、多篇文章的開場句型不自覺重複同一模式。

| 篇                    | Variant 規劃 | 章節 1 entry framing                               |
| --------------------- | ------------ | -------------------------------------------------- |
| 1 Splunk → Elastic    | 被動         | 「為什麼遷：cost / multi-vendor / cloud-native」   |
| 2 Redis → DragonflyDB | 被動         | 「為什麼遷：cost / single-thread / multi-tenancy」 |
| 3 Postgres → Aurora   | 被動         | 「為什麼遷：operational cost / HA / DR」           |
| 4 Datadog → Grafana   | 主動         | 「$50K/month bill 拆解」                           |
| 5 Kafka ↔ NATS        | 主動         | 「『Kafka → NATS migration』字面上不成立」         |

3/5 collapse — 主題語意 attractor「為什麼遷：X / Y / Z driver」在前 3 篇被動寫作下浮現。寫第 4 篇前發現問題、後 2 篇主動換 entry variant。

前 3 篇的 collapse 是 Stage 0 variant 規劃成為硬需求的直接證據。

### Type A-E 怎麼浮現

5 篇寫完後比對結構、發現 5 篇結構完全不同，但都可以用「主導差異維度」解釋：schema 差為主 → phased translation、全 Low → drop-in、operational 差為主 → hybrid。Type A-E 從這 5 篇的歸納中浮現，第二輪 dogfood 再加上 Type F（topology re-layout）。

## 第二輪 batch（5 篇）：漏類驗證 + 多軸 High 實證

第二輪刻意選漏類場景驗證 self-aware limitation：

- [PostgreSQL major version upgrade (14 → 17)](/backend/01-database/vendors/postgresql/major-version-upgrade/) — 漏類驗證（同 vendor）
- [Redis cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/) — 漏類驗證（topology 重劃）→ Type F 浮現
- [PostgreSQL → CockroachDB](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/) — 三維 High multi-axis 驗證
- [MySQL → PostgreSQL](/backend/01-database/vendors/mysql/migrate-to-postgresql/) — Type A 標準形態（263 行）
- [MongoDB → Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/) — Type C 標準形態（349 行）

Stage 0 variant 規劃從第二輪開始全面啟用，cadence collapse 從 3/5 降到 0/5。

### 驗證成立的 4 項預測

1. **5 type 漏類確認**：major version upgrade + re-sharding 結構跟 5 type 完全不同
2. **多重歸類 + tie-breaking 規則成立**：PostgreSQL → CockroachDB 三維皆 High、按主導維度走 Type E + 高維度獨立段
3. **Type A / Type C 標準形態仍適用**：MySQL → PostgreSQL + MongoDB → Atlas 走標準模板
4. **Stage 0 variant 規劃硬需求**：第二輪 5 篇全主動 variant、collapse 0/5

### 浮現的 3 項新議題

1. **新 audit 維度（data topology）**：re-sharding 揭露 5 維度沒「topology」軸 → 擴到 6 維
2. **「為什麼這篇不套」是漏類文章標準 frame**：major-version-upgrade + cluster-resharding 都用這個 frame 開頭
3. **「高維度獨立段」升級為 multi-axis migration 標準結構元素**

## 第三輪 batch（5 篇）：Type F dogfood + 候選軸驗證

第三輪驗證 data topology audit dimension 的 self-aware limitation 4 條 tripwire：

- [PostgreSQL partition redesign](/backend/01-database/vendors/postgresql/partition-redesign/)（246 行）— Type F dogfood #2
- [MongoDB shard + multi-DC expansion](/backend/01-database/vendors/mongodb/shard-expansion-multi-dc/)（291 行）— Type F dogfood #3 + parallel run 例外實證
- [Vault → AWS Secrets Manager](/backend/07-security-data-protection/vendors/hashicorp-vault/migrate-to-aws-secrets-manager/)（272 行）— Identity axis 候選（45% 工作量）
- [DynamoDB consistency model optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/)（249 行）— Consistency axis 候選（85% 工作量）
- [PostgreSQL multi-region GDPR rollout](/backend/01-database/vendors/postgresql/multi-region-gdpr-rollout/)（238 行）— Residency axis 候選（40% 工作量）

第三輪維持 collapse 0/5，但 Type F 分裂出 sub-type（F-cluster vs F-multi-region），框架仍在演化。

### 累積 evidence

- **Type F sub-type 浮現**：F-cluster（單 cluster 內、不需 parallel run）vs F-multi-region（跨 region、需 parallel run）
- **3 軸候選確認可獨立**：identity / consistency / residency 各帶 30-85% 獨立工作量；累積到 3-5 case / 軸後考慮升 audit 7-9 維
- **Residency 是 cross-cutting constraint**：不只是 driver、反向約束 topology + operational + application

## 三輪對照：方法論的演化軌跡

| 維度             | 第一輪（5 篇） | 第二輪（5 篇）    | 第三輪（5 篇）  |
| ---------------- | -------------- | ----------------- | --------------- |
| Type 集合        | A-E（5 type）  | A-F（+Type F）    | A-F + sub-type  |
| Audit 維度       | 5 維           | 6 維（+topology） | 6 維 + 3 候選軸 |
| Cadence collapse | 3/5 (60%)      | 0/5 (0%)          | 0/5 (0%)        |
| Variant 規劃     | 被動 → 主動    | 全主動            | 全主動          |
| 總行數           | ~1,200         | 1,389             | 1,292           |
| 單篇行數         | 200-300        | 263-349           | 238-288         |

關鍵轉折是第一輪到第二輪：後續批次未再觀察到 collapse。

## Self-aware limitation

本 methodology 從 15 篇 migration playbook dogfood 抽出 6 type；已知 limitation：

- **6 type 非窮盡**：major version upgrade / merger consolidation 等情境不在 6 type 內
- **多重歸類常見**：實際 source/target 配對很少完美對映單一 type
- **「主導維度」需 judgment**：優先序是 audience-dependent heuristic、不是 universal 規則
- **Collapse 歸因有共變因素**：第二輪以後 collapse 消失，但同時作者已有第一輪經驗、且知道自己在測量 cadence（Hawthorne effect）。Stage 0 variant 規劃是介入手段之一，無法完全隔離歸因。N=5 的二項信賴區間也無法排除偶然
- **候選軸未 commit**：identity / consistency / residency 各 N=1、累積到 3-5 case / 軸後才考慮升維

本 methodology 接受 evolution、不假裝穩定。

## 相關連結

- Migration Playbook Methodology skill（`.claude/skills/migration-playbook-methodology/`）— 操作步驟（6 維 audit、6 type、Stage 0 variant、4-reviewer）
- [Vendor deep article methodology](/posts/vendor-deep-article-methodology/) — sibling、處理 single feature implementation
- [Case-first Agent Team Review Workflow](/posts/case-first-agent-team-review-workflow/) — 教學模組級批次寫作流程
- [#199 一篇文章只承擔一種功能](/report/single-function-per-article-sop-vs-retrospective/) — 本文精簡的依據
