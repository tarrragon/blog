---
title: "Rolling Update"
date: 2026-04-23
description: "說明逐批替換服務版本的發版策略與風險控制"
weight: 152
---

Rolling update 的核心概念是「逐批替換舊版本實例，維持服務持續可用」。它可降低一次性切換風險。

## 概念位置

常搭配 [readiness](/backend/knowledge-cards/readiness/)、[graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 與 [service discovery](/backend/knowledge-cards/service-discovery/)。

## 設計責任

設計時要定義每批比例、健康檢查門檻、回滾條件與流量切換節奏。
