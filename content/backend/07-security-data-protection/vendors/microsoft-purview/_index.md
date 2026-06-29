---
title: "Microsoft Purview"
date: 2026-05-18
description: "Microsoft 跨 M365 / Azure / endpoint 的 data governance + information protection + DLP + insider risk 統合平台、label-driven"
weight: 6
tags: ["backend", "security", "vendor", "microsoft-purview", "dlp", "information-protection", "azure"]
---

Microsoft Purview 是 Microsoft 在 2022 年把原 Microsoft Information Protection (MIP)、Azure Purview data catalog、Microsoft 365 Compliance Center 合併後的統合品牌、定位是 *跨 M365 / Azure / endpoint / 跨平台* 的 data governance + information protection + DLP + audit + insider risk 平台。它跟 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) 的本質差異在 *控制層級*、功能列表反而看起來相似 — Purview 走 *information protection*（document / email / collaboration tool 的 sensitivity label + endpoint inline 攔截）、Google DLP 走 *infrastructure-level discovery + transformation*（GCS / BigQuery 的 content scan + de-identification）— 兩者層級不同、典型大型 Microsoft + GCP 混合環境會並存而非互斥。

## 服務定位

Purview 的核心 first-class concept 是 *sensitivity label* — 一個 label 帶動 encryption、access restriction、watermarking、DLP policy 多個控制、可由 user 手動標也可由 trainable classifier 自動標、跨 Office docs / SharePoint / Teams / Power BI / endpoint 繼承。其上的模組包含：*Data Loss Prevention (DLP)* — 跨 Exchange / SharePoint / Teams / Endpoint / Microsoft Defender for Cloud Apps (MDA) 的 policy 引擎；*Data Map / Data Catalog* — Azure / 多雲資料源 discovery + lineage；*Unified Audit Log* — M365 + Azure AD + Defender 統一 audit；*Insider Risk Management* — 行為 risk score 偵測內部威脅；*Communication Compliance* — Teams / email 內容 review。

跟 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) 比、Purview 走 *information protection 層 + label-driven + endpoint inline*、Google DLP 走 *infrastructure 層 + content-based + transformation pipeline*。跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 比、Purview 不是 SIEM — Unified Audit Log 是 *event source*、Splunk 或 Microsoft Sentinel 才是 aggregation 平面；Purview audit 進 SIEM 是常見組合。跟[雲端原生 data policy](/backend/07-security-data-protection/vendors/cloud-data-policy/)（BigQuery Column-Level Security / S3 Block Public Access）比、Purview 跨平台 + label 統一、雲端原生只覆蓋單一雲、不同責任邊界。

關鍵張力：*label 設計簡單度* ↔ *自動分類精準度* ↔ *使用者教育成本* 是 Purview 導入時最常踩的三角。label 太細（10+ 層 hierarchical）使用者選不出來、label 太粗（只有 Public / Internal / Confidential）DLP policy 觸發精度不夠。Trainable classifier + auto-labeling 是補救、但要投入訓練樣本維運。

## 本章目標

讀完本頁、讀者能判斷：

1. Purview 在 information protection stack 中承擔哪一段（label / DLP / audit / insider risk）、跟 [Azure RBAC + Entra ID](/backend/07-security-data-protection/vendors/azure-rbac/) / SIEM / cloud-native policy 怎麼分工
2. Sensitivity label 的層級設計（粗細、auto-label 條件、跨 Office / endpoint / Power BI 一致性）
3. DLP policy 的 location + condition + action 三軸如何配置、跟 endpoint DLP / MDA 怎麼覆蓋 SaaS shadow IT
4. Purview 計費分 SKU 的 trap、E3 + add-on vs E5 license 的決策

## 最短判讀路徑

判斷 Purview deployment 是否健康、最少看四件事：

- **Label 層級設計**：sensitivity label 幾層、是否 hierarchical（parent / sublabel）、是否定義 auto-labeling 條件（含某 SIT、來自某 SharePoint site、某 user group 建立）、跨 Office / endpoint / Power BI / Teams 是否一致繼承
- **DLP policy coverage**：location 是否涵蓋 Exchange + SharePoint + Teams + Endpoint + MDA、condition 是否用 SIT + label 雙軸（而非只看 SIT）、action 是否依風險分層（block / warn / encrypt / audit-only）
- **Audit + Insider Risk 證據鏈**：Unified Audit Log retention 是否足夠（預設 180 天、E5 可到 1 年、長期要 archive）、Insider Risk policy 是否定義「離職前 30 天 mass download」「異常時段 access」等 organization-specific pattern、是否 export 進 SIEM
- **License 跟模組對應**：Information Protection / DLP / Insider Risk / Communication Compliance 屬不同 SKU、是否買到所需模組、E3 + add-on 還是 E5、避免「policy 寫好但 license 沒解鎖功能」

