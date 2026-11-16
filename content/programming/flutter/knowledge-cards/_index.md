---
title: "Knowledge Cards"
tags: ["前置知識卡片", "Knowledge Cards"]
date: 2026-07-10
description: "Flutter 與 Dart 教材引用的語言機制與生態工具：用原子化卡片建立共同語言"
weight: -1
aliases: ["/flutter/knowledge-cards/"]
---

本模組的知識卡片把 Dart 語言機制與 Flutter 生態工具的高密度術語拆成可獨立閱讀的概念索引。work-log 文章遇到語言特有機制時連到對應卡片；卡片先回答概念本質、再寫判斷條件與後果。本模組的卡片跟 [DDD 知識卡](/software-design/ddd/knowledge-cards/) 有交叉引用——Dart 的語言機制如何影響領域模型設計是兩個模組的交集。

## Dart 語言機制

| 卡片                                                                   | 核心問題                                              |
| ---------------------------------------------------------------------- | ----------------------------------------------------- |
| [copyWith](/programming/flutter/knowledge-cards/copywith/)             | 逐欄位覆寫方法——對資料袋正確、對 entity 是逃生口      |
| [freezed](/programming/flutter/knowledge-cards/freezed/)               | immutable data class 生成器——把 copyWith 推成預設路徑 |
| [Extension Type](/programming/flutter/knowledge-cards/extension-type/) | Dart 3 零成本包裝型別——語意封閉的實作載體             |

## Flutter 渲染與效能量測

| 卡片                                                                                                 | 核心問題                                                          |
| ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [FrameTiming](/programming/flutter/knowledge-cards/frame-timing/)                                    | 每一幀的 build 與柵格化時間——掉幀看哪兩個值、預算依螢幕更新率算   |
| [Flutter Thread Model](/programming/flutter/knowledge-cards/flutter-thread-model/)                   | UI、raster 與平台執行緒——耗時的工作落在哪一條、合併執行緒的影響   |
| [Picture](/programming/flutter/knowledge-cards/picture/)                                             | 錄好的繪圖指令——重播省下的是 UI 執行緒，柵格化照做                |
| [RepaintBoundary](/programming/flutter/knowledge-cards/repaint-boundary/)                            | 子樹獨立的繪圖紀錄——隔開重畫，不減少排幀次數                      |
| [Texture Atlas](/programming/flutter/knowledge-cards/texture-atlas/)                                 | 一批小圖拼成一張大圖——每一幀的柵格化只剩取樣與貼上                |
| [Widget、Element 與 RenderObject](/programming/flutter/knowledge-cards/widget-element-renderobject/) | 畫面的設定、實例與繪製三層——rebuild、layout、paint 各自標記哪一層 |
