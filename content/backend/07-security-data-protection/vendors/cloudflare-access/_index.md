---
title: "Cloudflare Access"
date: 2026-05-18
description: "Zero Trust Network Access (ZTNA)、取代 VPN 的 application-layer access、Argo Tunnel + Device Posture + IdP integration"
weight: 15
tags: ["backend", "security", "vendor", "cloudflare-access", "ztna", "zero-trust", "pam"]
---

Cloudflare Access 是 application-layer Zero Trust Network Access (ZTNA) portal、定位是 *取代 VPN* — 使用者不再先撥 VPN 進內網再連 internal app、而是 IdP 認證後 Access policy 直接判斷能不能進該 application、流量走 Cloudflare global edge。它跟 [Teleport](/backend/07-security-data-protection/vendors/teleport/) / [Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/) / [Boundary](/backend/07-security-data-protection/vendors/boundary/) 解 *不同層的 access* — Cloudflare Access 解 *application 層 ZTNA*、Teleport 解 *infrastructure 層 PAM + session recording*、Tailscale 解 *device-level mesh VPN*、Boundary 解 *credential brokering*。

## 服務定位

Cloudflare Access 的核心責任是 *application-level 認證 + authorization*、不是 network-level routing。一個 Application（hostname / subdomain）對應一組 Access Policy（rule with identity / device / network condition）、user 從 [Okta](/backend/07-security-data-protection/vendors/okta/) / Google / Azure AD / GitHub 等 IdP 認證後、policy engine 決定能不能進、不能進連到 application backend 都沒機會。它是 Cloudflare Zero Trust suite 的核心、跟 *WARP client*（device agent）、*Gateway*（DNS / HTTP filtering、取代 Cisco Umbrella 類）、*Argo Tunnel*（origin-side outbound、不開 ingress port）組成完整 SASE / Cloudflare One 平台。

跟 [Teleport](/backend/07-security-data-protection/vendors/teleport/) 比、Cloudflare Access 走 *application-layer + Cloudflare edge*、Teleport 走 *infrastructure-layer + 完整 session recording*。需要 keystroke / RDP / kubectl 完整錄影做合規（PCI / HIPAA）走 Teleport、需要把所有 internal web app 收進統一 ZTNA portal 走 Cloudflare Access、兩者並存常見：Teleport 管 SSH / DB / Kubernetes、Cloudflare Access 管 internal web。跟 [Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/) 比、Tailscale 是 *mesh VPN + device-to-device WireGuard*、Cloudflare Access 是 *application proxy via edge*。Tailscale 適合 developer 直接 SSH 到雲機、Cloudflare Access 適合 internal app（GitLab / Jenkins / 內部 dashboard）統一收口。跟 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) 的關係：同 Cloudflare 控制面、共用 API token / Audit Log / Logpush、但解不同問題 — WAF 防 *public app*（attacker 從外打 production web）、Access 防 *internal app*（員工 / 廠商存取後台）、兩者常在同一個 Cloudflare account 共存。

關鍵張力：*Cloudflare 控制面信任成本* ↔ *統一 ZTNA portal 的工程紅利* 是 Cloudflare Access 客戶的長期取捨。Cloudflare 自家 control plane 出事（[Cloudflare 2023 control plane token](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/)）會直接打到 Access policy 變更權、客戶側必須有非 Cloudflare 路徑的 break-glass。

## 本章目標

讀完本頁、讀者能判斷：

1. Cloudflare Access 在 ZTNA / PAM stack 中承擔哪一段（application access）、哪些要外接（[Teleport](/backend/07-security-data-protection/vendors/teleport/) 管 infrastructure session、[Okta](/backend/07-security-data-protection/vendors/okta/) 管 IdP source of truth）
2. Application + Access Policy + Argo Tunnel 三者的 ownership 設計（誰建 Application、誰寫 policy、誰跑 cloudflared agent）
3. Cloudflare control plane 信任邊界 — 自家事故的 blast radius 跟客戶側 break-glass 預案
4. 何時用 Cloudflare Access、何時走 Teleport / Tailscale / Zscaler 的取捨

## 最短判讀路徑

判斷 Cloudflare Access deployment 是否健康、最少看四件事：

- **誰能改 Access Policy**：Cloudflare account 的 Super Admin / Access Admin 人數、policy change 是否走 Terraform / API + PR review、是否有 IdP claim 跟 Cloudflare group 雙重 enforcement
- **Application 收口完整度**：internal web / SSH / RDP / API 是否都進 Application 清單、是否還有 *bypass Cloudflare 直連 origin* 的暴露 IP、Argo Tunnel 是否強制（origin 防火牆只開 cloudflared outbound、不開 ingress）
- **Device Posture / Service Auth 治理**：human user 是否有 WARP + Device Posture 檢查（OS 版本 / EDR / disk encryption）、non-human（CI / 機器）是否走 Service Auth（mTLS cert / service token）而非共用 user account
- **Logpush + break-glass**：Access event / Audit Log 是否 Logpush 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 或外部 SIEM、Cloudflare 自家 control plane 出事時是否有 *非 Cloudflare* 路徑可進關鍵 application（例如 emergency bastion 走獨立 IdP）

