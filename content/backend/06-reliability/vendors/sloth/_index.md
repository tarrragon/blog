---
title: "Sloth"
date: 2026-05-01
description: "OSS SLO generator for Prometheus"
weight: 12
tags: ["backend", "reliability", "vendor"]
---

Sloth 是 OSS Prometheus SLO generator、承擔三個責任：輸入簡單 YAML 定義 SLO、輸出 Prometheus recording rules + alerting rules（multi-window multi-burn-rate）、降低 SLO 維護成本。設計取捨偏向「Prometheus-only + OSS + GitOps-friendly」、適合 Prometheus-based 環境的純 OSS SLO 流程、跟 Nobl9 的 SaaS / multi-source 是不同定位。

## 本章目標

讀完本章後、你應該能：

1. 寫 Sloth SLO YAML
2. 產生 Prometheus recording / alerting rules
3. 設計 multi-window multi-burn-rate alert
4. 用 K8s Operator mode 自動同步
5. 評估從 Sloth 升級到 Nobl9 / OpenSLO 路徑

## 最短路徑：5 分鐘把 Sloth 跑起來

```bash
# 1. 安裝
# TODO: brew install slok/sloth/sloth / docker run

# 2. 寫 SLO spec YAML
# TODO: version: prometheus/v1, service, slos: [{name, objective, sli}]

# 3. Generate rules
# TODO: sloth generate -i slo.yaml > rules.yaml
# TODO: 把 rules.yaml 載入 Prometheus
```

## 日常操作與決策形狀

### SLO YAML 結構

子議題：

- version + service
- slos[]：name / objective / SLI（events / raw）
- Alerting（page / ticket）

### Multi-window multi-burn-rate alert

子議題：

- Sloth 預設產生 Google SRE recommended alert（4 windows）
- Fast burn / slow burn
- 對應 page（urgent）vs ticket（non-urgent）

### Generate rules workflow

子議題：

- CLI generate
- Output: recording rules + alert rules
- 放進 Prometheus rule_files 載入

## 進階主題（按需閱讀）

### Kubernetes Operator mode

子議題：

- Sloth K8s Operator
- PrometheusServiceLevel CRD
- 自動 reconcile + 同步 Prometheus rules
- 對應 [Kubernetes vendor 頁](/backend/05-deployment-platform/vendors/kubernetes/)

### SLO types

子議題：

- Events-based SLI（好 events / 總 events）
- Raw query SLI（自訂 PromQL）
- 對應 PromQL 撰寫

### CI / GitOps

子議題：

- Sloth 在 CI 跑 generate
- Git commit rules.yaml
- Prometheus pull rules.yaml

### vs Pyrra

子議題：

- Sloth：CLI + Operator、產生 rules
- Pyrra：K8s-native CRD、UI 內建
- 選擇判讀：簡單 / CI-first → Sloth；K8s-native + UI → Pyrra

### vs Nobl9

子議題：

- Sloth：OSS / Prometheus-only / 無 SaaS
- Nobl9：商業 SaaS / 多 source / governance
- 升級路徑：OpenSLO YAML 部分相容

### Alert tuning

子議題：

- Burn rate threshold 調整（依 service criticality）
- Inhibition（alert 之間互相壓制）
- 對應 Alertmanager routing

## 排錯快速判讀

### Generate fail

操作原則：YAML 格式錯 / SLI query 語法錯。判讀：sloth validate。

### Alert noise

操作原則：burn rate threshold 過嚴。

### Recording rule 太多

操作原則：每 SLO 產生 N recording rules、cardinality 累積快。判讀：Prometheus series count。

### Operator reconcile 失敗

操作原則：CRD permission / Prometheus rule API 連不上。

## 何時改走其他服務

| 需求形狀            | 改走                                            |
| ------------------- | ----------------------------------------------- |
| Multi-source        | [Nobl9](/backend/06-reliability/vendors/nobl9/) |
| K8s-native CRD + UI | Pyrra                                           |
| Vendor 內建 SLO     | Datadog / Grafana / Honeycomb SLO               |
| 純 SaaS             | [Nobl9](/backend/06-reliability/vendors/nobl9/) |
| 完整 OpenSLO        | OpenSLO + 對應 generator                        |

## 不在本頁內的主題

- PromQL 語法基礎
- Prometheus alerting rule 內部
- Sloth 完整 CLI option

## 案例回寫

**待補 Sloth customer case**：Prometheus 重度團隊採用、Kubernetes Operator 落地案例。

## 下一步路由

- 上游概念：[knowledge cards burn-rate](/backend/knowledge-cards/burn-rate/)
- 平行 vendor：[Nobl9](/backend/06-reliability/vendors/nobl9/)、[Prometheus](/backend/04-observability/vendors/prometheus/)
- 下游能力：[04 observability](/backend/04-observability/)、[Alertmanager](/backend/04-observability/vendors/prometheus/)
