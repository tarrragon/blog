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
- origin 想改變已存副本時，各種更新手段的作用範圍（12.5）
- 在什麼條件下允許給出過期副本（12.6）
- 瀏覽器在重新整理與上一頁時怎麼使用它的副本（12.7）
- 把前述規則用在具體回應上（12.8）

## 讀者定位

讀者是寫過 HTTP 服務、知道狀態碼與標頭是什麼，但沒有系統讀過 HTTP 快取規範的後端工程師。他缺的是兩件事：標頭在各種快取上的精確語意，以及規範與實作之間的落差。

## 規範與實作預設的分界

本模組每一章都區分兩類行為：**規範規定的行為**（RFC 9111 HTTP Caching、RFC 9110 HTTP Semantics 與相關擴充），以及**某個快取實作的預設**。實測一次 Varnish 7.7、nginx 1.27 與 Chrome 154 的結果顯示，兩者落差很大：同一組標頭，實作的預設可能比規範保守、比規範寬鬆或違反規範，三類的界定寫在 12.1〈可以被保存的回應〉。文章寫出落差的形狀與該去哪個設定項查；預設數值只在說明落差形狀時引用，並標明讀取日期與版本；CDN 的預設行為各家不同，以各家文件為準。

## 章節列表

| 章節                                                                                                                | 主題                                                           |
| ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)                   | 私有快取與共用快取的定義、經營者、各自適用的指令               |
| [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)      | 副本可直接使用多久、Age 標頭、沒有指令時的啟發式期限           |
| [12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/)             | 驗證子、條件請求、no-cache 與 no-store 的差別、must-revalidate |
| [12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/)                         | 哪個請求拿到哪份副本、個人化回應在共用快取的處理規則、快取投毒 |
| [12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/) | 各種更新手段的作用範圍                                         |
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

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。目前沒有待辦項目。
