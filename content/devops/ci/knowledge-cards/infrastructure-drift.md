---
title: "Infrastructure Drift"
date: 2026-05-21
description: "說明真實基礎設施狀態與 IaC 宣告分叉時的偵測、判讀與修復責任"
tags: ["CD", "IaC", "platform", "drift", "knowledge-card"]
weight: 23
aliases: ["/ci/knowledge-cards/infrastructure-drift/"]
---

Infrastructure Drift 的核心概念是「真實環境狀態與宣告檔分叉」。它會削弱 [Environment Protection](/devops/ci/knowledge-cards/environment-protection/) 與 deployment review 的可信度，並影響下一次 plan / apply 的安全性。

## 跟其他概念的關係

Infrastructure Drift 位在 [IaC state](/devops/ci/knowledge-cards/state-lock/)、cloud resource、手動 hotfix 與外部 controller 之間，常由 console edit、事故修復、provider 預設值或自動調整造成。

## 可觀察訊號

- plan 顯示大量非預期變更。
- production 資源和 repository 宣告不一致。
- 下次 apply 可能覆蓋事故 hotfix。

## 接近真實服務的例子

事故中工程師在雲端 console 手動放寬 security group。服務恢復後，IaC plan 顯示 security group 與宣告檔不同；團隊需要判斷這個變更是短期 hotfix 還是應回寫成正式規則。

## 判斷條件與後果

Infrastructure drift 的處置取決於差異的性質：事故中手動放寬的 security group 是短期 hotfix 時，事故結束後由 apply 蓋回宣告檔的值；它應該成為正式規則時，要回寫進 repository。沒有回寫規則時，下一次 apply 會覆蓋 hotfix，事故的成因可能重新出現，原因是 apply 只依宣告檔決定資源該長什麼樣。偵測只在 apply 前順帶發生時，drift 存在的時間等於兩次 apply 的間隔，這段期間 deployment review 看的宣告檔跟真實環境不符；drift 沒有指定 owner 時，plan 裡的非預期變更持續累積，每一次 plan 都要有人重新分辨哪些變更是這次 PR 帶來的。
