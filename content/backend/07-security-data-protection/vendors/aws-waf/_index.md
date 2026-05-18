---
title: "AWS WAF"
date: 2026-05-18
description: "AWS-internal WAF、跟 ALB / CloudFront / API Gateway 直接整合、Web ACL + Managed Rule Group + Rate-based Rule、Shield Standard 內含"
weight: 2
tags: ["backend", "security", "vendor", "aws-waf", "waf", "aws"]
---

AWS WAF 是 *AWS-internal* 的 Web Application Firewall、掛在 ALB、CloudFront、API Gateway、App Runner、AppSync 與 Cognito User Pool 的前面，攔截 HTTP/HTTPS 攻擊。它跟 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) / [Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/) 的核心差異是 *部署位置在 AWS 內部*：流量先經 AWS 邊界進來、再進 Web ACL 過濾、最後抵達 origin；不是在 Cloudflare anycast edge 提早攔。對 AWS-heavy 客戶、AWS WAF 的價值是 *跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / VPC / [AWS Shield](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html) 同一個控制面*；對 multi-cloud / on-prem origin、AWS WAF 觸不到、要回到 edge WAF。

## 服務定位

AWS WAF 的核心定位是 *跟 AWS 服務深度耦合的 L7 防護層*。Web ACL 直接掛 AWS resource、規則用 IAM policy 管理、log 進 Kinesis Firehose / CloudWatch Logs / S3、跟 AWS Shield Standard（內含、L3/L4 DDoS）自動整合。這跟 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) 在 *origin 之前的 edge* 攔截不同 — AWS WAF 流量 *已經進到 AWS 邊界*、不是擋在外部。對 origin 跑在 ALB / CloudFront / API Gateway 後的客戶、AWS WAF 是天然選項；origin 在其他雲或地端、AWS WAF 觸不到。

跟 [Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/) 相比、AWS WAF 走 *signature + managed rule group* 偵測模型、不像 Fastly NG-WAF 走語意 / behavioral；AWS WAF 的 Managed Rule Group 來自 AWS Managed 與 AWS Marketplace 第三方（Fortinet、F5、Imperva 等）、客戶端 *看不到 rule logic*、debug 時要靠 sampled request 反推。

計費模型也是關鍵差異：AWS WAF 按 *per-Web-ACL + per-rule + per-request* 計費（單 ACL $5/月、單 rule $1/月、$0.60 per 1M request），Managed Rule Group 算多 rule、開太多套 ruleset 與流量大時帳單會明顯漲。Cloudflare 是 plan-tier 計費（Pro / Business / Enterprise）、不會因為多開 rule 線性漲價。

## 本章目標

讀完本頁、讀者能判斷：

1. AWS WAF 在 AWS-internal 防護 stack 中承擔哪一段、哪些要靠 [AWS Shield](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html) / VPC / CloudFront 補位
2. Web ACL scope（Regional vs CloudFront）的選擇與跨 region 部署成本
3. Managed Rule Group / Custom Rule / Rate-based Rule 的取捨、Bot Control add-on 是否值得開
4. 何時用 AWS WAF、何時走 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) / [Fastly NG-WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/) 的判準

## 最短判讀路徑

判斷 AWS WAF 配置是否健康、最少看四件事：

- **Web ACL scope 對不對**：CloudFront distribution 必須掛 *CloudFront scope*（強制在 us-east-1 建立 ACL）、ALB / API Gateway 必須掛 *Regional scope*（每個 region 各一份）；scope 配錯掛不上去、跨 region 部署是否用 IaC（Terraform / CloudFormation）同步複製 ACL
- **Managed Rule Group 與 sensitivity**：是否啟用 *AWSManagedRulesCommonRuleSet*（CRS）、*AmazonIpReputationList*（已知惡意 IP）、*AnonymousIpList*（VPN / proxy / Tor）、*KnownBadInputsRuleSet*（已知 exploit pattern）、Marketplace rule 是否在 Count mode 觀察 1-2 週 FP 再切 Block
- **Logging 有沒有開**：Web ACL log 預設關閉、必須手動配 Kinesis Firehose / CloudWatch Logs / S3 destination；event 是否進 SIEM（見 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)）、是否能對 sampled request 反推 rule 行為
- **IAM 邊界**：誰能 update Web ACL（`wafv2:UpdateWebACL`、`wafv2:UpdateRuleGroup`）、是否限定 admin role 才能改、CI 是否只有 `wafv2:Get*` / `List*` 用來 verify、敏感變更是否走 Change Management / [Audit Log](/backend/knowledge-cards/audit-log/)

