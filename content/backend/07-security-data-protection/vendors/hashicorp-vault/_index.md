---
title: "HashiCorp Vault"
date: 2026-05-18
description: "Self-hosted secret management 與 dynamic credential / encryption-as-a-service / PKI engine、跨雲跨環境的 secret 控制面"
weight: 1
tags: ["backend", "security", "vendor", "hashicorp-vault", "secret-management", "pki"]
---

HashiCorp Vault 是 self-hosted 的 secret management 控制面、解決三個核心問題：*static secret 集中保管*（KV engine、跟 [Secret Management](/backend/knowledge-cards/secret-management/) 卡同概念）、*dynamic credential 即用即發即收*（database / cloud / SSH engine 在請求時動態建立短期憑證）、*encryption-as-a-service 與內部 PKI*（transit engine 把加解密外包給 Vault、PKI engine 自簽憑證）。三件事在 cloud-native 替代品（[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) / [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) / [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)）裡通常拆成不同 service、且綁單一雲。

## 服務定位

Vault 的核心定位是 *跨雲 + 跨環境 + 跨 secret 形態的單一 secret 控制面*。當組織同時跑 AWS + GCP + on-prem K8s、又需要 dynamic database credential + 內部 PKI + envelope encryption、用三個 cloud-native service 拼起來會出現 *secret 治理鏈不連續*（AWS 的 secret 怎麼授權 GCP service 取用、on-prem app 怎麼拿短期 cloud credential、內部 CA 跟外部 ACM 怎麼分工）。Vault 把這層 *統一抽象* — 應用端只跟 Vault 講話、Vault 後端接各雲 KMS / database / PKI。

跟 [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) / [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) 相比、Vault 多了：*dynamic credential engine*（cloud-native 對應產品有限）、*transit engine* 做 encryption-as-a-service、*PKI engine* 自簽內部憑證、*跨雲統一介面*。代價是 *自管運維*（HA cluster、auto-unseal、replication、upgrade）— 跟自管 [Keycloak](/backend/07-security-data-protection/vendors/keycloak/) 的取捨同類。HCP Vault（HashiCorp Cloud Platform）是 HashiCorp 託管版、把運維交還、但綁 HashiCorp。

## 本章目標

讀完本頁、讀者能判斷：

1. 哪些 secret 適合 Vault（dynamic credential、跨雲、PKI、encryption-as-a-service）、哪些直接用雲端 native service 即可
2. Vault deployment 的最低安全需求（auto-unseal、HA、audit device、policy、replication）
3. Vault 自己出事時的降級路徑（seal storm、root token 復原、audit log gap）
4. 何時用 Vault、何時走 [Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) / [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) / [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/) 的取捨

## 最短判讀路徑

判斷 Vault deployment 是否健康、最少看五件事：

- **誰能做什麼**：root token 是否已 revoke、policy 是否走 path-based least privilege、admin 是否走 OIDC / [AWS IAM auth](/backend/07-security-data-protection/vendors/aws-iam/) 而不是 token、break-glass token 是否離線存
- **Auth method 收緊**：AppRole / Kubernetes / OIDC / JWT auth 哪些開、role 對應的 policy 是不是過寬、TTL 是否短、`bound_*` 條件是否鎖（namespace / audience / subject）
- **Secret engine 設定**：KV v2 開 versioning？dynamic engine（database / aws / pki）lease TTL 多久、max TTL 限制是什麼、revocation 是否驗證生效
- **Seal / unseal 治理**：是否走 auto-unseal（KMS-backed）、recovery key 持有者跟 Shamir threshold、replication 跟 DR cluster 是否同步
- **證據是否可回查**：audit device（file / syslog / socket）是否多 channel、是否同步到 SIEM、replay 攻擊防護是否開（HMAC + nonce）

五件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 [Secret Management](/backend/knowledge-cards/secret-management/) 邊界的待補項目。

## 日常操作與決策形狀

