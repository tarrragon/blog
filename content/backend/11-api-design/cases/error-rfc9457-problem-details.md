---
title: "11.C35 RFC 9457：problem+json 標準化錯誤格式"
date: 2026-07-03
description: "type 用 URI 外部化錯誤命名空間、client 必須忽略未知欄位的演化條款、IANA registry 補 7807 碎片化"
weight: 35
tags: ["backend", "api-design", "case-study", "error-model"]
---

這個案例的核心責任是提供錯誤格式標準化的現行基準（obsoletes RFC 7807）。

## 觀察

RFC 9457（IETF Proposed Standard、Standards Track、2023-07）定義 `application/problem+json`：五個核心成員 `type`（URI、預設 `about:blank`）、`title`、`status`、`detail`、`instance`；允許 extension members 且要求 client 忽略不認識的欄位；建立 IANA common problem types registry（7807 沒有）。RFC 明言 problem details 是補充 HTTP status code、不是取代。

## 判讀

`type` 用 URI 而非字串 enum、把錯誤種類的命名空間外部化、避免各團隊 code 撞名；「client MUST ignore unknown extensions」是向前相容的演化條款、等同錯誤模型的 OCP。registry 的新增是對 7807 生態碎片化的直接回應。

## 對應大綱

11.4 錯誤模型設計（anchor）、錯誤格式爭論文章。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [RFC 9457: Problem Details for HTTP APIs（IETF、2023）](https://www.rfc-editor.org/rfc/rfc9457.html)