四件事任一缺失、就是 [Entry Point Protection](/backend/07-security-data-protection/entrypoint-and-server-protection/) 邊界的待補項目。

## 日常操作與決策形狀

**Web ACL 與 scope**：Web ACL 是 AWS WAF 的 *規則容器*、必須 attach 到 AWS resource。Scope 兩種：*Regional*（給 ALB / API Gateway / App Runner / AppSync / Cognito User Pool、每 region 獨立）與 *CloudFront*（給 CloudFront distribution、必須在 us-east-1 建立、全球生效）。同一個 ACL 不能跨 scope 共用；跨 region 部署同一套規則必須複製 ACL、用 Terraform / CloudFormation 管理避免 drift。

**Rule action 五種**：每個 rule 觸發時可以做 *Block*（直接 403）、*Allow*（跳過後續 rule、放行）、*Count*（不擋、只記錄、用於 dry-run 觀察 FP）、*CAPTCHA*（出題給人類解、bot 過不去）、*Challenge*（silent JS challenge、無感驗證）。新 rule 上線標準動作是先 *Count* 1-2 週看 sample、確認 FP 在容忍範圍才切 *Block*。CAPTCHA / Challenge 是 [Bot Control add-on](https://docs.aws.amazon.com/waf/latest/developerguide/waf-bot-control.html) 配套、要額外計費。

**Managed Rule Group（managed by AWS / Marketplace）**：AWS Managed（免費含在 WAF）涵蓋 *Common Rule Set*（OWASP top10 對應）、*Known Bad Inputs*、*SQL Database*、*Linux*、*Unix*、*Windows*、*Anonymous IP List*、*Amazon IP Reputation List*、*Account Takeover Prevention (ATP)*、*Account Creation Fraud Prevention (ACFP)*。AWS Marketplace（付費）來自 Fortinet / F5 / Imperva / Cyber Security Cloud 等。Marketplace 規則 *不公開 rule logic*、攔錯時只能用 sampled request 反推、debug 比 AWS Managed 困難。

**Custom Rule（statement + 條件）**：Custom Rule 用 *statement*（match condition + transformation）組合：IP Set match、Geo match、Regex Pattern Set、Size constraint、SQL injection match、XSS match、String match（含 header / body / URI / query 各部位）。複雜條件用 AND / OR / NOT 組合、上限是每 Web ACL 5,000 Web ACL Capacity Units（WCU）— 規則越複雜 WCU 越高、Marketplace 大型 rule group 可能直接吃掉一半 budget。

**IP Set / Regex Pattern Set**：IP Set 存 IPv4 / IPv6 CIDR 清單、Regex Pattern Set 存正則表達式集合。兩者都是 *獨立資源*、可在多個 Web ACL 引用、單獨更新（不必動 Web ACL 結構）。實務上 threat intel feed 應該 push 到 IP Set、用 Lambda 自動 sync、不用手動加。

**Rate-based Rule**：限制 *單一 aggregate key* 在滾動 5 分鐘窗口內的請求數、超過 threshold 觸發 action。aggregate key 可選 *IP*、*Forwarded-IP*（看 X-Forwarded-For）、*HTTP method*、*URI path*、*Header*、*Cookie* 或組合。關鍵陷阱：**CloudFront 後 origin ALB 必須用 Forwarded-IP**、否則 Rate-based Rule 看到的全是 CloudFront 邊緣節點 IP、所有真實使用者被合併計算、要嘛全擋要嘛全放。

**Logging 必須手動開**：Web ACL log 預設關閉、destination 三選一：*Kinesis Data Firehose*（推到 S3 / Splunk / Datadog）、*CloudWatch Logs*（簡單但貴）、*S3*（直寫、需自己處理 partition）。production 通常走 Kinesis Firehose → S3 + Athena query、配合 SIEM 拉 alert。沒開 log 等於 *攻擊發生時沒證據*、事後無法回查。

**跟 AWS Shield 整合**：所有 AWS WAF 客戶自動含 *Shield Standard*（L3/L4 DDoS、免費、SYN flood / UDP reflection 等基礎防護）。*Shield Advanced* 是付費 add-on（$3,000/month per organization + per-resource fee + data transfer out fee）、提供 *24/7 DRT（DDoS Response Team）*、cost protection（DDoS 期間 AWS service scaling fee 補貼）、進階分析。一般客戶 Shield Standard 已足夠；金融 / 政府 / 高知名度品牌需要 Shield Advanced 的 DRT 與 cost protection。

**Lambda@Edge / CloudFront Functions 補位**：當 WAF rule statement 表達不出複雜業務邏輯（geofencing + business hour + user tier 組合、JWT claim 解析後判斷 routing）、用 *Lambda@Edge*（Node.js / Python、跑在 CloudFront 邊緣節點、4 個 phase：viewer-request / origin-request / origin-response / viewer-response）或 *CloudFront Functions*（純 JS、輕量、低延遲、只在 viewer-request / viewer-response）補位。Lambda@Edge 適合複雜邏輯、CloudFront Functions 適合 header rewrite / 簡單 routing；兩者都不能取代 WAF managed rule、但補位 WAF 表達力上限。

**跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) 整合**：誰能改 Web ACL 是 *IAM policy* 決定（`wafv2:CreateWebACL`、`wafv2:UpdateWebACL`、`wafv2:AssociateWebACL`、`wafv2:UpdateRuleGroup` 等 action）。production 標準配置：admin role 才能 update、CI / 開發者只有 `wafv2:Get*` / `List*` 用來 verify、敏感變更走 Change Management + CloudTrail [audit log](/backend/knowledge-cards/audit-log/)。

