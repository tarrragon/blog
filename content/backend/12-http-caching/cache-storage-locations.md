---
title: "12.1 HTTP 回應的保存位置：私有快取與共用快取"
slug: "cache-storage-locations"
date: 2026-10-02
description: "HTTP 回應離開 origin 之後可能被保存的位置：私有快取與共用快取的規範定義、瀏覽器、CDN、反向代理與轉送代理各由誰經營、規範列出的保存條件、只對共用快取或只對私有快取有效的指令，以及把指令指定給 CDN 的 CDN-Cache-Control"
weight: 1
tags: ["backend", "http-caching", "cache-control", "cdn"]
---

這篇整理一個 HTTP 回應從 origin（產生回應的源站伺服器）送出、到達使用者之前與之後，可能被另外保存的位置、規範允許保存的條件，以及 `Cache-Control` 標頭裡哪些指令只對共用快取或只對私有快取有效。範圍是 RFC 9111 定義的 HTTP 快取；瀏覽器的 back/forward cache 與 Service Worker 自行管理的快取不照這套規則運作，back/forward cache 在 [12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/) 說明，Service Worker 的快取不在本模組範圍。

## 私有快取與共用快取的定義

快取保存下來的回應，本模組稱為**副本**。RFC 9111 把快取分成兩種，分界是**一份副本會被幾個使用者重用**：

> A "shared cache" is a cache that stores responses for reuse by more than one user; shared caches are usually (but not always) deployed as a part of an intermediary. A "private cache", in contrast, is dedicated to a single user; often, they are deployed as a component of a user agent.（RFC 9111 §1）

**私有快取**只替一個使用者保存副本，最常見的是瀏覽器的 HTTP 快取：使用者 A 的瀏覽器存下的副本，只會再拿來回應使用者 A 自己的請求。**共用快取**保存的副本會被拿去回應不同使用者的請求，CDN、放在 origin 前面的反向代理、企業或電信業者的轉送代理都屬於這一種。

這個分界看的是重用範圍，不看快取放在網路上的哪個位置，原文的「usually」「often」就是在交代這一點。一台放在 origin 同一個機房、由同一個團隊維運的 nginx 反向代理，只要它把同一份副本發給不同使用者，它就是共用快取，所有適用於共用快取的規則都套用在它身上。

區分兩者的理由在後果：同一份回應如果帶著某個使用者的個人資料，存進私有快取只會回到那個使用者手上，存進共用快取就會被發給別人。規範裡多數只針對共用快取的規則，都在防止這件事。

## 各種快取的經營者與 origin 能直接操作的範圍

一個回應從 origin 到使用者之間，可能依序經過反向代理、CDN、轉送代理，最後到瀏覽器；本模組把路徑上的每一個快取稱為一**層**。各層的經營者不同，origin 能對它們做的事也不同：

| 快取                                                                     | 種類 | 經營者               | origin 能直接操作的範圍                                                                                                           |
| ------------------------------------------------------------------------ | ---- | -------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| 瀏覽器的 HTTP 快取                                                       | 私有 | 使用者自己的裝置     | 無法讀取或刪除；只能透過回應標頭指示，以及只作用於瀏覽器的 [Clear-Site-Data](/backend/12-http-caching/updating-stored-responses/) |
| CDN                                                                      | 共用 | 與 origin 簽約的業者 | 透過 CDN 自己提供的管理介面或 API 清除（purge），這是 CDN 的產品功能，不屬於 HTTP 規範                                            |
| 反向代理（例如 Varnish、nginx 的 proxy_cache）                           | 共用 | origin 自己的團隊    | 設定檔與管理指令都在自己手上                                                                                                      |
| 轉送代理（企業網路、部分電信業者；限明文 HTTP，或會解開 TLS 的企業代理） | 共用 | 第三方               | origin 通常不知道它存在，只能透過回應標頭指示                                                                                     |

「origin 能直接操作的範圍」這一欄推出一個前提：**瀏覽器快取與第三方轉送代理沒有任何管理介面可用，origin 想改變它們手上的副本，都要等它們再向 origin 送出請求。** 轉送代理會在副本過期、回來驗證或重抓時送出請求，經過它的請求帶的快取指令它可以不理（[12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/) 的〈請求端快取指令對中介快取的效力〉），origin 不能指望它提早更新；瀏覽器另外還有使用者之後造訪同一個網站時的請求，origin 可以利用那些請求帶上清除指令（[Clear-Site-Data](/backend/12-http-caching/updating-stored-responses/)），或由網頁程式以重抓模式覆寫副本、改用新網址繞開副本（[12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/) 的〈Fetch 規範的快取模式〉）。例如一個 API 回應誤設 `max-age=86400` 上線：企業轉送代理裡的副本，最壞的情況要等這一天過完；使用者瀏覽器裡的副本，可以讓前端改呼叫新的網址，或以 `fetch(url, { cache: "reload" })` 重抓一次，兩者都要等使用者再打開這個網站才會發生。簽約的 CDN 同樣不由 origin 經營，但它另外提供清除介面，清得到的範圍限於簽約的那一家。

