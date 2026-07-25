---
title: "Google Cloud KMS"
date: 2026-05-18
description: "GCP 原生 key management service、KeyRing / CryptoKey Version 設計、CMEK 整合 + Cloud HSM + External Key Manager"
weight: 5
tags: ["backend", "security", "vendor", "google-cloud-kms", "kms", "encryption", "gcp"]
---

Google Cloud KMS 是 GCP 原生的 key management service、把 envelope encryption、asymmetric signing 與 MAC 等密碼運算集中在受控的 key custodian 內、key material 不離保護邊界。應用端只持 *KMS resource name + IAM 權限*、用 `Encrypt` / `Decrypt` / `AsymmetricSign` API 把 plaintext 或 hash 送進 Cloud KMS、key 永遠在 Google 管理的 software 模組或 [HSM](/backend/knowledge-cards/hsm/) 內運算完才把結果送回。整個 GCP 的 CMEK（Customer Managed Encryption Key）生態都以 Cloud KMS 為錨點 — GCS bucket、BigQuery dataset、Persistent Disk、Cloud SQL、GKE etcd 都可指定一把 Cloud KMS key 做加密、跟 cloud-native 預設加密（GCP 自管 key、客戶看不到）拉出邊界。

## 服務定位

Cloud KMS 的核心定位是 *GCP-native envelope encryption + signing 控制面*、用 KeyRing 作為 organizational + locational grouping、CryptoKey + CryptoKeyVersion 作為 key material 的版本軸。跟 [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) 相比、最大差異是 *沒有獨立的 Key Policy*：權限完全走 GCP IAM（Role Binding 綁到 KeyRing 或 CryptoKey resource）、好處是跟 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) 統一治理（同一份 IAM audit、同一套 conditional binding）、代價是少了 AWS KMS Key Policy 那種 *key-level 的獨立 deny override*。

跟 [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/) 相比、Cloud KMS 拆得更細：Azure 把 secret + key + certificate 合在同一個 Key Vault service、Google 拆成 [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)（secret）+ Cloud KMS（key）+ Certificate Authority Service（PKI），各 service IAM、quota、audit 獨立。跟 [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/) 相比、Cloud KMS Protection Level=HSM 是 *managed HSM*（FIPS 140-2 Level 3、Google 顧 cluster）、CloudHSM 是 *single-tenant 專屬 HSM*（客戶顧 cluster、合規隔離更強）。跟 [Vault transit](/backend/07-security-data-protection/vendors/hashicorp-vault/) 相比、Cloud KMS 綁 GCP、Vault transit 可跨雲；但 Vault 自己常用 Cloud KMS 當 auto-unseal master key custodian。

## 本章目標

讀完本頁、讀者能判斷：

1. KeyRing 該放哪個 location（global / regional / dual-regional / multi-regional）、為何一旦決定無法搬遷
2. CryptoKey Version + Primary 版本軸怎麼支撐 rotation、何時該 disable / destroy 舊 version
3. Protection Level（SOFTWARE / HSM / EXTERNAL）跟 Cloud HSM、External Key Manager 的取捨
4. CMEK 整合 GCS / BigQuery / Persistent Disk 跟 cloud-native default encryption 的邊界差異

## 最短判讀路徑

判斷一份 Cloud KMS 部署是否健康、最少看四件事：

- **KeyRing location 對不對**：production sensitive key 用 region / multi-region、避免不必要的 `global` KeyRing；location 一旦設定 *不能改*、key 也搬不出原 KeyRing — 設錯只能建新 KeyRing + 重新加密所有 ciphertext
- **IAM Conditions 跟 least privilege**：`roles/cloudkms.cryptoKeyEncrypterDecrypter` 不該綁到 KeyRing level（會放大爆炸半徑）、應綁到具體 CryptoKey；admin 跟 use 角色分離（`roles/cloudkms.admin` ≠ `roles/cloudkms.signer`）；敏感 key 加 IAM Condition（時間窗、resource attribute）
- **Cloud Audit Logs 開到對的層級**：Admin Activity（建 key、改 IAM、destroy version）預設開、Data Access（每次 Encrypt / Decrypt / Sign）*預設關* — production sensitive key 必須在 IAM audit config 把 Data Access 開、否則「誰用 key 做了什麼」查不到
- **Protection Level 對齊合規**：production 跟 PII / 金融 / 醫療資料的 key 應走 HSM 或 EXTERNAL、SOFTWARE 只給 dev / 低敏感場景；EKM 對應 *資料主權*（key 物理上不在 GCP）

