---
title: "Nominal Integration Test（名義整合測試）"
date: 2026-06-19
description: "名稱含 integration 但核心依賴全用 fake 的 test，驗證內部狀態機而非真實服務互動"
weight: 3
tags: ["testing", "integration-test", "naming"]
---

名義 integration test 的核心概念是「test 標題或路徑包含 integration，但所有外部依賴都被 fake 替換，實際驗證的是內部邏輯而非真實服務互動」。它的問題在命名造成的認知偏差 — 團隊以為 integration 已驗證，實際上協議層完全沒被覆蓋。可先對照 [mock 遮蔽](/testing/knowledge-cards/mock-masking/)和 [protocol integration test](/testing/knowledge-cards/protocol-integration-test/)。

## 概念位置

名義 integration test 在 test 分類中介於 unit test 和真正的 integration test 之間。它的 scope 比 unit test 大（多個內部元件一起測），但驗證對象和 unit test 相同（程式碼內部邏輯）。它和 [mock 遮蔽](/testing/knowledge-cards/mock-masking/)的關係是：名義 integration test 用 mock 替換所有外部依賴，mock 遮蔽了協議層行為，而 test 名稱讓團隊以為這些行為已被驗證。

## 可觀察訊號與例子

辨識名義 integration test 的三個特徵：核心外部依賴 100% 被 fake 取代、沒有真實的 I/O 操作（網路、檔案、資料庫）、`setUp()` 不需要啟動外部程序或建立網路連線。

## 設計責任

修正策略分兩步：改名（讓 test 名稱反映真實驗證對象，如 `connection_state_machine_test`）和補寫（如果協議互動是關鍵路徑，補寫對真實服務的 [protocol integration test](/testing/knowledge-cards/protocol-integration-test/)）。在 test 檔案頂部標明被 fake 取代的依賴清單，讓後續讀者快速判斷驗證邊界。
