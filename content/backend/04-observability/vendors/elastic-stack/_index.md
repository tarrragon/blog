---
title: "Elastic Stack"
date: 2026-05-01
description: "ELK：Elasticsearch / Logstash / Kibana + Beats / APM"
weight: 5
---

Elastic Stack（前 ELK）是 logs 為主的 observability 棧、Elasticsearch 做搜尋與分析、Kibana 視覺化、Beats / Logstash 採集、Elastic APM 提供 tracing。可自管、Elastic Cloud SaaS、或 AWS OpenSearch fork。

## 適用場景

- Logs-heavy 場景、需要強 full-text search
- 既有 ELK 投資
- 需要 log + metrics + APM 統一搜尋介面
- 安全與 SIEM 整合（Elastic Security）

## 不適用場景

- Pure metrics 場景（不如 Prometheus）
- 想要 OSS-licensed（Elastic License 非 OSI、AWS 因此 fork OpenSearch）
- 維運成本敏感（自管 ES cluster 不簡單）

## 跟其他 vendor 的取捨

- vs `grafana-stack`：Loki 是 ES 的輕量替代
- vs `aws-opensearch`：OpenSearch 是 Elastic 7.10 fork、Apache 2.0 授權
- vs `splunk`（T2）：類似定位、Splunk 偏企業

## 預計實作話題

- Elasticsearch index 設計與 lifecycle
- Logstash vs Beats vs Filebeat
- Kibana dashboard
- Elastic APM
- Elastic License vs OpenSearch 取捨