四件事任一缺失、就是 [Data Protection and Masking Governance](/backend/07-security-data-protection/data-protection-and-masking-governance/) 邊界的待補項目。

## 日常操作與決策形狀

**Sensitivity label 是 first-class control**：label 不只是 metadata、而是 *單一 identifier 帶動多個控制* — 標到 document 後同時觸發 AES encryption（透過 Azure Rights Management）、access restriction（誰能開 / 列印 / 轉寄）、watermarking、DLP policy condition、Power BI dataset 繼承。Hierarchical label（Confidential → Confidential\\Finance、Confidential\\Legal）讓子部門客製、但層級超過 3 層使用者選擇困難。Label 設計要先決定 *跨 BU 共用 base set + 每 BU 自家 sublabel* 的拓撲、不是一次列 20 個。

**Trainable classifier 補 SIT 不足**：預定義 SIT（Sensitive Information Type、如 credit card / SSN / passport）涵蓋通用 PII / PCI、但 organization-specific 敏感資料（內部 product spec、合約模板、未公開財報草稿）SIT 抓不到。Trainable classifier 用 ML 訓練 — 提供 50-500 個正例 + 反例、Purview 訓 classifier、跑 staging 驗證 precision / recall 達標再 promote。維運成本是樣本要定期 refresh、business 變動時 classifier 會 drift。

**DLP policy = location + condition + action**：location（Exchange email / SharePoint site / Teams chat / OneDrive / Endpoint / MDA-managed SaaS）決定 *在哪攔*、condition（含某 SIT N 次 / 標 Confidential / 來自外部 user / 含某 trainable classifier 命中）決定 *何時觸發*、action（block + notify / encrypt / quarantine / audit-only / require justification）決定 *怎麼處理*。production 不該一上來就 block — 先 audit-only 跑 2 週收集 baseline、tune false positive、再 promote 到 warn、最後選擇性 block 高風險 condition。

**Endpoint DLP（Windows / macOS）**：透過 Microsoft Defender for Endpoint agent 在端點 inline 攔截 — copy to USB / upload to non-corp cloud（Dropbox / Google Drive personal）/ print / paste to browser、針對標 Confidential 的 document 自動 block 或 warn。跟 [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 的 Sensitive Data Scanner 不同層 — 後者 scan log / APM payload 事後發現、Endpoint DLP 事前在 user action 攔截。Endpoint DLP 要 Defender for Endpoint license + Purview Endpoint DLP add-on 雙重 license、容易踩計費 trap。

**Microsoft Defender for Cloud Apps (MDA) 整合**：MDA 是 Microsoft 的 CASB（Cloud Access Security Broker）、把 Purview DLP policy 延伸到非 Microsoft 的 SaaS（Salesforce / Box / Slack / Google Workspace）。MDA 透過 API connector 或 reverse proxy 攔截 SaaS 上的 sensitive document、套 Purview label / DLP action。覆蓋 shadow IT 跟 third-party SaaS 是 MDA 的價值、但每個 connector 都要單獨配置 + 維運。

**Data Map / Data Catalog discovery + lineage**：Purview Data Map 自動掃描 Azure Storage / Synapse / SQL DB / Power BI / 部分 AWS / GCP 資料源、產 metadata + classification + lineage。跟 information protection 模組是不同 surface — Data Map 偏 *data governance*（誰擁有什麼資料、資料流向哪）、information protection 偏 *control*（誰能存取、能否 export）。中大型組織通常分開 onboard、不要一次全推。

**Unified Audit Log 是 SIEM source**：M365 + Azure AD + Defender + Purview 自身的 audit event 統一進 Unified Audit Log、可透過 Compliance Center search、或 Office 365 Management Activity API export 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / Sentinel / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)。Purview 自己不做 correlation / alerting、要做跨來源 detection 必須接 SIEM。Retention 預設 180 天、E5 license 1 年、長期合規要走 Audit Premium 或 archive 到 long-term storage。

**Insider Risk Management 跟 SIEM 互補**：SIEM 主軸是 *external threat + cross-source correlation*、Insider Risk 主軸是 *single-user 行為 risk score over time* — 離職前 30 天 mass download、異常時段存取 sensitive folder、跨 sensitivity tier 大量 access。Risk score 累積到 threshold 觸發 case、進 Compliance officer review queue。預定義 policy template（departing employee、disgruntled employee、data leak）可快速 onboard、organization-specific pattern 要自己定。

**跟 [Azure RBAC + Entra ID](/backend/07-security-data-protection/vendors/azure-rbac/) 整合**：Purview policy 的 user / group 引用直接吃 Entra ID identity、sensitivity label 的 access restriction 也走 Entra ID group。Compliance / Information Protection admin 是 Entra ID role、應該收緊到少數人 + 走 PIM (Privileged Identity Management) just-in-time elevation。Break-glass account 要單獨設計、不能跟日常運維混。