**Auth method 設計**：AppRole 適合不在雲端 metadata 內的 workload（on-prem、CI runner）但 *secret_id* 本身要妥善保管；Kubernetes auth 適合 K8s 內 workload、用 ServiceAccount token + projected token；[AWS IAM auth](/backend/07-security-data-protection/vendors/aws-iam/) 適合 AWS 內 workload、走 STS 簽名驗證、不需要存 secret；OIDC / JWT 適合 human admin + CI（GitHub Actions / GitLab CI 走 OIDC token）。每個 auth method 對應 *一組 role*、role 綁 *policy* 跟 *TTL*。

**Secret engine 分層**：KV v2（static secret + version history）作為基線；dynamic database engine（PostgreSQL / MySQL / MongoDB）發短期 DB user、`max_ttl = 1h` 級別、過期 Vault 自動 revoke；AWS / Azure / GCP secret engine 對 cloud account 發短期 STS credential / service account key；PKI engine 自簽憑證、跟 [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) 整合做 K8s workload mTLS；transit engine 做 envelope encryption — app 把資料丟給 Vault 加密、key 不離 Vault。

**Policy（path-based）**：Vault policy 是 *path + capabilities*（create / read / update / delete / list / sudo）的 mapping。常見錯配：給 `secret/*` read 等於整個組織所有 secret 都看得到、應該用 `secret/data/{team}/*` 之類前綴限定；admin policy 不要給 `sudo` 太寬、policy 變更走 PR review + CI apply。

**Rotation 跟 lease 治理**：static secret（KV）的 rotation 是 *app 自己做*（拿新 secret 後手動 update）；dynamic secret 是 *Vault 控制 lease 生命週期*、app 只要在 TTL 內續租即可。對應 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)：static secret 的 rotation 必須有 *scope map* — 哪些 service 用了同一把 secret、哪個 service 支援零停機 rotation、誰是 last to be rotated。沒這份 map 就會發生「rotate 後某個被遺忘的 cron job 認證失敗、整個下游崩」。

**Seal / unseal 設計**：Vault 啟動時 sealed、必須 unseal 才能服務。Shamir secret sharing 是預設（5 key holders、3 threshold）— 任何重啟需要找齊 3 個人合 unseal、production 場景幾乎都該換 auto-unseal（用 [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) / [GCP KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) / [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/) 當 master key custodian）。代價是 *把 master key 託給雲廠* — 不接受的組織保留 Shamir + 嚴格 key holder rotation。

**Audit device 是 *必開***：Vault 預設不開 audit、要手動 enable（`vault audit enable file path=/var/log/vault_audit.log`）。沒 audit device 在 production = 事故時 *連 token 被誰用過都查不到*。建議多 channel（file + syslog + 推到外部 SIEM）— 單一 channel 失效（disk full、socket broken）Vault 會拒絕請求、影響 availability、所以多 channel 是必要冗餘。

**Break-glass 與 root token**：初始化時產生的 root token 應該 *用完立刻 revoke*、改用 admin policy + OIDC auth。break-glass scenario 用 *recovery key 重新發 root token*、recovery key 走 Shamir 多人持有 + 離線存。

## 核心取捨表

