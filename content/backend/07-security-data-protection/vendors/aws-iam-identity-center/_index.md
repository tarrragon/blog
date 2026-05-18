---
title: "AWS IAM Identity Center"
date: 2026-05-18
description: "AWS 原生 workforce SSO、前 AWS SSO、Permission Set 跨帳號 access、可串外部 IdP federation"
weight: 4
tags: ["backend", "security", "vendor", "aws-iam-identity-center", "aws-sso", "identity", "aws"]
---

AWS IAM Identity Center 是 AWS 原生的 workforce SSO 控制面、前身為 AWS SSO（2022 改名）。它承擔三個責任：人類身份進 AWS 多帳號的 *統一入口*（Access Portal）、把使用者映射到各帳號 IAM role 的 *Permission Set* 模板、以及對少量已整合 SAML app 的 SSO gateway。它不是 AWS IAM 的替代品、是疊在 AWS IAM 之上的 *人類入口層*。

## 服務定位

IAM Identity Center 是 *人類身份進 AWS 的 portal*、不是 cloud resource permission engine。它跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) 的分工是兩層：Identity Center 管「人是誰、能登入哪些 account」、AWS IAM 管「進到 account 後對 resource 能做什麼」。實際機制是 Identity Center 透過 Permission Set 在每個目標 account 建一個 `AWSReservedSSO_*` 命名的 IAM role、使用者 assume 該 role 拿短期 STS token。

跟 [Okta](/backend/07-security-data-protection/vendors/okta/) 相比、Identity Center 的核心優勢是 *跟 AWS Organizations + Control Tower 原生整合*、Permission Set 可以一次發佈到數百個 account、不必每個 account 各接 SAML。代價是 SaaS app integration 量級遠少於 Okta（Okta 7000+ 預建、Identity Center 僅中等規模）、跨雲 federation（GCP / Azure）也不在原生範圍。

許多大型組織採三層架構：Okta 是 HRIS 下游的 identity source of truth、SCIM push 進 Identity Center、Identity Center 再 map 到 AWS IAM Permission Set。Okta 管「人是誰」、Identity Center 管「AWS portal 入口」、AWS IAM 管「resource 能做什麼」。中小組織可以省略 Okta、直接用 Identity Center 內建 user store、但就失去跨 SaaS 統一 SSO。

## 本章目標

讀完本頁、讀者能判斷：

1. Identity Center 在 *人類身份 / AWS portal / resource permission* 三層裡的位置、何時該交回 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) 或上游 IdP
2. Identity Source 選擇（內建 / Active Directory / 外部 SAML）對 lifecycle 與 lock-in 的長期影響
3. Permission Set / Account Assignment / Access Portal 三個核心概念的稽核重點
4. 何時 Identity Center 夠用、何時要疊 Okta 在前、何時 Identity Center 反而是錯選擇

## 最短判讀路徑

判斷 Identity Center 配置是否健康、最少看四件事：

- **誰能 assume 哪個 role**：Permission Set 跟 Account Assignment 是否走最小權限、`AdministratorAccess` 範圍 Permission Set 是否限定 break-glass、是否強制 [phishing-resistant 認證](/backend/knowledge-cards/authentication/) 才能 assume 高權限
- **Permission Set 邊界**：每個 Permission Set 的 session duration（預設 1 hour、可調 12 hour）、inline policy vs Customer Managed Policy reference、是否用 ABAC tag 收斂跨 account 散佈
- **External IdP federation 狀態**：Identity Source 是內建 / AD / 外部 SAML、若走外部 IdP SCIM push 是否監控 sync 失敗、signing certificate 是否在 rotation 排程內
- **CloudTrail 是否完整**：Identity Center 事件分布在 management account 跟 member account、是否有 organization trail 收齊、admin 變更 / Permission Set 變更 / failed assume 是否 alert

四件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 [Authorization](/backend/knowledge-cards/authorization/) 邊界的待補項目。

## 日常操作與決策形狀

**Identity Source 是根信任**：Identity Center 支援三種 user/group 來源 — 內建 store、AWS Managed AD / on-prem AD via AD Connector、外部 SAML IdP（Okta / Entra ID 等、SCIM 推進來）。選了之後 user lifecycle 從哪來就鎖死、換 Identity Source 是大工程（要重建所有 Permission Set assignment、舊 user GUID 不通用）。早期決定錯比 Permission Set 設錯難救。

