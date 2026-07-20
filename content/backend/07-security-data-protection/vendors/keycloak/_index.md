---
title: "Keycloak"
date: 2026-05-18
description: "Open source self-hosted Identity Provider、Red Hat 主導、Realm-based multi-tenancy、適合資料主權與自訂 flow 需求"
weight: 3
tags: ["backend", "security", "vendor", "keycloak", "identity", "self-hosted", "open-source"]
---

Keycloak 是 open source 自管 Identity Provider、Red Hat 主導維護（商業支援版本為 Red Hat build of Keycloak、前身 Red Hat SSO）。它承擔的責任跟 SaaS IdP 相同 — SSO、MFA、federation、user lifecycle — 但 *整個控制面留在組織自己手上*：issuer signing key、support tooling、底層 PostgreSQL、HA cluster、CVE patch cadence 全部自管。決定上 Keycloak 不是技術偏好、是組織決定把 SaaS IdP 的「第三方信任成本」換成「自家 SRE 運維成本 + 安全責任」。在 [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/) 的光譜上、Keycloak 是認證能力「建」側的 canonical 例子 — 把 feature SaaS（Auth0 / Okta）的第三方信任成本、換成自管控制面的運維成本；什麼訊號該翻到這一側、見 0.22 與 [外包深度](/backend/knowledge-cards/capability-outsourcing-depth/) 卡。

## 服務定位

Keycloak 是 *自管控制面* 的 human identity 與 federation engine、不是 cloud resource permission engine。跟 [Okta](/backend/07-security-data-protection/vendors/okta/) / [Auth0](/backend/07-security-data-protection/vendors/auth0/) 的本質差異在於信任邊界落點：SaaS IdP 把 signing key、tenant 隔離、support workflow 都託管出去、客戶承擔「供應商出事我也跟著被打」的風險；Keycloak 把整條控制面收回自家機房或自家 VPC、客戶承擔「signing key 過期 / DB 崩 / Java app CVE 沒跟上」的運維風險。

跟 cloud-native SSO（[AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)）相比、Keycloak 的核心優勢是 *不綁雲廠 + 可深度客製 authentication flow + 資料不出境*。適合垂直：金融、政府、醫療某些不接受 SaaS IdP 的場景；以及預算敏感、員工數中等、SRE 量能足以接 24/7 on-call 的組織。

## 本章目標

讀完本頁、讀者能判斷：

1. Keycloak 該承擔哪一段 identity 控制（SSO / MFA / federation / brokering）、哪一段該交給雲端 IAM 或下游應用
2. 自管 IdP 的最低運維基線（HA、DB DR、cert / signing key rotation、CVE cadence、SIEM 接點）
3. Realm / Client / User Federation / Identity Broker / Authentication Flow / SPI 各自的決策時機與陷阱
4. 何時用 Keycloak、何時改走 SaaS（Okta / Auth0）或其他 OSS（Authentik / Zitadel）

## 最短判讀路徑

判斷 Keycloak 部署是否健康、最少看 SaaS IdP 的四件事加上自管特有的四個維度：

- **誰能做什麼**：master realm admin 的人數、是否走 access request workflow、admin console 是否限 IP / device trust、是否強制 [phishing-resistant 認證](/backend/knowledge-cards/authentication/)
- **憑證在哪裡**：client secret 是否走 [secret management](/backend/knowledge-cards/secret-management/)、realm signing key 的 rotation 排程、admin token 的 TTL
- **入口如何暴露**：哪些 realm 對外、reverse proxy / Ingress 是否做 rate limit、admin console（/auth/admin）是否限內網或 zero trust
- **證據是否可回查**：Event Listener SPI 是否接 SIEM、admin event 跟 login event 是否分流、保留期是否符合稽核
- **DB 健康**：PostgreSQL / MySQL 是否跨 AZ、是否有 PITR、是否做過 restore 演練（不是只有備份成功訊息）
- **Cert lifecycle**：TLS cert 與 realm signing key 各自的 rotation 排程、是否走 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/) 自動化
- **HA topology**：Keycloak cluster 是否多節點、Infinispan cache 是否跨 AZ、單節點重啟是否會踢掉所有 session
- **Upgrade cadence**：Keycloak 每年 major release、CVE patch 是否能在 SLA 內上、是否有 staging 跑 DB migration

