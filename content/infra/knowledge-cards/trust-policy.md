---
title: "Trust Policy"
date: 2026-06-26
description: "IAM role 的信任關係設定，規定哪個身分被允許 assume 這個 role"
weight: 18
tags: ["infra", "knowledge-cards"]
---

Trust policy 是附加在 [IAM](/infra/knowledge-cards/iam/) role 上的一份 JSON 文件，定義「誰被允許臨時取得（assume）這個 role 的權限」。跟 IAM policy 的差別是：IAM policy 描述「這個 role 能做什麼」，trust policy 描述「誰能變成這個 role」。兩者合在一起才構成完整的授權——先過 trust policy 的門、再受 IAM policy 的限。

## 概念位置

Trust policy 是 [OIDC](/infra/knowledge-cards/oidc/) 聯合的核心配件。當 CI/CD 平台（GitHub Actions、GitLab CI）要用短期憑證存取雲端資源時，trust policy 用 OIDC token 裡的 claim（issuer、audience、subject）決定「這個 token 代表的身分能不能 assume 這個 role」。

Trust policy 的設計要點是 claim 的收斂程度。只驗 issuer 而不驗 repo 和 branch，等於同一個 CI 平台上所有專案都能 assume 這個 role——這是常見的設定陷阱。收到最緊意味著限定到「某個 org 的某個 repo 的某個 branch 或 environment」。

## 可觀察訊號

`sts:AssumeRoleWithWebIdentity` 呼叫失敗、回傳 `AccessDenied` 時，問題通常在 trust policy 的 condition 比對不上。排查路徑是把 CI 平台簽發的 OIDC token decode（JWT 的 payload 部分），逐一比對 token 裡的 `iss`、`aud`、`sub` 跟 trust policy 的 condition 值。

另一個訊號是 trust policy 的 condition 用了 `StringLike` 但 pattern 太寬（如 `repo:my-org/*`），讓非預期的 repo 也能 assume——這類過寬的 trust policy 在安全稽核時會被標記。

## 設計責任

設計 trust policy 時要決定：允許哪些外部身分 assume（issuer + subject 的精確匹配）、audience 是否需要額外驗證（AWS 預設 `sts.amazonaws.com`）、以及是否把 plan role 和 apply role 分開（plan 只需 read-only、apply 需要 write，用兩個 role 各自設不同 trust condition 來區分 branch 或 environment）。

Trust policy 的變更跟 [IAM](/infra/knowledge-cards/iam/) policy 一樣要走 PR review——因為改寬一個 condition 就等於給更多外部身分開門。設定指南見 [OIDC Trust Policy 設定指南](/infra/02-identity-credentials/oidc-trust-policy-setup/)。

## 鄰卡

- [IAM](/infra/knowledge-cards/iam/) — trust policy 是 IAM role 的一部分
- [OIDC](/infra/knowledge-cards/oidc/) — trust policy 用 OIDC token 的 claim 做 assume 判斷
