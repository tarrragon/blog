---
title: "Picture（ui.Picture 與 PictureRecorder）"
tags: ["flutter", "knowledge-card", "rendering", "performance"]
date: 2026-11-16
description: "考慮把一段固定的繪圖事先錄起來、每一幀只重播，或想知道 CustomPainter 的 paint 產出的是什麼、為什麼繪製的成本跟柵格化的成本分開算時讀"
weight: 6
---

`ui.Picture` 是一串錄好的繪圖指令：先用 `PictureRecorder` 開一個 `Canvas`，對它呼叫 `drawRect`、`drawPath` 這類方法，再呼叫 `recorder.endRecording()`，得到的 `Picture` 記下了這些指令，之後不能再修改。之後要畫同樣的內容時，對任何一個 `Canvas` 呼叫 `drawPicture(picture)` 重播這串指令，不必重新計算每一個圖形。Flutter 的 paint 階段本身也是在錄 `Picture`：每一個 `CustomPainter.paint` 收到的 `Canvas`，背後就是 framework 開的錄製器，錄好的 `Picture` 放進圖層樹，交給 raster 執行緒[柵格化](/ux-design/knowledge-cards/rasterization/)（[Flutter Thread Model（Flutter 的執行緒模型）](/programming/flutter/knowledge-cards/flutter-thread-model/)）。

## 跟其他概念的關係

`Picture` 是向量指令，不是點陣圖：錄製發生在 UI 執行緒，成本記在 [FrameTiming](/programming/flutter/knowledge-cards/frame-timing/) 的 `buildDuration`；把指令變成像素是柵格化，在 raster 執行緒上，記在 `rasterDuration`。

- **重播 `Picture`** 指每一幀把錄好的指令再交給圖層樹，省下的是 UI 執行緒重新計算圖形的時間，raster 執行緒仍然每一幀柵格化一次。
- **`picture.toImage()`** 指把指令柵格化成一張點陣圖（`ui.Image`），之後畫的是圖片，柵格化指令的成本只付一次，代價是固定的解析度與一份圖片的記憶體。
- **[RepaintBoundary](/programming/flutter/knowledge-cards/repaint-boundary/)** 指 framework 替一棵子樹自動保留它上一次錄好的 `Picture`，子樹沒有標記要重畫時直接沿用；手動錄 `Picture` 是開發者自己決定錄什麼、什麼時候重錄。

## 可觀察訊號與例子

〔[Flutter 裝飾性動畫的驅動方式比較](/programming/flutter/hands-on/ambient-motion-frame-cost/)〕的像素樹場景，把每一叢葉子在啟動時錄成一個 `Picture`，每一幀只平移後重播。改成這樣之後，每個 vsync 都重畫的版本每幀 build 從逐格畫方塊時的約 1.5 ms 降到 0.38 ms，柵格化仍然每一幀都做（2026 年在 macOS 桌面版的量測，同時改了造型與畫面大小，三件事沒有拆開量）。

## 判斷條件與後果

- **一段繪圖的內容固定、每一幀只改位置或透明度時**，錄成 `Picture` 重播，省下 UI 執行緒每一幀重新算圖形的時間；內容每一幀都變時，每一幀都得重錄，錄製的成本照付。
- **瓶頸在 `rasterDuration` 時**，錄成 `Picture` 不改變柵格化的工作量，這時省得到時間的是 `toImage()` 換成點陣圖，或讓 engine 的快取把圖層存成點陣圖（只有 Skia 後端有這個快取，Impeller 沒有，見 [Texture Atlas（紋理圖集）](/programming/flutter/knowledge-cards/texture-atlas/) 卡的渲染後端那一條），代價是記憶體，以及放大時的失真（取樣方式決定是變糊還是變成方塊，見 [Texture Atlas（紋理圖集）](/programming/flutter/knowledge-cards/texture-atlas/)）。要畫的是很多個各自位移的小圖塊時，可以把柵格化好的點陣圖拼成一張紋理圖集，每一幀用一次 `drawAtlas` 畫完；〈可觀察訊號與例子〉那個像素樹場景改成這樣、同時把背景也畫成點陣圖並放進自己的圖層、換姿勢時不 rebuild 之後，每幀柵格化從約 3.7 ms 降到約 0.6 ms（這幾處改動沒有拆開量，量測在〔[Flutter 像素場景的每幀柵格化成本](/programming/flutter/hands-on/pixel-scene-texture-atlas-frame-cost/)〕）。
- **`Picture` 與 `ui.Image` 持有 engine 端的資源**，不再用時呼叫 `dispose()`；一直重錄而不釋放時，engine 端的記憶體跟著增加。
