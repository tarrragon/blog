---
title: "Heuristic Freshness（啟發式新鮮度期限）"
date: 2026-10-02
description: "回應沒寫任何快取期限卻仍被瀏覽器或 CDN 保存、改了內容使用者卻還拿到舊版時，查快取自己估期限的規則"
weight: 446
tags: ["backend", "http-caching", "freshness", "knowledge-card"]
---

回應寫了 `max-age`、`s-maxage` 或 `Expires` 時，快取依回應寫的期限使用它；三者都沒有時，規範允許快取對特定狀態碼的回應、以及用 `public` 這類指令明確標成可快取的回應**自己估一個期限**，這個估出來的期限稱為啟發式新鮮度期限（heuristic freshness lifetime，RFC 9111 §4.2.2）。它是 [TTL](/backend/knowledge-cards/ttl/) 由快取而不是由 origin 決定的情形，也是 [Cache-Control](/backend/knowledge-cards/cache-control/) 沒寫期限時的預設行為。

## 概念位置

啟發式期限在新鮮度期限取用順序的最後一個位置：`s-maxage`（只限共用快取）、`max-age`、`Expires` 都沒有時才輪到它。能被這樣估算的狀態碼由 RFC 9110 §15.1 列出，包括 200、203、204、206、300、301、308、404、405、410、414 與 501；302 與 307 不在其中，沒有快取標頭時規範不允許保存。估算方式規範只給建議：有 `Last-Modified` 時，取 `Last-Modified` 與回應產生時間之間間隔的一個比例，常見的比例是這段間隔的 10%。估出來的期限過了之後，副本照一般規則先驗證才能再用，或在 [Stale-While-Revalidate](/backend/knowledge-cards/stale-while-revalidate/) 這類指令允許的窗口內先給舊版。

## 可觀察訊號與例子

各實作的估法差異很大，而且只能從原始碼或實測得知。以 2026-10 的實測與原始碼為例：

- **Chromium**：對沒有快取標頭的 301 與 308 永不過期（300、410 也是），副本還在快取裡時，瀏覽器不再向 origin 送這個網址的請求。
- **Firefox**：取 `Last-Modified` 間隔的 10%，上限一週。
- **Varnish**：不看 `Last-Modified`，直接套用自己的預設存活時間。
- **nginx 的 proxy_cache**：沒有另外設定時不保存。

同一個沒有快取標頭的回應，在這幾個快取上得到從零到永久的不同期限。

典型的後果是改版或改轉址之後，部分使用者一直拿到舊版：靜態檔伺服器替 HTML 自動加了 `Last-Modified` 而沒有 Cache-Control，瀏覽器就用那 10% 的期限直接使用舊頁面。

## 判讀方式

回應的內容會改、或 origin 改了內容之後要在限定的時間內讓所有使用者都拿到新版，就不讓快取自己估：明寫期限（`max-age`），或寫 `no-cache` 讓每次使用前都先確認。判斷一個線上問題是不是出在這裡，先看回應有沒有任何期限指令；沒有的話，期限取決於讀者那一端是哪個瀏覽器、哪個代理，答案要查那個實作的規則。

規範條文、各實作的完整規則與實測紀錄見 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/) 的〈沒有明確期限時的啟發式期限〉與〈各實作的啟發式期限〉；轉址回應上的後果見 [12.8 快取設定的應用：轉址、需登入的 API 回應與個人化頁面](/backend/12-http-caching/applying-cache-headers/)。
