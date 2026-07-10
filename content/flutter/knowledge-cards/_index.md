---
title: "Knowledge Cards"
tags: ["前置知識卡片", "Knowledge Cards"]
date: 2026-07-10
description: "Flutter 與 Dart 教材引用的語言機制與生態工具：用原子化卡片建立共同語言"
weight: -1
---

本模組的知識卡片把 Dart 語言機制與 Flutter 生態工具的高密度術語拆成可獨立閱讀的概念索引。work-log 文章遇到語言特有機制時連到對應卡片；卡片先回答概念本質、再放設計責任。本模組的卡片跟 [DDD 知識卡](/ddd/knowledge-cards/) 有交叉引用——Dart 的語言機制如何影響領域模型設計是兩個模組的交集。

## Dart 語言機制

| 卡片                                                       | 核心問題                                              |
| ---------------------------------------------------------- | ----------------------------------------------------- |
| [copyWith](/flutter/knowledge-cards/copywith/)             | 逐欄位覆寫方法——對資料袋正確、對 entity 是逃生口      |
| [freezed](/flutter/knowledge-cards/freezed/)               | immutable data class 生成器——把 copyWith 推成預設路徑 |
| [Extension Type](/flutter/knowledge-cards/extension-type/) | Dart 3 零成本包裝型別——語意封閉的實作載體             |
