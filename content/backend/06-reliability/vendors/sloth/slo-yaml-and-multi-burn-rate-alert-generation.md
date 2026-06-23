---
title: "Sloth：SLO YAML 與 Multi-burn-rate Alert 生成"
date: 2026-06-23
description: "用宣告式 YAML 定義 SLO，自動生成 Prometheus multi-window multi-burn-rate recording 與 alerting rules。"
weight: 1
tags: ["backend", "reliability", "vendor", "slo"]
---

## 問題情境

SLO 從定義到 Prometheus 落地需要多層 rule。一個 SLO 對應 4 組 time window 的 recording rule（計算各窗口的 [burn rate](/backend/knowledge-cards/burn-rate/)），再對應 fast burn 和 slow burn 兩組 alerting rule。手動維護這些 rule 容易出錯：window 參數不一致、新增 SLO 忘記補 alert、修改 SLI expression 只改了部分 rule。

Sloth 的責任是把這個過程自動化。輸入一份 SLO YAML，產出一組完整的 Prometheus recording + alerting rules，讓 SLO 維護回到宣告式：改 YAML、重新生成、載入 Prometheus。

## SLO YAML 設計

Sloth YAML 的核心結構是 `version` → `service` → `slos[]`。每個 SLO 定義三件事：目標數字（objective）、量測方式（SLI）、告警等級（alerting）。

```yaml
version: prometheus/v1
service: checkout-api
slos:
  - name: availability
    objective: 99.9
    description: "checkout API 的請求成功率"
    sli:
      events:
        error_query: sum(rate(http_requests_total{service="checkout",code=~"5.."}[{{.window}}]))
        total_query: sum(rate(http_requests_total{service="checkout"}[{{.window}}]))
    alerting:
      name: CheckoutAvailability
      page_alert:
        labels:
          severity: critical
      ticket_alert:
        labels:
          severity: warning
```

SLI 有兩種類型。events-based SLI 用 error/total ratio 定義，Sloth 自動把 `{{.window}}` 參數代入各 recording rule 的 range vector。raw SLI 直接寫 PromQL expression 算 error ratio，適合非 request-based 的 SLO（如 data freshness、replication lag）。

raw SLI 範例 — data freshness：

```yaml
  - name: data-freshness
    objective: 99.5
    sli:
      raw:
        error_ratio_query: |
          1 - clamp_max(
            replication_lag_seconds{service="checkout-db"} / 60,
            1
          )
```

objective 數字的來源是 [6.6 SLO 政策](/backend/06-reliability/slo-error-budget/) — 先從使用者旅程定義服務承諾，再把承諾轉成 objective。Sloth 不負責決定 objective 該是多少，只負責把 objective 轉成可執行的 Prometheus rule。

alerting 分 page（嚴重，觸發即時通知）和 ticket（一般，產生工單）。兩者的 burn rate 門檻不同：page 用 fast burn window，ticket 用 slow burn window。label 設計跟 Alertmanager routing 對齊 — `severity: critical` 走 PagerDuty / Slack alert channel，`severity: warning` 走 ticket system（Jira / Linear）。

## Multi-window Multi-burn-rate Alert

Sloth 預設產生 Google SRE 推薦的 4-window alert 結構。每個 SLO 生成以下 recording rules 和 alerting rules。

| Window 組合 | 責任               | 觸發行動                        |
| ----------- | ------------------ | ------------------------------- |
| 5m / 1h     | Fast burn 偵測     | 短時間大量消耗 → page 通知      |
| 30m / 6h    | Moderate burn 偵測 | 中速消耗 → page 或 ticket       |
| 2h / 1d     | Slow burn 偵測     | 緩慢消耗 → ticket               |
| 6h / 3d     | Very slow 偵測     | 長期趨勢退化 → ticket 或 review |

fast burn alert 回答「error budget 是否正在被快速吃掉」。當 5 分鐘窗口的 burn rate 超過 14.4 倍（代表如果持續下去，1 小時會消耗完整個月的 budget），觸發 page。這個門檻的設計邏輯是：越短的窗口允許越高的 burn rate 容忍，因為短窗口的 false positive 率較高，需要搭配較長窗口的確認。

slow burn alert 回答「error budget 是否在不被注意的情況下被緩慢消耗」。6 小時窗口的 burn rate 超過 1 倍（代表月底會剛好用完 budget），觸發 ticket。slow burn 常被忽略，但它是高變更頻率服務最常見的可靠性退化模式 — 每次小回歸都不夠大到觸發 fast burn，累積到月底才發現 budget 已透支。

