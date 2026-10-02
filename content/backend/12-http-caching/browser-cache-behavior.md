---
title: "12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁"
slug: "browser-cache-behavior"
date: 2026-10-02
description: "瀏覽器在不同操作下怎麼使用自己的 HTTP 快取：WHATWG Fetch 規範定義的快取模式、一般瀏覽、重新整理與強制重新整理各自送出的請求、請求端快取指令對中介快取的效力，以及與 HTTP 快取分開運作的 back/forward cache"
weight: 7
tags: ["backend", "http-caching", "browser", "bfcache"]
---

這篇整理瀏覽器的 HTTP 快取（一種私有快取）在使用者不同操作下的行為：快取裡同一份保存下來的回應（本模組稱為副本），使用者點連結進來、按重新整理、按強制重新整理、按上一頁，瀏覽器的處理各不相同。私有快取的定義見 [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)。本篇的實測使用 Chrome 154，其他瀏覽器的差異以各自的文件為準。

## Fetch 規範的快取模式

瀏覽器發出的每一個請求都帶著一個**快取模式**（cache mode），由 WHATWG Fetch 規範定義，決定這個請求怎麼使用 HTTP 快取。網頁程式可以用 `fetch(url, { cache: "..." })` 指定，瀏覽器自己的導覽與重新整理也對應到其中幾種：

| 快取模式   | 行為                                                     | 附加的 `Cache-Control`／`Pragma` 請求標頭     |
| ---------- | -------------------------------------------------------- | --------------------------------------------- |
| `default`  | 照新鮮度期限使用快取；副本新鮮就直接用，過期就送條件請求 | 無額外標頭                                    |
| `no-cache` | 有副本就送條件請求，沒有就送一般請求                     | `Cache-Control: max-age=0`                    |
| `reload`   | 當作沒有快取，送一般請求，並用結果更新快取               | `Cache-Control: no-cache`、`Pragma: no-cache` |
| `no-store` | 不讀也不寫快取                                           | `Cache-Control: no-cache`、`Pragma: no-cache` |

上表整理自 Fetch 規範 2026-09-21 版的 cache mode 定義與 HTTP-network-or-cache fetch 演算法。`default` 模式另外納入了 `stale-while-revalidate`：快取裡的副本已過期、但還在 `stale-while-revalidate` 的窗口內時，先回傳它，同時發出條件請求更新快取（見 [12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/)）。

## 一般瀏覽、重新整理與強制重新整理送出的請求

使用者操作與快取模式的對應，Fetch 規範沒有寫定，由瀏覽器決定。MDN 描述的對應是：一般重新整理對應 `no-cache`（送 `Cache-Control: max-age=0`，並帶上 `If-None-Match`、`If-Modified-Since`），強制重新整理對應 `reload`；MDN 也註明 Chrome、Edge、Firefox 的請求大致如此，Safari 有些不同。

實測時準備了一個沒有快取標頭的頁面 `/page`，頁面裡引用一個帶 `Cache-Control: max-age=60` 與 `ETag` 的 `/res.js`，在 60 秒內依序操作，從 origin 的存取紀錄看瀏覽器實際送出什麼：

| 操作                                 | `/page`（沒有快取標頭）                            | `/res.js`（`max-age=60`）                                               |
| ------------------------------------ | -------------------------------------------------- | ----------------------------------------------------------------------- |
| 第一次前往                           | 送到 origin                                        | 送到 origin                                                             |
| 一般瀏覽（同一分頁再次前往同一網址） | 送到 origin                                        | **沒有送出請求**，由快取回應                                            |
| 一般重新整理                         | 送到 origin，帶 `Cache-Control: max-age=0`         | **沒有送出請求**，也沒有條件請求                                        |
| 強制重新整理                         | 帶 `Cache-Control: no-cache` 與 `Pragma: no-cache` | 帶 `Cache-Control: no-cache` 與 `Pragma: no-cache`，origin 回完整的 200 |

一般重新整理那一列，子資源 `/res.js` 沒有被重新驗證；MDN 在同一頁也註明 Chrome 改了這個行為。這是 Chrome 從 2017 年起的設計，重新整理時只驗證主文件，子資源照一般規則使用快取：

> Chrome now has a simplified reload behavior to only validate the main resource and continue with a regular page load.（Chromium Blog，2017-01-26）

