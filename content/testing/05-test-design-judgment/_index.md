---
title: "模組五：測試設計判斷"
date: 2026-06-19
description: "Mock 邊界判斷、assertion 設計、test data 代表性、flaky test 診斷"
weight: 5
tags: ["testing", "assertion", "flaky", "test-data", "mock"]
---

回答「這個斷言該怎麼寫」「這個 mock 邊界對嗎」。

## 對應 findings

| Finding | 來源                                                    | 內容                             |
| ------- | ------------------------------------------------------- | -------------------------------- |
| TF-4    | [T.C3](/testing/cases/ansi-parser-test-data-blindspot/) | 手寫測試資料是真實環境的乾淨子集 |
| TF-5    | [T.C3](/testing/cases/ansi-parser-test-data-blindspot/) | Parser 透傳未知序列的靜默副作用  |

## 待寫章節

- [x] Mock 邊界判斷決策表（什麼時候 mock 夠、什麼時候需要 real）
- [x] Test data 代表性（手寫 vs 錄製 vs 生成）
- [x] Assertion 品質三問（斷言的是行為嗎？能區分正確和錯誤嗎？會 flaky 嗎？）
- [x] Flaky test 根因分類（計時依賴 / 環境差異 / 資源競爭 / 非確定性）

## 跨分類引用

- → [monitoring 模組五 平台適配](/monitoring/05-platform-adaptation/)：各平台的 error 攔截機制差異影響 test 設計
