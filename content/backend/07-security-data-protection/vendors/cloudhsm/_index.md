---
title: "AWS CloudHSM"
date: 2026-05-18
description: "Single-tenant dedicated HSM（FIPS 140-2 Level 3）、AWS 不持 Crypto User credential、合規 + 資料主權場景的 key custody"
weight: 7
tags: ["backend", "security", "vendor", "cloudhsm", "hsm", "encryption", "aws", "compliance"]
---

AWS CloudHSM 是 *single-tenant dedicated [HSM](/backend/knowledge-cards/hsm/)* 服務（FIPS 140-2 Level 3）、客戶獨享一個 HSM cluster、AWS 提供 *硬體 + network + provisioning*、客戶自己管 *crypto user / partition / key custody / backup*。它跟 [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) 是 *不同信任模型* — KMS 是 multi-tenant managed、AWS 持有 key custody 與 API plane；CloudHSM 上 *AWS 看不到 key、也不能 reset Crypto User password*、客戶丟了 credential 等於 key 永久遺失。

## 服務定位

CloudHSM 的核心定位是 *把 cryptographic root of trust 放回客戶手上* — 適合金融、政府、醫療這類有資料主權、FIPS 140-2 Level 3、PCI HSM、HIPAA 合規壓力的場景。跟 [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) 比、KMS 也滿足 FIPS 140-2 Level 3、但 *HSM cluster 是 AWS 多租戶共用*、key material 由 AWS-controlled HSM 持有、控制面 API 也是 AWS。CloudHSM 把 HSM cluster 物理隔離給單一客戶、PKCS#11 / JCE / OpenSSL Dynamic Engine 直接打 HSM、AWS 在資料平面 *沒有讀 key 的能力*。

跟 *自管 on-prem HSM*（SafeNet / Thales 自架）比、CloudHSM 把硬體採購、機房、network、firmware patch 交還 AWS、客戶只管 key custody 跟 Crypto User policy；代價是不能完全脫離 AWS region。跟 [Vault auto-unseal](/backend/07-security-data-protection/vendors/hashicorp-vault/) 整合場景中、CloudHSM 是 *Vault master key 的 root custodian* — Vault unseal key 用 CloudHSM 加密、CloudHSM 出事整個 Vault cluster 沒法 unseal、所以可用性設計（cross-AZ cluster、cross-region backup）很關鍵。多數一般 web app / SaaS 用 KMS 即可、不需要 CloudHSM 的物理隔離。

## 本章目標

讀完本頁、讀者能判斷：

