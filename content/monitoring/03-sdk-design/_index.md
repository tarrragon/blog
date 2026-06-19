---
title: "模組三：SDK 設計模式"
date: 2026-06-19
description: "跨平台 SDK 的自動攔截、手動上報、攢批送出、離線 buffer 設計"
weight: 3
tags: ["monitoring", "sdk", "js", "flutter", "python"]
---

回答「怎麼在各平台埋點」。三個 SDK（JS/Flutter/Python）共用同一套事件格式，公開 API 保持一致。

## 待寫章節

- [ ] SDK 公開 API 設計（init / event / error / metric / flush / close）
- [ ] 自動攔截機制（JS window.onerror / Flutter FlutterError / Python sys.excepthook）
- [ ] 攢批送出策略（flush interval / buffer size / flush on close）
- [ ] 離線 buffer 與重試（FIFO 丟棄 / 本地 persistence / 恢復後補發的取捨）
- [ ] SDK redaction helper（模組七的實作層）

## 跨分類引用

- → [testing 模組三 協議整合測試](/testing/03-protocol-integration-test/)：SDK 的 HTTP POST 行為需要 protocol test
- → [monitoring 模組七 資安](/monitoring/07-security-privacy/)：redaction 在 SDK 端做
- 實作 repo：tarrragon/monitor 的 sdk-js / sdk-flutter / sdk-python
