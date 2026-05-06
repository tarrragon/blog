---
title: "Hot Key"
date: 2026-04-23
description: "說明單一 key 承受大量讀寫時如何形成容量瓶頸"
weight: 21
---


Hot key 的核心概念是「少數 key 承受遠高於平均值的流量」。快取、資料庫、broker partition、rate limit counter 與排行榜都可能因 hot key 形成單點瓶頸。 可先對照 [HTTP Client](/backend/knowledge-cards/http-client/)。

## 概念位置

Hot key 是流量分布問題。總 QPS 看起來可承受時，單一商品、直播間、明星帳號、熱門活動或全域 counter 仍可能把某個 shard、partition 或 Redis node 打滿。 可先對照 [HTTP Client](/backend/knowledge-cards/http-client/)。

## 可觀察訊號與例子

系統需要 hot key 分析的訊號是整體容量尚可，但特定頁面、特定商品或特定 tenant 延遲異常。大型促銷活動中，熱門商品庫存 key 可能比其他商品多出數百倍讀寫。

## 設計責任

Hot key 設計要考慮分片、local cache、讀寫分離、批次更新、限流與降級。觀測上要能按 key pattern、tenant、topic 或 partition 看流量集中度。