四件事任一缺失、就是 [Identity and Access Boundary](/backend/07-security-data-protection/identity-access-boundary/) 邊界的待補項目。

## 日常操作與決策形狀

**Application + Access Policy**：Application 是 first-class concept、對應一個 hostname（`gitlab.internal.example.com`）或一組 subdomain。Application 綁多個 Access Policy、每個 policy 是 *Allow / Block / Bypass* rule、條件可組合 identity（IdP group / email / SAML claim）、device（Device Posture 結果 / WARP enrolled）、network（country / IP range / Service Token）。policy 順序決定優先級、第一個 match 的生效。Production 寫法是 *deny by default + allow specific group*、不是 *allow all + block bad*。

**IdP integration**：Cloudflare Access 不存身份、只接 IdP — SAML / OIDC 對 [Okta](/backend/07-security-data-protection/vendors/okta/) / Azure AD / Google Workspace、OAuth 對 GitHub / GitLab、One-Time PIN 對外部廠商（沒 IdP 的合作方）。同一個 Application 可接多 IdP、policy 用 `identity.email ends with @vendor.com` 區分。IdP 是 source of truth、Cloudflare 是 enforcement point — IdP 出事（Okta / Azure AD 故障或被打）會直接擋住所有 Access user 登入、break-glass 預案必要。

**Argo Tunnel（cloudflared）**：internal app 不開 ingress port、不需要 public IP、由 `cloudflared` agent 在 origin 主動建 outbound tunnel 到 Cloudflare edge。攻擊面從「IP + port + WAF rule」收成「cloudflared agent + Tunnel token」— attacker 從外掃不到 origin，必須先拿到 Tunnel token 或 compromise cloudflared host。Argo Tunnel 的 token 是高敏 secret、應該存 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 或 cloud secret manager、定期 rotate。

**Browser-based SSH / RDP / VNC**：Cloudflare Access 對 SSH / RDP / VNC 提供 browser-based render — user 不裝 SSH client、瀏覽器直接連、session 經 Cloudflare edge proxy。可 log session metadata（user / app / time）但 *不像 Teleport 完整錄 keystroke / 螢幕*。合規場景（PCI 要求 session recording）需要外接 Teleport 或自己跑 session recording proxy、Cloudflare Access 解決的是 access enforcement 不是 audit replay。

**Service Auth（non-human access）**：CI runner / 機器人 / API client 走 Service Auth、不需要 user identity。兩種模式：*mTLS*（client cert + Cloudflare 驗 CA）、*Service Token*（HTTP header 帶 `CF-Access-Client-Id` + `CF-Access-Client-Secret`）。token 進 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 或 GitHub Actions secret、定期 rotate、access log 標 service token ID 做事後追蹤。

**Device Posture**：跟 WARP client / Gateway 整合、policy 可加 device 條件 — OS 版本最低、EDR（CrowdStrike / SentinelOne）running、disk encryption enabled、device certificate 已 enrolled。Device Posture check fail 時 deny access 或 fallback 到只讀 application。對應 [zero-trust workforce architecture](/backend/07-security-data-protection/blue-team/) 的章節原則。

**Gateway DNS / HTTP filtering**：Cloudflare Gateway 是 secure web gateway（SWG）、取代 Cisco Umbrella / Zscaler ZIA 類。WARP client 把 device DNS / HTTP traffic 導到 Gateway、policy 過濾 malicious domain / category / DLP。跟 Access 共用 Cloudflare 帳號、policy 跨 Access + Gateway + WARP 統一 — 這是 Cloudflare One / SASE 的核心賣點。

**Logpush 進 SIEM**：Access event（login / policy decision / session）+ Audit Log（policy change / admin action）透過 Logpush 推到 S3 / GCS / Splunk HEC / Datadog / Elastic。跟 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) 共用同一個 Logpush job 配置、SIEM 端做 cross-product correlation（WAF block + Access deny 同 IP）。

## 核心取捨表

