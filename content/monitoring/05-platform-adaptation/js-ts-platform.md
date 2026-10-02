---
title: "JS/TS 平台適配"
date: 2026-06-19
description: "CORS 限制、Service Worker 攔截、SPA 路由變換偵測 — 瀏覽器環境中 SDK 需要處理的平台特殊問題"
weight: 1
tags: ["monitoring", "platform", "javascript", "cors", "service-worker", "spa"]
---

瀏覽器環境中的監控 SDK 面臨三個平台特有的限制：跨域請求被 CORS 攔截、Service Worker 可以攔截和修改請求、SPA 的路由變換不觸發頁面載入事件。第一項的成因是瀏覽器預設不讓一個來源讀到另一個來源的回應，機制與它擋的到底是什麼見 [same-origin policy](/backend/knowledge-cards/same-origin-policy/)。每個限制需要 SDK 在設計層面做適配。

## CORS 限制

瀏覽器的同源政策限制網頁讀取不同 origin 的回應；collector 和網頁不在同一個 origin（protocol、domain、port 有任一不同）時，SDK 送出的請求受 CORS 規則約束。跨域請求要不要先送 preflight OPTIONS，由請求的方法與標頭決定：POST 的 Content-Type 是 CORS 安全清單內的值（`text/plain`、`application/x-www-form-urlencoded`、`multipart/form-data`）、而且沒有加自訂標頭時，不送 preflight；Content-Type 是 `application/json` 這類清單外的值時，瀏覽器先送 preflight，collector 回應允許之後才送出正式的請求。

SDK 端有兩種送法：

`navigator.sendBeacon(url, data)` 的用途是頁面進入背景或關閉時仍要送出的資料：Beacon 規範要求瀏覽器在頁面的 `visibilityState` 變成 `hidden` 時立即送出排隊中的 beacon，所以 flush 的程式註冊在 `visibilitychange` 事件上，比註冊在 `unload` 事件上可靠。它的 CORS 行為照上一段的規則：傳入資料的型別是安全清單內的 Content-Type 時以 no-cors 模式送出、不送 preflight；傳入 `application/json` 型別的 Blob 時要先 preflight。beacon 一律帶 credentials（Cookie），所以要 preflight 的那一種情形，collector 的 `Access-Control-Allow-Origin` 要寫出網頁的 origin、不能用 `*`，並回 `Access-Control-Allow-Credentials: true`，否則瀏覽器的 CORS 檢查判定失敗。

sendBeacon 的限制：一律用 POST 送出，不能指定請求方法與其他標頭（Content-Type 由傳入資料的型別決定）；payload 與 fetch 的 keepalive 請求共用同一份在途上限（Fetch 規範定為 64 KiB），超過時 sendBeacon 回傳 false、不送出；沒有回應 — 送出後無法知道 server 是否收到。

`fetch` 用在需要讀取回應、或送出超過 keepalive 上限的大 payload 時。以 JSON 送出時 collector 要回 `Access-Control-Allow-Origin`、`Access-Control-Allow-Methods: POST`、`Access-Control-Allow-Headers: Content-Type`；請求另外帶 Cookie（`credentials: 'include'`）時，`Access-Control-Allow-Origin` 同樣要寫出網頁的 origin，並加 `Access-Control-Allow-Credentials: true`。fetch 加上 `keepalive: true` 也能在頁面關閉時繼續送出，與 sendBeacon 共用 64 KiB 的上限。

## Service Worker 攔截

依 Fetch 規範，頁面送出的 fetch、XHR 與 sendBeacon 請求，都會觸發控制這個頁面的 Service Worker 的 fetch 事件（請求預設的 service-workers mode 是 `all`，Beacon 規範沒有改它）；瀏覽器實作是否對 sendBeacon 這類 keepalive 請求派送事件，以各瀏覽器的文件為準。監控請求在這一層會遇到什麼問題，取決於 SDK 用哪一種請求方法送資料：HTTP 快取與 Service Worker 的 Cache API，規則都按請求方法區分，而方法是由要送的資料形狀決定的。

**GET 像素**：把事件欄位放進網址的查詢參數，用 `new Image().src` 或 GET 請求送出。選它的需求是相容性，以及跨網域不必 preflight（沒有 `crossorigin` 屬性的圖片請求以 no-cors 模式送出），代價是只能帶少量欄位、受網址長度限制。GET 依 HTTP 語意可以被快取（[12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)），同一個網址的事件可能在三個位置被直接回應、沒有送到 collector，三個位置各有自己的處置：

