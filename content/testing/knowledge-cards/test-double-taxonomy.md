---
title: "Test Double Taxonomy（Fowler 分類）"
date: 2026-07-20
description: "test double 依據回應資料的來源與驗證方式分成五種角色，各自對應不同的可測範圍與盲區"
weight: 16
tags: ["testing", "test-double", "taxonomy", "mock", "stub", "fake"]
---

Test double 是所有「用來取代真實依賴」的測試替身的統稱，Martin Fowler 把它拆成五種角色：dummy（只填參數位置、從不被實際使用）、[stub](/testing/knowledge-cards/stub/)（測試作者寫死固定回應）、spy（記錄呼叫過程、供事後檢查）、mock（預先設定期望、呼叫不符期望即失敗）、fake（有狀態、可運作的簡化實作）。五種角色的分野在「資料從哪裡來」與「驗證的是狀態還是互動」，不是隨口互換的同義詞。

## 概念位置

本模組已經在用三種角色、只是沒有集中命名：[mock 遮蔽](/testing/knowledge-cards/mock-masking/)討論的 mock，忠實模擬 API 層的方法簽名與參數型別，驗證呼叫是否符合預期介面；[stub](/testing/knowledge-cards/stub/)是測試作者逐條寫死的固定回應，驗證「假設成立時」邏輯是否正確；[語意級假後端](/testing/knowledge-cards/semantic-fake-backend/)對應 fake——有狀態、可運作、模擬已證實後端行為的簡化實作。三者的差異不是實作細節，是各自能檢出的 bug 類型不同：mock 檢出介面誤用，stub 檢不出假設本身的錯誤，fake 能讓假設在多服務接力中被真正驗證。

## 可觀察訊號與例子

判斷一段程式碼裡的替身屬於哪個角色，看兩件事：資料是不是每條測試手動寫死的（是 → stub 或 dummy，取決於有沒有被實際讀取）、驗證是斷言最終狀態還是斷言呼叫發生過（前者偏 stub/fake，後者偏 spy/mock）。混用角色而不自知的訊號是：團隊說「這裡有 mock」，但程式碼裡其實是逐條寫死回應、沒有設定呼叫期望——用詞是 mock、行為是 stub，兩者的可測範圍不同，混用會讓覆蓋率的認知跟實際脫節。

## 設計責任

選角色的判準是「要驗證什麼」：只驗證程式碼內部邏輯、不涉及外部行為假設 → stub 或 dummy 就夠；要驗證「呼叫方式是否符合介面契約」→ mock；要驗證「假設成立時的多服務接力行為」，且假設本身有實測出處 → fake。角色選錯的典型後果是[凍結參照與活解析](/testing/knowledge-cards/frozen-vs-live-reference/)描述的那類盲區——用 stub 的地方假設會變、卻用了固定回應，狀態變化不會在測試裡發生。跨層盲區（協議層、假設層）疊加時，測試綠燈能證明的範圍比表面上薄。