1. 何時需要 CloudHSM 的 dedicated 模型、何時 [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) 已足夠
2. CloudHSM cluster 的最低安全 / 可用性需求（cross-AZ、Crypto Officer 分離、Quorum、backup）
3. Crypto User credential 出事的降級路徑（AWS 不能幫忙、靠 backup + Quorum）
4. 跟 [KMS Custom Key Store](https://docs.aws.amazon.com/kms/latest/developerguide/custom-key-store-overview.html) / [Vault auto-unseal](/backend/07-security-data-protection/vendors/hashicorp-vault/) 整合的取捨

## 最短判讀路徑

判斷 CloudHSM deployment 是否健康、最少看四件事：

- **Cluster 拓樸**：production cluster 是否至少 2 個 HSM instance 跨 AZ、cluster 內自動 replicate、單一 AZ 故障時 key 是否仍可用
- **Crypto User 管理**：Crypto Officer（CO）跟 Crypto User（CU）是否分離、CO password 是否走 break-glass 保管、CU credential 是否走 short-lived 取得 + audit
- **Quorum-based policy**：高敏 operation（建 CU、改 policy、key export wrapped）是否設 M-of-N approval、避免單一 admin compromise 後 silent abuse
- **Backup 治理**：automatic 24h backup 跟 manual backup 是否都開、cross-region backup 是否走 explicit copy、restore 流程是否定期演練

四件事任一缺失、就是 CloudHSM deployment 待補項目 — 跟 [secret management](/backend/knowledge-cards/secret-management/) 的 evidence 邊界同類。

## 日常操作與決策形狀

**Cluster + HSM Instance 拓樸**：CloudHSM 的部署單位是 *cluster*、cluster 內可以有 1-N 個 *HSM instance*。production 場景至少 2 個 HSM instance 跨 AZ、cluster 自動把 key material replicate 在所有 instance 上、單一 AZ 失效不影響 cryptographic operation。跨 region 不自動 replicate — 跨 region DR 要靠 backup copy。

**Crypto Officer (CO) vs Crypto User (CU)**：CO 是 cluster 管理員、能建 / 刪 CU、設 policy、做 backup；CU 是真的做 cryptographic operation 的 identity（encrypt / decrypt / sign / verify）。production 必須分離 — CO credential 走 break-glass 保管、CU credential 給 application 使用、application compromise 只影響 CU 邊界、不能改 CO policy。

**Quorum-based policy（M-of-N approval）**：CloudHSM 支援把高敏操作（建 CU、改 policy、key export wrapped）綁定 *M-of-N CO approval*。例如 3-of-5 quorum、單一 CO 即使 credential 外洩也不能單獨建後門 CU、必須拿到另外 2 個 CO 的 signed token。對應 [Storm-0558 signing key chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) 啟示：高價值 key custodian 的 admin operation 不該是 *單人單 token*、必須有第二人簽核才能改變信任根。

**Backup 治理**：CloudHSM 每 24 小時自動 backup 整個 cluster state（含 key material）、backup 是 AWS-managed encrypted blob、AWS 自己也不能解密、restore 必須在 CloudHSM cluster context 內進行。可手動 backup、可 copy 到其他 region 做 DR。Backup retention 預設 90 天、可延長。Backup 不是 *export* — 不能把 key material 從 HSM 拿出來看 plaintext。

**Key Replication 跨 region**：CloudHSM cluster 綁定單一 AWS region、跨 region 走 *backup → copy → restore* 流程、不是 active replication。設計 DR 時要算 RTO：restore 一個 cluster 從 backup 大約小時級、不適合 hot failover、應該 *primary region 跑、DR region 備好空 cluster + backup copy*。

**PKCS#11 / JCE / OpenSSL Dynamic Engine 整合**：application 不用 AWS SDK 講 CloudHSM、而是透過 *標準 cryptographic API library*（PKCS#11 for C/C++、JCE Provider for Java、OpenSSL Dynamic Engine 走 TLS termination）。好處是 *application code 用業界標準介面*、未來換 HSM 廠也只需要換 library。代價是 client SDK 要裝在 application host、CU credential 要 deploy 到 host、host security baseline 變成 cryptographic boundary 的一部分。

**跟 KMS Custom Key Store 整合**：[KMS Custom Key Store](https://docs.aws.amazon.com/kms/latest/developerguide/custom-key-store-overview.html) 把 KMS Key 的 *backing material 放在 CloudHSM*、API 仍透過 KMS（`kms:Encrypt` / `kms:Decrypt`）、application code 不需要改。這是 *KMS 易用 + HSM dedicated 雙重*：保留 KMS 的 IAM policy / key rotation / audit log（CloudTrail）、又得到 single-tenant HSM 的合規屬性。代價是 CloudHSM 失效時、Custom Key Store backing 的 KMS Key 全部不可用、需要監控 cluster health。

## 核心取捨表

| 取捨維度           | AWS CloudHSM                                    | AWS KMS                                | Azure Managed HSM                     | Google Cloud HSM                             |
| ------------------ | ----------------------------------------------- | -------------------------------------- | ------------------------------------- | -------------------------------------------- |
| 部署模型           | Single-tenant dedicated cluster                 | Multi-tenant managed                   | Single-tenant pool                    | HSM-backed Cloud KMS（Protection Level=HSM） |
| FIPS 140-2         | Level 3（dedicated）                            | Level 3（shared cluster）              | Level 3                               | Level 3                                      |
| AWS / 雲廠持 key？ | 不持（CU credential 客戶獨有）                  | 持（managed key custody）              | 不持（HSM admin 客戶獨有）            | 不持 plaintext key material                  |
| 整合介面           | PKCS#11 / JCE / OpenSSL                         | AWS SDK / CLI / KMS API                | Key Vault SDK / REST                  | Cloud KMS API                                |
| Quorum 多人簽核    | 內建（M-of-N）                                  | 透過 IAM policy + organization SCP     | RBAC + Privileged Identity Management | IAM Condition + organization policy          |
| 運維成本           | 高 — 自管 CU credential / patch / topology      | 低                                     | 中                                    | 低                                           |
| 合規憑證           | FIPS 140-2 L3 + PCI HSM + Common Criteria       | FIPS 140-2 L3 + PCI DSS                | FIPS 140-2 L3 + Common Criteria       | FIPS 140-2 L3                                |
| 適合場景           | 金融 / 政府 / 醫療、需要物理隔離 + AWS 不持 key | 一般 AWS-heavy workload、需要 IAM 整合 | Azure-heavy + 合規壓力                | GCP-heavy + 合規壓力                         |
| 退場成本           | 中 — backup 跨廠不可移植、key 不能 export       | 中                                     | 中                                    | 中                                           |

選 CloudHSM 的核心訴求：*合規明文要求 dedicated HSM*（PCI HSM、某些國家資料主權法規）、或 *trust model 上不接受 AWS 持 key*。多數 AWS-heavy workload 用 KMS 即可、加 CloudHSM 反而引入 *Crypto User credential 的單點失誤*（丟了 = key 永久遺失）。需要 KMS API 但又要 dedicated HSM、走 [Custom Key Store](https://docs.aws.amazon.com/kms/latest/developerguide/custom-key-store-overview.html) 是折衷路徑。

## 進階主題

**Quorum Auth 設計**：production 把 Quorum threshold 設為 *3-of-5* 或 *2-of-3*、五位 CO 由不同部門 / 不同地理位置持有、避免單一辦公室 / 單一網路同時被攻陷。Quorum token 有 TTL、單次 operation 用完就失效、防止 replay。建議 quarterly 演練：模擬一個 CO 不在、用剩餘 quorum 完成 emergency operation、驗證流程在事故時跑得通。

**KMS Custom Key Store 整合決策**：用 Custom Key Store 的關鍵問題是 *availability blast radius* — KMS Key 出事影響範圍是 *使用該 Key 的 AWS service*（S3、EBS、RDS encryption）、Custom Key Store backing 失效會讓這些 service 同步斷。設計時做 *分層 key strategy*：mass volume 的 S3 / EBS 用 AWS-managed KMS Key、高合規敏感的 database / secret 才用 Custom Key Store backing 的 KMS Key、降低單一 cluster 失效的影響面。

**Cross-Region Backup**：DR 要把 backup copy 到第二個 region、走 `CopyBackupToRegion` API、restore 時建空 cluster + 套 backup。整個 RTO 通常數小時、不適合熱備、設計上是 *容忍小時級 outage 換到 BCDR 環境*、不是 *秒級 failover*。對應 [Azure AD Identity Control Plane 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/) 對照啟示：身份 / 加密控制面的單點 outage 影響整個 platform、availability 的 topology 設計跟 confidentiality 同等重要。

**跟 Vault auto-unseal 整合**：[Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) auto-unseal 可用 CloudHSM 作 master key custodian、走 PKCS#11 plugin、Vault unseal 時呼叫 CloudHSM `Unwrap` master key。比起 [AWS KMS auto-unseal](/backend/07-security-data-protection/vendors/aws-kms/) 多一層 dedicated HSM 保證、適合監管特別嚴的場景。代價是 CloudHSM cluster 失效 → Vault 不能 unseal → 下游所有 secret 拿不到、要設計 break-glass 流程。

**合規憑證**：CloudHSM 同時持有 FIPS 140-2 Level 3、PCI HSM、Common Criteria EAL4+ 多個認證、可作金融 PIN block 處理、payment 業者的 HSM 上鏈、政府機敏資料加密的 *直接合規承諾*、不需要客戶端再做 HSM 認證 audit。

## 排錯與失敗快速判讀

- **Crypto User credential 丟失**：CU password 全公司只有一份、保管人離職 → AWS *不能 reset*、key material 永久不可用 — CU credential 要走 password manager + 多人持有、CO 有能力 revoke 舊 CU 建新 CU
- **Cluster 只有單一 HSM instance**：成本省了、單一 instance 故障 cluster 整個失效 — production 強制至少 2 個 instance、跨 AZ
- **Backup 沒測過 restore**：每天 automatic backup 跑、從未 restore 演練、DR 真要用時發現流程不通 — quarterly 演練 restore 到測試 cluster、驗證 key material 可用
- **Custom Key Store 沒監控 CloudHSM health**：CloudHSM cluster degraded 時、KMS Custom Key Store 跟著失效、application 看到 KMS 5xx — CloudWatch metric 監 `HsmsActive` / `HsmTemperature`、cluster health degrade 立即 alert
- **PKCS#11 library 版本漂移**：application host 的 client SDK 版本跟 cluster firmware 不相容、cryptographic operation 失敗 — version compatibility matrix 進 deployment pipeline、firmware upgrade 前先測 staging
- **Quorum CO 全部同地點**：5 個 CO 全在同一個辦公室、辦公室斷網 = quorum 不能組 — CO 跨 region / 跨組織分散
- **Audit log 沒接 SIEM**：CloudHSM activity 透過 CloudTrail + cluster audit log、沒接 SIEM 就無 forensic — CloudTrail 跟 cluster audit 都 push 到 SIEM（見 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)）

## 何時改走其他服務

| 需求形狀                                  | 改走                                                                                                                                                                        |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 一般 AWS workload 加密、無 dedicated 合規 | [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/)                                                                                                            |
| Azure-heavy + dedicated HSM 合規需求      | Azure Managed HSM（見上方對照表）                                                                                                                                           |
| GCP-heavy + dedicated HSM 合規需求        | Google Cloud HSM（Cloud KMS Protection Level=HSM）                                                                                                                          |
| Secret storage + dynamic credential       | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) / [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) |
| Certificate / PKI（不是 key custody）     | [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/) / [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)                               |
| 跨雲 unified key custody                  | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) transit engine（雲廠中立）                                                                 |
| Key rotation 證據鏈                       | [7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)                                                        |

