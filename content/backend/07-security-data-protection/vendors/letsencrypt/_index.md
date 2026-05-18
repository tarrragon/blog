---
title: "Let's Encrypt"
date: 2026-05-18
description: "免費 + 自動化的公共 ACME CA、90 天 TTL 強制自動化、跨雲跨平台 public TLS cert 的事實基礎"
weight: 10
tags: ["backend", "security", "vendor", "letsencrypt", "acme", "pki", "tls"]
---

Let's Encrypt 是免費 + 自動化的公共 ACME CA（Certificate Authority）、由 Internet Security Research Group (ISRG) 營運、簽發 DV（Domain Validation）等級的 public TLS cert。它的核心設計選擇是 *只發 90 天 TTL 的 cert + 完全自動化的 ACME protocol*、把人工管理選項從工程實務中拿掉、強迫 cert lifecycle 走機器化路線。今天大多數 public-facing web service 的 TLS cert 都直接或間接從 Let's Encrypt 來、是現代 Web 的事實基礎設施之一。

## 服務定位

Let's Encrypt 的角色是 *跨雲、跨平台、跨組織規模* 的公共 DV cert 來源。對於需要 public TLS cert 又不被特定雲廠綁定的場景（on-prem、edge node、跨雲 service、自架 CDN origin、開源專案）、Let's Encrypt 是預設選項。它解決的問題不是「能不能拿到 cert」、而是「能不能 *無人值守* 持續拿到 cert」— ACME protocol 把申請、驗證、issue、renew、revoke 全部標準化、ACME client（[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) / certbot / acme.sh / Caddy / Traefik）負責 client 端執行。

跟 [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/) 比、Let's Encrypt 跨雲跨平台、ACM 限 AWS-managed service（ALB / CloudFront / API Gateway）內使用、export 出去要另談；ACM Private CA 又是另一個產品。跟商業 CA（DigiCert / Sectigo / Entrust）比、商業 CA 提供 OV（Organization Validation）/ EV（Extended Validation）cert、cert 內含經過驗證的組織資訊、金融網站或法遵需求會用；Let's Encrypt 只發 DV cert、不驗證組織身份。跟 [HashiCorp Vault PKI](/backend/07-security-data-protection/vendors/hashicorp-vault/) 比、Vault PKI 是 *internal CA*（不被公共瀏覽器信任、適合 internal mTLS / workload identity）、Let's Encrypt 是 *public CA*（瀏覽器信任、適合 public-facing service）— 兩個是互補關係、不是替代。

## 本章目標

讀完本頁、讀者能判斷：

1. 哪些 cert 需求適合 Let's Encrypt（public-facing、DV、跨平台）、哪些該走 ACM / 商業 CA / Vault PKI
2. ACME protocol 的四個 first-class concept（Account / Order / Authorization / Challenge）跟自己選的 ACME client 怎麼對應
3. Rate limit 是 *硬限制*、SaaS 多 tenant 場景如何規劃（wildcard / SAN / rate limit exemption）
4. 90 天 TTL + CT log 公開 + revocation 弱化 在 production 設計上的影響

## 最短判讀路徑

判斷 Let's Encrypt 使用是否健康、最少看四件事：

- **Account 管理**：ACME account 是 *cross-domain* 的身份、同一個 account 可以申請組織所有 domain 的 cert — account key 外洩等於 attacker 可以對所有 domain 發 cert；account key 是否離線備份、是否跟 ACME client 用獨立 key（不重用 server key）
- **Challenge 選擇**：HTTP-01 需要 port 80 reachable、適合單機 + 直接 internet 暴露；DNS-01 需要 DNS API access、適合 wildcard + 私有環境；TLS-ALPN-01 走 443、適合 port 80 不可用的場景 — Challenge 選錯會卡在 validation 階段
- **Rate limit 規劃**：50 cert/week per registered domain、5 duplicate cert/week — 大型 SaaS 服務多 customer subdomain 容易撞牆、要先估 cert 量、再決定 wildcard / SAN / rate limit 申請
- **Revocation 流程**：cert 被洩漏怎麼辦 — revoke 不是 fleet-wide invalidation、real-world 失效靠 *rotate + 短 TTL*；revocation 程序是否寫入 runbook、舊 cert 是否在所有 endpoint 確實 retire

四件事任一缺失、就是 [Transport Trust and Certificate Lifecycle](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/) 跟 [Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/) 邊界的待補項目。

## 日常操作與決策形狀