| 取捨維度           | Vault (self-hosted)                               | HCP Vault                 | AWS Secrets Manager                                                                                                                | Google Secret Manager                        | Azure Key Vault                                                                               |
| ------------------ | ------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 部署模型           | 自管 cluster（HA + replication）                  | HashiCorp 託管            | AWS managed                                                                                                                        | GCP managed                                  | Azure managed                                                                                 |
| 跨雲               | 強 — 同一介面跨 AWS / GCP / Azure / on-prem       | 強                        | 弱 — 綁 AWS                                                                                                                        | 弱 — 綁 GCP                                  | 弱 — 綁 Azure                                                                                 |
| Dynamic credential | DB / cloud / SSH engine 完整                      | 同 OSS                    | 無 — 僅 RDS / Redshift static rotation Lambda                                                                                      | 無 — 自寫 Cloud Function；secret-less 走 WIF | 無 — 純 static；secret-less 走 Managed Identity                                               |
| PKI / transit      | 內建 PKI engine + transit engine                  | 同 OSS                    | 走 [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/) + [KMS](/backend/07-security-data-protection/vendors/aws-kms/) | 走 cloud KMS + Certificate Authority Service | 走 [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/) cert 功能 |
| 運維成本           | 高 — HA、upgrade、replication、cert 自己顧        | 低 — HashiCorp 顧         | 低                                                                                                                                 | 低                                           | 低                                                                                            |
| 第三方信任成本     | 低 — 自管                                         | 中 — HashiCorp 控制面     | 中 — AWS 控制面                                                                                                                    | 中 — GCP 控制面                              | 中 — Microsoft 控制面                                                                         |
| 適合場景           | 跨雲、需要 dynamic credential、內部 PKI、預算允許 | 想要 Vault 能力但不想自管 | AWS-heavy + 簡單 static secret                                                                                                     | GCP-heavy + Workload Identity 已主導         | Azure-heavy + Managed Identity 已主導                                                         |
| 退場成本           | 中 — 自己掌握資料、但 dynamic engine 接線多       | 中                        | 低                                                                                                                                 | 低                                           | 低                                                                                            |

選 Vault 的核心訴求：*跨雲 + dynamic credential + 內部 PKI + transit encryption 至少滿足兩項*、且能投入 SRE 量能跑 HA cluster、有 SIEM 接 audit log、能接受 self-hosted 的 upgrade / cert / DB 運維成本。單純需要 AWS-only static secret rotation、直接用 [Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) 更便宜更簡單。

## 進階主題

**Dynamic credential 的 lease 生命週期治理**：dynamic engine 發出的 credential 都帶 lease ID、Vault 在 TTL 到期時自動 revoke（database engine 真的會 DROP USER、cloud engine 真的會 DeleteAccessKey）。設計時要算清楚 *app 連線池的 connection lifetime* — DB connection 持續用同一組 credential、credential lease 過期但 connection 還在會出現 *staled credential* 問題。常見作法：lease TTL > connection idle timeout * 2、加 lease renewal mechanism（app 在 TTL 50% 時主動 renew）。

**Transit engine（encryption-as-a-service）**：app 不持 encryption key、把 plaintext 丟給 Vault `encrypt` API、拿 ciphertext 回來；解密時把 ciphertext 給 Vault `decrypt` API。Key 完全不離 Vault、所有 cryptographic operation 在 Vault 內、app 只需要 *encrypt / decrypt capability*。對應 [Storm-0558 signing key chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) 的對照啟示：key 不能 export 是減 blast radius 的關鍵設計 — transit 把這個原則內建。

**PKI engine + cert-manager 整合**：Vault PKI engine 可以當內部 root CA + intermediate CA、issue 短期 cert（hours-level）給 K8s workload；[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) 用 Vault PKI issuer 自動更新 cert。比起手動跑 OpenSSL CA、Vault PKI 的優勢是 *cert lifecycle 進 Vault audit*、跟 secret rotation 用同一套 evidence chain（呼應 [credential rotation scoped evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)）。

**Namespace（Enterprise）跟 multi-tenancy**：Enterprise 版 namespace 是 *tenant 邏輯隔離*、每個 namespace 有自己的 auth method、policy、secret engine。OSS 版沒 namespace — 多團隊共用 Vault 要靠 path 命名規約 + policy prefix 拼隔離、邊界較鬆。大組織通常需要 namespace 才能避免單一 admin 跨 team 越界。

**Replication（Enterprise）**：Performance Replication（主從 + 多 region active）跟 DR Replication（純 standby）是兩個獨立功能。production HA 通常需要 *同 region 的 cluster + 跨 region 的 DR replication*、recovery key 跟 unseal 機制要跨 cluster 一致。

## 排錯與失敗快速判讀

