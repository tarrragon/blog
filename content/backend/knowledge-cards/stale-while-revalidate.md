---
title: "Stale-While-Revalidate"
date: 2026-05-27
description: "HTTP cache-control directive，cache 過期後仍立即回舊版、背景發出 origin request 拉取新版本更新快取"
weight: 29
---

Stale-while-revalidate（SWR）的核心概念是「[TTL](/backend/knowledge-cards/ttl/) 過期後仍可立即回舊版本給使用者、同時背景發出 origin request 拉取新版本更新快取」。使用者體驗永遠快、新鮮度有「最多 stale `max-age + swr`」秒的上限。是天然的 [cache stampede](/backend/knowledge-cards/cache-stampede/) 緩解機制 — 把「TTL 過期那一刻 N 個請求同時打 origin」變成「TTL 過期那一刻 1 個請求打 origin、其他 N-1 個拿舊版」。

## 概念位置

SWR 處於 HTTP cache 失效策略層、跟 [TTL](/backend/knowledge-cards/ttl/)、[Cache Invalidation](/backend/knowledge-cards/cache-invalidation/) 是兄弟概念。TTL 定義「何時 expire」、SWR 定義「expire 之後仍允許用舊版的時間窗口」、cache invalidation 定義「主動清掉」。跟 [Stale-If-Error](/backend/knowledge-cards/stale-if-error/) 屬不同維度但常一起配置 — SWR 處理過期、SIE 處理錯誤。

## 可觀察訊號與例子

`Cache-Control: max-age=60, stale-while-revalidate=600` 的服務行為：60 秒內 cache 完全新鮮、60-660 秒之間 client 仍立即拿到舊版（但 cache 已背景重整）、660 秒後才強制等 origin response。Cloudflare / Fastly / Varnish 都支援、瀏覽器 cache 也尊重這個 directive。

新鮮度敏感的場景（庫存、價格、權限）不該全域開 SWR、會放大 stale 風險；blog 文章、商品描述、靜態 metadata 適合 SWR 降低 origin 壓力。

## 設計責任

選擇 SWR window 要在「origin 壓力」跟「freshness budget」間取捨。Window 越長、origin 壓力越低、stale 容忍度越高；window 越短、freshness 越接近 TTL、但 cache stampede 緩解效果下降。常見組合是 `stale-while-revalidate` 設成 `max-age` 的 5-10 倍。要在資料新鮮度敏感場景做白名單而非全域 default。