四件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 KMS 邊界的待補項目。

## 日常操作與決策形狀

**KeyRing 設計**：KeyRing 是 *組織單位 + 位置鎖*。建議切法：依 *環境 + 用途* 拆（`prod-data-encryption-asia-east1`、`prod-signing-global`、`dev-data-encryption-asia-east1`），不要全公司一個 KeyRing。Location 選擇：跟資料 colocate（GCS bucket 在 `asia-east1` 的 key 也放 `asia-east1` KeyRing、避免跨區延遲與資料主權問題）；signing key 多半放 `global` 或 multi-region 提高可用性；CMEK 給 BigQuery 時 KeyRing location 必須跟 dataset location 一致、否則綁不上。一個原則：*KeyRing location 是一次性決策*、上線前確認跟 cloud resource location + 法規要求對齊。

**CryptoKey Version 與 Primary**：CryptoKey 有多個 version（`projects/.../cryptoKeys/k/cryptoKeyVersions/1`、`v2`、`v3`）、其中一個是 Primary — 所有 `Encrypt` API 預設用 Primary version 加密、`Decrypt` 自動依 ciphertext 內嵌的 version ID 找對應 version 解。Rotation 不是「換 key」、是 *建立新 version 並 promote 為 Primary*；舊 version 仍可 decrypt 既有 ciphertext（除非手動 disable / destroy）。Destroy 是 24 小時延遲（可在期內 restore）、destroy 之後 ciphertext 永久不可解 — 排程 destroy 前必須確認沒有遺留 ciphertext 還在用該 version。

**Auto Rotation**：CryptoKey 可設 `rotationPeriod`（最短 1 天、預設 90 天）、KMS 在到期時自動建立新 version + promote 為 Primary、app 不需要改 code。Auto rotation 只對 *symmetric encryption key* 有效；asymmetric key（signing / decryption）不支援 auto rotation、需要手動建 version + 通知 consumer 更新 public key。注意 auto rotation 是 *key version 換*、不會 re-encrypt 既有資料 — 真正的 *資料 re-encryption* 是另一條工作流（讀回 ciphertext + 用新 Primary 重加密寫回）、要依 CMEK-integrated resource 各自規劃。

**Protection Level**：SOFTWARE（軟體運算、最便宜、FIPS 140-2 Level 1）/ HSM（Cloud HSM 後端、FIPS 140-2 Level 3、key 物理上在 Google 管理的 HSM cluster）/ EXTERNAL（External Key Manager、key 在客戶自管的外部 HSM、Cloud KMS 把運算委派出去）。Production sensitive key 應走 HSM、SOFTWARE 給 dev / 低敏感場景。Protection Level 是 *CryptoKey 建立時決定*、不能改 — 要升等只能建新 CryptoKey + 遷移 ciphertext。

**CMEK 整合**：CMEK 把 Cloud KMS key 綁到 GCS bucket / BigQuery dataset / Persistent Disk / Cloud SQL / GKE etcd / Pub/Sub topic / Dataflow job 等 resource。設定方式：cloud service 的 service account（如 `service-PROJECT_NUMBER@gs-project-accounts.iam.gserviceaccount.com`）取得該 CryptoKey 的 `cryptoKeyEncrypterDecrypter` 權限、resource 在加密時自動呼叫 KMS。跟 cloud-native default encryption（GCP 自己管 key）的差異：CMEK 下 *客戶可隨時 disable key 讓整個 bucket / dataset 立刻無法解*（compliance kill switch）、default encryption 沒這個能力。代價是 KMS 故障 = CMEK-integrated resource 全部讀寫卡住、所以 production KMS 自身 SLA 跟 monitoring 是 cluster-level dependency。

