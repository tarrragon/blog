---
title: "Tailscale SSH"
date: 2026-05-18
description: "WireGuard-based zero-trust mesh + identity-bound SSH、ACL JSON policy、developer-friendly、跟 IdP integration 取代 SSH key"
weight: 14
tags: ["backend", "security", "vendor", "tailscale-ssh", "pam", "zero-trust", "mesh-vpn"]
---

Tailscale 是 WireGuard-based zero-trust mesh VPN、Tailscale SSH 是其上的 SSH on overlay network 模組。核心 mindset 是 *不用 SSH key、不用 jump host*：所有 device 加入同一個 tailnet、ACL 控制誰能 SSH 到誰、user identity 從 Tailscale 的 IdP 整合（[Okta](/backend/07-security-data-protection/vendors/okta/) / Google / Microsoft / GitHub SSO）來。它跟 [Teleport](/backend/07-security-data-protection/vendors/teleport/) / [Boundary](/backend/07-security-data-protection/vendors/boundary/) / [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/) 的差異不在 *能不能管 SSH*、而在 *網路模型 + identity binding + audit 深度* — Tailscale 走 overlay mesh + identity-bound SSH，Teleport 走 Identity-Aware Proxy + first-class session recording，Boundary 走 network broker + dynamic credential。

## 服務定位

Tailscale 的核心定位是 *WireGuard overlay mesh + identity-bound 連線*、Tailscale SSH 是其上 *取代 sshd 的 SSH 模組*。底層是 Tailscale daemon（每台 device 跑、建立 WireGuard tunnel）+ Tailscale control plane（管 ACL、key exchange、IdP integration、node enrollment）。Tailscale SSH 不是把 OpenSSH 套上 VPN — 它是把 SSH server 換成 Tailscale daemon 內建版本、用 tailnet identity 取代 SSH key、ACL 跟 sshd 設定脫鉤。

跟 [Teleport](/backend/07-security-data-protection/vendors/teleport/) 比、Tailscale 走 *zero-config + developer-friendly*、Teleport 走 *audit-first + compliance-friendly* — Teleport session recording / RBAC / approval workflow 是 first-class、Tailscale Enterprise 才補 session recording、approval workflow 偏簡單。跟 [Boundary](/backend/07-security-data-protection/vendors/boundary/) 比、Boundary 是 *network broker*（client → broker → target、target 不在 client 網路上）、Tailscale 是 *overlay network*（client / target 都在 tailnet 上、直接點對點）；Boundary 配 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 發 dynamic credential、Tailscale 直接 bypass credential。跟 [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/) 比、Cloudflare Access 走 *application-layer reverse proxy*、Tailscale 走 *network-layer mesh*；application（HTTP / API）走 Cloudflare、機器存取（SSH / RDP / DB port）走 Tailscale。

關鍵張力：*developer 易用性* ↔ *audit / compliance 深度* 是 Tailscale 客戶的最大 trade-off。Tailscale 把 SSH 變成「裝完 Tailscale 客戶端、加入 tailnet、不用設 sshd」、developer onboarding 從幾天縮到幾分鐘；但 session recording、approval workflow、keystroke audit 在 Enterprise tier 才有、且深度仍不及 Teleport。

## 本章目標

讀完本頁、讀者能判斷：

1. Tailscale 在 access stack 承擔哪一段（mesh network / identity-bound SSH / Funnel external access）、哪些要外接（[Okta](/backend/07-security-data-protection/vendors/okta/) IdP、[Splunk](/backend/07-security-data-protection/vendors/splunk/) audit log、Teleport 補 session recording）
2. ACL JSON policy 的 ownership 設計（src / dst / group / tag、誰寫、誰 review、tag 命名空間如何治理）
3. Tailscale SSH vs Teleport vs Boundary vs Cloudflare Access 的選型判讀
4. 何時用 Tailscale、何時補上 Teleport（compliance）、何時補上 Boundary（dynamic credential）

## 最短判讀路徑

判斷 Tailscale SSH deployment 是否健康、最少看四件事：

- **ACL 是否走 tag 而非 IP**：production node 是否標 `tag:prod-*`、ACL 用 tag / group 寫（`src: ["group:sre"]`、`dst: ["tag:prod-db:22"]`）而非寫 device hostname；ACL JSON 是否進版控（Git → Tailscale GitOps integration）、change 經 PR review
- **Identity provider 是不是組織 IdP**：tailnet 是否綁 [Okta](/backend/07-security-data-protection/vendors/okta/) / Google Workspace / Microsoft Entra ID、user 從 IdP SCIM 同步、離職時 IdP deprovision 是否連動 tailnet（不是手動撤 tailnet user）
- **Tailscale SSH 是否取代 sshd**：production node 是否關掉 OpenSSH 的 port 22 listener、只允許 Tailscale SSH（避免 fallback 到 SSH key auth、繞過 tailnet ACL）
- **Audit log 是否進 SIEM**：Tailscale audit log（device add / ACL change / SSH session start）是否串到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)、跟 IdP log correlation；Enterprise tier 的 SSH session recording 是否啟用

