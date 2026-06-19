---
title: "模組一：測試策略分層"
date: 2026-06-19
description: "Unit / Protocol Integration / Screen State 三層測試各自的職責、盲區和判斷原則"
weight: 1
tags: ["testing", "mock", "integration-test", "strategy"]
---

回答「什麼測試抓什麼問題」。三層測試各自有明確的職責和盲區。192 個 mock test 全過但實機全壞的根因在層級缺失，不在數量不足。

## 對應 findings

| Finding | 來源                                                          | 內容                                                     |
| ------- | ------------------------------------------------------------- | -------------------------------------------------------- |
| TF-1    | [T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/)   | mock 模擬 API 層不模擬協議層 — **本模組主寫**            |
| TF-2    | [T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/) | mock happy path 比真實服務寬鬆 → 功能缺失不可見          |
| TF-3    | [T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/) | 「名義 integration」全用 fake → 驗證內部狀態機非真實互動 |

## 待寫章節

- [x] 三層定義與職責表（從 _index.md 的表格擴展為完整論述）
- [x] Mock 遮蔽機制分析（API 層 vs 協議層 vs 環境層的斷裂點）
- [x] 「名義 integration test」的識別與修正
- [x] 判斷原則：什麼時候需要 protocol integration test（決策表）
- [x] 反模式：用 mock 數量彌補 mock 盲區

## 跨分類引用

- → [monitoring 模組三 SDK 設計](/monitoring/03-sdk-design/)：SDK 的自動攔截機制影響哪些錯誤能被 test 覆蓋
- → [ux-design 模組一 畫面狀態機](/ux-design/01-screen-state-machine/)：狀態矩陣直接轉成 screen state test case
- ← [ux-design 模組二 Gate Fallback](/ux-design/02-gate-fallback/)：開發環境遮蔽 gate 問題的機制和 mock 遮蔽結構相同
- ← work-log 案例入口：[192 個測試全過、實機全壞](/work-log/testing_three_layer_strategy/)
