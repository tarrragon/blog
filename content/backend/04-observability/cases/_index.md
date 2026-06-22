---
title: "可觀測性案例正文"
date: 2026-05-07
description: "模組四案例正文入口，將企業案例補充轉成可回寫的訊號判讀文章。"
weight: 80
tags: ["backend", "observability", "case-study"]
---

這個資料夾的核心責任是把觀測案例變成可回寫章節。案例表格提供線索，正文負責輸出訊號邊界與路由。

## 章節列表

| 章節                                                                                     | 主題                     | 核心責任                                   |
| ---------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------ |
| [4.C1](/backend/04-observability/cases/fintech-audit-evidence-observability/)            | FinTech 審計證據觀測     | 把審計與證據鏈變成可觀測訊號               |
| [4.C2](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/)    | Gaming 高峰訊號治理      | 把高峰流量下訊號失真風險前移               |
| [4.C3](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)    | Healthcare 存取可追溯性  | 把資料主權場景的存取證據做成治理閉環       |
| [4.C4](/backend/04-observability/cases/xray-to-opentelemetry-migration/)                 | X-Ray 到 OTel 轉換       | 把觀測遷移標準化成可分段執行流程           |
| [4.C5](/backend/04-observability/cases/cloud-trace-otlp-adoption/)                       | Cloud Trace OTLP 導入    | 把資料通道標準化納入觀測平台治理           |
| [4.C6](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/)       | ADOT on EKS 遷移         | 把 collector/agent 管線轉換成集中治理      |
| [4.C7](/backend/04-observability/cases/datadog-otel-migration-practice/)                 | Datadog OTel 遷移實務    | 把 APM 採集轉成 OTel-compatible 流程       |
| [4.C8](/backend/04-observability/cases/airbnb-observability-k8s-scale-signals/)          | Airbnb K8s 規模化訊號    | 把叢集擴縮行為接回觀測與容量治理           |
| [4.C9](/backend/04-observability/cases/failure-otel-migration-signal-drift/)             | 反例：OTel 遷移訊號漂移  | 雙軌採集未對齊導致告警與 SLO 判讀失真      |
| [4.C10](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)        | 對照：規模差異下觀測遷移 | 不同規模團隊在觀測遷移的風險與流程差異     |
| [4.C11](/backend/04-observability/cases/uber-m3-metrics-platform-scale/)                 | Uber M3 大規模 Metrics   | 從散落的 Prometheus 到統一 metrics 平台    |
| [4.C12](/backend/04-observability/cases/cloudflare-internal-observability-architecture/) | Cloudflare 觀測三層能力  | monitoring / analytics / forensics 拆分    |
| [4.C13](/backend/04-observability/cases/discord-storage-growth-observability-gap/)       | Discord 儲存→觀測缺口    | 每次遷移暴露觀測盲區的共同結構             |
| [4.C14](/backend/04-observability/cases/observability-cost-governance-at-scale/)         | 觀測成本治理             | attribution + cardinality budget + tiering |
