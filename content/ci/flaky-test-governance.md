---
title: "Flaky test 治理"
date: 2026-05-21
description: "說明 CI/CD 如何把 flaky test 從重跑雜訊轉成可分類、可隔離、可修復的 gate 信任度問題"
tags: ["CI", "test", "flaky test", "governance"]
weight: 31
---

Flaky test 治理的核心責任是保護 CI gate 的信任度。[Flaky test](/ci/knowledge-cards/flaky-test/) 會讓團隊開始用重跑取代判讀，最後讓紅燈失去阻擋意義。

## 概念定位

Flaky test 是非決定性的 gate 訊號。它的危害不只在延遲 merge，而是在心理上訓練團隊忽略紅燈；當真回歸出現時，大家也可能先按 rerun。治理目標是把 flaky 分類、隔離、修復，並保持 required checks 的語意可信。

| 階段     | 責任                           | 判讀訊號                           |
| -------- | ------------------------------ | ---------------------------------- |
| Detect   | 找出非決定性失敗               | 同 commit 重跑結果不一致           |
| Classify | 區分測試、環境、資料與產品問題 | failure pattern、log、trace        |
| Contain  | 降低對主線 gate 的污染         | quarantine、owner、expiry          |
| Fix      | 修掉根因                       | timing、isolation、mock、resource  |
| Re-admit | 恢復 gate 信任                 | 連續穩定、觀測窗口、owner sign-off |

Detect 階段負責證明 flakiness。單次失敗不應直接貼 flaky 標籤；要看同一 commit、同一測試、相近環境下是否出現 pass / fail 不一致，並保存 log、trace、screenshot 或 seed。

Classify 階段負責找根因方向。常見來源包含時間競態、測試順序依賴、共享狀態、外部服務、隨機資料、資源不足、瀏覽器 layout timing、網路模擬與 CI runner 差異；不同來源需要不同修法。

Contain 階段負責保護主線。高價值但暫時 flaky 的測試可以進 quarantine workflow，但必須有 owner、issue、到期日與 replacement gate；直接從 required checks 移除而不追蹤，等於降低品質基線。

Fix 階段負責消除非決定性。常見修法是移除固定 sleep、改用可觀察條件等待、隔離資料、固定 random seed、避免測試共享全域狀態、mock 不穩定外部依賴或調整資源限制。

Re-admit 階段負責把測試放回 gate。測試修完後應在多次 workflow、不同 runner 或足夠時間窗口中穩定通過，再恢復 required checks；否則 gate 會反覆被污染。

## 分類矩陣

分類矩陣的責任是讓 flaky issue 有明確修復路由。沒有分類時，團隊容易只留下「偶發失敗」這種不可執行標籤。

| 類型         | 常見訊號                       | 修復方向                               |
| ------------ | ------------------------------ | -------------------------------------- |
| Timing       | sleep 不足、元素尚未出現       | 等待可觀察條件、移除固定 sleep         |
| Shared state | 單跑通過、整批失敗             | 隔離資料、清理全域狀態                 |
| Order        | 測試順序改變後失敗             | 移除順序依賴、獨立 setup               |
| External     | 第三方 API、網路或時間服務不穩 | mock、contract fixture、retry boundary |
| Resource     | CI runner 負載高時失敗         | 降低 parallelism、設定 resource        |
| Product race | 真實功能存在競態               | 回到產品修復，不只改測試               |

這張表的邊界是：flaky 可能來自測試，也可能來自產品 race condition。若測試揭露的是產品 race condition，它應該被當成真 bug 處理。

## Quarantine 契約

Quarantine 的責任是暫時隔離污染，並維持 gate 的長期品質基線。隔離測試時，要把責任、期限與替代風險控制寫清楚。

1. 每個 quarantine test 必須有 issue 與 owner。
2. 每個 issue 必須標明分類、失敗證據與修復方向。
3. Required checks 若移除測試，要補 replacement gate 或風險說明。
4. Quarantine workflow 仍需定期跑，並回報趨勢。
5. 到期未修復時要重新評估：修、刪、改寫或降級測試責任。

這個契約讓 quarantine 成為治理工具。沒有期限與 owner 的 quarantine 會變成測試墓地，讓主線 gate 永久失去一部分覆蓋。

## Tripwire

Tripwire 的責任是提示 flaky 已經從局部問題變成流程問題。

- 團隊看到紅燈第一反應是 rerun：暫停重跑習慣，要求先分類失敗。
- 同一測試一週內多次 quarantine：提升到測試架構或產品 race 檢討。
- Required checks 常因環境問題失敗：檢查 runner、resource、cache 與外部依賴。
- Flaky issue 沒 owner 或沒期限：把 quarantine 視為未完成修復，不視為已處理。

## 下一步路由

- Flaky 術語：讀 [Flaky Test](/ci/knowledge-cards/flaky-test/)。
- Failure routing：讀 [CI 失敗到修復發布流程](../github-actions-failure-flow/)。
- Gate 邊界：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
