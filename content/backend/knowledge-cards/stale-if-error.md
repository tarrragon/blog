---
title: "Stale-If-Error"
date: 2026-05-27
description: "HTTP cache-control directive、origin 出錯時用舊版頂著、確保使用者拿到有效回應"
weight: 31
---

Stale-if-error（SIE）的核心概念是「cache 過期後若 origin 回 5xx 或不可達、用舊版本頂著、確保使用者仍能拿到回應」。是 cache 充當 fallback 的明示授權 — 把 [origin protection](/backend/knowledge-cards/origin-protection/) 從「降低 origin 流量」延伸到「origin 故障時保持服務」。跟 [Stale-While-Revalidate](/backend/knowledge-cards/stale-while-revalidate/) 屬不同維度但常一起配置 — SWR 處理過期、SIE 處理錯誤。

## 概念位置

SIE 處於 HTTP cache 失效策略層、是 cache 從「降延遲工具」升級成「fallback 機制」的關鍵 directive。跟 [TTL](/backend/knowledge-cards/ttl/)、[Cache Invalidation](/backend/knowledge-cards/cache-invalidation/) 是兄弟。觸發條件跟 SWR 不同：SWR 在窗口內不論 origin 狀態都可以先給舊版、同時背景更新；SIE 只在向 origin 驗證遇到錯誤（500、502、503、504 或連不上）時才延用 — 一個是 time-driven、一個是 error-driven。它是 [Cache-Control](/backend/knowledge-cards/cache-control/) 的擴充指令（RFC 5861）：RFC 5861 寫它可以不顧其他新鮮度資訊延用，而 RFC 9111 規定 `s-maxage` 禁止共用快取給出過期副本，兩份規範對這個組合沒有一致的答案；Varnish 7.7 不認得這個指令。規範條文與實作支援差異見 [12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/)。

## 可觀察訊號與例子

`Cache-Control: max-age=60, stale-if-error=86400` 的服務行為：origin 正常時、60 秒新鮮、之後正常 revalidate；origin 回 5xx 或網路不可達時、cache 在 86400 秒（1 天）內仍可用舊版本回應。Cloudflare / Fastly / Akamai 支援度因 vendor 而異、部分 vendor 有 origin shield 整合。

電商商品頁、新聞文章、blog post 適合大 SIE window（origin 出事時舊版可用 1-7 天）；交易型 API、付款流程應該關閉 SIE — 在這類場景中、回 5xx 讓 client retry 比回 stale 安全。

## 設計責任

開啟 SIE 是明示「在 origin 故障期間、業務願意接受 stale data 換 availability」。Freshness-sensitive 場景要走白名單路徑、由 endpoint 個別 opt-in 開啟 SIE。SIE window 通常比 SWR 長（後者是常態、前者是故障 fallback）— 常見組合是 SIE 設一天、SWR 設十分鐘。同時搭配 origin 監控、確保 SIE 期間真實事故仍被察覺。
