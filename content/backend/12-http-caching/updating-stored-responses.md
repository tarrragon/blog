---
title: "12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期"
slug: "updating-stored-responses"
date: 2026-10-02
description: "origin 想改變已經被快取保存的副本時可用的手段：規範定義的失效、CDN 與反向代理提供的 purge、換網址的版本化做法與 immutable、只作用於瀏覽器的 Clear-Site-Data，以及每一種手段能傳到哪幾種快取"
weight: 5
tags: ["backend", "http-caching", "cache-control", "cache-invalidation", "cdn"]
---

這篇整理一份回應已經被各處快取保存之後，origin 要讓它們改用新內容時有哪些手段，以及每一種手段能傳到哪幾種快取。快取的種類與經營者見 [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)。瀏覽器快取與第三方轉送代理沒有管理介面，origin 要改變它們的副本，都要等它們再向 origin 送出請求；簽約的 CDN 與自己經營的反向代理另有清除手段，見下方〈purge〉。

## 規範定義的失效

HTTP 規範裡唯一讓快取主動丟棄副本的機制，綁在不安全的請求方法（規範術語，指會改變伺服器狀態的方法，RFC 9110 §9.2.1）上。快取收到 POST、PUT、DELETE 這類方法的成功回應時，必須讓同一個網址的副本失效：

> A cache MUST invalidate the target URI ... when it receives a non-error status code in response to an unsafe request method（RFC 9111 §4.4）

「失效」是把副本移除，或標成下次使用前必須驗證；「成功回應」指 2xx 與 3xx。回應裡 `Location` 與 `Content-Location` 指到的網址也可以一起失效，但必須和請求的網址屬於同一個來源（scheme、主機名稱與連接埠都相同；RFC 9110 稱為 origin，與本模組其他地方指源站伺服器的 origin 是兩件事）。

這個機制的作用範圍很窄，規範自己寫明了：

> a state-changing request would only invalidate responses in the caches it travels through.（RFC 9111 §4.4）

使用者甲送出一個 PUT 修改商品資料，被失效的只有使用者甲瀏覽器快取裡的副本，以及這個請求經過的那一個 CDN 節點上的副本。使用者乙的瀏覽器、其他 CDN 節點、使用者乙公司的轉送代理，都不會知道這次修改，各自繼續使用手上的副本直到過期。

## purge

**purge** 指 origin 直接要求某個快取刪除指定的副本。HTTP 規範沒有定義 purge 這個操作：RFC 9110 與 RFC 9111 都沒有規定它，IANA 的 HTTP 方法登錄表也沒有 `PURGE` 方法（2026-10-02 查閱）。MDN 對此的描述是：

> There is no way to delete responses on an intermediate server that have been stored with a long max-age.

purge 因此是各個快取產品自己的功能，能用到什麼程度取決於經營者：

- **CDN**：透過 CDN 的管理介面或 API 清除，可以依網址、依前綴或依標籤（tag，見 [Cache Tag Purge](/backend/knowledge-cards/cache-tag-purge/) 卡）清除。依標籤清除的操作模型見 [5.9 邊緣分發與靜態資源](/backend/05-deployment-platform/edge-cdn-static-distribution/) 的〈Tag-based Purge 的操作模型〉。清除傳到所有節點需要時間，傳播時間與 API 呼叫的額度限制查各家文件。
- **自己經營的反向代理**：Varnish 的內建設定把 `PURGE` 當成不認得的方法，直接轉給 origin、不動快取，要在設定檔（VCL）裡自己寫處理規則；實測時寫了 `PURGE`（刪除指定網址的副本）與 `BAN`（依條件一次標記一批副本失效）兩種規則之後，兩者都能讓下一個請求回到 origin。其他產品是否支援、怎麼開啟，查各自的文件。
- **瀏覽器與第三方轉送代理**：沒有 purge 管道。

## 版本化網址與 immutable

既然已存的副本難以刪除，另一種做法是不去改它：內容一改就換一個網址。這個做法也稱 cache busting，最常見的形式是由前端建置工具在打包時，把內容的雜湊值寫進檔名：

```text
/static/app.3f9a1c.js
```

內容改變時雜湊值跟著改變，網址也就跟著改變。新網址是一個新的快取鍵，所有快取都沒有它的副本，第一次請求一定會到 origin；舊網址的副本留在各處，重新載入過的頁面已經不再引用舊網址，這些副本等新鮮度期限過了、或快取空間不夠時自然被丟掉。已經開著的分頁仍可能延遲載入舊網址的程式片段，所以 origin 部署時舊檔要再保留一段時間，否則這些請求一落到沒有副本的快取，就會回到 origin 拿到 404。這個做法對每一層快取都有效，包括瀏覽器與轉送代理，因為它不需要任何快取配合刪除。

代價在引用端：引用這個資源的頁面必須跟著更新網址，而那個頁面本身就不能被長期快取，否則使用者拿到的舊頁面仍然引用舊網址。所以版本化網址要和引用它的頁面一起設定：頁面用短期限或 `no-cache`，頁面引用的靜態資源用版本化網址加長期限。

版本化網址的資源內容永遠不會改變，RFC 8246 為此定義了 `immutable` 指令：

```text
Cache-Control: max-age=31536000, immutable
```

`31536000` 秒是一年，是常見的取值，不是規範規定的上限。