- **瀏覽器的 HTTP 快取與轉送代理**：collector 對這個路徑回 `Cache-Control: no-store`；用 fetch 送時另加 `cache: 'no-store'`，讓瀏覽器的 HTTP 快取不讀也不存（快取模式見 [12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/) 的〈Fetch 規範的快取模式〉）。
- **Service Worker 用 Cache API 存下的回應**：Cache API 不看 `Cache-Control` 標頭，也不看 fetch 的 `cache` 選項，要由 Service Worker 對 collector 的路徑不呼叫 `event.respondWith()`，讓請求照常送往網路。
- **三個位置一起避開**：每次請求帶唯一的查詢參數（例如 `?_t=<時間戳>`），讓網址不同、對不上任何保存的副本。Service Worker 用 `cache.match` 比對時若設了 `ignoreSearch`，查詢參數不參與比對，這個方法在那裡無效。用 `Image` 送時沒有 `cache` 選項可設，唯一的查詢參數是 SDK 端能控制的方法。

**POST**（sendBeacon、fetch、XHR）：把錯誤堆疊、操作紀錄、效能數據這類結構化資料放在請求的 body。選它的需求是資料量與結構，以及頁面關閉時仍要送出。RFC 9110 §9.3.3 寫明 POST 請求不會由快取裡保存的 POST 回應回答（「a POST request cannot be satisfied by a cached POST response」）；Service Worker 規範的 Cache API 也只接受 GET：`cache.put` 對 POST 回傳以 TypeError 拒絕的 promise，`cache.match` 在沒有設 `ignoreMethod` 時對不到任何副本。所以「監控請求被快取、沒有送到 collector」不會發生在這種送法上，`no-store` 與唯一查詢參數對它沒有作用。

POST 的風險在 Service Worker 的程式本身：fetch 事件仍然會收到這個請求。常見的寫法是先 `fetch(event.request)`，再把回應用 `cache.put` 存進快取；遇到 POST 時，put 被拒絕的 promise 若接在 `respondWith()` 的鏈上，頁面拿到網路錯誤，而這時請求通常已經送到 collector，SDK 若因此重送，collector 會收到重複的事件。離線優先的處理程式若在網路失敗時回一個預設的回應，SDK 拿到的是假的成功。處置與 GET 的那一條相同：Service Worker 對非 GET 的請求、或 collector 的路徑不呼叫 `respondWith()`。

兩種送法的差別在於：POST 不需要防快取的處置，GET 除了防快取的處置，也要 Service Worker 放行。檢查時先確認 SDK 實際送出的請求方法：在瀏覽器開發者工具的 Network 面板點開那一筆請求，Headers 分頁的 Request Method 寫著方法。

如果 SDK 本身提供 Service Worker 模組（在 Service Worker 內攔截 error），需要注意 Service Worker 的生命週期和頁面不同 — Service Worker 可能在頁面關閉後仍在執行，也可能在空閒時被瀏覽器終止。

## SPA 路由變換偵測

Single Page Application 的路由變換（React Router、Vue Router、Angular Router）不觸發頁面重新載入。從監控角度看，使用者在不同「頁面」之間切換，但 `window.onload` 只在首次載入時觸發一次。

SDK 需要偵測 SPA 路由變換來記錄 `lifecycle.view.change` 事件。偵測方式：

`History API` 攔截：monkey-patch `history.pushState` 和 `history.replaceState`，在呼叫前後記錄路由變換。同時監聽 `popstate` 事件處理瀏覽器的上一頁/下一頁。

`MutationObserver`：監聽 DOM 變化偵測頁面內容更新。但 MutationObserver 觸發頻率高，需要 debounce 並搭配 URL 變化檢查，避免把 DOM 微調誤判為路由變換。

框架特定的 hook：如果 SDK 提供框架整合套件（React / Vue / Angular plugin），可以用框架的 router 事件（`useNavigate` hook、`router.afterEach` guard）直接取得路由變換資訊，比 monkey-patch History API 更可靠。

JS/TS 的平台限制理解後，其他平台各有各的挑戰 — [Flutter 平台適配](/monitoring/05-platform-adaptation/flutter-platform/)處理 isolate 和 platform channel 的問題。所有平台共同面對的 [timestamp 一致性](/monitoring/05-platform-adaptation/cross-platform-timestamp/)問題（時區、精度、clock drift）在獨立章節中展開。SDK 的跨平台公開 API 設計見[模組三 SDK 公開 API](/monitoring/03-sdk-design/public-api/)。
