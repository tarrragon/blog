---
title: "Fail Fast"
date: 2026-04-23
description: "說明已知無法完成時快速回應如何保護資源與上游判斷"
weight: 57
---

Fail fast 的核心概念是「已知當前操作無法成功時，快速回應明確失敗」。它讓上游不用等待到 timeout，也讓系統保留資源給仍可能成功的工作。

## 概念位置

Fail fast 常和 circuit breaker、validation、dependency health、rate limit 與 load shedding 搭配。它把已知會失敗的等待轉成可分類錯誤，讓上游可以選擇 fallback、重試或停止流程。

## 可觀察訊號與例子

系統需要 fail fast 的訊號是下游已知中斷，但上游仍持續等待。若 payment provider 已進入 circuit open，checkout 可以立即回應「付款暫停」或保留訂單，讓 request 快速進入明確結果。

## 設計責任

Fail fast 要提供清楚錯誤分類與使用者回應。對內錯誤要能區分 validation failure、dependency unavailable、quota exceeded 與 circuit open；對外回應要避免暴露敏感內部細節。
