---
title: "HashiCorp Boundary"
date: 2026-05-18
description: "Identity-based access broker、跟 Vault 同生態組合（Boundary 控連線 / Vault 給 credential）、Multi-hop Worker 跨網路分段"
weight: 13
tags: ["backend", "security", "vendor", "boundary", "pam", "zero-trust", "hashicorp"]
---

HashiCorp Boundary 是 *identity-based access broker*、把「使用者要連到某個內部資源」這件事拆成 *identity 驗證* + *target 授權* + *動態 credential 注入* 三段、由 Boundary 統一仲介。它跟 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 同生態、設計上預期兩者組合：*Boundary 控制誰能連到哪個資源、Vault 提供連線當下的 short-lived credential*。單獨用 Boundary 而不接 Vault、會失去它最大的價值。

## 服務定位

Boundary 的核心定位是 *連線層級的存取仲介*、不是傳統的 bastion host、也不是 identity-aware proxy。它把 *連線發起權* 收回控制面、user 不需要直接拿到 SSH key / DB password / cloud token、只需要對 Boundary 認證、由 Boundary 把 *target 資源的網路位置* + *Vault 動態簽發的 credential* 在 session 開始時注入連線。

跟 [Teleport](/backend/07-security-data-protection/vendors/teleport/) 比、Boundary 走 *network broker + dynamic credential injection*、Teleport 走 *identity-aware proxy + session recording*。Teleport 是 *看見每一個指令、可重播* 的 PAM；Boundary 是 *不存 credential、不錄影、靠 Vault short-lived token 來控制 blast radius*。兩者解的是同一類問題（內部資源存取治理）、但工程取捨完全不同 — Boundary 把「攻擊者拿到 credential 也只有 minutes-level 有效期」當主要防線、Teleport 把「全部 session 留下不可否認證據」當主要防線。

跟 [Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/) 比、Tailscale 走 mesh network + SSH-only、無 credential 仲介、無 dynamic injection；Boundary 走 broker 模式、支援 SSH / RDP / DB / TCP / HTTP 等多協議、且 credential 從 Vault 拉。跟 [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/) 比、Cloudflare 走 *Zero Trust portal + identity-aware reverse proxy*、是 HTTP-first；Boundary 是 *protocol-agnostic broker*、原生支援非 HTTP 協議（DB / SSH / RDP）。

關鍵張力：*Boundary + Vault 組合的工程複雜度* ↔ *不靠 session recording 的審計可信度*。已用 HashiCorp 生態（Terraform + Vault + Consul）的組織、Boundary 是 *最後一塊拼圖*；沒用 Vault 的組織用 Boundary 等於只剩一個 bastion 的弱化版、不如直接走 Teleport。合規強要求 keystroke audit 的場域、Boundary 預設不錄 session、要走 Enterprise add-on 才有、不如 Teleport first-class。

## 本章目標

讀完本頁、讀者能判斷：

1. Boundary 在 PAM stack 中承擔哪一段（broker / target / session）、哪些要外接（Vault 給 credential、IdP 給 auth、Enterprise add-on 給 session recording）
2. Controller + Worker + Multi-hop 拓樸怎麼對應實際網路分段（DMZ / internal / restricted subnet）
3. Vault Credential Library 怎麼設計、誰負責 host catalog、role / scope 怎麼劃
4. 何時用 Boundary、何時改走 Teleport / Tailscale SSH / Cloudflare Access 的取捨

## 最短判讀路徑

判斷 Boundary deployment 是否健康、最少看四件事：

- **是否真的接 Vault**：Credential Library 是否從 Vault 拉 dynamic credential（DB / SSH cert / cloud token）、session 結束是否自動 revoke、還是仍有 static credential 存在 Boundary 或人手裡
- **Scope 結構是否反映組織邊界**：Global → Org → Project 的三層 scope、Org 對應 BU / tenant、Project 對應應用或環境；role / grant 是否按 Project 切、還是全部塞 Global scope 變共享密碼
- **Worker 拓樸是否反映網路分段**：Controller 在 control plane、Worker 在每個網路 segment（DMZ / internal / restricted DB subnet）、Multi-hop 是否走 segment-aware routing、還是把所有 worker 塞同一個 VPC
- **Auth Method 是不是 IdP-backed**：OIDC（[Okta](/backend/07-security-data-protection/vendors/okta/) / Azure AD / Google）/ LDAP / Password — production 應該走 OIDC、Password auth method 只該存在於 break-glass

四件事任一缺失、就是 [Privileged Access and Just-in-Time Authority](/backend/07-security-data-protection/blue-team/) 邊界的待補項目。

## 日常操作與決策形狀

