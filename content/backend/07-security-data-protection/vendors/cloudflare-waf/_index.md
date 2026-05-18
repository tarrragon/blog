---
title: "Cloudflare WAF"
date: 2026-05-18
description: "Edge WAF + DDoS + Bot management 整合套件、global anycast 網路、控制面信任邊界跟客戶側補強的對照"
weight: 1
tags: ["backend", "security", "vendor", "cloudflare-waf", "waf", "edge", "ddos"]
---

Cloudflare WAF 是 *edge-deployed* 的 Web Application Firewall、跑在 Cloudflare 全球 anycast 網路上、攔截 HTTP/HTTPS 攻擊在抵達 origin 之前。它跟 [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/) / [Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/) 的核心差異是 *跟其他 Cloudflare 產品深度整合*：DDoS protection、Bot Management、Rate Limiting、Page Shield（JS supply chain）、API Shield（schema validation）、Zero Trust、Workers 邊緣計算共用同一個控制面。客戶選 Cloudflare WAF 通常不只是要 WAF、是要 *整套 edge security suite*。

## 服務定位

Cloudflare WAF 的核心定位是 *把攻擊擋在 origin 之前的一站式 edge security*。流量打到 Cloudflare anycast IP、經過 WAF / DDoS / Bot / Rate Limit / Page Shield 多層處理、再 proxy 到 origin。這跟 [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/) 跑在 AWS 內部 ALB / CloudFront / API Gateway 前是不同部署模型 — AWS WAF 流量 *已經進到 AWS*、Cloudflare WAF 流量 *還沒到 origin*。對 origin 是 *任意雲 / on-prem* 的客戶、Cloudflare 是天然選項；對 AWS-only 客戶、AWS WAF 整合更深但 edge 範圍小。

跟 [Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/)（前 Signal Sciences）相比、Cloudflare 走 *signature + managed rule + ML* 混合、Fastly NG-WAF 走 *語意分析 + behavioral detection*（不靠 regex signature）。Cloudflare managed rule 覆蓋廣但 false positive 較常見、需要 *sensitivity tuning*；Fastly NG-WAF 預設較低 FP 但需要 *自己定義業務 anomaly*。

關鍵張力：客戶信任的不只是 *WAF rule 攔截能力*、還包括 *Cloudflare control plane 的安全性*。[Cloudflare 2023 control plane token](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/) 跟 [Cloudflare 2026 route leak](/backend/07-security-data-protection/cases/cloudflare-route-leak-2026/) 兩個事件展示：vendor 自己被打進去 / 自動化配置失誤時、客戶側 *直接修不了*、只能等公告 + 客戶側 token rotation + emergency bypass。

## 本章目標

讀完本頁、讀者能判斷：

1. Cloudflare WAF 在 edge security stack 中承擔哪一段（DDoS / WAF / Bot / Page Shield / API Shield）、哪些要靠 origin 自己做
2. Managed Rule vs Custom Rule 的取捨、sensitivity tuning 跟 false positive curve
3. Cloudflare control plane 出事時的客戶側補強路徑（API token rotation、Origin Rules bypass、第二邊界 fallback）
4. 何時用 Cloudflare、何時走 [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/) / [Fastly NG-WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/) 的取捨

## 最短判讀路徑

判斷 Cloudflare WAF 配置是否健康、最少看四件事：

- **誰能改 WAF 規則**：Cloudflare account 的 admin / member role 配置、API token scope（不要用 Global API Key、用 scoped API token + 限定 zone / 限定 permission）、Audit Log 是否同步到 SIEM
- **規則覆蓋面**：Managed Ruleset（OWASP Core Ruleset + Cloudflare Managed Ruleset + Exposed Credentials Check）是否開、Sensitivity（Low / Medium / High）對應的 FP rate 是否監控、Custom Rule 是否進版控（Terraform provider）
- **入口暴露**：origin IP 是否曝光（DNS 直查 / 歷史 SAN cert / 子域名）、Argo Tunnel / Authenticated Origin Pull 是否強制、繞過 Cloudflare 直連 origin 的路徑是否封住
- **證據可回查**：Security Events Log 是否同步到 SIEM（Logpush 推到 R2 / S3 / Splunk）、Page Shield 偵測異常 script 是否 alert、API token 異常操作（特別 zone settings 變更）是否 alert

四件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 [Entry Point Protection](/backend/07-security-data-protection/entrypoint-and-server-protection/) 邊界的待補項目。

## 日常操作與決策形狀

