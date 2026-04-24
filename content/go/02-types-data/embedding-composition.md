---
title: "2.6 struct embedding 與組合式設計"
date: 2026-04-22
description: "理解 Go 的 embedding、方法提升與組合邊界"
weight: 6
---

struct embedding 的核心用途是組合既有能力。它可以讓欄位與方法被提升到外層型別，但設計重點仍然是清楚表達責任，而不是模擬繼承階層。

## 預計補充內容

這些組合邊界會在下列章節展開：

- [Go 入門：組合優先：小介面與明確依賴](../../00-philosophy/composition/)：先理解 Go 為什麼偏好組合，才能判斷 embedding 是在表達能力，還是在模仿繼承。
- [Go 入門：interface：用行為定義依賴](../interfaces/)：這裡會把 embedding 和 interface 的責任分開，避免欄位提升變成隱性耦合。
- [Go 進階：composition root 與依賴組裝](../../07-refactoring/composition-root/)：當組合開始影響 wiring 時，就要看依賴是在哪一層被建立的。

## 與其他章節的關係

本章承接 [組合優先：小介面與明確依賴](../../00-philosophy/composition/) 與 [interface：用行為定義依賴](../interfaces/)，後續會連到 [composition root 與依賴組裝](../../07-refactoring/composition-root/)。

## 和 Go 教材的關係

這一章承接的是組合、interface 與依賴組裝；如果你要先回看語言教材，可以讀：

- [Go：組合優先：小介面與明確依賴](../../00-philosophy/composition/)
- [Go：interface：用行為定義依賴](../interfaces/)
- [Go：composition root 與依賴組裝](../../07-refactoring/composition-root/)
- [Go：以 domain 重新整理 package](../../07-refactoring/domain-packages/)
