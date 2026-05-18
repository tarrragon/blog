---
title: "Fastly Next-Gen WAF"
date: 2026-05-18
description: "Behavioral / 語意分析 WAF（前 Signal Sciences）、低 false positive、Edge / Agent / Cloud 三種部署模型、API + ATO + Bot 一體"
weight: 3
tags: ["backend", "security", "vendor", "fastly-ngwaf", "waf", "edge", "behavioral-detection"]
---

Fastly Next-Gen WAF（NG-WAF）的核心定位是 *用語意分析 + behavioral detection 取代 regex signature* 的 web application firewall。它前身是 2020 年被 Fastly 收購的 Signal Sciences、跟 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) / [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/) 的根本差異不在覆蓋面、在 *偵測 mindset* — 不靠 pattern 比對、靠解析請求語意（這段內容像不像 SQL、像不像 shell command）跟跨請求行為模式（同一 token 在多 endpoint 連續觸發異常）下判斷。產出是 *低 false positive 的 inline block 模式可以直接上 production*、不需要先養 Log Mode 兩週、不需要 SOC 全職人員跟 rule 戰。

## 服務定位

Fastly NG-WAF 設計的第一順位是 *production 可直接走 Block 模式*。Signature WAF 的成本不在 rule 本身、在 false positive — 一條 SQLi pattern 可能誤判合法 SQL-like 字串（搜尋查詢、CSV 上傳）、production 開 Block 立刻炸合法流量、所以多數 signature WAF 跑在 *Detect / Log Only* 模式、攔不下真正攻擊。Fastly NG-WAF 走 *Signal* 模型：每個請求被解析後標記若干 Signal（SQLi、XSS、CMDI、Traversal、Anomaly 等）、再依 *threshold-based rule*（N 個 Signal 在 M 秒內聚集）才動作 — false positive 自然降低、Block 模式可開。

跟 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) 的對照：Cloudflare 走 signature + managed rule + ML 三層、覆蓋廣但需要 sensitivity tuning；Fastly NG-WAF 預設低 FP 但需要 *客戶自己定義業務語意*（哪些 path 是 admin、哪些 header 不該出現、哪些 anomaly 對自家業務代表攻擊）— 用 *Tag* + *Match Conditions* 表達。跟 [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/) 的對照：AWS WAF 跟 ALB / CloudFront / API Gateway 整合深、跨雲弱；Fastly NG-WAF 部署模型多樣（Edge / Agent / Cloud）、跨 AWS / GCP / on-prem / K8s 一致。

關鍵張力：低 FP 的 *代價* 是要花時間理解自家業務語意。Signature WAF 是「裝上就有保護」、Fastly NG-WAF 是「裝上有 baseline、業務 anomaly 要自己標」。沒有人定義 Tag + Power Rules、就只用到產品 30% 能力。

## 本章目標

讀完本頁、讀者能判斷：

1. Fastly NG-WAF 的 Signal / Tag / Rule / Mode 四個核心 first-class concept 各承擔什麼責任
2. Edge / Agent + Module / Cloud Proxy 三種部署模型的選擇條件
3. Account Takeover Protection、Bot Protection、API discovery 三個進階 module 的適用情境
4. 何時用 Fastly NG-WAF、何時走 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) / [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/) 的取捨

## 最短判讀路徑

判斷 Fastly NG-WAF 配置是否健康、最少看四件事：

- **部署模型對齊架構**：Fastly Edge inline（流量本來就過 Fastly CDN）/ Agent + Module（自管 Nginx / Apache / IIS / Envoy / .NET 加 sigsci-agent local process）/ Cloud Proxy（Fastly 接 origin proxy）三選一或混用、是否覆蓋所有入口（含 admin、internal API、staging）
- **Signal 與 Tag 設計**：預設 Signal（SQLi / XSS / CMDI / Traversal / Backdoor / Anomaly）是否全開、業務語意 Tag（admin-path、internal-only、payment-flow）是否定義並掛上 Match Conditions、Power Rules 是否組合多 Signal / Tag 走 threshold-based action
- **Rule mode 與 threshold**：Site-level 跟 Corp-level Rule 是 Block 還是 Off、threshold（連續幾個 Signal / 多久窗口）是否依 endpoint 業務調整、Template Rule（ATO、Bot）是否啟用
- **Logging 與 sigsci-agent token 治理**：Syslog / HTTP webhook / S3 / SIEM（Splunk / Datadog / Sumo Logic）整合是否 production-grade、sigsci-agent 連回控制面的 token 是否進 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、跨環境 token 是否分離

