---
title: "Knowledge Cards"
tags: ["前置知識卡片", "Knowledge Cards"]
date: 2026-10-19
description: "軟體設計原則的術語卡片：模組邊界怎麼畫、哪些程式碼該放在一起"
weight: -1
---

本模組的知識卡片收錄語言無關的設計原則與它們對應的程式碼壞味道。各語言模組的文章遇到這些術語時連到這裡，語言特定的寫法留在各語言模組。

## 模組邊界

| 卡片                                                                                                                   | 核心問題                                                         |
| ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [Single Responsibility Principle（單一職責原則）](/design-principles/knowledge-cards/single-responsibility-principle/) | 職責的定義是改變的理由，理由對到提出變更的人——不是「只做一件事」 |
| [Divergent Change（發散式變更）](/design-principles/knowledge-cards/divergent-change/)                                 | 多個不相干的需求改同一個模組——違反單一職責在修改紀錄上的樣子     |
| [Shotgun Surgery（散彈式修改）](/design-principles/knowledge-cards/shotgun-surgery/)                                   | 一個需求要改很多個模組——同一個理由被拆散，拆檔切過頭的結果       |
