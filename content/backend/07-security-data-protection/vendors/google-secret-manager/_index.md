---
title: "Google Secret Manager"
date: 2026-05-18
description: "GCP 原生 secret store、CMEK + Workload Identity Federation 整合、rotation 走自寫 Cloud Function 而非 built-in Lambda"
weight: 3
tags: ["backend", "security", "vendor", "google-secret-manager", "gsm", "secret-management", "gcp"]
---

Google Secret Manager（GSM）是 GCP 原生的 *static secret 集中保管* 服務、設計上刻意保持 *簡單*：只負責 secret 儲存、版本管理、IAM 授權、跟 [Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) 整合的 envelope encryption。rotation orchestration、cross-region replication policy、dynamic credential issuing 都不在 GSM 自己做、留給上層用 Cloud Function / Cloud Run 自組。跟 [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) 最大的差異是 *沒有 built-in rotation Lambda* — rotation logic 要自己寫、GSM 只提供 *Rotation Schedule + Pub/Sub event* 當觸發點。

## 服務定位

GSM 的定位是 *GCP-native 的 secret 集中點*、解決三件事：把 secret 從 environment variable / Cloud Build substitution / GitHub secret 收回單一受控位置；用 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) 的 *role binding on secret resource* 控制誰能讀；走 [Workload Identity Federation](/backend/07-security-data-protection/vendors/google-cloud-iam/) 讓 GKE / Cloud Run / 外部 workload（GitHub Actions / AWS / Azure）安全取用、避免長期 service account key 散落。

跟 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 比、GSM 沒有 dynamic credential engine、沒有 transit / PKI engine、沒有跨雲統一介面 — 但運維成本接近於零、跟 GCP IAM / KMS / Cloud Logging 的整合是 first-class。跟 [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) 比、GSM 把 rotation orchestration 推給應用層、自由度高但代價是 *rotation 流程要自己設計*；跟 [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/) 比、兩者 mindset 相近（單雲、IAM-driven、CMEK 整合）、各自綁雲。

## 本章目標

讀完本頁、讀者能判斷：

1. 哪些 secret 適合 GSM（GCP-only、static、靠 IAM 授權即可）、哪些該走 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 或其他雲端 native
2. GSM 最低安全設定（CMEK、Data Access audit、Workload Identity Federation、IAM Conditions）
3. 自寫 rotation Cloud Function 時必須處理的 *版本切換窗口* 跟 *fallback 邏輯*
4. 何時 GSM 不夠用、要往 Vault / Berglas / Cloud HSM 走

## 最短判讀路徑

判讀一個 GSM deployment 是否健康、最少看四件事：

- **誰能讀 secret**：secret resource 上的 IAM binding 是不是用最小單位授權（per-secret、不是 project-level `roles/secretmanager.secretAccessor`）、有沒有上 IAM Conditions 限定時間 / IP / resource tag
- **Key custody 分離**：encryption key 是 Google-managed default key、還是 [Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) CMEK？CMEK 的 key 持有 admin 跟 secret access admin 是不是分人
- **取用路徑**：workload 取 secret 是走 *service account key*（壞模式、長期憑證散落）還是 *Workload Identity Federation*（GKE WIF / 外部 OIDC token exchange）
- **證據是否可回查**：Admin Activity audit 預設開、Data Access audit（`AccessSecretVersion` 誰呼叫）預設 *關*、production 要手動 enable + 接 [Cloud Logging sink](/backend/07-security-data-protection/vendors/google-cloud-iam/) 推到 SIEM

四件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 [Secret Management](/backend/knowledge-cards/secret-management/) 邊界的待補項目。

## 日常操作與決策形狀

**IAM Conditions 收 scope**：GSM 的 secretAccessor role 預設綁到 secret resource、但組織常見錯配是給整個 project 上 `roles/secretmanager.secretAccessor` — 等於整個 project 所有 secret 都能讀。應該用 *per-secret binding*、再加 IAM Conditions（`resource.name.endsWith('prod-db-password')`、`request.time < timestamp('...')`）限縮時間窗口。對應 [Okta Cloudflare 2023 supply chain](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/) 的對照啟示：第三方 token scope 過寬時、上游事件直接傳導下游、IAM Conditions 是收 scope 的工具。