## 核心取捨表

| 取捨維度      | AWS WAF                                                | Cloudflare WAF                                       | Fastly Next-Gen WAF                                 |
| ------------- | ------------------------------------------------------ | ---------------------------------------------------- | --------------------------------------------------- |
| 部署位置      | AWS 內部（ALB / CloudFront / API Gateway 前）          | Cloudflare global edge（300+ POP）                   | Fastly global edge / 各 origin agent                |
| Origin 適配   | 強耦合 — origin 必須在 AWS                             | 強中立 — 任意雲 / on-prem                            | 強中立 — Fastly CDN / 任何 origin                   |
| 計費模型      | per-ACL + per-rule + per-request                       | plan tier（Free / Pro / Business / Enterprise）      | request-based + plan                                |
| Managed Rule  | AWS Managed（免費）+ Marketplace（付費、logic 不透明） | Cloudflare Managed + OWASP CRS + Exposed Credentials | Signal-based（語意、低 FP、不靠 regex signature）   |
| Rate Limiting | Rate-based Rule（含在 WAF、5 分鐘 window）             | Rate Limiting 獨立 product                           | inline rate limit + Signal                          |
| Bot 對應      | AWS WAF Bot Control（add-on、付費）                    | Bot Management（Pro+ add-on）                        | NG-WAF behavioral bot detection                     |
| DDoS 內建     | Shield Standard 自動含（L3/L4）、Advanced 加價         | 同套餐內建                                           | 內建 + Fastly DDoS                                  |
| 控制面整合    | 跟 IAM / CloudTrail / Shield / VPC 同 plane            | Cloudflare 控制面、跟其他 Cloudflare 產品同套        | Fastly 控制面、agent 跑在 origin                    |
| 學習曲線      | 中陡 — Web ACL + WCU + scope + IAM policy 多軌         | 中 — UI / Rules language / Terraform 完整            | 中 — agent 安裝 + Signal 語意設定                   |
| 適合場景      | AWS-heavy、ALB / CloudFront 是主要入口                 | Multi-cloud / on-prem origin、要整套 edge security   | 高 FP 容忍度低、業務有 schema、想避 regex signature |

