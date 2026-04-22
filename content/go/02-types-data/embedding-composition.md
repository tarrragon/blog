---
title: "2.6 struct embedding 與組合式設計"
date: 2026-04-22
description: "理解 Go 的 embedding、方法提升與組合邊界"
weight: 6
---

struct embedding 的核心用途是組合既有能力。它可以讓欄位與方法被提升到外層型別，但設計重點仍然是清楚表達責任，而不是模擬繼承階層。

## 預計補充內容

1. anonymous field 與一般 named field 的差異。
2. 欄位提升與方法提升如何影響呼叫端。
3. embedding interface 和 embedding struct 的不同語意。
4. 何時使用 embedding，何時改用明確欄位。
5. embedding 在 handler、logger、config、test helper 中的常見用法。

## 與其他章節的關係

本章承接 [組合優先：小介面與明確依賴](../00-philosophy/composition/) 與 [interface：用行為定義依賴](interfaces/)，後續會連到 [composition root 與依賴組裝](../07-refactoring/composition-root/)。