八個維度任一缺失、都是自管 IdP 常見事故的入口。

## 日常操作與決策形狀

**Realm 設計**：Realm 是 Keycloak 的隔離邊界、每個 realm 有獨立的 user store、client、role、signing key。multi-tenancy 走 realm 是正確選擇、但 *master realm 能管所有 realm*、master realm 的 admin compromise = 全公司 IdP compromise。把 master realm 鎖在內網、operational realm 才對外、是基本姿勢。

**Client 註冊與 secret**：每個應用是一個 client、confidential client 有 secret、public client（SPA / mobile）走 PKCE 不存 secret。client secret 不存 source code、走 [secret management](/backend/knowledge-cards/secret-management/) 注入。client 數量爆炸時要設 naming convention 跟 ownership 標記、不然 stale client 會堆積。

**User Federation**：把既有 LDAP / Active Directory 接進 Keycloak、user 還是住在原 directory、Keycloak 做 protocol 翻譯（LDAP → OIDC / SAML）。這是 Keycloak 強項之一 — 不需要 user migration、漸進接入。陷阱是 LDAP 連線健康 = IdP 健康、LDAP 慢 = 全公司 login 慢。

**Identity Brokering**：把外部 IdP（Google、Microsoft、其他 SAML / OIDC provider）federate 進來、Keycloak 當中介。B2B 合作常見模式 — partner 用自己的 IdP、不在我的 user store 開帳號。決策點是 *trust mapping*：外部 claim 怎麼對應到內部 role、外部 IdP 的 MFA 狀態怎麼信任。

**Authentication Flow**：Keycloak 把 login / registration / reset password 做成可編輯的 flow DAG、可以插入自訂 step。這是 Keycloak 跟 SaaS IdP 最大差異點之一 — 想要 [step-up](/backend/knowledge-cards/step-up-authentication/) MFA、device fingerprint、risk-based 判斷都可以自己接。雙面刃是 *自訂 flow 容易留漏洞*：跳過必要步驟、condition 寫錯讓 MFA 變可選、custom Authenticator SPI 沒處理 race condition。

**Theme / 客製 UI**：Keycloak 支援 theme override、可以改 login page HTML / CSS / JS。custom JS 在 login page = 自己注入 XSS 風險 — theme 寫進去之後就是 IdP 本體的攻擊面、不是普通網頁。CSP 跟 input sanitization 要當成 IdP 安全規範看待。

**Event Listener / Audit**：Keycloak 預設只把 event 寫進 DB、UI 上能查、但 *不會自動推到外部 SIEM*。生產環境必須接 Event Listener SPI（內建 jboss-logging、或自寫 Kafka / file listener）把 admin event 跟 login event 推進 SIEM。沒接的話 audit trail 只在 IdP 本機、IdP 出事就拿不到 evidence。

**Exception / break-glass**：master realm 留至少 2 個 break-glass admin、credential 離線存、走獨立 MFA（hardware key）。Keycloak cluster 整個失聯時、用 break-glass 直連 DB / 直連單一節點救回。

## 核心取捨表

| 取捨維度       | Keycloak（自管 OSS）                            | Okta（SaaS）                      | Auth0（SaaS / B2C）                     | Authentik / Zitadel（其他 OSS）      |
| -------------- | ----------------------------------------------- | --------------------------------- | --------------------------------------- | ------------------------------------ |
| 控制面責任     | 自己跑 issuer / signing / HA / DB / upgrade     | Okta 託管                         | Auth0 託管                              | 自己跑、但社群規模小於 Keycloak      |
| 客製化深度     | 高 — Authenticator SPI / theme / event listener | 中 — Workflows / Hooks、限定範圍  | 高 — Actions（JS hook）                 | 中 — Authentik flow 視覺化、彈性中等 |
| 第三方信任成本 | 低 — 自管、自己承擔運維                         | 高 — 供應商事件直接波及           | 高 — 同 Okta（同集團）                  | 低 — 自管                            |
| 運維成本       | 高 — HA、DR、cert、DB、CVE 都自管               | 低 — SaaS                         | 低 — SaaS                               | 高 — 同 Keycloak、生態系更小         |
| 適合場景       | 資料主權、預算敏感、需深度客製、有 SRE 量能     | 多雲、大量 SaaS、lifecycle 自動化 | B2C、消費者 identity、developer-centric | 規模小、Keycloak 太重、想要更現代 UI |
| 退場成本       | 中 — 自己掌握資料、protocol 標準可遷移          | 高 — SAML / SCIM 接線散在數百 app | 高 — Actions / Rules 客製綁定深         | 中 — 同 Keycloak                     |

