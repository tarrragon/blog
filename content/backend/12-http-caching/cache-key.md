---
title: "12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization"
slug: "cache-key"
date: 2026-10-02
description: "快取用什麼條件挑出一份副本回應請求：快取鍵的組成、Vary 如何把請求標頭加進快取鍵、帶 Authorization 的請求在共用快取的規則、Cookie 與 Set-Cookie 在規範與實作上的處理，個人化回應的標頭選擇，以及沒有列進快取鍵的輸入造成的快取投毒與快取規則造成的 web cache deception"
weight: 4
tags: ["backend", "http-caching", "cache-control", "vary", "security"]
---

這篇整理快取收到一個請求時，怎麼決定要拿哪一份保存的副本回應它，或判定沒有可用的副本。這個判斷決定了一份副本會被哪些人拿到，所以也是個人化內容外洩到別人手上的成因所在。保存位置的分類見 [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)。本篇談的外洩發生在共用快取上：同一份副本被發給不同使用者。另一種「看到別人的畫面」發生在同一台裝置上，前一個使用者的頁面在按上一頁時被瀏覽器的 back/forward cache 還原，見 [12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/) 的〈上一頁與 back/forward cache〉。

## 快取鍵的組成

快取用來挑選副本的資訊稱為**快取鍵**（cache key）。規範定義的最小組成是請求方法加上目標網址：

> The "cache key" is the information a cache uses to choose a response and is composed from, at a minimum, the request method and target URI（RFC 9111 §2）

規範也指出，許多常用的快取只保存 GET 的回應，所以只用網址當快取鍵。網址包含查詢字串，`/products?id=1` 與 `/products?id=1&utm_source=mail` 是兩個不同的快取鍵，各自保存一份副本。行銷追蹤參數這類不影響內容的查詢字串，會讓同一份內容被拆成很多份副本、降低命中率；CDN 通常提供忽略特定參數的設定，名稱與用法查各家文件。

方法方面，規範定義了 GET、HEAD、POST 三種方法的快取語意，而 PUT、DELETE 這類方法的回應不能快取（RFC 9110 §9.2.3、§9.3）。POST 的回應只有在帶明確期限、而且帶一個值和請求網址相同的 `Content-Location` 時才能保存（RFC 9110 §9.3.3）；規範也指出，絕大多數實作只支援 GET 與 HEAD（「the overwhelming majority of cache implementations only support GET and HEAD」，RFC 9110 §9.2.3）。

## Vary 標頭加進快取鍵的請求標頭

同一個網址可能依請求標頭回不同內容：依 `Accept-Encoding` 回 gzip 或 brotli 壓縮的版本，依 `Accept-Language` 回不同語言。origin 用 `Vary` 標頭告訴快取：這個回應的內容跟哪些請求標頭有關，挑副本時這些標頭也要相符。

```text
Vary: Accept-Encoding
```

> In other words, Vary expands the cache key required to match a new request to the stored cache entry.（RFC 9110 §12.5.5）

比對規則有幾個細節（RFC 9111 §4.1）：

- 快取比對新請求與副本當初那個請求在 `Vary` 列出的標頭值時，只允許去掉空白、合併同名標頭這類不改變語意的正規化，其餘要逐字相符。
- 請求沒有帶某個 `Vary` 列出的標頭時，只能和同樣沒有帶這個標頭的副本相符。
- `Vary: *` 永遠不相符，等於這個回應每次被重用前都要先向 origin 驗證。

`Vary` 列出的標頭值越分散，副本就越多。實測時同一個網址回 `Vary: Accept-Encoding`，nginx 1.27 依請求標頭的原始字串分開保存：`gzip`、`br`、`gzip, deflate, br` 與沒帶這個標頭各存一份。Varnish 7.7 在預設設定下會先把 `Accept-Encoding` 正規化、向 origin 一律要 gzip、再自己替客戶端解壓，所以四種請求共用同一份副本。這是實作的處理，不是規範的要求；所用的快取產品怎麼處理 `Vary`，要查它的文件。

## 帶 Authorization 的請求在共用快取的重用規則

請求帶 `Authorization` 標頭，代表回應可能只屬於那個使用者。規範對共用快取的規則是：除非回應用指令明確允許，否則不能把這種回應拿去回應其他請求。

> A shared cache MUST NOT use a cached response to a request with an Authorization header field ... to satisfy any subsequent request unless the response contains a Cache-Control field with a response directive ... that allows it to be stored by a shared cache（RFC 9111 §3.5）

