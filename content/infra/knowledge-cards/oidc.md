---
title: "OIDC 聯合"
date: 2026-06-26
description: "讓 CI/CD 平台用短期 token 取代長期 access key 存取雲端資源的身分聯合機制"
weight: 8
tags: ["infra", "knowledge-cards", "oidc", "security"]
---

OIDC（OpenID Connect）聯合的核心職責是讓跑在雲外的 CI/CD 平台（GitHub Actions、GitLab CI）用每次執行才簽發、幾分鐘後就失效的短期憑證存取雲端資源，從根本上消除「在 CI 環境裡存放長期 access key」這個攻擊面。

## 概念位置

OIDC 聯合在身分與憑證地基裡的角色是「雲外機器身分的認證機制」。跑在雲上的 workload（EC2、ECS task）可以用平台原生的 instance profile 或 task role 取得短期憑證；跑在雲外的 CI/CD 沒有這個管道，OIDC 就是替代方案。

運作方式是建立信任關係：雲端帳號信任某個外部 identity provider（如 GitHub Actions 的 OIDC issuer），CI 執行時平台簽發一個帶 claim 的 token（描述哪個 repo、哪個 branch、哪個 workflow），雲端用這個 token 換出一段臨時憑證。

## 可觀察訊號

以下狀況指向 OIDC 相關問題：

- CI pipeline 裡有 `AWS_ACCESS_KEY_ID` 和 `AWS_SECRET_ACCESS_KEY` 環境變數 — 這是長期 key，應該替換成 OIDC
- Trust policy 只驗 issuer 不驗 repo — 任何掛在同一個 CI 平台的專案都能假扮這個 role
- Pipeline 突然無法取得權限 — 可能是 trust policy 的 condition 跟 token claim 不匹配（常見於 repo 改名或 branch 改名後）

## 設計責任

設定 OIDC 聯合時要決定：

- **Trust policy 的 claim 收斂**：限定 issuer + audience + 特定 repo + 特定 branch，每個條件都收到最緊
- **Role 的權限範圍**：OIDC 換到的 role 仍然要遵循最小權限 — 只給 pipeline 需要的 action
- **Plan 與 apply 分開的 role**：plan 只需要 read 權限、apply 需要 write 權限，用兩個 role 降低 PR 階段的風險

## 鄰卡

- [IAM](/infra/knowledge-cards/iam/) — OIDC 是 IAM 身分系統的一種外部身分來源
- [Security Group](/infra/knowledge-cards/security-group/) — OIDC 解的是身分層的認證問題，跟網路層的 security group 正交
