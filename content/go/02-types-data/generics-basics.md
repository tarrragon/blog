---
title: "2.7 generics 入門：型別參數與約束"
date: 2026-04-22
description: "用最小範圍理解 Go generics 的適用場景"
weight: 7
---

generics 的核心用途是讓重複的型別安全邏輯可以被抽出來。Go 的泛型適合資料結構、集合 helper、測試工具與少量演算法；一般 application flow 仍應優先使用具體型別與小介面。

## 預計補充內容

這些型別系統邊界會在下列章節展開：

- [Go 入門：interface：用行為定義依賴](interfaces/)：先看 interface 與具體型別的邊界，才能判斷什麼情況值得引入 generics。
- [Go 入門：table-driven test](../../go/05-error-testing/table-driven-test/)：泛型 helper 常常是給測試工具用的，這裡會看到它怎麼支撐重複案例。
- [Go 進階：資料結構與 allocation 壓力](../../go-advanced/03-runtime-profiling/allocation/)：當泛型影響配置與熱路徑時，才需要往 runtime 成本那層看。

## 與 Backend 教材的分工

本章只處理 Go 型別系統。資料庫 row mapping、serialization schema 或外部 protocol code generation 會放在 Backend 或實戰章節中討論。

## 和 Go 教材的關係

這一章承接的是集合操作、型別約束與泛型應用；如果你要先回看語言教材，可以讀：

- [Go：slice 與 map](slices-maps/)
- [Go：interface：用行為定義依賴](interfaces/)
- [Go：指標與資料複製邊界](pointers-copy/)
- [Go：狀態管理的安全邊界](../07-refactoring/state-boundary/)
