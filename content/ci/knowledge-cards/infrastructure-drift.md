---
title: "Infrastructure Drift"
date: 2026-05-21
description: "說明真實基礎設施狀態與 IaC 宣告分叉時的偵測、判讀與修復責任"
tags: ["CD", "IaC", "platform", "drift", "knowledge-card"]
weight: 23
---

Infrastructure Drift 的核心概念是「真實環境狀態與宣告檔分叉」。它會削弱 [Environment Protection](/ci/knowledge-cards/environment-protection/) 與 deployment review 的可信度，並影響下一次 plan / apply 的安全性。

## 概念位置

Infrastructure Drift 位在 IaC state、cloud resource、手動 hotfix 與外部 controller 之間，常由 console edit、事故修復、provider 預設值或自動調整造成。

## 可觀察訊號

- plan 顯示大量非預期變更。
- production 資源和 repository 宣告不一致。
- 下次 apply 可能覆蓋事故 hotfix。

## 接近真實服務的例子

事故中工程師在雲端 console 手動放寬 security group。服務恢復後，IaC plan 顯示 security group 與宣告檔不同；團隊需要判斷這個變更是短期 hotfix 還是應回寫成正式規則。

## 設計責任

Infrastructure Drift 要定義偵測頻率、owner、修復路由、state repair 與回寫規則，讓平台狀態重新回到可審查流程。