明確允許的指令是 `public`、`s-maxage` 與 `must-revalidate`。所以帶 `Authorization` 的請求，回應只寫 `max-age=60` 時，共用快取不能拿它回應別人；寫成 `public, max-age=60` 時可以，而且可以拿去回應任何請求，包括沒有帶 `Authorization` 的匿名請求：共用快取不替 origin 檢查權限。只對登入者開放、但每個登入者內容都相同的回應，寫 `public` 等於對匿名使用者公開，仍要寫 `private`，或靠 CDN 自己在邊緣驗證身分。`Vary` 不必列 `Authorization`，因為 RFC 9111 §3.5 這條規則已經禁止跨使用者重用（RFC 9110 §12.5.5）。

實測兩個共用快取在 RFC 9111 §3.5 這條規則上的表現完全相反：

- **Varnish 7.7**：只要請求帶 `Authorization`，內建設定就不查快取、直接轉給 origin，連回應寫了 `public` 或 `s-maxage` 也一樣。這比規範保守。
- **nginx 1.27 的 proxy_cache**（預設設定）：使用者甲帶 `Authorization: Bearer t1` 請求一個只寫 `max-age=60` 的路徑，回應被保存下來；接著使用者乙帶 `Bearer t2`、以及完全沒帶 `Authorization` 的請求，都拿到了使用者甲的那份回應。這違反 RFC 9111 §3.5 的規則。

