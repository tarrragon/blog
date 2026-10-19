---
title: "Knowledge Cards"
tags: ["前置知識卡片", "Knowledge Cards"]
date: 2026-10-19
description: "軟體設計原則的術語卡片：模組邊界怎麼畫、哪些程式碼該放在一起"
weight: -1
---

本模組的知識卡片收錄語言無關的設計原則與它們對應的程式碼壞味道。各語言模組的文章遇到這些術語時連到這裡，語言特定的寫法留在各語言模組。

## 模組邊界

| 卡片                                                                                                                   | 核心問題                                                             |
| ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| [Single Responsibility Principle（單一職責原則）](/design-principles/knowledge-cards/single-responsibility-principle/) | 職責的定義是改變的理由，理由對到提出變更的人——不是「只做一件事」     |
| [Divergent Change（發散式變更）](/design-principles/knowledge-cards/divergent-change/)                                 | 多個不相干的需求改同一個模組——違反單一職責在修改紀錄上的樣子         |
| [Shotgun Surgery（散彈式修改）](/design-principles/knowledge-cards/shotgun-surgery/)                                   | 一個需求要改很多個模組——同一個理由被拆散，拆檔切過頭的結果           |
| [Open-Closed Principle（開放封閉原則）](/design-principles/knowledge-cards/open-closed-principle/)                     | 對選定的那一類變更封閉——使用端只依賴固定的抽象，封閉要有選擇         |
| [DRY（Don't Repeat Yourself）](/design-principles/knowledge-cards/dry-principle/)                                      | 每一份知識只有一個權威來源——字面相同而理由不同的程式碼不是同一份知識 |
| [Cohesion（內聚）](/design-principles/knowledge-cards/cohesion/)                                                       | 模組內部元素彼此相關的程度——依放在一起的理由分成由弱到強的幾種       |
| [Coupling（耦合）](/design-principles/knowledge-cards/coupling/)                                                       | 模組之間互相依賴的程度——依兩個模組共享什麼分成由強到弱的幾種         |
