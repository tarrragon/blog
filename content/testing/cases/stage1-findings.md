---
title: "Stage 1 Findings：測試策略案例 audit"
date: 2026-06-19
draft: true
description: "Case-first Stage 1 產物 — 從 T.C1~C4 四個 rich case 抽取 9 個 findings，標明 fact vs derive 分層和對應章節"
tags: ["testing", "case-first", "stage-1"]
---

## Findings 表

| #    | Finding                                                                                            | Case    | 對應模組 | Fact / Derive                |
| ---- | -------------------------------------------------------------------------------------------------- | ------- | -------- | ---------------------------- |
| TF-1 | mock 模擬 Dart API 層（`sink.add(dynamic)`），不模擬 WS 協議層（opcode）——兩層語意差距是結構性盲區 | T.C1    | 模組一   | Fact                         |
| TF-2 | mock happy path 比真實服務寬鬆時，功能缺失（非功能錯誤）變得不可見                                 | T.C2    | 模組一   | Fact                         |
| TF-3 | 「名義 integration test」全用 fake（3 依賴全替換），驗證內部狀態機而非真實互動                     | T.C2    | 模組一   | Fact                         |
| TF-4 | 手寫測試資料是真實環境的乾淨子集——18 test 覆蓋 1 類序列，真實環境 5+ 類                            | T.C3    | 模組五   | Fact                         |
| TF-5 | Parser「透傳」未知序列是合理設計，但透傳的靜默副作用不觸發 log                                     | T.C3    | 模組五   | Derive（tension 是本章合成） |
| TF-6 | 6 元件中 4 個零 log，2 個的 log 全是 W2 hotfix                                                     | T.C4    | 模組二   | Fact                         |
| TF-7 | 事後補的 developer.log 格式不統一——救火工具品質 vs 設計產物品質                                    | T.C4    | 模組二   | Fact                         |
| TF-8 | 自用工具 server+client 同機：protocol integration test 成本極低                                    | T.C1+C2 | 模組三   | Derive（成本判斷）           |
| TF-9 | log 設計應在功能規格階段完成（跟 API schema 同級）                                                 | T.C4    | 模組二   | Derive（方法論主張）         |

## SSoT 對應

| Frame                    | 主寫章節       | 其他章節 link        |
| ------------------------ | -------------- | -------------------- |
| mock 模擬 API 不模擬協議 | testing 模組一 | testing 模組三引用   |
| log 設計是功能規格一部分 | testing 模組二 | ux-design 模組一引用 |
