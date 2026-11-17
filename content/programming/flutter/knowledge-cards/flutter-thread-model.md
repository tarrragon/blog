---
title: "Flutter Thread Model（Flutter 的執行緒模型）"
tags: ["flutter", "knowledge-card", "rendering", "performance"]
date: 2026-11-16
description: "判斷一段 Dart 程式、一個平台呼叫或柵格化跑在哪個執行緒，讀 FrameTiming 的 build 與 raster 時間，或看到啟動 log 的 merged UI and platform thread 時讀"
weight: 5
---

Flutter 的 engine 把一個 App 的工作分給幾條執行緒（engine 叫它們 task runner）：**平台執行緒**（platform）是作業系統給 App 的主執行緒，處理系統事件與平台 API 的呼叫；**UI 執行緒**執行 Dart 程式，widget 的 build、layout、paint 都在這裡，產出一棵圖層樹；**raster 執行緒**把圖層樹[柵格化](/ux-design/knowledge-cards/rasterization/)，交給 GPU 並送到螢幕；**IO 執行緒**處理圖片解碼這類耗時的讀取。一幀在 UI 執行緒的那一段與在 raster 執行緒的那一段，分別記在 [FrameTiming](/programming/flutter/knowledge-cards/frame-timing/) 的 `buildDuration` 與 `rasterDuration`。

## 跟其他概念的關係

UI 執行緒與 raster 執行緒是兩條流水線：raster 執行緒在柵格化第 N 幀時，UI 執行緒可以開始 build 第 N+1 幀。所以一幀的兩段各自要在一個 vsync 間隔內做完，畫面才不掉幀，兩段加起來超過一個間隔不一定掉幀；[FrameTiming](/programming/flutter/knowledge-cards/frame-timing/) 把掉幀的判斷放在兩段各自的長度，就是這個原因。

**合併的 UI 與平台執行緒**指 UI 執行緒的工作改在平台執行緒上跑，Dart 程式跟平台 API 的呼叫共用同一條執行緒。Flutter 3.41.3 的 engine 預設合併（`common/settings.h` 的 `merged_platform_ui_thread` 預設 `kEnabled`）：iOS 不允許關閉（`FLTEnableMergedPlatformUIThread=false is no longer allowed`），macOS 可以在 Info.plist 用 `FLTEnableMergedPlatformUIThread` 關閉，Android 可以用 engine 的啟動旗標關閉。macOS 桌面版啟動時印出 `Running with merged UI and platform thread. Experimental.` 就是這個狀態。

## 可觀察訊號與例子

Dart 程式做一段耗時的同步計算時，UI 執行緒被佔住，`buildDuration` 變長、畫面掉幀；在合併的執行緒上，同一段計算也讓平台的事件處理一起等待。柵格化的內容太複雜（大量 path、模糊、陰影）時，`rasterDuration` 變長，而 Dart 程式的 profile 看起來很乾淨，因為那段時間不在 UI 執行緒上。

用 `ps` 這類工具量整個行程的 CPU 時，幾條執行緒的時間加在一起，分不出是 build 還是柵格化；要分開看，得用 DevTools 的 timeline 或 Xcode Instruments 這類能分執行緒的工具。

## 判斷條件與後果

- **`buildDuration` 超過預算時**，耗時的工作在 UI 執行緒上（rebuild 的範圍太大、同步計算、paint 裡即時算 path），把計算移到 isolate、縮小 rebuild 範圍或把繪圖指令事先錄成 [Picture](/programming/flutter/knowledge-cards/picture/)，減少的是這一段。
- **`rasterDuration` 超過預算而 `buildDuration` 正常時**，耗時的工作在柵格化，Dart 端的最佳化不影響它；要減少的是每一幀要柵格化的內容（模糊、陰影、大量 path、很多小圖塊各自重播的繪圖指令），或排幀的次數；內容固定的小圖塊可以預先畫成點陣圖、拼成 [Texture Atlas](/programming/flutter/knowledge-cards/texture-atlas/)。[RepaintBoundary](/programming/flutter/knowledge-cards/repaint-boundary/) 減少的是 UI 執行緒的重畫，柵格化照整個畫面計，它對 `rasterDuration` 的影響要看 engine 有沒有把那個圖層快取起來。
- **在合併執行緒的平台上**，Dart 端的耗時工作同時延遲平台的事件處理，平台 API 的呼叫回應變慢，跟掉幀一起出現。