**Controller + Worker 拓樸**：Controller 負責 control plane（auth、policy、session 管理、API endpoint）、Worker 負責 data plane（實際代理連線到 target）。Controller 通常 cluster 部署（3 個以上、HA）、Worker 按網路 segment 分散部署。Controller 從不直接連 target — user 跟 Controller 認證、Controller 告訴 user 走哪個 Worker、Worker 才實際代理連線。

**Target + Host Set + Host Catalog**：Target 是 user 看到的「可連對象」抽象（例如 `prod-db-cluster`）、Host Set 是 Target 對應的實際 host 集合、Host Catalog 是 host 的來源（static list 或從 cloud auto-discover）。Dynamic Host Catalog 可以從 AWS / Azure / GCP 用 tag 自動 enroll host、不需要手動維護 host list — 例如 `tag:role=prod-db` 的 EC2 自動進 `prod-db-cluster` Target。

**Credential Library（Vault 整合）**：Boundary 不存 credential、靠 Credential Library 從 Vault 拉。設計支援三種：*Vault Generic*（拉任意 Vault secret path）、*Vault SSH Certificate*（拉 Vault SSH CA 簽發的 short-lived cert）、*Vault Database*（拉 Vault Database Secret Engine 簽發的 DB user / password）。session 開始時 Boundary 拉 credential、注入連線、session 結束時 Vault 自動 revoke。這是 Boundary 的核心價值 — 沒接 Vault 等於丟掉 dynamic credential rotation 這個最大賣點。

**Auth Method**：支援 OIDC（OAuth2 / OpenID Connect、給 [Okta](/backend/07-security-data-protection/vendors/okta/) / Azure AD / Google）、LDAP（給 internal directory）、Password（給 break-glass）。Production 預設走 OIDC、跟 IdP 同源、user lifecycle 隨 IdP 變動（離職 IdP 鎖、Boundary 自動失效）。Password auth method 只該存在於 break-glass account、密碼進 Vault、單獨 audit。

**Role + Grant + Scope**：Boundary 的權限模型是 *scope-bound role*、role 屬於某個 scope（Global / Org / Project）、grant 是 role 內的具體權限（例如 `target=<id>;actions=authorize-session`）。Scope 三層分別對應：*Global* — platform-level admin、*Org* — 某 BU 或 tenant、*Project* — 應用或環境（prod / staging / dev）。設計時把 role 按 Project 切、不要全部塞 Global scope 變共享密碼。

**Session 生命週期**：user 對 Boundary 認證（OIDC）→ list authorized target → 對某 target 發起 `authorize-session`、Boundary 從 Credential Library 拉 credential → user 透過 Boundary CLI / Desktop / SDK 連線、實際走 Worker 代理 → session 有 *max duration*（預設 8 小時、可調短）、過期自動斷 + Vault credential revoke。session metadata（誰、何時、target、worker、duration）一律 audit log。

**Multi-hop Worker**：跨網路 segment（例如 user 在 corp 網、target 在 DMZ → internal → restricted DB subnet）時、Boundary 支援 worker chain — corp Worker 連到 DMZ Worker、DMZ Worker 連到 internal Worker、internal Worker 連到 DB。每段 worker 只看得到下一段、不需要 VPN trunk 把整個網路打通。這是 Boundary 相對 Teleport / Tailscale 的網路工程優勢、特別適合金融 / 政府 / 製造業的多層網路分段。

## 核心取捨表

| 取捨維度          | HashiCorp Boundary                               | Teleport                                  | Tailscale SSH                       | Cloudflare Access                             |
| ----------------- | ------------------------------------------------ | ----------------------------------------- | ----------------------------------- | --------------------------------------------- |
| 核心模式          | Network broker + dynamic credential injection    | Identity-aware proxy + session recording  | Mesh VPN + SSH CA                   | Zero Trust portal + identity-aware proxy      |
| Credential 處理   | 從 Vault 拉 short-lived、不存                    | Teleport CA 簽發 short-lived cert         | Tailscale SSH CA 簽發               | OAuth token、無 SSH credential 處理           |
| Session recording | Enterprise add-on（2023+、非 first-class）       | First-class（SSH / kubectl / DB 都錄）    | 無                                  | 無                                            |
| 協議支援          | SSH / RDP / DB（Postgres / MySQL）/ TCP / HTTP   | SSH / kubectl / DB / RDP / Web Apps       | SSH only（mesh 內任意 TCP）         | HTTP / SSH（透過 cloudflared）/ RDP           |
| 部署模型          | Self-hosted (OSS / Enterprise) / HCP (HashiCorp) | Self-hosted / Teleport Cloud              | SaaS only                           | SaaS only                                     |
| 網路拓樸          | Controller + Worker、Multi-hop 跨 segment 友善   | Proxy + Agent、單層 proxy                 | Mesh、所有節點對等                  | Cloudflare edge + cloudflared tunnel          |
| IdP 整合          | OIDC / LDAP / Password                           | OIDC / SAML / GitHub                      | OIDC（Okta / Google / Azure）       | OIDC / SAML / 內建 IdP                        |
| 跟其他 vendor 鎖  | 預設假設用 Vault、單獨用價值有限                 | 獨立完整、不依賴特定 secret store         | 獨立、Tailscale 生態                | 獨立、Cloudflare 生態                         |
| 適合場景          | 已用 HashiCorp 生態 + 多協議 + 多層網路分段      | 強合規 + session audit + kubectl-heavy    | 小團隊 + SSH-only + 不要 PAM 複雜度 | Cloud-native + Zero Trust portal + HTTP-first |
| 退場成本          | 中 — Vault 整合複雜、target / role / scope 量多  | 中 — Teleport-specific config + recording | 低 — Tailscale 拆掉就回 plain SSH   | 低 — Cloudflare 拆掉就回 origin               |

