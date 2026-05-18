---
title: "AWS KMS"
date: 2026-05-18
description: "AWS 原生 key management service、envelope encryption / digital signing / Multi-Region Key、Key Policy + Grant 雙軌授權"
weight: 4
tags: ["backend", "security", "vendor", "aws-kms", "kms", "encryption", "aws"]
---

AWS KMS 是 AWS 原生的 key management service、解決 *對稱 / 非對稱金鑰生命週期管理* 與 *envelope encryption pattern*：service 內部保管 master key（KMS Key）、應用層用 `GenerateDataKey` 取得短暫的 data key 對實際資料加密、master key 完全不離 KMS 服務邊界。整合面跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) / S3 / EBS / RDS 都串好、是 AWS 上幾乎所有靜態資料加密的後端。

## 服務定位

AWS KMS 的核心定位是 *AWS-only 的 multi-tenant managed key management*，FIPS 140-2 Level 3 認證、跨服務 envelope encryption 的共同地基。跟 [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/) 比、KMS 是 *managed + shared HSM 池*、CloudHSM 是 *single-tenant dedicated HSM*；需要更高隔離 / 自管 cluster / FIPS Level 3 single-tenant 時走 CloudHSM、或用 KMS Custom Key Store 把 KMS 後端指向自己的 CloudHSM。跟 [Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) / [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/) 比、設計概念相近、但 KMS 把 secret store 切出去（[Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)）、Key Vault 則把兩者合一。

跟 [Vault transit engine](/backend/07-security-data-protection/vendors/hashicorp-vault/) 比、行為相似（key 不離 service、app 拿 ciphertext）、但治理面完全不同：KMS 綁 AWS 控制面、IAM + Key Policy 雙層授權、CloudTrail 是稽核入口；Vault transit 是跨雲統一介面、token + policy 為主、需要自管 cluster。AWS-heavy 組織首選 KMS、跨雲組織才會把 KMS 當下游、上游用 Vault transit 抽象。

## 本章目標

讀完本頁、讀者能判斷：

1. 哪些資料 / 場景該用 Customer Managed KMS Key、哪些 AWS Managed Key 已經夠用、什麼時候直接走 CloudHSM
2. Key Policy + IAM + Grant 三層授權的分工、production 必開的 CloudTrail Data event 與 monitor 範圍
3. Multi-Region Key、Custom Key Store、External Key Store、BYOK 等進階形態的取捨
4. KMS 出事（IAM 過寬、Key Policy 把自己鎖死、Schedule Deletion 誤觸發）時的判讀路徑跟回退選項

## 最短判讀路徑

判斷一個 AWS KMS deployment 是否健康、最少看四件事：

- **Key Policy 設計**：是否含 `root` principal（不然 key 變孤兒）、是否走 least privilege（不是 `kms:*` 給整個 account）、admin / user / monitor 三類 principal 是否分開、policy 變更是否走 PR review
- **Grant 治理**：哪些 service-to-service 短期授權走 Grant（rotation Lambda / RDS / EBS）、Grant TTL 是否設、廢棄 grant 是否定期 `RetireGrant`
- **Multi-Region 與 rotation 策略**：是否啟用 annual automatic rotation（適用 symmetric encryption key）、Multi-Region Key 的 replica 是否跟 DR plan 對齊、asymmetric / signing key 的 manual rotation 流程是否有 runbook
- **CloudTrail Data Event 必開**：management event 預設記、但 `Encrypt` / `Decrypt` / `GenerateDataKey` 是 data event、預設不記 — 沒這層 forensic 沒著力點、Storm-0558 對照下完全無法回答「誰用哪把 key 簽了什麼 token」

四件事任一缺失、就回到 [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) 跟 [Audit Log](/backend/knowledge-cards/audit-log/) 的補丁清單。

## 日常操作與決策形狀

**Key Type 選擇**：symmetric encryption key（AES-256-GCM、最常用、S3 / EBS / RDS / Secrets Manager 都走這個）；asymmetric key pair（RSA / ECC、用於 sign / verify 或 encrypt / decrypt、JWT 簽署、CodeSign、文件簽章）；HMAC key（generate / verify MAC、API request signing）。對應 [Storm-0558 signing key chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) — 自己 host signing key 出事的核心教訓是 *key 不該離 HSM service*、所以 JWT signing 用 asymmetric KMS key 是 baseline 設計、private key 永遠不離 KMS。

