---
title: "模組三：SDK 設計模式"
date: 2026-06-19
description: "跨平台 SDK 的自動攔截、手動上報、攢批送出、離線 buffer 設計"
weight: 3
tags: ["monitoring", "sdk", "js", "flutter", "python"]
---

回答「怎麼在各平台埋點」。三個 SDK（JS/Flutter/Python）共用同一套事件格式，公開 API 保持一致。

## 章節

- [SDK 公開 API 設計](/monitoring/03-sdk-design/public-api/) — init / event / error / metric / flush / close 的介面設計
- [自動攔截機制](/monitoring/03-sdk-design/auto-intercept/) — JS window.onerror / Flutter FlutterError / Python sys.excepthook 的自動錯誤攔截
- [攢批送出策略](/monitoring/03-sdk-design/batch-flush/) — flush interval、buffer size、flush on close 的送出策略
- [離線 buffer 與重試](/monitoring/03-sdk-design/offline-buffer/) — FIFO 丟棄、本地 persistence、恢復後補發的取捨
- [SDK redaction helper](/monitoring/03-sdk-design/redaction-helper/) — 模組七 redaction 策略在 SDK 端的實作層
- [前端感測器設計](/monitoring/03-sdk-design/frontend-sensor-design/) — 什麼行為值得埋感測器、取樣策略和效能影響
- [感測器生命週期管理](/monitoring/03-sdk-design/sensor-lifecycle-management/) — 產品生命週期五個階段各啟用什麼感測器、feature flag 整合

## 跨分類引用

- → [testing 模組三 協議整合測試](/testing/03-protocol-integration-test/)：SDK 的 HTTP POST 行為需要 protocol test
- → [monitoring 模組七 資安](/monitoring/07-security-privacy/)：redaction 在 SDK 端做
- ← [testing 模組一 測試策略](/testing/01-test-strategy-layers/)：mock 遮蔽機制影響 SDK 的 auto-intercept 行為驗證
- 實作 repo：tarrragon/monitor 的 sdk-js / sdk-flutter / sdk-python