## 核心取捨表

| 取捨維度        | Microsoft Purview                                | Google DLP                                  | Splunk                       | 雲端原生 data policy（BigQuery / S3）   |
| --------------- | ------------------------------------------------ | ------------------------------------------- | ---------------------------- | --------------------------------------- |
| 控制層級        | Information protection（document / label）       | Infrastructure（content scan + transform）  | Detection / aggregation      | Resource policy（column / object 級別） |
| 核心抽象        | Sensitivity label + DLP policy                   | InfoType + de-identification                | SPL + correlation rule       | IAM policy + column tag                 |
| 覆蓋面          | M365 + Endpoint + MDA-managed SaaS + Azure       | GCS / BigQuery / Pub/Sub / 任意 API content | 任意 log source              | 單一雲服務內                            |
| 計費模型        | Per-user license（E3 + add-on / E5、模組分 SKU） | Per-GB scan + per-API call                  | Per-GB ingestion             | 多半免費 / 服務內計費                   |
| 自動分類        | Trainable classifier + 預定義 SIT                | InfoType detector（150+ 預定義 + custom）   | 不做分類                     | Column tag 手動 / catalog 工具自動      |
| Endpoint inline | 強 — Endpoint DLP（Win/macOS）                   | 無（基礎設施層）                            | 無（觀測層）                 | 無                                      |
| Shadow IT 覆蓋  | 強 — 透過 MDA CASB                               | 弱 — 限 GCP / API 整合                      | 無                           | 無                                      |
| 退場成本        | 高 — label 嵌入 document、跨 M365 黏著           | 中 — InfoType pattern 可移植                | 高 — SPL / detection content | 低 — IAM policy 較通用                  |
| 適合場景        | M365 / Office / collaboration 為主、insider risk | Infrastructure data + multi-cloud + GCP     | SIEM / SOC                   | 單一雲服務內 fine-grained access        |

選 Purview 的核心訴求：*M365 / Office / collaboration 為主、需要 label 統一控制跨 document / email / Teams / endpoint、insider risk 是主要威脅、且能買到 E5 或對應 add-on*。Non-Microsoft 環境或 infrastructure data 為主（BigQuery / S3）走 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / cloud-native policy 更直接、不要硬塞 Purview。

## 進階主題

**Trainable classifier 的 lifecycle**：classifier 不是 train 一次永久用、business context 變化（產品線改、合約模板更新、合規詞彙變）會讓 precision / recall 下降。Production 應定期 review classifier hit / miss、補新樣本 retrain、跟 SIT 互補不是替代 — 通用 PII 走 SIT 穩定、organization-specific 走 trainable classifier。Staging 跑 2 週驗證 false positive < threshold 才 promote。

**Endpoint DLP 跟 [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) Sensitive Data Scanner 的不同層**：Endpoint DLP 在 user action 當下攔截（copy / upload / print）、Datadog Sensitive Data Scanner 在 log / APM ingestion 時 scrub。兩者不互斥 — Endpoint DLP 防 *資料離開端點*、Datadog Scanner 防 *PII 寫進觀測 log*、典型 Microsoft + Datadog 環境會並存。

**Data Loss Prevention for Power BI**：Power BI dataset / report 可繼承 Purview sensitivity label、export to Excel / PDF 時 label 跟著走、DLP policy 可條件 *標 Highly Confidential 的 dataset 不能 export*。是 Microsoft analytics stack 比 Tableau / Looker 在 information protection 上的關鍵優勢。

**Information Barriers（內部 walled garden）**：合規場景（投行 research vs trading desk、law firm 對手客戶）需 organization 內部某 group 不能 Teams 對話 / 不能 share 檔案、Purview Information Barriers 設定 segment + policy 阻擋。是 compliance-specific feature、非合規環境用不到、但金融 / 法律 / 顧問業是 must-have。

**E3 + add-on vs E5 的計費決策**：Purview 完整功能（trainable classifier、Endpoint DLP、Insider Risk、Communication Compliance、Audit Premium）要 E5 license、單價約 E3 的 1.5 倍。中小組織從 E3 + 個別 add-on（Information Protection and Governance E5、Insider Risk Management E5）起步、避免一次 E5 全推；大組織直接 E5 反而簡化計費跟 license 管理。

## 排錯與失敗快速判讀

