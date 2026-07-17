---
title: "模組五：測試設計判斷"
date: 2026-06-19
description: "Mock 邊界判斷、assertion 設計、test data 代表性、flaky test 診斷"
weight: 5
tags: ["testing", "assertion", "flaky", "test-data", "mock"]
---

回答「這個斷言該怎麼寫」「這個 mock 邊界對嗎」。

## 本模組回應的測試盲區

| 案例                                                     | 盲區與補位                                                              |
| -------------------------------------------------------- | ----------------------------------------------------------------------- |
| [T.C3](/testing/cases/ansi-parser-test-data-blindspot/)  | 手寫測試資料是真實環境的乾淨子集                                        |
| [T.C3](/testing/cases/ansi-parser-test-data-blindspot/)  | Parser 透傳未知序列的靜默副作用                                         |
| [T.C8](/testing/cases/fire-and-forget-test-race/)        | fire-and-forget 編排讓測試單跑綠、合跑紅——對應 Flaky test 根因分類章    |
| [T.C9](/testing/cases/outbox-sequence-external-display/) | 序列斷言取代存在斷言、時序約束用索引比較鎖住——對應 Assertion 品質三問章 |

## 章節

- [Mock 邊界判斷決策表](/testing/05-test-design-judgment/mock-boundary-decision/) — 什麼時候 mock 夠用、什麼時候需要真實服務
- [Test data 代表性](/testing/05-test-design-judgment/test-data-representativeness/) — 手寫 vs 錄製 vs 生成三種測試資料來源
- [Assertion 品質三問](/testing/05-test-design-judgment/assertion-quality/) — 斷言的是行為嗎、能區分正確和錯誤嗎、會 flaky 嗎
- [Flaky test 根因分類](/testing/05-test-design-judgment/flaky-test-root-cause/) — 計時依賴 / 環境差異 / 資源競爭 / 非確定性
- [測試註解與命名紀律](/testing/05-test-design-judgment/test-comment-and-naming-discipline/) — 測試名稱與斷言說內容、註解只說操作約束、分析詞彙不入程式碼

## 跨分類引用

- → [monitoring 模組五 平台適配](/monitoring/05-platform-adaptation/)：各平台的 error 攔截機制差異影響 test 設計