**Key Origin（key material 來源）**：`AWS_KMS`（KMS 內部生成、預設）；`EXTERNAL`（BYOK、組織自己生成 key material、import 進 KMS、可以隨時 reimport 或刪除）；`AWS_CLOUDHSM`（Custom Key Store、key material 存在自己的 CloudHSM cluster）；`EXTERNAL_KEY_STORE`（XKS、AWS 外的 HSM、控制面在 AWS、key material 在 on-prem）。多數場景用 `AWS_KMS` 就夠、合規 / 主權需求才走 EXTERNAL / Custom Key Store。

**Key Policy 跟 IAM 的雙層**：KMS 跟其他 AWS service 最大差異是 *Key Policy 是主要授權機制*、IAM policy 單獨不夠。Key Policy 必含 `arn:aws:iam::ACCOUNT_ID:root` 給 root principal（不是 root user、是讓 IAM 能參與授權的開關）— 沒這條 key 變孤兒、即使 IAM 開了 admin 也救不回來。production 通常分三類 statement：admin（Create / Delete / Schedule、走 break-glass）、user（Encrypt / Decrypt / GenerateDataKey、給 app）、monitor（Describe / List、給 SRE）。

**Grant 是程式化短期授權**：service-to-service 整合（[Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) rotation Lambda、RDS 自動加密、EBS volume attach）通常走 Grant 而不是改 Key Policy — 每個 grant 有自己的 grant token、可以帶 TTL、可以 `RetireGrant` / `RevokeGrant` 收回、不跟 key policy 永久綁定。沒治理時 grant 累積上千個 / 沒人 retire 是常見問題、跟 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) 同類 — 沒 scope map 等於沒治理。

**Alias 與 Key ID 的解耦**：alias（`alias/my-app-prod-key`）是 *指向 key 的可變指標*、key ID / ARN 是 *不可變識別*。production code 應該用 alias、要換 key 時只需要重綁 alias、不用改 deployment。Cross-account 跨帳號使用必須用 ARN（alias 不跨帳號）。

**Key Rotation 的真實語義**：annual automatic rotation（symmetric encryption key 才支援）換的是 *KMS 內部的 backing key material*、key ARN / Alias / Key ID 都不變、app 完全不需要動。**舊資料仍用舊 backing key 解密、KMS 自動處理**、不是「資料全部重新加密」— 這是常見誤解。asymmetric / HMAC key 不支援 automatic rotation、必須 manual 建新 key + alias 切換 + app 端雙讀容忍窗口（跟 JWT signing key rotation 同套路）。

**Multi-Region Key**：跨 region replicate 的 KMS key 共用 *key material* 跟 *Key ID*（後綴帶 `mrk-`）、不是建立新 key — 跨 region 加密的 ciphertext 在另一 region 可以直接 decrypt、不用 cross-region API call。適合 multi-region active-active app + DR scenario。代價是 *replica region 跟 primary region 的權限要分別治理*、Key Policy 不會自動同步。

**Encryption Context 是 *authenticated data***：encrypt 時帶的 key-value pair（例：`{"app": "billing", "tenant": "acme"}`）、decrypt 必須提供同一組 context — 否則失敗。用來防 *ciphertext 被 replay 到別的 context*（攻擊者拿到 billing 的 ciphertext 想當 payroll 的 ciphertext 用）、所有 context 都會進 CloudTrail、是 forensic 上的關鍵欄位。production 一律帶 context、單純加密不帶 context 等於少一層防護。

**Customer Managed vs AWS Managed vs AWS Owned**：三層分權 — Customer Managed（CMK、自己控 Key Policy + 自選 rotation）、AWS Managed（`aws/secretsmanager`、`aws/s3`、AWS 管 Key Policy、看得到但改不了）、AWS Owned（完全看不見、AWS 自己用、無 CloudTrail）。production 高敏感資料應該用 Customer Managed、才能控 policy + 開 data event + 自選 rotation 週期。

## 核心取捨表

