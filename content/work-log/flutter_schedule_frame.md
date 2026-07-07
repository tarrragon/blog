---
title: "Flutter scheduleFrame()：按需 render 的最底層原語"
date: 2026-07-07
draft: false
description: "手動觸發重繪、或釐清 setState / 動畫 / markNeedsPaint 為何最終都要向引擎要一個 frame 時，回頭理解這個按需 render 的底層原語。"
tags: ["flutter", "rendering"]
---

排查副屏畫面落後、用 `scheduleFrame()` 當重繪兜底時（見 [畫面落後邏輯狀態的排查與心跳做法](../flutter_repaint_heartbeat/)），回頭釐清這個 API 原本的設計意義。

## Flutter 是「按需 render」

一個關鍵前提：**Flutter 預設按需 render——畫面靜止時根本不產生新的 frame**（省 CPU/GPU/電），不是持續 60fps 在畫。那「什麼時候該畫」怎麼決定？就靠 `scheduleFrame()`。

`WidgetsBinding.instance.scheduleFrame()` 是 `SchedulerBinding`（被 mixin 進 `WidgetsBinding`）上的**底層原語**，語意是：

> 跟引擎登記——請在下一個 vsync 回叫我一次，我要產生一個 frame。

流程：

```text
有內容要畫 → scheduleFrame() → 引擎在下個 vsync 回叫
          → handleBeginFrame（跑 transient callback：動畫 / Ticker）
          → handleDrawFrame（跑 pipeline：build → layout → paint → composite）
          → render(scene) → 引擎 rasterize + present
```

## 它是整個框架 render 的匯流點

你平常不會直接呼叫它，但每個「讓畫面更新」的 API 最後都走到這裡：

- `setState` / `markNeedsBuild` → `ensureVisualUpdate` → `scheduleFrame`
- `markNeedsLayout` / `markNeedsPaint` → 同上
- `Ticker`（動畫）每個 vsync → `scheduleFrameCallback` → `scheduleFrame`

所以 `scheduleFrame()` 是「我有內容要畫」與「平台 vsync 驅動的 frame 生產」之間的橋樑，是最原始那顆按鈕。上層那些 dirty-marking API 只是替你在對的時機按它。

## 設計特性

- **冪等**：一個 frame 週期內呼叫幾次都只排一個 frame（內部 `_hasScheduledFrame` 旗標擋重複）。語意是「若還沒排 frame 就排一個」。
- **綁 vsync**：不是「立刻畫」，是「排到下個 vsync 才畫」。所以靠它畫不可能超過螢幕刷新率，不會變成 busy loop。
- **受 `framesEnabled` 約束**：app 不可見（背景）時不會真的排；要無視可見性強制排才用 `scheduleForcedFrame()`。

## 直接呼叫的時機

正常情況你（或框架幫你）呼叫 `scheduleFrame` 是因為「真的有狀態變了要畫」。直接呼叫很少見，通常是：**你改了某個會影響畫面、但沒有走 `setState` / `markNeedsPaint` 的狀態**，框架偵測不到，得手動請一個 frame。

副屏重繪兜底就是這種「借字面效果」的用法：我們沒有狀態變更，是借它「產生並 present 一個 frame」逼合成層重新 present 一次（把 texture 圖層的最新內容一起推上去）。契約上完全合法——`scheduleFrame` 的職責就是「產生一個 frame」，不要求內容有變——只是偏離了「內容改變才排 frame」的常規，所以定位成兜底而非首選。

## 小結

- `scheduleFrame()` = Flutter 按需 render 的最底層「要一個 frame」原語。
- 所有 dirty-marking（setState / markNeedsPaint / 動畫）最終都匯流到它。
- 冪等、綁 vsync、背景不排（強制用 `scheduleForcedFrame`）。
- 直接呼叫適用於「畫面該更新但沒走正常 dirty 路徑」的場景。