選 Boundary 的核心訴求：*已用 HashiCorp 生態（特別是 Vault）* + *多協議內部資源（不只 SSH、還有 DB / RDP / TCP）* + *多層網路分段需要 Multi-hop*、可以接受 session recording 不是 first-class。沒用 Vault 的組織、Boundary 失去最大價值、應該直接走 Teleport。

## 進階主題

**Multi-hop Worker 跟網路分段**：金融 / 政府常見三段網路（corp → DMZ → restricted）、傳統做法是打 VPN trunk 把整個網路扁平化、accept 大 blast radius。Boundary 用 worker chain 反向 — 每個 segment 部署一個 worker、worker 之間用 mTLS 認證、user 只進 corp worker、後面 hop 由 Boundary control plane 編排。每段 worker 不知道後一段的 target 細節、只知道下一段 worker 的位置。配對 [Segmentation and Blast Radius Containment](/backend/07-security-data-protection/blue-team/) 的章節原則。

**Dynamic Host Catalog**：手動維護 host list 在 cloud-native 環境會壞 — auto-scaling group 起一台新 EC2、沒人去 Boundary 加 target。Dynamic Host Catalog 配 cloud provider plugin（AWS / Azure / GCP）、用 tag 自動 enroll：例如 `tag:env=prod tag:role=app` 的 EC2 自動進 `prod-app` Target、scale-down 也自動移除。這配 IaC（[Terraform](/backend/05-deployment-platform/vendors/terraform/) 管 tag）是 HashiCorp 生態一致性的核心賣點。

**Session Recording（Enterprise 才有）**：2023+ Boundary Enterprise 引入 session recording、支援 SSH 跟 RDP 的 keystroke + screen recording、output 加密存到 S3 / Azure Blob、metadata 走 audit。OSS Community Edition 沒有、只記 session metadata（who / when / what target / how long）。組織要 session recording 但又要 Boundary、要評估 Enterprise license cost vs Teleport license cost — 通常 Teleport 在 session recording 場景成本效益更好。

**Vault credential brokering 設計**：Boundary 連 Vault 的設計支援多種 secret engine — Database（Postgres / MySQL / Redis 等、簽 short-lived DB user）、SSH Certificate（簽 short-lived SSH cert）、AWS / Azure / GCP（簽 cloud STS token）、KV v2（拉靜態 secret、不推薦）。Production 預設用 dynamic engine、不要用 KV v2 — 靜態 secret 失去 Boundary 最大價值。Vault namespace / policy 設計要對齊 Boundary scope、否則 cross-scope credential 暴露變大問題。

**HCP Boundary（HashiCorp Cloud Platform）**：HashiCorp 託管的 SaaS 版、Controller 由 HashiCorp 管、user 只部署 Worker 到自己網路。優點是省去 Controller HA / upgrade 維運；缺點是 control plane 在 HashiCorp 雲、合規敏感場域要評估 data residency。SMB / 中型團隊適合走 HCP、大型 enterprise 通常 Self-hosted。

## 排錯與失敗快速判讀

- **Session 拿到 credential 但 target 連不上**：Worker 跟 target 之間網路不通、或 Worker 沒部署到 target 所在 segment — 檢查 Worker tag 跟 Target worker_filter、用 `boundary workers list` 確認 Worker 健康
- **OIDC login 失敗**：IdP redirect URI 沒對齊、或 IdP signing key 過期 — 對照 [Microsoft Storm-0558](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) 的啟示、Boundary OIDC auth method 依賴上游 IdP signing key、IdP 端 key rotation 不對 Boundary 通知會整批 session 認不過
- **Vault credential 拉不到 / 過期太快**：Boundary 服務帳戶在 Vault 的 policy 沒給 `creds/<role>` 權限、或 Vault 簽的 credential TTL 短於 session max duration — 對齊 TTL、加 Vault telemetry alert credential issuance 失敗
- **Multi-hop 連線中斷**：中間 hop 的 Worker 健康但 connection drop — 通常是中間 segment 的 firewall idle timeout 短於 session activity gap、調 firewall 或在 client 端開 keepalive
- **Target 量爆炸 / role 管不動**：所有 target 塞 Global scope、role 量線性漲 — 重構 scope 結構、按 Org / Project 切、role 從 Global 移到 Project 層
- **Dynamic Host Catalog 漏 host**：cloud tag 沒打 / IAM 沒給 Boundary 描述權限 — 檢查 cloud plugin 的 service account permission、加 catalog sync error 的 alert
- **OSS Community 升 Enterprise 才發現缺 feature**：選 OSS 之前沒確認需求 — session recording / SAML / 高級 RBAC / multi-region HA 都是 Enterprise 才有、評估時就要列清楚

