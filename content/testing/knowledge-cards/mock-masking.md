---
title: "Mock Masking（Mock 遮蔽）"
date: 2026-06-19
description: "mock 模擬 API 層但不模擬協議層，造成的結構性驗證盲區"
weight: 2
tags: ["testing", "mock", "blindspot"]
---

Mock 遮蔽的核心概念是「mock 忠實模擬程式語言的 API 契約，但跳過了協議層和環境層的行為差異，讓這些差異在 test 中不可見」。遮蔽是 mock 的設計邊界，遮蔽的範圍形成結構性的驗證盲區。可先對照 [protocol integration test](/testing/knowledge-cards/protocol-integration-test/) 和[名義 integration test](/testing/knowledge-cards/nominal-integration-test/)。

## 概念位置

Mock 遮蔽發生在 API 層和協議層之間的語意斷裂處。Mock 模擬的是最上層（方法簽名、參數型別、回傳值），真實行為發生在下面兩層（協議語意、執行環境）。遮蔽有兩種模式：功能存在但行為錯誤（mock 接受了真實服務不接受的輸入）、功能根本沒實作（mock 不需要該功能就能通過）。這條斷裂正是[名義 integration test](/testing/knowledge-cards/nominal-integration-test/)命名誤導的來源——測試名稱寫著 integration，實際驗證仍停在 mock 遮蔽的範圍內。

## 可觀察訊號與例子

Mock 遮蔽的訊號是：test 全過但實機失敗的 bug 類型集中在外部互動（連線、認證、編碼）、修復後原有 test 不需要改動、bug 修復是型別轉換或編碼調整。`FakeWebSocketChannel` 的 `sink.add(dynamic)` 不區分 text/binary frame 是典型案例。

## 設計責任

面對 mock 遮蔽的正確策略是分層驗證 — mock 負責 API 層，[protocol integration test](/testing/knowledge-cards/protocol-integration-test/) 負責協議層。增加 mock test 數量無法跨越層級盲區。Mock 也不應該模擬協議行為 — 讓 mock 更「逼真」會讓 mock 本身變成需要維護和驗證的複雜元件。需要模擬應用層行為時，改用行為有實測出處的[語意級假後端](/testing/knowledge-cards/semantic-fake-backend/)。假設層的另一種盲區見[凍結參照與活解析](/testing/knowledge-cards/frozen-vs-live-reference/)——stub 寫死的參照值可能在後端操作後已失效，遮蔽的是資料生命週期、不是協議差異。
