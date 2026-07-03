---
title: "11.C25 HackerOne：introspection 列舉出未授權的 CreateAdminUser"
date: 2026-07-03
description: "introspection 作為攻擊面偵察工具的實證：schema 自我揭露讓隱藏 mutation 免 fuzzing 直接可見"
weight: 25
tags: ["backend", "api-design", "case-study", "graphql", "security"]
---

這個案例的核心責任是提供「introspection 等於攻擊面偵察工具」的具體實證。

## 觀察

某電商平台的第三方 banner 服務暴露 GraphQL 端點、introspection 開啟；研究者（J. Francisco Bolivar、2023 HackerOne Ambassador World Cup 期間回報）用 introspection 列舉 schema、發現未加驗證的 `CreateAdminUser` mutation、直接取得管理權限、數日內修復。報告結論建議：production 關 introspection、field-level authorization、移除不必要的 mutation。

## 判讀

REST 世界要靠 fuzzing 才找得到的隱藏端點、GraphQL 用型別系統自己告訴你。教學上與 C22 的 CPU / 記憶體放大並列成兩類攻擊面：資訊暴露與資源耗盡。

## 對應大綱

[執行成本與攻擊面](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/)（introspection 段、已引用）。邊緣（安全單點案例）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [How a GraphQL Bug Resulted in Authentication Bypass（HackerOne blog）](https://www.hackerone.com/blog/how-graphql-bug-resulted-authentication-bypass)
