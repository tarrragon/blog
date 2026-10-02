---
title: "模組十二：HTTP 快取與回應保存規則"
date: 2026-10-02
description: "整理 HTTP 回應離開 origin 之後被瀏覽器、CDN 與代理保存的規則：保存位置、新鮮度期限、過期後的驗證、快取鍵、已存副本的更新、過期副本的延用、瀏覽器端行為，以及在轉址、API 與個人化頁面上的應用"
weight: 13
tags: ["backend", "http-caching", "cache-control", "cdn"]
---

HTTP 快取模組處理的是應用層快取以外的那一段：一個 HTTP 回應離開 origin 之後，瀏覽器、CDN、反向代理會另外保存它的副本，之後的請求由這些副本回應，不再送到 origin。應用層快取（Redis 這類由服務自己讀寫的快取）在 [模組二：快取與 Redis](/backend/02-cache-redis/) 處理；本模組處理的副本存放在 origin 不經營、也不直接讀寫的位置。

## 推導源頭

本模組各章從同一個事實展開：**回應離開 origin 之後，origin 能交給下游副本的指令只有回應當下附帶的標頭，而每個快取依自己的實作預設解讀這些指令。** 由這個事實依序推出：

- 副本存放在哪些快取、各由誰經營（12.1）
- 副本在不詢問 origin 的情況下可以直接使用多久（12.2）
- 副本過期之後怎麼向 origin 確認是否仍然有效（12.3）
- 一個請求會拿到哪一份副本（12.4）
- origin 想改變已存副本時，指令能傳到哪幾個快取（12.5）
- 在什麼條件下允許給出過期副本（12.6）
- 瀏覽器在重新整理與上一頁時怎麼使用它的副本（12.7）
- 把前述規則用在具體回應上（12.8）

## 讀者定位

讀者是寫過 HTTP 服務、知道狀態碼與標頭是什麼，但沒有系統讀過 HTTP 快取規範的後端工程師。他缺的是兩件事：標頭在各種快取上的精確語意，以及規範與實作之間的落差。

## 規範與實作預設的分界

本模組每一章都區分兩類行為：**規範規定的行為**（RFC 9111 HTTP Caching、RFC 9110 HTTP Semantics 與相關擴充），以及**某個快取實作的預設**。實測一次 Varnish 7.7、nginx 1.27 與 Chrome 154 的結果顯示，兩者落差很大：同一組標頭，有的實作比規範保守、有的實作違反規範。文章寫出落差的形狀與該去哪個設定項查；預設數值只在說明落差形狀時引用，並標明讀取日期與版本；CDN 的預設行為各家不同，以各家文件為準。

## 章節列表

| 章節                                                                                                                | 主題                                                           |
| ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)                   | 私有快取與共用快取的定義、經營者、各自適用的指令               |
| [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)      | 副本可直接使用多久、Age 標頭、沒有指令時的啟發式期限           |
| [12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/)             | 驗證子、條件請求、no-cache 與 no-store 的差別、must-revalidate |
| [12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/)                         | 哪個請求拿到哪份副本、個人化回應在共用快取的處理規則           |
| [12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) | 各種更新手段能傳到哪幾個快取                                   |
| [12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/)            | 允許給出過期副本的條件與實作支援差異                           |
| [12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/)         | 一般瀏覽、重新整理與強制重新整理送出的請求、back/forward cache |
| [12.8 快取設定的應用：轉址、需登入的 API 回應與個人化頁面](/backend/12-http-caching/applying-cache-headers/)        | 具體回應的快取標頭選擇                                         |

## 和其他模組的分工

- [5.9 邊緣分發與靜態資源](/backend/05-deployment-platform/edge-cdn-static-distribution/) 處理 CDN 的營運面（origin 保護、tag purge 的操作模型）；本模組處理標頭語意，5.9 快取分層表的瀏覽器與邊緣層兩列以本模組為準。
- [Stale-While-Revalidate](/backend/knowledge-cards/stale-while-revalidate/)、[Stale-If-Error](/backend/knowledge-cards/stale-if-error/) 兩張卡直接沿用；[Freshness Window](/backend/knowledge-cards/freshness-window/) 卡處理業務能容忍多久的舊資料，12.5 把它和新鮮度期限接上。
- [0.24 短網址服務的實作](/backend/00-service-selection/url-shortener-implementation/) 的快取標頭一節是 [12.8 快取設定的應用：轉址、需登入的 API 回應與個人化頁面](/backend/12-http-caching/applying-cache-headers/) 〈轉址回應的狀態碼與快取標頭〉一節的一個實例。

## 研究材料

