---
title: "Datadog → Grafana Stack：把 $50K/month bill 拆解到 self-hosted observability"
date: 2026-05-19
description: "Datadog 五層計費（host APM / metric / log ingest / log retention / RUM）拆解、對位 Grafana Stack（Mimir / Loki / Tempo / Grafana / Alloy）的 5 層責任；OTel-based agent migration、5 個 production 踩雷（cardinality 爆 / log volume cost / dashboard 不直接轉 / alert routing 換邏輯 / SLO definition 差異）、cost reality check"
weight: 12
tags: ["backend", "observability", "datadog", "grafana", "mimir", "loki", "tempo", "migration"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [Datadog](/backend/04-observability/vendors/datadog/)（source）跟 [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)（target）。跟前三篇 migration（[Splunk → Elastic](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) phased / [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) drop-in / [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) hybrid）對照、本篇是 *cost-driven multi-tool migration* — 不是換一個產品、是把 *一站式 SaaS* 拆成 *五個專責 OSS / cloud component*。

## $50K/month bill 拆解：先看錢花在哪、再決定怎麼遷

中型 SaaS（100-500 host、5K-50K metric series、TB-level log/day）的 Datadog 月帳單長這樣：

| 計費項                    | 平均單價                          | 中型 SaaS 估算 / month                |
| ------------------------- | --------------------------------- | ------------------------------------- |
| Infrastructure host       | $15-23 / host                      | 200 host × $20 = $4,000               |
| APM host                  | $31 / host                         | 100 host × $31 = $3,100               |
| Custom metrics            | $0.05 / 100 series                 | 30K series × $0.05 = $1,500           |
| Log ingest                | $0.10 / GB ingested                | 50TB × $0.10 = $5,000                 |
| Log retention（15-day）   | $1.27 / million events            | 50G event × $1.27 = $6,350           |
| Log indexing              | $1.70 / million events             | 50G × $1.70 = $8,500                 |
| Network                   | $5 / host                          | 200 × $5 = $1,000                    |
| RUM / Session             | $1.50 / 1000 session              | 30M session × $1.5 = $4,500          |
| Synthetics                | $5 / 10K test runs                 | 50K test = $25                       |
| Total                     | -                                  | **$34,000 / month**（保守估）         |

擴張到 500 host / 100TB log 的 production：$80K-150K / month 範圍。Grafana stack（self-hosted on K8s + Grafana Cloud 部分服務）對等 capacity 通常 $8K-30K / month — *2.5-5x cost reduction*。

但 cost 不是唯一 driver。其他 driver：

- **Multi-cloud / hybrid**：Datadog 集中、Grafana 可分散部署符合資料 residency
- **OpenTelemetry-first**：Grafana stack 對 OTel 是 native、Datadog 仍 vendor-specific agent
- **Long-term retention**：Loki 用 S3 cold tier 跑 1 年 retention 比 Datadog 便宜 10-50x

## 五個責任、五個 component：不是替換一個產品

Datadog 是 *一站式 SaaS*、單一 agent + 單一 UI 包 5 個責任。Grafana stack 把責任拆給 5 個專責 component：

| 責任             | Datadog 處理            | Grafana Stack 對應                                       |
| ---------------- | ----------------------- | -------------------------------------------------------- |
| Metric           | Datadog metric          | Mimir（Prometheus-compatible long-term）                |
| Log              | Datadog Logs            | Loki（label-indexed log）                                |
| Trace            | Datadog APM             | Tempo（trace-only object storage）                       |
| Dashboard        | Datadog dashboard       | Grafana                                                  |
| Agent / shipper  | Datadog Agent           | Alloy（OTel-based collector）+ Grafana Agent / Promtail |

Migration 是 *五個獨立 stream*、不是單一 cutover。SRE 對「一個 agent 包所有」的心智模型要拆。

## Migration 結構：每個 component 各自 phased、整體 staggered

不像前三篇 migration 是線性流程、本篇是 *5 個 parallel migration stream* + 跨 stream coordination：

```text
           Phase 0           Phase 1            Phase 2          Phase 3
           Audit             Deploy             Dual-ship        Cutover
Metric    [audit]──→        [deploy Mimir]──→ [dual-ship]──→  [cutover]
APM       [audit]──→        [deploy Tempo]──→ [dual-ship]──→  [cutover]
Log       [audit]──→        [deploy Loki]──→  [dual-ship]──→  [cutover]
Dashboard [audit]──→        [deploy Grafana]──→ [rebuild]──→   [cutover]
Alert     [audit]──→        [deploy Alertmgr]──→ [parallel]──→ [cutover]
```

每個 stream 獨立做 dual-ship + cutover、不必同步；通常 *Metric 先遷*（cardinality 議題暴露最快）、然後 Log、最後 APM（trace correlation 最依賴 dashboard / alert）。

## Agent migration：Datadog Agent → OTel Collector / Alloy

Datadog Agent 是 vendor-specific binary、抽出來換成 OpenTelemetry Collector / Grafana Alloy：

```yaml
# alloy config (HCL-like)
prometheus.scrape "k8s_pods" {
  targets = discovery.kubernetes.pods.targets
  forward_to = [prometheus.remote_write.mimir.receiver]
}

prometheus.remote_write "mimir" {
  endpoint {
    url = "https://mimir.internal/api/v1/push"
  }
}

loki.source.kubernetes "pods" {
  targets = discovery.kubernetes.pods.targets
  forward_to = [loki.write.production.receiver]
}

otelcol.receiver.otlp "default" {
  grpc {}
  output {
    traces = [otelcol.exporter.otlp.tempo.input]
  }
}
```

Migration 期間 *dual-shipper* 是標準作法：

- Datadog Agent 跟 Alloy 並存（短期 capacity 兩倍）
- 同 host 同時 ship 兩端、觀察一致性
- 漸進 disable Datadog Agent 的 metric / log / APM 子模組

## Production 故障演練

### Case 1：Cardinality 爆，Mimir 端 series 暴增

**徵兆**：Datadog 端 30K series、ship 到 Mimir 後 series 變 500K、Mimir indexer OOM。

**根因**：Datadog 內部對 tag 做 *自動 aggregation* 跟 *low-cardinality enforcement*；Prometheus / Mimir 對 *每個 unique label set* 算一個 series、application code 的 high-cardinality label（user_id / request_id）直接爆。

**修法**：

1. **Audit 階段** 跑 `topk(100, count by (__name__) ({__name__=~".+"}))` 找 high-cardinality metric
2. **drop high-cardinality label**：Alloy / OTel collector 端 `relabel` 規則 drop user_id 等 unbounded label
3. **改 histogram bucket**：高 cardinality 通常來自 label combination、改用 fixed-bucket histogram
4. **適當改 metric 為 log**：請求 ID 是 trace context、不該是 metric label

### Case 2：Log volume cost 預估失準

**徵兆**：Loki 部署 1 個月後 S3 帳單比預估高 2x；object storage 跟 query GB-scan 都超預期。

**根因**：Datadog 對 log 做自動 sampling / aggregation、bill 是 indexed event；Loki 是 *全量 raw ingest* + S3 cold storage、按實際 byte 計費。raw log volume 比 indexed event 高 3-10x。

**修法**：

1. **Ingest-side sampling**：Alloy / Promtail 端 sample debug / info log、只 ingest warn / error 全量
2. **Log structure**：JSON log 比 text log 壓縮率高、Loki S3 size 少 50%
3. **Retention tier**：hot 7 天 S3 standard / cold 1 年 S3 Glacier、retention budget 控制

### Case 3：Datadog dashboard 不能直接轉 Grafana

**徵兆**：Migration 計畫設「dashboard 自動轉換」、實際跑 Datadog API export → Grafana import、80% dashboard 缺 widget / metric 對不上。

**根因**：

- Datadog query syntax 跟 Grafana / Mimir 的 PromQL 不直接相容
- Datadog widget type（top-list / hostmap）Grafana 沒對應
- Tag-based aggregation 對應 Prometheus label 但語法不同

**修法**：

1. **接受重建**：production-grade dashboard 必須人工重建、不要期待自動轉
2. **Prioritize**：先重建 *SOC 用 / production-critical* 30%、其他 deprecate
3. **migration window 增 4-6 週**：dashboard rebuild 是 underestimated effort

### Case 4：Alert routing 換邏輯，PagerDuty integration 不通

**徵兆**：Cutover 後 alert 不送 PagerDuty、SOC 半小時才發現；alert 端 webhook 配置正確、但 payload format 跟 Datadog 不同、PagerDuty 端 rule 過濾掉。

**根因**：

- Datadog alert payload 含 `event_type=alert`、PagerDuty integration 用這個 routing
- Alertmanager 預設 payload 結構不同
- PagerDuty rule 端針對 Datadog event 寫 schema、Alertmanager event 不 match

**修法**：

1. **Pre-cutover test**：Alertmanager → PagerDuty 跑 dry-run、send test alert 驗證
2. **PagerDuty Service**：建獨立 Grafana-source Service、不共用 Datadog Service
3. **Alertmanager template**：用 webhook 自定 JSON template、payload 接近 Datadog 結構

### Case 5：SLO definition 跟 monitor type 對不上

**徵兆**：Datadog SLO 跑 99.9% availability、轉到 Grafana SLO + Mimir 後實際 9X% 數字不一致；SOC 跑 dashboard 比對 5 個 SLO、4 個誤差 0.1-0.3%。

**根因**：

- Datadog SLO 計算 over time window 用內部 query；Grafana SLO 用 PromQL 寫公式
- Datadog 對 `success_rate` 處理 missing data 跟 PromQL 預設不同
- Time bucket boundary 處理差異

**修法**：

1. **重定義 SLO 在 PromQL**：不嘗試「複製」、是「重定義」、認真寫 PromQL 表達式
2. **接受 ±0.1% drift**：production-critical SLO 跑 dual-track 1-2 個月、tune PromQL 到 acceptable drift
3. **SLO migration 不是 dashboard migration 子集**：獨立 stream、留更多時間

## Capacity / cost 對照

| 維度                       | Datadog                                | Grafana Stack（self-hosted on K8s）              |
| -------------------------- | -------------------------------------- | ------------------------------------------------ |
| Setup cost                 | 低（SaaS）                            | 中高（K8s deploy + storage backend）             |
| Operational cost (200 host) | $34K / month                          | $8-12K / month（含 S3 + K8s）                    |
| Operational cost (500 host) | $80-150K / month                       | $15-30K / month                                  |
| Operational FTE            | 0.1-0.3                                | 1-2 FTE（K8s + storage + Grafana operator）      |
| Long-term retention        | $1.27 / million event for 15+ day      | S3 + Loki：~$0.02 / GB / month                  |
| Multi-cloud / hybrid       | 受 Datadog region 限                   | 自由部署                                          |
| Vendor lock-in             | 高                                     | 低（OSS + OTel）                                 |
| Time to value              | 1-2 週                                  | 4-8 週                                            |
| Migration cost (one-time)  | -                                      | 1-3 FTE × 3 個月                                  |

**Break-even point**：~150 host 規模、3 年 amortized 後 self-hosted cheaper；< 100 host 規模 SaaS 較 ROI 高。

## 整合 / 下一步

### 跟 OpenTelemetry 對齊

Migration 是 *OTel-first 轉型* 的機會：

- Application code 用 OTel SDK、避免 Datadog SDK lock-in
- Trace context propagation 走 W3C Trace Context
- 未來換 backend 不用再改 application

### 跟 [Splunk → Elastic](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) 對照

兩篇都是 *cost-driven SaaS migration*、但細節差：

- Splunk → Elastic 是 SIEM 領域、schema translation 是核心議題
- Datadog → Grafana 是 multi-tool 拆分、agent + dashboard 重建是核心
- 共同 pattern：dual-ship → parallel run → cutover

### 反向遷移（Grafana Stack → Datadog）

存在但少數 — 主要是 *operational complexity reduction*（不想自管 Mimir / Loki）；schema 對位方向相反、agent 換回 Datadog Agent。

### 下一步議題

- **Grafana Cloud 混合**：部分 component（Tempo）用 Grafana Cloud SaaS、其他 self-host、混合架構
- **OpenTelemetry Collector 跟 Alloy 取捨**：兩者都是 OTel-based、Alloy 是 Grafana 自家 fork
- **Vector vs Alloy vs Fluentd**：log shipper 戰場、cost / 功能 / OTel 整合度比較

## 相關連結

- Source vendor：[Datadog](/backend/04-observability/vendors/datadog/)
- Target vendor：[Grafana Stack](/backend/04-observability/vendors/grafana-stack/)
- 平行 vendor：[Elastic Stack](/backend/04-observability/vendors/elastic-stack/) / [OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)
- 平行 migration playbook：[Splunk → Elastic Security](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) / [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) / [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
