---
title: "Retry Storm"
date: 2026-04-23
description: "說明大量重試如何把局部故障放大成系統壓力"
weight: 48
---

Retry storm 的核心概念是「大量 client 或 worker 在故障期間同時重試，導致下游壓力急速放大」。重試本來用來提高成功率，但在高流量下可能把暫時性故障變成持續過載。 可先對照 [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/)。

## 跟其他概念的關係

Retry storm 是 retry policy、timeout、backoff、jitter 與 rate limit 的共同風險。每一層服務若都自動重試，單一使用者 request 可能變成多倍下游呼叫。 可先對照 [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/)。

## 可觀察訊號與例子

系統需要防止 retry storm 的訊號是下游錯誤率上升後，request 數、連線數與 CPU 同步上升。付款 API 短暫變慢時，所有 checkout instance 同時重試，可能讓付款 API 在原本的流量回到平常之後仍然過載、停在失效狀態，見 [Metastable Failure](/backend/knowledge-cards/metastable-failure/)。

## 判斷條件與後果

Retry storm 從下游變慢開始，經由重試流量疊加在原始流量上而放大。呼叫鏈的每一層都自動重試時，一個使用者 request 到最底層變成多倍的呼叫，下游負載在它變慢的時候成倍增加；所有 instance 用同樣的固定間隔重試時，重試又集中在同一時刻送達。這兩件事讓下游在原始流量回到平常之後仍然過載。重試預算限制重試的總量，backoff 與 jitter 把重試的時間打散，rate limit 與 circuit breaker 在下游失敗時停止送出呼叫，各自截斷放大的一種來源。告警與 runbook 只看總流量時，分不出負載上升來自使用者還是來自重試，所以 runbook 要能看出原始流量與重試流量的比例。