**Managed Ruleset 分層**：Cloudflare 提供三類 managed rule — *OWASP Core Ruleset*（OWASP CRS、寬覆蓋、FP 較多）、*Cloudflare Managed Ruleset*（Cloudflare 維護、針對熱門 CMS / framework）、*Exposed Credentials Check*（檢測登入流量中的已洩漏 credential）。production 通常開全部三套 + 各設適當 sensitivity。Sensitivity 不是「敏感度越高越好」— High sensitivity 攔截更多 borderline traffic、business-critical endpoint 可能誤殺合法請求。建議從 *Log Mode* 開始、觀察 1-2 週的 FP pattern、再切到 *Block*。

**Custom Rule（Cloudflare Rules）**：用 Rules language（類 SQL 表達式）定義條件 + 動作（Block / Challenge / Log / JS Challenge / Managed Challenge）。常見用法：geo block（特定國家）、known bad IP（threat intel feed）、URI path-based limit（admin endpoint 限定 IP）、header anomaly（缺 User-Agent / 異常 Referer）。所有 Custom Rule 走 Terraform provider 進版控、避免 console 直接改、變更走 PR review。

**Rate Limiting**：跟 WAF rule 是 *獨立 product*、配置是 *threshold + window + action*（例：1000 req/min per IP → challenge）。Rate Limiting 比 WAF 適合處理 *legitimate-looking high volume*（credential stuffing、scraping、API abuse）。注意 *NAT pool IP* 的問題 — 一個公司 / ISP NAT 出口可能合法產生高 QPS、簡單 per-IP rate limit 會誤殺、需要組合 *cf.threat_score* 或 *cookie-based identification*。

**Bot Management（單獨 SKU）**：免費版 WAF 不含 Bot Management、需要 Pro / Business / Enterprise 才有。Bot Management 用 ML + behavioral fingerprint 區分 *human / good bot（搜尋引擎）/ likely bot / verified bot*、給 bot score（1-99）。客戶在 Custom Rule 用 `cf.bot_management.score < 30` 之類條件挑出 likely bot 處理。簡單 user-agent 過濾擋不住現代 headless browser、必須走 Bot Management。

