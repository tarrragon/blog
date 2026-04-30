---
title: "7.B5 Detection Engineering Lifecycle"
tags: ["Blue Team", "Detection Engineering", "Detection Rule", "Lifecycle"]
date: 2026-04-30
description: "把偵測規則視為可維護資產，建立從來源、測試、調校到退場的完整生命週期"
weight: 724
---

本篇的責任是建立偵測規則生命週期。讀者讀完後，能把一條 detection rule 從來源定義、驗證、調校、上線、退場整理成可維護流程。

## 核心論點

Detection engineering lifecycle 的核心概念是把規則當資產管理。規則資產包含來源、邏輯、測試、誤報處理、owner、驗收門檻與退場條件。

## 讀者入口

本篇適合銜接 [7.B2 從偵測到回應的路由](/backend/07-security-data-protection/blue-team/detection-to-response-routing/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 與 [Sigma：偵測規則生命週期素材](/backend/07-security-data-protection/blue-team/materials/professional-sources/sigma-detection-rule-lifecycle/)。

## 生命周期欄位

| 欄位                 | 責任                             | 常見來源                                                         |
| -------------------- | -------------------------------- | ---------------------------------------------------------------- |
| Rule source          | 描述規則來自哪個威脅假設與資料源 | Sigma、事件復盤、演練結果                                        |
| Detection logic      | 定義條件、例外、聚合方式         | rule repository、query package                                   |
| Validation evidence  | 證明規則可命中目標情境           | 測試事件、回放資料、對照 log                                     |
| Tuning decision      | 收斂誤報與漏報                   | triage 結果、分析註記、例外記錄                                  |
| Release condition    | 定義規則上線條件                 | [release gate](/backend/knowledge-cards/release-gate/)、變更審查 |
| Retirement condition | 定義規則退場條件                 | 覆蓋重疊、威脅變化、資料源變動                                   |

生命周期欄位的核心是讓規則維護可以追溯。每次規則更新都能回查它解哪個風險、用哪個證據驗證、為何做這次調整。

## 規則來源治理

規則來源治理的責任是讓規則與威脅假設對齊。來源可來自公開框架、事件教訓、演練情境與稽核要求，並需要在建立時寫清楚 threat hypothesis 與 data dependency。

## 驗證節奏

驗證節奏的責任是確保規則在上線前後都保持有效。建議至少建立三層驗證：

1. 邏輯驗證：條件可讀、可測、可重現。
2. 資料驗證：log schema 與欄位品質可支撐判讀。
3. 情境驗證：在事件回放或 game day 中能命中目標行為。

## 調校策略

調校策略的責任是把 alert 噪音轉成可判讀訊號。調校時同步記錄 false positive 情境、排除條件、影響範圍與回退方式，並和 [incident severity](/backend/knowledge-cards/incident-severity/) 對齊分級節奏。

## 上線與退場

上線與退場的責任是讓規則變更進入受控流程。上線前需確認 evidence、owner 與回退路徑；退場時要確認替代規則、覆蓋遷移與歷史證據保留。

## 與事故流程的交接

與事故流程交接的責任是把規則命中轉成回應路由。規則命中後應直接輸出 triage 問題、owner、升級條件與 [runbook](/backend/knowledge-cards/runbook/) 路由，讓 08 模組可以快速接手。

## 判讀訊號與路由

| 判讀訊號                   | 代表需求                   | 下一步路由  |
| -------------------------- | -------------------------- | ----------- |
| 規則持續觸發但分析結論分散 | 需要調校紀錄與 triage 問題 | 7.B5 → 7.B2 |
| 規則上線後缺少驗證證據     | 需要補 validation evidence | 7.B5 → 7.B3 |
| 相同風險出現多條重複規則   | 需要整理來源與退場條件     | 7.B5 → 7.B1 |
| 規則變更未進入放行流程     | 需要 release condition     | 7.B5 → 05   |
| 事故後規則未更新           | 需要 write-back 閉環       | 7.B5 → 7.24 |

判讀表格的作用是把規則問題轉成維護任務。每一列都能直接對應到 owner 與下一步交接章節。

## 必連章節

- [7.B2 從偵測到回應的路由](/backend/07-security-data-protection/blue-team/detection-to-response-routing/)
- [7.B3 資安控制驗證](/backend/07-security-data-protection/blue-team/security-control-validation/)
- [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- [7.BM1 藍隊專業來源卡](/backend/07-security-data-protection/blue-team/materials/professional-sources/)

## 完稿判準

完稿時要讓讀者能為一條偵測規則設計完整生命週期。輸出至少包含來源、邏輯、驗證證據、調校策略、上線條件、退場條件與回寫位置。