選 AWS WAF 的核心訴求：*AWS-internal app* + origin 跑在 ALB / CloudFront / API Gateway / App Runner 後 + 想跟 IAM / CloudTrail / Shield 同套 control plane 治理。Origin 不在 AWS、或要 *把攻擊擋在抵達雲之前*、應該走 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) 或 [Fastly NG-WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/)。

## 進階主題

**AWS WAF Bot Control（add-on）**：付費 add-on、用 AWS 自家 bot fingerprinting 區分 *verified bot*（搜尋引擎）/ *signal: automated browser*（headless Chrome 等）/ *signal: known bot*（已標記 IoT / scraper），給每個請求 *bot category label*。Custom Rule 在 label 上做條件、決定 Block / Challenge / CAPTCHA。比 user-agent 過濾準很多、但要額外計費（per-request）。Bot Control 有兩個 inspection level：*common*（便宜、基礎指紋）與 *targeted*（貴、含 JavaScript challenge、CAPTCHA、token-based）。

**Fraud Control（ATP / ACFP）**：*Account Takeover Prevention*（ATP）跟 *Account Creation Fraud Prevention*（ACFP）是 Managed Rule Group 的特殊類別、需付費啟用。ATP 看登入端點的 credential stuffing、ACFP 看註冊端點的 bot signup。兩者都用 AWS 自家 threat intel（被竊憑證 list、行為模型）打 label、客戶側用 Custom Rule 處理。對有 login / signup 端點的 SaaS / 電商有價值、純內部後台不必開。

**CAPTCHA / Challenge**：AWS WAF 內建 CAPTCHA puzzle 與 silent JS Challenge、可在 rule action 直接呼叫。Challenge 在客戶端執行 proof-of-work、合法瀏覽器無感、headless 工具卡住；CAPTCHA 是視覺題、人類解、bot 不會。Production 標準做法：Bot Control 給 label → Custom Rule 看 label → likely bot 走 Challenge、known bad 走 Block、人類流量直接 Allow。

**ACM Private CA + WAF 對 mTLS**：AWS WAF 本身不做 mTLS 驗證、mTLS 是 ALB / API Gateway / CloudFront 自己的功能（搭配 [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/) Private CA 簽發 client cert）。WAF 在 mTLS 完成後才看 L7 流量、可以用 *HTTP header match*（mTLS 後 ALB 注入 client cert 資訊到 header）做進一步 rule。Internal API 用 mTLS + WAF 是常見組合。

**Lambda@Edge 補 inline business logic**：複雜判斷（user tier × geo × business hour × A/B test）WAF rule statement 表達不出來、用 Lambda@Edge 在 *viewer-request* phase 解析 JWT、查 internal risk API、回 response header 給 WAF 後續判斷。代價：Lambda@Edge 部署只能在 us-east-1、code 更新傳播到全球 edge 要幾分鐘、debug 是分散式 CloudWatch Logs。

## 排錯與失敗快速判讀

