---
title: "AWS Secrets Manager"
date: 2026-05-18
description: "AWS 原生 secret store + 內建 RDS / Redshift rotation Lambda、Resource Policy 跨帳號共享、KMS 加密"
weight: 2
tags: ["backend", "security", "vendor", "aws-secrets-manager", "secret-management", "aws"]
---

AWS Secrets Manager 是 AWS 原生的 *static secret 集中保管 service*、核心能力是把 secret 用 [KMS](/backend/07-security-data-protection/vendors/aws-kms/) 加密儲存、加上 *built-in rotation Lambda*（針對 RDS / Redshift / DocumentDB）跟 *Resource Policy + IAM Policy 雙層 grant*、把 secret lifecycle 鎖在 AWS account / IAM 邊界內。設計取捨跟 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 不同 — Secrets Manager 不做 dynamic credential、不做 transit encryption、不做內部 PKI、只把 *static secret + AWS native DB rotation* 這條路徑做到極致。

## 服務定位

Secrets Manager 的定位是 *AWS-only workload 的 static secret 控制面*、跟 [SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/) SecureString 在 *存 secret* 這層功能重疊、但設計目的不同。Parameter Store 是 *parameter 管理*（free tier、advanced parameter 每 10000 個約 $0.05、KMS 加密但無 staging label 與 rotation Lambda）；Secrets Manager 是 *secret 管理*（每個 secret per month $0.40 + API call、有 staging label / rotation Lambda / Resource Policy / Cross-Region Replica）。價差 8 倍以上、選擇基準在 *是否需要 rotation 跟 cross-account sharing*。

跟 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 比、Secrets Manager 是 *單一雲、簡單、低運維*、Vault 是 *跨雲、dynamic credential、高表達力*。AWS-only 組織用 Vault 等於多扛一個 HA cluster 運維成本只為了拿 KV engine 跟 RDS rotation、ROI 不划算；反向跨雲組織用 Secrets Manager 等於每個雲都自己一套 secret store、治理鏈會斷。跟 [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) / [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/) 比、設計理念類似（雲廠 managed、KMS 加密、IAM 授權）但 rotation 機制各家不同 — Secrets Manager 用 built-in Lambda 四階段 flow、GSM 用 Pub/Sub event 觸發自寫 Cloud Function、Azure 用 Key Vault rotation policy + Event Grid。

## 本章目標

讀完本頁、讀者能判斷：

1. 哪些 secret 用 Secrets Manager、哪些可以下放到 Parameter Store、哪些該走 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 的 dynamic credential
2. Secrets Manager 的 *雙層 grant 模型*（Resource Policy + IAM Policy）跟 KMS encryption key custody 怎麼配
3. Built-in rotation 跟 Custom Rotation Lambda 的設計邊界、staging label 在 zero-downtime rotation 內的角色
4. 何時 Secrets Manager 已經不夠用、要往 Vault / 跨雲 broker 走

## 最短判讀路徑

判斷一個 Secrets Manager 部署是否健康、最少看四件事：

- **誰能 GetSecretValue**：IAM Policy 那邊是不是用 `secretsmanager:GetSecretValue` 限定到 *特定 secret ARN*（不是 `*`）、Resource Policy 是不是只允許特定 principal（不是 `Principal: *`）、跨帳號 share 有沒有用 ABAC tag 限縮
- **KMS key custody**：secret 用 *AWS-managed key*（`aws/secretsmanager`）還是 *customer-managed key*（CMK）— production 應該全部 CMK、key policy 限定 only Secrets Manager service principal 可用、KMS key 持有者跟 secret 持有者要分離
- **Rotation 設定**：rotation 開了沒、rotation interval 多久、Lambda 過去執行 success rate、staging label 在 rotation 過程中是否依序 promote（AWSPENDING → AWSCURRENT → AWSPREVIOUS）
- **CloudTrail data event**：`GetSecretValue` 是 *Data event*、預設不記、要手動開 data event logging — 沒開等於事故時看不到 *誰拿了 secret*、只看得到 management API（CreateSecret / UpdateSecret）

四件事任一缺失、就是 [Secret Management](/backend/knowledge-cards/secret-management/) 跟 [Audit Log](/backend/knowledge-cards/audit-log/) 邊界的待補項目。

## 日常操作與決策形狀

**Resource Policy + IAM Policy 雙層 grant**：Secrets Manager 跟 S3 bucket policy 同模型 — IAM Policy 控制 *principal 端能做什麼*、Resource Policy 控制 *secret 端允許誰來*、兩者要 *都同意* 才放行。常見錯配：Resource Policy 寫 `Principal: "*"` 加 `aws:SourceAccount` condition 想做跨帳號 share、但 condition 漏寫或寫錯就變成公開可讀。跨帳號 share 一定要明確列 `Principal: arn:aws:iam::123456789012:role/AppRole`、不要靠 wildcard + condition 拼隔離。