nginx 的行為代表：origin 依靠「請求帶了 `Authorization`，快取就不會共用」這條規則來保護個人資料，在預設設定的 nginx 前面失效。開發與測試時多半只用一個帳號打同一個路徑，拿到的永遠是自己的資料，這種共用因此不容易在上線前被看到。需要登入才能拿到的回應，要在 origin 端明寫 `private` 或 `no-store`，不依賴快取對請求裡 `Authorization` 標頭的判斷。改標頭只約束之後產生的回應；已經存進共用快取的那份副本仍照它當初的標頭運作，到期之前會繼續發給別人，要讓它立刻停止，得在副本所在的快取上清除，CDN 與反向代理的清除方式見 [12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 的〈purge〉。

## Cookie 與 Set-Cookie 在共用快取的處理

以 Cookie 識別使用者的服務，規範沒有對請求的 `Cookie` 標頭訂任何快取規則；它只是一個普通的請求標頭，除非 `Vary: Cookie`，否則不進快取鍵。回應的 `Set-Cookie` 也不會阻止保存：

> Note that the Set-Cookie response header field [COOKIE] does not inhibit caching; a cacheable response with a Set-Cookie header field can be (and often is) used to satisfy subsequent requests to caches.（RFC 9111 §7.3）

規範允許共用快取把一個帶 `Set-Cookie: session=使用者甲的值` 的回應保存下來，再原封不動地回應給使用者乙，原文也寫明這種事常常發生（「can be (and often is)」）；這時使用者乙的瀏覽器就收到了使用者甲的 session。規範在同一段建議 origin 自己用 `Cache-Control` 控制這類回應。

實作多半對帶 `Cookie` 的請求與帶 `Set-Cookie` 的回應加了保護，但做法不同，實測結果：

- **Varnish 7.7**：請求帶 `Cookie` 時內建設定一律不查快取；回應帶 `Set-Cookie` 時內建設定不保存。
- **nginx 1.27**：回應帶 `Set-Cookie` 時預設不保存；請求的 `Cookie` 不影響快取鍵，回應有 `Vary: Cookie` 時才依 Cookie 值分開保存。

這些保護是實作的預設，可以被設定關掉，CDN 的預設也各不相同。

## 個人化回應的標頭選擇

回應的內容因使用者而不同時，標頭層面的做法如下（`private` 那一列成立的前提是回應沒有另外帶 `CDN-Cache-Control` 或 `Surrogate-Control`，或這些欄位裡也寫了 `private`、`no-store`（Varnish 的 `Surrogate-Control` 只認 `no-store`），見 [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/) 的〈把指令指定給特定快取：CDN-Cache-Control〉）：

| 做法                      | 效果                           | 適用情形                                                                  |
| ------------------------- | ------------------------------ | ------------------------------------------------------------------------- |
| `Cache-Control: private`  | 共用快取不保存，瀏覽器可以保存 | 個人化頁面、需登入的 API 回應，允許使用者自己的瀏覽器重複使用             |
| `Cache-Control: no-store` | 任何快取都不保存               | 內容不能留在使用者裝置上（例如共用電腦上的敏感資料）                      |
| `Vary: Cookie`            | 共用快取依 Cookie 值分開保存   | 很少適用：Cookie 值通常每個使用者都不同，副本數接近使用者數，命中率接近零 |

標頭以外還有一種做法：頁面只有一小塊因使用者而不同（例如右上角的使用者名稱）時，把那一塊拆成另一個帶 `private` 的請求，頁面主體就能讓共用快取保存；前提是共用快取不會因為請求帶 Cookie 就跳過快取，Varnish 的內建設定會，要在 VCL 裡移除頁面主體請求的 Cookie。

MDN 的建議與表中 `private` 那一列一致：「you should specify Cache-Control: private instead of specifying a cookie for Vary.」個人化回應寫 `private`，是讓「這份回應能不能給別人」由 origin 決定，而不是交給共用快取的預設設定決定；〈帶 Authorization 的請求在共用快取的重用規則〉與〈Cookie 與 Set-Cookie 在共用快取的處理〉兩節的實測顯示，共用快取的預設在「會不會把回應發給別的使用者」這一點上，不同實作的結果相反。從外部確認某個網址有沒有把一個使用者的回應發給別人，做法在 [12.8 快取設定的應用：轉址、需登入的 API 回應與個人化頁面](/backend/12-http-caching/applying-cache-headers/) 的〈檢查實際送出的快取標頭〉。

## 沒有列進快取鍵的輸入與快取投毒

快取比對請求時只看快取鍵裡的部分。請求裡其他會改變回應內容的部分（某些請求標頭、某些查詢參數），PortSwigger 的研究稱為 unkeyed input，也就是沒有列進快取鍵的輸入。origin 依一個沒有列進快取鍵的輸入產生了不同的回應，而快取把這份回應存下來，在它過期之前，所有快取鍵相同的請求都會拿到它，不論那些請求有沒有帶那個輸入。攻擊者刻意利用這一點，送出帶惡意值的請求、讓有害的回應被存下來發給其他使用者，稱為 web cache poisoning（快取投毒）；James Kettle 在 2018 年 8 月發表於 PortSwigger 的研究〈Practical Web Cache Poisoning〉整理了這類實際案例。

一個常見的形態是框架讀取 `X-Forwarded-Host` 這類代理轉送用的請求標頭，拿它組出頁面裡的絕對網址。請求帶上攻擊者的網域時，回應裡的網址就指向攻擊者的伺服器；這個標頭不在快取鍵裡，被存下來的頁面就發給之後的每個使用者。這和本篇〈Vary 標頭加進快取鍵的請求標頭〉一節講的是同一件事的兩種結果：origin 依某個請求標頭改變回應時，那個標頭列進 `Vary`、或由快取設定加進快取鍵，不同的值就各存一份；沒有列進去，它就是一個沒有列進快取鍵的輸入，一個值產生的回應會被發給帶其他值的請求。

PortSwigger 列的防範裡，和快取鍵直接相關的有下面幾條：

- 網站用不到的請求標頭，在快取或 origin 前停用，不讓框架讀到。這類標頭多半是代理或框架預設支援的，網站本身不需要。
- 為了命中率想把某個輸入排除在快取鍵外時，改成在快取前把請求改寫成正規化的值，讓同一個快取鍵只對應一種回應。
- 不接受帶 body 的 GET 請求，因為 GET 請求的 body 不在快取鍵裡，卻可能被 origin 讀取。

其他還有把快取限縮在純靜態的回應、修補看似無法利用的前端漏洞，見研究原文。

## 快取規則與 web cache deception

web cache deception 和快取投毒是兩種不同的問題，PortSwigger 的文件也明確區分：快取投毒操弄的是快取鍵，讓攻擊者的有害回應被存下來發給別人；web cache deception 利用的是快取規則，讓受害者帶個人資料的回應被存下來，再被攻擊者取走。

CDN 常依副檔名（`.css`、`.js`）或目錄（`/static`）設定快取規則，把符合的網址當成可以保存的靜態檔，而快取與 origin 解析網址路徑的方式可能不同。攻擊者引誘已登入的使用者點一個在快取看來是靜態檔、在 origin 看來是個人頁面的網址，origin 回出帶個人資料的頁面，快取依規則存下它，攻擊者再請求同一個網址就拿到那份副本。這種情形下快取鍵本身沒有問題，出問題的是快取規則覆寫了 origin 對這份回應能不能保存的判斷。PortSwigger 的防範建議：

- 動態回應明寫 `Cache-Control: no-store, private`。
- CDN 的快取規則不覆寫 origin 的 `Cache-Control`。
- 啟用 CDN 比對回應的 `Content-Type` 與網址副檔名是否一致的保護。
- 確認 origin 與快取解析網址路徑的方式一致。

## 瀏覽器快取的分區

瀏覽器上另有一層規範允許的做法：在快取鍵裡加入額外資訊。規範舉的例子是加入發出請求的網站：

> user agent caches might include the referring site's identity, thereby "double keying" the cache to avoid some privacy risks（RFC 9111 §2）

WHATWG Fetch 規範把 HTTP 快取依「頂層網站」分區（Fetch 的 network partition key）：同一個第三方資源，在網站甲與網站乙上被載入時，各存一份，目的是防止網站透過「某個資源是否已經在快取裡」推測使用者造訪過哪些網站。它對 origin 的影響是：跨網站共用的資源（例如公共 CDN 上的函式庫），不能預期因為使用者在別的網站載入過而命中快取。各瀏覽器分區的確切方式查各自的文件。
