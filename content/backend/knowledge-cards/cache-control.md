---
title: "Cache-Control（快取控制標頭）"
date: 2026-10-02
description: "看到回應帶 Cache-Control、或要決定某個回應能被誰保存、保存多久、使用前要不要先問 origin 時，查這個標頭各指令的分工"
weight: 444
tags: ["backend", "http-caching", "cache-control", "knowledge-card"]
---

Cache-Control 是 HTTP 回應（與請求）上的標頭，用一組指令告訴沿路的快取三件事：這份回應能不能保存、保存在哪一種快取、保存之後多久之內可以不問 origin 直接使用。它是 origin 對瀏覽器、CDN 與代理下指令的主要管道，可以直接使用的那段時間就是 [TTL](/backend/knowledge-cards/ttl/)，超過之後是否允許先給舊版，由 [Stale-While-Revalidate](/backend/knowledge-cards/stale-while-revalidate/) 這類擴充指令決定。

## 概念位置

Cache-Control 位在 HTTP 快取的指令層，常用指令按職責分組：

- **保存位置**：`private` 只讓使用者自己的瀏覽器保存，`public` 允許共用快取保存帶 `Authorization` 請求的回應，`no-store` 讓任何快取都不保存。
- **新鮮度期限**：`max-age` 給所有快取，`s-maxage` 只給共用快取並取代 `max-age`。兩者都沒有、也沒有 `Expires` 時，快取改用 [Heuristic Freshness](/backend/knowledge-cards/heuristic-freshness/) 自己估。
- **過期後的處理**：`no-cache` 要求每次使用前都先向 origin 驗證，`must-revalidate` 禁止過期之後不經驗證就給出舊版，[Stale-If-Error](/backend/knowledge-cards/stale-if-error/) 允許 origin 出錯時給出舊版。

哪些請求共用同一份保存的回應不由這個標頭管，那是快取鍵與 [Vary](/backend/knowledge-cards/vary/) 的職責。

## 可觀察訊號與例子

一個需要登入才拿得到的 API 回應寫 `Cache-Control: private, no-cache` 加上 `ETag`：CDN 不保存，使用者的瀏覽器可以保存，但每次使用前都送條件請求確認，內容沒變時 origin 回 304、省下傳輸內容。同一個網站的版本化靜態檔（檔名含內容雜湊）寫 `public, max-age=31536000, immutable`，每一層快取都可以在一年內直接使用。

回應完全沒有 Cache-Control、也沒有 `Expires` 時，它仍可能被保存：狀態碼屬於可啟發式快取的種類（例如 200、301、404）時，各快取依自己的規則估一個期限，同一個 301 在不同瀏覽器與代理上得到的期限可能差到從零到永不過期。

## 判讀方式

讀一個回應的 Cache-Control 時，依序問三件事：它能不能給別人（看 `private`／`public`；請求帶 `Authorization` 時規範禁止共用，但實作不一定遵守，需登入的回應明寫 `private`，見 [12.4 快取鍵與副本共用：Vary、Cookie 與 Authorization](/backend/12-http-caching/cache-key/)）、內容會不會改（看期限指令，沒有期限就是交給各快取自己估）、origin 改了內容之後最慢多久要讓所有人看到（期限加上 stale 窗口，以及上游沒傳 `Age` 時各層期限相加，見 [12.5 已保存副本的更新方式：失效、purge、版本化網址與等待到期](/backend/12-http-caching/updating-stored-responses/)）。

名稱與作用容易對不上的兩個指令：

- `no-cache`：可以保存，但每次使用前都要驗證；讓快取完全不保存的是 `no-store`。
- `private`：只規定保存位置（共用快取不存），不保護內容本身。另外，回應另外帶了有效的 `CDN-Cache-Control`（或該 CDN 認得的同類欄位）時，實作它的 CDN 會整個忽略這則回應的 Cache-Control，`private` 也跟著失效。

完整的規範與實作差異在 [模組十二：HTTP 快取與回應保存規則](/backend/12-http-caching/)：保存位置與各指令的對象見 [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)，期限的取用順序見 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)，`no-cache`、`no-store`、`must-revalidate` 的差別見 [12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/)，具體回應的標頭選擇見 [12.8 快取設定的應用：轉址、需登入的 API 回應與個人化頁面](/backend/12-http-caching/applying-cache-headers/)。
