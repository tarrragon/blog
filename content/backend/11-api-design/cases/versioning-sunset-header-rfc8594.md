---
title: "11.C15 RFC 8594 Sunset header：退場宣告的機器可讀層"
date: 2026-07-03
description: "用 HTTP header 宣告資源退場時點的標準化嘗試、Informational 地位與實務採用有限"
weight: 15
tags: ["backend", "api-design", "case-study", "versioning"]
---

這個案例的核心責任是提供 deprecation 通訊的機器可讀層標準與它的誠實邊界。

## 觀察

Sunset header 帶 HTTP-date、宣告資源預期不可用的時點；spec 明確區分 deprecation 兩階段 — header 只對應第二階段（真的下線）、不用於「不再推薦」。另定義 `sunset` link relation 指向退場政策與遷移文件。定位是 client hint、不是保證。RFC 地位為 Informational、非 Standards Track（2019、Erik Wilde）。

## 判讀

公告與 email 觸及人、header 觸及程式 — 這是 Sunset header 承擔的縫隙。教材引用時要標明它是「約定嘗試」而非普及標準：Slack 與 GitHub 的實務分別用 in-band response warning 與 brownout、沒等這個 spec。

## 對應大綱

11.5 版本策略與 deprecation、11.6 向後相容的變更紀律。邊緣（spec 補充）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [RFC 8594: The Sunset HTTP Header Field（IETF、Informational、2019）](https://www.rfc-editor.org/rfc/rfc8594.html)
