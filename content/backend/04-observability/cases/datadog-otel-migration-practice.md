---
title: "4.C7 Datadog：OTel 相容遷移實務"
date: 2026-05-07
description: "APM 採集從專有代理轉向 OTel 相容模式的治理案例。"
weight: 7
---

這個案例的核心責任是把 observability 遷移做成可逐步替換的技術路線。

## 觀察

Datadog 與 OTel 生態整合的做法，顯示團隊可在不一次重寫下逐步切換採集管線。

## 判讀

觀測遷移的主要風險是資料語意漂移與管線雙軌期成本，而非單一 agent 安裝。

## 策略

1. 先建立雙軌採集的對照驗證。
2. 把 schema 與 sampling 政策版本化。
3. 用品質指標決定何時關閉舊管線。

## 下一步路由

回 [4.11](/backend/04-observability/telemetry-pipeline/) 與 [4.17](/backend/04-observability/telemetry-data-quality/)。

## 引用源

- [Datadog and OpenTelemetry](https://www.datadoghq.com/blog/instrument-python-apps-with-datadog-and-opentelemetry/)