規範條文取自 RFC 9111、RFC 9110、RFC 9213、RFC 5861、RFC 8246 原文（2026-10-02 取得）；瀏覽器實作對照 Chromium `net/http/http_response_headers.cc` 與 Firefox `nsHttpResponseHead.cpp`（同日 main 分支）；實測環境是 docker 上的 Python origin、Varnish 7.7.3、nginx 1.27.5 與 Chrome 154。實測腳本與設定不放進文章，文章只引用觀察結果。

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                                                                                                                                                                                                             | 類型   | 前置條件                  | 規模 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | ------------------------- | ---- |
| 建 HTTP Cache-Control 知識卡：摘要 12.1–12.3 的定義、卡連回 12.1；文章保留行內定義（主線術語不外移）。00-service-selection/_index Backlog 的同一張卡改成指向這一列                                                                                                                               | 知識卡 | 無                        | 1 張 |
| 建 Vary、Heuristic Freshness 兩張卡（11-api 版本化辯論、5.9、0.24 會引用）                                                                                                                                                                                                                       | 知識卡 | 無                        | 2 張 |
| Stale-While-Revalidate、Stale-If-Error 兩張卡的〈概念位置〉連回 12.6；SIE 卡「SWR 是 TTL 過期但 origin 正常」改成 SWR 不論 origin 狀態都在窗口內可用；兩張卡補 s-maxage 組合的規範分歧與 Varnish 不認 stale-if-error                                                                             | 知識卡 | 無                        | 小   |
| 02 cache-aside〈應用層 + 邊緣層 Invalidation Pipeline〉漏了瀏覽器層：補「瀏覽器裡的副本清不掉，帶 max-age 的回應最長要等那個 max-age」並連 12.5〈等待到期與改版全面生效的時間〉（必修：照流程走會以為清完兩層大家就看到新資料）。00 cross-module-checkout-episode 的 Invalidation 順序同一個問題 | 跨模組 | 無                        | 小   |
| 5.9〈Origin Protection 的設計責任〉與判讀訊號「高峰時 origin 出現 5xx 尖峰」：動作改成 stale-if-error，補 s-maxage 組合的規範分歧與實作支援差異，連 12.6（必修：診斷與動作對不上）                                                                                                               | 跨模組 | 無                        | 小   |
| 5.9〈Cacheable vs Non-Cacheable 的判讀〉引用 12.4、12.2；〈Purge 與 Invalidation 的操作模型〉引用 12.5〈purge〉與〈版本化網址與 immutable〉                                                                                                                                                      | 跨模組 | 無                        | 小   |
| 5.9〈快取分層的責任分工〉連到 12.1，補反向代理與轉送代理；瀏覽器那一格補「下一次驗證」與 Clear-Site-Data；指向 0.24 的連結在 0.24 縮減後改指 12.8〈轉址回應的狀態碼與快取標頭〉；〈跨模組路由〉加模組十二，〈常見誤區〉的個人資料段連 12.4                                                       | 跨模組 | 無                        | 小   |
| 0.24 的快取標頭一節改成引用 12.8，只留短網址特有的部分；〈各層快取與撤回所需的時間〉的撤回時間公式補 stale 窗口與年齡沒傳下去的層，連 12.5（必修：據此算出的撤回 SLA 偏短）                                                                                                                      | 跨模組 | 無                        | 小   |
| 02 的 HTTP 層路由改放在 cache-aside.md（02 目錄頁讀者看不到）                                                                                                                                                                                                                                    | 跨模組 | 無                        | 小   |
| 補連結：11-api versioning-strategy-debate 的 Vary → 12.4；ci static-artifact-preview-flow → 12.8 靜態資源；09 peak-event-readiness 的 TTL → 12.2；06 performance-regression-gate 的 cache key → 12.4                                                                                             | 跨模組 | 無                        | 小   |
| monitoring js-ts-platform 的 `cache: 'no-store'` 機制說錯（它管 HTTP 快取，不管 Service Worker），改寫並連 12.7                                                                                                                                                                                  | 跨模組 | 無                        | 小   |
| 快取投毒（沒有列進快取鍵的請求標頭）與 web cache deception：12.4 新增一節或交給 07 安全模組                                                                                                                                                                                                      | 主章   | 查證 PortSwigger 研究原文 | 中   |
| origin 被打爆的集中入口：12.5〈purge〉補清空後的回源尖峰、12.3 補 no-cache 讓命中率歸零，連 Cache Stampede 卡與 5.9                                                                                                                                                                              | 主章   | 無                        | 小   |
| 遺留組合 `no-cache, no-store, must-revalidate` 加 `Pragma` 加 `Expires: 0` 的實際效果，以及回應端 `Pragma` 的落點                                                                                                                                                                                | 主章   | 查 RFC 9111 §5.4          | 小   |
| 「每一層能被哪些手段改到副本」在 12.1、12.4–12.8 換了六種說法、只有表頭有名字；實作相對規範「更保守／更寬鬆／違反」的分類只寫在本頁：各取一個名字在 12.1 界定，其他篇改用名字                                                                                                                    | 主章   | 無                        | 中   |
| 補跑 lab：`/cond` 回應後寬限時間內的請求，確認 Varnish 背景抓取帶 `If-None-Match`（目前依原始碼寫）；POST 後 GET 確認 Varnish、nginx 不做規範失效                                                                                                                                                | 案例   | 無                        | 小   |
