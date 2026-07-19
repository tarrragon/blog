---
title: "流程測試"
date: 2026-07-17
description: "在假後端上驅動真實前端服務鏈、斷言散佈於業務旅程各階段的測試形態；與 unit / integration / E2E 的邊界劃分"
weight: 6
tags: ["testing", "flow-test", "strategy"]
---

流程測試驗證一段跨服務的業務旅程：在[語意級假後端](/testing/knowledge-cards/semantic-fake-backend/)上啟動真實的前端服務鏈，執行會改變後端狀態的業務操作，斷言散佈在旅程各階段的可觀察結果上——假後端的狀態變化、前端的狀態對齊、對外輸出的副作用。

## 概念位置

流程測試的 scope 介於 unit test 與 E2E 之間，驗證對象則自成一格：unit test 斷言單一元件的邏輯，E2E 經過 UI 驗證完整系統，流程測試跳過 UI（直接呼叫編排入口），在假後端上跑真實的多服務接力。相對於測試三層（unit / [protocol integration](/testing/knowledge-cards/protocol-integration-test/) / [screen state](/testing/knowledge-cards/screen-state-test/)），它是分層之外的補位形態——三層各自守一層的驗證責任，跨服務互動鏈落在層與層之間的縫隙。

## 可觀察訊號與例子

Bug 集中在服務接力的縫隙（各服務的 unit test 全綠，組合起來出錯）、或編排對順序與時序敏感。實例：套件首跑抓到修復自身引入的順序 bug（[T.C6](/testing/cases/flow-test-first-run-ordering-catch/)）、合跑暴露 [fire-and-forget 編排](/testing/knowledge-cards/fire-and-forget-orchestration/)的時序競態（[T.C8](/testing/cases/fire-and-forget-test-race/)）。

## 設計責任

流程測試開工前要過可測性閘門（編排入口能否在測試環境立起來）、確立驗證邊界（純 UI 互動排除在外）、維持隔離紀律（每條劇本重建假後端實例）。劇本模板與閘門判定的推導在[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)章。