**IAM Policy 細粒度授權**：`secretsmanager:GetSecretValue` 該限定到 *specific secret ARN*（不是 `*`）、配合 ABAC tag condition（`secretsmanager:ResourceTag/team = payments`）限縮 blast radius。對應 [CircleCI 2023 Secrets Rotation](/backend/07-security-data-protection/red-team/cases/supply-chain/circleci-2023-secrets-rotation/) — CI 出事時要能依 tag 快速列出 *CI runner 可拿的所有 secret*、沒這套 tag 就只能盲目 rotate 全部。

**KMS encryption key 選 CMK 不是 default**：每個 secret 用一把 KMS key 加密、預設用 AWS-managed key `aws/secretsmanager`、production 應該換 customer-managed key（CMK）。差別在 *key policy 是不是自己控* — AWS-managed key 的 policy 同 account 任何 service 可呼叫、CMK 的 key policy 可以鎖到 only Secrets Manager service principal 加 only specific role 可 Decrypt。對應 [Storm-0558](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) 的對照啟示：*key 的 blast radius 來自 key policy*、用 CMK 把 policy 寫窄是減 blast radius 的關鍵動作。

**Built-in Rotation Lambda 只限 AWS native DB**：Secrets Manager 內建 rotation template 涵蓋 RDS（PostgreSQL / MySQL / MariaDB / Oracle / SQL Server）/ Aurora / Redshift / DocumentDB — 拿 AWS 提供的 Lambda template、設定 rotation interval（最短 1 天、最長 365 天）、Secrets Manager 自動排程觸發。其他 DB（self-hosted PostgreSQL、MongoDB Atlas、Snowflake）或 API key 要寫 *Custom Rotation Lambda*、走 4-step state machine：`createSecret`（產新 credential 存為 AWSPENDING）、`setSecret`（把新 credential 寫到 target system）、`testSecret`（用新 credential 驗證可連）、`finishSecret`（promote AWSPENDING → AWSCURRENT）。Lambda 任一步失敗 Secrets Manager 會 rollback、舊 credential 不受影響。

**Staging Label（AWSCURRENT / AWSPENDING / AWSPREVIOUS）**：staging label 是 *指向 version 的 pointer*、app 一律用 `GetSecretValue` 不帶 VersionStage 拿 AWSCURRENT、rotation 過程中 Secrets Manager 先把新 credential 標 AWSPENDING、testSecret 過後 promote 到 AWSCURRENT、舊的降到 AWSPREVIOUS。設計初衷是 *zero-downtime rotation* — 但 *只有 app 端支援 AWSPREVIOUS fallback* 期間才有意義：rotation 完成瞬間有些 app instance 還拿著舊 credential，target system 應該同時接受 AWSCURRENT 跟 AWSPREVIOUS（DB rotation template 會在 setSecret 階段保留舊 user 一段時間）。對應 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)：scope map 沒做、AWSPREVIOUS 窗口期太短、長尾 batch job 拿到舊 credential 就掛。

**Cross-Region Replica**：multi-region app 把 secret replicate 到其他 region、replica 在 replica region 有獨立 ARN、KMS key 跟 rotation 都要在 replica region 各自配（不能跨 region 共用 KMS key）。replica 是 *讀副本*、寫只能在 primary region、rotation 觸發後新 version 自動 sync 到 replica（有秒級延遲）。failover 時 app 直接讀 replica region ARN、不需要 cross-region call。

**Cross-Account Sharing**：跨帳號 share secret 走 Resource Policy + 對方帳號 IAM Policy 雙向授權 — Resource Policy 列對方 account 的具體 role ARN、對方 role 的 IAM Policy 加 `GetSecretValue` 對應 ARN。KMS key 也要跨帳號授權（KMS key policy 加對方 role 的 Decrypt 權限）— 漏了 KMS 授權會出現 *GetSecretValue 成功但 Decrypt 失敗* 的詭異錯誤。

## 核心取捨表

