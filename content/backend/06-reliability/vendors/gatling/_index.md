---
title: "Gatling"
date: 2026-05-01
description: "JVM-based load test、Scala / Java DSL、HTTP / WebSocket"
weight: 4
---

Gatling 是 JVM-based load test 工具、Scala / Java / Kotlin DSL、強型別測試 script、適合 JVM 生態團隊與複雜 scenario。Gatling Enterprise（前 FrontLine）提供 cloud 版。

## 適用場景

- JVM 生態團隊
- 需要強型別 DSL 表達複雜 scenario
- HTTP / WebSocket / JMS / MQTT
- CI 整合與 HTML report

## 不適用場景

- 非 JVM 團隊（學習曲線）
- 想要極輕量 CLI（用 k6）

## 跟其他 vendor 的取捨

- vs `k6`：Gatling Scala 表達；k6 JS 易學
- vs `jmeter`：Gatling code-first；JMeter GUI-first

## 預計實作話題

- Scenario / simulation 設計
- Load injection profile
- Assertion 與 threshold
- Gatling Enterprise（distributed）
- Recording / 從 HAR 產生 script
