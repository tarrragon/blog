---
title: "資安與資料保護 Vendor 清單"
date: 2026-05-15
description: "規劃身份、秘密、金鑰、入口防護、供應鏈與偵測工具的服務頁撰寫順序與教學大綱"
weight: 90
tags: ["backend", "security", "data-protection", "vendor"]
---

資安與資料保護 Vendor 清單的核心責任是把安全服務名稱放回控制面、信任邊界、證據鏈與交接路由的判斷。每個服務頁先回答它承擔身份、秘密、傳輸、入口、資料保護、供應鏈或偵測哪一段控制責任，再討論導入條件、操作成本、例外治理與事故回寫。

## 讀法

資安服務要從控制問題進入。讀者如果要處理身份與授權，先回到 [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)；如果要處理秘密與機器憑證，先回到 [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)；如果要處理入口與伺服器暴露，先回到 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)。

## 教學順序同步

資安服務頁的教學順序是先建立 identity / IAM，再進入 secrets / KMS / PKI、edge、supply chain、detection / DLP。這個順序對齊 checkout E6：讀者先理解誰能做什麼、秘密與金鑰如何生命週期化，再比較入口防護、artifact trust、偵測訊號與資料控制如何接到 release gate、evidence package 與 incident handoff。

## T1 服務頁大綱

| 服務群             | 候選服務                                                                                                                                                                                                                                                                                                                                                                       | 頁面要回答的核心問題                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| Identity / IdP     | [Okta](/backend/07-security-data-protection/vendors/okta/)、[Auth0](/backend/07-security-data-protection/vendors/auth0/)、[Keycloak](/backend/07-security-data-protection/vendors/keycloak/)、[AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)                                                                                 | 人類身份、SSO、MFA、group、role 與 session 邊界如何治理                  |
| Cloud IAM          | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)、[Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)、[Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)                                                                                                                                                   | cloud resource 權限、policy、role assumption 與 least privilege 如何落地 |
| Secrets / Vault    | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)、[Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)                                                                                                       | secret storage、rotation、lease、audit 與 application delivery 如何治理  |
| KMS / HSM          | [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/)、[Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)、[Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)、[CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)                                                                     | key lifecycle、envelope encryption、rotation 與權限分離如何成立          |
| Edge / WAF         | [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)、[AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/)、[Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/)                                                                                                                                            | 入口防護、bot、rate limit、managed rule 與 false positive 如何取捨       |
| Certificate / PKI  | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)、[AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/)、[Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/)、[SPIRE](/backend/07-security-data-protection/vendors/spire/)                                                                                         | TLS、mTLS、workload identity 與憑證生命週期如何自動化                    |
| Supply chain       | [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/)、[Snyk](/backend/07-security-data-protection/vendors/snyk/)、[Dependabot](/backend/07-security-data-protection/vendors/dependabot/)、[Trivy](/backend/07-security-data-protection/vendors/trivy/)、[Syft / Grype](/backend/07-security-data-protection/vendors/syft-grype/) | SCA、container scan、SBOM、artifact trust 與 release gate 如何接軌       |
| SIEM / Detection   | [Splunk](/backend/07-security-data-protection/vendors/splunk/)、[Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)、[Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)、[Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)                                 | 偵測訊號、log pipeline、alert quality 與 incident handoff 如何治理       |
| DLP / Data control | [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/)、[Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)、[Cloud-native Data Policy (BigQuery + S3)](/backend/07-security-data-protection/vendors/cloud-data-policy/)                                                                                                      | 資料分類、遮罩、匯出、資料駐留與證據鏈如何落地                           |

## 內容覆蓋進度

每個 vendor 服務頁下會擴充兩類文章：deep article（vendor 自身的配置、故障、容量、走 [6-section 模板](/posts/vendor-deep-article-methodology/)）跟 migration playbook（跨 vendor 遷移流程、走 [6-type 結構](/posts/migration-playbook-methodology/)）。「→ X」代表遷移到 X 的 playbook。

| Vendor                              | Deep article                                               | Migration playbook                                                       |
| ----------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------ |
| [Cloudflare WAF](cloudflare-waf/)   | [page-shield-csp-sri](cloudflare-waf/page-shield-csp-sri/) | —                                                                        |
| [HashiCorp Vault](hashicorp-vault/) | [dynamic-credential](hashicorp-vault/dynamic-credential/)  | [→ AWS Secrets Manager](hashicorp-vault/migrate-to-aws-secrets-manager/) |
| [Splunk](splunk/)                   | [risk-based-alerting](splunk/risk-based-alerting/)         | [→ Elastic Security](splunk/migrate-to-elastic-security/)                |