| 取捨維度            | AWS Secrets Manager                          | SSM Parameter Store SecureString           | [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) | [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) | [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/) |
| ------------------- | -------------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 部署模型            | AWS managed                                  | AWS managed                                | 自管 cluster                                                           | GCP managed                                                                                  | Azure managed                                                                    |
| 跨雲                | 弱 — 綁 AWS                                  | 弱 — 綁 AWS                                | 強                                                                     | 弱 — 綁 GCP                                                                                  | 弱 — 綁 Azure                                                                    |
| 每月每 secret 成本  | ~$0.40 + API call                            | free / advanced ~$0.05/10k                 | self-hosted 成本                                                       | ~$0.06 + API call                                                                            | ~$0.03 + operation                                                               |
| Built-in rotation   | RDS / Redshift / DocumentDB 內建 Lambda      | 無                                         | dynamic engine 自動發短期 credential                                   | 無 built-in                                                                                  | Key Vault rotation policy（key 為主）                                            |
| Staging label       | AWSCURRENT / AWSPENDING / AWSPREVIOUS        | 無、用 version number                      | KV v2 用 version                                                       | version 機制                                                                                 | version 機制                                                                     |
| Cross-account share | Resource Policy + IAM                        | 不支援（同 account only）                  | Vault namespace + policy                                               | IAM cross-project                                                                            | RBAC cross-tenant                                                                |
| Dynamic credential  | 無（rotation Lambda 是 static 換 static）    | 無                                         | 有（DB / cloud / SSH engine）                                          | 弱（IAM impersonation）                                                                      | 弱（Managed Identity）                                                           |
| 適合場景            | AWS-only + static secret + RDS rotation 為主 | AWS-only + 大量低敏 config + 不需 rotation | 跨雲 + dynamic credential + 內部 PKI                                   | GCP-only + Workload Identity 已主導                                                          | Azure-only + Managed Identity 已主導                                             |
| 退場成本            | 低                                           | 低                                         | 中                                                                     | 低                                                                                           | 低                                                                               |

選 Secrets Manager 的核心訴求：*AWS-only* + *大部分 secret 是 static 或 AWS native DB credential* + *需要 cross-account share 或 rotation Lambda* + *不想 / 沒量能自管 Vault*。如果只是要存 config（feature flag、non-sensitive endpoint）、Parameter Store 8 倍便宜；如果跨雲 + 需要 dynamic credential / transit / PKI、Vault 才能滿足。

## 進階主題

**Custom Rotation Lambda 設計**：4-step state machine 是 *idempotent contract* — Lambda 必須能被 Secrets Manager 重試任意步驟而不破壞狀態。常見實作陷阱：createSecret 不檢查 AWSPENDING 是否已存在、重試時又產生一把新的、AWSPENDING 對不上 setSecret 寫進去的；setSecret 沒處理「target system 已經有同名 user」的情況、第二次跑會卡住。Template 提供的 PostgreSQL rotation Lambda 用 *cloning approach* — 在 DB 內 clone 一份 user、改密碼、保留舊 user 跨 rotation 一個週期、下次 rotation 才 drop。

**Resource Policy + ABAC tag 跨帳號**：跨帳號 share 時用 ABAC tag 條件比硬列 role ARN 有彈性 — Resource Policy 寫 `Condition: aws:PrincipalTag/team = payments`、對方 account 任何帶該 tag 的 role 都可讀。代價是 *tag 治理* 變成 critical control：對方 account 內誰能 attach tag = 誰能拿 secret、IAM Policy 要鎖 `iam:TagRole` 跟 `iam:UntagRole` 權限。

**Rotation 失敗的監控訊號**：Lambda 執行失敗會在 CloudWatch 留 invocation error、Secrets Manager 把 rotation 標記為 failed、但 *secret 仍可用*（AWSCURRENT 保留舊 version）— 容易出現 *半年沒 rotate 成功但 app 看起來正常* 的盲區。要監控 `SecretsManager.RotationFailed` event（EventBridge rule）+ `LastRotatedDate` metric 超過 rotation interval 1.5 倍就 alert。

**跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) 整合**：誰可以 `GetSecretValue` 完全由 IAM 控制、最佳實踐是 *workload role* 拿 secret（EC2 instance role / ECS task role / Lambda execution role / EKS IRSA）、不要硬把 AWS credential 塞進 secret 再給 application read。Secret 內容應該是 *DB password / API token / third-party credential*、不應該是 *AWS credential*（AWS credential 用 IAM role 短期 STS 拿就好）。

**CloudTrail data event 的成本權衡**：開 `GetSecretValue` data event 等於每次 secret 取用都進 CloudTrail、高 QPS application 一天可能跑數百萬筆、CloudTrail 成本（每 100k events 約 $0.10）跟 S3 儲存成本會明顯上升。降本作法：在 EventBridge 用 *filtering*（只送特定 sensitive secret 的 data event 到 SIEM）、CloudWatch Logs 端設 retention 短一點（7-30 天熱資料、長尾走 S3 + Athena）。

## 排錯與失敗快速判讀

