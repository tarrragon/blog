---
title: "模組一：測試策略分層"
date: 2026-06-19
description: "Unit / Protocol Integration / Screen State 三層測試各自的職責、盲區和判斷原則"
weight: 1
tags: ["testing", "mock", "integration-test", "strategy"]
---

回答「什麼測試抓什麼問題」。三層測試各自有明確的職責和盲區。192 個 mock test 全過但實機全壞的根因在層級缺失，不在數量不足。

## 本模組回應的測試盲區

| 案例                                                          | 盲區與補位                                                |
| ------------------------------------------------------------- | --------------------------------------------------------- |
| [T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/)   | mock 模擬 API 層不模擬協議層 — 本模組的核心案例           |
| [T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/) | mock happy path 比真實服務寬鬆 → 功能缺失不可見           |
| [T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/) | 「名義 integration」全用 fake → 驗證內部狀態機非真實互動  |
| [T.C5](/testing/cases/stale-reference-stub-blindspot/)        | 由測試餵資料的 stub 回放作者假設 → 假設錯誤型 bug 不可見  |
| [T.C6](/testing/cases/flow-test-first-run-ordering-catch/)    | 流程測試讓資料走真實鏈路 → 首跑抓到單元測試繞過的順序 bug |

## 章節

- [三層定義與職責表](/testing/01-test-strategy-layers/three-layer-definition/) — Unit / Protocol Integration / Screen State 各層職責、驗證目標與盲區
- [Mock 遮蔽機制分析](/testing/01-test-strategy-layers/mock-masking-mechanism/) — API 層、協議層、環境層之間的斷裂點
- [「名義 integration test」的識別與修正](/testing/01-test-strategy-layers/nominal-integration-test/) — 名稱含 integration 但核心依賴全用 fake 的辨認與修正
- [判斷原則：什麼時候需要 protocol integration test](/testing/01-test-strategy-layers/when-protocol-integration-test/) — 協議複雜度、mock 寬鬆度、失敗靜默度三個維度的決策流程
- [反模式：用 mock 數量彌補 mock 盲區](/testing/01-test-strategy-layers/anti-pattern-mock-quantity/) — 數量與覆蓋率的真正關係
- [語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/) — stub 假設回放的補位形態、與模組三的真實後端驗證測試配對

## 跨分類引用

- → [monitoring 模組三 SDK 設計](/monitoring/03-sdk-design/)：SDK 的自動攔截機制影響哪些錯誤能被 test 覆蓋
- → [ux-design 模組一 畫面狀態機](/ux-design/01-screen-state-machine/)：狀態矩陣直接轉成 screen state test case
- ← [ux-design 模組二 Gate Fallback](/ux-design/02-gate-fallback/)：開發環境遮蔽 gate 問題的機制和 mock 遮蔽結構相同
- ← work-log 案例入口：[192 個測試全過、實機全壞](/work-log/testing_three_layer_strategy/)