**Permission Set 是 cross-account role template**：定義一次、apply 到多 account、實際在每個 account 部署成一個 AWS-Reserved 命名的 IAM role。Permission Set 本身不是 role、是 *role 的部署模板* — 改 Permission Set 會 push 到所有 account 上對應的 role。Customer Managed Policy reference 比 inline policy 好維護、但要先確保每個 target account 都有同名 policy、否則 assignment 會失敗。

**Account Assignment**：把 user/group 綁到 Permission Set + 特定 account 的三元組。這層用 group 而不是個別 user、跟著 Identity Source 的 group 變動自動同步。臨時權限（離職員工延長、incident 應變）走 access request workflow 或 IAM Access Analyzer + Just-in-Time、不要永久 assignment。

**Access Portal URL 是 phishing 目標**：custom URL（`https://<alias>.awsapps.com/start`）設定後變成員工每天用的入口、phishing 攻擊會 mimic。要強制 phishing-resistant MFA（WebAuthn / passkey）、純 push MFA 抗不過 fatigue。CLI 走 `aws sso login` 自帶 browser-based flow、不要叫員工複製貼 access key。

**Application assignment**：Identity Center 也能管 SAML app 的 SSO assignment、但 integration 數量遠少於 Okta。大量 SaaS app 的場景應該疊 Okta 在前、Identity Center 只管 AWS portal。

## 核心取捨表

| 取捨維度       | IAM Identity Center                   | Okta + AWS IAM                                       | 直接用 AWS IAM Users（不推薦）          |
| -------------- | ------------------------------------- | ---------------------------------------------------- | --------------------------------------- |
| 控制面責任     | AWS 託管、限 AWS 帳號 + 中等 SAML app | Okta 管人類身份、AWS IAM 管 resource、兩層分工       | 每個 account 各自管 user、無跨帳號統一  |
| 多帳號統一入口 | 原生、Permission Set 一次發到全 Org   | 透過 SAML federation 到 IAM role                     | 不存在 — 每個 account 各自 IAM Users    |
| SaaS app 範圍  | 中等規模 integration                  | 7000+ 預建 integration                               | 無                                      |
| Lifecycle      | 內建 / AD / 外部 SCIM 進來            | Okta 走 HRIS SCIM 同步、Identity Center 接 Okta SCIM | 手動管理、容易 stale                    |
| 退場成本       | 中 — AWS 內部換                       | 高 — Okta + Identity Center 都要拆                   | 高 — 大量 IAM Users 散佈在 N 個 account |
| 適合場景       | AWS-heavy、員工數中等、SaaS app 少    | 多雲 + 大量 SaaS + AWS 帳號數十個以上                | 不存在合理場景（small lab 例外）        |

選 Identity Center 的核心訴求：*AWS 是主要工作環境、員工 SaaS app 用量低、要統一多帳號入口而不要再付 Okta 訂閱*。員工大量用 SaaS 的場景應該疊 Okta 在前。

## 進階主題

**External IdP federation（Okta / Entra ID SCIM 進來）**：Identity Center 接外部 IdP 是 *push model* — IdP 主動 SCIM push、Identity Center 不 pull。push provisioning 失敗會 silent（IdP 端有 log、Identity Center 端只看到 user 沒出現）、要在 IdP 端設 sync failure alert。SAML signing certificate rotation 兩邊都要排程、過期會整個 federation 斷。

**Multi-account Permission Set 設計**：避免每個 environment / team 各自一份 Permission Set — 用 ABAC（tag-based access control）把「`Environment=Prod` + `Team=Payments`」的條件寫進一個 Permission Set 的 policy、tag 跟著 user attribute 跑。Permission Set 數量爆炸是 Identity Center 老化最常見訊號。

**Customer Managed Policy reference**：Permission Set 可以 reference target account 裡的 customer managed policy（同名同 path）、policy 本身在每個 account 獨立維護。比 inline policy 適合大規模、但要靠 CI / Terraform 確保 policy 在所有 target account 同步存在、否則 assignment 失敗。

**Session duration 是攻擊面**：預設 1 hour、可調到 12 hour。長 session 對 dev 體驗友善、但不利於 [credential rotation](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) — 高權限 Permission Set（`AdministratorAccess`、production write）應該短 session（1-2 hour）、低風險 read-only 可放 8-12 hour。