**ACME client 選擇**：[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) 適合 K8s 環境、Ingress / Gateway / Certificate CRD 自動化；certbot 適合單機 / VM、官方參考實作；acme.sh 是 pure shell、嵌入既有 deployment script 容易；Caddy / Traefik 把 ACME 內建進 reverse proxy、零設定拿 cert。client 端的選擇決定 *cert 怎麼存、怎麼 deploy 到 termination point*、Let's Encrypt 自己不管這層。

**ACME Account（cross-domain identity）**：Account 是 ACME server 認可的身份、用一把 account key（不同於 cert private key）簽 ACME request。同一個 account 可以申請 *組織所有 domain* 的 cert — 安全意義是 account key 外洩 = attacker 對所有 domain 都能 issue cert。Production 場景把 account key 視為跟 root signing key 同等級的 secret、離線備份、跟日常 ACME client 用獨立 key。

**Challenge 選擇 — HTTP-01 / DNS-01 / TLS-ALPN-01**：HTTP-01 在 `/.well-known/acme-challenge/<token>` 放 response、Let's Encrypt 從 port 80 拉、適合單機 + 直接 internet 暴露；DNS-01 在 `_acme-challenge.<domain>` 放 TXT record、適合 wildcard cert（`*.example.com` 必須 DNS-01、HTTP-01 不行）跟私有環境（不需要 port 80 開放）；TLS-ALPN-01 走 port 443、用 special ALPN extension 回 challenge、適合 port 80 被擋的場景。Wildcard cert 強制 DNS-01 是 Let's Encrypt 政策、不能用 HTTP-01 繞過。

