---
title: "Cohesion（內聚）"
date: 2026-10-19
description: "要判斷一個模組裡的元素放在一起的理由夠不夠強、或讀到「高內聚、低耦合」想知道內聚量的是什麼時：內聚是模組內部元素彼此相關的程度，依放在一起的理由分成由弱到強的幾種"
weight: 6
tags: ["design-principles", "knowledge-card", "cohesion", "structured-design"]
---

Cohesion（內聚）是一個模組內部的元素彼此相關、應該放在一起的程度。這裡的模組泛指任何有對外介面的程式單位：函式、類別、檔案或套件。這個詞由 Larry Constantine 在 1960 年代後期的結構化設計（structured design）裡提出，1974 年 Stevens、Myers 與 Constantine 在 IBM Systems Journal 的〈Structured Design〉一文把它與 [Coupling（耦合）](/design-principles/knowledge-cards/coupling/) 一起寫成模組設計的兩個衡量標準：內聚量模組內部，耦合量模組之間。內聚與 [Single Responsibility Principle（單一職責原則）](/design-principles/knowledge-cards/single-responsibility-principle/) 衡量的是同一件事——哪些元素該放在一起——而判斷依據不同：內聚的傳統定義看元素在功能上是否相關，單一職責原則看元素是否因為同一個理由改變。

## 概念位置

內聚依「這些元素為什麼放在一起」分成幾種。由弱到強的排序依據是放在一起的理由與模組那件工作的關係有多緊：偶然內聚的元素之間完全無關，功能內聚的每個元素都屬於同一件工作。

- **偶然內聚（coincidental）**：放在一起沒有任何理由，例如一個什麼都放的 `utils` 模組。
- **邏輯內聚（logical）**：元素屬於同一個類別，例如所有輸入處理都放在一起，而每一種輸入的處理彼此無關。
- **時間內聚（temporal）**：元素在同一個時間點執行，例如程式啟動時要做的所有初始化。
- **程序內聚（procedural）**：元素總是依某個順序執行。
- **通訊內聚（communicational）**：元素操作同一份資料。
- **循序內聚（sequential）**：一個元素的輸出是下一個元素的輸入。
- **功能內聚（functional）**：所有元素一起完成一件定義明確的工作。

Robert C. Martin 在《Agile Software Development》的單一職責那一章寫明，這條原則在 Tom DeMarco 與 Meilir Page-Jones 的著作裡已有描述，「They called it cohesion」，他們把內聚定義成模組元素在功能上的相關程度；Martin 在那一章把內聚的意思稍微移動，改成和「讓模組改變的力量」相關。兩種判斷用到的資訊不同：功能相關看程式碼在做什麼，[單一職責原則](/design-principles/knowledge-cards/single-responsibility-principle/)看誰會要求它改變。兩種判斷可能給出不同結果：一個模組完成一件定義明確的工作，屬於功能內聚；如果那件工作的規則由兩個業務職能各管一半，它仍然有兩個改變的理由。決定要不要拆時以改變的理由為準，內聚的層級用來描述元素放在一起的理由屬於哪一種。

## 可觀察訊號與例子

低內聚的模組有幾個可以觀察到的訊號：

- **名字說不出它做什麼**：`utils`、`helpers`、`common`、`misc` 這類名字通常代表偶然內聚，裡面的函式彼此沒有關係，只是沒有更好的去處。
- **改一處要讀整個模組，而讀到的大部分與這次修改無關**：模組裡混了幾群互不相關的元素。
- **修改紀錄裡同一個模組被不相干的需求輪流修改**：這是內聚不足在版本歷史上的樣子，也就是 [Divergent Change（發散式變更）](/design-principles/knowledge-cards/divergent-change/)。

反方向的錯誤是把同一件工作拆到好幾個模組，每個模組單獨看都很小，而那件工作的每一次修改都要同時改它們，這是 [Shotgun Surgery（散彈式修改）](/design-principles/knowledge-cards/shotgun-surgery/)。

## 設計責任

提高內聚的設計責任是讓模組裡的每個元素都因為同一個理由放在這裡，理由指的是改變的理由：誰會要求這個元素改變。判斷問句是：逐一寫出模組裡每個元素會被哪一個需求來源要求修改；同一個來源的那一群留下，屬於別的來源的、或寫得出的原因只有「沒有別的地方放」的，移到它所屬的模組。移完之後回頭看 [Coupling（耦合）](/design-principles/knowledge-cards/coupling/)：移出去的元素如果仍然大量讀寫原模組的內部資料、而且每次修改都要和原模組一起改，那個元素與原模組本來就屬於同一個模組，移出去的判斷錯了。