四件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 [Entry Point Protection](/backend/07-security-data-protection/entrypoint-and-server-protection/) 邊界的待補項目。

## 日常操作與決策形狀

**部署模型選擇**：*Fastly Edge inline* 是最簡部署、流量已過 Fastly CDN 就 inline 加 NG-WAF、沒有額外 agent 要管；*Agent + Module* 是 self-managed Nginx / Apache / IIS / Envoy / HAProxy / .NET / Java（Tomcat）等加裝 sigsci-module（process 內 module 攔請求）+ sigsci-agent（本機 daemon、跟 Fastly 控制面 sync rule、collect event）— 適合 origin 不過 Fastly CDN、或 internal API；*Cloud Proxy* 是 Fastly 提供 reverse proxy 端點、客戶 DNS 指過去、origin 在後面 — 適合不想改 origin、又沒用 Fastly CDN。三種混用常見、大企業 edge 用 Fastly Edge、internal service 用 Agent + Module。

**Signal 是已知攻擊指標**：Fastly NG-WAF 預定義 Signal 包含 *SQLi / XSS / CMDI（command injection）/ Traversal（路徑穿越）/ Backdoor / RCE / Anomaly* 等。Signal 是 *語意解析結果* — request body 被 parser 拆解（JSON / form / multipart）、每個欄位看「這像不像某類攻擊」、不是 regex 比對。意義是 *encoding 變化攔不住*（base64 / URL encode / Unicode normalize 都會被解開）、跟 signature WAF 的脆性對比明顯。

**Tag 是客戶自定 Signal**：用 *Match Conditions*（path / method / IP / header / body content / query 參數）定義「什麼樣的請求叫某 tag」、例：`Path: /admin/* AND Source IP NOT IN internal_cidr → tag: admin-external-access`。Tag 之後可以走 Rule 處理（看到 admin-external-access 就 alert / block）。Tag 是 Fastly NG-WAF 表達 *業務語意* 的主要工具、不是用來補強 Signal。

**Rule 三層**：*Site-level Rule*（單一 site / property）/ *Corp-level Rule*（整個 organization 共用、用於 corp-wide block list、跨 BU 統一 policy）/ *Template Rule*（Fastly 提供的預設複合 rule、如 ATO template、Bot template）。Rule 表達式組合 Signal / Tag / Source IP / Path / Method、走 Block / Off。Power Rules 是進階版 — 支援 *threshold* + *時間窗口* + *多條件 AND/OR*、例：「同 IP 在 60 秒內觸發 5 個 SQLi Signal 就 Block 10 分鐘」。

**Mode 兩種**：*Block*（攔截、回 406 / 自訂 status）/ *Off*（不動作、純 log）。沒有 Cloudflare 的 Sensitivity 滑桿 — 因為 Signal 本身已是語意判讀結果、不需要敏感度調整、調整在 *threshold*（多少 Signal 才動作）。

**Account Takeover Protection（ATO）**：偵測 credential stuffing pattern — 同 IP 多 login fail、跨 IP 同 account 多 login、impossible travel、unusual UA。Fastly NG-WAF 內建 *login endpoint detection*（自動 / 手動標記 `/login`、`/auth/signin` 等）、配合 ATO Template Rule 直接 inline 處理（rate limit、challenge、block）。對應 [Identity Boundary](/backend/07-security-data-protection/identity-access-boundary/) 的 ATO 對策、但是在 WAF 層直接攔、不等 IdP 內 ATO 邏輯。

**Bot Protection**：跟 Cloudflare Bot Management 同類、走 behavioral + browser fingerprint + JS challenge、區分 verified bot / likely bot / human。比 user-agent 過濾穩、headless browser 攔得住。

**API discovery**：Fastly NG-WAF 自動學習 site 的 API endpoint 與 schema、偵測 *schema drift*（突然出現的多餘欄位、缺欄位、type mismatch）— 比手動維護 OpenAPI schema 輕量、適合內部 API 多但沒寫完整 OpenAPI 的團隊。

**Logging 與 sigsci-agent 治理**：所有 event 走 Fastly NG-WAF 控制面 + 客戶端 Syslog / HTTP webhook / S3 / SIEM（Splunk / Datadog / Sumo Logic）。sigsci-agent 連回控制面用 *Site API key* — 該 key 進 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、跨環境 prod / staging 分離、rotation 走標準 secret rotation 流程、不能寫死在 agent 配置檔。

## 核心取捨表

