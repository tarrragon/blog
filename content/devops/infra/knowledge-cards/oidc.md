---
title: "OIDC Federation（OIDC 聯合）"
date: 2026-06-26
description: "讓 CI/CD 平台用短期 token 取代長期 access key 存取雲端資源的身分聯合機制"
weight: 8
tags: ["infra", "knowledge-cards", "oidc", "security"]
aliases: ["/infra/knowledge-cards/oidc/"]
---

OIDC（OpenID Connect）聯合的核心職責是讓跑在雲外的 CI/CD 平台（GitHub Actions、GitLab CI）用每次執行才簽發、幾分鐘後就失效的短期憑證存取雲端資源，從根本上消除「在 CI 環境裡存放長期 access key」這個攻擊面，信任關係的收斂條件寫在 [trust policy](/devops/infra/knowledge-cards/trust-policy/) 裡。

## 跟其他概念的關係

OIDC 聯合在身分與存取憑證地基裡的角色是「雲外機器身分的認證機制」。跑在雲上的 workload（EC2、ECS task）可以用平台原生的 [IAM](/devops/infra/knowledge-cards/iam/) instance profile 或 task role 取得短期憑證；跑在雲外的 CI/CD 沒有這個管道，OIDC 就是替代方案。

運作方式是建立信任關係：雲端帳號信任某個外部 identity provider（如 GitHub Actions 的 OIDC issuer），CI 執行時平台簽發一個帶 claim 的 token（描述哪個 repo、哪個 branch、哪個 workflow），雲端用這個 token 換出一段臨時憑證。

## 可觀察訊號

以下狀況指向 OIDC 相關問題：

- CI pipeline 裡有 `AWS_ACCESS_KEY_ID` 和 `AWS_SECRET_ACCESS_KEY` 環境變數 — 這是長期 key，應該替換成 OIDC
- Trust policy 只驗 issuer 不驗 repo — 任何掛在同一個 CI 平台的專案都能假扮這個 role
- Pipeline 突然無法取得權限 — 可能是 trust policy 的 condition 跟 token claim 不匹配（常見於 repo 改名或 branch 改名後）

## 判斷條件與後果

OIDC 聯合拿掉了 CI 環境裡的長期 access key，風險因此移到兩個位置：哪些 token 換得到 role，以及換到之後能做什麼。下面三項設定各自決定其中一個位置的範圍：

- **Trust policy 的 claim**：只驗 issuer 時，同一個 CI 平台上任何一個專案的 token 都換得到這個 role；再限定 audience、特定 repo 與特定 branch 之後，只有那個 repo 的那個 branch 換得到。代價是 repo 或 branch 改名時 claim 不再匹配，pipeline 會突然取不到權限
- **Role 的權限範圍**：短期憑證縮短的是外洩之後能用的時間，能做的事仍由 role 的權限決定；role 給了 pipeline 用不到的 action 時，憑證有效的那幾分鐘裡，被濫用的範圍就是整個 role 的權限
- **Plan 與 apply 的 role**：plan 只需要 read 權限，apply 需要 write 權限。兩者共用一個有 write 權限的 role 時，PR 階段跑 plan 的 pipeline 也拿著寫入權限，能開 PR 改 workflow 的人就能用它寫入；分成兩個 role 之後，PR 階段只拿得到 read

## 鄰卡

- [IAM](/devops/infra/knowledge-cards/iam/) — OIDC 是 IAM 身分系統的一種外部身分來源
- [Security Group](/devops/infra/knowledge-cards/security-group/) — OIDC 解的是身分層的認證問題，跟網路層的 security group 正交
