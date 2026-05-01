---
title: "Locust"
date: 2026-05-01
description: "Python-based load test、distributed、易擴展"
weight: 6
---

Locust 是 Python-based load test 工具、test 用 Python class 寫、distributed mode 內建、Web UI 即時查看。適合 Python 團隊與需要極高自訂邏輯的場景。

## 適用場景

- Python 團隊
- 需要 Python 表達複雜邏輯
- Distributed load test
- 自訂 protocol 測試（Python lib 任選）

## 不適用場景

- 極端高 VU 效能需求（Python GIL 限制、需要 distributed 才衝高）
- 想要編譯後分發的 binary（用 k6）

## 跟其他 vendor 的取捨

- vs `k6`：Locust Python；k6 JS 編譯
- vs `jmeter`：Locust code-first；JMeter GUI
- vs `gatling`：Python vs JVM

## 預計實作話題

- User class 與 task 設計
- Distributed mode（master / worker）
- 自訂 client（gRPC、WebSocket、custom protocol）
- Web UI vs headless
- locust-plugins 生態