## 何時改走其他服務

| 需求形狀                                     | 改走                                                                                                |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 強合規要 session recording / keystroke audit | [Teleport](/backend/07-security-data-protection/vendors/teleport/)                                  |
| 小團隊 + SSH-only + 不要 PAM 複雜度          | [Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/)                        |
| Cloud-native + Zero Trust portal             | [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/)                |
| Kubernetes kubectl-first PAM                 | [Teleport](/backend/07-security-data-protection/vendors/teleport/)（kubectl proxy first-class）     |
| Secret storage / rotation 核心               | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（Boundary 的搭檔） |
| IdP / SSO 治理                               | [Okta](/backend/07-security-data-protection/vendors/okta/) / Azure AD                               |
| Cloud IAM role assumption                    | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / 對應雲                           |
| 事故路由                                     | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                    |

## 不在本頁內的主題

- Boundary CLI / Desktop / Terraform provider 的完整指令 reference
- HCP Boundary 跟 Self-hosted 的功能對照細節（HashiCorp 官方有 matrix）
- Vault 內部的 secret engine 設計（在 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 頁）
- OIDC / SAML 協議本身的攻擊面（[2.3 SSO 攻擊面](/backend/07-security-data-protection/identity-access-boundary/)）
- Network segmentation 的整體設計（[Segmentation and Blast Radius Containment](/backend/07-security-data-protection/blue-team/)）

## 案例回寫

Boundary 在 07 案例庫沒有直接 vendor-level 事件、但 PAM / credential rotation / IdP 相關 case 都是它的設計取捨對照：

| 案例                                                                                                                                                       | 跟 Boundary 的關係（對照啟示）                                                                                                                                                                                                     |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)                        | Boundary + Vault Credential Library 直接解此 case 的 scope map 問題 — 每 session 拿 Vault 簽的 short-lived credential、session 結束自動 revoke、不需要 batch rotation、scope map 由 Vault policy + Boundary role 雙向約束          |
| [MGM 2023 Identity Lateral Impact](/backend/07-security-data-protection/red-team/cases/identity-access/mgm-2023-identity-lateral-impact/)                  | helpdesk 走 SE 拿到 reset 後的密碼、但 Boundary 仍要求 session 開始時拿 Vault dynamic credential、attacker 在 Vault policy 端被擋；前提是 Boundary OIDC auth method 不依賴可被 SE 重置的 password、IdP 要走 phishing-resistant MFA |
| [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | Boundary OIDC auth method 依賴上游 IdP signing key、IdP 出事時 Boundary access 也要 rotate；對應啟示是 *broker 的 trust chain 取決於上游 IdP*、不要把 OIDC 當無責任接口                                                            |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)                  | static credential 在離職 / 外洩後仍可用是核心問題、Boundary + Vault Database Secret Engine 直接消除 static credential 存在、改成每 session 簽 short-lived DB user                                                                  |
| [Privileged Access and JIT Authority (section)](/backend/07-security-data-protection/blue-team/)                                                           | Boundary 的 *authorize-session* 模型是 JIT authority 的具體實作、session 期限 + Vault TTL 雙重約束 blast radius                                                                                                                    |

## 下一步路由

- 上游：[7.B Privileged Access and JIT Authority](/backend/07-security-data-protection/blue-team/)、[7.B Segmentation and Blast Radius Containment](/backend/07-security-data-protection/blue-team/)
- 平行：[Teleport](/backend/07-security-data-protection/vendors/teleport/)、[Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/)、[Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/)
- 搭檔：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（Credential Library 核心）、[Okta](/backend/07-security-data-protection/vendors/okta/)（OIDC IdP）
- 跨類：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)（cloud target 的 STS token 來源）、[Terraform](/backend/05-deployment-platform/vendors/terraform/)（target / scope / role 進 IaC）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Boundary audit log → SIEM → IR routing）、[2.3 SSO 攻擊面](/backend/07-security-data-protection/identity-access-boundary/)
- 官方：[Boundary Documentation](https://developer.hashicorp.com/boundary)
