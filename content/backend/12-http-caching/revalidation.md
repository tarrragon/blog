---
title: "12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store"
slug: "revalidation"
date: 2026-10-02
description: "副本過期之後快取怎麼向 origin 確認它是否仍然有效：ETag 與 Last-Modified 兩種驗證子、條件請求與 304 回應、no-cache、no-store 與 must-revalidate 的語意差別，以及共用快取實作在驗證上的預設行為"
weight: 3
tags: ["backend", "http-caching", "cache-control", "etag", "conditional-request"]
---

這篇整理一份副本過期之後，快取怎麼向 origin 確認它還能不能用。新鮮度期限怎麼算見 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)；在某些條件下不驗證就直接給出過期副本，是 [12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/) 的範圍。

副本過期之後仍可以繼續使用，條件是先向 origin 確認：快取帶著副本的版本識別去問 origin，如果 origin 端的內容沒變，origin 只回一個沒有內容的 304，快取更新副本的標頭後繼續使用原本的內容。規範把這個過程稱為**驗證**（validating 或 revalidating，RFC 9111 §4.3）。驗證省下的是傳輸內容的頻寬與 origin 產生內容的成本，請求本身仍然要送到 origin。

## 驗證子：ETag 與 Last-Modified

拿來比對版本的值稱為**驗證子**（validator），有兩種：

- **`ETag`**：origin 替內容的每個版本給的識別字串，例如 `ETag: "v1"`。內容改變時 ETag 跟著改變。
- **`Last-Modified`**：內容最後修改的時間，例如 `Last-Modified: Mon, 01 Jan 2024 00:00:00 GMT`。

`ETag` 分強弱兩種。**強驗證子**在內容的任何位元改變時都會改變；做不到這一點的（例如只在語意有變時才換值），origin 必須在值前面加 `W/` 標成弱驗證子，例如 `ETag: W/"v1"`（RFC 9110 §8.8.1、§8.8.3）。驗證快取副本時用的是弱比較，所以強弱 ETag 都能用來驗證（RFC 9110 §13.1.2）；強弱的差別影響的是分段請求（Range）這類需要逐位元一致的場合。

`Last-Modified` 的時間解析度只到秒。同一秒內改了兩次的內容，`Last-Modified` 分不出來，這時要靠 `ETag`（RFC 9110 §8.8.3）。origin 通常兩種都送，規範也要求快取送出驗證請求時，副本有 `ETag` 就必須放進請求，有 `Last-Modified` 通常也要放（RFC 9111 §4.3.1）。

## 條件請求與 304 回應

快取驗證時送出的是**條件請求**：在請求裡附上副本的驗證子，問 origin「這個版本還是最新的嗎」。

```text
GET /res.js HTTP/1.1
If-None-Match: "v1"
If-Modified-Since: Mon, 01 Jan 2024 00:00:00 GMT
```

- `If-None-Match` 帶副本的 `ETag`。origin 端目前的 ETag 與它相符（弱比較），代表內容沒變。
- `If-Modified-Since` 帶副本的 `Last-Modified`。origin 端內容的修改時間早於或等於這個時間，代表內容沒變。
- 兩個都有時，origin 只看 `If-None-Match`，忽略 `If-Modified-Since`（RFC 9110 §13.1.3）。

內容沒變時，origin 對 GET 與 HEAD 回 **304 Not Modified**；內容變了就回 200 與新內容（RFC 9110 §13.1.2）。304 沒有內容，但必須帶上 200 回應會帶的 `Cache-Control`、`Expires`、`ETag`、`Date`、`Vary` 等標頭（RFC 9110 §15.4.5）。快取收到 304 之後，用這些標頭更新副本，副本因此重新變新鮮，新的期限照 304 帶來的 `Cache-Control` 計算（RFC 9111 §4.3.3、§4.3.4）。

所以 origin 修改一個網址回應的 `Cache-Control` 時，不必等快取把副本丟掉：下一次驗證時 origin 回的 304 帶著新的 `Cache-Control`，快取把副本標頭裡的指令換成新的，內容仍沿用原本那一份。

驗證時 origin 回 5xx，快取可以把錯誤轉給客戶端，也可以當成 origin 沒有回應（RFC 9111 §4.3.3）；當成沒有回應時，快取能在 [12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/) 說明的條件下延用過期副本。

## 過期副本在驗證前的處理

規範的預設是過期副本不能直接給出：

> A cache MUST NOT generate a stale response unless it is disconnected or doing so is explicitly permitted by the client or origin server（RFC 9111 §4.2.4）

也就是只有兩種情形可以給出過期副本：快取連不上 origin，或 origin 與客戶端用指令明確允許（例如 `stale-while-revalidate`）。有些指令連這兩種情形也一併禁止：`no-cache` 與 `must-revalidate`（語意見下方〈no-cache、no-store 與 must-revalidate 的語意〉），以及只對共用快取有效的 `proxy-revalidate` 與 `s-maxage`（[12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)）。

## no-cache、no-store 與 must-revalidate 的語意

這三個回應指令在保存、新鮮期間內（副本目前年齡小於新鮮度期限的那段時間）的使用、過期後與連不上 origin 時各有規定：