**Rate limit 是硬限制**：50 cert/week per registered domain（包含 SAN 在內）、5 duplicate cert/week（同樣 SAN 組合）、300 new orders/3 hours per account、5 failed validation/hour。大型 SaaS 對 N 個 customer subdomain 發 cert 容易撞牆 — 解法有三：用 wildcard cert 把多 subdomain 合一張（單張 cert 服務無限 subdomain）、用 SAN cert 把多個 subdomain 寫進同一張 cert、申請 rate limit 上限提高（[官方表單](https://isrg.formstack.com/forms/rate_limit_adjustment_request)）。撞 rate limit 後該 domain 整個 week 不能發新 cert、是 production outage 等級。

**Staging environment 必用於測試**：`acme-staging-v02.api.letsencrypt.org` 是 Let's Encrypt 的測試 endpoint、cert 不被瀏覽器信任、但 *rate limit 寬鬆很多*（30000 cert/week / 60 duplicate cert/week）。debug ACME client 設定、新 deploy pipeline、CI 跑 cert renewal test 都應該先指 staging、確認 OK 再切 production endpoint。直接在 production 試錯撞 rate limit 是常見事故。

**90 天 TTL + 60 天 renew cadence**：Let's Encrypt cert 固定 90 天 TTL、ACME client convention 是 *過 60 天就開始 renew*、留 30 天 buffer 給 retry。90 天是 *設計選擇*、不是技術限制 — 短 TTL 強迫自動化、把「過期前手動處理」這個失敗模式從設計中拿掉。如果你的 cert renewal 還需要人介入、表示 ACME client / deployment pipeline / monitoring 哪邊沒做好、要在 60 天 buffer 內修。

**CT log 公開可查**：Let's Encrypt cert 都會進 Certificate Transparency log（CT log）、可以用 [crt.sh](https://crt.sh) 查任何 domain 的歷史 cert。對 production 意義有兩面：blue team 可以監控自家 domain 的 unexpected cert（attacker 用相似 domain 釣魚會留痕）；red team 可以查 target 公司新出現的 internal hostname（cert 上的 SAN 等於公開的 service inventory）。對 *internal-only* hostname、不要用 Let's Encrypt cert、否則 SAN 變成 recon 資料源 — 內部服務走 Vault PKI / 私有 CA。

## 核心取捨表

| 取捨維度   | Let's Encrypt                           | AWS ACM                                    | 商業 CA（DigiCert / Sectigo）   | Vault PKI（internal CA）                           |
| ---------- | --------------------------------------- | ------------------------------------------ | ------------------------------- | -------------------------------------------------- |
| 信任範圍   | Public（公共瀏覽器信任）                | Public（公共瀏覽器信任）                   | Public（公共瀏覽器信任）        | Internal（需要客戶端裝 CA cert）                   |
| 部署範圍   | 跨雲、跨平台、on-prem                   | 限 AWS-managed service（ALB / CF / APIGW） | 跨雲、跨平台                    | 自管、跨雲皆可                                     |
| Cert 等級  | DV（Domain Validation）                 | DV（ACM）/ Private CA 任意                 | DV / OV / EV                    | 自定義（內部信任）                                 |
| 費用       | 免費                                    | 免費（ACM public）/ Private CA 收費        | 收費（DV / OV / EV 各價位）     | 自管成本                                           |
| 自動化     | ACME protocol 標準化                    | ACM 自動 renew（限 AWS-managed service）   | 多數需手動 / API 申請、自動化弱 | 自管 + ACME server 可選                            |
| TTL        | 90 天（硬性）                           | 13 個月（AWS rotate）                      | 1-2 年                          | 自訂                                               |
| 適合場景   | public-facing、跨雲、open source、SaaS  | AWS-only + ALB/CloudFront 內               | 金融、政府、需要 EV 顯示組織    | internal mTLS、workload identity、企業內部 service |
| 不適合場景 | internal mTLS、EV cert、cert 內需含組織 | 跨雲、export 出 AWS                        | 需要快速自動化、預算敏感        | public-facing、不能要求客戶端裝 CA                 |

選 Let's Encrypt 的核心訴求：*public-facing + DV 等級夠用 + 跨平台 + 需要自動化*。需要 EV cert 走商業 CA、需要 internal mTLS 走 Vault PKI、AWS-only + 留在 ALB / CloudFront 內走 ACM 更省事。

## 進階主題

**Rate limit 規劃跟 SaaS 多 tenant**：N 個 customer subdomain 場景下、單 domain 50 cert/week 很容易撞牆。設計選項：(1) wildcard cert（`*.app.example.com`）一張覆蓋無限 subdomain、但 wildcard cert 不能保護 nested subdomain（`*.app.example.com` 不蓋 `foo.bar.app.example.com`）；(2) SAN cert 把多個 subdomain 寫進同一張 cert（單張最多 100 個 SAN）、適合 customer 數固定、新增不頻繁的場景；(3) 申請 rate limit 上限提高、production scale SaaS 走這條；(4) cert reuse — 同樣 SAN 組合在 5 duplicate cert/week 內可 reuse、不重發。

**跟 cert-manager + DNS-01 整合**：production K8s 環境最常見組合是 cert-manager + Let's Encrypt + DNS-01、DNS provider 走 Route53 / Cloud DNS / Cloudflare。cert-manager 用 ClusterIssuer 設定 Let's Encrypt account + DNS solver、Certificate CRD 宣告需要的 cert、cert-manager 自動完成 ACME flow。優勢是 *wildcard cert 可用*（DNS-01 不受 HTTP-01 的 port 80 限制）、跨 cluster 可標準化、cert renewal 進 K8s event stream 容易監控。

**ACME profiles（client-specific behavior）**：Let's Encrypt 2024 開始提供 ACME profile 機制、允許 client 選擇 cert 屬性（如 short-lived 6 天 cert vs standard 90 天）。short-lived cert 適合機器 workload、進一步壓縮 revocation 缺陷的影響窗口；普通 web service 用 standard profile 即可。Profile 是 opt-in、ACME client 要支援。

**跨 ACME CA fallback**：Let's Encrypt 不是唯一 ACME CA — ZeroSSL、Buypass、Google Trust Services 都提供 ACME endpoint。production 建議 ACME client 設兩個 issuer（Let's Encrypt primary + ZeroSSL / Buypass secondary）、Let's Encrypt 出事（rate limit 撞牆、AWS outage 影響 challenge 驗證、ISRG 服務中斷）時可以 fallback、不會 cert 全停。cert-manager 用兩個 ClusterIssuer 即可、application 端零感知。

**Revocation 的弱化現實**：cert 可以 revoke、但實際失效路徑薄弱 — CRL（Certificate Revocation List）跟 OCSP（Online Certificate Status Protocol）更新有延遲、且大多數 client（瀏覽器、API client）不會主動檢查 revocation 狀態（soft-fail：查不到就放行）。real-world 的 cert 失效機制其實是 *短 TTL + rotate*、不是 revocation API。設計時不要寄望 revoke 後 attacker 拿到的 cert 就無效 — rotate 出新 cert + 在所有 endpoint deploy 新 cert + 觀察舊 cert traffic 歸零、才算真正失效。

## 排錯與失敗快速判讀

- **ACME challenge 失敗**：HTTP-01 拉不到 `/.well-known/acme-challenge/<token>`、檢查 port 80 reachability、firewall、CDN 是否擋；DNS-01 TXT record 沒生效、檢查 DNS provider API permission、TXT TTL 是否設太長
- **撞 rate limit**：50 cert/week per registered domain 撞牆、整個 week 不能發新 cert — production 必須先 *staging 測完* 再切 production、cert reuse 機制要開（同 SAN 組合不重發）、長期解走 wildcard / SAN consolidation / rate limit exemption
- **Renewal 沒在 60 天前開始**：cert 過期前才 renew、撞到 ACME server 暫時不可用會直接過期 — ACME client 設 60 天 renew threshold、cert expiry 30 天前 alert 給 oncall
- **Account key 沒備份**：account key 弄丟、可以重新註冊但 *舊 cert 的 revocation 權限沒了*（除非用 cert 私鑰 revoke）— account key 跟 root signing key 同等級保護、離線備份
- **CT log 暴露 internal hostname**：Let's Encrypt cert 進 CT log、internal-only hostname 的 SAN 變 recon 資料源 — internal service 不用 Let's Encrypt、改 Vault PKI / 私有 CA
- **Wildcard cert 用 HTTP-01**：`*.example.com` 申請失敗、Let's Encrypt 政策強制 wildcard 走 DNS-01 — 切到 DNS-01 solver、設定 DNS provider API access
- **Cert 出事 revoke 後 attacker 還能用**：revocation 不是 fleet-wide invalidation、CRL/OCSP 多數 client 不檢查 — 真正失效靠 rotate + 觀察舊 cert traffic 歸零、不是 revoke API

## 何時改走其他服務

| 需求形狀                               | 改走                                                                                                                                                |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS-only + 留在 ALB / CloudFront 內    | [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/)                                                                                    |
| 需要 OV / EV cert（cert 含組織資訊）   | 商業 CA（DigiCert / Sectigo / Entrust）                                                                                                             |
| Internal mTLS / workload identity      | [HashiCorp Vault PKI](/backend/07-security-data-protection/vendors/hashicorp-vault/) / [SPIRE](/backend/07-security-data-protection/vendors/spire/) |
| K8s workload cert 自動化（用 LE 當源） | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)                                                                          |
| Cert lifecycle 治理（跨 vendor 通則）  | [7.4 Transport Trust and Certificate Lifecycle](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)                    |
| Cert rotation 證據鏈                   | [7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)                                |

