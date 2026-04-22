---
title: "2.7 generics 入門：型別參數與約束"
date: 2026-04-22
description: "用最小範圍理解 Go generics 的適用場景"
weight: 7
---

generics 的核心用途是讓重複的型別安全邏輯可以被抽出來。Go 的泛型適合資料結構、集合 helper、測試工具與少量演算法；一般 application flow 仍應優先使用具體型別與小介面。

## 預計補充內容

1. 型別參數的基本語法。
2. constraint 如何限制可接受型別。
3. generic function 與 generic type 的使用場景。
4. `any`、`comparable` 與自訂 constraint。
5. application code 中過度泛型化的判斷方式。

## 與 Backend 教材的分工

本章只處理 Go 型別系統。資料庫 row mapping、serialization schema 或外部 protocol code generation 會放在 Backend 或實戰章節中討論。
