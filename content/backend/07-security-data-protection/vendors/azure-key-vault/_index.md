---
title: "Azure Key Vault"
date: 2026-05-18
description: "Azure 三合一 service（Secret + Key + Certificate）、整合 Managed Identity + Entra ID RBAC、Premium tier 走 HSM"
weight: 6
tags: ["backend", "security", "vendor", "azure-key-vault", "kms", "secret-management", "azure"]
---

Azure Key Vault 是 Azure 平台把 *secret*、*cryptographic key*、*X.509 certificate* 三類資產 *合進同一個 service* 的設計。Vault instance 本身是 first-class ARM resource、有 FQDN endpoint（`https://<vault-name>.vault.azure.net`）、跟 [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/) 跟 [Entra ID](/backend/07-security-data-protection/vendors/azure-rbac/) Managed Identity 深度整合 — 每個 Vault 自己一個邊界、區別於 region-wide service 的模型。

## 服務定位

Azure Key Vault 的核心定位是 *三合一 secret + key + cert service 加 Azure-native secret-less 取用*。AWS 是 [Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) + [KMS](/backend/07-security-data-protection/vendors/aws-kms/) + [ACM](/backend/07-security-data-protection/vendors/aws-acm/) 三個獨立 service、職責邊界清楚但要管三套權限；GCP 是 [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) + [Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) + Certificate Authority Service 三個獨立；Azure 把這三件事合在 Key Vault — 同一 RBAC role 可同時管 secret / key / cert、減少 IAM 維護成本、但治理上需要在 Vault 內用 *naming convention + 多 Vault instance* 自己劃分敏感度邊界（例：production secret / cert 分開不同 Vault、admin access 分人）。

跟 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 相比、Azure Key Vault 是 Azure-only 的 *static-focused* 服務 — 沒有 dynamic credential engine、沒有 transit encryption-as-a-service、沒有跨雲統一介面。優勢是 *零運維* + *Managed Identity 取用免 client secret* + *Premium tier 直接 [HSM](/backend/knowledge-cards/hsm/)-backed*。Azure-heavy + 一站式 secret/key/cert + secret-less workload 取用是 Key Vault 的甜蜜點。

## 本章目標

讀完本頁、讀者能判斷：

