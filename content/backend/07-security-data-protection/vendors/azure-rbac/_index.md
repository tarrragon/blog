---
title: "Azure RBAC + Entra ID"
date: 2026-05-18
description: "Azure 雙層身份/權限體系、Entra ID（IdP）+ Azure RBAC（resource permission）、Conditional Access、PIM、Managed Identity"
weight: 7
tags: ["backend", "security", "vendor", "azure-rbac", "entra-id", "azure", "iam", "cloud-iam", "identity"]
---

Azure 的身份與權限體系是 *雙層* — Entra ID（前 Azure AD）是 IdP，承擔人類與 workload 的身份來源、SSO、MFA 與 Conditional Access；Azure RBAC 是 cloud resource 的 permission engine，把 role 指派到 scope（Management Group / Subscription / Resource Group / Resource）上的 principal。兩層責任不同、設定介面不同、出事故時的徵兆也不同 — 把兩者寫成同一件事是 Azure 治理最常見的混淆來源。

## 服務定位

Entra ID 是 *Microsoft 自有的 workforce IdP*、跟 [Okta](/backend/07-security-data-protection/vendors/okta/) 是直接競爭者。M365 / Azure-heavy 的組織通常直接用 Entra ID 當主 IdP；Okta-first 的組織可以把 Entra ID 當下游 SP（federation）、也可以雙 IdP 並存、但雙 IdP 的 break-glass 跟 lifecycle 路徑要重新設計。Entra ID 同時承擔 *consumer-side 跟 partner-side 的 multi-tenant app* 信任、跟 [Auth0](/backend/07-security-data-protection/vendors/auth0/) 在 B2C 場景有交集。

Azure RBAC 是 cloud resource permission engine、跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) 同層 — 都在解「身份對 cloud resource 能做什麼」。差異在 *scope hierarchy* — Azure 用 Management Group → Subscription → Resource Group → Resource 四層繼承、AWS 用 account + organization、Google 用 organization → folder → project。Azure RBAC 預期 *role assignment 沿 scope 向下繼承*、這跟 AWS 在每個 account 重新指派的習慣不一樣、跨雲團隊轉過來常踩到。

## 本章目標

讀完本頁、讀者能判斷：

1. 哪一段控制屬於 Entra ID（身份）、哪一段屬於 Azure RBAC（resource permission）、不要把兩層當同一件事
2. Entra ID tenant 的最低稽核需求（Global Admin、App Registration、Conditional Access、Managed Identity）
3. Azure RBAC 的 scope 設計、Custom Role 跟 PIM 何時必要
4. Entra ID 控制面事故的降級路徑、跟 Azure RBAC 出事的徵兆差異

## 最短判讀路徑

判斷 Azure 雙層體系是否健康、要分兩層各看兩件事、跟「日常操作與決策形狀」段的兩層結構對齊。

**Entra ID 層**（身份控制面）：