四件事任一缺失、就是 [Identity Access Boundary](/backend/07-security-data-protection/identity-access-boundary/) 的待補項目。

## 日常操作與決策形狀

**Tailnet 與 Node enrollment**：Tailnet 是一個邏輯網路（一個組織通常一個）、Node 是加入 tailnet 的 device（laptop / server / container）。Enrollment 兩種路徑 — *interactive*（人類 device 跑 `tailscale up`、瀏覽器跳 IdP 登入）、*auth key*（ephemeral / reusable / preauthorized key、CI / IaC 用）。Production server 通常用 *auth key + tag* 加入、tag 在 enrollment 時就綁定、不能事後改。

**ACL JSON policy**：Tailscale ACL 是 HuJSON（JSON with comments）文件、由 `acls` / `groups` / `tagOwners` / `ssh` 區塊組成。`acls` 寫 `action: accept` + `src` + `dst` + `proto` + `port`、`groups` 把 user 抽成角色（`group:sre`、`group:helpdesk`）、`tagOwners` 控制誰能 mint 某個 tag、`ssh` 區塊定義誰能用 Tailscale SSH 連到哪些 tag（額外於 `acls`）。ACL 寫得好不好直接決定 *lateral movement blast radius*。

**Tailscale SSH（取代 sshd）**：Tailscale SSH 是 daemon 內建的 SSH server、user 連線時不出示 SSH key、Tailscale 用 *tailnet identity*（從 IdP 來）做 authn、用 ACL 的 `ssh` 區塊做 authz。SSH session 的 OS user 由 ACL 指定（`users: ["root", "ubuntu"]`）、不是 user 自己挑。意義是 *SSH key rotation 從 lifecycle 移除*、user 離職 IdP deprovision 後立即失去所有 SSH access。

**Identity provider 整合**：Tailscale 自身不存 password、user identity 完全外包給 IdP。Okta / Google Workspace 通常用 SCIM 同步 user + group、GitHub SSO 走 OAuth、Microsoft Entra ID 走 SAML。Group 從 IdP 同步進 tailnet 後、ACL 直接用 `group:sre`、`group:contractor`。IdP 的 MFA / Conditional Access policy 自動套用到 tailnet authn。

**Tag-based machine identity**：Tag 是 Tailscale 的 *machine identity primitive*、語意接近 [SPIRE](/backend/07-security-data-protection/vendors/spire/) workload identity（但 Tailscale-specific、不是 SPIFFE 標準）。Production 用 tag 把 node 分類（`tag:prod-db`、`tag:prod-app`、`tag:ci-runner`）、ACL 用 tag 寫規則。Tag 在 enrollment 時 bind、之後不能改（要重新 enroll）；`tagOwners` 控制誰能 mint 該 tag、防止 dev tag 升 prod tag。

**Subnet Router 與 Exit Node**：*Subnet Router* 把 on-prem subnet（例如 `10.0.0.0/16` 的舊資料中心）route 到 tailnet、不用在每台舊機器裝 Tailscale daemon — 適合 legacy infra migration。*Exit Node* 把所有流量（不只 tailnet）走某個 node 出去、適合 remote worker 需要從固定 IP 出網。兩者都是 mesh 之外的擴展、不是 first-class、容易擴大 blast radius 要謹慎用。

**Funnel（external HTTPS access）**：Funnel 把 tailnet 上的 internal service 暴露到 internet（透過 Tailscale relay、Tailscale 出 TLS cert）、適合 webhook receiver、dev preview environment、demo URL。Production-grade external access 應該走 [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/) 或 reverse proxy + WAF — Funnel 沒有 WAF、bot protection、rate limit，是 *zero-config 暴露*、不是 *production hardened ingress*。

**跟 OS firewall 互動**：Tailscale 是 overlay network、不取代 OS firewall。Production node 應該用 OS firewall（iptables / nftables / Windows Firewall）封鎖 *非 tailnet* 流量到 port 22 / 3306 / 5432、只允許 `tailscale0` 介面進來；不然攻擊者拿到 node IP 後仍能繞過 ACL 直接 SSH。

## 核心取捨表

