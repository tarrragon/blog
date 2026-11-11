---
title: "SCP (Service Control Policy)"
date: 2026-06-26
description: "AWS Organizations 層級的權限天花板，套用到 OU 後連管理員都越不過"
weight: 16
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/scp/"]
---

Service Control Policy（SCP）是 AWS Organizations 裡套用在 OU 或帳號上的權限上限。SCP 不授予權限——它設定一個天花板，限制該範圍內的 IAM 能做什麼。即使帳號內有 `AdministratorAccess` 的 [IAM](/devops/infra/knowledge-cards/iam/) role，SCP deny 的操作仍然被擋下。

## 跟其他概念的關係

SCP 跟 [IAM](/devops/infra/knowledge-cards/iam/) policy 的關係是交集而非覆蓋：一個操作要同時被 SCP 允許且被 IAM policy 允許才會生效。SCP 的設計目的是讓組織管理者設定「即使帳號管理員也做不了」的護欄，常見的 day-1 SCP 包括：禁止關閉 CloudTrail、禁止離開指定 region、禁止刪除 VPC Flow Logs。

SCP 套用在 OU 上時會繼承給 OU 下所有帳號和子 OU。Management account（Organizations 的根帳號）不受 SCP 約束——這是設計上的逃生門，也是 management account 應該盡量不跑 workload 的原因。

## 可觀察訊號

當帳號內的 IAM role 執行某個操作時收到 `AccessDeniedException`、但該 role 的 IAM policy 確實允許該操作，SCP 是第一個要檢查的位置。另一個訊號是新帳號加入 OU 後某些原本能用的服務突然不可用——通常是繼承了 OU 的 SCP deny list。

## 判斷條件與後果

SCP 會繼承給 OU 底下每個帳號與子 OU，連帳號管理員都越不過，所以策略的寫法決定整個 OU 的帳號能做什麼。採 deny-list 策略（預設全開、明確列出禁止項）時，新服務不必改 SCP 就能用，維護量只跟禁止項的數量有關，代價是沒列進去的危險操作一律放行。採 allow-list 策略（預設全關、明確列出允許項）時，沒列到的服務一律被擋，範圍收得最緊，代價是每一次有新服務需求都要改一次 SCP。

一條 SCP 直接套到正在跑 workload 的 OU 時，它擋到的既有操作會在那一刻對 OU 底下的每個帳號同時失敗，錯誤是 `AccessDeniedException`，而那些帳號的 IAM policy 看起來都允許，排查要回頭找到 SCP 才看得出原因；先套在 sandbox OU、確認既有 workload 不受影響，失敗就只發生在 sandbox。SCP 的一行變更影響的帳號數跟 OU 的大小成正比，所以它跟 [IAM](/devops/infra/knowledge-cards/iam/) policy 一樣走 PR review。跨帳號策略的完整設計見[跨帳號策略文章](/devops/infra/02-identity-credentials/multi-account-strategy/)。

## 鄰卡

- [IAM](/devops/infra/knowledge-cards/iam/) — SCP 是 IAM policy 的上層天花板
- [環境分離](/devops/infra/knowledge-cards/environment-separation/) — SCP 靠 OU 結構實現環境之間的權限隔離