- **誰能做什麼**：Global Admin / Privileged Role Administrator 的人數、是否走 [PIM](#進階主題) just-in-time、Conditional Access 是否強制 [phishing-resistant 認證](/backend/knowledge-cards/authentication/)、break-glass 帳號是否 *exclude* 自所有 CA policy 又單獨監控
- **入口如何暴露**：App Registration 是否限定 single-tenant、multi-tenant app 的 admin consent 流程是否經審查、Managed Identity 是否取代 service principal client secret

**Azure RBAC 層**（resource permission）：

- **誰能對 resource 做什麼**：Owner / Contributor 在哪個 scope（Management Group 還是 Subscription）、production 環境是否用 Custom Role 收緊權限、有沒有 standing assignment 該改 PIM
- **證據是否可回查**：Entra ID Sign-in Log / Audit Log 是否同步到 SIEM、Azure Activity Log 是否設保留與 alert、admin consent / role assignment 變更是否觸發 [alert runbook](/backend/knowledge-cards/alert-runbook/)

兩層任一邊任一條缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 [Authorization](/backend/knowledge-cards/authorization/) 邊界的待補項目。

## 日常操作與決策形狀

### Entra ID 層

**User / Group / lifecycle**：HRIS 推 SCIM 進 Entra ID、Entra ID 同步到下游 SaaS 跟 Azure RBAC group。決策點是 *source of truth* — 多數組織把 HRIS 設為人員來源、Entra ID 當分發層、避免雙寫造成 stale account。

**Conditional Access 是 MFA *主要強制機制***：MFA 不是設在 user 屬性上、是 Conditional Access policy 在登入時判斷 user / device / location / app / risk 後觸發。常見設定錯誤包含 *exclude legacy auth 沒做、break-glass 規則太寬、emergency access 帳號沒獨立監控*。Conditional Access 規則設計錯、就是高權限 bypass 的入口。

**App Registration vs Enterprise Application**：開發者註冊 multi-tenant app 走 *App Registration*（app 的定義）、組織 admin 為某 app 設定 SAML SSO / admin consent 走 *Enterprise Application*（該 tenant 對 app 的信任）。兩者常被混講、但安全意義不同 — App Registration 是「我們做了一個 app」、Enterprise Application 是「我們信任這個 app 用我們的身份」。Consent phishing 攻擊就是針對後者。

**Managed Identity**：Azure resource（VM、Function、AKS pod）自帶身份、不需要 service principal client secret、跟 [Google Workload Identity Federation](/backend/07-security-data-protection/vendors/google-cloud-iam/) 同概念但 Azure-internal。System-assigned 跟 resource 生命週期綁定、resource 刪掉 identity 跟著刪；User-assigned 獨立、可跨 resource 共用。production 環境的服務存取 Key Vault / Storage 應走 Managed Identity、不該用 client secret。

**Workload Identity Federation**：Entra ID 可以 *trust 外部 OIDC issuer*（GitHub Actions、AWS、Google）、讓外部 workload 直接拿 Entra ID token、不用儲存 client secret。CI/CD 的 OIDC 整合是這層的主用例、比把 client secret 塞進 CI variable 安全很多。

**Signing key 是 control plane 託管**：Entra ID 不暴露 signing key、客戶沒有 rotate 它的能力。這層信任邊界一旦失守、客戶側 *直接修不了*、要等供應商發 patch 或公告 — Storm-0558 揭示了這條依賴的代價。客戶側能做的補強是 *下游檢查* 而非 *上游修復*：

- 訂閱 Microsoft Security Advisory（MSRC）+ tenant-specific notification、讓事件公告第一時間進 IR pipeline、不要靠新聞才知道
- SIEM alert *anomalous token issuance pattern*（跨租戶 token 在 Exchange / Graph API 出現異常存取序列）、不能只信 token signature valid
- 高敏 app 的 token validation 不只看 Entra ID 標準驗證、加 *issuer + tenant + audience + nonce* 多層比對、攻擊者偽造跨租戶 token 時可能漏掉某層
- Conditional Access 配 *token protection*（token binding to device）、降低 stolen token replay 的命中率
- IR playbook 預設 *signing key 事件* 一條 — 一旦供應商公告、強制 sign-out 高權限 user、token TTL 收短、回頭看 90 天 sign-in log 找異常

### Azure RBAC 層

**Scope 設計**：role assignment 沿 Management Group → Subscription → Resource Group → Resource 向下繼承。在 Management Group 給 Contributor、底下所有 subscription / RG / resource 都繼承 — 這既是優點（統一治理）也是風險（誤指派擴散範圍大）。設計原則是 *指派盡量低、不要對全 Management Group 給 Contributor*。

**Built-in role vs Custom Role**：Owner（含 user access admin）/ Contributor（不含權限管理）/ Reader 是 built-in、通常太粗。production 環境需要 Custom Role 把 `Microsoft.Storage/storageAccounts/listKeys/action` 之類的高風險 action 收掉、只留 read。Custom Role 是 [least privilege](/backend/knowledge-cards/authorization/) 在 Azure 的落實工具、不做就是用 Contributor 當預設、權限過寬。

**Privileged Identity Management（PIM）**：高權限角色（Global Admin、Subscription Owner、User Access Administrator）應走 just-in-time activation、需要 MFA 跟 approval、不該 permanent assignment。沒上 PIM 的組織通常會發現 *standing Global Admin 超過 10 個*、那是 phishing / token theft 的高價值靶。

**Service principal vs Managed Identity**：service principal 是 app 在 Entra ID 的代表、可以用 client secret 或 certificate 認證；Managed Identity 是 service principal 的特殊形式、由 Azure 自動管 credential。能用 Managed Identity 就不用 service principal client secret — 後者要自己 rotate、要存 [secret management](/backend/knowledge-cards/secret-management/)、容易 stale。

**Azure Policy 是 RBAC 的補位**：RBAC 管 *principal 能不能對 resource 做這個 action*、Azure Policy 管 *允不允許這樣設定 resource*（例如 storage account 強制加密、VM 只能用認可的 image）。RBAC 給 Contributor 的人可以建 storage account、但 Azure Policy 可以拒絕未加密的 storage account 建立 — 兩層互補、缺一不可。

## 核心取捨表

Azure 雙層體系的取捨要分開看 — 一張表回答 *cloud resource permission 該選哪家*（Azure RBAC vs AWS IAM vs Google IAM）、一張表回答 *workforce IdP 該選哪家*（Entra ID vs Okta）。兩個決策獨立、可以混搭（例如：Okta 當 workforce IdP + federate 到 Entra ID + 走 Azure RBAC 管 Azure resource）。

### Azure RBAC vs AWS IAM vs Google Cloud IAM

| 維度     | Azure RBAC                                      | AWS IAM                                        | Google Cloud IAM                    |
| -------- | ----------------------------------------------- | ---------------------------------------------- | ----------------------------------- |
| Scope    | Management Group → Subscription → RG → Resource | Account + Organization、policy attach          | Organization → Folder → Project     |
| 繼承模型 | scope 向下繼承                                  | account boundary 強、跨 account 用 assume role | scope 向下繼承、condition 強        |
| 自訂角色 | Custom Role（JSON）                             | Custom managed policy（JSON）                  | Custom Role（YAML / API）           |
| JIT 機制 | Privileged Identity Management（PIM）內建       | 無原生 JIT、要靠 IAM Identity Center / 第三方  | 無原生 JIT、要靠 third-party / 自建 |
| Workload | Managed Identity（內部）+ Workload Identity Fed | IAM role + OIDC trust                          | Workload Identity Federation        |
| 適合場景 | Azure-heavy、M365 整合                          | AWS-heavy、account isolation 模型成熟          | GCP-heavy、resource hierarchy 治理  |

### Entra ID vs Okta（workforce IdP）

| 維度       | Entra ID                                           | Okta                                            |
| ---------- | -------------------------------------------------- | ----------------------------------------------- |
| 主場       | M365 / Azure 原生、跟 RBAC 共生                    | 多雲 + SaaS、跨平台 SSO                         |
| MFA 機制   | Conditional Access 觸發、Authenticator app / FIDO2 | Sign-On / Authentication Policy、多 factor 選擇 |
| Lifecycle  | SCIM + cross-tenant sync                           | SCIM + Lifecycle Management、整合更廣           |
| Workload   | Managed Identity / Workload Identity Federation    | 較弱、CI 通常 federate 到雲 IAM                 |
| 整合廣度   | M365 / Azure / Office app 深、外部 SaaS 比 Okta 少 | 7000+ SaaS app 預建                             |
| 第三方風險 | Microsoft 控制面（Storm-0558、Midnight Blizzard）  | Okta 控制面（2022 / 2023 多起）                 |

選 Entra ID 的核心訴求：*M365 / Azure 重度使用、要跟 RBAC + Managed Identity 直接整合、能接受 Microsoft 控制面風險*；選 Okta 的核心訴求看 [Okta vendor 頁](/backend/07-security-data-protection/vendors/okta/)。

## 進階主題

**Conditional Access 進階規則**：除了 user / device / location 基本條件、進階場景包含 *risk-based*（Identity Protection 給的 user risk / sign-in risk）、*token protection*（token binding 到 device、防止 token replay）、*authentication strength*（強制 phishing-resistant factor）。production tenant 至少要有「Global Admin 必須走 phishing-resistant + compliant device」這條規則。

**Privileged Identity Management（PIM）的設計細節**：activation 要求 MFA、approval（高權限角色）、justification、時限（預設 8 小時、最長 24）。Access Review 是 PIM 的配套 — 季度檢視 standing assignment 是否還需要、不需要的撤掉。沒做 Access Review 的 PIM 等於只把問題從 standing 推到 *誰申請就給* — 不是 least privilege。

**Workload Identity Federation 跨雲**：Entra ID 可以 trust GitHub Actions / GitLab / AWS / Google 的 OIDC issuer、讓 CI 直接拿 Azure token。同向也成立 — Azure workload 可以拿 Google ID token federate 進 GCP。多雲 CI 不該存任何 client secret、走 federation 比較安全。

**Custom Role 設計實務**：用 `Microsoft.Authorization/roleDefinitions` API 或 portal 定義、`actions` / `notActions` / `dataActions` 各自獨立 — `actions` 是 control plane、`dataActions` 是 data plane（讀寫 blob、key vault secret 內容）。常見錯誤是只收 `actions` 沒收 `dataActions`、結果 storage account 設定改不了但 blob 內容隨便讀。

**Azure Policy 跟 Initiative**：Policy 是單一規則、Initiative 是 policy 的集合（用來組 baseline、例如 CIS、ISO 27001）。Policy effect 有 audit / deny / deployIfNotExists、後者可以自動補洞（例如自動加 diagnostic setting）。RBAC + Policy 一起設計才是完整的 [Authorization](/backend/knowledge-cards/authorization/) 邊界。

## 排錯與失敗快速判讀

- **Global Admin 過多**：standing Global Admin 超過 5 個就要警惕 — 上 PIM、把日常運維改用 Privileged Role Administrator + 特定 admin role group
- **Conditional Access 規則漏 legacy auth**：規則只 cover modern auth、IMAP / POP / SMTP 等 legacy protocol 不走 CA — 用「Block legacy authentication」baseline policy 補
- **App Registration / Enterprise Application admin consent 沒審查**：使用者自己 consent 把 mail.read 給三方 app、變 consent phishing 入口 — 關閉 user consent、改 admin consent workflow
- **Service principal client secret 散落**：CI / 服務裡有大量 client secret、rotate 沒節奏 — 改 Managed Identity（內部）或 Workload Identity Federation（跨雲 CI）
- **Subscription Owner 太多**：subscription 級 Owner 是高風險、應該收到 Management Group 級 Reader + 必要時 PIM activate Owner
- **Azure Activity Log 沒進 SIEM**：role assignment 變更、Key Vault access policy 變更只在 Azure portal 看得到、沒 alert — 用 Diagnostic Setting 推 Event Hub / Log Analytics、再進 SIEM
- **Break-glass 帳號 exclude 自所有 CA policy、但沒監控**：emergency access 帳號不能被 CA 鎖、但 *任何登入都該 alert* — 配對 Sign-in Log alert + 季度驗證可用

## 何時改走其他服務

| 需求形狀                       | 改走                                                                                                                                                     |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS-only 環境                  | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)                                                                                         |
| GCP-only 環境                  | [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)                                                                       |
| 多雲 + 大量 SaaS、IdP 中心化   | [Okta](/backend/07-security-data-protection/vendors/okta/)                                                                                               |
| Customer / B2C identity        | [Auth0](/backend/07-security-data-protection/vendors/auth0/)                                                                                             |
| 自管 IdP / 不接受 SaaS         | [Keycloak](/backend/07-security-data-protection/vendors/keycloak/)                                                                                       |
| Secret / Key 管理              | [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)（Azure Key Vault vendor 頁 S2 批次撰寫中） |
| 偵測訊號（不只 Entra ID 內部） | 07 SIEM 章節、04 observability                                                                                                                           |

