---
title: "Google Cloud IAM"
date: 2026-05-18
description: "GCP cloud resource permission engine、Role Binding / Service Account / Workload Identity Federation、resource hierarchy 為核心的權限治理"
weight: 6
tags: ["backend", "security", "vendor", "google-cloud-iam", "gcp", "iam", "cloud-iam"]
---

Google Cloud IAM 是 GCP 的 cloud resource permission engine、把 *誰能對哪個 resource 做什麼* 統一成一個模型：Principal + Role + Resource scope 三件事拼成一個 *role binding*。它跟 [Okta](/backend/07-security-data-protection/vendors/okta/) 等 IdP 是兩層責任 — Okta 回答「這個人是誰」、Google IAM 回答「這個身份能對 GCP resource 做什麼」。設計上比 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) 統一、沒有 resource-based policy vs identity-based policy 雙軌、也沒有 SCP / Permission Boundary 多層覆蓋、policy 評估路徑短而可預測。

## 服務定位

Google Cloud IAM 的核心抽象是 *role binding on a resource scope*：把 role grant 給 principal、生效範圍是某個 Organization / Folder / Project / 個別 resource、沿 resource hierarchy 向下繼承。同一個 principal 在不同 scope 可以有不同 role、有效權限是所有 binding 的 union。這跟 AWS IAM 的「identity policy + resource policy + SCP + boundary 多層 intersect / union」相比、推理成本低、但也意味著 *guardrail 必須走 Organization Policy 這另一個系統* — 不是 IAM grant 的一部分。

跟 Azure RBAC 相比、兩者都是 scope-based、都靠 hierarchy 繼承。差異在 *Service Account 是 GCP 的 first-class identity*：有自己的 email、可被 impersonate、可以 grant role 給它也可以 grant `iam.serviceAccountUser` 讓人類 act-as 它。Azure 的對應是 Managed Identity、語義接近但 impersonation chain 的表達更隱晦。選 GCP（= 用 Google Cloud IAM）的核心訴求通常是：BigQuery / Vertex AI / GKE workload、想用 Workload Identity Federation 取代 long-lived key、團隊偏好較統一的 policy 模型。

## 本章目標

讀完本頁、讀者能判斷：

1. Google Cloud IAM 該承擔哪一段權限（resource access、service-to-service、cross-cloud federation）、哪一段該交給 [Okta](/backend/07-security-data-protection/vendors/okta/) / IdP
2. Role 的選擇順序（Predefined > Custom > Basic）與 IAM Conditions 何時補上
3. Service Account / Workload Identity Federation 的信任邊界、何時不該再發 service account key
4. 何時改走 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/) / Organization Policy / VPC Service Controls

## 最短判讀路徑

判斷一個 GCP project 的 IAM 配置是否健康、最少看五件事：

- **Principal 級別**：誰是 Owner / Editor / Viewer（Basic Role 應該幾乎為空）、Service Account 是否獨立列管、有沒有 user 直接 grant 沒走 group
- **Role 種類**：Predefined Role 是 baseline、Custom Role 收斂 least privilege、Basic Role 視為待修；user-managed Service Account key 是否存在（理想是 0）
- **Impersonation chain 展平稽核**：誰有 `iam.serviceAccountTokenCreator` / `iam.serviceAccountUser` 對哪個 SA、間接 chain（A → B → C）展平後 *誰最終能 act as 高權限 SA*。這是 GCP IAM 最容易漏稽核的一條 — 直接 binding 看 Role、但 lateral movement 走 impersonation chain
- **IAM Conditions**：高敏 resource（prod bucket、KMS key、BigQuery dataset）是否用 condition expression 補 attribute-level 限制（resource name prefix、request time、IP）
- **Audit Logs**：Admin Activity 預設開、Data Access logs 在 sensitive resource 是否手動開、System Log 是否同步到 SIEM 並 alert role 變更與 service account key 建立

五件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 [Authorization](/backend/knowledge-cards/authorization/) 邊界的待補項目。