**Secret Version + Alias 模型**：每個 secret 有 monotonic version（v1、v2、v3…）、預設 alias `latest` 指向最新 enabled version。rotation 不是「更新現有 secret」、是 *建立新 version + 把舊 version disable*。應用端要支援 *讀新 version 失敗時 fallback 舊 version*、或在 rotation Cloud Function 內實作 *雙軌驗證窗口*（新版本上線後一段時間舊版還能讀、確認所有 consumer 切過去再 destroy 舊版）。沒這層設計、一次 rotation 就會打掉沒及時更新的 consumer。

**CMEK（Customer-Managed Encryption Key）**：GSM 預設用 Google-managed key、production 應該指向 [Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) CMEK。意義是 *把 key 持有跟 secret 取用分離* — 即使 secret admin 被攻破、沒有 CMEK 的 `decrypt` 權限拿不到明文。代價是 CMEK key region 跟 secret replication 要對齊（key 在 `us-central1` 但 secret 設 automatic replication = key 進不去其他 region、secret access 會失敗）。

**Replication 策略**：automatic 是 GCP 自動跨 region replicate（高可用、不需要管 region 一致性、但 data residency 受 GCP 全球策略支配）；user-managed 是手動指定 region list（精細控制資料駐留、適合有 GDPR / 跨境合規需求的場景、但 region 加減要自己管 + CMEK key 要在每個指定 region 都存在）。一個常見錯配：選 user-managed 但只設一個 region — 等於沒有跨 region 冗餘、該 region 出事 secret 完全讀不到。

**Rotation 是自管 schedule**：GSM 提供的不是 rotation logic、是 *Rotation Schedule*（cron 或固定間隔）、到期會發 *Pub/Sub message* 到指定 topic、由 *自己寫的 Cloud Function / Cloud Run* 訂閱該 topic 執行實際 rotation（呼叫上游系統 API 生新 credential、寫成新 secret version、disable 舊 version）。對應 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)：rotation Cloud Function 必須自己處理 *scope map*（哪些 consumer 用了同一把 secret）跟 *雙軌驗證窗口*（confirm 所有 consumer 切到新版本才 disable 舊版）、不像 AWS Secrets Manager 有 built-in 四階段 flow（`createSecret` → `setSecret` → `testSecret` → `finishSecret`）。

**Workload Identity Federation 取用**：external workload（GitHub Actions / AWS workload / Azure workload / on-prem K8s）用 WIF 拿 GSM secret 是現代預設模式 — workload 用自己的 OIDC token（GitHub OIDC、AWS STS）跟 GCP STS 交換 short-lived access token、再用 token 呼叫 GSM。避開了「長期 service account JSON key 散落 CI / 第三方環境」的問題。GKE 內 workload 走 *GKE Workload Identity*（pod ServiceAccount → GCP service account 綁定）取 secret、也是同 mindset。

**Audit log 治理**：GSM 的 audit 分兩層 — Admin Activity（create / delete / IAM 變更、預設開、免費）、Data Access（`AccessSecretVersion`、預設 *關*、開啟有 log 量跟 BigQuery export cost）。production 不開 Data Access = 事故時 *連 secret 被誰取過都查不到*、必須在 project IAM Audit Config 開、Cloud Logging sink 推到 SIEM 或 BigQuery（見 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)）。

## 核心取捨表