| 指令              | 能不能保存 | 新鮮期間內能不能直接使用     | 過期後                 | 連不上 origin 時                     |
| ----------------- | ---------- | ---------------------------- | ---------------------- | ------------------------------------ |
| `no-store`        | 不能       | 不適用（沒有副本）           | 不適用（沒有副本）     | 不適用（沒有副本）                   |
| `no-cache`        | 能         | 不能，每次使用前都要驗證成功 | 每次使用前都要驗證成功 | 不能給出副本                         |
| `must-revalidate` | 能         | 能                           | 必須驗證成功才能使用   | 回錯誤（建議 504），不能給出過期副本 |
| 只有 `max-age`    | 能         | 能                           | 驗證後使用             | 可以給出過期副本                     |

規範原文：

- `no-cache`：「the response MUST NOT be used to satisfy any other request without forwarding it for validation and receiving a successful response」（RFC 9111 §5.2.2.4）。`no-cache` 的回應可以保存，每次使用前都要驗證成功；名稱裡的「cache」指的是不經驗證就直接使用。
- `no-store`：「a cache MUST NOT store any part of either the immediate request or the response」（RFC 9111 §5.2.2.5）。它是唯一禁止所有快取保存的指令（`private` 只禁止共用快取保存）。規範同一節也寫明它不是可靠的隱私保證（「not a reliable or sufficient mechanism for ensuring privacy」）。另外，MDN 註明一個回應帶 `no-store`，不會刪掉快取裡同一個網址先前存下的副本。
- `must-revalidate`：新鮮期間內照常使用，過期之後一定要驗證；連不上 origin 時要回錯誤，不能拿過期副本頂替（RFC 9111 §5.2.2.2）。規範對它的用途說得很具體：「if and only if failure to validate a request could cause incorrect operation, such as a silently unexecuted financial transaction」。

選擇的依據是兩個問題。第一，內容能不能留在任何快取裡，包括使用者自己的裝置：不能就是 `no-store`；只是不能讓別人拿到，用 `private` 就夠了（[12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/)），`no-store` 會連帶失去瀏覽器保存與條件請求省下的傳輸頻寬。第二，拿到舊內容的後果有多嚴重：每次都要確認是最新就是 `no-cache`；新鮮期間內可以接受、過期後即使連不上 origin 也不能拿舊內容頂替，就是 `must-revalidate`。

## 共用快取實作的驗證預設

快取向 origin 送條件請求這一步，在實測的情境（`no-cache` 的回應，以及 Varnish 寬限時間過後、nginx 過期後的請求）裡，Varnish 7.7 與 nginx 1.27 預設設定下都沒有發生：

- **`no-cache` 回應**：兩者預設都不保存。規範允許保存 `no-cache` 回應，Varnish 自己的期限計算也判定可以保存；讓 Varnish 不保存的是內建設定（builtin VCL，VCL 是 Varnish 的設定語言）裡一條在回應沒有 `Surrogate-Control` 時，把 `no-cache|no-store|private` 一律標成不可快取的規則。結果是 Varnish 與 nginx 把每個請求都以一般的 GET 轉給 origin，不是條件請求，origin 每次都回完整的 200。
- **有 `max-age` 的回應過期之後**：Varnish 預設在一段寬限時間（參數 `default_grace`）內先給出過期副本，同時在背景向 origin 抓新的（見 [12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/)）；依 Varnish 7.7 的原始碼，副本是帶 `ETag` 或 `Last-Modified` 的 200 回應、內容不是空的時，這次背景抓取會送條件請求（這一點只有原始碼依據，實測沒有在寬限時間內送出請求）。寬限時間也過了之後，副本只在保留時間（參數 `default_keep`，預設 0）內留著供條件請求使用；預設設定下副本已經丟掉，實測在這個時間點的請求，Varnish 送給 origin 的是一般的 GET。nginx 預設不打開 `proxy_cache_revalidate`，過期後同步向 origin 送一般的 GET。把 Varnish 的 keep 設成大於 0（實測同時把 grace 設為 0、keep 設為 60 秒）、或打開 nginx 的 `proxy_cache_revalidate` 之後，Varnish 寬限時間過後的請求、以及 nginx 過期後的請求才改送帶 `If-None-Match` 與 `If-Modified-Since` 的條件請求，origin 回 304，快取繼續使用原本的內容。
- **客戶端自己送條件請求、而快取裡的副本還新鮮**：兩者都直接回 304 給客戶端，不轉送到 origin。這是規範允許的行為。

這代表 origin 端設定好 `ETag` 與 `no-cache`，不保證共用快取會照規範去驗證。origin 有多台伺服器時，同一份內容在每一台算出的 `ETag` 也要相同，否則條件請求落到另一台就比對不上，只能回完整的 200。要讓驗證在共用快取上發生，要另外查手上那個快取的設定：Varnish 的 keep 與內建設定的覆寫方式，nginx 的 `proxy_cache_revalidate`，CDN 則查各家文件裡「revalidation」或「conditional request」相關的說明。

瀏覽器上的驗證什麼時候發生，跟使用者是重新整理、強制重新整理還是一般瀏覽有關，見 [12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/)。
