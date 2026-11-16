---
title: "Widget、Element 與 RenderObject（Flutter 的三棵樹）"
tags: ["flutter", "knowledge-card", "rendering", "performance"]
date: 2026-11-17
description: "想知道 setState 之後 framework 重做了哪些工作、rebuild 跟重畫差在哪，或考慮把會變的值交給 CustomPainter 的 repaint 參數、不再呼叫 setState 時讀"
weight: 9
---

Flutter 用三種物件組成畫面，每一種各自連成一棵樹。**Widget** 是畫面的設定：建構之後不能修改，`build` 方法每執行一次就產生一批新的 widget。**Element** 是某一個 widget 在樹上某個位置的實例：它在 rebuild 之間保留下來，`StatefulWidget` 的 `State` 物件由它持有，`build` 方法收到的 `BuildContext` 就是它。**RenderObject** 負責 layout（決定大小與位置）、paint（錄繪圖指令，見 [Picture](/programming/flutter/knowledge-cards/picture/)）與點擊判定；它由 `RenderObjectWidget` 這一類 widget 建立（`CustomPaint`、`SizedBox`、`RepaintBoundary` 都屬於這一類），跟 element 一樣在 rebuild 之間保留下來。

rebuild 時，element 拿新的 widget 跟上一次的比：同一個物件時，整棵子樹不 rebuild，`const` 建構的 widget 每次都是同一個物件，所以落在這一種；型別與 `key` 都相同時（`Widget.canUpdate`），element 留著，換上新的 widget，對應的 render object 也留著，只把新 widget 的欄位寫進去（`updateRenderObject`）；型別或 `key` 不同時，舊的 element 與 render object 拆掉，重新建一組。

## 跟其他概念的關係

一幀裡 UI 執行緒依序做 build、layout、paint 與合成圖層樹，四段都記在 [FrameTiming](/programming/flutter/knowledge-cards/frame-timing/) 的 `buildDuration`，做完之後交給 raster 執行緒柵格化（[Flutter Thread Model（Flutter 的執行緒模型）](/programming/flutter/knowledge-cards/flutter-thread-model/)）。三段各有自己的標記，標記之後都會要求排下一幀：

- **要 rebuild**：`setState` 把那個 `State` 所屬的 element 標成要 rebuild（`markNeedsBuild`）。下一幀的 build 重新執行它的 `build` 方法，再依上面的比對規則往下更新整棵子樹。
- **要重新 layout**：render object 的大小或排版相關的欄位改變時呼叫 `markNeedsLayout`，下一幀從最近的 relayout boundary 往下重算大小與位置。relayout boundary 是父節點的 layout 不依賴它大小的那個 render object（例如收到的限制是固定大小時）。
- **要重畫**：render object 呼叫 `markNeedsPaint`，標記往上傳到最近的 [RepaintBoundary](/programming/flutter/knowledge-cards/repaint-boundary/) 為止，下一幀只重錄那個邊界裡面的繪圖指令。

`CustomPaint` 對應的 render object 是 `RenderCustomPaint`，它有兩條路徑被標成要重畫：

- **換上新的 painter**：rebuild 產生新的 `CustomPainter` 時，`RenderCustomPaint` 比較新舊兩個 painter，型別不同或 `shouldRepaint` 回傳 `true` 才呼叫 `markNeedsPaint`。這條路徑先付了 rebuild 的成本。
- **`repaint` 參數**：`CustomPainter` 建構子收一個 `Listenable`（`ValueNotifier`、`AnimationController` 都是），`RenderCustomPaint` 監聽這個物件，它一通知，`RenderCustomPaint` 就直接呼叫 `markNeedsPaint`。`CustomPainter` 的文件寫的是這條路徑跳過 pipeline 的 build 與 layout 兩段。

## 可觀察訊號與例子

debug 模式下看哪些 widget 被 rebuild：設定 `debugPrintRebuildDirtyWidgets = true`，每一次 build 印出被標成要 rebuild 的 element；DevTools 的 Flutter Inspector 也能逐個 widget 計 rebuild 次數。`debugDumpApp()` 印出 widget 與 element 的樹，`debugDumpRenderTree()` 印出 render object 的樹。要看 build、layout、paint 各花了多少時間，在 profile 模式打開 `debugProfileBuildsEnabled`、`debugProfileLayoutsEnabled`、`debugProfilePaintsEnabled`，DevTools 的時間軸會多出每一個 widget 與 render object 的事件。

〔[Flutter 像素場景的每幀柵格化成本](/programming/flutter/hands-on/pixel-scene-texture-atlas-frame-cost/)〕的像素樹，原本把姿勢存在 `State` 的欄位、每次換姿勢呼叫 `setState`，每一次都 rebuild `GestureDetector` 以下的整棵子樹、建一個新的 painter，再由 `shouldRepaint` 決定要不要重畫；改成把姿勢放進 `ValueNotifier`、交給 `repaint` 參數之後，換姿勢只走 `markNeedsPaint`。那一篇同時改了幾處，沒有單獨量這一項省下的時間。

## 判斷條件與後果

- **改變的只有畫在固定大小範圍裡的內容時**（位置、顏色、進度），把會變的值放進 `Listenable`、交給 `repaint` 參數，每一次改變省下 rebuild；painter 在 `paint` 裡讀這個值，所以這些內容只能用 `Canvas` 畫，不能用 widget 組出來。改變得越頻繁（每個 vsync 一次的動畫），省下的 rebuild 次數越多。
- **改變的是畫面結構時**（多一個子元件、換一段文字、換一種排版），要 rebuild，`setState` 是這條路徑。rebuild 的範圍是呼叫 `setState` 的那個 `State` 底下整棵子樹，所以把會變的狀態放在離它影響的 widget 最近的那一層；子樹裡不隨狀態改變的部分寫成 `const`，element 比對到同一個物件就整段跳過。
- **改變會影響大小時**，除了 rebuild 或重畫，還要重新 layout；layout 的範圍到最近的 relayout boundary 為止，父節點的大小依賴子節點時，標記會一路往上傳。
- **瓶頸在柵格化時**，三種標記都只減少 UI 執行緒的工作；raster 執行緒每一幀要柵格化的內容不因為少了一次 rebuild 而變少，要省那一段，照 [Picture](/programming/flutter/knowledge-cards/picture/) 卡判斷條件裡瓶頸在 `rasterDuration` 那一條。
