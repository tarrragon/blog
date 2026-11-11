---
title: "Circuit Breaker"
date: 2026-04-23
description: "說明下游持續失敗時如何暫停呼叫並保護系統"
weight: 30
---

Circuit breaker 的核心概念是「下游持續失敗時，暫時停止呼叫該下游」。它讓 application [fail fast](/backend/knowledge-cards/fail-fast/)、使用 [fallback](/backend/knowledge-cards/fallback/) 或進入 [degradation](/backend/knowledge-cards/degradation/)，降低每個 request 都等待同一個失效依賴的風險。

## 跟其他概念的關係

Circuit breaker 是失敗隔離工具。它通常搭配 [timeout](/backend/knowledge-cards/timeout/)、[retry policy](/backend/knowledge-cards/retry-policy/)、[rate limit](/backend/knowledge-cards/rate-limit/)、fallback 與 [dashboard](/backend/knowledge-cards/dashboard/) 使用；目標是控制故障擴散，而非修復下游。

## 可觀察訊號與例子

系統需要 circuit breaker 的訊號是下游錯誤率高、latency 飆升，並拖慢上游服務。推薦服務持續 timeout 時，商品頁可以短暫停止呼叫推薦，改顯示熱門商品。

## 判斷條件與後果

Circuit breaker 的每一個狀態轉換都靠一個條件觸發，缺了哪一個，它就停在錯的狀態。開啟門檻低於下游錯誤率平常的波動時，下游健康時 breaker 也會反覆開啟，原本會成功的請求被擋下，可用性反而由 breaker 自己拉低；所以門檻要對照 [metrics](/backend/knowledge-cards/metrics/) 上下游平常的錯誤率來定。沒有半開探測與恢復條件時，breaker 開啟之後無從得知下游是否恢復，只能等固定時間後全部放行，下游若還沒恢復，就同時收到全部被擋下的請求。fallback 行為沒有定義時，breaker 開啟後上游拿到的是錯誤而不是降級的結果；沒有 [alert](/backend/knowledge-cards/alert/) 時，breaker 開著的期間功能已經降級，而沒有任何通知。
