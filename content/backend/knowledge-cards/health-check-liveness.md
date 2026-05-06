---
title: "Liveness"
date: 2026-04-23
description: "說明平台如何判斷 process 是否仍然存活，以及何時應重啟"
weight: 31
---


Liveness 的核心概念是「判斷 instance 是否仍能維持基本存活」。平台用這類訊號決定是否重啟 instance；readiness 則決定 instance 是否接收正式流量。 可先對照 [Health Check](/backend/knowledge-cards/health-check/)。

## 概念位置

Liveness 關注 process 是否卡死、主 loop 是否停止、必要 runtime 是否失效。Readiness 關注接流量條件。兩者混用會讓平台在下游短暫故障時重啟正常 instance，造成更大波動。 可先對照 [Health Check](/backend/knowledge-cards/health-check/)。

## 可觀察訊號與例子

系統需要分清 liveness 與 readiness 的訊號是部署或下游波動時 instance 被反覆重啟。資料庫短暫 timeout 應影響 readiness 或功能降級；process deadlock 才應觸發 liveness 失敗。

## 設計責任

Liveness check 要簡單、穩定、成本低。Runbook 應說明 liveness fail 代表什麼、平台何時重啟、重啟後如何觀察 crash loop 與資源限制。
