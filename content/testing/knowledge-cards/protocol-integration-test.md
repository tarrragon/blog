---
title: "Protocol Integration Test"
date: 2026-06-19
description: "驗證程式碼和真實外部服務之間的協議互動是否正確的 test 層級"
weight: 1
tags: ["testing", "integration-test", "protocol"]
---

Protocol integration test 的核心概念是「對真實服務實例驗證協議層行為」。它跳過 mock，直接連線到真實的外部服務，觀察連線握手、認證流程、資料編碼和回應格式是否符合協議規格。和 [mock 遮蔽](/testing/knowledge-cards/mock-masking/)互補 — mock 遮蔽的盲區正是 protocol integration test 的驗證範圍。可先對照[名義 integration test](/testing/knowledge-cards/nominal-integration-test/)。

## 概念位置

Protocol integration test 位在 unit test 和 E2E test 之間。Unit test 用 mock 驗證程式碼邏輯，E2E test 經過 UI 驗證完整流程，protocol integration test 用程式碼直接呼叫 client 端連線函式、對真實服務執行操作。它填補「程式碼邏輯正確但協議互動錯誤」這個 mock 結構性無法覆蓋的空隙。業務行為層的漂移偵測由[真實後端驗證測試](/testing/knowledge-cards/real-backend-verification-test/)承擔——兩卡以協議契約 vs 業務行為劃界。

## 可觀察訊號與例子

需要 protocol integration test 的訊號是：API 簽名用寬泛型別（`dynamic`、`Object`、`Any`）隱藏了協議層的行為分支、mock 跳過了業務關鍵步驟（認證、握手）、或外部服務對錯誤輸入靜默忽略。WebSocket 的 text/binary frame 差異、gRPC 的 streaming deadline、MQTT 的 QoS level 都是典型場景。

## 設計責任

Protocol integration test 要決定服務 fixture 的管理方式（Process.start / Docker / testcontainers）、健康檢查策略（port 可達 / HTTP health / 業務操作成功）、和狀態隔離方式（每 test 重啟 / 重設狀態 / 獨立 namespace）。成本判斷依據服務啟動成本和協議複雜度兩個維度。