**External Key Manager (EKM)**：GCP 把 encryption / decryption operation *委派* 給客戶自管的外部 HSM（Thales、Equinix SmartKey、Fortanix 等）、key 物理上不在 GCP、Cloud KMS 只是個 proxy。適合 *資料主權* 嚴格的場景（歐盟金融、政府機密、跨境法規）— 客戶撤銷外部 HSM 的存取、GCP 立刻無法解密、達成「Google 看不到資料」的合規承諾。代價：每次 Encrypt / Decrypt 都打外部 HSM、延遲跟可用性受外部 HSM 影響、運維複雜度大幅上升。

**IAM 整合**：用 Role Binding 控制存取（綁在 KeyRing 或 CryptoKey resource）— `roles/cloudkms.cryptoKeyEncrypterDecrypter`（Encrypt + Decrypt）/ `roles/cloudkms.signer`（AsymmetricSign）/ `roles/cloudkms.signerVerifier`（含 public key 取得）/ `roles/cloudkms.admin`（建 key、改 IAM）。對應 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) 的 conditional binding、可加時間窗、resource attribute、access level 條件。跟 AWS KMS 的關鍵差異：*沒有 Key Policy* — 所有授權都在 IAM、好處是統一治理、代價是少了 key-level 的獨立 deny override（AWS KMS Key Policy 可寫「即使 IAM 給了 admin、仍 deny destroy」、Cloud KMS 要用 Organization Policy 或 IAM Deny 達成類似效果）。

## 核心取捨表

| 取捨維度         | Google Cloud KMS                                             | AWS KMS                                                    | Azure Key Vault                         | Vault transit                                |
| ---------------- | ------------------------------------------------------------ | ---------------------------------------------------------- | --------------------------------------- | -------------------------------------------- |
| 部署模型         | GCP managed                                                  | AWS managed                                                | Azure managed                           | self-hosted 或 HCP                           |
| 跨雲             | 弱 — 綁 GCP                                                  | 弱 — 綁 AWS                                                | 弱 — 綁 Azure                           | 強 — 同介面跨雲                              |
| Multi-region key | 用 multi-region KeyRing（key material 在多 region 鏡像）     | Multi-Region Key 較直接（單一 key ID、跨 region 自動同步） | 支援 geo-replication                    | 跨雲、需自行設計 replication                 |
| Key 權限模型     | 純 IAM Role Binding、無 Key Policy                           | IAM + 獨立 Key Policy（雙層授權）                          | RBAC + Access Policy 雙模式             | Vault policy（path-based）                   |
| HSM 選項         | Protection Level=HSM（managed、FIPS 140-2 L3）               | AWS KMS HSM-backed（預設）+ CloudHSM（專屬）               | Premium tier + Managed HSM              | 依賴後端 KMS / HSM                           |
| 外部 key 託管    | External Key Manager (EKM)                                   | XKS (External Key Store)                                   | BYOK + Managed HSM                      | 自管 HSM unseal                              |
| Audit            | Cloud Audit Logs（Data Access 需手動開）                     | CloudTrail（KMS event 自動進）                             | Azure Monitor / Activity Log            | Vault audit device                           |
| CMEK 整合廣度    | GCS / BQ / PD / Cloud SQL / GKE etcd / Pub/Sub / Dataflow    | S3 / EBS / RDS / DynamoDB / Lambda env                     | Storage / SQL / Cosmos / Disk           | 不適用（app-level）                          |
| 適合場景         | GCP-heavy、需 CMEK 整合、Workload Identity Federation 已主導 | AWS-heavy、需 Multi-Region Key + Key Policy 精細控制       | Azure-heavy、需要 secret + key 統一治理 | 跨雲、需要 app-level encryption-as-a-service |

選 Cloud KMS 的核心訴求：*GCP 是主力雲* + 需要 CMEK 把 GCS / BigQuery / PD / Cloud SQL 的加密 key custody 拉回客戶手上 + 接受 IAM-only 授權模型。需要 *跨雲統一 key custody* 走 [Vault transit](/backend/07-security-data-protection/vendors/hashicorp-vault/) 或 EKM；需要 *單一專屬 HSM 隔離* 走 [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/) 或 EKM 接 on-prem HSM。

