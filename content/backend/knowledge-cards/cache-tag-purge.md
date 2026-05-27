---
title: "Cache Tag Purge"
date: 2026-05-27
description: "CDN / cache 用 tag / surrogate key 標記資源、批量失效時用 tag 一次清除多個關聯資源"
weight: 358
---

Cache tag purge（也稱 surrogate key purge）是 CDN / cache 的進階失效機制。寫入快取時、除了 cache key 還附加多個 tag；purge 時用 tag 觸發、一次失效所有帶該 tag 的資源、不必逐一指定 cache key。是大型內容系統的事實標準 — 比版本化路徑更通用、比逐個 purge 更可控。跟 [cache invalidation](/backend/knowledge-cards/cache-invalidation/) 是上下層關係：cache invalidation 是「該不該清」、tag purge 是「怎麼批量清」。

## 概念位置

Cache tag purge 處於 CDN / cache 失效策略的「批量失效機制」層、是 [cache invalidation](/backend/knowledge-cards/cache-invalidation/) 的進階實作機制。常見 vendor 實作：

- **Fastly Cache Tag（Surrogate-Key header）**：每個 response 附 `Surrogate-Key: tag1 tag2 tag3`、purge 用 `POST /service/.../purge/<tag>`
- **Cloudflare Cache Tag**（Enterprise plan）：類似機制、用 `Cache-Tag` header
- **Akamai Surrogate Key**：同概念、稱呼 surrogate key
- **Varnish**：用 X-Cache-Tag header + ban-list 機制實作

## 為什麼批量失效需要 tag 而非 wildcard

CDN 用 cache key（通常是 URL + Vary header）做快取存取。批量失效有三條路：

1. **逐個 URL purge**：拿到所有受影響 URL 清單、逐一發 purge — 不知道哪些 URL 帶該資源時做不到
2. **Wildcard purge**：`purge /products/*`、語意粗、容易誤傷
3. **Tag purge**：寫入時就標 tag、失效時用 tag 觸發、精準批量

Tag purge 的優勢是「失效範圍在寫入時就規劃好」、不是事後用 wildcard 猜。

## 使用情境

- **電商商品頁**：商品 page、相關搜尋、推薦 widget 都帶 `product:123` tag；商品下架時 purge `product:123` 一次清乾淨
- **新聞媒體**：文章 + tag page + author page + RSS 都帶 `article:456` tag；文章更新時批量失效相關頁
- **CMS 內容**：模組 / 模板更新時、所有 reference 該模組的頁面用 `template:hero-v2` tag 一次清

## 反模式

- **Tag 太粗**：所有頁面都帶 `site:main` tag、結果每次小更新都全站 purge — 失去 tag 的精準批量優勢
- **Tag 太細**：每個資源獨立 tag、batch purge 需要 enumerate 所有 tag — 退化成逐個 purge
- **跨服務 tag 不同步**：CDN 有 tag、應用層快取沒對應機制、CDN purge 後應用層仍 stale、回填到 CDN
- **不知道 vendor 上限**：Fastly / Cloudflare 對 tag 數量、tag 長度、purge API rate 都有 vendor 上限、要 audit
