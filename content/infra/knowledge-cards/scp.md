---
title: "SCP (Service Control Policy)"
date: 2026-06-26
description: "AWS Organizations 層級的權限天花板，套用到 OU 後連管理員都越不過"
weight: 16
tags: ["infra", "knowledge-cards"]
---

Service Control Policy（SCP）是 AWS Organizations 裡套用在 OU 或帳號上的權限上限。SCP 不授予權限——它設定一個天花板，限制該範圍內的 IAM 能做什麼。即使帳號內有 `AdministratorAccess` 的 IAM role，SCP deny 的操作仍然被擋下。

## 概念位置

SCP 跟 [IAM](/infra/knowledge-cards/iam/) policy 的關係是交集而非覆蓋：一個操作要同時被 SCP 允許且被 IAM policy 允許才會生效。SCP 的設計目的是讓組織管理者設定「即使帳號管理員也做不了」的護欄，常見的 day-1 SCP 包括：禁止關閉 CloudTrail、禁止離開指定 region、禁止刪除 VPC Flow Logs。

SCP 套用在 OU 上時會繼承給 OU 下所有帳號和子 OU。Management account（Organizations 的根帳號）不受 SCP 約束——這是設計上的逃生門，也是 management account 應該盡量不跑 workload 的原因。

## 可觀察訊號

當帳號內的 IAM role 執行某個操作時收到 `AccessDeniedException`、但該 role 的 IAM policy 確實允許該操作，SCP 是第一個要檢查的位置。另一個訊號是新帳號加入 OU 後某些原本能用的服務突然不可用——通常是繼承了 OU 的 SCP deny list。

## 設計責任

SCP 的設計要決定：用 deny-list 策略（預設全開、明確列出禁止項）還是 allow-list 策略（預設全關、明確列出允許項）。Deny-list 較常見也較易維護——只需要管「哪些該禁」。Allow-list 更嚴格但維護成本高——每次有新服務需求都要更新 SCP。

套用 SCP 前要確認不會擋到正在運作的服務——先在 sandbox OU 測試，確認既有 workload 不受影響再推到 workload OU。SCP 的變更跟 [IAM](/infra/knowledge-cards/iam/) 一樣要走 PR review。跨帳號策略的完整設計見[跨帳號策略文章](/infra/02-identity-credentials/multi-account-strategy/)。

## 鄰卡

- [IAM](/infra/knowledge-cards/iam/) — SCP 是 IAM policy 的上層天花板
- [環境分離](/infra/knowledge-cards/environment-separation/) — SCP 靠 OU 結構實現環境之間的權限隔離