## 日常操作與決策形狀

**Role 選擇順序**：Predefined Role 是 baseline、覆蓋 80% 場景；Custom Role 用於收斂 least privilege（例如只給 `bigquery.dataViewer` 的特定子集）；Basic Role（Owner / Editor / Viewer）幾乎不該再用 — Editor 預設帶寫權限到幾乎所有資源類型、Owner 還能改 IAM policy 本身、粒度過粗。Project 建立預設給的 Owner role 是 *人類自己 grant 自己*、不是無法避免的 baseline。

**Principal type**：人類用 Google Workspace user / external user，群組走 Google Group（grant 給 group 比 grant 給 user 更穩、離職 lifecycle 由 IdP / HRIS 推 group 變更即可）。Service Account 是 *第一級身份*、跟 user 同等、有自己的 email（`name@project.iam.gserviceaccount.com`）、可被 grant role 也可被 impersonate。Workload identity（K8s SA、外部 OIDC subject）是 federation 層、不在 IAM 內直接列管、但 *最後仍 impersonate 一個 Service Account 來拿 GCP 權限*。

**IAM Conditions**：在 role binding 上加 attribute-based 條件、補純 RBAC 不足。常見 expression：`resource.name.startsWith("projects/_/buckets/prod-")`、`request.time < timestamp("2026-12-31T00:00:00Z")`、`resource.type == "storage.googleapis.com/Bucket"`。適合 *temporary access*、*resource name 範圍限定*、*環境隔離*；不適合複雜 ABAC 規則（會難以稽核、且 condition 只能用在支援的 resource type 上）。

**Service Account impersonation**：人類或另一個 Service Account 透過 `iam.serviceAccountTokenCreator` role 借用目標 SA 的權限、不需要 SA key。impersonation chain 可以串（A 可 impersonate B、B 可 impersonate C）— 這條鏈是 lateral movement 風險、稽核時要展平看 *誰最終能 act as 高權限 SA*。對應 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) 的教訓：rotation 沒分域時、單點 SA compromise 會跨環境擴散。

**Workload Identity Federation（WIF）**：GCP 接受外部 OIDC / SAML issuer（GitHub Actions、AWS、Azure、自管 K8s OIDC、CircleCI 等）發的 token、在 Workload Identity Pool 設 attribute mapping 後、外部 token 換成 short-lived GCP credential、最後 impersonate 指定 Service Account。是 *取代 SA JSON key 的 modern best practice*、CI / 跨雲 / 邊緣 workload 都該優先用。Trust 條件要鎖 *issuer + audience + subject*（例：`assertion.repository == "myorg/myrepo"`）— 缺一個就可能被同 issuer 下其他 subject 借用，這是 [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) 對 external OIDC 信任的提醒：發 token 的 issuer 一旦被攻破、所有信任它的 audience 都跟著受害。

**Service Account key（避免）**：user-managed JSON key 是 long-lived credential、無 TTL、無 IP 限制、外洩偵測難。應該以 Workload Identity Federation 或 Service Account Impersonation 取代；若必須用、走 Organization Policy `iam.disableServiceAccountKeyCreation` 預設禁用、例外申請走 ticket、key 進 [Secret Management](/backend/knowledge-cards/secret-management/)、季度盤點未使用 key 刪除。

**Organization Policy（guardrail）**：跟 IAM 完全不同層 — 不是 grant、是 *限制可以做什麼設定*。常用 constraint：`iam.disableServiceAccountKeyCreation`、`iam.allowedPolicyMemberDomains`（限制只能 grant 給特定 domain 的 principal）、`compute.vmExternalIpAccess`（限制 VM external IP）、`storage.publicAccessPrevention`。Org Policy 在 Organization / Folder / Project 層設定、IAM 即使想 grant 也擋得住。

