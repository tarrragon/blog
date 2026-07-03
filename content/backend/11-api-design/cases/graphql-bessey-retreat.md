---
title: "11.C22 Matt Bessey：六年 GraphQL 老手的撤退清單（反例）"
date: 2026-07-03
description: "反例：授權下推到 field、成本不可預測、解析層攻擊面的執行期代價清單、附撤退判準"
weight: 22
tags: ["backend", "api-design", "case-study", "graphql"]
---

這個案例的核心責任是提供 GraphQL 撤退論證中最完整的執行期代價清單。

## 觀察

作者（六年 GraphQL 使用經驗）列舉：每個 field 都要各自做授權檢查；128 bytes 的惡意查詢可耗 10 秒 CPU；畸形 directives 造成 2,000 倍記憶體放大；N+1 迫使處處防禦性套 Dataloader、且授權檢查本身也會 N+1。建議控制得了 client 的團隊改用 OpenAPI 3 REST（FastAPI / tsoa / TypeSpec）。

## 判讀

代價清單全部落在執行期與安全面 — 跟採用文宣的 DX 敘事正交、逐條對應「執行成本與安全」章的大綱（授權下推到 field、成本不可預測、解析層攻擊面）。撤退判準的核心句：「控制得了 client、就不需要 GraphQL 的彈性」。

## 對應大綱

styles/graphql/「執行成本與安全」+「公開 API 的 GraphQL 進退」。反例。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Why, after 6 years, I'm over GraphQL（Matt Bessey、2024）](https://bessey.dev/blog/2024/05/24/why-im-over-graphql/)
