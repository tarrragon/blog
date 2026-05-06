---
title: "ACME Automation"
date: 2026-04-23
description: "說明網站憑證如何透過 ACME 自動簽發與續期"
weight: 146
---


ACME automation 的核心概念是「用標準化協議自動化網站憑證簽發與續期」。它透過 HTTP-01、DNS-01 或 TLS-ALPN-01 驗證網域控制權，減少手動更新憑證的風險。 可先對照 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)。

## 概念位置

ACME 自動化是 [website certificate lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/) 的簽發與續期機制。它通常和 ingress、CDN、load balancer 或 [API Gateway](/backend/knowledge-cards/api-gateway/) 整合，確保多節點部署時維持一致憑證狀態。

## 可觀察訊號與例子

系統需要 ACME 自動化的訊號是站點數量增加、環境增加或憑證更新頻率提高。多網域 SaaS 服務若使用手動續期，憑證遺漏更新的風險會快速上升。

## 設計責任

設計要定義 challenge 類型、失敗重試、續期窗口、憑證分發、失敗 [alert](/backend/knowledge-cards/alert/) 與回復 [runbook](/backend/knowledge-cards/runbook/)。網域與 DNS 權限要和 [least privilege](/backend/knowledge-cards/least-privilege/) 對齊。