1. 哪些 secret / key / cert 適合放 Key Vault、哪些該走 [Managed HSM](https://learn.microsoft.com/azure/key-vault/managed-hsm/overview)（FIPS 140-2 Level 3 需求）
2. Access Policy 跟 Azure RBAC 兩種授權模型的差異與 migration 路徑
3. Soft Delete + Purge Protection 的 *防誤刪* 與 *防勒索* 邊界
4. 何時用 Key Vault、何時改走 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（跨雲 + dynamic credential）的取捨

## 最短判讀路徑

判斷 Azure Key Vault deployment 是否健康、最少看四件事：

- **誰能 access**：Vault 用 Access Policy 還是 Azure RBAC、是否還有 legacy Access Policy 沒清掉、Managed Identity 的 role assignment 是否最小化（Key Vault Secrets User 而非 Key Vault Administrator）
- **RBAC vs Access Policy 模型**：production 應該全走 Azure RBAC（跟 [Azure RBAC vendor](/backend/07-security-data-protection/vendors/azure-rbac/) 同套）、舊 Access Policy 是 migration backlog、不可長期兩軌並存
- **Soft Delete + Purge Protection**：兩個都應開、Soft Delete 90 天 retention、Purge Protection 開了之後連 owner 都不能立即 purge — 防誤刪 + 防 ransomware 一次性刪光
- **Diagnostic Logs**：Key Vault *預設不記操作 log*、必須手動配 Diagnostic Setting 推 Log Analytics / Event Hub / Storage — 沒這層 `KeyVaultGet` / `SecretGet` 都沒 audit trail

四件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 [Secret Management](/backend/knowledge-cards/secret-management/) 邊界的待補項目。

## 日常操作與決策形狀

**Vault Standard vs Premium**：Standard 用 software protection（key 存在 Microsoft-managed software boundary）、Premium 用 FIPS 140-2 Level 2 HSM-backed key、key material 在 HSM 內、不可 export。Premium 適合 *signing key / wrapping key 等高敏 key*、Standard 適合 *application secret + 常規 envelope encryption key*。要 FIPS 140-2 Level 3、Standard 跟 Premium 都不夠、必須用 Managed HSM。

**Access Policy vs Azure RBAC（兩種授權）**：Access Policy 是 Key Vault legacy 模型 — 在 Vault 物件上掛一張 capability 表（Get / List / Set / Delete / Encrypt / Sign 等細粒度權限）、跟 Azure RBAC 體系獨立。Azure RBAC 模型是新版 — 用 Azure built-in role（Key Vault Secrets User / Key Vault Crypto User / Key Vault Administrator）走 [Entra ID](/backend/07-security-data-protection/vendors/azure-rbac/) 統一身份治理。production 全走 RBAC、舊 Vault 的 Access Policy 是 migration backlog — 兩軌並存會出現 *RBAC 拒絕但 Access Policy 允許* 的權限漏洞。

**Managed Identity 取用（secret-less）**：Azure VM / Function / App Service / AKS pod 走 *Managed Identity* 直接呼叫 Key Vault API — 不需要存 client secret 或 cert。Workload 拿 IMDS token、token 帶 Entra ID identity、Key Vault 端用 RBAC role assignment 驗證 — 這是 Azure-native 的 secret-less 取用模式、跟 [AWS IAM Role for Service Account](/backend/07-security-data-protection/vendors/aws-iam/) / [GCP Workload Identity](/backend/07-security-data-protection/vendors/google-cloud-iam/) 同類設計。production 應該 *只允許* Managed Identity 取用、禁用 service principal + client secret。

**Secret rotation（手動 / event-driven）**：Key Vault Secret *沒有像 [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) 內建的 rotation Lambda*。Rotation 走兩條路：手動更新 secret version（app 端拉新版）、或 Event Grid 通知 secret 過期 + Azure Function 觸發 rotation。後者需要自己寫 rotation logic、Key Vault 只提供 *版本管理* 跟 *過期通知*、不負責執行 rotation。

**Key Rotation Policy**：Key（不是 Secret）有 native Rotation Policy — Vault 在 key 到期前自動生成新版、舊版保留可解密但不再 encrypt。policy 設 `rotationPeriod` + `notifyBeforeExpiry`、Key Vault 自動跑、不需要外部觸發。Secret 沒這功能、Key 才有。

**Certificate auto-renewal**：Certificate object 可整合 *Issuer*（DigiCert / GlobalSign / 自簽）做 auto-issue + auto-renew — Key Vault 在到期前自動跑 CSR、向 Issuer 申請新 cert、寫回同一個 Certificate object（保留歷史版本）。比起手動跑 OpenSSL + 寫進 [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/)、Certificate object 的優勢是 *Issuer 在 Vault 端統一治理* — 不過只支援整合過的 public CA。

**Soft Delete + Purge Protection**：Soft Delete 預設開（2020 後新 Vault 強制開）、delete 後 90 天 retention、Recover 可救回。Purge Protection 是 *額外* 開關 — 開了之後 retention 內任何人（包含 subscription owner）都不能 `purge` 立即清除、必須等 90 天到期才會物理刪除。這是 *防勒索* 的關鍵 — 沒 Purge Protection、attacker 拿到 owner role 可以 delete + purge 一次性清光。

**Private Endpoint**：Key Vault 預設是 public endpoint（FQDN 走 internet）。Private Endpoint 把 Vault 拉進 VNet、只走內網存取 — 高敏 Vault 應該關 public access、強制走 Private Endpoint + Firewall rule（IP 白名單）。

## 核心取捨表

| 取捨維度               | Azure Key Vault                                                  | AWS（拆三個）                                                                                                                                     | GCP（拆三個）                             | HashiCorp Vault                                                                              |
| ---------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------- |
| 部署模型               | Azure managed、三合一                                            | AWS managed、Secrets Manager + KMS + ACM 各獨立                                                                                                   | GCP managed、GSM + Cloud KMS + CAS 各獨立 | 自管或 HCP managed                                                                           |
| 服務邊界               | 一個 Vault 內 secret/key/cert 共用 ACL                           | 三個 service 各自 IAM policy、邊界清楚                                                                                                            | 三個 service 各自 IAM policy              | 一個 cluster 內 path-based policy                                                            |
| Secret-less 取用       | Managed Identity 原生                                            | IAM Role for Service Account / IRSA                                                                                                               | Workload Identity Federation              | AppRole / K8s / cloud IAM auth                                                               |
| Dynamic credential     | 無 — 純 static                                                   | 部分（RDS rotation Lambda）                                                                                                                       | 較弱（依靠 IAM impersonation）            | 強 — database / cloud / SSH engine                                                           |
| HSM 等級               | Standard 軟體 / Premium FIPS 140-2 Level 2 / Managed HSM Level 3 | [KMS](/backend/07-security-data-protection/vendors/aws-kms/) Level 3 / [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/) Level 3 | Cloud KMS HSM Level 3 / Cloud HSM Level 3 | 走後端 KMS（AWS / GCP / Azure）                                                              |
| Certificate auto-renew | 內建（整合 DigiCert / GlobalSign）                               | [ACM](/backend/07-security-data-protection/vendors/aws-acm/) auto-renew、限 AWS-issued                                                            | CAS + Public CA 整合                      | PKI engine 自簽 + [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) |
| 跨雲                   | 弱 — Azure-only                                                  | 弱 — AWS-only                                                                                                                                     | 弱 — GCP-only                             | 強 — 跨雲統一介面                                                                            |
| 適合場景               | Azure-heavy + 三合一一站式 + Managed Identity                    | AWS-heavy + 職責拆分 + RDS 自動 rotation                                                                                                          | GCP-heavy + Workload Identity Federation  | 跨雲 + dynamic credential + 內部 PKI                                                         |

選 Azure Key Vault 的核心訴求：*Azure-only*、需要 *secret + key + cert* 一站式、workload 走 *Managed Identity* secret-less 取用、可接受 *無 dynamic credential*。需要跨雲統一 secret 控制面、或要 dynamic database credential、走 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)。

