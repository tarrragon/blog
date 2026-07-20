---
title: "Auth0"
date: 2026-05-18
description: "B2C / B2B Customer Identity Provider、Universal Login、Action / Rule hook、屬 Okta 旗下 Customer Identity Cloud"
weight: 2
tags: ["backend", "security", "vendor", "auth0", "identity", "customer-identity"]
---

Auth0 是 Customer Identity Cloud 的代表選項。它承擔三段責任：B2C / B2B app 的*使用者登入流程*託管、社交與企業 connection 的 token broker、user profile 與 metadata 的 store。當產品把登入交給 Auth0、信任邊界從「我的 app 自管密碼表」變成「tenant 配置 + Action hook 程式碼 + signing key 託管」三件事是否健康。認證在 [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/) 裡是 commodity 買的典型、Auth0 正是它的 feature SaaS（dev-tool 端）例子；要不要買、外包到多深、見 [外包深度](/backend/knowledge-cards/capability-outsourcing-depth/) 卡。

## 服務定位

Auth0 是 *customer identity 的控制面*、不是員工 SSO（員工走 [Okta Workforce](/backend/07-security-data-protection/vendors/okta/) 或 [AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)）。雖然 Auth0 於 2021 被 Okta 收購、目前屬「Customer Identity Cloud」產品線、跟 Workforce Okta 是 *同公司不同 control plane*：tenant 叢集、事件分布、signing key 託管路徑都分開、Okta Workforce 的事故（2022 Sitel、2023 support system HAR）並未直接打到 Auth0 customer。

