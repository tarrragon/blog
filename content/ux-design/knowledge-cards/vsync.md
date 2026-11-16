---
title: "VSync（垂直同步）"
date: 2026-11-16
description: "估算一個動畫每秒要畫幾幀、在不同更新率的螢幕上成本差多少，或分辨 vsync 這個詞指的是螢幕訊號、Flutter 的 vsync 參數還是遊戲的垂直同步開關時讀"
weight: 11
tags: ["ux-design", "knowledge-card", "interaction-feedback", "rendering"]
---

VSync（vertical synchronization，垂直同步）指螢幕每開始一次刷新時發出的時間訊號：螢幕以固定的更新率重畫整個面板，60 Hz 的螢幕每 16.7 ms 刷新一次，144 Hz 的螢幕每 6.9 ms 一次，每一次刷新的起點就是一個 vsync。名字來自 CRT 時代電子束畫完最後一行、回到頂端的那段垂直回掃時間。UI 框架把產生畫面的節奏對齊這個訊號：Flutter 的引擎在每個 vsync 通知 framework 開始一幀，Web 的 `requestAnimationFrame`、iOS 的 `CADisplayLink`、Android 的 `Choreographer` 也都在每個 vsync 呼叫一次回呼。框架只在有東西要求下一幀時才接這個訊號，這一點寫在 [On-demand Rendering（按需重繪）](/ux-design/knowledge-cards/on-demand-rendering/)。

## 跟其他概念的關係

vsync 是時間的刻度，[按需重繪](/ux-design/knowledge-cards/on-demand-rendering/)決定這個刻度上的哪幾格實際產生一幀：每個 vsync 都要求下一幀的動畫驅動器（Flutter 的 `Ticker`、`requestAnimationFrame` 迴圈），每秒的幀數等於螢幕更新率；只在事件來時才要求的驅動器，大部分 vsync 都不產生幀。

這個詞在不同脈絡指三種對象：

- **螢幕的刷新訊號**指本卡開頭定義的時間點，是另外兩種用法共同的來源。
- **Flutter 的 `vsync:` 參數**（`AnimationController(vsync: this)`）指一個 `TickerProvider`，它負責建立 `Ticker`，並在它所在的子樹被 `TickerMode` 關閉時（例如被另一個不透明頁面蓋住的頁面）讓 `Ticker` 暫停；參數取這個名字，是因為 `Ticker` 每個 vsync 觸發一次。
- **遊戲與顯示卡設定裡的「垂直同步」開關**指畫好的一幀要不要等到下一個 vsync 才交給螢幕。關掉時，新的一幀可能在螢幕刷新到一半時換上去，同一次刷新的上半部與下半部來自不同的幀，看起來是一條水平的撕裂線（tearing）；打開時沒有撕裂，代價是每一幀多等一段時間才顯示。

## 可觀察訊號與例子

同一個 App 換一台螢幕，動畫的幀數跟著變：用 Flutter 的 `AnimationController` 做的持續動畫，在 60 Hz 的螢幕上每秒約 60 幀，拖到 144 Hz 的外接螢幕上變成每秒約 144 幀，CPU 使用率也跟著升高（2026 年在 macOS 桌面版的量測，寫在〔[Flutter 裝飾性動畫的驅動方式比較](/programming/flutter/hands-on/ambient-motion-frame-cost/)〕）。

iPhone 的 ProMotion 螢幕最高 120 Hz，App 沒有在 Info.plist 設 `CADisableMinimumFrameDurationOnPhone` 時，`CADisplayLink` 最高只到 60 Hz（Apple〈Optimizing ProMotion refresh rates for iPhone 13 Pro and iPad Pro〉）：這時 vsync 驅動的回呼頻率由系統設的上限決定，螢幕的更新率只是上限的上限。

一幀的工作沒有在下一個 vsync 之前做完時，螢幕在那一次刷新重複顯示上一幀，使用者看到的是動畫頓一下（掉幀）。

## 判斷條件與後果

- **動畫的驅動器每個 vsync 都觸發時**，每秒的幀數由 App 視窗所在的那台螢幕決定，同一份程式在 144 Hz 的螢幕上產生的幀數是 60 Hz 的 2.4 倍。估成本或比較量測數字時，要先寫出螢幕的更新率，否則兩次量測的幀數對不起來。
- **每一幀的時間預算是一個 vsync 間隔**：60 Hz 是 16.7 ms，144 Hz 是 6.9 ms。在 60 Hz 下做得完的一幀，換到高更新率的螢幕上可能超過預算而掉幀，原因是預算縮短了，每一幀的工作量沒有變。
- **驅動器不綁 vsync 時**（計時器每 100 ms 觸發一次），每秒的幀數由計時器的間隔決定，跟螢幕更新率無關；計時器要求的那一幀仍然排到下一個 vsync 才產生，所以畫面更新的時間點會落在最近的一個刷新點上。

不同驅動器的成本差多少、為什麼繪製次數降了而柵格化次數沒有降，寫在〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕。
