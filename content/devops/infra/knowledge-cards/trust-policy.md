---
title: "Trust Policy"
date: 2026-06-26
description: "IAM role 的信任關係設定，規定哪個身分被允許 assume 這個 role"
weight: 18
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/trust-policy/"]
---

Trust policy 是附加在 [IAM](/devops/infra/knowledge-cards/iam/) role 上的一份 JSON 文件，定義「誰被允許臨時取得（assume）這個 role 的權限」。跟 IAM policy 的差別是：IAM policy 描述「這個 role 能做什麼」，trust policy 描述「誰能變成這個 role」。兩者合在一起才構成完整的授權——先過 trust policy 的門、再受 IAM policy 的限。

## 跟其他概念的關係

Trust policy 是 [OIDC](/devops/infra/knowledge-cards/oidc/) 聯合的核心配件。當 CI/CD 平台（GitHub Actions、GitLab CI）要用短期憑證存取雲端資源時，trust policy 用 OIDC token 裡的 claim（issuer、audience、subject）決定「這個 token 代表的身分能不能 assume 這個 role」。

Trust policy 的設計要點是 claim 的收斂程度。只驗 issuer 而不驗 repo 和 branch，等於同一個 CI 平台上所有專案都能 assume 這個 role——這是常見的設定陷阱。收到最緊意味著限定到「某個 org 的某個 repo 的某個 branch 或 environment」。

## 可觀察訊號

`sts:AssumeRoleWithWebIdentity` 呼叫失敗、回傳 `AccessDenied` 時，問題通常在 trust policy 的 condition 比對不上。排查路徑是把 CI 平台簽發的 OIDC token decode（JWT 的 payload 部分），逐一比對 token 裡的 `iss`、`aud`、`sub` 跟 trust policy 的 condition 值。

另一個訊號是 trust policy 的 condition 用了 `StringLike` 但 pattern 太寬（如 `repo:my-org/*`），讓非預期的 repo 也能 assume——這類過寬的 trust policy 在安全稽核時會被標記。

## 判斷條件與後果

trust policy 只管哪些身分能取得這個 role，取得之後能做什麼由 role 的 IAM policy 另外限制，所以 trust policy 的條件都寫在 token 的 claim 上。條件只比對 issuer、沒有精確比對 subject 時，同一個 CI 平台上任何專案簽出的 token 都能 assume 這個 role；subject 精確到某個 repo 的某個 branch 或 environment 時，能 assume 的只剩那一條流水線。audience 沒有驗證時（AWS 的預設值是 `sts.amazonaws.com`），發給別的接收方的 token 也會被接受。plan 與 apply 共用一個 role 時，任何分支跑 plan 都拿得到 write 權限；拆成只有 read-only 的 plan role 與有 write 權限的 apply role、兩者的 trust condition 限定不同的 branch 或 environment 時，沒有合併進主線的分支只拿得到讀取權限。

改寬 trust policy 的一個 condition，能 assume 這個 role 的外部身分就跟著變多，而這個變化在 IAM policy 那一邊看不出來，所以 trust policy 的變更跟 [IAM](/devops/infra/knowledge-cards/iam/) policy 一樣走 PR review。設定指南見 [OIDC Trust Policy 設定指南](/devops/infra/02-identity-credentials/oidc-trust-policy-setup/)。

## 鄰卡

- [IAM](/devops/infra/knowledge-cards/iam/) — trust policy 是 IAM role 的一部分
- [OIDC](/devops/infra/knowledge-cards/oidc/) — trust policy 用 OIDC token 的 claim 做 assume 判斷
