---
title: "Teleport"
date: 2026-05-18
description: "Identity-Aware Proxy + PAM、SSH / DB / K8s / Desktop session 統一 short-lived cert + session recording + JIT、跟 Okta / Vault 互補"
weight: 12
tags: ["backend", "security", "vendor", "teleport", "pam", "zero-trust", "session-recording"]
---

Teleport 是 *Identity-Aware Proxy + PAM*（Privileged Access Management）、把 SSH / Database / Kubernetes / Windows Desktop / Cloud API / 內部 web app 的 *privileged session* 統一收到一個 zero-trust 入口、所有 session 改走 *short-lived cert + per-session MFA + 全程錄影*、取代傳統「long-lived SSH key + bastion + 手動 audit」。它跟 [Okta](/backend/07-security-data-protection/vendors/okta/) 是兩層職責 — Okta 認證 *人是誰*、Teleport 控制 *拿到身份後 privileged session 怎麼進、留什麼證據*；典型部署是 *Okta SSO into Teleport、Teleport proxies SSH/DB/K8s session*。

## 服務定位

Teleport 的核心定位是 *infrastructure access plane*、不是 IdP、不是 secret store、也不是 network mesh。它的責任是 *把 admin / engineer 對 production 資源的 session 通通走可治理的入口*、每個 session 有 *identity-bound short-lived cert*、有 *audit log*、有 *錄影*、有 *MFA gate*。比較對象：

- 跟 [Okta](/backend/07-security-data-protection/vendors/okta/) / Azure AD 等 IdP 比、Teleport 不取代 SSO、而是 *把 SSO identity 帶到 infrastructure layer* — Okta 給 user identity + group、Teleport 把這個 identity 翻譯成 SSH cert / DB cert / K8s cert
- 跟傳統 bastion + SSH key 比、Teleport 把 *long-lived SSH key* 換成 *short-lived cert*（預設 TTL 數小時、過期自動失效）、把 *看不到的 session* 換成 *全程錄影 + searchable audit log*
- 跟 HashiCorp Boundary 比、Teleport 走 *protocol-aware proxy*（懂 SSH / PostgreSQL / Kubernetes API 協議、可以 decode keystroke 跟 query）、Boundary 走 *generic TCP proxy*（協議無感、不能錄 keystroke 但部署更輕）
- 跟 Tailscale SSH 比、Tailscale 是 *network mesh 加 SSH*、適合小團隊 flat network；Teleport 是 *PAM + 多協議 + 跨環境 audit*、適合需要 SOC handoff 的環境
- 跟 [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-waf/) 比、Cloudflare Access 是 *application-layer ZTNA*（內部 web app / API 用）、Teleport 是 *infrastructure-layer ZTNA*（SSH / DB / K8s 用）、兩者互補

關鍵張力：*PAM 的覆蓋完整度* ↔ *operator 摩擦*。Teleport 開越多（per-session MFA、Access Request 要 approval、Device Trust 強制企業裝置）、helpdesk SE 那種「拿到密碼直接進 prod」的 blast radius 越小、但 on-call engineer 在凌晨三點修事故時的摩擦也越大。要根據 *資源敏感度分層* 設定、不是一刀切。

## 本章目標

讀完本頁、讀者能判斷：

1. Teleport 在 access stack 中承擔哪一段（infrastructure session）、哪些不屬於它（user identity 屬 Okta、long-lived service secret 屬 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、application access 可用 Cloudflare Access）
2. Cluster / Proxy / Auth Service / Node 拓樸的部署選擇（Cloud SaaS vs Self-hosted、Trusted Cluster 跨環境）
3. Roles + Access Requests + Per-session MFA + Session Recording 四件套的工程化設定（誰能 approve、TTL 多長、錄影存哪）
4. 何時用 Teleport、何時走 Boundary / Tailscale SSH / Cloudflare Access 的取捨

## 最短判讀路徑

判斷 Teleport deployment 是否健康、最少看四件事：

- **是否還有 long-lived credential 旁路**：production host 是否仍接受 `~/.ssh/authorized_keys` 的長期 key、DB 是否仍有 shared admin password、K8s kubeconfig 是否還在 engineer laptop 永存 — Teleport 收編失敗的最大訊號是 *存在 bypass Teleport 的捷徑*
- **Per-session MFA 是否對 sensitive resource 強制**：prod SSH / prod DB / payment system 進 session 時是否每次都 re-MFA、不是「早上登入一次後 8 小時都通行」、role 設定有沒有 `require_session_mfa: true`
- **Access Request 的 standing privilege 是否收零**：日常 role 是否只有 read-only、所有 write / admin operation 是否走 *Access Request* + approver gate + TTL、approver 是否 SOC / SRE on-call 而非任意 lead
- **Session Recording 是否真的可回查**：SSH / K8s / DB session 錄影是否落地 S3 / GCS、是否可在 audit log 透過 user / time / resource 三軸搜尋並回放、recording retention 是否符合合規（金融通常 7 年）