## 可以被保存的回應

規範用一份條件清單規定快取什麼時候**不可以**保存回應（RFC 9111 §3）。規範用大寫的 MUST、SHOULD、MAY 標示要求的強度（RFC 9111 §1.1 引用 RFC 2119 與 RFC 8174 的定義）：MUST 是必須，SHOULD 是除非有充分理由否則應該，MAY 是允許；小寫的同一個字是一般用語。主要條件整理如下，全部滿足才可以保存：

- 請求方法是快取理解、而且允許快取的方法（多數實作只支援 GET 與 HEAD，見 [12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/)）。
- 回應的狀態碼是最終回應（不是 1xx 這類中間回應）。
- 狀態碼是 206 或 304、或回應帶 `must-understand` 指令時，快取要理解這個狀態碼。
- 回應沒有 `no-store`。
- 共用快取另外兩條：回應沒有 `private`；請求沒有 `Authorization`，或回應用指令明確允許共用（見 [12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/) 的〈帶 Authorization 的請求在共用快取的重用規則〉）。
- 回應至少帶有下列一項：`public`、`private`（僅限私有快取）、`Expires`、`max-age`、`s-maxage`（僅限共用快取）、允許快取的擴充指令，或狀態碼屬於「可啟發式快取」的種類。

清單的最後一條決定了沒有任何快取指令的回應能不能被保存：狀態碼在可啟發式快取的清單裡（例如 200、301），就可以保存，保存之後能直接使用多久由快取自己估算；不在清單裡（例如 302、307），規範不允許保存。這份清單與估算方式在 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/) 的〈沒有明確期限時的啟發式期限〉。

這份清單是規範的要求，而實作的預設可能和它有三種落差，本模組各篇用同一組名稱標出：

- **比規範保守**：規範允許保存或重用的回應，實作不保存或不重用。對 origin 的代價是失去快取的效益，這些請求的負載全部回到 origin。例子是 Varnish 預設不保存 `no-cache` 的回應（[12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/) 的〈共用快取實作的驗證預設〉）。
- **比規範寬鬆**：規範預設不允許、但留了出口讓經營者用設定開啟的行為，實作預設就開著。RFC 9111 §4.2.4 預設不給出過期副本，同時允許依「out-of-band contract」的設定給出，Varnish 預設的寬限時間就落在這個出口上（[12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/)）。代價落在使用者這一端：拿到的舊內容比標頭宣告的期限更舊。
- **違反規範**：規範沒有留出口的禁止，實作照樣做。代價最直接，可能把一個使用者的回應發給別人。例子是預設設定的 nginx 共用帶 `Authorization` 請求的回應（[12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/) 的〈帶 Authorization 的請求在共用快取的重用規則〉）；回應明寫 `must-revalidate` 而 Varnish 仍在寬限時間內給出它的過期副本，也屬於這一類，因為明確的指令禁止沒有設定上的出口（[12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/)）。

三種落差都只能從實作的文件、原始碼或實測得知。規範隱含的保護（例如帶 `Authorization` 的回應不被共用）不能依賴，要由回應明寫的標頭（`private`、`no-store`）承擔；延用過期副本這一類，連明寫的 `must-revalidate` 都可能被實作的寬限時間略過，要回到快取自己的設定處理。

## 只對共用快取或只對私有快取有效的指令

`Cache-Control` 標頭裡有幾個指令只對共用快取或只對私有快取有效，表中 `no-store` 列作對照，它對兩種快取都有效：

| 指令               | 對私有快取                                       | 對共用快取                                                                   | 出處               |
| ------------------ | ------------------------------------------------ | ---------------------------------------------------------------------------- | ------------------ |
| `private`          | 可以保存（即使回應原本不屬於可啟發式快取的種類） | 不可保存                                                                     | RFC 9111 §5.2.2.7  |
| `public`           | 標示可保存                                       | 允許把帶 `Authorization` 標頭的請求所拿到的回應保存下來重用                  | RFC 9111 §5.2.2.9  |
| `s-maxage`         | 忽略                                             | 取代 `max-age` 與 `Expires` 作為新鮮度期限，並帶有 `proxy-revalidate` 的語意 | RFC 9111 §5.2.2.10 |
| `proxy-revalidate` | 忽略                                             | 過期後必須向 origin 驗證成功才能使用                                         | RFC 9111 §5.2.2.8  |
| `no-store`         | 不可保存                                         | 不可保存                                                                     | RFC 9111 §5.2.2.5  |

`private` 只規定保存位置：共用快取不可以存，瀏覽器可以存。規範在同一節明寫它不是保密機制：

