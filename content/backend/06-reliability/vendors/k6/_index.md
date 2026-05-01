---
title: "k6"
date: 2026-05-01
description: "現代 load test、JS scripting、Grafana Labs"
weight: 3
---

k6 是 Grafana Labs 出品的 load test 工具、Go 寫成、JS 寫測試 script、CLI-first、cloud 版（k6 Cloud / Grafana Cloud k6）。是現代 load test 主流選擇。

## 適用場景

- HTTP / WebSocket / gRPC load test
- CI 內整合（threshold-based pass/fail）
- 需要 JS scripting 表達能力
- Grafana 生態整合

## 不適用場景

- 需要 GUI 拖拉式測試設計（用 JMeter）
- 極端複雜 protocol（k6 偏 HTTP-family）
- 預算極敏感且需要 cloud（k6 Cloud 商業）

## 跟其他 vendor 的取捨

- vs `gatling`：k6 JS 易學；Gatling Scala / Java 表達豐富
- vs `jmeter`：k6 CLI-first；JMeter GUI + 老牌
- vs `locust`：k6 編譯效能；Locust Python 彈性

## 預計實作話題

- Test script 結構（VU / iteration / stages）
- Threshold 設計與 CI 整合
- k6 extensions（xk6）
- Distributed load（k6 Operator on k8s）
- Browser testing（k6 browser）
- Grafana Cloud k6