| 取捨維度            | AWS KMS                                          | Google Cloud KMS                        | Azure Key Vault                        | AWS CloudHSM                            | Vault transit engine            |
| ------------------- | ------------------------------------------------ | --------------------------------------- | -------------------------------------- | --------------------------------------- | ------------------------------- |
| 部署模型            | AWS managed multi-tenant、FIPS 140-2 Level 3     | GCP managed multi-tenant、FIPS 140-2 L3 | Azure managed、Standard / Premium tier | AWS managed single-tenant HSM cluster   | 自管 Vault cluster              |
| 跨雲                | 弱 — AWS-only                                    | 弱 — GCP-only                           | 弱 — Azure-only                        | 弱 — AWS-only                           | 強 — 跨雲統一介面               |
| 授權模型            | Key Policy（強制） + IAM + Grant 三層            | IAM 為主、Resource policy 輔            | Access policy + RBAC 雙模式            | CloudHSM user / role + Cluster IAM      | path-based policy + token       |
| Multi-Region        | Multi-Region Key（共用 key material）            | 自動跨 region replication 較易          | Geo-replication 透過 Premium tier      | 自管 cross-region replication           | Replication（Enterprise）       |
| Envelope encryption | 一級 pattern（`GenerateDataKey`）                | 一級 pattern                            | 一級 pattern                           | 自己實作                                | 內建（transit engine）          |
| Asymmetric signing  | 支援（RSA / ECC、JWT / CodeSign 直用）           | 支援                                    | 支援                                   | 支援 + 完整 PKCS#11                     | 支援（部分）                    |
| 整合面              | 全 AWS service 原生（S3 / EBS / RDS / Lambda）   | 全 GCP service 原生                     | 全 Azure service 原生                  | PKCS#11 / JCE / OpenSSL                 | 應用層 SDK                      |
| 適合場景            | AWS-heavy + envelope encryption + JWT signing    | GCP-heavy                               | Azure-heavy + 跟 AD 整合               | 合規 / FIPS L3 single-tenant / 自管 HSM | 跨雲 + key 不離 service         |
| 不適合場景          | 跨雲統一 custody、需 FIPS L4、需自管 HSM cluster | 同左                                    | 同左                                   | 純 envelope encryption 用 KMS 即可      | AWS-only 簡單需求（KMS 更便宜） |

KMS 是 AWS 上的 *預設選擇*、CloudHSM 是合規 / 自管要求才上的 *昇級*、Vault transit 是跨雲統一介面、Google / Azure 對標品在各自雲一樣是預設選擇。

## 進階主題

**KMS Custom Key Store + CloudHSM 整合**：Custom Key Store 把 KMS 的 *控制面*（API、Key Policy、CloudTrail、IAM 整合）保留、但 *key material 存在自己的 CloudHSM cluster*。組織需要 FIPS 140-2 Level 3 single-tenant 但又不想放棄 KMS 的 service 整合（S3 SSE-KMS / EBS encryption）時用。代價是 CloudHSM cluster 的運維成本（cluster HA、user 管理、backup）。

**External Key Store (XKS)**：更激進的形態 — key material 完全在 AWS 之外（on-prem HSM 或第三方 HSM）、AWS 透過 XKS proxy 呼叫外部 HSM 做 cryptographic operation。用於 *資料主權* 場景（金融 / 政府 / 跨境合規要求 key 不出組織邊界）、代價是 latency 跟 availability 完全綁外部 HSM、AWS service 整合面要算清楚。

**Multi-Region Replica Key 跟 DR**：primary region 出事時 replica region 仍能 decrypt 既有 ciphertext、不需要 cross-region API call。但 *primary 跟 replica 是各自獨立的 Key Policy*、變更不會自動同步 — 跟 [Audit Log](/backend/knowledge-cards/audit-log/) 治理一樣、replica region 也要納入 CloudTrail Data Event 覆蓋範圍。

**BYOK（Bring Your Own Key）**：`Origin = EXTERNAL` 的 KMS Key、key material 由組織自己生成、用 wrapping key 加密後 import 進 KMS。優點是組織保有 *master copy*（KMS 出事時仍能 re-import 到別處）、缺點是 *automatic rotation 不支援*（必須手動 import 新 key material）、且必須自己處理 wrapping key 的生命週期。

**跟 [Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) 的整合**：Secrets Manager 的 secret 本身用 KMS key 加密（預設 AWS Managed `aws/secretsmanager`、production 應該指到 Customer Managed CMK）。rotation Lambda 透過 Grant 取得 Decrypt + Encrypt 能力、跟 Secrets Manager 一起構成 *static secret rotation 的證據鏈* — 跟 [credential rotation scoped evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/) 對齊。

**Asymmetric signing 的 use cases**：JWT signing（KMS `Sign` API 直接簽 JWT header.payload、private key 不離 KMS、跟 Storm-0558 的設計對照鮮明）；CodeSign / S3 object signing（artifact integrity）；mTLS client cert 的 private key（搭配 [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) AWS issuer）。代價是 *latency*（每次 sign 一次 KMS API call、~10ms 級別、不適合超高 QPS）跟 *cost*（asymmetric operation 比 symmetric 貴 ~5x）。

