---
title: "Gatling"
date: 2026-05-01
description: "JVM-based load test、Scala / Java DSL、HTTP / WebSocket"
weight: 4
tags: ["backend", "reliability", "vendor"]
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

## 案例回寫

| 案例方向                                                                                                           | 對應主題                                            |
| ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| [LinkedIn：Capacity 與 On-call 分層](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/) | JVM 服務的 capacity headroom 與 automated load test |
| [Shopify：BFCM 容量治理與 Game Day](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)             | 峰值準備期 scenario-driven load test 的對照組       |

**待補 Gatling customer case**：JVM 重度生態（金融 / e-commerce）採用 Gatling Enterprise、HAR-driven scenario recording 實踐案例。
