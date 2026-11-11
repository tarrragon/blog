---
title: "Least Privilege"
date: 2026-04-23
description: "說明身份、服務與人員只應取得完成工作所需的最小權限"
weight: 120
---

Least privilege 的核心概念是「每個身份只取得完成工作所需的最小權限」。身份可以是使用者、管理員、service account、CI job、database user 或第三方 integration。 可先對照 [Load Balancer Contract](/backend/knowledge-cards/load-balancer-contract/)。

## 跟其他概念的關係

Least privilege 是權限模型與事故限縮工具。權限越大，credential 洩漏、程式 bug 或人為操作的影響範圍越大。 可先對照 [Load Balancer Contract](/backend/knowledge-cards/load-balancer-contract/)。

## 可觀察訊號與例子

系統需要 least privilege 的訊號是多個服務共用同一把高權限 credential。報表服務只需要讀取訂單摘要時，應使用專門的唯讀資料庫帳號。

## 判斷條件與後果

權限沒有依角色、服務、環境與資源切開時，一把 credential 的影響範圍是這幾個維度的聯集：報表服務與訂單服務共用一把高權限資料庫帳號，報表服務的 bug 或 credential 洩漏就能改寫訂單；測試環境的帳號動得到正式環境時，一次測試操作的影響範圍包含正式資料。切開之後，權限仍會隨時間偏離最小範圍：沒有權限審查時，換了工作的身份保留著原本的權限；沒有 credential rotation 與撤銷流程時，外洩的 credential 一直有效；沒有異常操作的 audit 時，被濫用的權限查不出是誰在什麼時候用的。所以 runbook 收進這四項。
