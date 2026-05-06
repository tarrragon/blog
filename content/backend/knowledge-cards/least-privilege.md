---
title: "Least Privilege"
date: 2026-04-23
description: "說明身份、服務與人員只應取得完成工作所需的最小權限"
weight: 119
---


Least privilege 的核心概念是「每個身份只取得完成工作所需的最小權限」。身份可以是使用者、管理員、service account、CI job、database user 或第三方 integration。 可先對照 [Load Balancer Contract](/backend/knowledge-cards/load-balancer-contract/)。

## 概念位置

Least privilege 是權限模型與事故限縮工具。權限越大，credential 洩漏、程式 bug 或人為操作的影響範圍越大。 可先對照 [Load Balancer Contract](/backend/knowledge-cards/load-balancer-contract/)。

## 可觀察訊號與例子

系統需要 least privilege 的訊號是多個服務共用同一把高權限 credential。報表服務只需要讀取訂單摘要時，應使用專門的唯讀資料庫帳號。

## 設計責任

權限設計要分角色、分服務、分環境、分資源。Runbook 應包含權限審查、credential rotation、撤銷流程與異常操作 audit。
