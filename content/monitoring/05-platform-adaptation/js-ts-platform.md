---
title: "JS/TS 平台適配"
date: 2026-06-19
description: "CORS 限制、Service Worker 攔截、SPA 路由變換偵測 — 瀏覽器環境中 SDK 需要處理的平台特殊問題"
weight: 1
tags: ["monitoring", "platform", "javascript", "cors", "service-worker", "spa"]
---

瀏覽器環境中的監控 SDK 面臨三個平台特有的限制：跨域請求被 CORS 攔截、Service Worker 可以攔截和修改請求、SPA 的路由變換不觸發頁面載入事件。每個限制需要 SDK 在設計層面做適配。

## CORS 限制

瀏覽器的同源政策限制網頁向不同 origin 發送請求。SDK 的 HTTP POST 送到 collector endpoint 時，如果 collector 和網頁不在同一個 origin（protocol + domain + port 都相同），瀏覽器會先發送 preflight OPTIONS 請求確認 server 允許跨域存取。

SDK 端的適配：

使用 `navigator.sendBeacon(url, data)` 代替 `fetch` / `XMLHttpRequest`。sendBeacon 不受 CORS 限制（瀏覽器對 beacon 請求不做 preflight），且在頁面 unload 時仍能可靠送出 — 適合 close flush 場景。

sendBeacon 的限制：payload 大小有上限（通常 64KB），不能自訂 Content-Type header（固定為 `text/plain` 或 `application/x-www-form-urlencoded`），沒有回應 — 送出後無法知道 server 是否收到。

如果需要 fetch（例如需要讀取回應或送出大 payload），collector 端需要設定 CORS header：`Access-Control-Allow-Origin`、`Access-Control-Allow-Methods: POST`、`Access-Control-Allow-Headers: Content-Type`。

## Service Worker 攔截

Service Worker 可以攔截頁面發出的所有 HTTP 請求（包括 SDK 的 POST 請求到 collector）。如果應用程式的 Service Worker 有 cache 策略（cache-first、network-first），SDK 的監控請求可能被快取而非送到 collector。

SDK 端的適配：

在 fetch 請求中加 `cache: 'no-store'` 防止 Service Worker 快取監控請求。或在請求 URL 加唯一的 query parameter（`?_t=timestamp`）讓每次請求的 URL 都不同，繞過 cache 比對。

如果 SDK 本身提供 Service Worker 模組（在 Service Worker 內攔截 error），需要注意 Service Worker 的生命週期和頁面不同 — Service Worker 可能在頁面關閉後仍在執行，也可能在空閒時被瀏覽器終止。

## SPA 路由變換偵測

Single Page Application 的路由變換（React Router、Vue Router、Angular Router）不觸發頁面重新載入。從監控角度看，使用者在不同「頁面」之間切換，但 `window.onload` 只在首次載入時觸發一次。

SDK 需要偵測 SPA 路由變換來記錄 `lifecycle.view.change` 事件。偵測方式：

`History API` 攔截：monkey-patch `history.pushState` 和 `history.replaceState`，在呼叫前後記錄路由變換。同時監聽 `popstate` 事件處理瀏覽器的上一頁/下一頁。

`MutationObserver`：監聽 DOM 變化偵測頁面內容更新。但 MutationObserver 觸發頻率高，需要 debounce 並搭配 URL 變化檢查，避免把 DOM 微調誤判為路由變換。

框架特定的 hook：如果 SDK 提供框架整合套件（React / Vue / Angular plugin），可以用框架的 router 事件（`useNavigate` hook、`router.afterEach` guard）直接取得路由變換資訊，比 monkey-patch History API 更可靠。

JS/TS 的平台限制理解後，其他平台各有各的挑戰 — [Flutter 平台適配](/monitoring/05-platform-adaptation/flutter-platform/)處理 isolate 和 platform channel 的問題。所有平台共同面對的 [timestamp 一致性](/monitoring/05-platform-adaptation/cross-platform-timestamp/)問題（時區、精度、clock drift）在獨立章節中展開。SDK 的跨平台公開 API 設計見[模組三 SDK 公開 API](/monitoring/03-sdk-design/public-api/)。
