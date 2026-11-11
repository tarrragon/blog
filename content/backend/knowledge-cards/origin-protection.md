---
title: "Origin Protection"
date: 2026-07-20
description: "快取失效或冷啟動時、miss 流量集中打回正式來源會不會壓垮它——回源保護的手段組合與監控面"
weight: 391
tags: ["backend", "knowledge-card", "cache", "reliability"]
---

Origin protection 的核心責任是避免 cache miss 把壓力集中打回資料庫或下游服務。快取越接近高流量路徑，越要把 miss 當成需要治理的事件，而不是預設「miss 只是少數例外」。它是 [cache stampede](/backend/knowledge-cards/cache-stampede/) 與 [cache penetration](/backend/knowledge-cards/cache-penetration/) 的共同防護目標，兩種現象的成因不同，但都要靠 origin protection 的手段收斂。

## 跟其他概念的關係

Origin protection 守的是快取層與 [source of truth](/backend/knowledge-cards/source-of-truth/) 之間，責任是把「快取失效」跟「回源流量失控」這兩件事解耦。快取原本用來保護資料庫，若熱門資料同時過期或大量查詢命中不存在的 key，快取反而會把大量請求集中送到資料庫——origin protection 就是防止這個反轉發生的整套手段。

## 可觀察訊號與例子

需要加強 origin protection 的訊號是 cache miss rate 突然升高，同時資料庫查詢數、latency 與 timeout 一併上升。常見保護手段有四種，各自對應不同觸發條件：[cache warmup](/backend/knowledge-cards/cache-warmup/) 在流量到來前先建立熱門資料覆蓋；[singleflight](/backend/knowledge-cards/singleflight/)（也稱 request coalescing）讓相同 key 的並發 miss 只留一個請求真正打下游；對回源查詢設 rate limit、timeout 與 fallback；[negative cache](/backend/knowledge-cards/negative-cache/) 把「查無此 key」的結果也快取一小段時間，擋掉 cache penetration 的重複穿透。

## 判斷條件與後果

Origin protection 的判斷對象是 cache miss 發生時，有多少回源請求抵達 [source of truth](/backend/knowledge-cards/source-of-truth/)。命中率整體良好而回源出現尖峰時（熱門 key 同時過期），資料庫的查詢數、latency 與 timeout 一起上升，快取從保護資料庫的元件變成把請求集中送到資料庫的元件；只監控 cache hit rate 的部署看到異常時，回源壓力往往已經持續了一段時間，所以 origin QPS 與 latency 要跟 hit rate 一起看。四種手段各自收斂一種 miss 成因，只用其中一種時其餘成因照樣回源：只有 warmup 時，流量開始後同一個 key 的並發 miss 仍然各自打到下游；只有 singleflight 時，查詢不存在 key 的請求仍然逐一穿透；只有 negative cache 時，熱門資料同時過期照樣造成回源尖峰；rate limit 限制的是前三種手段收斂之後剩下的流量。實際 migration 與 rollout 場景下的回源保護節奏見 [2.9 Cache Migration 與 Stampede Rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)。
