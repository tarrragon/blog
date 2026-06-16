---
title: "Negative Cache"
date: 2026-06-16
description: "說明把「查無此 key」的結果也快取一小段時間，擋掉重複穿透的防護與代價"
weight: 385
---

Negative cache 的核心概念是「把『查無此 key』這個結果也快取一小段時間，讓重複的不存在查詢不再每次都穿透到資料庫」。它是 [cache penetration](/backend/knowledge-cards/cache-penetration/) 的主要防護工具。 可先對照 [Cache Penetration](/backend/knowledge-cards/cache-penetration/)。

## 概念位置

Negative cache 是 [cache penetration](/backend/knowledge-cards/cache-penetration/) 防護的主工具，與 [cache hit / miss](/backend/knowledge-cards/cache-hit-miss/) 的差別是它快取的是「miss 這個結果」而非資料本身。它跟一般快取共用 [TTL](/backend/knowledge-cards/ttl/) 機制，但 TTL 策略相反：要短到避免遮擋真實資料、又長到擋住重複穿透。 可先對照 [Cache Penetration](/backend/knowledge-cards/cache-penetration/)。

## 可觀察訊號與例子

需要 negative cache 的訊號是「大量重複查詢同一批不存在的 key、回源被無謂打爆」。把「查無此商品」用很短的 TTL 快取，第二次以後的相同查詢直接命中 negative 項、不再打資料庫。

## 設計責任

negative cache 自身有代價：真實資料建立後要等 negative 項過期才會被命中，TTL 太長會讓新上架資料短暫不可見。設計時 TTL 要明顯短於正常資料的快取週期，並在資料寫入路徑主動失效對應的 negative 項，避免新資料被「查無」結果遮擋。
