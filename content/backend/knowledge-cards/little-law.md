---
title: "Little's Law"
date: 2026-05-12
description: "說明系統內並發數、到達率與逗留時間三者的數學關係"
weight: 220
---

Little's Law 的核心概念是「穩態系統內、平均並發 = 到達率 × 平均逗留時間（L = λW）」。三個變數固定兩個就能推第三個、是容量規劃最小的數學工具。可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 概念位置

Little's Law 連接「業務需求」跟「系統參數」。給定預期 RPS（λ）跟 SLO latency 上限（W）、能算出系統最大同時並發數（L）；反過來、給定 connection pool size（L）跟 latency 目標、能算出可支撐的 RPS。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 可觀察訊號與例子

需要用 Little's Law 反推的訊號是「不知道該訂多少 connection pool、thread pool、async worker」。例如：付款 API 預期 1000 RPS、SLO 是 p99 < 200ms、那麼穩態並發 ≈ 1000 × 0.2 = 200、connection pool 至少 200 + headroom。

## 設計責任

Little's Law 只在穩態（steady state）下成立、不適用 burst transient。應用前要確認系統已度過 warmup、流量穩定才有意義。所有 stage（網路、應用、DB）都可獨立套用、用於 latency budget 分解。
