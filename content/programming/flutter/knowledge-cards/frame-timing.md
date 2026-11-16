---
title: "FrameTiming（Flutter 每一幀的時間紀錄）"
tags: ["flutter", "knowledge-card", "rendering", "performance"]
date: 2026-11-16
description: "用 addTimingsCallback 量掉幀、量每一幀的 build 與柵格化時間，或判斷 buildDuration、rasterDuration、totalSpan 各自代表什麼時讀"
weight: 4
---

`FrameTiming` 是 Flutter 的 `dart:ui` 替每一幀記下的時間戳記組：engine 收到 vsync 的時間（`vsyncStart`）、UI 執行緒開始與結束 build 的時間（`buildStart`、`buildFinish`）、raster 執行緒開始與結束柵格化的時間（`rasterStart`、`rasterFinish`）。從這些時間點算出四個長度：`buildDuration`（build 結束減開始）、`rasterDuration`（柵格化結束減開始）、`vsyncOverhead`（收到 vsync 到開始 build）、`totalSpan`（收到 vsync 到柵格化結束）。build 與柵格化分別跑在哪個執行緒，寫在 [Flutter Thread Model（Flutter 的執行緒模型）](/programming/flutter/knowledge-cards/flutter-thread-model/)。

App 用 `SchedulerBinding.instance.addTimingsCallback` 註冊回呼取得這些紀錄。engine 把紀錄成批送來：release 模式約每秒一批，debug 與 profile 模式約每 100 ms 一批，第一幀不等批次直接送（`scheduler/binding.dart` 的 `addTimingsCallback` 文件註解，Flutter 3.41.3）。

## 跟其他概念的關係

`FrameTiming` 量的是渲染管線每一段花的牆鐘時間，管線的兩段各自對應一個執行緒：`buildDuration` 是 UI 執行緒處理這一幀的時間，從 framework 開始處理這一幀算到它呼叫 `FlutterView.render` 把圖層樹交給 engine 為止（`dart:ui` 文件寫 build 在 `FlutterView.render` 被呼叫時結束），包含動畫的回呼、widget 的 rebuild、layout、繪製（paint 把繪圖指令錄成 [Picture](/programming/flutter/knowledge-cards/picture/)），以及 framework 把各圖層組成圖層樹的那一步；`rasterDuration` 是 raster 執行緒把圖層樹柵格化並送出畫面的時間。

三個常被混用的長度各自回答不同的事：

- **`buildDuration` 與 `rasterDuration`** 指管線各段花的時間。`dart:ui` 的文件把「有沒有掉幀」放在這兩個值各自有沒有超過單幀預算（1000 ÷ 螢幕更新率，60 Hz 約 16 ms，120 Hz 約 8 ms），因為兩段跑在不同執行緒，可以跟前後幀重疊。
- **`totalSpan`** 指從 vsync 到柵格化結束的延遲，文件把它放在「延遲高不高」。它超過預算不一定掉幀。
- **`vsyncOverhead`** 指 UI 執行緒收到 vsync 之後多久才開始 build，UI 執行緒被別的工作佔住時會變長。

## 可觀察訊號與例子

`rasterDuration` 是牆鐘時間，不等於 CPU 時間：Flutter 3.41.3 的 engine 把整個繪製到 surface 的過程算進柵格化的起訖，macOS 版送出畫面時還會等 Metal 的 command buffer 排進 GPU（`rasterizer.cc` 的 `DrawToSurfaceUnsafe`、`FlutterSurfaceManager.mm` 的 `waitUntilScheduled`）。2026 年在 macOS 桌面版的一次量測裡，同一個場景每秒排 144 幀時平均每幀柵格化約 4 ms，每秒只排 10 幀時約 10 ms（〔[Flutter 裝飾性動畫的驅動方式比較](/programming/flutter/hands-on/ambient-motion-frame-cost/)〕）。同一個場景改成預先畫好的點陣圖與 [Texture Atlas](/programming/flutter/knowledge-cards/texture-atlas/)、每一幀要柵格化的工作變少之後（同時改了另外幾處繪製方式，一起量），兩者縮到約 0.6 到 0.8 ms 對 0.7 到 0.9 ms（〔[Flutter 像素場景的每幀柵格化成本](/programming/flutter/hands-on/pixel-scene-texture-atlas-frame-cost/)〕）。

## 判斷條件與後果

- **拿 `FrameTiming` 判掉幀時**，單幀預算要依 App 所在螢幕的更新率算，比較 `buildDuration` 與 `rasterDuration`；寫死 16 ms 時，120 Hz 螢幕上花了 8 到 16 ms 的幀超過預算卻不會被記下，拿 `totalSpan` 比時，延遲高而沒有掉幀的幀會被記成掉幀。
- **拿 `rasterDuration` 估成本時**，它含等 GPU 的時間，低幀率時每幀的值可能偏長；要知道 CPU 花在哪裡，得用 DevTools 或 Instruments 分執行緒量。
- **回呼是成批到達的**，要算「每秒幾幀」時，以 `vsyncStart` 的時間戳把紀錄分到各秒，不以回呼到達的時間分：一批跨過整秒邊界時，以到達時間分會讓某一秒多算或少算一批。

監控 SDK 裡用 `FrameTiming` 回報掉幀的寫法，在〔[前端感測器設計](/devops/monitoring/03-sdk-design/frontend-sensor-design/)〕的〈Flutter frame timing〉。
