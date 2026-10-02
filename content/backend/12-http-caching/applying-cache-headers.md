---
title: "12.8 快取設定的應用：轉址、需登入的 API 回應與個人化頁面"
slug: "applying-cache-headers"
date: 2026-10-02
description: "把 HTTP 快取的保存位置、新鮮度、驗證、快取鍵與更新規則用在具體回應上：永久與暫時轉址的狀態碼與快取標頭、需登入的 API 回應、個人化頁面、靜態資源與引用它的頁面，以及檢查實際送出的快取標頭的方法"
weight: 8
tags: ["backend", "http-caching", "cache-control", "redirect"]
---

這篇把本模組前面各章的規則用在幾種常見的回應上，逐一說明標頭怎麼選、選擇的依據落在哪一章的哪條規則。每一種回應都從同一組問題出發：這份回應能不能留在使用者的裝置上（[12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/)）、可以給哪些人（[12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/)）、內容會不會改（[12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)）、過期或 origin 出錯時能不能給舊的（[12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/)）、改了之後最慢多久要讓所有人看到（[12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/)）。

## 轉址回應的狀態碼與快取標頭

轉址回應有兩個獨立的設定：**狀態碼**決定轉址的語意，**快取標頭**決定各處快取把這個轉址當作新鮮多久。

狀態碼的語意由 RFC 9110 定義：

| 狀態碼 | 語意     | 重送時方法是否保留         | 沒有快取標頭時能否被啟發式保存 |
| ------ | -------- | -------------------------- | ------------------------------ |
| 301    | 永久移動 | 歷史上可能把 POST 改成 GET | 能                             |
| 308    | 永久移動 | 保留                       | 能                             |
| 302    | 暫時移動 | 歷史上可能把 POST 改成 GET | 規範不允許                     |
| 307    | 暫時移動 | 保留                       | 規範不允許                     |

「永久」與「暫時」的差別在於轉址的對象會不會再變：RFC 9110 對永久轉址的說明是，能編輯連結的客戶端應該把指向原網址的引用改成新網址（RFC 9110 §15.4.2）。快取標頭則決定各處快取直接使用這個轉址多久；回應沒有快取標頭時，301 與 308 落入 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/) 的啟發式期限，在 Chromium 上永不過期。實測時 Chrome 保存了一個沒有快取標頭的 301，之後 origin 改了目的地，Chrome 仍然直接去舊的目的地，沒有向 origin 送出請求；同一個 301 加上 `Cache-Control: max-age=5` 之後，過了 5 秒 Chrome 就回到 origin 取得新的目的地。

轉址回應的快取標頭由兩件事決定：共用快取可不可以保存（加不加 `private`），以及轉址設錯或要改時，願意等多久讓已經存下它的瀏覽器改過來（`max-age` 的長度）。轉址常見的三種情形如下，前兩種依目的地會不會變區分：

