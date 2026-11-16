---
title: "RepaintBoundary（重畫邊界）"
tags: ["flutter", "knowledge-card", "rendering", "performance"]
date: 2026-11-16
description: "畫面上一小塊一直在動、想知道它會不會連帶讓整個畫面重畫，或考慮在哪裡包 RepaintBoundary、包了之後省下什麼時讀"
weight: 7
---

`RepaintBoundary` 是一個 widget，它讓子樹有一份獨立的繪圖紀錄：Flutter 的 `RenderRepaintBoundary` 文件寫的是替子樹建立一份分開的 display list（錄好的繪圖指令，見 [Picture](/programming/flutter/knowledge-cards/picture/)）。子樹裡的元件要求重畫時，重畫只往上傳到最近的邊界為止，只重錄邊界裡面那一份；邊界外面要重畫而子樹沒有變時，直接沿用子樹上一次錄好的那一份。

## 跟其他概念的關係

`RepaintBoundary` 隔開的是 paint 這一段，也就是 UI 執行緒上錄繪圖指令的工作，記在 [FrameTiming](/programming/flutter/knowledge-cards/frame-timing/) 的 `buildDuration`。包了它，畫面要不要排一幀照舊由驅動器與重建的要求決定：子樹裡一個每個 vsync 都觸發的動畫，照樣讓整個畫面每個 vsync 產生一幀，合成與柵格化照整個畫面計（[按需重繪](/ux-design/knowledge-cards/on-demand-rendering/)）。

- **`RepaintBoundary`** 指 framework 自動替子樹保留上一次的繪圖紀錄，子樹沒變就沿用。
- **手動錄 [Picture](/programming/flutter/knowledge-cards/picture/)** 指開發者自己決定錄哪一段、什麼時候重錄，子樹每一幀都變位置時也能重播同一份內容。

`ListView`、`GridView` 的 builder 預設替每一個項目包一層 `RepaintBoundary`（`addRepaintBoundaries` 參數）。

## 可觀察訊號與例子

Flutter 的 `RenderRepaintBoundary` 文件舉的例子是郵件 App：未讀數與郵件清單在新郵件進來時一起變，只把其中一個包進邊界時整個 App 每次都重畫，兩個都包時只有那兩塊重畫。要看邊界有沒有用，debug 模式下打開 `debugRepaintRainbowEnabled`（每一次重畫換一個外框顏色），或呼叫 `debugDumpRenderTree()`，每一個 `RenderRepaintBoundary` 會印出它省下重畫與沒省下的次數比例（`debugAsymmetricPaintCount` 與 `debugSymmetricPaintCount`）。

## 判斷條件與後果

- **子樹重畫的時機跟周圍不同時**（一個一直在轉的圖示放在靜止的頁面上、一塊每秒更新的數字旁邊是大量靜態內容），包一層邊界，周圍不必跟著重錄，省下的是 UI 執行緒的 paint 時間。
- **子樹跟周圍總是一起重畫時**，邊界兩邊每一次都要重錄，省不到時間，多出一個圖層的管理成本與記憶體；`debugDumpRenderTree()` 印出的比例裡，沒省下的次數佔多數就是這種情形。
- **瓶頸在排幀次數或柵格化時**，`RepaintBoundary` 不減少畫面產生幾幀，也不保證減少柵格化的工作；要省這兩項，得讓驅動器少排幀，或減少每一幀要柵格化的內容（[Flutter Thread Model（Flutter 的執行緒模型）](/programming/flutter/knowledge-cards/flutter-thread-model/)）；很多個內容固定的小圖塊，可以預先畫成點陣圖、拼成 [Texture Atlas](/programming/flutter/knowledge-cards/texture-atlas/)。
