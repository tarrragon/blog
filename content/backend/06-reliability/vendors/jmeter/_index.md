---
title: "Apache JMeter"
date: 2026-05-01
description: "老牌 load test 工具、GUI + plugins"
weight: 5
---

JMeter 是 Apache 出品的老牌 load test 工具、GUI 設計 + XML save format、plugins 生態廣、支援多 protocol（HTTP / JDBC / JMS / FTP / mail）。學習曲線低、企業環境常見。

## 適用場景

- 既有 JMeter 投資與測試資產
- 多 protocol 測試（不只 HTTP）
- GUI 設計者主導
- 企業內部、監管環境

## 不適用場景

- CI-first / code-first workflow（用 k6 / Gatling）
- 需要極高 VU 量（JVM 限制）
- 模組化與版本控制（XML 不友善）

## 跟其他 vendor 的取捨

- vs `k6` / `gatling`：JMeter GUI；其他 code-first
- vs Locust：JMeter Java；Locust Python

## 預計實作話題

- Thread group / sampler / listener
- Distributed testing
- Plugins（JMeter Plugins Manager）
- Non-GUI mode for CI
- HTML report（dashboard）