## 不在本頁內的主題

- Entra ID 完整 SAML / OIDC / SCIM 規格細節
- Azure RBAC built-in role 完整清單與 action 對照
- Conditional Access policy template 細節
- Azure Policy 內建 initiative 完整清單
- Microsoft 365 / Defender for Identity 等周邊產品

## 案例回寫

| 案例                                                                                                                                                                  | 跟 Entra ID / Azure RBAC 的關係                                                                                                                                                   |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Azure AD Identity Control Plane 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)                                              | Entra ID 控制面故障外溢到 Teams / SharePoint / Exchange、業務必須有降級與切換策略、不能完全依賴單一 IdP 可用性                                                                    |
| [Microsoft Storm-0558 Signing Key 2023](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/)                                            | signing key 治理失效會跨租戶影響 token 驗證信任、客戶側只能等供應商修復（MSRC / CSRB 公開報告補充了 crash dump / Exchange Online 等具體外洩路徑、屬 case 檔之外的歷史 reference） |
| [Microsoft Storm-0558 Signing Key Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | [HSM](/backend/knowledge-cards/hsm/)-bound key 是 control plane 必要前提、跨租戶 token 異常要立即升級、不能等供應商先公告                                                         |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                                   | Entra ID app secret 跟 Managed Identity 的 rotation 分域、不該把 service principal client secret 跟 user password 混在同一個 rotation policy                                      |

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)、[Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)、[Okta](/backend/07-security-data-protection/vendors/okta/)
- 下游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)（Entra ID / Managed Identity 之後的 secret / key 層、Azure Key Vendor 個別 vendor 頁 S2 批次撰寫中）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Entra ID / Azure 事件如何 routing 進 IR 流程）
- 官方：[Microsoft Entra Documentation](https://learn.microsoft.com/entra/)、[Azure RBAC Documentation](https://learn.microsoft.com/azure/role-based-access-control/)