| 取捨維度        | Cloudflare Access                              | Teleport                                       | Tailscale SSH                              | Zscaler ZIA / ZPA                      |
| --------------- | ---------------------------------------------- | ---------------------------------------------- | ------------------------------------------ | -------------------------------------- |
| 控制層級        | Application layer（hostname / subdomain）      | Infrastructure layer（SSH / DB / k8s / RDP）   | Network layer（device mesh WireGuard）     | Network + application（SASE 整套）     |
| 流量路徑        | Cloudflare global edge proxy                   | Teleport proxy（self-hosted / Cloud）          | Device-to-device WireGuard（peer-to-peer） | Zscaler global cloud                   |
| Session 錄影    | 不錄 keystroke、只記 metadata                  | 完整 keystroke / 螢幕 / kubectl 錄影           | 不錄（mesh 性質）                          | HTTP / web session 可錄、SSH 弱        |
| 取代 VPN        | 強 — application-layer ZTNA 核心訴求           | 部分 — 偏 PAM、需配 VPN 補 catch-all           | 強 — mesh VPN 直接替代                     | 強 — ZPA 核心訴求                      |
| Origin 暴露     | Argo Tunnel：origin 零 ingress                 | Proxy 收口：origin 只開 Teleport node port     | 不需 ingress：mesh peer 直連               | App connector：類似 Argo Tunnel        |
| IdP integration | SAML / OIDC / OAuth、One-Time PIN for vendor   | SAML / OIDC                                    | SSO via IdP（簡單）                        | SAML / OIDC                            |
| 計費            | Free（50 user）/ Standard / Premium per-user   | Per-user（Teleport Cloud / Enterprise）        | Per-user（含 free tier）                   | Per-user enterprise license            |
| 適合場景        | Internal web app + browser SSH/RDP 統一 portal | Infrastructure access + 合規 session recording | Developer SSH mesh + 小型 team             | 大型企業全 SASE（含 SWG / CASB / DLP） |
| 退場成本        | 中 — policy 跟 Tunnel 改設可遷                 | 中 — session log 鎖在 Teleport                 | 低 — WireGuard 標準                        | 高 — 全 stack 鎖在 Zscaler             |

選 Cloudflare Access 的核心訴求：*application-layer ZTNA 取代 VPN* + *internal web app 為主 + 偶爾 browser SSH/RDP* + *已用 Cloudflare WAF / CDN 控制面*。需要 infrastructure-level session recording 走 Teleport、developer SSH mesh 為主走 Tailscale、要全 SASE / SWG / CASB 套裝走 Zscaler。

## 進階主題

**Service Auth 的 non-human access 設計**：CI / 機器人 / 第三方 API client 不該共用 user account、改走 Service Token 或 mTLS。設計重點：*token 不進 git*（[Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) / GitHub Actions secret）、*per-service token*（不共用、追蹤責任）、*rotation lifecycle*（90 天 / 半年 rotate）、*access log 標 token ID*（事後追責）。token leak 的處理是 *rotate + audit log review*、不是 *all-users password reset*。

**Device Posture + EDR 整合**：Gateway / WARP 可接 CrowdStrike Falcon / SentinelOne / Microsoft Defender for Endpoint 的 device health、policy 可寫 `require posture: crowdstrike.running == true AND crowdstrike.last_check < 1h`。意義是 endpoint compromise 時 EDR 標紅、Access policy 自動 deny — 不需要 SOC 手動把 user disable。前提是 EDR fleet coverage 接近 100%、不然 fallback 設不好會誤殺。

**Cloudflare One（Access + WARP + Gateway + Magic Transit）**：Cloudflare 把 ZTNA + SWG + CASB + 網路骨幹整成 SASE 套裝、競爭對手是 Zscaler / Netskope / Palo Alto Prisma Access。買整套的紅利是 policy / log / IdP 統一、痛點是 *Cloudflare 控制面信任成本指數放大* — 一個 admin 角色失控影響 Access + Gateway + WAF + DNS 全部、不只是單一產品。

**跟 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) 共用 control plane 的取捨**：紅利是同一 Logpush job / 同一 API token 管理 / 同一 Audit Log、SIEM 端 correlation 容易。信任成本是 [Cloudflare 2023 control plane token](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/) 那類事故會同時影響 WAF rule + Access policy + DNS、客戶側必須有 *non-Cloudflare break-glass*（例如保留一條 emergency bastion 走獨立 IdP + 獨立網路、不經過 Cloudflare edge）。

## 排錯與失敗快速判讀

