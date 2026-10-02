---
title: "12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error"
slug: "serving-stale"
date: 2026-10-02
description: "快取在什麼條件下可以給出已經過期的副本：規範對過期副本的預設禁止、RFC 5861 的 stale-while-revalidate 與 stale-if-error 兩個擴充指令的語意與窗口，以及 Varnish、nginx 與瀏覽器在支援上的差異"
weight: 6
tags: ["backend", "http-caching", "cache-control", "stale-while-revalidate", "stale-if-error"]
---

這篇整理快取可以不等驗證、直接給出已經過期的副本的條件。副本過期之後的一般處理（驗證）見 [12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/)；本篇處理的是兩種例外：驗證可以在背景進行的時候，以及 origin 出錯的時候。新鮮度期限（副本不必詢問 origin 就能直接使用的時間）怎麼算，見 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)。

## 規範對過期副本的預設

規範的預設是過期副本不能直接給出，只有兩種情形例外：快取連不上 origin，或 origin 與客戶端用指令明確允許（RFC 9111 §4.2.4）。`no-cache`、`must-revalidate`、`proxy-revalidate` 與共用快取上的 `s-maxage` 會連這兩種例外一起禁止，完整的規定見 [12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/) 的〈過期副本在驗證前的處理〉。回應同時寫了 `s-maxage` 與下面兩個指令時，兩個指令的情形不同。`s-maxage` 在共用快取上禁止給出未經驗證的過期副本（RFC 9111 §4.2.4、§5.2.2.10）；§4.2.4 另一段列出的擴充指令許可，只在沒有這條禁止時才適用，所以 `s-maxage` 與 `stale-while-revalidate` 並用時，規範的答案是共用快取不延用過期副本。`stale-if-error` 則不同：RFC 5861 §4 寫它可以「regardless of other freshness information」，與 RFC 9111 的禁止衝突，兩份規範之間沒有一致的答案。實作上，Varnish 7.7 的原始碼把 `stale-while-revalidate` 的值直接當成寬限時間，不看 `s-maxage`；CDN 怎麼處理這個組合，以各家文件與實測為準。

明確允許的指令裡最常用的是 `stale-while-revalidate` 與 `stale-if-error`，兩者由 RFC 5861 定義。這份 RFC 的類別是 Informational，不在標準軌上（「This document is not an Internet Standards Track specification」），所以它的支援程度比 RFC 9111 的核心指令更依賴各實作。RFC 5861 寫到給出過期副本時要附 `Warning` 標頭，而 `Warning` 已在 RFC 9111 §5.5 廢止，實作多半不再送出它，不能拿它判斷回應是不是過期副本。

## stale-while-revalidate

```text
Cache-Control: max-age=600, stale-while-revalidate=600
```

這組標頭的意思是：新鮮度期限 600 秒；過期之後的 600 秒內，快取可以先把過期副本給出去，同時在背景向 origin 驗證或重新抓取，不讓請求等待（RFC 5861 §3）。過期之後允許給出過期副本的這段時間，本篇稱為 `stale-while-revalidate` 的**窗口**，長度就是指令後面的秒數。

> indicates that caches MAY serve the response in which it appears after it becomes stale, up to the indicated number of seconds.（RFC 5861 §3）

`stale-while-revalidate` 的使用條件：

- **背景更新要靠請求觸發**。只有在窗口內有請求進來，快取才會開始背景驗證；窗口內完全沒有請求，窗口結束後副本就照一般規則處理（RFC 5861 §3.1）。規範建議以請求觸發背景驗證，理由是避免放大攻擊（amplification attack，RFC 5861 §5）。
- **使用者可能拿到的最舊內容，年齡是 `max-age` 加上 `stale-while-revalidate` 的值**。以 `max-age=600, stale-while-revalidate=600` 為例，使用者最長可能拿到 1200 秒前產生的內容（RFC 5861 §3.1 的例子）。
- **窗口過後還沒更新成功，就不應該（SHOULD NOT）再給出過期副本**，除非符合規範允許的另一種例外，例如連不上 origin（RFC 5861 §3）。

站內 [Stale-While-Revalidate](/backend/knowledge-cards/stale-while-revalidate/) 卡從使用者體驗與新鮮度的取捨描述同一個機制。

## stale-if-error

```text
Cache-Control: max-age=600, stale-if-error=1200
```

