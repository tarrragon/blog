---
title: "Self-managed Prometheus → Grafana Cloud Metrics：feature × ops × cost 對照"
date: 2026-05-19
description: "Self-managed Prometheus → Grafana Cloud Metrics (Mimir-backed) 是 Type C operational redesign — Prometheus query API 完全相容、operational stack (HA / retention / scaling) 全託管；本文用 feature / ops / cost 三維對照表開頭、5 個 production 踩雷"
weight: 11
tags: ["backend", "observability", "prometheus", "grafana-cloud", "mimir", "managed", "migration", "type-c"]
---

> 本文是跨 vendor migration playbook、cross-link [Prometheus](/backend/04-observability/vendors/prometheus/) 跟 [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)（Grafana Cloud Metrics、Mimir-backed）。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *Operational = High → Type C operational redesign hybrid*。

## Feature / ops / cost 三維對照

| 維度 | Self-managed Prometheus | Grafana Cloud Metrics |
|---|---|---|
| Storage backend | Local disk + remote_write (optional) | Mimir + S3 (auto cold tier) |
| Retention | TSDB local 15 天 default | 13 個月 default、可延長 |
| HA | Two Prometheus + sidecar | Built-in multi-AZ |
| Cardinality limit | 自管 limit + recording rule | 1.5M active series / tier、scale-up 配額 |
| Query API | PromQL + Prometheus HTTP API | 完全相容 |
| Alert | Alertmanager self-managed | Grafana Cloud Alerting |
| Dashboard | Grafana self-managed | Grafana Cloud (included) |
| Long-term storage | Thanos / Cortex / Mimir 自管 | Mimir 內建 |
| Cost (mid-tier) | $500-2000 / mo + ops FTE | $300-1500 / mo (按 series) |
| Operational FTE | 0.3-0.8 | 0.05-0.15 |

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/)：

| 維度 | 等級 |
|---|---|
| Schema / API | Low（PromQL + API 完全相容）|
| Operational | **High**（HA / retention / scaling 全託管）|
| Paradigm | Low（同 Prometheus metric paradigm）|
| Components | Low |
| Application change | Low（remote_write endpoint 改）|
| Data topology | Low |

Operational = High → Type C standard。

## 為什麼遷：retention / ops / vendor consolidation 三條 driver

| Driver | 觸發 |
|---|---|
| Retention | Prometheus TSDB local 預設 15 天、長期 retention 需要 Thanos / Cortex / Mimir 自管 |
| Ops FTE | Self-managed Prometheus + Alertmanager + Grafana 自管全部加起來 0.5-1 FTE |
| Vendor consolidation | 已用 Grafana Cloud（logs / traces）、metric 加進 stack 統一 |

## Operational redesign

| Concept | Self-managed | Grafana Cloud Metrics |
|---|---|---|
| Cluster bootstrap | Helm chart + manual config | UI 一鍵建 |
| HA | Two Prometheus 配置 | 內建 multi-AZ Mimir |
| Long-term retention | Thanos / Cortex / Mimir 自管 | Built-in (S3-backed) |
| Cardinality control | Manual recording rule + relabel | Adaptive sampling + cardinality limit |
| Alerting | Alertmanager 自管 | Grafana Cloud Alerting (integrated) |
| Dashboard | Grafana self-host | Grafana Cloud (free tier 包含) |

## Migration 4-phase

### Phase 0：Audit

- 列所有 Prometheus job / scrape config
- 統計 active series 數（Mimir tier 計費基準）
- 估 retention 需求

### Phase 1：Grafana Cloud setup

- Account + organization 設定
- API key for `remote_write`
- Grafana Cloud Mimir endpoint 啟用

### Phase 2：Dual-write

```yaml
# prometheus.yml
remote_write:
  - url: https://prometheus-prod-XX-prod-us-central-0.grafana.net/api/prom/push
    basic_auth:
      username: <INSTANCE_ID>
      password: <API_KEY>
    write_relabel_configs:
      # Optional: drop high-cardinality before sending
      - source_labels: [__name__]
        regex: 'high_card_metric_.*'
        action: drop
```

跑 4-8 週、確認 query 結果一致 + cost 在預期。

### Phase 3：Cutover

- Dashboard / alert 切到 Grafana Cloud endpoint
- 應用層 / Grafana 自管 instance 關閉 query 對 self-managed Prometheus

### Phase 4：Cleanup

- Self-managed Prometheus stop scrape
- 留 1-2 月歷史查詢能力（用 archive snapshot）
- Decommission

## Production 故障演練

