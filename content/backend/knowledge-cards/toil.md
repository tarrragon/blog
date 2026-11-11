---
title: "Toil"
tags: ["Toil", "重複手動工作"]
date: 2026-05-02
description: "說明重複、手動、無永久價值的工作如何成為工程治理對象"
weight: 316
---

Toil 的核心概念是「重複、手動、無永久價值、可自動化的工作」。它通常和 [on-call](/backend/knowledge-cards/on-call/) 壓力、[alert fatigue](/backend/knowledge-cards/alert-fatigue/) 與 [runbook](/backend/knowledge-cards/runbook/) 綁在一起。

## 跟其他概念的關係

Toil 位在 [alert-fatigue](/backend/knowledge-cards/alert-fatigue/)、[runbook](/backend/knowledge-cards/runbook/) 與 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 之間。它把反覆出現的手動修復工作，轉成能被自動化或系統性消除的治理對象。

## 可觀察訊號與例子

系統需要 toil 治理的訊號是值班時間被重複修復工作吃掉，且每次事故後都只是多一個手動步驟。常見例子包括固定重啟、手動 replay、人工清 queue、或每週都要補同一份報表。

## 判斷條件與後果

一項 toil 是否值得先處理，看它重複的頻率與自動化的成本：固定重啟、每週補同一份報表這類高頻工作，自動化之後省下的值班時間逐週累積；很少出現的手動步驟，自動化的成本可能高過省下的時間，所以消滅所有手工流程既不必要也不現實。一項 toil 沒有 owner 時，它留在清單上，每次事故後只多一個手動步驟；沒有替代路徑（自動化、修掉根因或直接取消這項工作）時，它沒有方式離開清單；沒有移除條件時，無法判斷它何時算處理完。這四項齊備時，沒有長期價值的重複成本才會逐項減少。
