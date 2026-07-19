---
title: "Screen State Test"
date: 2026-06-19
description: "驗證使用者可見的畫面狀態覆蓋度和狀態間轉換完整性的 test 層級"
weight: 4
tags: ["testing", "screen-state", "ui-test"]
---

Screen state test 的核心概念是「驗證畫面層級的狀態機是否完整 — 每個狀態下使用者看到什麼、能操作什麼、怎麼離開」。它的斷言對象是使用者可見的畫面，和 unit test（斷言函式回傳值）及 [protocol integration test](/testing/knowledge-cards/protocol-integration-test/)（斷言協議互動）職責不同。可先對照[畫面狀態矩陣](/ux-design/knowledge-cards/screen-state-matrix/)。

## 概念位置

Screen state test 是測試三層中的第三層。Unit test 驗證程式碼邏輯，protocol integration test 驗證協議互動，screen state test 驗證畫面狀態。同一段程式碼可能 unit test 通過但 screen state test 失敗 — 因為 UI binding 的問題讓正確的邏輯沒有反映到畫面上。跨服務互動鏈落在三層之間的縫隙時，由[流程測試](/testing/knowledge-cards/flow-test/)補位——它繞過 UI 皮層、從編排入口驅動整條服務鏈。

## 可觀察訊號與例子

需要 screen state test 的訊號是畫面有多個狀態（loading / connected / error / disconnected）且狀態轉換邏輯複雜。[畫面狀態矩陣](/ux-design/knowledge-cards/screen-state-matrix/)直接轉成 test case — 矩陣中每個狀態的「顯示」「可用操作」「退出路徑」各對應一個 assertion。

## 設計責任

Screen state test 要決定用什麼工具驗證畫面（widget test / integration test / Playwright）、斷言的粒度（元素存在 / 文字內容 / 視覺比對）、和狀態的觸發方式（mock 觸發狀態切換 / 真實操作觸發）。
