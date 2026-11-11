---
title: "Mock Masking（Mock 遮蔽）"
date: 2026-06-19
description: "mock 模擬 API 層但不模擬協議層，造成的結構性驗證盲區"
weight: 2
tags: ["testing", "mock", "blindspot"]
---

Mock 遮蔽的核心概念是「mock 忠實模擬程式語言的 API 契約，但跳過了協議層和環境層的行為差異，讓這些差異在 test 中不可見」。遮蔽是 mock 的設計邊界，遮蔽的範圍形成結構性的驗證盲區。可先對照 [protocol integration test](/testing/knowledge-cards/protocol-integration-test/) 和[名義 integration test](/testing/knowledge-cards/nominal-integration-test/)。

## 跟其他概念的關係

Mock 遮蔽發生在 API 層和協議層之間的語意斷裂處。Mock 模擬的是最上層（方法簽名、參數型別、回傳值），真實行為發生在下面兩層（協議語意、執行環境）。遮蔽有兩種模式：功能存在但行為錯誤（mock 接受了真實服務不接受的輸入）、功能根本沒實作（mock 不需要該功能就能通過）。這條斷裂正是[名義 integration test](/testing/knowledge-cards/nominal-integration-test/)命名誤導的來源——測試名稱寫著 integration，實際驗證仍停在 mock 遮蔽的範圍內。

## 可觀察訊號與例子

Mock 遮蔽的訊號是：test 全過但實機失敗的 bug 類型集中在外部互動（連線、認證、編碼）、修復後原有 test 不需要改動、bug 修復是型別轉換或編碼調整。`FakeWebSocketChannel` 的 `sink.add(dynamic)` 不區分 text/binary frame 是典型案例。

## 判斷條件與後果

遮蔽的範圍由 mock 模擬到哪一層決定。增加 mock test 的數量時，新增的測試仍停在 API 層，協議層的盲區一處都沒有少；分層驗證讓 mock 負責 API 層、[protocol integration test](/testing/knowledge-cards/protocol-integration-test/) 負責協議層，協議層才有測試對真實服務檢查。讓 mock 模擬協議行為、變得更「逼真」時，mock 本身成為需要維護與驗證的複雜元件，而它的模擬是否正確沒有任何測試檢查；需要模擬應用層行為時，[語意級假後端](/testing/knowledge-cards/semantic-fake-backend/)的每一條行為都有實測出處，模擬的正確性有來源可查。假設層的另一種盲區見[凍結參照與活解析](/testing/knowledge-cards/frozen-vs-live-reference/)——stub 寫死的參照值可能在後端操作後已失效，遮蔽的是資料生命週期、不是協議差異。同一個遮蔽機制也會發生在應用邊界之內，範圍由測試邊界畫在哪決定：把每個協作類別都替換掉的做法讓類別之間的真實協作行為一併不可見，判斷標準見 [Sociable vs Solitary Unit Test](/testing/knowledge-cards/unit-definition-two-schools/)。