## 進階主題

**External Key Manager (EKM) 與資料主權**：EKM 讓 key 物理上不在 GCP、Cloud KMS 變成 proxy 把 cryptographic operation 委派給客戶自管 HSM。常見部署：金融 / 政府用 *EKM via VPC*（外部 HSM 在客戶 VPC 內、Cloud KMS 走 PSC 連線、延遲較低）、跨境合規用 *EKM via Internet*（HSM 在第三方 KMS provider、延遲較高但治理邊界更乾淨）。代價：每次 Encrypt / Decrypt = 一次外部呼叫、CMEK-integrated resource 的讀寫吞吐量受外部 HSM 限制、外部 HSM 故障 = 整個 GCP 端讀寫卡住。

**Cloud HSM（Protection Level=HSM）**：把 CryptoKey 物理上鎖在 Google 託管的 FIPS 140-2 Level 3 HSM cluster 內、key 不可 export、所有 cryptographic operation 在 HSM 邊界內完成。對應 [Microsoft Storm-0558 Signing Key 2023](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/) 的對照啟示：signing key 一旦能被 export 或從 memory crash dump 撈出、整個信任鏈崩 — HSM-bound key 從設計上斷掉這條路徑。代價：HSM 後端比 SOFTWARE 貴、operation 延遲略高（典型多 < 10ms）、quota 也獨立計算。

**Asymmetric Key 做 JWT signing**：CryptoKey purpose=`ASYMMETRIC_SIGN` 配 algorithm（RSA / EC）、app 透過 `AsymmetricSign` API 把 JWT header+payload 的 hash 送進 KMS、KMS 回 signature。Public key 走 `GetPublicKey` API 取得、給 JWKS endpoint 對外發布。優勢：private key 不離 KMS、即使 app server compromise 也無法搬走 signing key；劣勢：每次簽名都 round-trip 一次 KMS、高 QPS 場景要算 quota 跟延遲（典型 ~10-30ms / sign）。

**跟 Google Secret Manager 的 CMEK 整合**：[Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) 預設用 GCP 管的 key 加密 secret、若要 *客戶管 key*、可設 CMEK 把 GSM 的 secret 用客戶 Cloud KMS key 加密。意義：disable Cloud KMS key 立刻讓 GSM secret 不可讀（compliance kill switch）— 但代價是 KMS 故障 = GSM 也卡住、是強耦合 dependency。

**Multi-region key**：Cloud KMS 的 multi-region KeyRing（如 `us`、`europe`、`asia`）讓 key material 在多 region 鏡像、提高可用性但加密 / 解密延遲較高。AWS KMS 的 Multi-Region Key 設計不同（單一 key ID 跨 region 同步、有獨立的 primary / replica 角色）— 跨雲遷移 / 多雲 active-active 設計時要留意這個差異、Cloud KMS multi-region 比較像 *單一邏輯 key 多 region 可用*、不是 *多 region 各自獨立可寫*。

**Import 自有 key material（BYOK）**：Cloud KMS 可 import 客戶自產的 key material（透過 wrapping key 包覆後上傳）、適合需要 *客戶端 key generation 證據鏈* 的合規場景。代價：import 的 key 不能 auto rotate（rotation 必須客戶端重新產 key 再 import），且 SOFTWARE / HSM Protection Level 都支援、EXTERNAL 不適用（EXTERNAL 本來就在外部 HSM、不走 import 路徑）。

**Organization Policy 與防護欄**：跟 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) 整合的 Org Policy 可在 organization-level 強制 *只允許 HSM / EXTERNAL key*（`constraints/gcp.restrictNonCmekServices`）、防止工程師建出 SOFTWARE key 處理敏感資料。這層防護欄比依賴 reviewer 紀律有效、屬於 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) 同類「規約靠系統而非紀律」的設計。

## 排錯與失敗快速判讀

