---
title: "Stale-If-Error"
date: 2026-05-27
description: "HTTP cache-control directive、origin 出錯時用舊版頂著、避免使用者看到錯誤"
weight: 30
---

Stale-if-error（SIE）的核心概念是「cache 過期後若 origin 回 5xx 或不可達、用舊版本頂著、避免使用者直接看到錯誤」。是 cache 充當 fallback 的明示授權 — 把 [origin protection](/backend/05-deployment-platform/edge-cdn-static-distribution/) 從「降低 origin 流量」延伸到「origin 故障時保持服務」。跟 [Stale-While-Revalidate](/backend/knowledge-cards/stale-while-revalidate/) 屬不同維度但常一起配置 — SWR 處理過期、SIE 處理錯誤。

## 概念位置

SIE 處於 HTTP cache 失效策略層、是 cache 從「降延遲工具」升級成「fallback 機制」的關鍵 directive。跟 [TTL](/backend/knowledge-cards/ttl/)、[Cache Invalidation](/backend/knowledge-cards/cache-invalidation/) 是兄弟。觸發條件跟 SWR 不同：SWR 是「TTL 過期但 origin 正常」、SIE 是「origin 出錯」— 一個是 condition-driven、一個是 error-driven。

## 可觀察訊號與例子

`Cache-Control: max-age=60, stale-if-error=86400` 的服務行為：origin 正常時、60 秒新鮮、之後正常 revalidate；origin 回 5xx 或網路不可達時、cache 在 86400 秒（1 天）內仍可用舊版本回應。Cloudflare / Fastly / Akamai 支援度因 vendor 而異、部分 vendor 有 origin shield 整合。

電商商品頁、新聞文章、blog post 適合大 SIE window（origin 出事時舊版可用 1-7 天）；交易型 API、付款流程不該用 SIE — 寧可錯誤也不該回 stale。

## 設計責任

開啟 SIE 是明示「在 origin 故障期間、業務願意接受 stale data 換 availability」。要在 freshness-sensitive 場景做白名單而非全域 default。SIE window 通常比 SWR 長（後者是常態、前者是故障 fallback）— 實務上 SIE 設一天、SWR 設十分鐘是常見組合。同時搭配 origin 監控、避免 SIE 遮掉真實事故。
