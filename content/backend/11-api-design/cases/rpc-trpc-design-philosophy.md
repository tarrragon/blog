---
title: "11.C33 tRPC 設計哲學：無 schema 無 codegen 的型別共享"
date: 2026-07-03
description: "把 API 契約從 IDL 檔搬進型別系統的極端點、官方自述的前提與代價（TS-only、同倉共置）"
weight: 33
tags: ["backend", "api-design", "case-study", "rpc"]
---

這個案例的核心責任是記錄 tRPC 官方自述的設計哲學、含它自己承認的前提與代價。

## 觀察

核心主張：「build & consume fully typesafe APIs without schemas or code generation」、靠 TypeScript 型別推導、無 codegen、無 runtime bloat、無 build pipeline。官方 FAQ 明言前提與代價：脫離 monorepo 就失去 client 與 server 一起運作的保證、替代方案是把 backend 型別發成 private npm package；動態型別輸出做不到（需 TypeScript 尚未支援的 higher-kinded types）；Netflix、Pleo 等在 production 使用。

## 判讀

tRPC 是「把 API 契約從 IDL 檔搬進型別系統」的極端點 — 換到零 codegen 的 DX、付出語言鎖定（TS-only）與部署形態鎖定（同倉或私有 npm 包）。教學上與 protobuf 對照：兩者都在解契約同步、一個走 schema-first 跨語言、一個走 inference-first 單語言。

## 對應大綱

styles/rpc-revival/「tRPC 與型別共享」（anchor、與 C23 Echobind 並用）、11.2 風格選型交叉。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [tRPC docs](https://trpc.io/docs)
- [tRPC FAQ](https://trpc.io/docs/faq)