| 取捨維度         | Fastly Next-Gen WAF                                  | Cloudflare WAF                                    | AWS WAF                                            |
| ---------------- | ---------------------------------------------------- | ------------------------------------------------- | -------------------------------------------------- |
| 偵測模型         | Signal / 語意分析 / behavioral（低 FP）              | Signature + Managed Rule + ML                     | Signature + Managed Rule + Lambda 自訂             |
| 部署位置         | Fastly Edge / Agent + Module / Cloud Proxy           | Cloudflare global edge                            | AWS region 內 ALB / CloudFront / API Gateway 前    |
| Block 模式可行性 | 高 — 預設低 FP、production 可直開                    | 中 — 需 sensitivity tuning + Log Mode 觀察        | 中 — managed rule FP 需排除、custom rule 自管      |
| 業務語意表達     | Tag + Match Conditions + Power Rules（threshold）    | Custom Rule（Rules language）+ Bot Score          | JSON policy + Lambda 自訂                          |
| 自管伺服器支援   | 強 — sigsci-agent + module 覆蓋 Nginx / Apache / IIS | 弱 — 必須流量過 Cloudflare edge                   | 弱 — 必須走 AWS service                            |
| ATO 內建         | 是 — Template Rule 直接 inline                       | Exposed Credentials Check（部分覆蓋）             | AWS WAF Fraud Control（加價）                      |
| Bot Protection   | 內建（同層產品）                                     | 加價 add-on（Pro / Business / Enterprise）        | AWS WAF Bot Control（加價）                        |
| API discovery    | 內建（auto schema learning）                         | API Shield（Enterprise）                          | API Gateway request validator                      |
| 學習曲線         | 中 — Signal / Tag mindset 要轉、agent 安裝要熟       | 中 — UI 易上手、Rules language 表達力強           | 較陡 — JSON policy + 多 AWS service 整合           |
| 價格             | 較高 — Enterprise tier 為主、按請求量計              | 分層（Free / Pro / Business / Enterprise）        | 按 rule + request 量、起步低                       |
| 適合場景         | 低 FP 要求、API 重、自管伺服器多、跨雲 / on-prem     | 多雲 / on-prem origin、要整套 edge security suite | AWS-heavy、ALB / CloudFront / API Gateway 是主入口 |

選 Fastly NG-WAF 的核心訴求：*production 直接 Block* + *API / schema-rich 業務* + *自管伺服器需要 inline agent* + *跨雲 / on-prem mix*、且有預算支付 Enterprise tier。純 AWS-internal 簡單 web app 用 AWS WAF 整合更直接；要整套 edge security suite 用 Cloudflare。

## 進階主題

**VCL + Edge custom rule**：Fastly Edge 部署模式下、NG-WAF 跟 [Fastly CDN](https://www.fastly.com/) 的 VCL（Varnish Configuration Language）共存、複雜邏輯可寫 VCL 在 NG-WAF 處理前後攔截 — 例：geo block 在 VCL 做、NG-WAF 處理通過的請求。Compute@Edge（Fastly 的 edge serverless、類 Cloudflare Workers）也可以接 NG-WAF 結果做進一步處理。代價是 VCL / Compute@Edge code 變另一條 ops trace、要有版控與 staging。

**ATO 進階 — credential stuffing 場景**：login endpoint 接 ATO Template Rule 後、可進一步整合 *已洩漏 credential check*（類 Have I Been Pwned 整合）、failed login burst → progressive challenge（先 CAPTCHA、再 block）。對應 [Identity Boundary](/backend/07-security-data-protection/identity-access-boundary/) 的 IdP ATO 邏輯、Fastly 在 WAF 層攔的好處是 *攻擊不會打到 IdP*、減少 IdP 端 rate limit 壓力。

**Bot Protection 進階**：browser fingerprint + behavioral pattern + JS challenge 三層、可掛 *bot score threshold* 在 Power Rules 內、配合 ATO 做 *high-risk login flow*（bot score 高 + login endpoint → 強 challenge）。

**Agent + Module 在 K8s / VM**：K8s 場景 sigsci-agent 走 sidecar 或 DaemonSet、sigsci-module 在 ingress controller（Nginx Ingress Controller 加 sigsci-nginx module）；VM 場景 sigsci-agent 走 systemd service、module 隨 web server 啟動。跨環境 token 隔離（prod / staging / dev）走 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) dynamic secret 或環境變數注入、不寫死配置檔。

**Corp-level Rule 共用**：多 BU / 多產品線在同一 Corp（Fastly NG-WAF 的 organization 概念）下、Corp Rule 跨所有 Site 生效 — 適合表達「全公司禁 IP X」「全公司 ATO Template 都開」、避免每個 Site 重複配置。