## 不在本頁內的主題

- CloudHSM 完整 PKCS#11 / JCE API reference
- CloudHSM Classic（舊版、已 EOL）的差異
- 每種合規法規（PCI HSM、HIPAA、FedRAMP）的逐條對應
- CloudHSM CLI 跟 `cloudhsm_mgmt_util` 詳細指令
- 應用層使用 HSM-bound key 做 TLS termination 的 nginx / Apache 配置細節

## 案例回寫

CloudHSM 在 07 案例庫沒有直接 vendor-level 事件、以下案例採對照引用：

| 案例                                                                                                                                                       | 跟 CloudHSM 的關係（對照）                                                                                                                                    |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | 核心對照 — CloudHSM 設計 *AWS 不持 key + key 不能 export* 是 Storm-0558 反設計、攻擊者進 cluster 也搬不走 key material、Quorum policy 阻單一 admin compromise |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                        | CloudHSM key rotation 需要應用層配合 key alias 切換、不像 KMS 自動 rotation；scope map 跟雙軌驗證窗口更明顯、PKCS#11 client 散落 host 群時 rotation 要分批    |
| [Azure AD Identity Control Plane 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)                                   | 對照啟示 — HSM cluster 是 single point of compromise、cross-AZ topology + cross-region backup 是 *availability* 的設計依據、不是 confidentiality              |

## 下一步路由

- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)（HSM 為 CA / signing key 的 FIPS-grade root custodian）、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/)、[Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)、[Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)
- 整合：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（CloudHSM 作為 Vault auto-unseal master key custodian）
- 整合：[KMS Custom Key Store](https://docs.aws.amazon.com/kms/latest/developerguide/custom-key-store-overview.html)（KMS API + CloudHSM backing 雙重）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（HSM 失效如何 routing 進 IR 流程）
- 官方：[AWS CloudHSM Documentation](https://docs.aws.amazon.com/cloudhsm/)
