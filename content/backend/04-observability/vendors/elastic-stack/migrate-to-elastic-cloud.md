---
title: "Self-managed ELK → Elastic Cloud：5 年 ELK 集群的 lifecycle 收尾"
date: 2026-05-19
description: "Self-managed ELK Stack → Elastic Cloud 是 Type C operational redesign — protocol drop-in、operational stack（cluster sizing / shard 治理 / upgrade / backup）全託管；本文按 5 年 ELK lifecycle (build → scale → degrade → save → migrate) 組織、5 個 production 踩雷"
weight: 12
tags: ["backend", "observability", "elastic-stack", "elastic-cloud", "managed", "migration", "type-c"]
---

> 本文是跨 vendor migration playbook、cross-link [Elastic Stack](/backend/04-observability/vendors/elastic-stack/) 跟 Elastic Cloud。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *Operational = High（self-managed → Elastic managed）→ Type C operational redesign hybrid*。

## 5 年 ELK 集群的 lifecycle 收尾

跟前批 [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 同 Type C、本文用 *lifecycle-driven* entry — 看 5 年 ELK 集群典型壽命曲線：

| 年份 | Phase             | 集群狀態                                                         |
| ---- | ----------------- | ---------------------------------------------------------------- |
| 0-1  | Build             | 3 node、簡單部署、SOC 學 Lucene query / dashboard / alert        |
| 1-2  | Scale-out        | 5-7 node、shard 計畫、hot/warm/cold tier、index lifecycle management |
| 2-3  | Degrade          | 10+ node、shard 過多、query latency 升、upgrade window 開始痛   |
| 3-4  | Save             | 加 dedicated master / cross-cluster replication、ops cost 飛漲   |
| 4-5  | Migrate decision | 評估走 Elastic Cloud（managed）或下一個 SIEM vendor              |

多數中型 organization 在 lifecycle 第 4-5 年遇到 *operational ceiling* — SRE team 0.5-1.5 FTE 跑 ELK ops、新 feature 開發停滯、cost 跟 alternative observability vendor 比較。Elastic Cloud 把 operational stack 全託管、SOC 留在 *Lucene query + dashboard + alert* 層、不再管 cluster sizing。

## 為什麼遷：FTE / availability / version cadence 三條 driver

| Driver | 觸發 |
|---|---|
| FTE | Self-managed ELK 0.5-1.5 FTE 跑 ops、Elastic Cloud 降到 0.1-0.3 FTE |
| Availability | Cross-AZ failover 自管太複雜、Cloud 內建 |
| Version cadence | Elasticsearch 8.x quarterly release、self-managed upgrade window 是痛點、Cloud 自動 |

## 6 維 audit

| 維度 | 等級 |
|---|---|
| Schema / API | Low（Elasticsearch API 完全相容）|
| Operational | **High**（cluster mgmt 全託管）|
| Paradigm | Low（同 Elasticsearch + Kibana + Beats / Logstash）|
| Components | Low |
| Application change | Low-Medium（連線 endpoint + auth 改）|
| Data topology | Low |

Operational = High → Type C standard。

## Operational redesign 對位

| Concept | Self-managed ELK | Elastic Cloud |
|---|---|---|
| Cluster bootstrap | 手動 install + config | UI / API 一鍵建 deployment |
| HA | 自管 master / dedicated voting / cross-AZ | 內建 multi-AZ |
| Upgrade | 手動 rolling restart 6-12 小時 | 自動 patch + minor version |
| Backup | 自管 snapshot to S3 | 內建 snapshot lifecycle |
| Shard management | 手動 ILM policy | UI-driven ILM |
| Security | 自管 X-Pack / SSL cert | 內建 + 自動 cert rotation |
| Monitoring | 自管 Metricbeat → 自己集群 | 內建 deployment monitoring |

## Migration 4-phase

### Phase 0：Pre-migration audit

- 列 application 連線 endpoint (Logstash / Beats / SDK direct)
- 列 ILM policy + retention setting
- 估 deployment size（hot tier RAM / cold tier storage）

### Phase 1：Elastic Cloud deployment 建置

- 選 region + provider（AWS / GCP / Azure）
- Hot tier RAM × N + cold tier S3-backed × N
- Snapshot lifecycle 配置

### Phase 2：Data migration

- **Cross-cluster replication (CCR)** 從 self-managed → Cloud（推薦、incremental）
- 或 **snapshot + restore**（簡單但需要 maintenance window）

### Phase 3：Cutover + cleanup

- Application 端切 endpoint
- Self-managed 端 read-only 1-2 月
- Decommission

## Production 故障演練

### Case 1：Application endpoint hardcode、cutover 失敗

**徵兆**：cutover 後 N 個 application 仍連舊 endpoint、log / metric 斷流。

**根因**：endpoint 寫死在 config file、deploy 時沒一起改。

**修法**：endpoint 用 ENV variable + service discovery、cutover 是 single deploy。

### Case 2：CCR replication lag、cutover 時資料 gap

**徵兆**：CCR 跑 1 週、cutover 前 lag 200ms 看似 OK；application 切到 Cloud 後 search 顯示 *缺最近 5 分鐘 data*。

**根因**：CCR replication 不保證即時 catch up、cutover 期間仍可能 lag；且 follower index 對 *write* 不接受。

**修法**：

1. Cutover 流程加 *drain window* — 停 application write 5-10 分鐘、等 CCR catch up
2. 確認 follower index 已 *promote* 成 write-capable
3. 監控 CCR lag、< 100ms 才 cutover

### Case 3：Auth 改變、SOC alert 失效

**徵兆**：cutover 後 SOC dashboard 顯示「authentication failed」、SIEM rule 全失效。

**根因**：self-managed 用 X-Pack basic auth、Cloud 用 API key + SSO；SOC tooling 沒改 auth。

**修法**：

1. Pre-cutover 列所有 tool 連線 ELK 的 auth
2. 改 API key、用 IAM-friendly token rotation
3. Cloud 端 enable SSO + 設 service account

### Case 4：Cost 暴漲、cold tier 設定錯

**徵兆**：第一個月 Cloud 帳單比預估高 50%；cold tier 用 *fast storage*（hot-tier-level）而非 S3-backed。

**根因**：Cloud deployment template 預設 hot 是 fast、cold 也是 fast（slow 需要明示）；team 沒 review template。

**修法**：

1. Pre-cutover review deployment template、確認 cold tier = searchable snapshot to S3
2. Cost monitor 第一週密集 check
3. Hot tier RAM 估算 conservative

### Case 5：Snapshot 跨 region 失效

**徵兆**：DR drill 切 region 失敗；Cloud 內建 snapshot 是 same-region、不跨 region。

**根因**：multi-region DR 需要 *cross-region snapshot* 或 *multi-deployment*、不是預設。

**修法**：

1. 評估 DR 需求、是否需要 cross-region
2. 配 *additional deployment in DR region* + CCR
3. Cost 增 50-100%、是 DR 投資不是 cost optimization

## Capacity / cost

| 維度 | Self-managed ELK | Elastic Cloud |
|---|---|---|
| Compute cost (5 node) | $1,000-2,000 / mo | $1,500-3,000 / mo |
| Storage cost | EBS | included + 加 S3 cold tier |
| Operational FTE | 0.5-1.5 = $5K-15K | 0.1-0.3 = $1K-3K |
| Total (5 node, mid-tier) | $6K-17K / mo | $2.5K-6K / mo |
| Migration cost | - | 1-2 FTE × 1-2 個月 |

## 整合 / 下一步

### 跟 [Splunk → Elastic Security migration](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) 對位

兩篇都到 Elastic 生態、但 Splunk → Elastic Security 是 Schema 高差 Type A、本篇是 Operational 高差 Type C；如果同時跑兩個 migration、Splunk → Elastic Security 先、ELK Cloud 後（避免雙重變動）。

### 跟 Application observability stack 整合

Elastic Cloud + APM + OpenTelemetry：cutover 後可以 *順便升 OTel 化 application*、避免下次 vendor 切換重複工作。

## 相關連結

- Source vendor：[Elastic Stack](/backend/04-observability/vendors/elastic-stack/)
- 平行 migration playbook (Type C)：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) / [MongoDB → Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/) / [Kafka → MSK](/backend/03-message-queue/vendors/kafka/migrate-to-msk/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