四件事任一缺失、就回到 [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/) 補設定。最容易踩的是第三點 — Teleport 裝了但日常 role 仍給 standing admin、Access Request 變裝飾、helpdesk SE 場景的 mitigation 等於沒上。

## 日常操作與決策形狀

**Cluster + Proxy + Auth Service 拓樸**：Teleport cluster 由三個 first-class component 組成 — *Auth Service*（CA、簽 cert、存 audit log、policy decision point）、*Proxy*（user 連線入口、做 protocol translation、把 SSH / DB / K8s request 轉到 Node）、*Node*（被保護的資源、裝 Teleport agent 或走 agentless 模式）。Cloud（SaaS）把 Auth + Proxy 託管、客戶只管 Node；Self-hosted 三層都自管、適合需要 data residency / FedRAMP 的環境。

**多協議 Resource Access**：Teleport 是 *protocol-aware proxy*、不是 generic TCP tunnel — SSH Access 懂 OpenSSH、Database Access 懂 PostgreSQL / MySQL / MongoDB / Snowflake / Redis wire protocol、Kubernetes Access 懂 K8s API + RBAC impersonation、Desktop Access 懂 RDP、Application Access 懂 HTTP（包 AWS / GCP console 跟內部 web app）。協議感知的價值是 *可以錄 keystroke / query / 滑鼠移動*、可以做 *per-query approval*（DB Access 可設「DROP TABLE 要 approver」）、generic proxy 做不到。

**Roles + RBAC**：Teleport role 是 YAML 定義的 RBAC policy、控制 *誰可以連哪些 resource、用什麼 OS user、執行什麼指令、session TTL 多長、要不要 per-session MFA*。Role 跟 Okta group 透過 SAML / OIDC attribute mapping 綁定 — Okta `group=sre-prod` 自動拿到 Teleport `role=prod-ssh-readonly`、不用 Teleport 端維護 user list。

**Access Requests（JIT approval）**：standing privilege 收零的核心機制 — engineer 平常只有 read-only role、需要 write / admin 時透過 CLI / web UI 開 *Access Request*、指定 role + reason + TTL、approver 在 Slack / web 收到通知後 approve / deny、approve 後該 user 拿到該 role TTL（例如 4 小時）、過期自動 revoke。對應 [MGM 2023](/backend/07-security-data-protection/red-team/cases/identity-access/mgm-2023-identity-lateral-impact/) 的 mitigation — 即使 helpdesk SE 拿到 user 密碼、該 user 也沒有 standing admin 可用、要進 prod 必須額外開 Access Request + approver 看到 reason 異常會 deny。

**Per-session MFA**：高敏 session 強制每次連線都 re-MFA、不是登入一次後 session TTL 內都通行。role 設 `require_session_mfa: true`、user `tsh ssh prod-db-01` 時會跳 Yubikey / WebAuthn 提示、過了才連得進去。對應 [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/) 的 lesson — 即使 attacker 用 push fatigue 拿到 IdP session、要進 prod infrastructure 還會撞到第二道 MFA。

**Session Recording + Audit**：所有 SSH / K8s / DB / Desktop session 全程錄影、SSH 錄 keystroke + output、DB 錄 SQL query、K8s 錄 API call、Desktop 錄畫面。錄影預設存 Auth Service local disk、production 應該設 *sync mode* 即時寫 S3 / GCS、不要等 session 結束才上傳（attacker 結束前 wipe）。Audit log 走結構化 JSON、可 export 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / Elastic、是 SOC 的 first-class signal。

**Trusted Cluster 跨環境 federation**：dev / staging / prod 各自跑 Teleport cluster、用 *Trusted Cluster* 建立信任關係、user 從 root cluster 一次 login 就能 `tsh ssh --cluster=prod node-01`、不用每個環境各 login。設計重點是 *root cluster 是 SSO + 政策中心、leaf cluster 是各環境本地控制*、leaf 出事不會把 root identity 拖下水。

**跟 Okta / GitHub OIDC SSO 整合**：Teleport 不做 user identity、authentication 全部委派給 IdP — Okta 設 SAML app、Teleport 設 SAML connector、user `tsh login` 跳 Okta 認證後拿 Teleport short-lived cert。GitHub Actions 也可以用 OIDC token 換 Teleport cert（給 CI 用、見下方 Machine ID）、不用埋 GitHub Actions secret。

## 核心取捨表