選 Keycloak 的核心訴求：*資料主權 + 預算控制 + 客製 flow 需求*、且有 SRE 團隊能 24/7 on-call、能接受自管的運維重量。團隊小於 50 人沒 SRE 量能、應用主要在 SaaS（pre-built integration 用不上 Keycloak 強項）、需要快速接 7000+ SaaS app — 都該回頭看 Okta / Auth0。

## 進階主題

**User Federation 跟 LDAP 整合**：企業環境常見「Active Directory 是 user source of truth、Keycloak 做 protocol 層」。注意 LDAP 同步策略（read-only / writable / import）、LDAP 健康直接影響 IdP 可用性、LDAP timeout 要設嚴格避免 login 卡住整個 cluster。

**Identity Brokering 跟外部 IdP**：把 Google / Microsoft / 其他 SAML IdP federate 進來、外部 user 進來時 Keycloak 自動建 link。trust mapping 是關鍵 — 外部 IdP 宣稱「這個 user 已 MFA」、要不要信？外部 group claim 怎麼對應到內部 role？沒有預設答案、要用 [authorization](/backend/knowledge-cards/authorization/) 邊界決定。

**Fine-Grained Authorization（UMA / Authorization Services）**：Keycloak 內建 policy engine、可以做 resource-level 授權（不只是 role-based）。適合需要中央化 policy decision 的場景、但會把應用的授權邏輯綁進 Keycloak、退場成本變高。多數場景應該把 authorization 留在應用內、Keycloak 只做 authentication + role token 發行。

**Custom Authenticator SPI**：用 Java 寫自訂 authenticator、插進 Authentication Flow。能做 step-up MFA、device posture、risk score 判斷。陷阱是 SPI 程式碼就是 IdP 本體的一部分、bug = IdP 漏洞、必須走完整 code review + 安全測試流程、不能當普通 feature 開發。

**Realm signing key rotation**：每個 realm 有自己的 RSA / EC signing key、用來簽 ID token / SAML assertion。rotation 必須跟下游 client 協調（key rollover 期間 client 要能接受新舊 key）、否則 rotation 當天全公司 login 失敗。分域分批是必做的、參考 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)。

## 排錯與失敗快速判讀

- **DB 是 SPOF**：Keycloak 所有 state 在 PostgreSQL / MySQL、DB 出事 = IdP 停 = 全公司 SSO 停。跨 AZ replication + PITR + 季度 restore 演練、不是 nice-to-have
- **Cert / signing key 過期**：自管 IdP 最常見事故、TLS cert 過期擋對外 endpoint、realm signing key 過期讓所有 token 變無效。走 [Certificate Rotation](/backend/knowledge-cards/certificate-rotation-renewal/) 自動化、過期前 30 天 alert
- **Cluster split-brain**：Infinispan cache 跨節點同步、網路分區時 session 狀態不一致、user 看起來登入但下一個 request 又被踢出。HA topology 設計要考慮 cache mode（distributed vs replicated）、network 健康監控要 alert split-brain
- **Major upgrade 卡 DB migration**：每年 major release 帶 schema migration、staging 沒跑過就 production 升級 = 數小時 downtime。upgrade plan 包含 rollback DB snapshot + staging full rehearsal
- **Custom theme / Authenticator 留漏洞**：theme JS 引入 XSS、custom Authenticator 跳過 MFA、SPI 沒處理 race condition。把 IdP 客製當成 [supply chain](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 看待、走 code review + 安全測試
- **Event 沒進 SIEM**：預設只在 Keycloak DB、IdP 出事就拿不到 evidence。Event Listener SPI 接 Kafka / file / SIEM、admin event 跟 login event 各自接 [alert runbook](/backend/knowledge-cards/alert-runbook/)
- **Master realm admin 過多**：日常工作不該用 master realm admin、應該在 operational realm 開有限權限 admin。master realm 是 single point of compromise

## 何時改走其他服務

| 需求形狀                        | 改走                                                                                                                                                                                                                     |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 不想自管、要 SaaS IdP           | [Okta](/backend/07-security-data-protection/vendors/okta/) / [Auth0](/backend/07-security-data-protection/vendors/auth0/)                                                                                                |
| AWS-only 員工 SSO               | [AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)                                                                                                                         |
| Cloud resource 權限             | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/) |
| 小團隊、Keycloak 太重           | Authentik / Zitadel / Ory Hydra（更輕量 OSS、生態系較小）                                                                                                                                                                |
| 事件偵測（不只 Keycloak event） | 04 SIEM / detection 工具（[04 observability](/backend/04-observability/) 跟 07 SIEM 章節）                                                                                                                               |
| Secret / signing key 治理       | [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)                                                                                                            |