跟自管 [Keycloak](/backend/07-security-data-protection/vendors/keycloak/) 比、Auth0 把 Universal Login UI、social connection 預建、Rules / Action runtime、attack protection 都託管出去 — 代價是 *SaaS 計費、token issuance / login attempt 都計量*、流量大的 B2C 場景遇到 credential stuffing 不擋會吃成本。跟 [AWS Cognito](https://docs.aws.amazon.com/cognito/) / [Firebase Auth](https://firebase.google.com/docs/auth) 比、Auth0 的核心優勢是 *developer-first tenant 體驗 + 預建 social connection（Google / Facebook / Apple / Microsoft 等數十種）+ Action hook 寫 JS 客製*。

## 本章目標

讀完本頁、讀者能判斷：

1. Auth0 該承擔哪一段 customer identity 控制（login flow / token broker / profile store / B2B Organizations）、哪一段該回到自己的 app
2. Auth0 tenant 的信任邊界與最低稽核需求（admin role、management API token、Action 程式碼、connection 設定）
3. Auth0 流量出事或母公司事件時的降級路徑（fallback connection、token rotation、anomaly throttle）
4. 何時用 Auth0、何時走 Cognito / Firebase Auth / Keycloak 的取捨

## 最短判讀路徑

判斷 Auth0 tenant 是否健康、最少看四件事：

- **誰能做什麼**：Dashboard admin、Management API token 的 owner 與 scope、Action 是否走 code review、tenant 之間（dev / staging / prod）是否分離且授權獨立
- **憑證在哪裡**：Management API token / M2M client 的 scope 與 TTL、社交 connection 的 client secret 存放位置、signing key（per-tenant）的 rotation 節奏、是否啟用 Custom Domain（避免 token issuer 暴露 `*.auth0.com` 域名）
- **入口如何暴露**：登入走 Universal Login（託管 UI）還是 Embedded Login（嵌自家 app）、Cross-Origin Authentication 是否打開、Attack Protection（bot detection / brute-force / breached password / suspicious IP throttling）配置強度
- **證據是否可回查**：Tenant Log 是否同步到 SIEM（Log Stream 推 HTTP / Datadog / Splunk）、登入失敗 / Action 例外 / Management API 變更是否 alert、保留期是否符合合規要求

四件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 [Authentication](/backend/knowledge-cards/authentication/) 邊界的待補項目。

## 日常操作與決策形狀

**Tenant 與環境分離**：Auth0 的 tenant 是邏輯隔離的多租戶 SaaS、不是物理叢集。每個環境（dev / staging / prod）開獨立 tenant、避免 dev 的 Action bug 打到 prod 流量、避免共用 client secret 跨環境洩漏。tenant 間用 `auth0-deploy-cli` 同步配置、Action 程式碼進版控。

**Connection 設計**：Database Connection（Auth0 託管帳密 store）跟 Social / Enterprise Connection（OIDC / SAML federation 到 Google / Microsoft / Okta）是兩種來源。決策點是 *user 是否要進 Auth0 profile store* — 純 federation 不存密碼、純 Database Connection 是 Auth0 替 app 管帳密表。混用要清楚 *primary identity* 與 *linked account* 的合併規則。

**Action / Rule hook 的風險**：Action（新框架）跟 Rule（舊框架）讓 tenant admin 在 login pipeline 注入 JS 程式碼（pre / post login、M2M、send email 等）。這是 Auth0 強大但也是 *最大的供應鏈攻擊面* — Action 可以 `require()` npm package、惡意 dependency 會在每個 login flow 執行。應該 pin dependency 版本、code review、用最小權限的 Management API scope、定期掃 dependency CVE（思維對齊 [紅隊 supply chain 案例](/backend/07-security-data-protection/red-team/cases/supply-chain/)）。

**Universal Login vs Embedded Login**：Universal Login 把登入 UI 託管在 Auth0 domain（或 Custom Domain）、user 跳轉到該頁完成登入後 redirect 回 app — 防 phishing / CSRF 的成本由 Auth0 吃。Embedded Login 把登入表單嵌進自己 app 並用 `/co/authenticate` 端點 — 看似 UX 順、但要自己防 XSS、CSRF、CORS、credential leak、且要打開 Cross-Origin Authentication（暴露額外攻擊面）。預設選 Universal Login、Embedded 只在 UX 強需求且能承擔安全成本時開。

**Management API token / M2M client**：Management API 控制整個 tenant（建 user、改 client secret、改 Action 程式碼）。token 不該長期存在程式碼或 CI；改用 M2M Application（client credentials grant）拿短期 token、scope 收到最小（`read:users` ≠ `update:users` ≠ `update:actions`）、走 [Secret Management](/backend/knowledge-cards/secret-management/) 取用。

**Attack Protection 配置**：B2C 流量大、登入嘗試本身計費也是攻擊面。Brute-force Protection（單 IP 多失敗鎖 user）、Suspicious IP Throttling（單 IP 多失敗鎖 IP）、Breached Password Detection（已洩漏密碼禁用）、Bot Detection（CAPTCHA / risk score）四個機制都該打開、否則 credential stuffing 既吃成本也提高帳號被接管的機率。

**Break-glass 與 fallback**：B2C 場景沒有「員工備用 admin」概念、break-glass 是 *確保使用者在 Auth0 暫不可用時仍能登入*。常見作法：app 端容忍 Auth0 暫時失敗、提供 magic link / email OTP 的替代登入路徑（透過獨立 ESP）、或預先發放長 TTL 的 refresh token 撐過短時故障。tenant 管理面則維持至少 2 個獨立 admin、credential 離線存。

**Audit / handoff**：Tenant Log 透過 Log Stream 推 SIEM、alert 三類事件 — Management API 對 Action / Connection / Client 的變更（供應鏈）、登入異常突增（credential stuffing）、support impersonation / Auth0 員工 access tenant 的紀錄（control plane）。

## 核心取捨表

| 取捨維度          | Auth0                                                | AWS Cognito                                | Firebase Auth                              | 自管 Keycloak                              |
| ----------------- | ---------------------------------------------------- | ------------------------------------------ | ------------------------------------------ | ------------------------------------------ |
| 控制面責任        | Auth0 託管 issuer / signing / Action runtime         | AWS 託管、限 AWS 帳號信任邊界              | Google 託管、綁 Firebase / GCP             | 自己跑 issuer、key、HA、support            |
| Social connection | 預建數十種、UI / token broker 完整                   | 主要 OIDC / SAML、social 要自己接          | Google / Apple / Facebook 預建、其他要自接 | OIDC / SAML 通用、specific provider 要自配 |
| 客製化能力        | Action JS hook 強、Universal Login 高度客製          | Lambda Trigger、UI 客製有限                | Cloud Function Trigger、UI 客製中等        | 任何 — 自己掌握程式碼                      |
| 計費模型          | 月活躍 user（MAU）+ B2B Organizations + 進階功能加價 | MAU 階梯、AWS 內部其他資源費用             | MAU + 簡訊 / phone auth 另計               | 自管基礎設施成本                           |
| 成本陡升點        | 大量 MAU、credential stuffing、Adaptive MFA 加價     | Cognito Identity Pool federation 複雜場景  | 通常便宜、但 phone auth 成本明顯           | 規模化後運維成本（HA、DR、cert、upgrade）  |
| 適合場景          | B2C / B2B SaaS、要 social login、developer-first     | AWS-heavy 後端、不要求 social 廣度         | mobile-first、Firebase 生態內              | 主權 / 自管要求、不接受 SaaS IdP           |
| 退場成本          | 中高 — user / password hash 可匯出、Action 要重寫    | 中 — Cognito user pool 可匯出、policy 重寫 | 中 — Firebase user 可匯出                  | 低 — 自己掌握                              |

選 Auth0 的核心訴求：*customer identity + 大量 social / enterprise connection + 要 developer 客製 login flow*、且接受 SaaS 計費與第三方控制面風險、能投入 SIEM / Action 程式碼治理 / attack protection 配置。

Microsoft 生態（Entra External ID / 前 Azure AD B2C）是另一個 B2C / B2B 選項、本表沒列入主要競品 — 它在 M365 / Azure 重度組織內是合理選擇、但 social connection 預建廣度跟 developer-centric tenant 體驗仍不及 Auth0。M365 重度 + B2C 需求的組織可同時評估 [Entra ID](/backend/07-security-data-protection/vendors/azure-rbac/) 的 External ID 產品線。

## 進階主題

**Action / Rule 的供應鏈治理**：Action 程式碼進版控、走 PR review、`auth0-deploy-cli` 部署。Action 引用的 npm dependency pin 版本、避免 `^` / `~`、CI 跑 SCA 掃 CVE。新增 Action 時 default scope 給 read-only、需要寫操作另外升級。Action secret（OAuth credential、API key）走 Action Secret 管理、不寫死在程式碼。

**B2B Organizations**：Auth0 Organizations 把同 tenant 內的多客戶（B2B 場景）邏輯隔離 — 每個 organization 有自己的 connection、branding、member。設計點是 *user 是 organization member 還是 tenant-wide user*、跨 organization 操作的 admin 是否有 organization scope。Organization 之間的隔離是 tenant 內邏輯層、共享底層 control plane、不能等同實體 tenant 隔離。

**Adaptive MFA / [Step-up Authentication](/backend/knowledge-cards/step-up-authentication/)**：Auth0 Adaptive MFA 用 device / location / behavioral signal 動態升級 MFA 要求（impossible travel、新裝置、低信任 IP）。屬付費 add-on、本質是把 risk-based 認證內建。對 B2C 場景比強制全 user MFA 友善、但要把 *risk threshold* 跟 *false positive 容忍度* 設清楚、避免合法 user 被連續挑戰流失。

**Custom Domain**：預設登入網域是 `<tenant>.auth0.com`、揭露使用 Auth0 與 tenant 名稱、且 issuer 是 Auth0 子網域。Custom Domain 把 issuer 改成自己網域（如 `login.example.com`）、user 看到的 URL 一致、降低 phishing 對照成本。屬付費功能、production app 預設應該開。

**Cross-Origin Authentication 的攻擊面**：Embedded Login 必須開 Cross-Origin Authentication、讓 app 域名直接呼叫 Auth0 的 `/co/authenticate`。風險是 XSS 拿到 token、CSRF 偽造登入、third-party cookie 政策變動讓 silent auth 壞掉。Universal Login 不需要這個、所以同樣風險不存在 — 這是 Universal Login 推薦的核心理由。

## 排錯與失敗快速判讀

- **Management API token 散落 / 過權**：CI / 後端服務各自存 token、scope 都給 `update:users` / `update:actions` — 改 M2M Application + 最小 scope、定期 rotate、用 [Secret Management](/backend/knowledge-cards/secret-management/) 集中取用
- **Action 直接 `require` 未 pin 的 npm package**：login flow 每次都拉最新版、惡意 dependency 直接執行 — pin 版本、code review、定期掃 CVE
- **登入嘗試暴增 / 計費突增**：Attack Protection 沒開或門檻太鬆、credential stuffing 吃額度 — 打開 Bot Detection、Brute-force、Suspicious IP Throttling、配合 [Anomaly Detection](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- **使用 Embedded Login 又沒控 XSS**：自家 app 一旦 XSS、token 直接被偷 — 改 Universal Login、或補上嚴格 CSP / DOM 防護、定期 pen test
- **Tenant Log 沒進 SIEM**：事件只在 Dashboard、無法跨系統 correlation — 配 Log Stream 打到 [SIEM](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、特定事件接 [alert runbook](/backend/knowledge-cards/alert-runbook/)
- **沒 Custom Domain**：phishing 對照成本低、issuer 暴露 vendor — 配 Custom Domain、TLS cert 自管或走 Auth0 託管
- **B2B Organizations 缺 scope 限制**：admin 工具沒按 organization scope、單一 admin compromise 跨 organization 擴散 — 思維對齊 [Okta Cross-Tenant 2023](/backend/07-security-data-protection/cases/okta-cross-tenant-impersonation-2023/) 的 lesson

## 何時改走其他服務

| 需求形狀                          | 改走                                                                                                                                                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 員工 SSO / Workforce identity     | [Okta vendor](/backend/07-security-data-protection/vendors/okta/) / [AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)                                                     |
| 自管 / 不接受 SaaS IdP            | [Keycloak vendor](/backend/07-security-data-protection/vendors/keycloak/)                                                                                                                                                |
| AWS-only 應用                     | [AWS Cognito](https://docs.aws.amazon.com/cognito/)                                                                                                                                                                      |
| Firebase / mobile-first 生態      | [Firebase Authentication](https://firebase.google.com/docs/auth)                                                                                                                                                         |
| Cloud resource 權限（非人類身份） | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/) |
| 事件偵測（跨系統）                | [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)                                                                                                              |
| Secret / API key 治理             | [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)                                                                                                            |

## 不在本頁內的主題

- Auth0 完整 OIDC / OAuth2 規格細節
- Action / Rule 完整 API 與 trigger 清單
- B2B Organizations 完整 schema 與 SDK 整合教學
- Auth0 定價層級的詳細功能對照
- 各 social connection provider 的 OAuth app 註冊步驟

## 案例回寫

Auth0 在 07 沒有直接案例（母公司 Okta 的事件並未直接打到 Auth0 customer），以下案例採對照引用、抽取對 Auth0 customer 的 lesson。要注意的是 *缺直接案例不等於 vendor 沒有風險* — Auth0 自 2021 被 Okta 收購以來未公開重大 vendor 級事件、但同類 SaaS IdP 的歷史事件（Okta 集團、signing key 託管、credential stuffing）都是 Auth0 customer 的可預期風險面、不該等到第一次出事才補控制：

| 案例                                                                                                                                                        | 跟 Auth0 的關係（對照）                                                                                        |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| [Okta Support System Incident 2023](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)                                          | 母公司 Workforce 事件、Auth0 customer 未直接受害；lesson：signing key 受託管時 break-glass 與替代登入路徑必要  |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                         | Management API token / connection client secret 的 rotation 要分域 — 多 tenant / 多 connection 不能用同一把    |
| [Cloudflare 2023 Okta Token Follow-Through](/backend/07-security-data-protection/red-team/cases/identity-access/cloudflare-2023-okta-token-follow-through/) | 上游 IdP 事件後客戶側的 token rotation 節奏；Auth0 customer 應主動 rotate Management API token、不等供應商公告 |
| [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)                                         | Auth0 Adaptive MFA / step-up 的設計目標 — 高風險動作要求 phishing-resistant factor、避免單純 push fatigue      |
| [紅隊 supply chain 案例](/backend/07-security-data-protection/red-team/cases/supply-chain/)                                                                 | Action / Rule 引用 npm dependency 的供應鏈攻擊面、思維同 build pipeline 但發生在 login flow                    |

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[Okta vendor](/backend/07-security-data-protection/vendors/okta/)、[Keycloak vendor](/backend/07-security-data-protection/vendors/keycloak/)、[AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)
- 下游：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)（Auth0 認證後的 cloud resource 權限層）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Auth0 異常如何 routing 進 IR 流程）
- 官方：[Auth0 Documentation](https://auth0.com/docs)