| 取捨維度         | Teleport                                     | HashiCorp Boundary                       | Tailscale SSH                 | Cloudflare Access                    |
| ---------------- | -------------------------------------------- | ---------------------------------------- | ----------------------------- | ------------------------------------ |
| 主要 surface     | Infrastructure（SSH / DB / K8s / Desktop）   | Infrastructure（generic TCP）            | Network mesh + SSH            | Application（web app / API）         |
| 協議感知         | 強 — 懂 SSH / DB / K8s / RDP / HTTP          | 弱 — generic TCP proxy、不解協議         | 弱 — SSH 為主、其他靠 network | HTTP-only                            |
| Short-lived cert | 強 — 各協議都有專屬 cert（SSH / DB / K8s）   | 中 — 主要靠 Vault credential broker      | 中 — SSH cert by Tailscale CA | N/A（HTTP token）                    |
| Session 錄影     | 全程 keystroke / query / 畫面                | TCP-level 連線 metadata、不錄內容        | 基本 SSH log、不錄 keystroke  | HTTP request log                     |
| JIT access       | Access Request + approver + TTL              | Vault dynamic credential lease           | ACL tag、無 approver workflow | Policy + identity gate               |
| Per-session MFA  | 第一級支援、role 級別 toggle                 | 透過 Vault MFA、間接                     | 透過 Tailscale identity、間接 | App-level MFA（透過 Cloudflare）     |
| 部署模型         | Cloud SaaS / Self-hosted（含 air-gapped）    | Self-hosted（OSS）+ HCP Boundary（SaaS） | SaaS only                     | SaaS only（Cloudflare 邊緣）         |
| 計費             | Per protected resource + MAU、Cloud / Self   | 跟 Vault Enterprise 綁定                 | Per user / device             | Per user                             |
| 適合場景         | 需要 PAM + audit + JIT 的 admin session 治理 | 已是 Vault 重度使用者、generic TCP 多    | 小團隊 flat network、SSH 為主 | 內部 web app / API 走 ZTNA、非 infra |
| 退場成本         | 中 — role YAML / Trusted Cluster 設定多      | 中 — Boundary target 設定                | 低 — ACL 移植性高             | 低 — policy 簡單                     |

選 Teleport 的核心訴求：*多協議 infrastructure session* + *session recording + JIT + per-session MFA 是 SOC 必要證據* + *跨環境 federation*（dev / staging / prod / partner）+ *願意承擔 cluster 維運成本（self-hosted）或 SaaS 訂閱*。純小團隊 flat network 走 Tailscale 更輕、純內部 web app 走 Cloudflare Access 更便宜、純 Vault-driven workflow 走 Boundary 整合更順。

## 進階主題

**Machine ID — service-to-service short-lived cert**：CI / 內部 worker / cron job 也走 Teleport 拿 short-lived cert、不用埋長期 SSH key 或 DB password。Machine ID agent（`tbot`）跑在 CI runner、用 IAM role / GitHub OIDC token / Kubernetes service account 證明自己身份、Teleport 簽 short-lived SSH cert / DB cert（TTL 通常 1 小時）。對應 [SPIRE](/backend/07-security-data-protection/vendors/spire/) 的 workload identity 概念、Teleport Machine ID 是 SPIRE 在 infrastructure access surface 的對等實作。

**Device Trust — 裝置驗證**：除了 user identity + MFA、Teleport Enterprise 還可以強制 *只有企業 enrolled 裝置可以連 prod*。裝置透過 TPM / Secure Enclave 註冊 hardware-bound key、Teleport login 時驗證裝置 cert。對應 BYOD 風險 — 即使 attacker 拿到 user credential + MFA token、沒有企業裝置就連不進 prod。

**Moderated Session + Session Live View**：高敏 session 設定 *需要第二人在線 moderate*、SOC analyst 即時看 keystroke、可以 `kill session`。對應金融 / 政府的「四眼原則」合規要求。Live View 也可以給 SOC 在 incident 進行中即時看 attacker 操作（如果 attacker 不知道被監聽）。

**FedRAMP / HIPAA / PCI compliance**：Teleport Enterprise 有 FedRAMP Moderate authorization、Self-hosted 模式可部署 air-gapped 環境、audit log 滿足 HIPAA / PCI 的 access logging 要求。Cloud 版本走 SOC 2 Type II、FedRAMP 版本走 GovCloud 部署。

**跟 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) / [SPIRE](/backend/07-security-data-protection/vendors/spire/) 的職責切分**：Vault 管 *service-to-service secret*（DB password、API key、PKI CA）、SPIRE 管 *workload identity*（SVID、跨服務 mTLS）、Teleport 管 *人類 admin session + service short-lived cert（透過 Machine ID）*。三者互補不重疊 — Vault 不該直接給 engineer 拿 SSH key、SPIRE 不該管 helpdesk admin 怎麼進 prod、Teleport 不該變成長期 API key 倉庫。