- **GetSecretValue AccessDenied 但 IAM Policy 看起來對**：檢查 Resource Policy 是否限定 source account / VPC、檢查 KMS key policy 是否允許該 role Decrypt — 兩層 grant + KMS 三點任一缺都會 AccessDenied
- **跨帳號 secret 拿不到**：Resource Policy 沒列對方 role、或 KMS key policy 沒給對方 Decrypt 權限 — 跨帳號要同步配三處（Resource Policy + 對方 IAM + KMS key policy）
- **Rotation 一直失敗但沒人發現**：沒設 EventBridge alert on `RotationFailed`、AWSCURRENT 保持舊 version、app 正常但 secret 過期 — 必設 LastRotatedDate metric alert
- **App 拿到 stale secret rotation 後爆掉**：app 端用了 SDK cache（如 AWS SDK 的 Secrets Manager Cache）、rotation 完成後 cache 沒 invalidate — cache TTL 要短於 staging label 重疊窗口、或實作 retry-on-auth-fail 觸發 cache refresh
- **CloudTrail 看不到誰拿 secret**：沒開 data event logging — 在 CloudTrail trail 設定加上 `AWS::SecretsManager::Secret` 為 data resource
- **跨 region replica rotation 失效**：rotation Lambda 只在 primary region 配、replica region 沒對應 Lambda — 每個 region 各自配 Lambda、或乾脆只在 primary rotate 讓 replica 自動 sync
- **AWSPREVIOUS fallback 沒生效 batch job 掛**：rotation Lambda finishSecret 太快 drop 舊 user、batch job 拿到舊 credential 連 DB 失敗 — DB rotation template 預設保留舊 user 一個 rotation 週期、custom Lambda 要自己實作雙軌窗口

## 何時改走其他服務

| 需求形狀                                      | 改走                                                                                                                                                                             |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 大量低敏 config / feature flag                | [SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/)（free tier、無 rotation 需求）                                                                               |
| 跨雲統一 secret 控制面                        | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)                                                                                                 |
| Dynamic DB credential（non-AWS DB）           | [Vault database engine](/backend/07-security-data-protection/vendors/hashicorp-vault/)                                                                                           |
| Workload 拿 AWS credential                    | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) role（EC2 instance role / ECS task role / IRSA）— 不要把 AWS credential 塞 secret                               |
| Encryption-as-a-service / envelope encryption | [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) Encrypt / Decrypt API、或 [Vault transit engine](/backend/07-security-data-protection/vendors/hashicorp-vault/) |
| 內部 PKI / mTLS workload cert                 | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) + [AWS Private CA](/backend/07-security-data-protection/vendors/aws-acm/)                             |
| Secret rotation 跨服務 scope 治理             | [7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)                                                             |

## 不在本頁內的主題

- Secrets Manager 完整 API reference 跟 SDK 用法
- 每種 RDS engine 的 rotation Lambda template 內部 SQL 細節
- AWS pricing 詳細計算（每 region 略有差異）
- Terraform / CDK 跟 Secrets Manager 的 IaC 整合
- AWS account organization / SCP 怎麼限制 secret 建立

## 案例回寫

Secrets Manager 在 07 案例庫沒有直接 vendor-level 事件、以下案例採對照引用：

| 案例                                                                                                                                                                  | 跟 Secrets Manager 的關係（對照）                                                                                                                                                                             |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                                   | Secrets Manager rotation 必須有 scope map — 跨服務共用同一把 secret 時、AWSPREVIOUS 窗口期 + 雙軌驗證要對齊長尾 batch job、不能單靠 Lambda 自動 promote                                                       |
| [CircleCI 2023 Secrets Rotation (red-team)](/backend/07-security-data-protection/red-team/cases/supply-chain/circleci-2023-secrets-rotation/)                         | CI 出事時 Secrets Manager 內 *所有 CI runner role 可拿的 secret* 都要 rotate — 必須事先以 ABAC tag 標 blast radius、不然只能盲掃整個 account                                                                  |
| [Microsoft Storm-0558 Signing Key Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | 對照啟示 — Secrets Manager 的 KMS encryption key 必須走 CMK 而非 AWS-managed key、key policy 限定 only Secrets Manager service principal 且 only specific role 可 Decrypt、把 blast radius 鎖在 key policy 內 |

## 下一步路由

- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、[Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)、[Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)
- 下游：[AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/)（Secrets Manager 加密 key custodian、CMK 與 key policy 治理）
- 下游：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)（誰可以 GetSecretValue、跨帳號 share 的 principal 來源）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（secret 外洩事件如何 routing 進 IR 流程）
- 官方：[AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