一般重新整理與強制重新整理兩列的差別，對 origin 有直接的影響：使用者回報「重新整理也沒看到新版」時，新鮮期間內的子資源在一般重新整理下不會被重新抓取，只有強制重新整理、或等副本過期之後，瀏覽器才會重新向 origin 取得。要讓瀏覽器立刻取得改版後的子資源，靠的是 [12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 的版本化網址，不能靠請使用者重新整理。

`/page` 在「再次前往」時也送到了 origin，原因是它沒有快取標頭，也沒有 `Last-Modified`；依 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/) 整理的 Chromium 啟發式規則，這種回應的期限是 0。反過來，同一個頁面如果帶 `Last-Modified`，Chromium 會用 `Date` 與 `Last-Modified` 間隔的 10% 當期限，期間內再次前往時直接使用舊的 HTML；舊 HTML 引用的仍是舊的資源網址，改版就看不到。HTML 頁面因此要明寫 `no-cache`，理由見 [12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 的〈版本化網址與 immutable〉。

## 請求端快取指令對中介快取的效力

重新整理時瀏覽器送出的 `Cache-Control: max-age=0` 或 `no-cache` 是**請求指令**，意思是「不要給我未經確認的副本」。這個請求在到達 origin 之前，會經過**中介快取**，也就是位在瀏覽器與 origin 之間的共用快取（CDN、反向代理、轉送代理，見 [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)）。請求指令對中介快取只是建議：

> They are advisory; caches MAY implement them, but are not required to.（RFC 9111 §5.2.1）

所以使用者強制重新整理，不保證 CDN 或轉送代理會跳過它們的副本回到 origin；是否遵守由各快取的設定決定，CDN 是否遵守客戶端送來的快取指令、能不能設定，查各家文件。從使用者這一端無法強迫中介快取更新，這也是換網址的版本化做法能對每一層快取都有效的原因：它不需要任何一層快取配合。

## 上一頁與 back/forward cache

使用者按上一頁、下一頁時，瀏覽器可能完全不經過 HTTP 快取，而是從 **back/forward cache**（bfcache）還原整個頁面。兩者是不同的機制：

> bfcache is a snapshot of the entire page in memory, including the JavaScript heap, whereas the HTTP cache contains only the responses for previously made requests.（web.dev，bfcache，2026-09-03 更新）

bfcache 還原的是記憶體裡的整個頁面狀態，包括網頁程式的變數，所以 `Cache-Control` 的新鮮度規則對它不適用。HTTP 快取規範在這點上留了空間：

> a history mechanism can display a previous representation even if it has expired（RFC 9111 §6）

實測時在一個帶 `Cache-Control: no-store` 的頁面上設一個網頁程式變數，點連結離開後按上一頁：頁面回來時那個變數還在，origin 也沒有收到請求，看起來是從 bfcache 整頁還原。web.dev 記載瀏覽器過去對帶 `no-store` 的頁面選擇不放進 bfcache，並說明 Chrome 正在調整，讓帶 `no-store` 的頁面在保護隱私的前提下也能放進去；放不放進 bfcache 是實作的選擇，規範沒有規定。所以 `no-store` 不能拿來保證「使用者按上一頁一定會重新向 origin 取得頁面」。登出後按上一頁仍看得到前一個使用者的畫面，這類問題要由網頁程式在 `pageshow` 事件裡檢查 `event.persisted`（為 true 代表頁面是從 bfcache 還原的），再重新確認登入狀態；登出時一併送出 `Clear-Site-Data: "cache", "cookies"`，可以清掉這個網站在瀏覽器裡的 HTTP 快取與 Cookie，它會不會讓 bfcache 裡的頁面失效，規格沒有寫明，要查各瀏覽器的文件（見 [12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) 的〈Clear-Site-Data〉）。各瀏覽器 bfcache 的資格條件查各自的文件。

## 記憶體快取與磁碟快取

瀏覽器的開發者工具常把來自快取的回應分成「memory cache」與「disk cache」。這是瀏覽器內部的儲存位置，HTTP 規範沒有這個區分。規範只提到瀏覽器可能另有頁面內的資源快取，而且這類快取「may or may not honor HTTP caching semantics」（RFC 9111 §6）。實測時用網頁的 performance API 只能看出回應來自快取（`deliveryType` 為 `cache`、`transferSize` 為 0），分不出是哪一種；判斷後端行為時，看的是請求有沒有送到 origin，不是這份回應落在哪一種儲存。