## 排錯與失敗快速判讀

- **裝了 Teleport 但 engineer 還在用直接 SSH key**：production host 沒收掉 `authorized_keys`、long-lived key 旁路存在 — host onboarding 流程強制走 Teleport Node enrollment、CI 跑 `sshd_config` audit 抓 `AuthorizedKeysFile`
- **Access Request 變裝飾、approver 秒按**：approver 是同團隊 lead 沒看 reason、TTL 設 24 小時等於 standing — approver 改 SOC on-call / cross-team、TTL 預設 1-4 小時、high-impact role 強制兩人 approve
- **Per-session MFA 開了但 user 抱怨太煩**：所有 role 一刀切要 MFA — 分層：dev / staging role 只要登入 MFA、prod role 才 per-session MFA、payment / PII DB 加 moderated session
- **Session recording 沒存到 S3、attacker 結束前 wipe**：用 default async mode、recording 留在 Auth Service local — 改 *sync mode* 即時寫 S3、S3 開 object lock 防刪除
- **Trusted Cluster leaf 出事拖累 root**：leaf cluster admin 也有 root cluster 權限 — leaf 用獨立 role mapping、leaf admin 不繼承 root identity、leaf 出事只影響該環境
- **Cloud SaaS 跨區 latency 高**：team 在亞太但 Teleport Cloud 在 us-east — 選 Teleport Cloud 地區 / 改 Self-hosted 部署在自家最近 region
- **Machine ID cert TTL 短導致 CI 中途失效**：long-running job > cert TTL — 在 job 內定期 `tbot` renew、或拉長 TTL 但收緊 IAM role binding

## 何時改走其他服務

| 需求形狀                                | 改走                                                                                                                                                                        |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 純內部 web app / API access             | [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-waf/)（application-layer ZTNA）                                                                 |
| 小團隊 flat network + SSH               | Tailscale SSH（network mesh + 輕量 SSH cert）                                                                                                                               |
| 已重度使用 Vault、generic TCP 為主      | HashiCorp Boundary（跟 Vault credential broker 整合）                                                                                                                       |
| Service-to-service secret 跟 long-lived | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) / [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) |
| Workload identity / SVID                | [SPIRE](/backend/07-security-data-protection/vendors/spire/)                                                                                                                |
| 人類 SSO / IdP                          | [Okta](/backend/07-security-data-protection/vendors/okta/) / [Keycloak](/backend/07-security-data-protection/vendors/keycloak/)                                             |
| Session audit log 進 SIEM               | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)                         |

## 不在本頁內的主題

- Teleport role YAML 完整 reference、predicate language 進階用法
- Teleport Cloud vs Self-hosted 的 SLA / pricing 細節
- Teleport Connect（桌面 client app）的具體操作流程
- Air-gapped 部署的 license server 跟 update workflow
- 各協議的 wire protocol 解析（PostgreSQL / MySQL session 怎麼被 decode）

## 案例回寫

Teleport 沒有 vendor-level 公開事故、但 07 案例庫的 identity / access 系列都是 PAM 設計的對照：

| 案例                                                                                                                                      | 跟 Teleport 的關係（對照啟示）                                                                                                                                                                     |
| ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [MGM 2023 Identity Lateral Impact](/backend/07-security-data-protection/red-team/cases/identity-access/mgm-2023-identity-lateral-impact/) | helpdesk SE 拿到 reset 密碼後直接進 prod admin — Teleport JIT Access Request + per-session MFA 是 first-class mitigation、standing access 收零後 SE 拿到密碼也進不了 prod                          |
| [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)                       | push-based MFA fail 後 attacker 拿到 standing internal tool access — Teleport per-session MFA 是第二道 gate（即使 IdP session 被劫、進 prod infra 還要 re-MFA）+ session recording 給 SOC 事後重建 |
| [Okta Support System 2023](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)                                 | IdP 端 support tool compromise 後 attacker 拿到客戶 session token — 客戶側 Teleport audit log 仍能看到「異常 source IP / device 進 SSH session」、是 IdP 失守時的補位偵測層                        |

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)
- 平行：HashiCorp Boundary / Tailscale SSH / [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-waf/)
- 互補：[Okta](/backend/07-security-data-protection/vendors/okta/)（IdP、user identity）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（service secret）、[SPIRE](/backend/07-security-data-protection/vendors/spire/)（workload identity）
- 偵測：[Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)（session audit log 入 SIEM）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（compromise session 走 IR workflow）
- 官方：[Teleport Documentation](https://goteleport.com/docs/)