**Audit / handoff**：Admin Activity Log 預設開、不能關、保留 400 天免費；Data Access Log 預設關、開了會大量 log（也大量計費）— 對 sensitive resource（KMS key access、BigQuery dataset read、Secret Manager access）應該手動開；System Event Log 補基礎設施事件。三類都接 Cloud Logging sink 推到 SIEM、特別 alert 三件事 — IAM policy 變更、Service Account key 建立 / 上傳、Workload Identity Pool / Provider 變更。

## 核心取捨表

| 取捨維度               | Google Cloud IAM                            | AWS IAM                                            | Azure RBAC                                      |
| ---------------------- | ------------------------------------------- | -------------------------------------------------- | ----------------------------------------------- |
| Policy 模型            | Role binding on resource scope、單軌        | Identity policy + resource policy + SCP + boundary | Scope-based、Management Group 階層              |
| 表達力                 | 中等、IAM Conditions 補 attribute           | 最高、policy language 表達 ABAC / 條件 / 否決      | 中等、Azure Policy 補 ABAC                      |
| Guardrail 機制         | Organization Policy（獨立系統、constraint） | SCP（policy 同語法、separate plane）               | Azure Policy（獨立系統、constraint）            |
| Machine identity       | Service Account first-class + WIF           | IAM Role + STS AssumeRole + OIDC trust             | Managed Identity + Workload Identity Federation |
| Cross-cloud federation | WIF 接外部 OIDC 是 modern best practice     | OIDC trust on IAM Role、表達力強                   | Federated credentials、近年補齊                 |
| 學習曲線               | 較緩、模型統一                              | 陡、policy 評估順序複雜                            | 中等、scope inheritance 直覺                    |
| 推理 / 稽核成本        | 低 — binding union、Org Policy 獨立看       | 高 — 多層 intersect / union、需 policy simulator   | 中 — scope 繼承明確、policy 分散                |

選 Google Cloud IAM 的核心訴求：*已在 GCP 上、或想用 BigQuery / Vertex AI / GKE*、團隊偏好較統一的 policy 模型、跨雲場景靠 WIF 對外發 trust 而不維護多套 key。

## 進階主題

**Workload Identity Federation 的深層應用**：除了 GitHub Actions、AWS、Azure 這類常見 issuer、WIF 也支援自管 K8s OIDC issuer（OSS K8s cluster 跑 GKE workload identity 等價物）、SaaS（Snowflake、Terraform Cloud）發的 OIDC token。trust 設定要鎖 issuer URL、audience、subject pattern 三件事 — 任何一個太寬都是同 issuer 下別人借用你 SA 的入口。

**Organization Policy 的 dry-run / 例外**：constraint 可以先設 `dryRun` 觀察會擋掉哪些操作再 enforce；例外用 *exception folder*（特定 folder 不繼承上層 constraint）或 *condition*（特定 resource pattern 不擋）。直接全 org 一次 enforce 通常會打掉既有 workload、要分階段。

**IAM Conditions 的有限性**：condition 只能用在支援的 resource type 上、不是全 GCP 通用；複雜 expression 難稽核（CEL 語法、不易讀）；condition 不能否決 — 只能限制 binding 的生效範圍、不能像 AWS policy 那樣寫 `Deny`。複雜 ABAC 場景該走 Organization Policy + 應用層授權邊界、不是把所有規則塞進 IAM Conditions。

**Service Account Impersonation chain 的稽核**：列出 *有 `serviceAccountTokenCreator` 的 principal* 是基本；展平 chain（A → B → C）需要 graph walk 工具或 Policy Analyzer；高權限 SA（owner-equivalent custom role、跨 project 寫權限）的 impersonation 來源應該是 *寫死的少數 admin SA + break-glass*、不該開放給 CI / 一般 service。

**VPC Service Controls（資料邊界、跟 IAM 互補）**：在 IAM 之外加 *資料 perimeter* — 即使 principal 有 IAM 權限、如果請求不是來自 perimeter 內（VPC、特定 IP、特定 service account），仍然會被擋。適合 BigQuery / GCS / Secret Manager 這類存資料的 service、防 *合法 credential 從外部 exfiltrate 資料*（[Azure AD Identity Control Plane 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/) 場景的下游補位：identity 控制面失守時、資料層仍有獨立 perimeter）。

