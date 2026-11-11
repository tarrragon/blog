---
title: "Cache Tag Purge"
date: 2026-05-27
description: "CDN / cache 用 tag / surrogate key 批量失效多個關聯資源"
weight: 359
---

Cache tag purge（也稱 surrogate key purge）的核心責任是讓 CDN / cache 批量失效操作可控 — 寫入快取時除了 cache key 還附加多個 tag；purge 時用 tag 觸發、一次失效所有帶該 tag 的資源、用單一 tag 取代逐個 cache key 列舉。是大型內容系統的事實標準 — 比版本化路徑通用、比逐個 purge 可控。跟 [cache invalidation](/backend/knowledge-cards/cache-invalidation/) 是執行手段關係（cache invalidation 規定「何時清」、本卡提供「怎麼批量清」）。

## 跟其他概念的關係

Cache tag purge 處於 CDN / cache 失效策略的「批量失效機制」層、是 [cache invalidation](/backend/knowledge-cards/cache-invalidation/) 的執行手段。常見 vendor 實作：Fastly Cache Tag（`Surrogate-Key` header、purge 用 `POST /service/.../purge/<tag>`）、Cloudflare Cache Tag（Enterprise plan、用 `Cache-Tag` header）、Akamai Surrogate Key、Varnish（用 `X-Cache-Tag` header + ban-list）。

CDN 用 cache key（通常是 URL + Vary header）做快取存取。批量失效的三條路是：逐個 URL purge（拿到所有受影響 URL 清單）、wildcard purge（粗、容易誤傷）、tag purge（寫入時就標 tag、失效時用 tag 觸發、精準批量）。tag purge 的優勢是失效範圍在寫入時就規劃好、屬「寫入時規劃」型 invalidation、跟 wildcard 的「事後猜」型對比。

## 可觀察訊號與例子

電商商品頁、相關搜尋、推薦 widget 都帶 `product:123` tag、商品下架時 purge `product:123` 一次清乾淨；新聞文章 + tag page + author page + RSS 都帶 `article:456` tag、文章更新時批量失效相關頁；CMS 模組更新時、所有 reference 該模組的頁面用 `template:hero-v2` tag 一次清。實測大型內容系統一次 tag purge 可影響數萬 cache entry、比逐個 purge 快數量級。

## 判斷條件與後果

Tag 的粒度決定一次 purge 清掉多少資源。tag 太粗時（所有頁面都帶 `site:main` tag），每次小更新都清掉全站快取，每次更新之後回源流量大量湧上；tag 太細時（每個資源一個獨立 tag），批量 purge 要列舉所有 tag，退化成逐個 purge。Vendor 對 tag 數量、tag 長度與 purge API 的呼叫頻率都有上限，粒度設計超過上限時，purge 請求被拒絕，失效沒有發生，所以上線前對照 vendor 的限制核對一次。CDN 有 tag 而應用層快取沒有對應的失效機制時，CDN purge 之後回源讀到應用層的舊值，舊值又回填到 CDN，等於沒有清；所以兩層的失效視為同一條 invalidation pipeline，同一次更新同時清兩層。
