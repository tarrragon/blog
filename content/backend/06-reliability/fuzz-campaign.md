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

## 概念定位

[Fuzz test](/backend/knowledge-cards/fuzz-test/) 是針對未知輸入邊界做自動探索的驗證流程，責任是把沒想過的輸入轉成可重播、可修補的失敗案例。

這一頁處理的是輸入空間的盲區。當 API、parser、codec 或 schema 的邊界不清楚時，fuzz 比人工列案例更能覆蓋非預期路徑。

## 核心判讀

判讀 fuzz 的品質，不看 crash 數量而已，要看是否能把失敗收斂成可定位的 corpus。

重點判斷：

- fuzz target 是否足夠小，能對準單一責任
- corpus 是否持續收斂，而不是只累積雜訊
- crash reproduction 是否可重播到同一條路徑
- 修補後是否回寫成 regression test

## 案例對照

- [Google](/backend/06-reliability/cases/google/_index.md)：大量基礎元件需要持續 fuzz 來補邊界盲區。
- [Stripe](/backend/06-reliability/cases/stripe/_index.md)：API / serialization 邊界需要穩定的輸入探索。
- [GitHub](/backend/08-incident-response/cases/github/_index.md)：schema 或 webhook 類邊界適合用 fuzz 補回歸。

## 下一步路由

- 06.10 contract testing：把已知契約邊界收進 CI
- 06.16 test data：把 fuzz 找到的案例沉澱成 seed
- 08.9 事故型態庫：把 recurrent crash pattern 抽成型態

## 判讀訊號

- fuzz corpus 從未更新、覆蓋率停滯
- crash 復現靠人工 minimization、無自動化
- fuzz 找到 bug 沒回灌成 regression test
- input boundary 無 spec、fuzz 範圍模糊
- production 出 crash 但 fuzz 沒抓到、信心錯配

## 交接路由

- 06.10 contract testing：schema fuzz 跟契約驗證互補
