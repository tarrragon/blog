---
title: "Clean Architecture 實作指引"
date: 2026-03-04
draft: false
description: "我們在 AI 協作開發中引入 Clean Architecture 作為任務分派的核心判斷框架。這篇文章整理了四層架構的設計順序、實作順序，以及我們實際執行時的關鍵檢查點。"
tags: ["AI協作心得","方法論"]
---

定義敏捷開發方法論時，我們需要一個明確的判斷基準：哪些任務屬於同一層？哪些必須依序完成？哪些可以並行？

我們選擇了 Clean Architecture。它不只是架構模式，更是一套「責任分層」語言，讓我們和 AI 代理人都能用同一套詞彙討論誰該負責哪個部分、什麼時候可以動手。

<!--more-->

## 核心原則：依賴只能由外向內

Clean Architecture 最核心的一句話是「依賴只能由外向內」。內層不知道外層的存在，外層依賴內層定義的介面。業務邏輯因此得以獨立，換資料庫、換 UI 框架都不需要動到核心規則。

架構由內到外分為四層：

**Entities（核心業務規則）** 封裝核心業務概念，例如書籍、訂單、使用者。定義實體屬性和業務不變量的驗證，不依賴任何框架或資料庫。

**Use Cases（應用業務邏輯）** 協調 Entities 之間的互動，定義系統功能。同時定義 Input Port、Output Port、Repository Port，只依賴 Entities 和這些自己定義的介面。

**Interface Adapters（介面轉接層）** 橋接業務邏輯和外部技術。Controller 接收外部請求並轉換為 Use Case 輸入，Presenter 格式化 Use Case 輸出，Repository 實作在這一層開始成形。

**Frameworks & Drivers（框架與外部系統）** 包含所有技術細節——資料庫、UI 框架、第三方服務。可以隨時替換，完全不影響內層。

## 依賴反轉原則（DIP）讓這一切成立

Use Case 需要存取資料，但不能直接依賴 SQLite。正確做法是：在 Use Cases 層定義 Repository Port（抽象介面），Use Case 只依賴這個介面。真正的資料庫實作在最外層，它去實作這個介面。

依賴方向因此被反轉：資料庫實作依賴 Use Case 定義的介面，而非 Use Case 依賴資料庫。最後在 Composition Root 把具體實作注入進去，這就是依賴注入的本質。

## 設計從內到外，實作從外到內

這是我們在 AI 協作中最重要的一個認知。

**設計階段由內到外：**

1. 設計 Entities：識別業務實體、定義 Value Objects（ISBN、Title 這類有驗證規則的值物件），在建構子中驗證業務不變量。
2. 設計 Use Cases：定義 Input Port、Output Port、Repository Port。確定業務邏輯需要什麼，但不決定如何實作。
3. 設計 Interface Adapters：Controller 如何轉換外部請求、Presenter 如何格式化輸出。
4. 設計 Frameworks：選擇資料庫方案，實作 Repository。到這步才碰具體技術。

**實作階段由外到內：**

1. 先定義所有 Ports。在寫任何實作之前，確立 Use Case 介面和 Repository 介面，這是系統的骨架。
2. 外層用 Mock 介面開發和測試。Controller 在 Use Case 還沒真正實作前就能測試，因為它依賴的是抽象介面。
3. 補完內層實作：Interactor 實作業務邏輯，Repository 存取真正的資料庫。
4. Composition Root 組裝依賴注入，系統就能真正執行。

設計階段確保業務邏輯不被技術細節污染，實作階段讓每一層都能獨立開發和測試。

## 驗證架構是否正確

每個 Phase 完成後，我們對照以下幾個方向確認。

**依賴方向：**

- Entities 沒有任何外層的 import
- Use Cases 只 import Entities 和自己定義的介面
- Frameworks 層實作的是 Interface Adapters 定義的介面

**介面契約：**

- Repository Port 定義在 Use Cases 層（不是 Frameworks 層）
- Repository 回傳的是 Entity 而不是資料庫 DTO
- Input/Output Port 沒有洩漏框架的型別（例如 HTTP Request、SQLite Row）

**業務邏輯位置：**

- 業務不變量的驗證在 Entity 建構子
- 應用層邏輯在 Use Case Interactor
- Controller 只負責轉換和呼叫，不包含業務判斷

**Interface-Driven Development：**

- 所有 Ports 在設計階段就定義完成
- 外層真的用 Mock 介面在開發測試
- 組裝注入在 Composition Root 統一處理

## 為什麼這對 AI 協作特別有價值

傳統開發中，架構邊界的維護依賴工程師的經驗，容易在壓力下妥協。AI 代理人則非常適合執行有明確規則的框架——規則夠清楚，它就能持續一致地遵守。

分層邊界就是這樣的規則。告訴代理人「這個 class 屬於 Use Cases 層，所以不能 import 任何 Framework 層的東西」，代理人就能機械性地驗證和維護這個邊界。

這套語言也讓任務拆分有了清楚的依據。「這個功能需要修改 Entity 和 Use Case，但不涉及 Repository 實作」是一個清楚的任務描述，對應到具體的修改範圍，不會模糊。

從實際經驗來看，引入 Clean Architecture 之後，AI 的實作結果更容易預測，測試覆蓋率更容易維持，架構審查也更有效率。代價是設計階段需要更多前置思考，但這個投資通常值得。