**IAM Identity Center API 不該當 workforce IdP 用**：API 是給 admin 管 assignment 用、不是給 app 拿 user token。要 workforce app SSO 走 SAML / OIDC federation、不要叫 app 打 Identity Center API 查 user。

## 排錯與失敗快速判讀

- **Permission Set 數量爆炸**：每個 team / environment 各一份、上百個 Permission Set 沒人敢動 — 改用 ABAC + user attribute 把條件寫進 policy、收斂到十位數
- **Identity Source 選錯難換**：早期選內建 store、後來公司導入 Okta 要換成外部 SAML — 整個 user GUID 重新映射、Permission Set assignment 重綁、評估比建新 tenant 還久
- **External SCIM sync 失敗 silent**：Okta 端 push 失敗、Identity Center 沒人 — 要在上游 IdP 設 SCIM provisioning failure alert、不要等使用者反映「我登不進去」
- **Access Portal URL 被 phishing**：custom URL 員工記憶、phishing 站 mimic、無 phishing-resistant MFA 擋不住 — 強制 WebAuthn / passkey、員工教育只認 bookmark / SSO launcher
- **CloudTrail 不完整**：只開 management account trail、member account 的 role assumption 看不到 — 開 organization trail 收齊、特別 alert Permission Set 變更與失敗 assume
- **Break-glass 缺席**：Identity Center 控制面故障時 console 進不去 — 保留每個 account 的 root credential（離線存）跟少數 break-glass IAM User（hardware MFA、與 Identity Center 獨立 audit）、季度驗證

## 何時改走其他服務

| 需求形狀                                       | 改走                                                                                                                                                        |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 大量 SaaS app 統一 SSO                         | [Okta vendor](/backend/07-security-data-protection/vendors/okta/)（疊在 Identity Center 前）                                                                |
| Customer / B2C identity                        | [Auth0 vendor](/backend/07-security-data-protection/vendors/auth0/)                                                                                         |
| 自管 / 不接受 cloud-managed IdP                | [Keycloak vendor](/backend/07-security-data-protection/vendors/keycloak/)                                                                                   |
| AWS resource permission（policy / role / STS） | [AWS IAM vendor](/backend/07-security-data-protection/vendors/aws-iam/)                                                                                     |
| 跨雲 federation（GCP / Azure workforce）       | [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/) |
| Secret / API key 治理                          | [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)                                               |

## 不在本頁內的主題

- AWS IAM 的 policy / role / STS 機制細節（屬 AWS IAM vendor 頁）
- Permission Set 的 JSON policy 撰寫教學
- AWS Organizations / Control Tower 的完整架構
- 各 SaaS app SAML 接線教學

## 案例回寫

| 案例                                                                                                                                                        | 跟 IAM Identity Center 的關係                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| [Azure AD Identity Control Plane 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)                                    | Identity Center 控制面故障會擋住 AWS console portal、降級路徑必須事先設計（emergency root credential、break-glass IAM User）     |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                         | Permission Set session duration 跟 external IdP signing key rotation 是不同域、要分開排程、不能混為一談                          |
| [Okta Support System Incident 2023](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)                                          | Okta 作為 Identity Center 的 external IdP 時、上游事件會傳導下來、Identity Center 端要看 SCIM sync 異常與 federation token reuse |
| [Cloudflare 2023 Okta Token Follow-Through](/backend/07-security-data-protection/red-team/cases/identity-access/cloudflare-2023-okta-token-follow-through/) | 上游 IdP 出事後、Identity Center 端的 active session 是否要強制 reauth、不能等供應商公告                                         |

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[Okta vendor](/backend/07-security-data-protection/vendors/okta/)（外部 IdP 疊在前）、[Auth0 vendor](/backend/07-security-data-protection/vendors/auth0/)、[Keycloak vendor](/backend/07-security-data-protection/vendors/keycloak/)
- 下游：[AWS IAM vendor](/backend/07-security-data-protection/vendors/aws-iam/)（Permission Set 落地的 resource permission 層）、[Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)（多雲對照）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Identity Center 事件如何 routing 進 IR 流程）
- 官方：[AWS IAM Identity Center Documentation](https://docs.aws.amazon.com/singlesignon/)