> This usage of the word "private" only controls where the response can be stored; it cannot ensure the privacy of the message content.（RFC 9111 §5.2.2.7）

`public` 在多數情形下是多餘的：回應本來就可以被快取時，加上它不改變任何行為（RFC 9111 §5.2.2.9）。它有作用的情形是請求帶了 `Authorization` 標頭，這種情形在 [12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/) 說明。

本模組的實測環境是 docker 上的一支 Python origin，前面分別接 Varnish 7.7.3 與 nginx 1.27.5，瀏覽器是 Chrome 154。Varnish 只另外加了測試 purge 與 ban 用的規則，一般路徑的請求都走內建設定；nginx 在一般路徑上只加了開啟快取所需的 `proxy_cache_path` 與 `proxy_cache`，另有轉送與記錄用的設定，不影響快取判斷。各篇說的「預設設定」都指這個狀態，個別調過參數的測試會在該處寫明。用實測對照規範：回應帶 `Cache-Control: private, max-age=60` 時，Varnish 7.7 與 nginx 1.27 的 proxy_cache 兩者都沒有保存，每個請求都送到 origin，與規範一致。回應帶 `max-age=5, s-maxage=30` 時，兩者在第一次請求之後的第 18 秒（`max-age` 的 5 秒已過、`s-maxage` 的 30 秒未到）仍由快取直接回應，也就是採用了 `s-maxage`。

## 把指令指定給特定快取：CDN-Cache-Control

`s-maxage` 能區分「共用快取」與「私有快取」，但無法再細分到某一個共用快取。規範明寫這個限制：

> It is not possible to target a directive to a specific cache.（RFC 9111 §5.2）

這個限制的代價是：origin 經常想讓自己簽約的 CDN 把副本當作新鮮久一點（因為 CDN 有清除介面，內容要改時可以主動清掉），同時讓瀏覽器與第三方轉送代理短一點（因為它們清不掉）。用 `s-maxage` 只能把 CDN 與轉送代理綁在一起設定。

RFC 9213 為這個需求定義了「指定目標的快取控制欄位」：欄位的語意和 `Cache-Control` 相同，但欄位名稱指明了適用對象。其中 `CDN-Cache-Control` 適用於代表 origin 運作的分散式快取網路，也就是 CDN。實作這個欄位的快取，在這個欄位有有效值時忽略回應裡的 `Cache-Control` 與 `Expires`，改用它（RFC 9213 §2.2）。規範裡的例子：

```text
Cache-Control: max-age=60, s-maxage=120
CDN-Cache-Control: max-age=600
```

這組標頭讓 CDN 把副本視為新鮮 600 秒，其他共用快取 120 秒，瀏覽器 60 秒。不支援 `CDN-Cache-Control` 的快取把它當成一個不認得的標頭欄位：RFC 9110 §5.1 要求代理照樣轉送不認得的欄位，其他接收者應該（SHOULD）忽略這個欄位；實作了 RFC 9213、但 `CDN-Cache-Control` 不在自己目標清單裡的快取，依 RFC 9213 §2.2 不可以因為這個欄位改變行為。所以加上這個欄位，不支援的快取照 `Cache-Control` 運作。反過來，實作這個欄位的 CDN 會整個忽略 `Cache-Control`，包括其中的 `private`（RFC 9213 §2.2；§5 也提醒這種組合可能讓帶敏感資訊的回應被重用）；Varnish 的內建設定在回應帶 `Surrogate-Control` 時，不再檢查 `Cache-Control` 的 `no-cache`、`no-store` 與 `private`，只看 `Surrogate-Control` 裡有沒有 `no-store`。個人化的回應要在 `CDN-Cache-Control` 裡寫 `private` 或 `no-store`、在 `Surrogate-Control` 裡寫 `no-store`，或不送這些欄位。

在 RFC 9213 之前，部分 CDN 用 `Surrogate-Control` 這類自訂欄位把指令指定給 CDN。它出自 2001 年的一份 W3C Note（Edge Architecture Specification 1.0），不是標準，RFC 9213 對這類先行做法的評語是「their interoperability is low」。手上的 CDN 支援 `CDN-Cache-Control`、`Surrogate-Control` 還是自己的欄位，以該 CDN 的文件為準。

## 沒有快取標頭的回應的預設處理

規範的預設立場是重用保存的回應：

> it can be assumed that reusing a cached response is desirable and that such reuse is the default behavior when no requirement or local configuration prevents it.（RFC 9111 §2）

所以沒有寫 `Cache-Control` 的回應仍可能被快取：依〈可以被保存的回應〉的最後一條，狀態碼在可啟發式快取的清單裡就能保存，直接使用多久由各快取自行估算，估算方式在 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)。要確定某個回應不被任何快取保存，要明寫 `no-store`；要讓它可以保存但每次使用前都先問 origin，寫 `no-cache`，兩者的差別在 [12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/)。
