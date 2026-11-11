---
title: "Protocol Integration Test"
date: 2026-06-19
description: "驗證程式碼和真實外部服務之間的協議互動是否正確的 test 層級"
weight: 1
tags: ["testing", "integration-test", "protocol"]
---

Protocol integration test 的核心概念是「對真實服務實例驗證協議層行為」。它跳過 mock，直接連線到真實的外部服務，觀察連線握手、認證流程、資料編碼和回應格式是否符合協議規格。和 [mock 遮蔽](/testing/knowledge-cards/mock-masking/)互補 — mock 遮蔽的盲區正是 protocol integration test 的驗證範圍。可先對照[名義 integration test](/testing/knowledge-cards/nominal-integration-test/)。

## 跟其他概念的關係

Protocol integration test 位在 unit test 和 E2E test 之間。Unit test 用 mock 驗證程式碼邏輯，E2E test 經過 UI 驗證完整流程，protocol integration test 用程式碼直接呼叫 client 端連線函式、對真實服務執行操作。它填補「程式碼邏輯正確但協議互動錯誤」這個 mock 結構性無法覆蓋的空隙。業務行為層的漂移偵測由[真實後端驗證測試](/testing/knowledge-cards/real-backend-verification-test/)承擔——兩卡以協議契約 vs 業務行為劃界。

## 可觀察訊號與例子

需要 protocol integration test 的訊號是：API 簽名用寬泛型別（`dynamic`、`Object`、`Any`）隱藏了協議層的行為分支、mock 跳過了業務關鍵步驟（認證、握手）、或外部服務對錯誤輸入靜默忽略。WebSocket 的 text/binary frame 差異、gRPC 的 streaming deadline、MQTT 的 QoS level 都是典型場景。

## 判斷條件與後果

這類測試的三個設計選擇，各自決定一類失敗是否出現。服務 fixture 用 Process.start、Docker 或 testcontainers 管理，三者的啟動成本不同，而每次啟動的等待時間乘上啟動次數就是套件的固定成本。健康檢查只看 port 可達時，服務可能還沒完成初始化就接受連線，第一個 test 在服務就緒前執行而失敗；以 HTTP health 或一次業務操作成功當就緒條件，判定的是服務已經能處理請求。狀態隔離用每 test 重啟、重設狀態或獨立 namespace；沒有隔離時，前一個 test 寫進服務的狀態成為下一個 test 的前提，test 的執行順序一變結果就跟著變。這些成本是否值得付，依服務啟動成本和協議複雜度兩個維度判斷。