- **User 一進 Application 就被 deny**：policy 順序錯（Block rule 在 Allow 前面 match）、或 IdP group claim 沒帶到 — 看 Access log 的 `decision_reason`、確認 policy 順序跟 IdP claim mapping
- **Argo Tunnel 斷線 / 找不到 origin**：cloudflared 程序掛或 token 過期、origin 防火牆把 outbound 443 擋了 — 重啟 cloudflared、確認 outbound 規則、token rotate 後重新 deploy
- **Service Token 大量 leak / 在 GitHub repo 出現**：CI secret 設定錯放成 plaintext、或第三方 vendor commit 了 — Cloudflare dashboard rotate token、audit log 找受影響時間窗、補 secret scanning（[GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/)）
- **Device Posture 把合法 user 鎖在外**：EDR agent 暫時離線或 OS 升級導致 posture check fail — fallback 設 graceful（降級到只讀 / 加 step-up MFA）、不是直接 deny；EDR fleet coverage 沒到位前不要 hard enforcement
- **IdP 出事 Access user 全進不來**：Okta / Azure AD downtime 把 Access login 全鎖死 — break-glass 走 *Service Token + 緊急 Application*（不接 IdP、只接 mTLS / token），預先 staging tested
- **Bypass 流量直連 origin**：Application 收口不完整、origin 還有 public IP + 沒設 firewall 只接 Cloudflare IP — Argo Tunnel 收完、origin firewall 只允許 Cloudflare IP range 或完全只開 cloudflared outbound
- **Cloudflare control plane 出事**：Cloudflare 自家 admin token / control plane 被打、客戶側 Access policy 暫時改不了或被偷改 — 預案：保留 *非 Cloudflare emergency bastion* + 關鍵 application 的 Logpush 進外部 SIEM（不只 Cloudflare dashboard）

## 何時改走其他服務

| 需求形狀                            | 改走                                                                                                                                                                                                                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Infrastructure access + 合規錄影    | [Teleport](/backend/07-security-data-protection/vendors/teleport/)                                                                                                                                                                                           |
| Developer SSH mesh / 小型 team      | [Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/)                                                                                                                                                                                 |
| Credential brokering / 動態 DB cred | [Boundary](/backend/07-security-data-protection/vendors/boundary/) + [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)                                                                                                                  |
| 全 SASE 套裝（SWG + CASB + DLP）    | Zscaler / Netskope / Palo Alto Prisma Access                                                                                                                                                                                                                 |
| Public app 入口防護                 | [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) / [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/)                                                                                                            |
| IdP 本體（身份 source of truth）    | [Okta](/backend/07-security-data-protection/vendors/okta/) / [Auth0](/backend/07-security-data-protection/vendors/auth0/) / [Keycloak](/backend/07-security-data-protection/vendors/keycloak/)                                                               |
| SIEM 接 Access log                  | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) |
| Incident routing                    | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                                                                                                                             |

## 不在本頁內的主題

- Cloudflare WARP client 完整部署 / device enrollment 細節
- Gateway DNS / HTTP filtering 完整 policy 語法
- Cloudflare One / Magic Transit / Magic WAN 的網路骨幹細節（屬 SD-WAN / SASE 整套架構、不在 ZTNA 範圍）
- cloudflared agent 進階配置（multi-region / HA / load balancing）
- Cloudflare account / API token 管理本身（屬 Cloudflare 平台治理、跨產品共用）

## 案例回寫

Cloudflare Access 在 07 案例庫的關聯來自 *Cloudflare 控制面信任* 跟 *IdP 上游事故傳導*：

| 案例                                                                                                                                                        | 跟 Cloudflare Access 的關係（對照啟示）                                                                                                                       |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Cloudflare Control Plane Token 2023](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/)                                      | Cloudflare 自家 control plane 出事時、Access policy 變更權跟著受影響、客戶側必須有非 Cloudflare 路徑的 break-glass、關鍵 application 的 Logpush 進外部 SIEM   |
| [MGM 2023 Identity Lateral Impact](/backend/07-security-data-protection/red-team/cases/identity-access/mgm-2023-identity-lateral-impact/)                   | Cloudflare Access 在 helpdesk SE 拿到 IdP credential 後、Device Posture + Application policy + Service Token 是額外 hop 成本、不是 IdP 一拿就全通             |
| [Okta-Cloudflare 2023 Support Supply Chain](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/) | 上游 IdP（Okta）出事傳導到 Cloudflare Access enrollment、需要 force re-auth + service token rotate + Logpush audit 找受影響時間窗、IdP 跟 Access 不可同時失能 |

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[zero-trust workforce architecture](/backend/07-security-data-protection/blue-team/)
- 平行：[Teleport](/backend/07-security-data-protection/vendors/teleport/)、[Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/)、[Boundary](/backend/07-security-data-protection/vendors/boundary/)
- 下游：[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)（共用 control plane）、[Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)（Logpush 目的地）
- 跨類：[Okta](/backend/07-security-data-protection/vendors/okta/) / [Auth0](/backend/07-security-data-protection/vendors/auth0/)（IdP source）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（Tunnel token / Service Token 儲存）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Access deny / 異常登入 routing）、[5 deployment vendors](/backend/05-deployment-platform/vendors/)（Argo Tunnel + CI 部署整合）
- 官方：[Cloudflare Zero Trust Documentation](https://developers.cloudflare.com/cloudflare-one/)