## 不在本頁內的主題

- Keycloak 完整 SAML / OIDC 規格細節、SPI Java API 文件
- Red Hat build of Keycloak 商業支援的差異與授權細節
- Keycloak Operator（Kubernetes deployment）的逐步部署教學
- LDAP / Active Directory 各種 schema 對應規格

## 案例回寫

Keycloak 沒有直接的廠商級公開事件（OSS 沒有 vendor incident 的對應形態）、自管 IdP 的失效模式以下分兩類整理：跨 vendor 共通的 *同構失效* 用既有 case 對照、自管 IdP *特有* 的失效情境補敘事說明、避免案例表變成「同一個 frame 拼四個 case slug」。

**對照引用（跨 vendor 同構失效）**：

| 案例                                                                                                                                | 跟 Keycloak 的關係                                                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| [Azure AD Identity Control Plane 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)            | 對所有自管 IdP 的啟示：IdP 控制面故障會外溢到下游所有依賴 SSO 的服務、降級策略（local fallback、cached session）必須事先設計 |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) | Keycloak realm signing key rotation 必須分域分批、一次 rotate 全部 realm = 全公司 login 同時失敗                             |
| [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)                 | 純 push MFA 抗不過 fatigue、Keycloak 自訂 Authentication Flow 應該強制高風險操作走 phishing-resistant factor                 |

**自管 IdP 特有的失效情境**（沒有對應公開 vendor case、來自自管運維常見事故樣態）：

- **Cert 過期讓全公司 SSO 卡死**：Keycloak signing cert / TLS cert / 後端 DB cert 都自己管、任何一張過期 = login 全停。Okta / Auth0 客戶不會遇到這個失效面（vendor 自己 rotate）— 自管組織必須有 cert lifecycle monitoring（Prometheus exporter + alert）+ 季度 rotate rehearsal、不能等 Let's Encrypt / 公司 PKI 發過期通知才動
- **Major upgrade 卡 DB migration 變數小時 downtime**：Keycloak 每年 major release 帶 schema migration、若 staging 沒 full rehearsal 就 production 升級、可能遇到 migration 比預期慢 5-10 倍、整個維護視窗炸掉。對照 Okta / Auth0：vendor 自己升、客戶感知是 minutes-level、不是 hours-level
- **Realm scope 在小規模時用法跟大規模衝突**：[Contrast: Identity Governance by Scale](/backend/07-security-data-protection/cases/contrast-identity-governance-by-scale/) 揭示不同規模治理模式差異 — 小團隊用單一 realm 順、團隊長大後該拆 realm 卻沒拆、最後 admin compromise blast radius 變整個組織。Keycloak 比 SaaS IdP 更容易踩到、因為 realm 拆分要自己決定時機、沒 vendor 推使用者升級 tier
- **DB 是 SPOF、自管沒做好 = SSO 跟 DB 一起死**：Keycloak 用 PostgreSQL / MySQL 存 user / session / signing key、DB 出事 = IdP 停。跨 AZ HA + 跨 region DR + 季度 failover 演練是硬性要求、不是 nice-to-have；SaaS IdP 客戶不會遇到這個層次的失效面

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[Okta vendor](/backend/07-security-data-protection/vendors/okta/)、[Auth0 vendor](/backend/07-security-data-protection/vendors/auth0/)、[AWS IAM Identity Center](/backend/07-security-data-protection/vendors/aws-iam-identity-center/)
- 下游：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)（Keycloak 之後的 cloud resource permission 層）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（自管 IdP 事件如何 routing 進 IR 流程）
- 官方：[Keycloak Documentation](https://www.keycloak.org/documentation)
