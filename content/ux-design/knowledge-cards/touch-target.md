---
title: "Touch Target（觸控目標）"
date: 2026-07-16
description: "實機測試點列表行文字卻無反應、或可用性測試觀察到使用者重複點擊同一行時使用。觸控目標有兩層要求：尺寸不小於平台底線、範圍涵蓋視覺暗示的可點區域——後者在列表行展開/收合場景最常被忽略。"
weight: 6
tags: ["ux-design", "knowledge-card", "interaction-feedback", "touch-target", "mobile"]
---

Touch Target 的核心概念是「可點擊區域必須涵蓋視覺上暗示可點的範圍」。視覺設計透過整行反白、箭頭圖示、卡片邊框暗示「這裡可以點」；若實際的 gesture 區域小於視覺暗示的範圍，使用者點了沒反應，體感跟按鈕壞掉相同。它處理的是回饋發生之前的問題 — 點擊沒有落在 gesture 區域內，[三層回饋](/ux-design/06-interaction-feedback/feedback-three-layers/)連第一層都不會啟動。與 [Doherty Threshold](/ux-design/knowledge-cards/doherty-threshold/)（回饋時間門檻）互補：Doherty 管「點擊後多久要有反應」，Touch Target 管「點擊有沒有落在可反應的區域」。

## 概念位置

Touch Target 處理的是回饋鏈的第零層——點擊有沒有落在可反應的區域。[三層回饋](/ux-design/06-interaction-feedback/feedback-three-layers/)（點擊確認 / 等待指示 / 結果通知）假設點擊已經落在 gesture 區域內；Touch Target 確保這個前提成立。與 [Doherty Threshold](/ux-design/knowledge-cards/doherty-threshold/) 的關係是空間 vs 時間：Doherty 管回饋的時間門檻、Touch Target 管回饋的空間門檻。與 [Screen State Matrix](/ux-design/knowledge-cards/screen-state-matrix/) 無直接關聯——狀態矩陣管畫面層級的轉換、Touch Target 管元件層級的互動。

## 尺寸底線與範圍對齊

兩個層次的要求，缺一都會產生「點了沒反應」：

- **尺寸底線**：Material Design 規定最小觸控目標 48x48dp、iOS HIG 規定 44x44pt。小於底線的目標（如單獨一顆 24dp 圖示）即使精準點擊也容易失手。
- **範圍對齊**：觸控區域要等於視覺暗示的可點範圍。列表行的展開/收合是典型場景 — 整行是一個視覺單元，使用者直覺點行的任何位置；若 gesture 只掛在尾端箭頭 `IconButton` 上，點標籤名稱、點空白處都無反應。

一個書庫管理 App 的標籤管理頁實證了範圍錯位（案例見 [U.C8](/ux-design/cases/tag-row-touch-target-scope/)）：二級標籤的展開/收合只有尾端箭頭可點，實機測試使用者直覺點整行、無反應。修復是在包裹整行的 `InkWell` 加上 `onTap`（與箭頭觸發同一個 callback）；內層 `IconButton` 是獨立 gesture 區域，點箭頭時由它自己處理，不會被外層重複觸發 — 整行成為觸控目標，箭頭行為不變。

## 可觀察訊號與例子

範圍錯位的訊號是「使用者點了視覺單元的非 icon 區域而無反應」：實機測試點列表行文字無反應、可用性測試觀察到使用者重複點擊同一行、觸控熱點分析顯示大量落在 gesture 區域外的點擊。程式碼層的訊號是 gesture 只掛在視覺單元的子元件（trailing icon、小圖示）而非整個單元容器。

## 設計責任

Touch Target 的設計責任是讓「看起來可以點的地方」與「實際可以點的地方」一致，且不小於平台底線。列表行的主要操作（展開、進入詳情）以整行為觸控目標；行內若有次要操作（刪除、更多選單），保留為獨立的內層 gesture 區域，兩者互不干擾。設計審查時對每個可互動視覺單元問一句：使用者最直覺點的位置，在 gesture 區域內嗎？
