---
title: "Retry Budget"
date: 2026-04-23
description: "說明重試次數如何受整體容量與錯誤預算限制"
weight: 58
---

Retry budget 的核心概念是「把重試量限制在系統可承受的預算內」。它承認重試會消耗下游容量，因此重試規則需要納入共享容量與全局保護。

## 概念位置

Retry budget 是 retry storm 的防護工具。它可以用比例、token bucket、error budget、全域配額或每個 client 配額實作，讓重試量和正常流量維持合理比例。

## 可觀察訊號與例子

系統需要 retry budget 的訊號是下游故障時重試流量比正常流量更大。搜尋服務 5% request timeout 時，如果所有 client 重試三次，下游實際壓力可能快速翻倍。

## 設計責任

Retry budget 要定義消耗規則、補充規則、超出預算後的行為與告警。觀測上要分開顯示原始 request、retry request、retry success 與 retry failure。