本章節 vendor 服務頁覆蓋率高（51 個 vendor 服務頁、上方「T1 服務頁大綱」跟「後續候選」段已全部建立），但 deep article / migration playbook 還在早期階段。對應的 backlog 議題見上方「T1 服務頁大綱」段每個服務群要回答的核心問題、跟各 vendor `_index.md` 的「預計實作話題」段。

## 服務頁標準章節

| 章節               | 資安服務頁要補的內容                                                                    |
| ------------------ | --------------------------------------------------------------------------------------- |
| 服務定位           | 它是 identity、IAM、secret、KMS、WAF、PKI、supply chain、SIEM 還是 DLP                  |
| 本章目標           | 讀者能判斷控制面責任、信任邊界、證據需求、例外與事故交接                                |
| 最短判讀路徑       | 用「誰能做什麼、憑證在哪裡、入口如何暴露、證據是否可回查」快速定位                      |
| 日常操作與決策形狀 | onboarding、policy、rotation、rule update、exception、audit、handoff                    |
| 核心取捨表         | managed service、self-hosted control、cloud-native、SaaS security tool 的機會成本       |
| 進階主題           | federation、workload identity、mTLS、SBOM、DLP、multi-cloud policy                      |
| 排錯與失敗快速判讀 | over-permission、stale secret、broken rotation、WAF false positive、missing audit trail |
| 何時改走其他服務   | 觀測訊號回 04、release gate 回 06、入口部署回 05、事故處理回 08                         |
| 不在本頁內的主題   | 合規逐條法規解讀、完整 SOC 2 / HIPAA 流程、所有攻擊技術細節                             |
| 案例回寫           | 回到 7.C cases、7.B blue-team materials、8 incident write-back 連到對應 vendor 事件     |
| 下一步路由         | 上游 chapter（7.X）、平行 vendor、下游模組（04 / 05 / 06 / 08）的交接                   |

## 撰寫批次

| 批次 | 服務群                    | 撰寫目的                                                 | 狀態                                 |
| ---- | ------------------------- | -------------------------------------------------------- | ------------------------------------ |
| S1   | Identity / Cloud IAM      | 建立人類身份、機器身份、role / policy baseline           | **完成（2026-05-18、7 個 vendor）**  |
| S2   | Secrets / KMS / PKI       | 建立 secret、key、certificate lifecycle 與 rotation 判準 | **完成（2026-05-18、11 個 vendor）** |
| S3   | Edge / WAF / Supply chain | 建立入口防護、artifact trust 與 release gate 對照        | **完成（2026-05-18、8 個 vendor）**  |
| S4   | SIEM / Detection / DLP    | 建立偵測覆蓋、資料保護、證據鏈與事故 handoff             | **完成（2026-05-18、7 個 vendor）**  |

## 後續候選（C 批次完成）

| 類型              | 候選服務                                                                                                                                                                                                                                                                                                   | 寫作重點 / 狀態                                                                     |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| PAM / access      | [Teleport](/backend/07-security-data-protection/vendors/teleport/)、[Boundary](/backend/07-security-data-protection/vendors/boundary/)、[Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/)、[Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/) | 完成（C1、4 vendor）— 管理面 access、session audit、JIT                             |
| CSPM / CNAPP      | [Wiz](/backend/07-security-data-protection/vendors/wiz/)、[Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/)、[Lacework](/backend/07-security-data-protection/vendors/lacework/)、[CrowdStrike Falcon CS](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/)     | 完成（C2、4 vendor）— cloud posture、asset inventory、risk prioritization           |
| Policy as code    | [OPA](/backend/07-security-data-protection/vendors/opa/)、[Conftest](/backend/07-security-data-protection/vendors/conftest/)、[Kyverno](/backend/07-security-data-protection/vendors/kyverno/)、[Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/)                                     | 完成（C3、4 vendor）— admission control、policy review、exception workflow          |
| Runtime detection | [Falco](/backend/07-security-data-protection/vendors/falco/)、[Cilium Tetragon](/backend/07-security-data-protection/vendors/cilium-tetragon/)                                                                                                                                                             | 完成（C4、2 vendor）— syscall / runtime signal、container threat detection          |
| Secret scanning   | [GitGuardian](/backend/07-security-data-protection/vendors/gitguardian/)、[Gitleaks](/backend/07-security-data-protection/vendors/gitleaks/)                                                                                                                                                               | 完成（C4、2 vendor）— leaked secret detection、developer workflow、rotation trigger |
| Data security     | [Immuta](/backend/07-security-data-protection/vendors/immuta/)、[Privacera](/backend/07-security-data-protection/vendors/privacera/)、[Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)                                                                                 | 完成（C5 + S4、3 vendor）— data access policy、masking、lineage、governance         |

