---
title: "Transient Failure"
date: 2026-04-23
description: "說明暫時性故障如何影響重試、告警與使用者回應"
weight: 49
---

Transient failure 的核心概念是「短時間內發生、稍後可能自行恢復的故障」。常見來源包含網路抖動、短暫 timeout、下游重啟、連線重建、rate limit 與 leader 切換。

## 概念位置

暫時性故障適合用 retry、backoff、jitter、timeout 與 fallback 吸收。它和永久性錯誤不同；payload schema 錯、權限拒絕、業務狀態不允許通常需要分類處理，而非持續重試。

## 可觀察訊號與例子

系統需要分辨 transient failure 的訊號是錯誤短暫升高後恢復。Redis failover 期間可能出現短暫連線錯誤；consumer 可以退避重試，但要控制重試量避免擴大故障。

## 設計責任

錯誤分類要標出 temporary、permanent、timeout、rate limited 與 dependency unavailable。Runbook 應說明哪些錯誤可以自動重試，哪些要進入 dead-letter 或人工處理。