## 排錯與失敗快速判讀

- **Key Policy 沒有 `root` principal**：Schedule 時忘了寫、key 立刻變孤兒、誰都不能用 — 只能透過 AWS Support 救（流程慢）；建立流程強制 template 含 root principal
- **IAM admin 改不動 KMS key**：Key Policy 沒授權 IAM 介入、即使 admin policy 有 `kms:*` 也擋掉 — 加 `Enable IAM User Permissions` statement 給 root principal、IAM 才能參與授權
- **Schedule Key Deletion 誤觸發**：min 7 天、max 30 天的等待期、期內可 cancel — production key 必含 alert（CloudWatch Alarm on `ScheduleKeyDeletion` event）+ 強制 4-eyes approval
- **CloudTrail Data Event 沒開**：事故後想查「誰 decrypt 了什麼」、發現只有 management event — production 必開 KMS data event、預估 cost（每 100k events ~$0.10）、敏感 key 一律開
- **Encryption Context 不一致**：encrypt 時帶 context、decrypt 時忘了帶（或帶錯）、`InvalidCiphertextException` — code review 強制 context schema、用 typed wrapper 避免人手帶錯
- **Grant 累積 + 沒 retire**：每個 KMS key 有 50,000 grant 上限、rotation Lambda 跑久了 grant 累積 — 定期 `ListGrants` + `RetireGrant` 廢棄的、IaC 治理 grant lifecycle
- **Cross-region decrypt 失敗**：以為 ciphertext 跨 region 通用、結果原本不是 Multi-Region Key — production 跨 region 場景一律建 Multi-Region Key、不要事後補
- **CMK rotation 後舊 ciphertext 還能 decrypt**：annual rotation 不會 re-encrypt 舊資料、KMS 自動用對應 backing key — 這是設計、不是 bug；真要全量 re-encrypt 要走 application-level migration

## 何時改走其他服務

| 需求形狀                                    | 改走                                                                                                                                          |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| FIPS 140-2 Level 3 single-tenant HSM        | [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)、或 KMS Custom Key Store 橋接                                              |
| GCP-heavy 環境                              | [Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)                                                            |
| Azure-heavy + 跟 AD / Managed Identity 整合 | [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)                                                              |
| 跨雲統一 key custody                        | [HashiCorp Vault transit engine](/backend/07-security-data-protection/vendors/hashicorp-vault/)                                               |
| Static secret + rotation orchestration      | [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)（後端是 KMS）                                        |
| K8s workload mTLS cert                      | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)（可用 KMS asymmetric key）                                         |
| Public TLS cert                             | [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/) / [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) |
| 數據主權 / on-prem HSM required             | KMS External Key Store (XKS) 或直接 [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)                                        |

## 不在本頁內的主題

- KMS 完整 API reference 跟 SDK 範例
- 各 AWS service（S3 SSE-KMS、EBS encryption、RDS encryption、DynamoDB encryption）的詳盡設定步驟
- 跟 AWS Organizations / SCPs 的 cross-account KMS sharing 完整治理流程
- CloudHSM cluster 的完整運維（高可用、user 管理、backup）— 看 [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)
- 各種 cryptographic algorithm 的數學原理跟選型細節

## 案例回寫

KMS 在 07 案例庫沒有直接 vendor-level 事件、以下案例採對照引用：

| 案例                                                                                                                                                                  | 跟 KMS 的關係（對照）                                                                                                                                |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Microsoft Storm-0558 Signing Key 2023](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/)                                            | KMS 設計核心對照 — signing key 必須 HSM-bound + 不可導出、KMS 預設 key 完全不離 service；自己 host private key 是 Storm-0558 級事件的根因            |
| [Microsoft Storm-0558 Signing Key Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | 三件事必到位：asymmetric KMS Key 做 JWT signing（private key 永遠不離 KMS）、強制 rotation 流程、CloudTrail Data Event 紀錄「誰用 key 簽什麼 token」 |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                                   | KMS Alias / Grant 的 rotation 跟 revocation 要分域 — 一次 Schedule Key Deletion 沒 scope map 等於潛在全停、Grant lifecycle 要納入治理                |

## 下一步路由

- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)、[Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)、[CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)
- 下游：[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)（後端用 KMS）、[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)（可用 KMS asymmetric key 當 issuer）
- 對照：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（transit engine / 跨雲統一介面）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（KMS 事件如何 routing 進 IR 流程）
- 官方：[AWS KMS Documentation](https://docs.aws.amazon.com/kms/)
