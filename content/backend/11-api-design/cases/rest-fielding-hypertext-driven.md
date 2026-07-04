---
title: "11.C2 Fielding：REST API 必須是 hypertext-driven"
date: 2026-07-03
description: "REST 定義擁有者公開否定業界主流用法的引爆點文獻、六條規則劃出 hypertext-driven 的判別線"
weight: 2
tags: ["backend", "api-design", "case-study", "rest"]
---

這個案例的核心責任是記錄「語意學之爭」的引爆點：定義擁有者親自劃線。

## 觀察

Fielding 在 2008 年的 blog 文列出六條 REST API 規則：協定獨立、不改標準協定、描述精力放在 media type 與 relation name（而非逐 URI 逐方法的文件）、server 必須擁有自己的 namespace（client 不得假設固定 URI 結構）、resource type 對 client 不可見、所有 application state transition 必須由 client 從 server 提供的選項中選擇驅動。文中直接批評自稱 REST 的 RPC-style API 造成過度耦合。

## 判讀

教學判準：「client 是否需要 out-of-band 文件才能操作 — 需要、就不是 Fielding 意義的 REST」。同時揭露命名權之爭：術語定義者與業界慣行的張力、是流派層敘事的起點。

## 對應大綱

[REST 流派總覽](/backend/11-api-design/styles/rest/)（out-of-band 知識判別線的來源、已引用）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [REST APIs must be hypertext-driven（Roy Fielding blog、2008）](https://roy.gbiv.com/untangled/2008/rest-apis-must-be-hypertext-driven)