| 取捨維度           | Google Secret Manager                                                                                     | HashiCorp Vault                             | AWS Secrets Manager                                                  | Azure Key Vault                         |
| ------------------ | --------------------------------------------------------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------- |
| 部署模型           | GCP managed                                                                                               | 自管 cluster（HA + replication）            | AWS managed                                                          | Azure managed                           |
| 跨雲               | 弱 — 綁 GCP                                                                                               | 強 — 同一介面跨 AWS / GCP / Azure / on-prem | 弱 — 綁 AWS                                                          | 弱 — 綁 Azure                           |
| Rotation 模型      | 自寫 Cloud Function（Pub/Sub trigger）                                                                    | dynamic engine 自動 lease                   | built-in Lambda 四階段 flow                                          | 自寫 Function App（Event Grid trigger） |
| Dynamic credential | 無（靠 IAM impersonation 替代）                                                                           | DB / cloud / SSH engine 完整                | RDS rotation 有、cloud STS 較弱                                      | 較弱（依靠 Managed Identity）           |
| Encryption key     | Google-managed default / [Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) CMEK | 自管 / KMS auto-unseal                      | [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) CMK | Azure Key Vault key                     |
| External workload  | Workload Identity Federation（成熟）                                                                      | AppRole / Kubernetes / OIDC auth            | IAM Roles Anywhere（較新）                                           | Managed Identity / Workload Identity    |
| 運維成本           | 低                                                                                                        | 高 — HA、upgrade、replication 自己顧        | 低                                                                   | 低                                      |
| 適合場景           | GCP-heavy + WIF 已主導 + static secret 為主                                                               | 跨雲、dynamic credential、內部 PKI          | AWS-heavy + 需要 built-in rotation 收斂                              | Azure-heavy + Managed Identity 已主導   |
| 退場成本           | 低                                                                                                        | 中 — dynamic engine 接線多                  | 低                                                                   | 低                                      |

選 GSM 的核心訴求：workload 主要跑在 GCP（GKE / Cloud Run / Cloud Build）、已經用 Workload Identity Federation 收 service account key、secret 形態以 static 為主（DB password、third-party API key、private key）、rotation 邏輯願意用 Cloud Function 自寫。要跨雲、要 dynamic credential、要內建 rotation flow、需要 transit encryption — 走 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)。

## 進階主題

**CMEK + Cloud KMS 雙軌權限分離**：production 應該 *至少* 把 prod secret 的 CMEK key 跟 secret IAM 分到不同 admin group — secret admin 可以建 / 改 secret 但不能 decrypt（沒 KMS `cloudkms.cryptoKeyDecrypter`），KMS admin 可以管 key 但不能讀 secret 內容。對應 [Microsoft Storm-0558 signing key chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) 的對照啟示：key 不離 KMS 邊界、跟 [HSM](/backend/knowledge-cards/hsm/)-bound 同 mindset；CMEK 是把這個原則內建到 secret 路徑。