- **目的地確定不會再變**（例如 HTTP 轉 HTTPS、網域搬遷後的舊網址；網域送了 HSTS 時，瀏覽器會在本機直接改用 HTTPS、不送出請求，之後要撤回 HTTPS 受的是 HSTS 的期限約束，HSTS 不在本模組範圍）：301 或 308，並明寫一個有限的 `max-age`。期限的長度以「這條轉址設錯時，願意花多久等它在所有瀏覽器上過期」來定：origin 沒有辦法讓所有使用者瀏覽器裡的副本一起失效：[12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 的〈各種更新手段的作用範圍〉裡，作用範圍涵蓋全部使用者瀏覽器的手段只有版本化網址與等待到期，而轉址的網址就是使用者手上的連結、換不掉，剩下的只有等待到期。不寫期限等於把這個時間交給各瀏覽器的啟發式規則。
- **目的地可能會改**（例如可修改目的地的短網址、活動連結）：用 302 或 307 並明寫快取標頭（例如 `Cache-Control: private, max-age=<秒數>` 或 `no-store`），或用 301 並附上 `Cache-Control: private, max-age=<秒數>`。302 與 307 依規範不會被啟發式保存，但部分 CDN 的預設會替沒有快取標頭的轉址套用保存時間（[12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)），所以不論哪個狀態碼都明寫標頭。`private` 讓 CDN 與轉送代理不保存，`<秒數>` 填的是 origin 改了目的地之後，最慢多久要讓已經存下這個轉址的瀏覽器改去新的目的地。2026-10-02 對 bit.ly 與 t.co 的短網址各送一次請求，兩者的回應都是 301 加上 `private` 與很短的 `max-age`。
- **要統計每一次點擊**：同樣用 302、307，或 301 加 `private` 與短 `max-age`；`max-age` 的長度同時決定同一個瀏覽器多久內的重複點擊不會送到 origin、也就不會被計入點擊數。

已經發出、沒有快取標頭的 301，在 Chromium 上永不過期，事後在 origin 補上 `max-age` 傳不到已經存下它的 Chromium 瀏覽器：它們不會再向 origin 送出這個網址的請求。剩下的處置都繞過這個副本：讓舊的目的地網址本身再轉址到新的目的地（前提是舊目的地還在自己手上），或在使用者之後造訪同一個主機的其他網址時，用 `Clear-Site-Data` 清掉，代價是這個主機在那個瀏覽器裡的快取條目會全部清掉（[12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 的〈Clear-Site-Data〉）。

短網址服務的轉址也照這組規則選標頭；短網址特有的取捨（撤回延遲、點擊計數、濫用處理，以及短網址服務保留 301 的理由）見 [0.24 短網址服務的實作](/backend/00-service-selection/url-shortener-implementation/)。

## 需登入的 API 回應的快取標頭

需要登入才能取得的 API 回應，內容只屬於發出請求的使用者。規範對帶 `Authorization` 的請求有保護規則：共用快取不能把回應拿去回應別人，除非回應明確允許（RFC 9111 §3.5）。這條規則在 [12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/) 的實測裡，被預設設定的 nginx 1.27 proxy_cache 違反了：使用者甲的回應被發給了使用者乙與沒有登入的請求。而以 Cookie 識別使用者的服務，規範本來就沒有對應的保護規則。

所以需登入的 API 回應，由 origin 明寫快取標頭，不依賴快取對請求的判斷：

```text
Cache-Control: private, no-cache
ETag: "<驗證子>"
```

- `private`：共用快取不保存，使用者自己的瀏覽器可以保存。前提是回應沒有另外帶 `CDN-Cache-Control` 或 `Surrogate-Control`，或這些欄位裡也寫了 `private`、`no-store`（Varnish 的 `Surrogate-Control` 只認 `no-store`）；實作那些欄位的共用快取會忽略 `Cache-Control` 裡的 `private`（[12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/) 的〈把指令指定給特定快取：CDN-Cache-Control〉）。
- `no-cache`：瀏覽器每次使用前都送條件請求確認；內容沒變時 origin 回 304，省下傳輸內容的成本（[12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/)）。
- `ETag`：給條件請求比對用的驗證子，`<驗證子>` 換成這份內容的版本識別字串，例如內容的雜湊值或資料的更新版本號。

內容不能留在任何快取裡、包括使用者自己的裝置（共用電腦上的醫療或金融資料），改用 `Cache-Control: no-store`，代價是每次都要完整重抓。

## 個人化頁面的快取標頭

個人化的 HTML 頁面（帶使用者名稱的首頁、購物車頁面）和需登入的 API 回應用同一組標頭：`private` 加 `no-cache` 加 `ETag`。兩個額外的風險：

- **回應帶 `Set-Cookie`**：規範不禁止保存帶 `Set-Cookie` 的回應（RFC 9111 §7.3）。一個沒有 `private` 的頁面同時設定了 session Cookie，規範允許共用快取把它連同 Cookie 一起發給下一個使用者。`private` 同時擋住了這個風險。
- **上一頁還原**：瀏覽器的 back/forward cache 不受 `Cache-Control` 約束，登出之後按上一頁仍可能看到登出前的畫面（[12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/)）。這要由網頁程式在 `pageshow` 事件裡檢查 `event.persisted`（為 true 代表頁面是從 back/forward cache 還原的），再重新確認登入狀態，快取標頭處理不了。

## 靜態資源與引用它的頁面的快取標頭

JS、CSS、圖片這類靜態資源，和引用它們的 HTML 頁面要分開設定（[12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 的版本化網址）：

| 回應                                            | 標頭                                                 | 理由                                                                           |
| ----------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------ |
| 版本化網址的靜態資源（`/static/app.3f9a1c.js`） | `Cache-Control: public, max-age=31536000, immutable` | 內容改了就換網址，同一個網址的內容永遠不變，每一層快取都可以在一年內直接使用它 |
| 引用它們的 HTML 頁面                            | `Cache-Control: no-cache` 加 `ETag`                  | 頁面是改版的入口，每次都要確認，使用者才會拿到引用新資源網址的版本             |

靜態資源那一列的 `public` 在多數情形是多餘的（[12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)），寫上它是為了讓意圖明確。`31536000` 是一年的秒數，是常見的取值，不是規範規定的上限。

HTML 頁面那一列放在共用快取後面時有一個代價：實測的 Varnish 與 nginx 預設不保存 `no-cache` 的回應，每個請求都會到 origin（[12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/) 的〈共用快取實作的驗證預設〉）。要讓 CDN 也保存 HTML，用只給 CDN 的期限，例如 `CDN-Cache-Control: max-age=600`，`Cache-Control` 維持 `no-cache`：實作 RFC 9213 的 CDN 依它保存並忽略 `Cache-Control`，其他快取照 `no-cache`（[12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/) 的〈把指令指定給特定快取：CDN-Cache-Control〉）。`s-maxage` 不適合這個用途：它同時作用於清不掉的轉送代理，而且和 `no-cache` 並存時，共用快取每次使用前仍要驗證。改版時再用 purge 清掉 CDN 上的副本（[12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 的〈purge〉）。這組設定還有一個前提：網站沒有用 Service Worker 以快取優先的策略攔截頁面請求，否則 HTML 的 `no-cache` 不會生效。

## 公開且會變動的回應的快取標頭

不分使用者、但內容會變動的回應（文章列表、商品資訊、公開的讀取 API），可以讓每一層快取保存，期限由業務能容忍多久的舊資料決定，例如 `Cache-Control: max-age=<秒數>, stale-while-revalidate=<秒數>, stale-if-error=<秒數>`：`max-age` 是可以直接使用的時間，兩個 stale 窗口讓過期之後與 origin 出錯時仍有內容可給（[12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/)）。舊資料會造成錯誤行為的回應（付款狀態、庫存數字）不加 stale 指令，改用 `no-cache`。

錯誤回應也要明寫標頭：404 屬於可啟發式快取的狀態碼，資源上線前被查過一次，沒有快取標頭的 404 就可能留在快取裡，上線之後仍回 404。實測的 Varnish 會把它保存 `default_ttl` 的時間，Chromium 與 Firefox 的啟發式規則對 404 不保存，CDN 查各家的預設。

## 檢查實際送出的快取標頭

設定寫在 origin 的程式或伺服器設定裡，但使用者實際拿到的標頭，可能被 CDN、反向代理或框架改過。檢查方式是從外部送請求，看回應：

```bash
# 只看標頭：-s 不顯示進度，-I 送 HEAD 請求並印出回應標頭
curl -sI https://<網域>/<路徑>

# 送 GET、只印標頭：-D - 把回應標頭印到標準輸出，-o /dev/null 丟掉內容
curl -s -D - -o /dev/null https://<網域>/<路徑>

# 帶身分送 GET，標頭與內容都印出來，再拿去和不帶身分的結果比對
curl -s -D - -H "Authorization: Bearer <token>" https://<網域>/<路徑>

# 以 Cookie 識別身分的服務，改帶 Cookie
curl -s -D - -H "Cookie: <cookie>" https://<網域>/<路徑>

# 繞過 CDN、直接連 origin，取得 origin 原本送出的標頭，再和上面經過 CDN 的結果比對
curl -sI --resolve <網域>:443:<origin 的 IP> https://<網域>/<路徑>
```

`<網域>/<路徑>` 換成要檢查的網址；`<token>` 換成某個測試帳號登入後拿到的存取權杖，`Bearer` 是權杖類型，服務用的若是別種驗證方式就換成它要的格式；`<cookie>` 填那個測試帳號登入後的 Cookie 值；`<origin 的 IP>` 填 origin 伺服器自己的位址，也就是 CDN 設定裡的回源位址，`--resolve` 讓 curl 把這個網域直接連到那個位址、不經過 CDN。規範要求伺服器對 HEAD 回應的標頭應該（SHOULD）與 GET 相同，但允許省略只有產生內容時才決定的欄位，例如 `Vary`（RFC 9110 §9.3.2），所以檢查 `Vary` 時用送 GET、只印標頭的那條指令。

看回應時注意四件事：

- `Cache-Control` 是不是 origin 設定的那一組，有沒有被中間的 CDN、反向代理或框架改寫或附加。
- 有沒有 `Age`：有就代表這份回應來自某個快取，值是副本的年齡（[12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)）；沒有不代表一定來自 origin（實測的 nginx 1.27 proxy_cache 不送 `Age`）。
- CDN 自己加的命中標頭（名稱各家不同，查各家文件）：看這次是命中快取還是回到 origin。
- 先跑帶身分的那條，讓沿路的快取有機會存下這份回應；在共用快取保存這份回應的期限內（看 `s-maxage`、`max-age`、`Expires`、`CDN-Cache-Control` 或 CDN 設定的保存時間，都沒有就緊接著跑），再跑拿掉 `-H` 的同一條，兩次都連對外的網址（經過 CDN 與反向代理），比對兩份內容。不帶身分卻拿到測試帳號的內容，就是 [12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/) 描述的外洩。兩份內容沒有差異，不能證明沒有外洩：兩次請求可能落在 CDN 的不同節點，要多跑幾次並對照命中標頭。順序顛倒時檢查的是另一件事：快取存下的匿名回應，會不會被發給登入的使用者。
