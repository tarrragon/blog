---
title: "11.C23 Echobind：從 GraphQL 撤到 tRPC 的量化帳（反例）"
date: 2026-07-03
description: "反例：五層重複宣告與三層 codegen 拖垮 DX 的量化紀錄、同時自列 tRPC 的適用前提"
weight: 23
tags: ["backend", "api-design", "case-study", "graphql", "rpc"]
---

這個案例的核心責任是劃出 GraphQL 與 tRPC 各自的適用邊界、單一 TypeScript 團隊場景的量化對照。跨主題案例：GraphQL 撤退面與 tRPC 採用面共用本檔。

## 觀察

痛點是 double declaration：同一資料形狀要在 Prisma / Nexus / GraphQL operations / codegen types / client queries 五層宣告；三層 codegen 產出 8,200 行型別檔、常需重啟 VSCode language server；GraphQL 依賴 81.2kb、tRPC 23.7kb；Apollo normalized cache 在 mutation 後常態性要手動 `refetchQueries`。遷移後淨減 1,608 行。文章同時明列 tRPC 前提：「server 用 TypeScript 且與 client 共置」、無法有效服務公開第三方 API。

## 判讀

撤退動因是「單一團隊同時擁有前後端」時、GraphQL 的 schema 中介層變成純開銷 — schema 作為跨團隊 / 跨 client 契約才有價值、同構 TypeScript 單團隊是反指標。作者自列的 tRPC 邊界（公開 API 不適用）可直接引用、避免被讀成萬用推薦。

## 對應大綱

styles/graphql/「公開 API 的 GraphQL 進退」（適用邊界段、反例）、styles/rpc-revival/「tRPC 與型別共享」（anchor）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Why we ditched GraphQL for tRPC（Echobind blog、2022）](https://echobind.com/post/why-we-ditched-graphql-for-trpc)