## 進階主題

**Managed HSM（dedicated）**：Managed HSM 是 *dedicated single-tenant HSM cluster*、FIPS 140-2 Level 3、跟 multi-tenant 的 Key Vault Premium 是不同 service。Managed HSM 適合 *主權合規*（key material 完全自有控制權、Microsoft 也不可存取）、*金融 / 醫療 / 政府場景*。代價是 *貴* 跟 *初始化要走 ceremony*（多人持有 activation key、Microsoft 不可單方面操作）— 不是 Premium 的簡單升級、是另一條 product line。

**Premium tier HSM-backed Key**：Premium tier 的 key 有 `HSM-protected` 屬性、key material 在 multi-tenant HSM 內、API call 還是走標準 Key Vault endpoint、但 cryptographic operation 在 HSM 跑。比 Standard 慢一點、價格高、適合 *signing key / wrapping key / root encryption key* — 一般 application secret 還是 Standard 即可。

**Certificate Issuer 整合**：Vault 內可註冊 Issuer（DigiCert / GlobalSign / Entrust）、提供 API credential、Vault 在 Certificate 到期前自動跑 CSR、向 Issuer 申請、Issuer 簽完寫回 Vault。Self-signed / Unknown Issuer 也支援、後者表示 *Vault 產 CSR、人或 pipeline 拿去外部 CA 簽完再 import 回 Vault*。

**Cross-tenant key access（federated identity）**：Key Vault 可允許跨 Entra ID tenant 的 service principal 取用 — 透過 Federated Identity Credential（Workload Identity Federation）、外部 tenant 的 identity（甚至 GitHub Actions OIDC、AWS workload）拿 token 來 Key Vault 驗證。這是 cross-cloud workload 拉 Azure secret 的方式、不需要存 Azure service principal credential。

**跟 [Entra ID](/backend/07-security-data-protection/vendors/azure-rbac/) Conditional Access 整合**：Key Vault 用 Azure RBAC 模型時、可走 Conditional Access policy — *特定 IP*、*已 enrolled 裝置*、*MFA 已驗證* 才能取用 secret / key。production 高敏 Vault 應該疊 Conditional Access、避免單純 RBAC 在 token leak 時就直接被存取。

## 排錯與失敗快速判讀

