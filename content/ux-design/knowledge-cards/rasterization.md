---
title: "Rasterization（柵格化）"
date: 2026-11-17
description: "讀到 raster 執行緒、rasterDuration、柵格化或光柵化，要知道它是渲染的哪一段工作、跑在 GPU 還是 CPU 上，或要估一個畫面每一幀的柵格化成本、判斷剔除這類最佳化有沒有畫錯時讀"
weight: 14
tags: ["ux-design", "knowledge-card", "interaction-feedback", "rendering"]
---

Rasterization（柵格化）是把用幾何描述的圖形（路徑、多邊形、字形、圖片的變形）轉成一格一格離散顏色值的工作：對畫面上的每一格判斷圖形蓋到它多少，決定那一格填什麼顏色。格子通常是螢幕的像素；終端機動畫的格子是一個字元格，程式要決定每一格畫哪個字元、用什麼顏色。其他中文資料常寫作「光柵化」，指的是同一件事；本站用「柵格化」，因為「光柵」在物理光學裡另指繞射光柵。在按需重繪的 UI 框架裡，柵格化是渲染管線每產生一幀都要跑的一段（[On-demand Rendering（按需重繪）](/ux-design/knowledge-cards/on-demand-rendering/)），排在重新計算版面、繪製與合成圖層之後；一秒跑幾次由排幀的次數決定（[VSync（垂直同步）](/ux-design/knowledge-cards/vsync/)）。

## 跟其他概念的關係

柵格化跑在哪一個處理器上，依框架與情境而定，量成本時要先分清楚：

- **UI 框架交給 GPU 做**：Flutter 的 raster 執行緒把 UI 執行緒產出的圖層樹交給 GPU 柵格化（[Flutter 的執行緒模型](/programming/flutter/knowledge-cards/flutter-thread-model/)），每一幀花多久記在 [FrameTiming](/programming/flutter/knowledge-cards/frame-timing/) 的 `rasterDuration`；瀏覽器把 canvas 與頁面的圖層交給 GPU 程序。這一段的時間不在 Dart 或 JavaScript 的 profile 裡，量程式自己的執行時間看不到它。
- **在 CPU 上做**：沒有 GPU 的測試環境（`flutter test` 畫出的圖，一般推論是軟體柵格化，本站沒有查證），以及程式自己實作的柵格化。終端機的 ASCII 動畫自己決定每一個字元格畫什麼，這一段是程式自己的運算，出現在它的 CPU profile 裡。

每一幀柵格化的工作量取決於要填的格子數與每一格的取樣次數：蓋住大片畫面的圖形、模糊與陰影、一格取好幾個點的反鋸齒都讓工作量變大。減少這段工作的做法有兩類：減少每一幀要畫的內容（預先畫成點陣圖、拼成 [Texture Atlas](/programming/flutter/knowledge-cards/texture-atlas/)、用 [RepaintBoundary](/programming/flutter/knowledge-cards/repaint-boundary/) 讓沒變的部分不重畫），以及跳過確定蓋不到的格子（剔除，culling）。每秒柵格化幾次等於渲染管線每秒產生幾幀，由要求下一幀的驅動器決定（[On-demand Rendering（按需重繪）](/ux-design/knowledge-cards/on-demand-rendering/)）；每一幀的工作量與每秒的次數相乘，才是柵格化的總成本。

## 可觀察訊號與例子

- 一個終端機 ASCII 鯊魚動畫原本對每條鯊魚外框裡的每一個字元格取 5 個點，每個點跟脊椎的 19 段逐一比對距離。用 Node 的 `--cpu-prof` 錄下來，程式忙碌的時間裡約七成在這段柵格化，模擬全部的魚與鯊魚約一成（〔[量終端機動畫程式的 CPU](/work-log/terminal-animation-cpu-measurement/)〕）。改法替每段脊椎算出「離它多遠還可能落在鯊魚身上」的上限，確定落空的格子不取樣。
- Flutter 桌面版的像素場景裡，`Timer` 驅動的版本幀數約是每個 vsync 排幀版本的十四分之一，CPU 取樣卻約是五分之一：低幀率時平均每一幀的柵格化時間比較長。同一個場景改成預先畫好的點陣圖、每一幀要柵格化的工作變少之後（同時改了另外幾處繪製方式，一起量），CPU 的比例約十分之一，更接近幀數的比例（〔[Flutter 裝飾性動畫的驅動方式比較](/programming/flutter/hands-on/ambient-motion-frame-cost/)〕）。

## 判斷條件與後果

- **量到的 CPU 或幀時間偏高、而程式自己的 profile 看起來很乾淨時**，耗時的工作可能是交給 GPU 的柵格化，程式碼的最佳化影響不到它；要減少的是每一幀要柵格化的內容，或排幀的次數。量整個行程的 CPU 時，各執行緒的時間加在一起，分不出是哪一段；Flutter 用 `rasterDuration`，瀏覽器加總 GPU 程序的 CPU 或用 Performance 面板。
- **柵格化是程式自己在 CPU 上做的時候**，它跟模擬、組輸出一樣出現在 profile 裡，先錄 profile 再決定改哪裡：讀程式碼時容易以為模擬最貴。
- **改柵格化只為了變快（剔除、快取、改用點陣圖），宣稱畫面不變時**，畫錯的格子只在特定的形狀與位置出現，看幾幀畫面確認不了。要拿同一組輸入讓改之前與改之後的版本各畫一次、逐格比對；同一次改動刻意改了畫面時，參照換成同一個新行為、關掉剔除的版本（〔[效能最佳化的正確性要拿一份產生同樣畫面的參照實作逐格比](/report/optimization-equivalence-needs-a-reference-of-the-same-behavior/)〕）。