這組標頭的意思是：過期之後，如果向 origin 驗證時遇到錯誤，快取可以在 1200 秒內改給過期副本，不把錯誤轉給客戶端（RFC 5861 §4）；這 1200 秒是 `stale-if-error` 的窗口。規範對「錯誤」的定義是會產生 500、502、503、504 的情形，包括連不上 origin。

> when an error is encountered, a cached stale response MAY be used to satisfy the request, regardless of other freshness information.（RFC 5861 §4）

它也可以出現在請求裡，作用範圍只限那一個請求。它的用途是把 origin 的短暫故障擋在快取這一層，站內 [Stale-If-Error](/backend/knowledge-cards/stale-if-error/) 卡把它放在 origin 保護的脈絡下討論。

## stale-while-revalidate 與 stale-if-error 的實作支援差異

這兩個指令的實作支援差異很大。實測 Varnish 7.7 與 nginx 1.27（預設設定，origin 回 `max-age=5` 加上其中一個指令；最後一列不加 stale 指令，改用 `max-age=10`）：

| 情形                                     | Varnish 7.7                                                          | nginx 1.27 proxy_cache                                                             |
| ---------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `stale-while-revalidate=30`，origin 正常 | 過期後先給過期副本，同時在背景抓新的                                 | 過期後同步回 origin 抓新的，請求要等；預設沒有打開 `proxy_cache_background_update` |
| `stale-while-revalidate=30`，origin 停機 | 窗口內給過期副本，超過後回 503                                       | 窗口內給過期副本，超過後回 504                                                     |
| `stale-if-error=60`，origin 停機         | 不認得這個指令，只靠自己的預設寬限時間延用過期副本，之後回 503       | 窗口內給過期副本                                                                   |
| 沒有任何 stale 指令，`max-age=10`        | 過期後仍有一段寬限時間（參數 `default_grace`）先給過期副本、背景更新 | 過期後同步回 origin                                                                |

沒有任何 stale 指令時，Varnish 預設也會在過期後的一段時間內給出過期副本。規範的預設是不給出過期副本，所以這是比規範寬鬆的實作預設：沒寫任何 stale 指令的回應（例如商品價格）放在 Varnish 後面，過期後仍可能被給出一小段時間。

在瀏覽器上，WHATWG Fetch 規範的 `default` 快取模式（見 [12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/) 的〈Fetch 規範的快取模式〉）納入了 `stale-while-revalidate`：快取裡的副本已過期、但還在窗口內時，先回傳它，同時發出條件請求更新快取。`stale-if-error` 在瀏覽器的支援情形查各自的文件。CDN 對這兩個指令的支援與上限，同樣查各家文件。

## stale-while-revalidate 與 stale-if-error 的選擇

兩個指令回答的是不同的問題：

- **`stale-while-revalidate`** 回答「內容過期一小段時間，使用者拿到舊版可以接受嗎」。可以接受的內容（文章列表、商品介紹）用它換取每次都不必等 origin 回應；不能接受的內容（庫存數字、權限相關的回應）不用它。
- **`stale-if-error`** 回答「origin 故障時，給舊內容比給錯誤頁好嗎」。對多數讀取型內容答案是肯定的；對寫入結果、付款狀態這類「舊答案會造成錯誤行為」的內容，答案是否定的，那類回應用 `no-cache`，每次使用前都向 origin 確認；`must-revalidate` 只適合新鮮期間內可以接受舊值、過期後不能延用的內容（兩者的差別見 [12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/)）。`must-revalidate` 禁止給出過期副本是規範層的要求；Varnish 7.7 的原始碼裡，寬限時間預設取 `default_grace`，不因 `must-revalidate` 關閉，所以預設設定下帶 `must-revalidate` 的副本仍會在寬限時間內被給出，要在 VCL 裡另外處理（`no-cache` 的回應 Varnish 預設不保存，沒有這個問題）。

兩個窗口都會延長內容改版後全面生效的時間：正常運作時延長的是 `stale-while-revalidate` 的窗口，origin 出錯期間延長的是 `stale-if-error` 的窗口，加在 [12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 的〈等待到期與改版全面生效的時間〉列出的其他成分之上。決定窗口長度時，要同時看 [12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 裡各種更新手段的作用範圍：瀏覽器、CDN、反向代理這幾層快取當中，哪一層的副本清得掉、哪一層只能等到期。