## 不在本頁內的主題

- ACME protocol RFC 8555 完整規格逐條解讀
- 每個 ACME client（certbot / cert-manager / acme.sh / Caddy / Traefik）的完整設定教學
- Let's Encrypt 內部 CA infrastructure 跟 ISRG governance 細節
- CT log 內部結構跟 SCT（Signed Certificate Timestamp）驗證流程
- DNS provider 的 API 認證設定（Route53 IAM / Cloud DNS service account / Cloudflare API token）

## 案例回寫

Let's Encrypt 在 07 案例庫沒有直接 vendor-level 事件、以下案例採對照引用：

| 案例                                                                                                                                    | 跟 Let's Encrypt 的關係（對照）                                                                                                                                     |
| --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Transport Trust and Certificate Lifecycle (section)](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)  | Let's Encrypt 90 天 TTL + 強制 ACME 自動化、把人工依賴從 cert lifecycle 設計中拿掉、是 *forcing function 級別* 的治理選擇                                           |
| [Credential Rotation Scoped Evidence (section)](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)              | Let's Encrypt 沒提供 fleet-wide revocation API、cert 出事後客戶側自己負責 fleet update + session invalidation、是 scope map 必要的典型情境                          |
| [Citrix Bleed 2023 Session Hijack](/backend/07-security-data-protection/red-team/cases/edge-exposure/citrix-bleed-2023-session-hijack/) | 對照啟示 — cert rotation 跟 session invalidation 是兩件事、Let's Encrypt cert renew 不會 invalidate 既有 TLS session 跟 application-layer session、要分別處理       |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)     | Let's Encrypt rate limit（50 cert/week per domain）是 scope-driven 設計的硬約束、單一 domain 不能無限 rotation、wildcard / SAN consolidation 必須納入 rotation 策略 |

## 下一步路由

- 上游：[7.4 Transport Trust and Certificate Lifecycle](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)、[7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)
- 平行：[AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/)、[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)、[SPIRE](/backend/07-security-data-protection/vendors/spire/)
- 下游：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（Vault PKI 處理 internal CA、跟 Let's Encrypt public CA 互補）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（cert 出事 / private key 外洩如何 routing 進 IR 流程）
- 官方：[Let's Encrypt Documentation](https://letsencrypt.org/docs/)、[ACME RFC 8555](https://datatracker.ietf.org/doc/html/rfc8555)、[crt.sh CT log search](https://crt.sh)