## 排錯與失敗快速判讀

- **Basic Role 還在用**：Project Owner / Editor 散落、新人 onboard 直接 Editor — 改 group + Predefined Role、Basic Role 改成 break-glass 限定
- **Service Account key 散落**：CI 用 JSON key、key 進 git 或環境變數、無 rotation — 改 WIF（GitHub Actions / GitLab CI 都支援）、Org Policy 禁用 SA key 建立
- **WIF trust 太寬**：只鎖 issuer 沒鎖 subject、同 GitHub org 任何 repo 都能借用 SA — trust 要含 `assertion.repository`、`assertion.ref`（main branch only）等 condition
- **IAM Conditions 越寫越多**：condition expression 過度複雜、稽核時沒人讀得懂 — 簡化條件、把複雜規則上移到應用層或 Org Policy
- **Data Access Logs 沒開**：sensitive resource 出事時只有 Admin Activity、看不到 *誰讀了什麼* — KMS key、Secret Manager、BigQuery 高敏 dataset 必開 Data Access Log
- **Impersonation chain 失控**：太多人有 `serviceAccountTokenCreator` 到高權限 SA — 用 Policy Analyzer 展平、收斂到必要 admin + break-glass
- **Org Policy 沒設**：root org 沒有 baseline constraint、新建 project 預設可建 SA key / public IP / public bucket — 至少設 `disableServiceAccountKeyCreation` + `publicAccessPrevention` + `allowedPolicyMemberDomains`

## 何時改走其他服務

| 需求形狀                                    | 改走                                                                                                          |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 人類身份的 SSO / MFA / lifecycle            | [Okta](/backend/07-security-data-protection/vendors/okta/) / IdP                                              |
| AWS resource permission                     | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)                                              |
| Azure resource permission                   | [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)                                        |
| 跨雲 unified IAM                            | 沒有單一答案 — 各雲 IAM + Workload Identity Federation 對接、或外部 PAM（Teleport / Boundary）                |
| Secret / Service Account key 治理           | [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) |
| 資料分類 / DLP / 匯出控制                   | [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)        |
| Workload runtime detection（容器、syscall） | 04 + Falco / Cilium Tetragon 類工具                                                                           |

## 不在本頁內的主題

- 各 Predefined Role 的完整權限清單與細部 permission 差異
- IAM Conditions CEL 語法的完整 spec
- Workload Identity Federation 跟特定 issuer（GitHub / AWS / Azure）的逐步設定教學
- BigQuery / GCS / KMS 等服務的 service-specific IAM 行為細節
- GCP 計費 / SKU 對 Audit Log 開關的影響

## 案例回寫

| 案例                                                                                                                                                       | 跟 Google Cloud IAM 的關係                                                                                                                               |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Azure AD Identity Control Plane 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)                                   | Identity 控制面故障不直接打到 Google IAM、但設計啟示是 IAM evaluation 路徑必須 HA、且 VPC Service Controls 等資料 perimeter 是 identity 失守時的下游補位 |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                        | Service Account key、WIF provider 的 rotation 必須分域 — 跨 project / 跨環境的 SA 共用是 blast radius 放大器                                             |
| [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | 對 WIF 的提醒 — 信任 external OIDC issuer 時、issuer 自己被攻破會打到所有 audience；trust condition 必須鎖 issuer + audience + subject 三件事            |

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)
- 平行：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)、[Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)、[Okta](/backend/07-security-data-protection/vendors/okta/)、[AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)
- 下游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)（Google Secret Manager / Google Cloud KMS 個別 vendor 頁 S2 批次撰寫中）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（GCP IAM 事件如何 routing 進 IR 流程）
- 官方：[Google Cloud IAM Documentation](https://cloud.google.com/iam/docs)
