---
title: "6.3 fuzz campaign"
date: 2026-04-23
description: "整理輸入邊界、corpus 與 crash reproduction"
weight: 3
---

## 大綱

- input boundary
- corpus management
- crash reproduction
- minimization

## 判讀訊號

- fuzz corpus 從未更新、覆蓋率停滯
- crash 復現靠人工 minimization、無自動化
- fuzz 找到 bug 沒回灌成 regression test
- input boundary 無 spec、fuzz 範圍模糊
- production 出 crash 但 fuzz 沒抓到、信心錯配

## 交接路由

- 06.10 contract testing：schema fuzz 跟契約驗證互補
