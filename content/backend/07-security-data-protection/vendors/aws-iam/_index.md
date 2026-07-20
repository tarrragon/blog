---
title: "AWS IAM"
date: 2026-05-18
description: "AWS cloud resource permission engine、Role / Policy / STS、跨帳號信任邊界與 OIDC federation 的核心"
weight: 5
tags: ["backend", "security", "vendor", "aws-iam", "iam", "aws", "cloud-iam"]
---

AWS IAM 是 AWS 的 cloud resource permission engine — 它回答的問題是「這個身份能對哪一個 AWS resource 做哪一個 API call」。它不是 workforce IdP、也不負責「這個人類是誰」的判定。所有 AWS API 流量（無論來自 console 操作、CI pipeline、Lambda、EC2、跨帳號 partner）最終都要經過 IAM 的 policy 評估、IAM 是 AWS 安全模型的根。

## 服務定位

AWS IAM 是 *cloud resource permission engine*、人類 workforce 的 SSO 與 lifecycle 應該走 [AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/) 或外部 IdP（[Okta](/backend/07-security-data-protection/vendors/okta/) / [Keycloak](/backend/07-security-data-protection/vendors/keycloak/)）。Identity Center 把人類映射到 *Permission Set*、Permission Set 在每個目標帳號裡實際上是 AWS-Reserved IAM Role — 也就是說：人類登入走 Identity Center、實際的 API 授權判斷一定回到 IAM。兩層責任分清楚、policy 才不會錯放在「誰是誰」的地方。

AWS IAM 跟 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/) 在 policy model 上設計差異很大。AWS 的表達力最強 — identity-based policy、resource-based policy、Service Control Policy（SCP）、Permission Boundary、Session Policy 是五個獨立的層、最終結果由 *Explicit Deny > Org SCP > Resource-based > Identity-based > Permission Boundary > Session Policy* 的評估順序決定。表達力換來的代價是 *最容易設定錯*：S3 bucket policy 設錯 = public、KMS key policy 漏一個 condition = 跨帳號可以解密、Trust Policy 沒設 ExternalID = confused deputy 攻擊面。

## 本章目標

讀完本頁、讀者能判斷：

1. 哪些 IAM first-class concept（User / Group / Role / Policy / STS）對應到自己的場景、哪些要避免（例如：給人類發 IAM User access key）
2. 跨帳號信任、CI / 第三方 SaaS 連進 AWS、service-to-service 認證該走 Role assumption / OIDC trust 還是 Roles Anywhere
3. SCP、Permission Boundary、resource-based policy 三層上限的疊加方式、何時用哪一層
4. CloudTrail + Access Analyzer 的稽核 baseline、出事時的最短取證路徑

## 最短判讀路徑

判斷一個 AWS 帳號的 IAM 配置是否健康、最少看四件事：

- **誰能 assume 哪個 Role**：所有 Role 的 Trust Policy（誰能呼叫 `sts:AssumeRole`）、有沒有跨帳號 trust、跨帳號 trust 是否帶 ExternalID、有沒有 `*` 在 Principal 裡
- **Resource-based policy 暴露面**：S3 bucket policy、KMS key policy、Lambda function policy、SNS / SQS policy 是否有 `Principal: *` 或來自非預期帳號；用 [IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html) 找 *unintended external access*
- **Permission Boundary 與 SCP 是否生效**：開發者建的 Role 是否 attach Permission Boundary（防止 admin 自己給自己升權）、Organization 是否 attach SCP 做整個 OU 的上限
- **CloudTrail 是否完整、是否進 SIEM**：management event 跟 data event 都開、跨 region、跨帳號、保留期符合稽核要求、特定事件（`AssumeRole` 失敗、root login、`CreateAccessKey`）接 [alert runbook](/backend/knowledge-cards/alert-runbook/)

四件事任一缺失、就是 [Authorization](/backend/knowledge-cards/authorization/) 與 [Audit Log](/backend/knowledge-cards/audit-log/) 邊界的待補項目。

## 日常操作與決策形狀

**Role 設計（cross-account / service / OIDC trust）**：所有 *持續性* 的身份都應該是 Role、不是 IAM User。Service Role（給 EC2 / Lambda / ECS task）是 AWS 內部 service-to-service；Cross-account Role 給 partner 帳號或自家其他帳號用 `sts:AssumeRole` 進來；OIDC trust 是現代 CI 必備路徑（GitHub Actions / GitLab / 自管 K8s 用短期 OIDC token 換 AWS STS 短期憑證、不在 secret store 存 long-lived access key）。

**Policy 種類分工**：identity-based policy attach 在 User / Group / Role 上、回答「這個身份能做什麼」。Resource-based policy attach 在 resource 上（S3 bucket、KMS key、SNS topic、Lambda function）、回答「誰能對這個 resource 做什麼」— 同帳號內 identity-based 跟 resource-based 任一個 allow 就通過、跨帳號 *兩邊都要 allow*。SCP 是 Organization 層級的上限、不是 grant — SCP allow 不會給任何權限、SCP deny 會擋掉整個 OU 的所有 identity。Permission Boundary 是 *user 角度的上限*、給 admin 用來限制「我把 admin 權限委派給 developer 後、developer 自己建的 role 不能超過這條線」。

