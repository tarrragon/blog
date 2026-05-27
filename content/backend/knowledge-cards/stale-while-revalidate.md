---
title: "Stale-While-Revalidate / Stale-If-Error"
date: 2026-05-27
description: "說明 HTTP cache-control 兩個 directive 如何讓快取在 origin 不健康時仍能服務、用 freshness budget 換 availability"
weight: 29
---

Stale-while-revalidate（SWR）跟 stale-if-error（SIE）是 HTTP `Cache-Control` 的兩個 directive，定義 cache 在 [TTL](/backend/knowledge-cards/ttl/) 過期後該怎麼處理「舊版內容仍可用」這件事。兩者協作降低 origin 壓力、同時保持使用者感知的 availability。

- **Stale-while-revalidate**：cache 過期後仍可立即回傳舊版本給使用者、同時背景發出 origin request 拉取新版本更新快取。使用者體驗是「永遠快」、新鮮度有「最多 stale `max-age + swr`」秒的上限。
- **Stale-if-error**：cache 過期後若 origin 回 5xx 或不可達、用舊版本頂著、避免使用者直接看到錯誤。是 cache 充當 fallback 的明示授權。

兩個 directive 屬不同維度、可以同時用：

```text
Cache-Control: max-age=60, stale-while-revalidate=600, stale-if-error=86400
```

意思是「正常 60 秒新鮮 → 接下來 10 分鐘背景重整 → origin 死掉時可用 1 天舊版」。新鮮度跟可用性各自有獨立 budget。

使用上的核心邊界：SWR 跟 SIE 都會擴大 stale data 風險、要在資料新鮮度敏感的場景（庫存、價格、權限）做白名單而非全域 default。CDN / browser / API gateway / 應用層快取都可以參與這層協議、各自的支援度跟細節依 vendor 而異（Cloudflare / Fastly / Varnish 各有自己的擴充語意）。

對應到 [Cache Stampede](/backend/knowledge-cards/cache-stampede/) 的關係：SWR 把「TTL 過期那一刻 N 個請求同時打 origin」變成「TTL 過期那一刻 1 個請求打 origin、其他 N-1 個拿舊版」、是天然的 stampede 緩解機制。

## 概念位置

SWR / SIE 處於 HTTP cache 失效策略層、跟 [TTL](/backend/knowledge-cards/ttl/) 跟 [Cache Invalidation](/backend/knowledge-cards/cache-invalidation/) 是兄弟概念。TTL 定義「何時 expire」、SWR / SIE 定義「expire 之後仍允許用舊版的條件」、cache invalidation 定義「主動清掉」。三者一起組成 cache freshness 的完整協議。