- **Audit device 沒開**：production 啟動時忘了 enable audit、事故發生時無 forensic data — 啟動 checklist 必含「enable audit before serving traffic」、SRE runbook 用 health check 驗
- **Policy 過寬**：給整個 `secret/*` read、單一 token 等於拿到全公司 secret — 用 path prefix 限定到 `{team}/{env}/*`、policy review 走 PR
- **Dynamic credential lease 太長 / 沒 max_ttl**：DB user 跑了一週還沒收、攻擊者只要拿到一次就長期可用 — 設定 lease TTL = 1h、max_ttl = 24h
- **Auto-unseal KMS access 沒監控**：[AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) / [GCP KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) 的 Vault auto-unseal key 沒 alert 異常使用 — KMS 端設 alert（GetKeyValue / Decrypt 突增）
- **Replication lag 沒 alert**：Performance / DR replication 落後幾分鐘到幾小時、failover 時拿到 stale state — Prometheus 監控 `vault.replication.*` metric
- **Root token 未 revoke**：初始化時的 root token 還在用、policy / audit / OIDC 全 bypass — 初始化 checklist 強制 revoke、CI 跑 `vault token lookup` 驗證 root 不可用
- **Sealed 後 unseal key 找不到人**：production cluster 緊急 restart、Shamir threshold 3 但有 1 個 key holder 在度假 — production 必須 auto-unseal、recovery key 走 [break-glass](/backend/07-security-data-protection/identity-access-boundary/) 流程

## 何時改走其他服務

| 需求形狀                                                       | 改走                                                                                                                                          |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS-only + 簡單 static secret                                  | [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)                                                      |
| GCP-only + 已用 Workload Identity                              | [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)                                                  |
| Azure-only + 已用 Managed Identity                             | [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)                                                              |
| 大型 cryptographic / [HSM](/backend/knowledge-cards/hsm/) 需求 | [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)（FIPS 140-2 Level 3、Vault auto-unseal 後端）                              |
| 公開憑證 PKI（serving cert）                                   | [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/) / [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) |
| K8s workload cert 自動化                                       | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)（可用 Vault 當 issuer）                                            |
| 跨服務 workload identity (SPIFFE)                              | [SPIRE](/backend/07-security-data-protection/vendors/spire/)                                                                                  |
| Secret 全公司 rotation 證據鏈                                  | [7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)                          |

## 不在本頁內的主題

- Vault 完整 API reference 跟 CLI 詳盡用法
- 每個 secret engine 的內部實作細節（DB connection pool、cloud SDK 呼叫順序）
- Enterprise 各 license tier 的功能對照
- Terraform / Ansible 跟 Vault 整合的完整步驟
- 各 auth method 的 OIDC / SAML provider 設定教學

## 案例回寫

Vault 在 07 案例庫沒有直接 vendor-level 事件、以下案例採對照引用：

| 案例                                                                                                                                                                  | 跟 Vault 的關係（對照）                                                                                                                                        |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                                   | static secret rotation 必須有 scope map — Vault KV 多 service 共用同一把 secret 時、rotation 要分批 + 雙軌驗證窗口、不能一次 push 全域更新                     |
| [Microsoft Storm-0558 Signing Key Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | transit engine 的設計啟示 — key 不離保護邊界、即使被讀也搬不走、跟 HSM-bound 同 mindset                                                                        |
| [CircleCI 2023 Secrets Rotation (red-team)](/backend/07-security-data-protection/red-team/cases/supply-chain/circleci-2023-secrets-rotation/)                         | CI 平台 secret 集中化的 blast radius — Vault AppRole secret_id 散落在 CI runner 時、CI 出事 = 大量 AppRole credential 一次外洩、需 scope tag + 優先級 rotation |
| [Okta Support System 2023](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)                                                             | 對照啟示 — Vault 自己的 support / debug tooling（root token、recovery key）也是 secret leak vector、HAR 級別的事件可發生在任何 admin console                   |

## 下一步路由

- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)、[Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)、[Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)
- 下游：[AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) / [Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)（Vault auto-unseal master key custodian）
- 下游：[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)（用 Vault PKI engine 作為 K8s workload cert issuer）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Vault 事件如何 routing 進 IR 流程）
- 官方：[Vault Documentation](https://developer.hashicorp.com/vault/docs)