**STS 與臨時憑證**：所有 cross-account、service-to-service、人類 console federation 都應該走 STS — `sts:AssumeRole`（跨帳號 / 跨 role）、`sts:AssumeRoleWithSAML`（SAML IdP）、`sts:AssumeRoleWithWebIdentity`（OIDC）、`sts:GetFederationToken`（外部 broker）。Session 預設 1 小時、最長可設 12 小時（依 Role 設定）。Debug 起手式：`aws sts get-caller-identity` 確認當前 caller 是誰、是 User、Role 還是 federated session。

**Access Key 治理**：IAM User 的 long-lived access key 是 *最後手段*、用於 break-glass 或無法跑 IMDS / Roles Anywhere 的 legacy。所有 access key 走 [Secret Management](/backend/knowledge-cards/secret-management/)、定期 rotation、IAM Access Analyzer 的 unused access finding 找閒置 key。

**CloudTrail / Access Analyzer baseline**：CloudTrail organization trail 開到所有帳號、management event 必開、data event（S3 object level、Lambda invoke）依資料敏感度開。Access Analyzer 至少跑 *external access*（找 resource-based policy 把資源暴露給外部帳號）跟 *unused access*（找閒置 Role、user、permission）。

**Trust Policy / ExternalID**：第三方 SaaS（監控、CSPM、備份服務）要進你的 AWS 帳號時、其 Trust Policy 必須要求 ExternalID — 否則攻擊者只要知道 Role ARN 就能假冒第三方 SaaS 的呼叫端、走 confused deputy 攻擊面（[AWS confused deputy 官方說明](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html)）。自家跨帳號 trust 不一定要 ExternalID、第三方一定要。

## 核心取捨表

| 取捨維度       | AWS IAM                                                  | Google Cloud IAM                            | Azure RBAC                                      |
| -------------- | -------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------- |
| 基本單位       | Policy（attach 到 identity 或 resource）                 | Role Binding（principal + role + resource） | Role Assignment（scope + principal + role）     |
| 隔離邊界       | Account（root）+ Organization SCP                        | Project / Folder / Org（階層 inherit）      | Subscription / Management Group（階層 inherit） |
| Policy 表達力  | 高 — identity / resource / SCP / boundary / session 五層 | 中 — Conditional IAM + Organization Policy  | 中 — RBAC + Azure Policy 兩層                   |
| Resource-based | 多 service 支援（S3 / KMS / SNS / SQS / Lambda...）      | 較少（GCS / Pub/Sub / KMS 等）              | 較少、多走 RBAC 統一                            |
| 設定錯誤代價   | 高 — bucket / key policy 設錯就 public                   | 中 — 較統一但精細度也較低                   | 中 — 階層 inherit 容易誤放                      |

AWS IAM 是 *表達力最強、最容易設定錯* 的雲端 IAM。Google Cloud IAM 設計較統一、policy model 易讀但精細度有限。Azure RBAC 走 inheritance + scope、靠 Management Group 結構治理。三家都不能直接互換、跨雲環境需要在每家自己的 IAM 模型裡建等價的 least-privilege baseline。

## 進階主題

**Service Control Policy（SCP）**：Organization 層級的上限、用來宣告「整個 OU 永遠不能做什麼」 — 例如禁止 root user 操作、禁止關閉 CloudTrail、禁止在非允許 region 建 resource。SCP 是 *deny-list 防護網*、不是日常授權；日常授權交給 identity-based policy。SCP 過嚴會擋住合法操作、過鬆等於沒設、設計時要對齊 organization 的安全政策骨幹。

**Permission Boundary**：用在 *委派 admin* 場景 — 公司想讓 platform team 自己建 IAM Role 給應用、但又不想讓他們建出 admin role。Admin 給 platform team 一個 Permission Boundary policy、platform team 建的所有 Role 都會被這個 boundary 限制 *上限*、就算 attach 了 `AdministratorAccess` 也只能在 boundary 範圍內生效。

**ABAC（attribute-based / tag-based access control）**：大規模 multi-account 環境、每個 service 一個 Role 會 Role 爆炸。ABAC 用 *tag*（principal tag、resource tag、request tag）做 policy condition — 例如「Role 上有 `team=payments` tag 的人能操作 `team=payments` tag 的 resource」。設計成立的前提是 tag 來源可信、不能讓使用者自己改 principal tag。

**IAM Roles Anywhere**：給 AWS 之外的 workload（地端 K8s、其他雲、邊緣設備）用 X.509 憑證換 STS 短期憑證。前提是有一個可信的 PKI（自管 CA 或公開 CA）跟 trust anchor。比起把 IAM User access key 放在地端 secret store、Roles Anywhere 是更安全的設計。