| 取捨維度          | Tailscale SSH                                   | Teleport                                        | Boundary                                    | Cloudflare Access                               |
| ----------------- | ----------------------------------------------- | ----------------------------------------------- | ------------------------------------------- | ----------------------------------------------- |
| 網路模型          | WireGuard overlay mesh（peer-to-peer）          | Identity-Aware Proxy（client → proxy → target） | Network broker（client → broker → target）  | Application-layer reverse proxy                 |
| Identity binding  | tailnet identity（IdP-bound、無 SSH key）       | Teleport cert（SSO-issued、short-lived）        | Boundary session token（IdP-bound）         | Cloudflare identity（SSO-issued、跟 ZTNA 整合） |
| Session recording | Enterprise tier、Tailscale-specific             | First-class、所有 tier、tsh play 回放           | 無（依賴 target 自身）                      | 無（屬 application layer、不 record SSH）       |
| Audit 深度        | ACL change / device add / session start         | Full session recording + RBAC audit + approval  | Session log + dynamic credential audit      | HTTP request log（不適用 SSH）                  |
| Credential model  | No credential（identity-bound）                 | Short-lived cert（per-session）                 | Dynamic credential（Vault-issued）          | OAuth / JWT（per-request）                      |
| 學習曲線          | 緩 — 裝 client 即用                             | 中 — RBAC role / tsh CLI / approval workflow    | 陡 — broker / target / credential brokering | 緩 — Cloudflare 既有用戶上手快                  |
| 部署模型          | SaaS（Tailscale）+ self-hosted（Headscale OSS） | Self-hosted / Teleport Cloud                    | Self-hosted（HashiCorp）/ HCP Boundary      | SaaS only（Cloudflare）                         |
| 適合場景          | developer-heavy、SSH-first、zero-config 訴求    | Compliance / SOC 2 / 重 audit 場景              | Dynamic credential + Vault 已用             | Application 層存取（HTTP / API）                |
| 退場成本          | 低 — 拆 client + 開 sshd 即可                   | 中 — RBAC / approval workflow 已 codify         | 中 — broker 設定 + Vault integration        | 中 — ZTNA policy + IdP 整合                     |

選 Tailscale SSH 的核心訴求：*developer 易用性 + zero-trust mesh + 願意接受 Tailscale 控制面信任*、且 audit / compliance 要求是中度而非極致（SOC 2 Type II + 內部 SOX 等級就配 Enterprise tier session recording、HIPAA / FedRAMP / 重 compliance 走 Teleport）。

## 進階主題

**Tailscale SSH session recording（Enterprise）**：2023 後 Enterprise tier 提供 SSH session 錄影、存到組織自己的 S3 / GCS（不是 Tailscale 控制面）、用 *recorder node*（tag:tailscale-recorder）攔流量寫盤。意義是 *audit 不再依賴 OS-level 工具（auditd / OSSEC）*；但跟 Teleport 比、Tailscale recording 仍偏簡單、approval workflow 是基本版、structured query 跟 keystroke replay UI 不如 Teleport。

**Subnet Router 的 blast radius**：Subnet Router 把整個 subnet route 到 tailnet、ACL 控制粒度從 *device-level* 退到 *subnet-level*（除非搭 tag）— 一台 Subnet Router 給太多人用就是 jump host 復活。production 應該 *每個 subnet 至少兩個 Subnet Router*（HA）、tag 區分（`tag:subnet-router-prod`）、ACL 限定誰能透過它走。

**Headscale（OSS control plane alternative）**：Headscale 是社群維護的 Tailscale control plane OSS 重實作、self-hosted、跟官方 Tailscale client 相容。適用 *資料主權 / air-gapped / 不信任 Tailscale 控制面* 場景。代價是 ACL JSON 編輯器 / GitOps / SCIM / IdP integration 都要自己拼、沒有官方 SaaS 的 console UX 跟 SLA。production 用 Headscale 通常配 [SPIRE](/backend/07-security-data-protection/vendors/spire/) workload identity 補 machine identity。

**跟 SPIRE workload identity 對照**：Tailscale tag 是 Tailscale-specific 的 machine identity primitive、語意接近 SPIRE 的 SPIFFE ID（`spiffe://example.org/prod-db`）；差異在 SPIRE 走 SPIFFE 開放標準、跨 platform（Kubernetes / VM / serverless）、tag 只在 tailnet 內有意義。重 multi-platform workload identity 走 SPIRE、SSH access 為主走 Tailscale tag。

**Just-In-Time access pattern**：Tailscale 預設是 *standing access*（user 在 group:sre、永遠能 SSH 到 prod-db）、不是 JIT。要做 JIT 通常 *IdP 端做*（Okta Workflows 加 user 進 group:sre-oncall、SCIM 同步進 tailnet、ACL 給 group:sre-oncall 對 prod-db 的 SSH 權限）、或 *Tailscale API 自寫 ACL 寫入腳本*。Teleport / Boundary 有 first-class JIT approval、Tailscale 要自己拼。

