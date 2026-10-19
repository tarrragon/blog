---
title: "Shotgun Surgery（散彈式修改）"
date: 2026-10-19
description: "每做一個小變更都要同時改好幾個檔案、漏改一處就出錯，或依行數拆完檔之後同一個主題的修改散到好幾份時：這是同一個改變理由被拆散到多個模組的壞味道"
weight: 3
tags: ["design-principles", "knowledge-card", "code-smell", "refactoring"]
---

Shotgun Surgery（散彈式修改，其他中文資料常寫作「霰彈式修改」或「散彈槍手術」）是 Martin Fowler 在《Refactoring》列出的程式碼壞味道：每做一種變更，都要在很多個模組裡各做一點小修改。它是 [Divergent Change（發散式變更）](/design-principles/knowledge-cards/divergent-change/) 的反方向——那一種是多個不相干的需求改同一個模組，這一種是一個需求要改多個模組。依 [Single Responsibility Principle（單一職責原則）](/design-principles/knowledge-cards/single-responsibility-principle/) 的說法，這是把因同一個理由改變的程式碼拆散了。

## 概念位置

[單一職責原則](/design-principles/knowledge-cards/single-responsibility-principle/)有兩句方向相反的指示：把因不同理由改變的程式碼分開，把因同一個理由改變的程式碼放在一起。只照前一句切，最常出現的結果就是 Shotgun Surgery——切的人看到「做了好幾件事」就切開，沒有檢查那幾件事是不是總是一起改。它與 [Divergent Change](/design-principles/knowledge-cards/divergent-change/) 都是改變的理由與模組沒有一對一對應的情形，修正方向相反，所以拆檔之後要兩個方向都檢查。

## 可觀察訊號與例子

Fowler 指出這種壞味道的主要風險是漏改：變更散在很多地方時，很難全部找到，漏掉一處就留下不一致。常見的形態有三種：

- **依行數拆檔**：把一個 900 行、只屬於同一個需求連續演進的解析器切成三份，之後同一個主題的每一次修改都要同時改三個檔。行數判斷與修改競爭判斷在這種檔案上給出相反的結論，對照在[從修改競爭判斷拆檔](/python/07-refactoring/file-split-by-contention/)。
- **新增一個欄位要改每一層**：欄位定義、資料存取、序列化、畫面各在一個檔案，加一個欄位就要依序改過每一層。這種情形有時是分層架構刻意付的成本，判斷時看這幾層是不是總是一起改、而且由同一個理由驅動。
- **同一段規則複製在好幾處**：規則改了，每一份複本都要找出來改。這與 DRY 處理的是同一件事，Python 的寫法在[DRY 原則](/python/07-refactoring/dry-principle/)。

站內偵測規則與修正範例（Extract Interface、Introduce Facade）在 [Code Smell 檢查清單](/record/code_smell/)。

## 設計責任

修正 Shotgun Surgery 的方向是提高[內聚](/design-principles/knowledge-cards/cohesion/)，把總是一起改的函式與資料收回同一個模組：用 Move Function、Move Field 把散落的函式與資料移到一處，散開的那幾個模組若只剩空殼就用 Inline Class 併回去。判斷問句是：最近幾次同一類變更，各改了哪幾個檔案；每次都改同一組檔案，那一組就是應該合併的候選。合併之後回頭檢查另一個方向：新的模組是否因此開始被不相干的需求修改，是的話就併過頭了，變成 [Divergent Change](/design-principles/knowledge-cards/divergent-change/)。