- **Web ACL 掛不上 CloudFront**：scope 配成 Regional、CloudFront 拒絕 attach — Web ACL 必須在 us-east-1 + CloudFront scope 才能掛 CloudFront；ALB / API Gateway 反過來只能掛 Regional scope
- **Rate-based Rule 全擋 / 全放**：CloudFront 後 origin 看到全部都是 CloudFront IP、aggregate key 沒換 Forwarded-IP — 改用 *Forwarded-IP*（X-Forwarded-For）作 aggregate key，並設 Fallback behavior
- **Managed Rule Group 誤殺合法請求**：CRS High sensitivity 開後 file upload / rich text editor 端點被 Block — 找 sampled request 看 rule_id、用 *Scope-down statement* 限定該 rule 在某 path 不執行、或開該 rule 為 Count、不要關整個 group
- **Marketplace Rule 攔不明流量**：Marketplace rule logic 不公開、sampled request 看到 rule label 但不知為何 — 切該 rule 到 Count mode 觀察、若無 attack 跡象換 AWS Managed 同類 rule
- **WCU 超限**：Web ACL 上限 5,000 WCU、加 Marketplace + 多個 AWS Managed 就會爆 — 看 *Capacity Used*、移除重疊 rule、把 Custom Rule 表達式簡化（少用 *transformation chain*）
- **Logging 沒設 / 設錯**：事件發生後沒有完整 log 可查、只有 sampled request（保留 3 小時、機率抽樣） — 必開 *Logging configuration* 到 Kinesis Firehose / S3 / CloudWatch Logs、確認 IAM role 有 firehose:PutRecord 權限
- **IAM 權限過寬**：CI account 拿到 `wafv2:*` 整 zone 都能改 — 收斂到 `wafv2:Get*` / `List*` 唯讀、敏感寫入限 admin role + MFA + Change Management
- **跨 region 部署 drift**：手動在 console 改 us-east-1 ACL、其他 region 沒同步 — 用 Terraform / CloudFormation IaC 管理、PR review、CI plan 檢查 drift
- **Shield Standard 不夠擋大型 L7 DDoS**：Standard 只防 L3/L4、L7 attack 靠 WAF Rate-based Rule + Bot Control — 若反覆遭遇大型 L7 DDoS、評估 Shield Advanced 的 DRT + cost protection 是否值得

## 何時改走其他服務

| 需求形狀                     | 改走                                                                                                                                                              |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Multi-cloud / on-prem origin | [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)                                                                                    |
| 低 FP 容忍 / 業務有 schema   | [Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/)                                                                                 |
| L3/L4 DDoS 進階防護          | AWS Shield Advanced / Cloudflare Magic Transit                                                                                                                    |
| 純內部 mTLS / east-west      | [SPIRE](/backend/07-security-data-protection/vendors/spire/) + service mesh                                                                                       |
| Cert lifecycle               | [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/) / [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)                     |
| Secrets / API key            | [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) / [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) |
| 複雜業務邏輯 inline 處理     | Lambda@Edge / CloudFront Functions                                                                                                                                |

## 不在本頁內的主題

- AWS WAF Classic（v1）的遷移細節 — 本頁全以 WAFv2 為準
- 完整 WCU 計算規則與每個 statement 的 WCU cost reference
- Marketplace 第三方 rule group 各家功能矩陣
- AWS WAF 在 GovCloud / China region 的差異
- Bot Control / ATP / ACFP 完整 label schema reference

## 案例回寫

AWS WAF 在 07 案例庫無直接 vendor-level case、但多個 case 對應 WAF 作為 *修補窗口期臨時控制* 與 *entry point 治理* 的角色：

| 案例                                                                                                                                          | 跟 AWS WAF 的關係                                                                                                                                       |
| --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)        | 對照啟示 — AWS Managed Rule Group 當時推出 Log4Shell 規則作為 emergency mitigation；但 exploitation 通過 WAF 後在後端執行，不能單靠 WAF 防 supply chain |
| [Citrix Bleed 2023 Session Hijack](/backend/07-security-data-protection/red-team/cases/edge-exposure/citrix-bleed-2023-session-hijack/)       | 對照啟示 — WAF 攔不住 edge appliance zero-day、需要「修補 + session 失效 + 異常清查」三同步                                                             |
| [Fortinet SSL-VPN CVE 2023-27997](/backend/07-security-data-protection/red-team/cases/edge-exposure/fortinet-cve-2023-27997-sslvpn-overflow/) | 對照啟示 — vendor patch 前的臨時 AWS WAF Custom Rule + Shield Advanced + Origin lockdown 是修補窗口期動作                                               |
| [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)                                            | AWS WAF 是 entry point protection 的工具、章節原則對應 WAF rule lifecycle 治理（Count → Block、IaC、IAM 收斂）                                          |

## 下一步路由

- 上游：[7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)
- 平行：[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)、[Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/)
- 下游：[7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)（WAF block 不夠時、資料層也要遮罩）
- 跨類：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)（誰能改 Web ACL）、[AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/)（mTLS client cert）、[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)（rule update 用的 API key）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（WAF block 事件如何 routing 進 IR）
- 官方：[AWS WAF Documentation](https://docs.aws.amazon.com/waf/latest/developerguide/)
