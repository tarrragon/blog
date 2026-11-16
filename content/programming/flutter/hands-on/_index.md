---
title: "Flutter 的實作紀錄"
date: 2026-11-16
description: "想照著做一次 Flutter 的量測或操作、看每一步的程式碼與實際輸出時讀：渲染管線 frame 數的量測、每幀柵格化成本的量測。"
weight: 99
tags: ["flutter", "hands-on"]
---

Flutter 模組的實作文章：讀者照著做就能重做一次的量測與操作，每一篇記下環境、程式碼、輸出與讀法。觀念層的推導在模組的章節文章與其他模組的概念文章，各篇開場連過去。瀏覽器上同一類的量測（canvas 動畫的重畫上限），放在 UX 模組六的[實作紀錄](/ux-design/06-interaction-feedback/hands-on/)。

## 章節

| 文章                                                                                                                                                              | 操作與量到的值                                                                                                                                                                                                                                        | 連回的概念文章                                                                                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Flutter 裝飾性動畫的驅動方式比較：AnimationController、Ticker、Timer 與事件觸發的 frame 數與 CPU 量測](/programming/flutter/hands-on/ambient-motion-frame-cost/) | 兩個像素場景（簡化樹；橡樹加松樹）各自以不動、AnimationController、Ticker 低頻換姿勢、Timer、事件觸發幾種方式跑，量 framework frame、raster frame、paint、柵格化時間與 CPU；144 Hz 螢幕上 Ticker 版本仍每秒柵格化 144 次                              | [App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)                                                                                     |
| [Flutter 像素場景的每幀柵格化成本：紋理圖集、背景點陣圖、獨立圖層與不 rebuild 的改法與量測](/programming/flutter/hands-on/pixel-scene-texture-atlas-frame-cost/)  | 同一個橡樹加松樹場景，葉叢改用 drawRawAtlas 畫紋理圖集、背景改成點陣圖並獨立成圖層、換姿勢不 rebuild，在 flutter test 裡逐位元組比對畫面，量五種驅動方式的每幀柵格化、build 與 CPU；144 Hz 螢幕上每幀柵格化降到原本的約五分之一到十六分之一，幀數不變 | [App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)；判斷條件在 [Texture Atlas](/programming/flutter/knowledge-cards/texture-atlas/) 卡 |
