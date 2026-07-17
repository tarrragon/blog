---
title: "Affordance（操作暗示）"
date: 2026-07-17
description: "說明介面元素透過外觀傳達「可以對它做什麼」的訊號 — 可點、可捲、可拖的暗示與實際行為對齊時介面才可預測"
weight: 8
tags: ["ux-design", "knowledge-card", "affordance", "interaction-feedback"]
---

Affordance 的核心概念是「介面元素的外觀傳達它能被怎麼操作」。按鈕的邊框與底色暗示可點、清單邊緣的漸層暗示可捲、把手圖示暗示可拖 — 使用者不讀說明書、靠這些視覺訊號判斷能做什麼。暗示與實際行為對齊時介面可預測；錯位時使用者把「沒反應」讀成「壞掉」。尺寸層的對齊另見 [Touch Target](/ux-design/knowledge-cards/touch-target/)。

## 概念位置

Affordance 在互動發生之前起作用 — [互動回饋三層模型](/ux-design/06-interaction-feedback/feedback-three-layers/)管「操作之後系統怎麼回應」，affordance 管「操作之前使用者怎麼知道能操作」。兩個方向的錯位各自成類：暗示了但做不到（視覺像按鈕的狀態圖示、看似整行可點的列表行）、做得到但沒暗示（可捲動清單無捲動提示、隱藏手勢）。與 [Touch Target](/ux-design/knowledge-cards/touch-target/) 的分工：affordance 管「看起來能不能操作」、touch target 管「可操作範圍與尺寸是否足夠」。

## 可觀察訊號與例子

需要檢查 affordance 的訊號是使用者回報「按了沒反應」或「找不到功能」、而程式行為正確。實戰案例：狀態圖示與動作按鈕同形混排、被當成壞掉的按鈕（[U.C18](/ux-design/cases/status-icon-mistaken-for-button/)）；水平篩選列可捲動但無提示、截斷被讀成被遮蔽（[U.C16](/ux-design/cases/filter-chips-overflow-no-affordance/)）；整行反白暗示可點、gesture 只掛在尾端箭頭（[U.C8](/ux-design/cases/tag-row-touch-target-scope/)）。

## 設計責任

Affordance 的設計責任是讓「看起來能做的」與「實際能做的」一致：可互動元素帶明確的互動形態（按鈕容器、ripple）、非互動指示用明顯非按鈕的形態、隱藏的能力（捲動、手勢）補可見提示。審查問句：這個畫面上哪些元素可互動，使用者分得出來嗎？
