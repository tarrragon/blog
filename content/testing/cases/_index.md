---
title: "開發測試案例庫"
date: 2026-06-19
description: "測試策略失效、mock 遮蔽、協議契約違反、客戶端可觀測性缺口的實戰案例"
weight: 90
tags: ["testing", "case-study"]
---

這個資料夾收錄測試策略的實戰案例，聚焦兩個問題：「測試為什麼沒抓到問題」、以及「換了測試形態之後怎麼抓到」。每個案例記錄一個真實的測試盲區、分析成因機制、提出可重用的防護策略。

案例來源分三類：

- **自有案例**：app_tunnel 專案的實機測試教訓（first-party，有完整程式碼和 commit 歷史）
- **匿名自有案例**：另一個 APP 專案（前端＋後端 API）的測試建置教訓（first-party，情節完整但不揭露專案與程式碼）
- **外部案例**：開源專案和社群的已知測試陷阱（third-party，引用公開來源）

## 案例覆蓋缺口

以下章節目前公開 case 稀薄，Stage 0 採集後視覆蓋情況補強：

| 章節                     | 缺口                                       | 備註                                                        |
| ------------------------ | ------------------------------------------ | ----------------------------------------------------------- |
| 模組二（客戶端可觀測性） | 自架 log endpoint 的實戰案例               | 多數公開案例偏商業方案（Sentry/Datadog）                    |
| 模組四（自動化 UI 驗證） | widget test 狀態覆蓋的 false negative 案例 | 待採集 Flutter/React 社群案例                               |
| 模組五（測試設計判斷）   | flaky test 根因分類的量化案例              | 質性面已由 T.C8 填補；量化案例仍缺，CI 平台有公開統計但散落 |

## 案例列表

| 案例                                                          | 主題                                        | 來源          | 測試層               | 機制                       |
| ------------------------------------------------------------- | ------------------------------------------- | ------------- | -------------------- | -------------------------- |
| [T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/)   | WebSocket text/binary frame 被 mock 遮蔽    | app_tunnel    | protocol-integration | mock 不區分 frame type     |
| [T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/) | Auth handshake 邏輯缺失被 mock 遮蔽         | app_tunnel    | protocol-integration | mock 不需認證              |
| [T.C3](/testing/cases/ansi-parser-test-data-blindspot/)       | ANSI parser 測試資料不覆蓋真實 shell output | app_tunnel    | unit-test-data       | 手寫測試字串是乾淨子集     |
| [T.C4](/testing/cases/client-log-absent-debug-cost/)          | Client-side log 缺失導致 debug 只能靠實機   | app_tunnel    | observability        | 企劃階段未設計 log 點      |
| [T.C5](/testing/cases/stale-reference-stub-blindspot/)        | 凍結參照失效被 stub 遮蔽，測試全綠功能全壞  | 匿名 APP 專案 | fake-backend         | stub 回放測試作者的假設    |
| [T.C6](/testing/cases/flow-test-first-run-ordering-catch/)    | 流程測試首跑抓到修復自己引入的順序 bug      | 匿名 APP 專案 | flow-test            | 單測直接塞狀態、繞過過濾鏈 |
| [T.C7](/testing/cases/dual-semantics-attribution/)            | 症狀相同成因兩種——用測試切開前後端責任      | 匿名 APP 專案 | real-backend         | 畫面殘留與後端未做無法區分 |
| [T.C8](/testing/cases/fire-and-forget-test-race/)             | fire-and-forget 編排讓測試單跑綠合跑紅      | 匿名 APP 專案 | flaky                | 斷言與未等待的背景收尾賽跑 |
| [T.C9](/testing/cases/outbox-sequence-external-display/)      | 外接螢幕漏通知——訊息序列斷言與訂閱盲區      | 匿名 APP 專案 | sequence-assertion   | 顯式呼叫路徑無人提醒補推送 |