## 排錯與失敗快速判讀

- **Signal 沒觸發、攻擊穿過**：Encoding 異常 / parser 沒解析該 content-type — 確認 Content-Type 正確、body 大小沒超過 sigsci-module 限制（預設 100KB）、Signal scope 是否包含該 endpoint
- **Tag 沒掛上**：Match Conditions 寫錯（path 大小寫、trailing slash、wildcard 語意）— 在 Fastly NG-WAF console 用 *Rule Evaluation* 工具測試 request 是否命中
- **Block 模式誤殺**：Power Rules threshold 太低、單一合法請求觸發多 Signal — 調 threshold 或加 Site Rule exception 排除特定 path / source
- **sigsci-agent 跟控制面失聯**：Site API key 過期 / firewall block out-bound / agent 版本太舊 — agent log 看 connection status、輪換 token 走 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、保持 agent 在 supported version range
- **sigsci-module load 失敗**：web server 啟動報 module 載入錯 — 確認 module 版本跟 web server major version 對齊（Nginx 1.20 對 sigsci-nginx 對應版本）
- **ATO Template 沒攔到**：login endpoint detection 沒標到自家 path — 手動在 console 標記 login endpoint 路徑
- **Logging gap**：Syslog / webhook 送失敗、SIEM 沒收到 — 確認 destination accept、TLS cert 沒過期、retry policy
- **跨環境 token 漏氣**：staging token 流到 prod、改 staging 影響 prod rule — Vault 環境分離、token 加標籤、定期 audit token usage

## 何時改走其他服務

| 需求形狀                            | 改走                                                                                                                                                    |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS-only + ALB / CloudFront origin  | [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/)                                                                                        |
| 多雲 + 要整套 edge security suite   | [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)                                                                          |
| 純 internal mTLS / east-west        | [SPIRE](/backend/07-security-data-protection/vendors/spire/) + service mesh                                                                             |
| Cert lifecycle                      | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) / [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) |
| Bot management 為主要訴求、預算敏感 | Cloudflare Bot Management 入門 / AWS WAF Bot Control                                                                                                    |
| DDoS L3/L4 為主                     | Cloudflare Magic Transit / AWS Shield Advanced                                                                                                          |

## 不在本頁內的主題

- Signal Sciences 收購前的 product line 演進細節
- 完整 Signal 清單與每個 Signal 的內部解析邏輯
- VCL / Compute@Edge 完整語法 reference
- Fastly CDN 本身的 caching / TLS / origin shielding 細節
- Enterprise 合約細節、各國資料駐留選項

## 案例回寫

Fastly NG-WAF 沒有直接 vendor-level 公開事件、案例庫對照引用以「behavioral detection 在 zero-day / supply chain 場景的 inline mitigation 角色」為主：

| 案例                                                                                                                                          | 跟 Fastly NG-WAF 的關係                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)        | 對照啟示 — Anomaly Signal 對 JNDI pattern 有 immediate inline detection、不需等 vendor signature 更新；但 exploitation 進後端後仍要靠 supply chain 治理 |
| [Citrix Bleed 2023 Session Hijack](/backend/07-security-data-protection/red-team/cases/edge-exposure/citrix-bleed-2023-session-hijack/)       | 對照啟示 — WAF 攔不住 edge appliance zero-day、需要「修補 + session 失效 + 異常清查」三同步、NG-WAF Power Rules 可在窗口期提供臨時 anomaly 偵測         |
| [Fortinet SSL-VPN CVE 2023-27997](/backend/07-security-data-protection/red-team/cases/edge-exposure/fortinet-cve-2023-27997-sslvpn-overflow/) | 對照啟示 — vendor patch 前用 Power Rules + Tag 快速部署臨時 mitigation、收斂可達來源是修補窗口期的標準動作                                              |
| [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)                                            | Fastly NG-WAF 是 entry point protection 的工具、低 FP 設計讓 production Block 模式可行、跟 signature WAF 的部署成本曲線根本不同                         |

## 下一步路由

- 上游：[7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)
- 平行：[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)、[AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/)
- 下游：[7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)（WAF block 不夠時、資料層也要遮罩）
- 跨類：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（sigsci-agent Site API key 存放）、[Okta](/backend/07-security-data-protection/vendors/okta/)（Fastly admin 走 SSO）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（WAF block 事件 routing 進 IR）
- 官方：[Fastly Next-Gen WAF Documentation](https://docs.fastly.com/products/next-gen-waf)