它告訴客戶端，新鮮期間內 origin 不會更新這個資源，客戶端在新鮮期間內不應該（SHOULD NOT）送條件請求確認，使用者按一般的重新整理時也不送（RFC 8246 §2）。幾個限制：使用者強制重新整理時仍然會重新抓取；規範建議客戶端只在 HTTPS 這類經過驗證的連線上採用 `immutable`（RFC 8246 §3）；不認得它的瀏覽器依 RFC 9111 忽略這個指令，照一般的 `max-age` 運作，各瀏覽器的支援情形查各自的文件。重新整理時瀏覽器送出什麼請求，見 [12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/)。

## Clear-Site-Data

`Clear-Site-Data` 是 W3C 的一份規格，讓回應可以要求瀏覽器清除這個網站存在本機的資料，其中 `"cache"` 這個值清的是 HTTP 快取：

```text
Clear-Site-Data: "cache"
```

它有幾個限制，使它無法當成一般的更新手段：

- **只作用在瀏覽器**。MDN 寫明它「has no effect on intermediate caches」，CDN 與轉送代理裡的副本不受影響。
- **要瀏覽器對同一個主機送出請求、並在回應裡收到 `Clear-Site-Data` 才會生效**。清除的範圍是主機名稱相同的整批快取條目，不限於收到標頭的那個網址。一個在 Chromium 上永不過期的 301（見 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)），使用者點它時不會連到 origin，這次點擊本身不會觸發清除；這份 301 副本清不清得掉，取決於使用者之後會不會造訪同一個主機的其他網址，這不是 origin 控制得了的。
- **只在 HTTPS 上有效**。
- **規格狀態**：W3C 正式發布的版本停在 2017 年的 Working Draft，Editor's Draft 最後更新於 2023 年，兩者都不是 Recommendation。各瀏覽器支援哪些值，查各自的文件。

它適合的用途是使用者登出這類「從這個使用者的瀏覽器裡清掉資料」的時機，而不是改版時讓所有人拿到新內容。登出時通常不只清 `"cache"`，還會一起清 `"cookies"` 與 `"storage"`，各值在各瀏覽器的支援情形查 MDN 的 Clear-Site-Data 頁面。

## 各種手段能傳到的快取

| 手段                                     | 瀏覽器                       | 自己經營的反向代理       | 簽約的 CDN             | 第三方轉送代理           |
| ---------------------------------------- | ---------------------------- | ------------------------ | ---------------------- | ------------------------ |
| 規範的失效（不安全方法）                 | 只有發出請求的那個使用者     | 只有那個請求經過的那一台 | 只有請求經過的那個節點 | 只有那個請求經過的那一台 |
| purge                                    | 無                           | 依產品設定               | 依 CDN 功能            | 無                       |
| 版本化網址                               | 有效                         | 有效                     | 有效                   | 有效                     |
| Clear-Site-Data                          | 只有收到這個回應的那個使用者 | 無                       | 無                     | 無                       |
| 等待到期                                 | 有效                         | 有效                     | 有效                   | 有效                     |
| 下一次驗證（內容變了回 200、沒變回 304） | 驗證時更新                   | 驗證時更新               | 驗證時更新             | 驗證時更新               |

## 等待到期與改版全面生效的時間

表中「規範的失效」那一列是規範的要求：依 Varnish 7.7 的內建設定，POST、PUT、DELETE、PATCH 走 pass、直接轉給 origin，不會因此讓副本失效（這一點來自設定檔，沒有實測）；nginx 與各家 CDN 是否實作，查各自的文件。

上表的「等待到期」與「下一次驗證」兩種手段對每一層都有效，但它們都要等：等副本過期，或等快取下一次回來驗證。所以一個網址的內容「改了之後最慢多久所有人都看得到新版」，有三個成分：

- **各層的新鮮度期限**：回應寫了明確期限、而且每一層都正確傳遞 `Age` 時，這個成分的上限是各層裡最長的那個期限。回應沒有寫明確期限時，期限由各層自己估算，Chromium 對沒有快取標頭的 301 永不過期，這時就沒有上限（[12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)）。
- **過期副本的延用**：`stale-while-revalidate` 與 `stale-if-error` 的窗口（過期之後仍允許給出過期副本的秒數），以及 Varnish 這類實作自帶的寬限時間（參數 `default_grace`），會在期限之後再延長一段（[12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/)）。
- **年齡沒有傳下去的層**：這是各層新鮮度期限那一項的前提（每一層都正確傳遞 `Age`）不成立的情形。上游不送 `Age` 又改寫 `Date` 時，下游把收到的副本當成剛產生的，從零開始算它的期限；副本在上游已經放了的時間，會再加在下游的期限上，上限改成沿路各層期限相加（實測的 nginx proxy_cache 就是這樣，見 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/) 的〈Age 標頭與副本的目前年齡〉）。

這三個成分只計 HTTP 快取：已經開著的分頁、back/forward cache 與 Service Worker 不受這些期限約束；也假設沒有任何一層用自己的設定覆寫 origin 的期限。

所以選各層的期限（`max-age`、`s-maxage`、`CDN-Cache-Control`）的值，同時也是在選內容改版時最慢多久能全面生效，而這個時間要估得出來，前提是回應寫了明確期限。業務上能容忍多久的舊資料，在 [Freshness Window](/backend/knowledge-cards/freshness-window/) 卡裡是一個分級的需求；`max-age` 是讓 HTTP 快取符合那個需求的手段。

[Cache Invalidation](/backend/knowledge-cards/cache-invalidation/) 卡以應用層快取為主，討論 TTL、主動刪除、版本鍵、事件驅動等失效策略，和本篇的差別在快取由誰經營：應用層快取由服務自己讀寫，刪除一定做得到；本篇的快取多數不在 origin 手上。