- **KeyRing location 設錯**：KeyRing 建在 `global`、要綁 `asia-east1` 的 BigQuery dataset CMEK — 綁不上、location 不能改、只能建新 KeyRing + 重新加密 — 上線前 review KeyRing location 跟 resource location 對齊
- **Data Access audit 沒開**：production 用 Cloud KMS 做 signing、事故時要查 *誰用 key 簽了什麼*、發現只有 Admin Activity log、沒有 Decrypt / Sign 記錄 — IAM audit config 加 `dataAccess` log type、留意 audit log 自己會增加成本與 quota
- **CMEK key disable 後 resource 全卡**：disable CryptoKey 想做 compliance 演練、整個 GCS bucket 讀寫立刻 503 — disable 是 *全或無*、要演練得排維護窗、有 rollback 計畫（re-enable 後恢復）
- **Auto rotation 設定 + asymmetric key**：以為 asymmetric signing key 也會 auto rotate、上線數月後發現 version 1 還在用 — asymmetric key 不支援 auto rotation、要手動建 version + 通知 JWKS consumer
- **IAM Role 過寬**：給整個 KeyRing `cryptoKeyEncrypterDecrypter`、單一 service account 可以解所有 key — 改綁到具體 CryptoKey、加 IAM Condition
- **EKM 外部 HSM 故障**：外部 HSM 連線中斷、Cloud KMS 端 Encrypt / Decrypt 全 fail、所有 CMEK-integrated resource 讀寫卡住 — EKM 需要 dual HSM redundancy + Cloud KMS 端 monitoring alert
- **Destroy 後資料不可解**：CryptoKeyVersion destroy 後 24 小時 grace period 過了、發現某個 backup 還是用該 version 加密 — destroy 前必須跑 inventory 確認沒有 ciphertext 還掛在該 version

## 何時改走其他服務

| 需求形狀                                 | 改走                                                                                                                 |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| AWS-only 加密 + 需 Key Policy 精細控制   | [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/)                                                     |
| Azure-only 加密 + 需 secret + key 同治理 | [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)                                     |
| 跨雲統一 encryption-as-a-service         | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) transit engine                      |
| 單一專屬 HSM 隔離 / 跨雲合規             | [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)                                                   |
| GCP secret 管理（非 key）                | [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)                         |
| GCP IAM 治理基底                         | [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)                                   |
| 公開憑證 / PKI                           | Certificate Authority Service（GCP）或 [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/)    |
| Secret rotation 證據鏈                   | [7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/) |

## 不在本頁內的主題

- Cloud KMS 完整 API reference 跟 `gcloud kms` CLI 詳盡用法
- Cloud HSM partition 內部架構、FIPS 140-2 Level 3 驗證細節
- EKM 各 partner（Thales / Fortanix / Equinix）的整合步驟與 API 對照
- BigQuery / GCS / Cloud SQL 各自 CMEK 設定的完整教學
- Cloud KMS pricing 詳盡計算（key version 數、operation 次數、HSM 加成）

## 案例回寫

Cloud KMS 在 07 案例庫沒有直接 vendor-level 事件、以下案例採對照引用：

| 案例                                                                                                                                                                  | 跟 Cloud KMS 的關係（對照）                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Microsoft Storm-0558 Signing Key 2023](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/)                                            | Cloud KMS Protection Level=HSM 把 signing key 鎖在硬體、不可 export、跟 HSM-bound mindset 同源 — signing key 一旦能 export 整條信任鏈崩                                     |
| [Microsoft Storm-0558 Signing Key Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | Asymmetric Key + Cloud Audit Data Access 是 *誰用 key 簽什麼* 的稽核基礎、預設關閉的 Data Access log 在 production 必須開、否則事故時無證據                                 |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                                   | Auto Rotation 是 vendor-controlled、但 CMEK 整合的 GCS bucket / BQ dataset 的 *re-encryption schedule* 還是要自己管、否則 rotation 只換 key version、舊資料還是用舊 version |

## 下一步路由

- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)（KMS 為 TLS / signing key 的 root custodian）、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/)、[Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)、[CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)
- 平行（secret）：[Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)
- 上游（IAM）：[Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)（Cloud KMS 權限完全走 IAM Role Binding）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（KMS 事件如何 routing 進 IR 流程）
- 官方：[Cloud KMS Documentation](https://cloud.google.com/kms/docs)