### Case 1：Cardinality 爆、cost 暴漲

**徵兆**：dual-write 第 2 週 Grafana Cloud series 從預估 100K 漲到 800K、cost 翻 8 倍。

**根因**：application-level high-cardinality label（user_id / request_id）沒被 drop、scraped 進來。

**修法**：

1. `write_relabel_configs` drop unbounded label
2. Application metric 設計改 fixed-bucket histogram、不用 unbounded label
3. Mimir cardinality limit 設保護 + alert

### Case 2：Recording rule 對應失效

**徵兆**：cutover 後 Grafana dashboard 某些 panel 顯示空；發現用了 Prometheus 端 recording rule (`job:request_count:rate5m`)、Grafana Cloud 端沒對應 rule。

**根因**：Prometheus 端 recording rule 是 *server-side*、不會跟著 remote_write 帶過去；Grafana Cloud 需要自己 setup recording rule。

**修法**：

1. Export 所有 recording rule、import 到 Grafana Cloud Mimir
2. 或改用 *raw query* + Grafana query template、不依賴 recording rule

### Case 3：PromQL 微差行為

**徵兆**：某些 query 在 self-managed Prometheus 跑得好好的、切 Grafana Cloud Mimir 後 returns slightly different results。

**根因**：Mimir 對某些 edge case（empty result handling / staleness marker timing）行為跟 Prometheus 略不同；多數 query 一致、< 1% query 受影響。

**修法**：

1. Pre-cutover dual-query 驗證、用 critical dashboard 比對
2. Affected query 重寫、用更 robust PromQL pattern
3. 文件 known incompatibility list

### Case 4：Alert routing 改變

**徵兆**：Cutover 後 PagerDuty / Slack 收不到 alert；發現 Alertmanager 端 webhook 沒切。

**根因**：alert 邏輯從 self-managed Alertmanager 搬到 Grafana Cloud Alerting、routing / contact 配置完全重做。

**修法**：

1. Pre-cutover 在 Grafana Cloud 端 rebuild alert + routing
2. 雙 alert pipeline 跑 1-2 週、確認 Grafana Cloud 收到
3. Cutover 切 routing、SOC drill 一次

### Case 5：歷史資料查不到

**徵兆**：Cutover 後 SOC 想 query 6 個月前事件、Grafana Cloud 只有 2 個月（dual-write 後的）資料。

**根因**：Grafana Cloud 從 dual-write 開始才有資料、之前的 self-managed Prometheus historical data 沒 backfill。

**修法**：

1. Phase 2 期間用 `promtool tsdb dump` + `mimirtool` 把 self-managed historical 灌進 Mimir
2. 或保留 self-managed Prometheus read-only 6 個月（給 historical query）
3. Long-term：retention 從 cutover 開始算、historical 是 *one-time backfill*

## Capacity / cost

| 維度 | Self-managed | Grafana Cloud Metrics |
|---|---|---|
| Compute (100 host, 100K series) | $500-1000 / mo + ops | $300-800 / mo |
| Operational FTE | 0.3-0.8 = $3K-8K | 0.05-0.15 = $500-1500 |
| Long-term retention | Thanos / Cortex / Mimir 自管 | Built-in 13 個月 |
| Total (mid-tier) | $4K-9K / mo (含 FTE) | $1K-2.5K / mo |
| Migration cost | - | 1-2 FTE × 1-2 個月 |

## 整合 / 下一步

### 跟 [Datadog → Grafana Stack migration](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/) 對位

兩條 Grafana Stack 路線：

- Self-host (Mimir + Loki + Tempo) on K8s：開源、自管
- Grafana Cloud：SaaS、operational simplification

本篇是「self-managed Prometheus → Grafana Cloud」、互補；如果跑兩階段（self-host → Cloud）跟「Datadog → Grafana Cloud」差不多。

### 跟 OpenTelemetry 整合

OTel Collector 可同時 ship 到 Mimir (metric) + Loki (log) + Tempo (trace)；Migration 順便升 OTel 化避免下次 vendor 切換重複。

## 相關連結

- Source vendor：[Prometheus](/backend/04-observability/vendors/prometheus/)
- Target vendor：[Grafana Stack](/backend/04-observability/vendors/grafana-stack/)
- 平行 migration playbook (Type C)：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) / [Kafka → MSK](/backend/03-message-queue/vendors/kafka/migrate-to-msk/) / [ELK → Elastic Cloud](/backend/04-observability/vendors/elastic-stack/migrate-to-elastic-cloud/)
- 平行 D-type 對位：[Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