**Page Shield（JS supply chain 防護）**：Page Shield 監測客戶網頁載入的 JS / connect 來源、發現 *新出現的腳本* 或 *已洩漏的 script*（CT log + threat intel）就 alert。意義是 *防 third-party script 被供應鏈攻擊*（類 [Magecart](https://en.wikipedia.org/wiki/Magecart)）— WAF 攔不住、因為攻擊發生在 *browser 端* 而非 *origin 流量*。需要在 Page 載入 Page Shield 的 monitoring script。

**API Shield**：用 OpenAPI schema validation、auto-discovery API endpoint、mTLS 驗證、JWT validation。對於有 schema 的 API、可以擋掉 *schema 不符的請求*（多餘欄位、型別錯誤、缺必要欄位）— 比 generic WAF rule 精準。

**Origin 暴露面收緊**：Cloudflare 唯一有效的前提是 *流量必須經過 Cloudflare*。如果攻擊者拿到 origin 真實 IP（DNS 歷史記錄、漏洞披露網站、SSL cert SAN）、可以繞過 Cloudflare 直打 origin。控制方法：origin firewall 只允許 Cloudflare IP range 入站、Argo Tunnel（origin 主動建 outbound 連線到 Cloudflare、不開任何入站 port）、Authenticated Origin Pull（origin 用 cert 驗證請求來自 Cloudflare）三選一或組合。

**API token 治理**：避免 Global API Key（全帳號 root token）、改用 *scoped API token*（限 zone + 限 permission + 限 IP + 限 TTL）。token 進 [Secret Management](/backend/knowledge-cards/secret-management/) / [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、定期 rotate。對應 [Cloudflare control plane token 2023](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/) 揭示的 lesson：Cloudflare 自己也踩過 token 治理不足、客戶側不能假設 vendor 完美。

## 核心取捨表

| 取捨維度        | Cloudflare WAF                                     | AWS WAF                                         | Fastly Next-Gen WAF                                                                            |
| --------------- | -------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 部署位置        | Cloudflare global edge（300+ POP）                 | AWS region 內 ALB / CloudFront / API Gateway 前 | Fastly edge + Agent + Module（自管 Nginx / Apache / Envoy / IIS）+ Cloud WAF proxy、三模型可混 |
| Origin 中立性   | 強 — origin 可以是任何雲 / on-prem                 | 弱 — 跟 AWS 緊耦合（限 AWS service 前）         | 強 — Fastly CDN / 任何 origin                                                                  |
| 偵測模型        | Signature + Managed Rule + ML                      | Signature + Managed Rule + Lambda 自訂          | Signal / behavioral（語意分析、低 FP）                                                         |
| DDoS 內建       | 是 — 跟 WAF 同套餐                                 | AWS Shield Standard 內建、Advanced 加價         | 內建 + Fastly DDoS                                                                             |
| Bot Management  | 加價 add-on（Pro / Business / Enterprise）         | AWS WAF Bot Control                             | 加價 add-on                                                                                    |
| JS supply chain | Page Shield（Business+）                           | 無原生、靠後端 CSP / 第三方                     | Inline JS monitoring（Next-Gen WAF 部分）                                                      |
| API schema      | API Shield（Enterprise）                           | AWS WAF + API Gateway request validator         | NG-WAF inline + sigsci-agent                                                                   |
| 學習曲線        | 中 — UI / Rules language 易上手、Terraform 完整    | 較陡 — JSON policy + 跟 AWS service 整合多軌    | 中 — agent 安裝 + Signal 語意設定                                                              |
| 第三方信任成本  | 高 — Cloudflare 控制面（2023、2026 自家事件）      | 中 — AWS 控制面、跟 IAM 同套                    | 中 — Fastly 控制面（規模小、事件少但社群影響也小）                                             |
| 適合場景        | Multi-cloud / on-prem origin、要整套 edge security | AWS-heavy、ALB / CloudFront 是主要入口          | 高 FP 容忍度低、業務有 schema、想避 regex signature                                            |

選 Cloudflare WAF 的核心訴求：*多雲 / on-prem origin* + 需要 *整套 edge security suite*（DDoS + WAF + Bot + Page Shield + API Shield） + 接受 Cloudflare 控制面風險、且有預算做 Enterprise tier 才能拿到完整功能。純 AWS-internal app + ALB origin 用 AWS WAF 整合更直接。

## 進階主題

**Workers + Workers AI 作為 custom logic**：當 managed rule + custom rule 表達力不夠（例：根據 user account tier 決定 challenge 強度、整合內部 risk score API）、可以用 Cloudflare Workers 寫 JavaScript / TypeScript / Rust 在 edge 執行。Workers AI 提供 edge ML inference、可以做 inline content moderation 或 anomaly detection。代價是 *Workers code 進 Cloudflare 控制面*、變更要走部署流程、debug 跟 origin 是兩條 trace。

**Logpush 跟 SIEM 整合**：Cloudflare Security Events 量大、free / Pro 在 dashboard 看、Business / Enterprise 走 Logpush 到 R2 / S3 / Splunk / Datadog / Sumo Logic。production 必須走 Logpush、不能只在 dashboard — 事件 30 天保留期是 Cloudflare 端、SIEM 留更久。Logpush 也是 SIEM 上做 *跨來源 correlation* 的前提（WAF event + origin app log + IdP log）。

**Multi-account / Tenant**：大企業有多個 Cloudflare account（不同 BU / 不同產品線）、要走 *Cloudflare for SaaS* 或 *Account-level access*、API token scope 要限定 account。Single account 多 zone 是常見小組織配置、但跨組織 / 跨產品線必須拆 account 隔離 admin compromise blast radius。

**Magic Transit / Zero Trust integration**：Magic Transit 是 L3 DDoS（不只 HTTP、TCP / UDP 也 anycast）、Zero Trust 是 employee access（取代 VPN）。跟 WAF 是不同產品、但常一起部署 — Magic Transit 防 L3/L4 attack、WAF 防 L7、Zero Trust 防內部 east-west。

## 排錯與失敗快速判讀

- **Managed Rule 誤殺合法請求**：High sensitivity 開後 business endpoint 變慢 / 報錯 — 看 Security Events 找 rule_id、用 Custom Rule skip 該 rule 在特定 path / 特定 user-agent、不要全 zone 關 rule
- **Bot Management 太嚴 / 太鬆**：bot score threshold 設不對、合法 API client 被當 bot、或攻擊者拿到 verified bot 假冒 — 用 *Bot Analytics* 看分數分布、調整 threshold 同時加白名單（API key + IP CIDR）
- **Rate Limit 誤殺 NAT 用戶**：per-IP rate limit 在 NAT 出口 IP 上炸 — 改 per-session（cookie-based）或 cf.threat_score 條件
- **Origin IP 外洩**：DNS 歷史 + 漏洞披露 + cert SAN 揭露真實 origin、攻擊繞 Cloudflare 直打 — 換 IP + 開 origin firewall（只允許 Cloudflare CIDR）+ Argo Tunnel
- **API token over-scoped**：CI / 第三方 SaaS 拿到 Global API Key、整 account 都被改 — 改 scoped token、限 zone + permission + IP、進 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)
- **Security Events 沒進 SIEM**：事件只在 dashboard、跨來源 correlation 沒法做 — 配 Logpush + alert 規則
- **Page Shield 沒裝**：客戶端 JS 被植入、伺服器端日誌看不到攻擊、第三方 script CDN 被打 — 啟用 Page Shield + CSP report-uri 雙軌
- **第二邊界沒設**：完全依賴 Cloudflare、Cloudflare 出事流量全停（[2023 / 2026 自家事件](/backend/07-security-data-protection/cases/cloudflare-route-leak-2026/)）— 高 SLA 服務應該設 fallback origin / secondary DNS（如 Route53 health check failover 到 Fastly 或直連 origin）

## 何時改走其他服務

| 需求形狀                           | 改走                                                                                                                                                    |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS-only + ALB / CloudFront origin | [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/)                                                                                        |
| 低 FP 容忍 / 業務有 schema         | [Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/)                                                                       |
| 純內部 mTLS / east-west            | [SPIRE](/backend/07-security-data-protection/vendors/spire/) + service mesh                                                                             |
| Cert lifecycle                     | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) / [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) |
| 客戶端 JS supply chain             | Page Shield + [supply chain integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                                 |
| DDoS L3/L4                         | Cloudflare Magic Transit / AWS Shield Advanced                                                                                                          |

## 不在本頁內的主題

- Cloudflare 完整 product line（Workers / Pages / R2 / D1 / Magic Transit / Zero Trust 各自細節）
- WAF Rules language 完整語法 reference
- Page Shield / API Shield Enterprise tier 完整功能對照
- 各 PCI DSS / SOC 2 / FedRAMP 合規矩陣
- Cloudflare 在中國的部署模式（JD Cloud Union 合作）

## 案例回寫

Cloudflare WAF 在 07 案例庫有 *兩個直接 vendor-level 事件* + 多個 edge-exposure 對照：

| 案例                                                                                                                                                        | 跟 Cloudflare WAF 的關係                                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [Cloudflare Control Plane Token 2023](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/)                                      | 直接 — Cloudflare 自家 API token 治理不足、客戶側必須假設 vendor 也會被打、API token rotation 跟 IP allowlist 必做 |
| [Cloudflare Route Leak 2026](/backend/07-security-data-protection/cases/cloudflare-route-leak-2026/)                                                        | 直接 — 自動化路由配置錯誤導致流量擁塞、客戶側應有 secondary DNS / failover origin 預案                             |
| [Citrix Bleed 2023 Session Hijack](/backend/07-security-data-protection/red-team/cases/edge-exposure/citrix-bleed-2023-session-hijack/)                     | 對照啟示 — WAF 攔不住 edge appliance zero-day、需要「修補 + session 失效 + 異常清查」三同步                        |
| [Fortinet SSL-VPN CVE 2023-27997](/backend/07-security-data-protection/red-team/cases/edge-exposure/fortinet-cve-2023-27997-sslvpn-overflow/)               | 對照啟示 — vendor patch 前的臨時 WAF rule + 收斂可達來源是修補窗口期的標準動作                                     |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)                      | 對照啟示 — WAF rule 是 emergency mitigation、但 exploitation 過 WAF 後在後端執行、不能單靠 WAF 防後端 supply chain |
| [Okta-Cloudflare 2023 Support Supply Chain](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/) | 對照啟示 — 上游 IdP 出事傳導到 Cloudflare admin 帳號、API token / admin session 要立即 rotate、不等供應商公告      |

## 下一步路由

- 上游：[7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)
- 平行：[AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/)、[Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/)
- 下游：[7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)（WAF block 不夠時、資料層也要遮罩）
- 跨類：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（Cloudflare API token 存放）、[Okta](/backend/07-security-data-protection/vendors/okta/)（Cloudflare admin 走 SSO）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（WAF block 事件 / Cloudflare 自家事件如何 routing 進 IR）
- 官方：[Cloudflare WAF Documentation](https://developers.cloudflare.com/waf/)