**Berglas（OSS pattern）**：[Berglas](https://github.com/GoogleCloudPlatform/berglas) 是 Google 開源的 GSM client library + CLI、在 Cloud Run / Cloud Function / GKE 啟動時把 `sm://...` 參考自動 resolve 成實際 secret value、注進環境變數或檔案。比起應用端寫 SDK 取 secret 的好處：*secret 不進 container image / build manifest*、只有 runtime 取得；缺點是多一層 dependency、且 Berglas 自己有 IAM 需求要管。

**GKE Workload Identity 取用**：GKE pod 用 ServiceAccount → IAM service account 綁定（透過 `iam.gke.io/gcp-service-account` annotation）、pod 內呼叫 GSM API 自動帶 GCP service account 身份、metadata server 簽 token。比起把 service account JSON key mount 進 pod、Workload Identity 沒有長期 credential 在 pod 內、credential rotation 由 GCP metadata 自動處理。

**Secret rotation Cloud Function 樣板**：訂閱 secret 的 rotation topic（Pub/Sub）、message 帶 secret name 跟 trigger reason；Function 內呼叫上游系統 API（DB / SaaS）生新 credential、用 `secretmanager.AddSecretVersion` 寫新 version、等一段時間（雙軌驗證窗口）後 `DisableSecretVersion` 舊 version、最後 `DestroySecretVersion` 完成 rotation。**雙軌窗口的長度必須大於 consumer 的最長 cache TTL**、否則沒及時 refresh 的 consumer 會在 disable 後失敗。

**Pub/Sub event subscription（new in 2023+）**：除了 rotation schedule 自動發 event、GSM 也支援對 secret 任意變更（new version、IAM change）發 Pub/Sub message、可接 SOAR / SIEM 做 *secret 異常變更告警*（例：非 CI service account 在週末新增 secret version）。

## 排錯與失敗快速判讀

- **取 secret 拿到 PERMISSION_DENIED**：通常是 IAM binding 在 project 層但 secret 在某 sub-resource、或 IAM Conditions 把當前 caller 排除 — 用 `gcloud secrets get-iam-policy` 直接看 binding、確認 condition 表達式
- **CMEK 設定後突然讀不到 secret**：CMEK key region 跟 secret replication region 不對齊、或 caller 沒有 KMS decrypt 權限 — 確認 key 在所有 replication region 都有版本、secret accessor service account 有 `cloudkms.cryptoKeyDecrypter`
- **Rotation Cloud Function 跑了但 consumer 認證失敗**：雙軌窗口太短或 consumer 沒實作 *latest version 失敗 fallback*、舊版 disable 後孤兒 consumer 直接斷 — 把雙軌窗口拉到 cache TTL × 2、補 fallback 邏輯
- **Data Access audit 沒紀錄**：預設關、要在 project IAM Audit Config 明確開 `secretmanager.googleapis.com` 的 DATA_READ — 不開等於沒辦法回答「事故當下誰讀了 secret」
- **External workload 拿不到 secret**：Workload Identity Federation 的 provider attribute mapping 沒對齊（GitHub OIDC token 的 `repository` claim 沒被 map 到 attribute condition）— 走 `gcloud iam workload-identity-pools providers describe` 看 mapping、用 token introspection 驗實際 claim
- **Secret version 累積過多**：rotation 只 disable 不 destroy、版本無限長 — 加 lifecycle policy（手動 / Cloud Function 排程）destroy 超過 N 個版本以前的舊版
- **GKE pod 用 Workload Identity 但拿不到 secret**：通常是 GKE 沒 enable Workload Identity feature、或 `iam.gke.io/gcp-service-account` annotation 拼錯、或 GCP service account 沒給 K8s ServiceAccount `iam.workloadIdentityUser` — 三層都要對才能通

## 何時改走其他服務

| 需求形狀                                 | 改走                                                                                                                 |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 跨雲 secret 統一介面                     | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)                                     |
| 需要 dynamic database / cloud credential | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) dynamic engine                      |
| 需要 built-in 四階段 rotation flow       | [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)（若可遷 AWS）               |
| Encryption-as-a-service / 內部 PKI       | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) transit / PKI engine                |
| FIPS 140-2 Level 3 HSM 需求              | [Cloud HSM](/backend/07-security-data-protection/vendors/google-cloud-kms/)（KMS 後端可改 HSM）                      |
| 公開憑證 PKI                             | Google Certificate Authority Service / [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/)    |
| K8s workload cert 自動化                 | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)                                           |
| Secret rotation 證據鏈                   | [7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/) |

## 不在本頁內的主題

- GSM 完整 REST API 跟 `gcloud secrets` 詳盡子命令
- Cloud KMS key lifecycle 跟 rotation 細節（看 [Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) 章）
- Workload Identity Federation 完整設定步驟（attribute mapping、condition expression、provider 設定看 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) 章）
- Berglas 完整 CLI 用法
- Cloud Function / Cloud Run 部署細節
- GCP Organization Policy 跟 secret 跨 project 共享的進階場景

## 案例回寫

GSM 在 07 案例庫沒有直接 vendor-level 事件、以下案例採對照引用：

| 案例                                                                                                                                                                   | 跟 GSM 的關係（對照）                                                                                                                                                                                                    |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                                    | GSM rotation 是自寫 Cloud Function、scope map 跟雙軌驗證窗口都要自己設計、不像 AWS Secrets Manager 有 built-in 四階段 flow — 設計時就要把 consumer scope 跟 cache TTL 算進 rotation 排程                                 |
| [Microsoft Storm-0558 Signing Key Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/)  | 對照啟示 — GSM CMEK 把 encryption key 放 [Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)、key 不離 KMS 邊界、跟 HSM-bound 同 mindset；secret admin 跟 KMS admin 分人是減 blast radius 的關鍵 |
| [Okta Cloudflare 2023 Support Supply Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/) | 對照啟示 — GSM 管的第三方 token（GitHub PAT / Slack token / SaaS API key）scope 過寬時、上游事件直接傳導下游、要走 IAM Conditions 收 caller scope 跟過期時間                                                             |

## 下一步路由

- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)、[Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)
- 下游：[Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)（GSM CMEK 後端、key custody 分離）
- 下游：[Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)（secret IAM binding、Workload Identity Federation 設定）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（GSM 事件如何 routing 進 IR 流程）
- 官方：[Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