burn rate alert 跟 [6.6 SLO error budget 政策](/backend/06-reliability/slo-error-budget/) 直接對應：fast burn → 凍結變更；slow burn → 提高驗證門檻；budget 健康 → 正常發版。

Sloth 產出的 recording rule 範例（5m window）：

```yaml
- record: slo:sli_error:ratio_rate5m
  expr: |
    sum(rate(http_requests_total{service="checkout",code=~"5.."}[5m]))
    /
    sum(rate(http_requests_total{service="checkout"}[5m]))
  labels:
    sloth_service: checkout-api
    sloth_slo: availability
```

對應的 alerting rule（fast burn）：

```yaml
- alert: CheckoutAvailabilityFastBurn
  expr: |
    slo:sli_error:ratio_rate5m{sloth_slo="availability"} > (14.4 * 0.001)
    and
    slo:sli_error:ratio_rate1h{sloth_slo="availability"} > (14.4 * 0.001)
  labels:
    severity: critical
```

fast burn alert 要求 5m 和 1h 兩個窗口同時超過門檻，短窗口防止 spike false positive、長窗口確認趨勢持續。

## 實作流程

### CLI 生成

```bash
sloth generate -i slo.yaml -o rules.yaml
sloth validate -i slo.yaml
```

`generate` 產出的 `rules.yaml` 包含所有 recording rules 和 alerting rules，直接放入 Prometheus 的 `rule_files` 載入。`validate` 在 CI 中先行檢查 YAML 格式與 SLI expression 語法。

### K8s Operator mode

Sloth 提供 K8s Operator，用 `PrometheusServiceLevel` CRD 定義 SLO。Operator 自動 reconcile，把 CRD 轉成 Prometheus rules 並同步到 Prometheus Operator 的 `PrometheusRule` 資源。

Operator mode 適合 K8s-native 環境：SLO 定義跟 service deployment 放在同一個 GitOps repo，變更 SLO 跟變更服務走同一套 PR review + CI 流程。

### CI / GitOps 整合

在 CI pipeline 中跑 `sloth validate` 驗證 YAML，再跑 `sloth generate` 產出 rules，commit 進 GitOps repo。Prometheus 透過 config reload 或 Operator reconcile 載入新 rules。這條流程讓 SLO 變更有版本歷史、有 review、有 rollback 能力。

## 邊界與陷阱

Sloth 只支援 Prometheus 作為後端。若觀測平台是 Datadog、New Relic、Honeycomb 或 Grafana Cloud，需要各平台自己的 SLO 功能或 [Nobl9](/backend/06-reliability/vendors/nobl9/) 的 multi-source 整合。

SLI expression 錯誤是最常見的問題。分母為零（service 沒有流量）會產生 NaN，cascading 到所有 recording rule。label 不匹配（`service` label 拼錯）會產生空 series，alert 永遠不觸發。`sloth validate` 檢查語法但不檢查 Prometheus 中是否真的有對應 series — 上線後需要用 Prometheus query 確認 recording rule 產出非空結果。

SLO 數量增長會累積 recording rule 成本。每個 SLO 產生約 30 條 recording rule（4 windows × 多組 aggregation）。100 個 SLO 產生 3000 條 rule，Prometheus 的 rule evaluation 會消耗明顯的 CPU 和記憶體。定期監控 `prometheus_rule_evaluation_duration_seconds` 和 `prometheus_rule_group_rules`，在 rule 數量影響 evaluation latency 前調整。

升級路徑：Sloth YAML 跟 OpenSLO spec 部分相容。從 Sloth 移到 Nobl9 時，SLO 定義的語意可以保留，SLI expression 需要改寫成 Nobl9 的 data source query。這條路徑適合從 Prometheus-only 環境逐步擴展到 multi-source SLO governance。

## 整合路由

- 上游：[6.6 SLO 與 Error Budget 政策](/backend/06-reliability/slo-error-budget/) — SLO 定義與 objective 來源
- 下游：[6.8 Release Gate](/backend/06-reliability/release-gate/) — burn rate alert 觸發凍結
- 平行：[Nobl9](/backend/06-reliability/vendors/nobl9/)（SaaS multi-source）、Pyrra（K8s-native + UI）
- 案例回寫：[Google G1](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/)（error budget policy 原典）、[Honeycomb HC1](/backend/06-reliability/cases/honeycomb/burn-rate-driven-reliability-operations/)（burn rate 驅動可靠性操作）