主流覆蓋檢查的重點是分開 preventive control、detective control 與 response handoff。IAM / KMS / WAF / policy-as-code 是 preventive control；SIEM / runtime detection / secret scanning 是 detective control；PAM、incident channel 與 evidence write-back 連到 08 的 response handoff。

## Reading paths（51 個 vendor 的進入順序建議）

讀完 51 個 vendor 不是線性目的、是 *依組織當前的安全成熟度跳讀*。以下是四條常見路徑：

**Path A — Startup baseline（< 50 人、cloud-native）**：
[Okta](/backend/07-security-data-protection/vendors/okta/) → [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) → [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) / [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) → [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) → [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/) → [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)。共 7-8 個 vendor、預算敏感、cloud-native、SaaS 優先。

**Path B — Enterprise multi-cloud（500+ 人、跨雲）**：
[Okta](/backend/07-security-data-protection/vendors/okta/) + [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) → 各雲 IAM（[AWS](/backend/07-security-data-protection/vendors/aws-iam/) / [GCP](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [Azure](/backend/07-security-data-protection/vendors/azure-rbac/)）→ [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) + [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/) → [SPIRE](/backend/07-security-data-protection/vendors/spire/) + [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) → [Fastly NG-WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/) → [Snyk](/backend/07-security-data-protection/vendors/snyk/) + [Trivy](/backend/07-security-data-protection/vendors/trivy/) → [Splunk](/backend/07-security-data-protection/vendors/splunk/) → [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) + [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)。

**Path C — Compliance-heavy（金融 / 醫療 / 政府）**：
[Keycloak](/backend/07-security-data-protection/vendors/keycloak/)（資料主權）→ [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) + [CloudHSM](/backend/07-security-data-protection/vendors/cloudhsm/)（FIPS 140-2 L3）→ [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) + [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) → [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) + [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) → [Cloud-native data policy](/backend/07-security-data-protection/vendors/cloud-data-policy/) → [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)（Mandiant + 大規模）。

**Path D — 事故驅動補洞**：先讀 [7.C 案例](/backend/07-security-data-protection/cases/) + [紅隊案例](/backend/07-security-data-protection/red-team/cases/) 對應自家事故、再回 vendor 頁找控制面缺口。例如 helpdesk social engineering 失效 → [Okta](/backend/07-security-data-protection/vendors/okta/) callback workflow + [Splunk](/backend/07-security-data-protection/vendors/splunk/) anomaly detection；signing key 失控 → [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) / [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/) HSM-bound key + [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) cross-tenant token forging detection。

## Cross-category 整合 stack

實務 stack 通常跨多個類別組合、不是單一 vendor。下表列三個典型 stack：

| Stack 場景                  | Identity                                                                                                                                                            | Cloud IAM      | Secrets / KMS                                                                                                                                               | WAF + Supply chain                                                                                                                                           | SIEM + DLP                                                                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS-only SaaS               | [AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/) → [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) | AWS IAM        | [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) + [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) | [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/) + [GHAS](/backend/07-security-data-protection/vendors/github-advanced-security/)            | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) |
| Multi-cloud + on-prem       | [Okta](/backend/07-security-data-protection/vendors/okta/)（人類）+ [SPIRE](/backend/07-security-data-protection/vendors/spire/)（workload）                        | 三家 cloud IAM | [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（跨雲統一）                                                                          | [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) + [Snyk](/backend/07-security-data-protection/vendors/snyk/)                  | [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)（OSS-friendly）                                                  |
| Microsoft 365 + Azure heavy | [Entra ID](/backend/07-security-data-protection/vendors/azure-rbac/)                                                                                                | Azure RBAC     | [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)                                                                            | [Fastly NG-WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/) + [GHAS](/backend/07-security-data-protection/vendors/github-advanced-security/) | [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) + Sentinel                                                     |

Stack 不是一次到位、按 [Path A → B → C](#reading-paths33-個-vendor-的進入順序建議) 的成熟度演進加 vendor。每加一個 vendor 都要對應一個 *已被 case 庫驗證* 的失效模式 — 不是「業界都用」就上。

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)
- 上游：[7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 案例：[7.C 資安案例正文](/backend/07-security-data-protection/cases/)
- 服務路徑：[7.27 Credential Rotation with Scoped Evidence 實作示範](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)
