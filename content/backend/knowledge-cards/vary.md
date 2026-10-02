---
title: "Vary（快取鍵變體標頭）"
date: 2026-10-02
description: "同一個網址會依請求標頭回不同內容、或快取命中率異常低時，查這個回應標頭怎麼把請求標頭加進快取鍵"
weight: 445
tags: ["backend", "http-caching", "vary", "cache-key", "knowledge-card"]
---

快取找保存的回應時，規範要求至少比對請求方法與網址；同一個網址會因為某個請求標頭回出不同內容時（例如依 `Accept-Encoding` 回 gzip 或 br 壓縮的版本），origin 在回應上寫 `Vary: <標頭名稱>`，快取就把那個請求標頭的值也加進比對條件，不同的值各存一份、各自重用。它是 [Cache-Control](/backend/knowledge-cards/cache-control/) 以外，回應影響「誰拿到哪一份保存內容」的另一個標頭。

## 概念位置

Vary 屬於快取鍵這一層：Cache-Control 決定一份回應能不能保存、能用多久，Vary 決定保存的這一份可以拿去回應哪些請求。它與 [Cache Hit Rate](/backend/knowledge-cards/cache-hit-rate/) 直接相關，列進去的標頭值越分散，同一個網址就被切成越多份，每一份被重用的機會越少。`Vary: *` 讓比對永遠失敗，這份回應每次被重用前都要先向 origin 驗證。

## 可觀察訊號與例子

`Vary: Accept-Encoding` 是最常見的用法。規範只允許快取在比對前做去掉空白這類不改變語意的正規化，所以 `gzip`、`br`、`gzip, deflate, br` 三種寫法照字面會被當成三種值；實作可以自己再正規化（例如 Varnish 預設把它收斂成同一份），各產品的做法不同。

`Vary: Cookie` 是另一端：Cookie 的值幾乎每個使用者都不同，共用快取存下的份數接近使用者數，命中率接近零。個人化回應的建議做法是寫 `Cache-Control: private` 讓共用快取不保存，而不是用 `Vary: Cookie`。

## 判讀方式

看到一個回應帶 Vary，先問列出的標頭在實際流量裡有幾種值：值少而且有意義（壓縮方式、語系）時 Vary 讓不同版本安全地共用快取；值幾乎一人一種（Cookie、未經正規化的完整 `User-Agent` 字串）時它實質上關掉了共用快取，要改用 `private` 或在快取前先把標頭正規化成少數幾種值。

`Authorization` 不必列進 Vary：規範已經禁止共用快取把帶 `Authorization` 請求的回應拿去回應別人，除非回應用 `public` 這類指令明確允許。這是規範的要求，實作不一定遵守（實測預設設定的 nginx 1.27 會共用），需登入的回應仍由 origin 明寫 `private` 或 `no-store`。反過來，自訂的請求標頭（例如以標頭指定 API 版本）沒有列進 Vary 時，快取會把一個版本的回應發給要另一個版本的請求。

規範的比對規則、Varnish 與 nginx 的實測差異，以及 Cookie、Authorization 在共用快取上的處理，見 [12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/)。
