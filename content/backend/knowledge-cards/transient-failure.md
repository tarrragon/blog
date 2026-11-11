---
title: "Transient Failure"
date: 2026-04-23
description: "說明暫時性故障如何影響重試、告警與使用者回應"
weight: 50
---

Transient failure 的核心概念是「短時間內發生、稍後可能自行恢復的故障」。常見來源包含網路抖動、短暫 timeout、下游重啟、連線重建、rate limit 與 leader 切換。 可先對照 [Tripwire](/backend/knowledge-cards/tripwire/)。

## 跟其他概念的關係

暫時性故障適合用 retry、backoff、jitter、timeout 與 fallback 吸收。它和永久性錯誤不同；payload schema 錯、權限拒絕、業務狀態不允許通常需要分類處理，而非持續重試。 可先對照 [Tripwire](/backend/knowledge-cards/tripwire/)。

## 可觀察訊號與例子

系統需要分辨 transient failure 的訊號是錯誤短暫升高後恢復。Redis failover 期間可能出現短暫連線錯誤；consumer 可以退避重試，但要控制重試量避免擴大故障。

## 判斷條件與後果

錯誤的類別決定重試之後它是否會消失。temporary、timeout、rate limited 與 dependency unavailable 這幾類在下游恢復後會消失，自動重試配上 backoff 可以吸收；payload schema 錯、權限拒絕這類 permanent 錯誤每次重試都得到同樣的結果，重試只增加下游負載。沒有分類時，系統只能對全部錯誤一律重試或一律放棄：一律重試在下游故障期間放大流量，一律放棄把短暫抖動變成人工處理的工單。所以 runbook 寫出哪幾類自動重試，哪幾類進 dead-letter 或交人工處理。