## 排錯與失敗快速判讀

- **ACL 改錯把全公司鎖在外面**：ACL JSON 寫錯 default deny 規則、Tailscale 控制面套用後沒人能連 — 用 Tailscale 控制面的 ACL preview / test 功能、production 走 GitOps PR review、保留 `admin-emergency-access` group bypass
- **離職員工還能 SSH**：IdP deprovision 沒連動 tailnet（手動管 user）— 改走 SCIM 同步 + IdP group binding、ACL 用 group 而非個別 user
- **OpenSSH 還在 listen port 22 給 fallback**：node 沒關 sshd、攻擊者拿到 IP 後用 SSH key 繞過 tailnet ACL — production node 關掉 sshd、OS firewall 只允許 tailscale0 介面的 22 port
- **tag 被誤升 prod**：dev user 自己 mint `tag:prod-db` 給 node、ACL 給 prod-db SSH 權限就此擴散 — `tagOwners` 限定 `tag:prod-*` 只有 group:sre 能 mint
- **Funnel 暴露 internal service**：dev 為了 demo 開 Funnel、忘了關、production data 外洩 — Funnel 走 audit log + alert、預設不該開、要開走 short-lived auth key + tag isolation
- **Subnet Router 變新 jump host**：一台 Subnet Router 給全公司用 legacy subnet、ACL 退到 subnet-level — tag 區分 router、ACL 限定誰能透過它、HA 跑兩台以上
- **Audit log 沒進 SIEM**：Tailscale console 看 audit log 很慢、跟 IdP / cloud control plane 沒 correlation — 啟用 Tailscale audit log streaming 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)、跨來源 correlation

## 何時改走其他服務

| 需求形狀                          | 改走                                                                                                                                                |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Compliance / SOC 2 / 重 audit     | [Teleport](/backend/07-security-data-protection/vendors/teleport/)                                                                                  |
| Dynamic credential + Vault 已用   | [Boundary](/backend/07-security-data-protection/vendors/boundary/) + [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)         |
| Application 層存取（HTTP / API）  | [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/)                                                                |
| Workload identity 跨 platform     | [SPIRE](/backend/07-security-data-protection/vendors/spire/)                                                                                        |
| External HTTPS production ingress | [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) + reverse proxy                                                      |
| Audit log SIEM                    | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) |
| Incident routing                  | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                    |

## 不在本頁內的主題

- WireGuard 協定本身的密碼學細節跟 NAT traversal 機制
- Tailscale 計費 tier 的逐項功能對照（看 Tailscale 官方 pricing page）
- Headscale 完整部署 + GitOps + SCIM 自拼方案
- Tailscale 跟 OPNsense / pfSense 等傳統 VPN gateway 的整合
- Tailscale 內網 DNS（MagicDNS）跟 split-horizon DNS 的細節

## 案例回寫

| 案例                                                                                                                                                       | 跟 Tailscale SSH 的關係（對照啟示）                                                                                                                                                                                      |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)                                        | Tailscale SSH 走 IdP identity、push MFA fail 後 attacker 仍要拿 IdP 通過 + tailnet enrollment、雙層 mitigation 比 SSH key 強；但 standing tailnet access 本身是風險、需配合 short-lived auth key 或 JIT group assignment |
| [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | Tailscale 上游 IdP（Okta / Google / Microsoft）signing key 出事時、tailnet enrollment 也跟著受影響、要 force re-auth；Tailscale 自身的 control plane 信任也是同一條鏈、要 audit                                          |
| [MGM 2023 Identity Lateral Impact](/backend/07-security-data-protection/red-team/cases/identity-access/mgm-2023-identity-lateral-impact/)                  | Tailscale ACL 做 tag-based scope（helpdesk group 不能 SSH 到 `tag:prod-db`）、限制 lateral movement blast radius；對照啟示是 helpdesk 工具不該共享 tailnet 跟 prod node、或 ACL 要切乾淨                                 |

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)
- 平行：[Teleport](/backend/07-security-data-protection/vendors/teleport/)、[Boundary](/backend/07-security-data-protection/vendors/boundary/)、[Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/)
- 下游：[SPIRE](/backend/07-security-data-protection/vendors/spire/)（workload identity 補位）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（dynamic credential 補位）
- 跨類：[Okta](/backend/07-security-data-protection/vendors/okta/)（IdP 來源）、[Splunk](/backend/07-security-data-protection/vendors/splunk/)（audit log SIEM）、[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)（external HTTPS production ingress）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（tailnet compromise IR routing）
- 官方：[Tailscale Documentation](https://tailscale.com/kb/)、[Tailscale SSH](https://tailscale.com/kb/1193/tailscale-ssh/)、[Headscale](https://github.com/juanfont/headscale)
