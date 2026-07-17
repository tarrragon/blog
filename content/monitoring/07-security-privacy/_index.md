---
title: "模組七：資安與隱私"
date: 2026-06-19
description: "SDK redaction / transport 加密 / collector access control / 去識別化 — 蒐集的資料本身就是風險資產"
weight: 7
tags: ["monitoring", "security", "privacy", "redaction", "gdpr"]
---

回答「蒐集的資料本身就是風險資產，怎麼保護」。三層防護：SDK 端 redaction → transport 加密 → collector access control。

## 章節

- [SDK Redaction API 設計](/monitoring/07-security-privacy/sdk-redaction-api/) — 預設 redaction rule 與自訂 pattern 的 API 設計
- [Transport 安全](/monitoring/07-security-privacy/transport-security/) — HTTPS、basic auth、同區網也要加密的理由
- [Collector Access Control 實作](/monitoring/07-security-privacy/collector-access-control/) — 認證 / 授權 / access log 的 Collector 端實作
- [去識別化策略](/monitoring/07-security-privacy/anonymization-strategy/) — IP 截斷、user agent 簡化、stack trace 路徑清理、session UUID
- [GDPR 最小化原則的工程落地](/monitoring/07-security-privacy/gdpr-minimization/) — GDPR 最小化原則在監控系統的工程落地
- [監控資料洩漏的 Threat Model](/monitoring/07-security-privacy/monitoring-data-threat-model/) — 監控資料洩漏的威脅模型與緩解策略
- [Client-side SDK 認證的根本限制](/monitoring/07-security-privacy/client-sdk-authentication/) — credential 必然暴露的根本限制與多層緩解策略

## 跨分類引用

- → [backend 07 資安](/backend/07-security-data-protection/)：server-side 的 secret management 跟本模組的 redaction 互補
- ← [ux-design 模組三 輸入機制](/ux-design/03-input-mechanism/)：IME 個人化學習 = secret 洩漏
- ← [testing 模組二 客戶端可觀測性](/testing/02-client-observability/)：log 內容可能含 secret，需要 redaction
- → [monitoring 模組八](/monitoring/08-business-analytics/)：去識別化是商業利用的入場條件
- 待建連結 → `compliance/`（隱私法規教學分類）