- **Diagnostic Setting 沒開**：production Vault 啟用後忘了配 Diagnostic Setting 推 log、事故發生時無 `SecretGet` / `KeyDecrypt` 紀錄 — 啟動 checklist 必含「Diagnostic Setting → Log Analytics」、Azure Policy 強制全 subscription Vault 都配
- **Access Policy 跟 RBAC 兩軌並存**：migration 過程中 RBAC 已切換但舊 Access Policy 沒清、出現 *RBAC 拒絕但 Access Policy 允許* — migration 一次切斷、跑 `az keyvault update --enable-rbac-authorization true` 後清空所有 Access Policy
- **Soft Delete 沒開 / Purge Protection 沒開**：誤刪 secret 救不回、或 attacker 拿到 owner role 一次 purge 清光 — 新 Vault 兩個都強制開、Azure Policy 阻擋 `enablePurgeProtection: false` 的 Vault 建立
- **Managed Identity role 過寬**：給 workload identity `Key Vault Administrator` 而非 `Key Vault Secrets User` — workload 拿到 admin role 等於可改 ACL — role assignment 走 least privilege built-in role
- **Premium key 跑非 HSM operation**：Premium key 配錯 attribute、key 變成 software-protected 而非 HSM-protected — 建 key 時明示 `--protection hsm`、CI 驗證 key attribute
- **Certificate auto-renew Issuer credential 過期**：Vault 內 DigiCert API credential 過期、auto-renew 默默失敗、cert 到期前才發現 — Issuer credential 也要 rotation + monitor
- **Public access 開著**：Vault 沒關 public endpoint、secret 暴露在 internet（雖然有 RBAC、但 attack surface 多一層）— 高敏 Vault 強制 Private Endpoint + Firewall rule

## 何時改走其他服務

| 需求形狀                                  | 改走                                                                                                                                                 |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 跨雲統一 secret 控制面                    | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)                                                                     |
| Dynamic database / cloud credential       | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（database / cloud secret engine）                                   |
| FIPS 140-2 Level 3 HSM                    | [Managed HSM](https://learn.microsoft.com/azure/key-vault/managed-hsm/overview) / [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/) |
| 內部 PKI workload mTLS                    | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) + Vault PKI / SPIRE                                                       |
| 公開 web cert 自動更新（非 Azure-issued） | [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) + cert-manager                                                            |
| Entra ID 身份治理 / Conditional Access    | [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)                                                                               |
| Secret rotation 證據鏈                    | [7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)                                 |

## 不在本頁內的主題

- Key Vault REST API / Azure CLI 完整 reference
- Managed HSM activation ceremony 完整步驟
- Bicep / Terraform 配置 Key Vault 的完整 IaC 範例
- Certificate Issuer（DigiCert / GlobalSign）的合約與計價細節
- 每個 Entra ID role 的細粒度 permission map

## 案例回寫

| 案例                                                                                                                                                                  | 跟 Azure Key Vault 的關係                                                                                                                                              |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Azure AD Identity Control Plane 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)                                              | Key Vault 是身份控制面下游、Entra ID 出事時 Managed Identity 取 Vault 也失敗 — 需要 fallback access plan（emergency Access Policy + separate identity 走 break-glass） |
| [Microsoft Storm-0558 Signing Key 2023](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/)                                            | Key Vault Premium / Managed HSM 把 signing key 鎖硬體、key 不離保護邊界、跟 HSM-bound 同 mindset — signing key 必上 Premium 或 Managed HSM、不放 Standard              |
| [Microsoft Storm-0558 Signing Key Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | Asymmetric Key + Diagnostic Logs 是「誰用 key」的稽核基礎 — production Vault 必開 Diagnostic Setting 推 SIEM、不然 key 被誰用過完全沒紀錄                              |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                                   | Key Vault Secret 跨 service 共用時 rotation 要分域 — Vault 端用 Event Grid 通知 + app 端訂閱 rotation event、不能一次 push 全域更新                                    |

## 下一步路由

- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)（Key Vault Certificate + Managed HSM 為 TLS / signing key 的 root custodian）、[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- 平行（secret store）：[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)、[Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)
- 平行（KMS-class）：[AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/)、[Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)、[CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)（Key Vault 是跨類 vendor、同時是 secret store 跟 key management）
- 下游：[Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)（Managed Identity + RBAC 取用模型）
- 下游：[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)（K8s workload cert 自動化、可整合 Key Vault Certificate）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Key Vault 事件如何 routing 進 IR 流程）
- 官方：[Azure Key Vault Documentation](https://learn.microsoft.com/azure/key-vault/)
