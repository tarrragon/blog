---
title: "Semantic Fake Backend（語意級假後端）"
date: 2026-07-17
description: "持有狀態、只固化已證實後端行為的測試假件；與由測試餵資料的 stub 以狀態歸屬和行為出處劃界"
weight: 5
tags: ["testing", "fake-backend", "test-double"]
---

語意級假後端是一個持有狀態、只固化已證實後端行為的測試假件：多個前端服務對它走完整的互動鏈，每個操作演變它內部的狀態。在 test double 分類中它對應 Fowler 定義的 fake（有狀態、可運作的簡化實作），「語意級」限定的是行為出處——每一條行為都經過實測證實。它是[流程測試](/testing/knowledge-cards/flow-test/)的地基，與[真實後端驗證測試](/testing/knowledge-cards/real-backend-verification-test/)配對運作。

## 概念位置

與「由測試餵資料的 stub」的分界有兩條：狀態的歸屬（stub 的回應由測試作者逐條寫死，假後端自己持有狀態並隨操作演變）、行為的出處（stub 回放作者對後端的假設，假後端只收錄實測證實的後端行為）。它與 [mock 遮蔽](/testing/knowledge-cards/mock-masking/)批評的「讓 mock 更逼真」處在相異層次：假後端的模擬止於應用層行為，協議層仍歸 [protocol integration test](/testing/knowledge-cards/protocol-integration-test/)。

## 可觀察訊號與例子

多個前端服務對同一份後端狀態接力，且出現過「對後端行為假設錯誤」型的漏網 bug。典型例：後端合併資料時重建全部子項並更換 id，前端依賴[凍結參照](/testing/knowledge-cards/frozen-vs-live-reference/)的錯誤在 stub 上永遠測不紅（[T.C5](/testing/cases/stale-reference-stub-blindspot/)）。

## 設計責任

假後端要決定掛載接縫（in-process 假實作或本地假 server）、行為取證方式、與配對慣例——每一條行為假設對應一條真實後端驗證斷言。掛載判準、取證選單與成本量級的推導在[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)章。