**OIDC trust（GitHub Actions / GitLab CI / 第三方 CI）**：CI / CD 連 AWS 的標準做法。在 AWS 建一個 OIDC identity provider 指向 CI 的 OIDC issuer、Role 的 Trust Policy condition 限制 `repo:org/repo:ref:refs/heads/main`、CI workflow 直接 `aws sts assume-role-with-web-identity`。完全不需要在 CI secret store 存 long-lived AWS access key、token TTL 隨 job 結束自動失效。

**Resource-based policy 跨帳號設計**：S3 bucket policy、KMS key policy、SNS / SQS / Lambda policy 都支援跨帳號授權。設計時兩件事必查：Principal 是否包含預期的帳號 / Role ARN、condition 是否限制來源（`aws:SourceAccount`、`aws:SourceArn`、`aws:PrincipalOrgID`）。漏了 condition、就可能讓任何拿到「假裝是某個 service」身份的人都能呼叫 — Capital One 2019 事件本質就是 SSRF 取得 EC2 IMDS 的 Role credential、再用該 Role 的權限去 S3 列舉跟讀取資料、揭示 *resource-based policy + identity-based policy 沒有最小化、就會在事故時最大化*。

## 排錯與失敗快速判讀

- **`AccessDenied` 但 policy 看起來 allow**：先用 [IAM Policy Simulator](https://policysim.aws.amazon.com/) 或 `aws iam simulate-principal-policy` 重算、確認是 SCP 擋、Permission Boundary 擋、resource-based policy 沒 allow、還是 condition key 不匹配。Explicit Deny 永遠贏。
- **跨帳號 `sts:AssumeRole` 失敗**：兩邊都要設 — caller 帳號的 identity-based policy 要 allow `sts:AssumeRole` 到目標 Role ARN、目標 Role 的 Trust Policy 要 allow caller 的 Principal。漏其一就失敗。
- **S3 bucket 不小心 public**：用 Access Analyzer 的 external access finding 找、用 *Block Public Access* 帳號級別開關擋掉（即使 bucket policy 寫了 public、Block Public Access 也會擋）。常見根因：bucket policy 寫 `Principal: *` 沒加 condition、或 ACL 殘留歷史設定。
- **Role / access key 殘留**：用 Access Analyzer 的 unused access finding、或 IAM credential report 找超過 90 天沒用的 user / role、配 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) 的分域分批 rotation 流程清理
- **第三方 SaaS Role 缺 ExternalID**：稽核第三方 vendor 的 onboarding 文件、若沒要求 ExternalID 是 vendor 自己安全模型有破口、自己這邊也要拒絕這種 onboarding
- **CloudTrail 落地不全**：Organization trail 沒覆蓋新建帳號、data event 沒開、log 沒進 SIEM、保留期不足 — 這四件事都會讓事故發生時拿不到證據

## 何時改走其他服務

| 需求形狀                            | 改走                                                                                                                                              |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 人類員工 SSO 進 AWS                 | [AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)                                                  |
| 多雲 / SaaS app 統一 SSO            | [Okta](/backend/07-security-data-protection/vendors/okta/) / [Keycloak](/backend/07-security-data-protection/vendors/keycloak/)                   |
| Customer / B2C identity             | [Auth0](/backend/07-security-data-protection/vendors/auth0/)                                                                                      |
| Google Cloud resource 權限          | [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)                                                                |
| Azure resource 權限                 | [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)                                                                            |
| Secret / API key 治理               | [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)                                     |
| Key lifecycle / envelope encryption | AWS KMS vendor 頁（S2 批次撰寫中）+ [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) |
| 事件偵測（CloudTrail 以外）         | 04 SIEM / detection 工具與 07 SIEM 章節                                                                                                           |

## 不在本頁內的主題

- IAM policy JSON 語法完整 reference 與所有 condition key 清單
- 每個 AWS service 的細部 IAM 動作對照
- AWS Organization、Control Tower、Landing Zone 完整建置流程
- KMS / Secrets Manager / Certificate Manager 的內部細節（見對應 vendor 頁）

## 案例回寫

| 案例                                                                                                                                                                  | 跟 AWS IAM 的關係                                                                                                                                                                                    |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Microsoft Storm-0558 Signing Key 2023](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/)                                            | 雖是 Microsoft Entra / Exchange Online 事件、對 AWS *cross-account role assumption signing chain* 提供對照：ExternalID 設計、[HSM](/backend/knowledge-cards/hsm/)-bound key、跨帳號 token 驗證一致性 |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                                   | IAM User access key、STS session、Role trust 的 rotation 必須分域分批、不能單一指令打全部                                                                                                            |
| [Microsoft Storm-0558 Signing Key Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | 對 IAM Roles Anywhere / OIDC trust 的 signing material 治理啟示：trust anchor、key custody、跨環境驗證                                                                                               |

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)、[Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)、[Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)
- 下游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)（AWS KMS vendor 頁 S2 批次撰寫中）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（CloudTrail / Access Analyzer 訊號如何 routing 進 IR 流程）
- 官方：[AWS IAM User Guide](https://docs.aws.amazon.com/IAM/latest/UserGuide/)、[AWS IAM Identity Center User Guide](https://docs.aws.amazon.com/singlesignon/latest/userguide/)
