---
title: "Fail Fast"
date: 2026-04-23
description: "說明已知無法完成時快速回應如何保護資源與上游判斷"
weight: 58
---

Fail fast 的核心概念是「已知當前操作無法成功時，快速回應明確失敗」。它讓上游不用等待到 timeout，也讓系統保留資源給仍可能成功的工作。 可先對照 [Failover](/backend/knowledge-cards/failover/)。

## 跟其他概念的關係

Fail fast 常和 circuit breaker、validation、dependency health、rate limit 與 load shedding 搭配。它把已知會失敗的等待轉成可分類錯誤，讓上游可以選擇 fallback、重試或停止流程。 可先對照 [Failover](/backend/knowledge-cards/failover/)。

## 可觀察訊號與例子

系統需要 fail fast 的訊號是下游已知中斷，但上游仍持續等待。若 payment provider 已進入 circuit open，checkout 可以立即回應「付款暫停」或保留訂單，讓 request 快速進入明確結果。

## 判斷條件與後果

Fail fast 回應的錯誤分得出種類時，上游才選得了下一步。validation failure、dependency unavailable、quota exceeded 與 circuit open 混成同一個錯誤碼時，上游分不出這次失敗重試是否會成功：validation failure 重試幾次都一樣，circuit open 等一段時間之後可能恢復，quota exceeded 要等額度重置。上游只能一律重試或一律放棄；一律重試對已知中斷的下游持續施壓，一律放棄則丟掉了稍後就能成功的請求。對外的回應帶著內部的依賴名稱或錯誤細節時，呼叫端拿得到服務內部結構的資訊，所以對外回應只寫使用者可以採取的結果（付款暫停、訂單已保留）。