- **DLP policy 寫好但沒觸發**：condition 或 location 設錯（policy 只覆蓋 Exchange 沒包 SharePoint）、或 license 沒解鎖該模組（Endpoint DLP 要額外 add-on）— 在 Compliance Center 看 policy match 統計、確認 license 對應
- **使用者抱怨 label 選不出來 / 選錯**：label 層級太細 + 沒有預設 label、user 不知該選哪個 — 簡化到 3-5 個 base label、用 auto-labeling 補自動分類、加 label tooltip
- **Trainable classifier false positive 多**：訓練樣本不足 / 正反例失衡 — 補樣本到 50+ per class、retrain、staging 跑 2 週驗證再 promote
- **Audit log retention 不夠 / 合規查不到**：預設 180 天、合規要 1 年以上 — 升 E5 或 Audit Premium、或 export 到 SIEM / long-term storage
- **Insider Risk policy 太敏感 / 太多 case**：預設 template 沒 tune organization baseline — 跑 audit-only 模式 30 天統計、調 threshold、加 user group 排除（VIP / legitimate bulk download role）
- **Endpoint DLP 攔到合法業務操作**：policy 沒區分 corp managed device vs BYOD、或沒給 user override + justification — 加 device compliance condition、設 warn + justification 而非直接 block
- **MDA connector 落後 SaaS 新功能**：API connector 有 lag、新功能未涵蓋 — 對高風險 SaaS 補 reverse proxy 模式、或在 SaaS 側設原生 DLP
- **License 模組混亂**：policy 寫好但功能沒解鎖、admin 不知道哪些要 E5 — 維護 license-to-feature 對照表、Compliance Center 警示「需要 license」要直接修

## 何時改走其他服務

| 需求形狀                              | 改走                                                                                |
| ------------------------------------- | ----------------------------------------------------------------------------------- |
| Infrastructure data（GCS / BigQuery） | [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/)              |
| SIEM / cross-source correlation       | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / Microsoft Sentinel |
| Observability log PII scrubbing       | [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)  |
| 單一雲 column / object 級別權限       | BigQuery Column-Level Security / S3 Block Public Access                             |
| AWS-centric data protection           | AWS Macie / [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/)        |
| Endpoint detection 為主（不只 DLP）   | CrowdStrike Falcon / Microsoft Defender for Endpoint                                |
| Incident routing                      | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                    |

## 不在本頁內的主題

- Microsoft 365 / Azure AD 完整管理（屬 [Azure RBAC + Entra ID](/backend/07-security-data-protection/vendors/azure-rbac/)）
- eDiscovery 跟法律 hold 流程細節
- Microsoft Sentinel SIEM 完整配置（屬 SIEM 群、跟 Purview 是互補不是同一頁）
- Purview Data Map 對非 Azure 資料源（AWS / GCP / on-prem）的完整 connector 矩陣
- Compliance Manager 的法規對照與 scoring 細節
- Azure Information Protection (AIP) 舊版 client 的 migration 流程

## 案例回寫

Purview 在 07 案例庫沒有直接 vendor-level 事件、但 information protection + insider risk 角度跟多個案例對照：

| 案例                                                                                                                                          | 跟 Purview 的關係（對照啟示）                                                                                                                                            |
| --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Mailchimp 2023 Support Tool Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/mailchimp-2023-support-tool-abuse/) | 客服系統客戶資料應標「Customer Confidential」label、DLP policy 自動阻擋大量匯出、Insider Risk Management 偵測異常 operator 行為                                          |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)     | Endpoint DLP 在 Microsoft 端點攔截從 Snowflake 下載到 USB / personal cloud 的大量資料；對照啟示是「資料平台外洩仍可在 endpoint 端補位攔截」、不是依賴 Snowflake 自身控制 |
| [Okta Support System 2023](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)                                     | Unified Audit Log 紀錄 support tool 高風險操作、Insider Risk 偵測異常 pattern、跟 SIEM 串接做 cross-source correlation                                                   |
| [Data Protection and Masking Governance (section)](/backend/07-security-data-protection/data-protection-and-masking-governance/)              | Sensitivity label + DLP policy 是 information protection 的工具、跟 Google DLP transformation 不同層、可並存                                                             |
| [Audit Trail and Accountability Boundary (section)](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)            | Unified Audit Log 是 accountability evidence chain、retention 跟 export 設計是合規證據可用性的關鍵                                                                       |

## 下一步路由

- 上游：[7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)、[7.8 稽核軌跡與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)
- 平行：[Google DLP](/backend/07-security-data-protection/vendors/google-dlp/)（infrastructure 層 DLP、跟 Purview 並存）、[Cloud-native Data Policy (BigQuery + S3)](/backend/07-security-data-protection/vendors/cloud-data-policy/)（resource-bound access control、跟 Purview label-driven 互補）
- 下游：[Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)（Unified Audit Log export 進 SIEM）
- 跨類：[Azure RBAC + Entra ID](/backend/07-security-data-protection/vendors/azure-rbac/)（identity 基底）、[Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)（log PII scrubbing、不同層互補）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Insider Risk case → IR routing）
- 官方：[Microsoft Purview Documentation](https://learn.microsoft.com/en-us/purview/)
