---
title: "On-demand Rendering（按需重繪）"
date: 2026-11-16
description: "畫面靜止時 App 是否仍在產生幀、一個持續動畫為什麼讓整個畫面一直重繪，或比較 UI 框架與遊戲引擎的繪製成本時讀"
weight: 12
tags: ["ux-design", "knowledge-card", "interaction-feedback", "rendering"]
---

On-demand rendering（按需重繪）是 UI 框架產生畫面的方式：只有某個元件要求下一幀時，框架才在下一個 [VSync（垂直同步）](/ux-design/knowledge-cards/vsync/)跑一次渲染管線（重新計算版面、繪製、合成圖層、柵格化），畫面沒有內容要更新時就不產生新的一幀，螢幕重複顯示上一幀。Flutter、瀏覽器、iOS 的 UIKit 與 Android 的 View 系統都是這樣運作。Flutter 裡發出要求的最底層呼叫是 `scheduleFrame()`，`setState`、動畫的 `Ticker` 與 `markNeedsPaint` 最後都走到它（〔[Flutter scheduleFrame()：按需 render 的最底層原語](/work-log/flutter_schedule_frame/)〕）。

## 跟其他概念的關係

按需重繪決定哪幾個 [vsync](/ux-design/knowledge-cards/vsync/) 會產生一幀，跟它對照的是持續渲染：

- **按需重繪**指有要求才產生幀，靜止的畫面每秒 0 幀，成本跟著「多少個 vsync 有人要求下一幀」走。
- **持續渲染**指每個 vsync（或盡可能快地）都把整個畫面重畫一次，不看內容有沒有變。遊戲的主迴圈多半是這一種：場景裡隨時有東西在動，每一幀重畫整個場景是預設的做法，物理每幀更新不增加額外的幀。

把遊戲的寫法搬進 UI 框架時，兩者的差別會變成成本：遊戲裡「每一幀都更新一點」不需要額外的幀，搬進按需重繪的框架就需要一個每個 vsync 都觸發的驅動器，讓本來可以靜止的畫面一直在重繪。

渲染管線是整個畫面共用的：一個元件要求下一幀，產生的是整個畫面的一幀，合成與柵格化照整個畫面計；元件只能用 `RepaintBoundary` 這類隔離讓沒變的部分少重畫，不能讓整個畫面不產生那一幀。

## 可觀察訊號與例子

按需重繪的框架裡，靜止畫面的幀數應該是 0：用 Flutter 的 `FrameTiming`、Chrome Performance 面板的 frame 列或 Xcode Instruments 量，畫面看起來沒在動、幀數卻是每秒 60 或 144 時，畫面上某處有一個沒停下來的驅動器，例如一個 `repeat()` 的 `AnimationController`、一個 `requestAnimationFrame` 迴圈，或一個播放中的動畫檔。

反過來的訊號是畫面該更新卻沒有更新：程式的狀態已經改了、log 也印對了，畫面停在舊的一幀。按需重繪的框架只在有人要求時才畫，狀態的改動沒有經過會要求下一幀的路徑（例如外部 texture 更新了，卻沒有通知 framework）時，畫面就不會跟上（排查過程在〔[Flutter 畫面落後邏輯狀態（log 正確、畫面不符）— 重繪訊號排查與心跳做法](/work-log/flutter_repaint_heartbeat/)〕）。

## 判斷條件與後果

- **畫面上沒有任何驅動器在要求下一幀時**，渲染管線不跑，CPU 與 GPU 在這個畫面上的成本接近 0。按需重繪省電的效果就來自這一段時間，所以裝飾性動畫只在事件那一陣啟動驅動器、播完停住時，事件之間的時間都落在這個狀態。
- **畫面上只要有一個驅動器每個 vsync 都要求下一幀**，整個畫面就每秒產生螢幕更新率那麼多幀，同一畫面上其他元件省下的繪製，省不掉這些幀的合成與柵格化。一秒產生幾幀由最頻繁的那個驅動器決定，所以一個不起眼的持續動畫（角落的吉祥物、一直轉的載入圖示）就讓整個畫面離開零成本的狀態；每一幀花多少成本，另外看那一幀要柵格化多少內容（同一個畫面幀數不變、每一幀的柵格化工作變少時，CPU 也跟著降；那次同時改了幾處繪製方式、一起量，量測在〔[Flutter 像素場景的每幀柵格化成本](/programming/flutter/hands-on/pixel-scene-texture-atlas-frame-cost/)〕）。這一條描述的是 Flutter 的 `Ticker` 的行為；瀏覽器的 `requestAnimationFrame` 回呼每個 vsync 都進來、但沒有改動 canvas 時，從一次量測推論瀏覽器不重新柵格化那張 canvas，CPU 隨實際重畫的次數下降（沒有用 Performance 面板確認），量測在〔[瀏覽器 canvas 像素動畫的 CPU 量測與重畫上限](/ux-design/06-interaction-feedback/hands-on/canvas-ambient-frame-cap/)〕。
- **狀態改了而畫面沒變時**，要找的是狀態改動有沒有接到要求下一幀的那條路徑：按需重繪的框架不會自己發現狀態變了，原因是它只在收到要求時才畫。

驅動器的種類與各自的成本，寫在〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈重繪成本與動畫驅動器的排幀頻率〉。
