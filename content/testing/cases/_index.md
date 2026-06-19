---
title: "開發測試案例庫"
date: 2026-06-19
description: "測試策略失效、mock 遮蔽、協議契約違反、客戶端可觀測性缺口的實戰案例"
weight: 90
tags: ["testing", "case-study"]
---

這個資料夾收錄測試策略的實戰案例 — 重點不在「測試怎麼寫」，而在「測試為什麼沒抓到問題」。每個案例記錄一個真實的測試盲區、分析遮蔽機制、提出可重用的防護策略。

案例來源分兩類：

- **自有案例**：app_tunnel 專案的實機測試教訓（first-party，有完整程式碼和 commit 歷史）
- **外部案例**：開源專案和社群的已知測試陷阱（third-party，引用公開來源）

## 案例覆蓋缺口

以下章節目前公開 case 稀薄，Stage 0 採集後視覆蓋情況補強：

| 章節                     | 缺口                                       | 備註                                     |
| ------------------------ | ------------------------------------------ | ---------------------------------------- |
| 模組二（客戶端可觀測性） | 自架 log endpoint 的實戰案例               | 多數公開案例偏商業方案（Sentry/Datadog） |
| 模組四（自動化 UI 驗證） | widget test 狀態覆蓋的 false negative 案例 | 待採集 Flutter/React 社群案例            |
| 模組五（測試設計判斷）   | flaky test 根因分類的量化案例              | CI 平台有公開統計但散落                  |

## 案例列表

| 案例                                                          | 主題                                     | 來源       | 測試層               | 遮蔽機制               |
| ------------------------------------------------------------- | ---------------------------------------- | ---------- | -------------------- | ---------------------- |
| [T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/)   | WebSocket text/binary frame 被 mock 遮蔽 | app_tunnel | protocol-integration | mock 不區分 frame type |
| [T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/) | Auth handshake 邏輯缺失被 mock 遮蔽      | app_tunnel | protocol-integration | mock 不需認證          |

待補案例（Stage 0 後續輪次）：

- T.C3：ANSI parser 測試資料不覆蓋真實 shell output（unit-test-data 盲區）
- T.C4：Client-side log 缺失導致 debug 只能靠實機（可觀測性缺口）
