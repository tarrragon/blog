---
title: "Google DLP"
date: 2026-05-18
description: "GCP 原生 Sensitive Data Protection：infoType discovery + transformation (mask / FPE / tokenize / k-anonymity)、整合 BigQuery / GCS / Cloud SQL"
weight: 5
tags: ["backend", "security", "vendor", "google-dlp", "dlp", "sensitive-data", "gcp"]
---

Google DLP（Data Loss Prevention、2023 重新命名為 *Sensitive Data Protection / SDP*）是 GCP 原生的敏感資料 *discovery + classification + transformation* 服務。它跟 [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) / AWS Macie / [Cloud-native data policy](/backend/07-security-data-protection/vendors/cloud-data-policy/) 的差異不在「能不能發現 PII」、而在 *發現之後能做多少事* — Google DLP 的核心優勢是 transformation 層（masking / Format-Preserving Encryption / tokenization / k-anonymity / differential privacy），不只是 detection。

## 服務定位

Google DLP 的核心定位是 *infrastructure-level 敏感資料治理*、跨 GCS / BigQuery / Cloud SQL / 任意 Inspect API input 的 PII 發現與去識別化。三層能力堆疊：*Discovery*（背景 scan GCS bucket / BigQuery table / Cloud SQL instance 找 PII / payment / credential）、*Classification*（150+ 預定義 infoType + custom infoType 組合）、*Transformation*（redact / mask / replace / pseudonymize / Format-Preserving Encryption / k-anonymity / differential privacy）。

跟 [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) 比、Purview 走 *information protection*（sensitivity label + Office docs + Microsoft 365）+ DLP、Google DLP 走 *infrastructure-level data scan + transformation*；兩者解不同層、企業若 Office docs / SharePoint 為主走 Purview、cloud data warehouse / object storage 為主走 Google DLP。跟 AWS Macie 比、Macie 限 S3 + EBS / RDS snapshot、Google DLP 跨 GCS + BigQuery + Cloud SQL + 任意 Inspect API content（含 streaming / on-prem 透過 API call）。跟 [Cloud-native data policy](/backend/07-security-data-protection/vendors/cloud-data-policy/) 比、Google DLP 是 *detection + transformation*、Cloud-native policy 是 *access control*；production 常組合使用 — DLP 發現敏感欄位 → policy 限制誰能 access → 必要時 DLP transformation 在 query time 自動 redact。

關鍵張力：*content scanned 計費* ↔ *偵測覆蓋率*。DLP API 按 scanned bytes 計費、整 BigQuery dataset full scan 在 PB-scale 跟 SIEM ingestion 同類痛點。實務應該分 *sample scan*（每 dataset 抽 1% 找 infoType 分布）+ *full scan*（高敏感 dataset 才完整 scan）+ *streaming scan*（write path 即時擋）三層。

## 本章目標

讀完本頁、讀者能判斷：

1. Google DLP 在 GCP 資料保護 stack 中承擔哪一段（discovery / classification / transformation）、哪些要外接（[Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) 管 DLP service account、BigQuery column-level security 補 access control）
2. infoType / Inspection Job / transformation 種類的選用判準（什麼場景 mask、什麼場景 FPE、什麼場景 k-anonymity）
3. 計費 trap 的應對（sample scan + full scan 分層、Pub/Sub trigger 避免重複 scan）
4. 何時用 Google DLP、何時走 Purview / Macie / Cloud-native policy 的取捨

## 最短判讀路徑

判斷 Google DLP deployment 是否健康、最少看四件事：

- **誰跑 Inspection Job**：DLP service account 的 IAM role（`roles/dlp.user` / `roles/dlp.jobsEditor`）、能 scan 哪些 project / bucket / dataset、findings 寫進哪個 BigQuery table、誰能讀 findings
- **infoType coverage**：是否覆蓋 organization-specific PII（員工 ID / 客戶 ID 用 custom infoType + dictionary）、預定義 infoType 是否 enable 對應業務的（PCI 場景需 CREDIT_CARD_NUMBER + Luhn check、HIPAA 場景需 healthcare infoType）
- **Transformation lifecycle**：發現 PII 後做什麼（自動 quarantine bucket / 自動 redact view / Pub/Sub trigger Cloud Function）、transformation 是 *one-way*（mask / redact）還是 *reversible*（FPE / tokenization 需 key management 走 [Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)）
- **Cost 治理**：scan 頻率 vs scan scope 的策略、是否分 sample / full / streaming 三層、findings retention policy（findings table 本身也是敏感資料、不該無限保留）

四件事任一缺失、就是 [Data Protection and Masking Governance](/backend/07-security-data-protection/data-protection-and-masking-governance/) 邊界的待補項目。

## 日常操作與決策形狀

**使用模式：Inspect API vs Inspection Job**：DLP 有兩種呼叫模式 — *Inspect API* 走同步單次 scan（小 payload、即時 mask、API 寫入前的 streaming gate）、*Inspection Job* 走非同步批次 scan（大 dataset、結果存 BigQuery findings table、Pub/Sub trigger 後續 workflow）。production 通常混用：write path（Cloud Function / API gateway）走 Inspect API 即時擋住敏感資料寫進儲存、背景 Inspection Job 對既有 dataset 跑覆盤。

**infoType 是 first-class concept**：infoType 不是 regex、是 *PII 分類單位*。預定義 150+ 種（CREDIT_CARD_NUMBER / EMAIL_ADDRESS / US_SOCIAL_SECURITY_NUMBER / IP_ADDRESS / GENERIC_ID / PERSON_NAME 等）、各帶內建驗證邏輯（CREDIT_CARD_NUMBER 內建 Luhn check 比純 regex 精準、減少 FP）。Custom infoType 三種：*regex pattern*（自訂 regex）、*dictionary*（明確 token list、例員工 ID 全集）、*hotword rule*（context-aware、附近出現特定字才認、例「身分證」附近的數字才認 ID）。FP rate 直接由 infoType 精度決定、production rule 應該優先用預定義 infoType + hotword 限縮。

**Transformation 種類遠不只 mask**：DLP 的 transformation 是它跟其他 discovery-only 工具的核心差異。*Redact* 完全刪除（query result 看不到欄位）；*Mask* 保留長度替換字元（`****1234`）；*Replace* 替換成固定字串（`[REDACTED]`）；*Pseudonymize / Tokenization* 一致性 token（同樣 input 給同樣 output、可做 join 但不可逆）；*Format-Preserving Encryption (FPE)* 保留長度 / format 的可逆加密（key 在 [Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)、analyst 查 anonymized data + 必要時授權 reverse）；*k-anonymity / l-diversity* aggregate 到至少 k 個 record 才公開（防止 quasi-identifier re-identification）；*Differential privacy* 加 noise 保證 statistical privacy（aggregated analytics 用）。後三項是 production analytics 場景的關鍵 — 不是「藏起來」而是「可用但保護」。

**跟 BigQuery 深度整合**：DLP 可 inline scan BigQuery column、findings 自動寫回 metadata。配合 BigQuery *column-level security*（policy tag）+ *authorized view* 做「敏感 column 只給特定 role + 自動 redact 給其他 role」。Production 模式：DLP Inspection Job 跑完後、自動 apply policy tag 到含 PII 的 column、無 tag access 的 query 自動失敗或 mask。

**跟 Cloud Storage 整合**：可 schedule 掃 bucket 整批檔案、發現後可自動 *quarantine*（移到隔離 bucket、不同 IAM、警告 owner）。對應 [LastPass 2022 Backup Chain](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/) 的對照：backup bucket 應該獨立 DLP scan、含 credential 的 backup 走獨立 quarantine bucket + 不同 IAM 邊界、不是放在跟 dev backup 同一個 bucket。

**Pub/Sub trigger workflow**：Inspection Job 完成後可 publish 到 Pub/Sub topic、Cloud Function 訂閱後執行 — 自動 quarantine / 自動通知 owner / 自動寫進 [SIEM](/backend/07-security-data-protection/vendors/splunk/) findings index / 觸發 BigQuery policy tag update。這是 detection → response 自動化的 first-class pattern、不是後加的 webhook。

**IAM 邊界**：DLP service account 需要讀 source data（`roles/storage.objectViewer` / `roles/bigquery.dataViewer`）+ 寫 findings（`roles/bigquery.dataEditor` to findings dataset）+ 呼叫 DLP API（`roles/dlp.user`）。service account 本身是高敏感 — 它能讀整個 organization 的 PII、應該走 short-lived credential（[Workload Identity Federation](/backend/07-security-data-protection/vendors/google-cloud-iam/)）+ 嚴格 audit。

## 核心取捨表

| 取捨維度         | Google DLP                                       | Microsoft Purview                             | AWS Macie                                  | Cloud-native data policy                       |
| ---------------- | ------------------------------------------------ | --------------------------------------------- | ------------------------------------------ | ---------------------------------------------- |
| 核心能力         | Discovery + classification + **transformation**  | Sensitivity label + DLP + Office docs         | Discovery + classification（無 transform） | Access control + column-level security         |
| Data source 範圍 | GCS + BigQuery + Cloud SQL + 任意 Inspect API    | Microsoft 365 + SharePoint + Azure data       | S3 + EBS / RDS snapshot 限定               | BigQuery / S3 / Snowflake 各自 native          |
| Transformation   | mask / FPE / tokenize / k-anonymity / DP（全套） | redact + Office sensitivity label             | 無 — 只 detection                          | 無 — 只 access control                         |
| 計費模型         | 按 content scanned（GB）                         | 按 user / asset / 流量                        | 按 storage scanned（GB） + bucket count    | 多半含在 cloud platform、policy 規模相關       |
| Custom 分類能力  | infoType (regex + dictionary + hotword)          | sensitive info type + classifier (ML)         | managed data identifier + custom           | tag-based / column-level、無 content scan      |
| Healthcare / PHI | Cloud DLP for Healthcare（FHIR / DICOM）         | Purview Healthcare data + Microsoft 365 PHI   | 有限                                       | 無原生 PHI 認知                                |
| 適合場景         | GCP-first + BigQuery / GCS 為 PII 儲存層         | Microsoft 365 / Office docs / SharePoint 為主 | AWS-only + S3 為 PII 儲存層                | 已知敏感 column、想做 access control 不做 mask |
| 退場成本         | 中 — transformation 邏輯耦合 DLP API             | 高 — sensitivity label 跟 Microsoft 365 深綁  | 低 — 只是 finding 跟 alert                 | 低 — policy 是 metadata                        |

選 Google DLP 的核心訴求：*GCP 為主資料平台 + BigQuery / GCS 有大量 PII + 需要 transformation（不只 detection）+ 合規（GDPR / HIPAA / PCI）需要 column-level redaction / tokenization*。on-prem 為主或 Office docs 為主走 Purview、AWS-only 走 Macie + S3 policy。

## 進階主題

**Custom infoType 三層組合**：production 自家業務的 PII（員工 ID / 客戶 ID / 內部 case ID）需要 custom infoType。三種組合：*regex* 抓 pattern（員工 ID 格式 `EMP-\d{6}`）、*dictionary* 抓明確 token list（內部 case ID 全集、月更新）、*hotword* 限縮 context（附近出現「員工」「ID」才認、避免一般 6 位數字誤判）。三者組合的 FP rate 比單獨 regex 低一個量級。

**Format-Preserving Encryption (FPE) vs Tokenization**：兩者都產生「外觀像原值但不是原值」的替換。*FPE* 是可逆加密、key 在 [Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)、analyst 在 anonymized data 工作 + 必要時走授權流程 reverse（例：客服需要看完整信用卡號處理退款）。*Tokenization* 是 deterministic mapping、同樣 input 給同樣 output、可做 join 分析但 token table 不存（理論上不可逆、實務上看 implementation）。選擇判準：*需要分析 join 同一 user 跨 dataset* 用 tokenization、*需要授權 reverse* 用 FPE、*只要遮蔽不需要還原* 用 mask / redact。

**k-anonymity / l-diversity / differential privacy**：解決 *quasi-identifier re-identification* 問題 — 即使欄位不是直接 PII（如 ZIP + 性別 + 年齡）、組合起來能反推個人。*k-anonymity* 保證每個 record 在 quasi-identifier 上至少跟 k-1 個其他 record 一樣（典型 k=5）。*l-diversity* 進一步保證 sensitive attribute 在每組內至少 l 個不同值（防止 homogeneity attack）。*Differential privacy* 加 calibrated noise 到 aggregate query 結果、保證個別 record 加入或刪除對結果影響有 bound。Risk Analysis API 可估算 dataset 的 k-anonymity / l-diversity 風險、不需要先 transform 才知道風險。

**跟 Cloud DLP for Healthcare 整合**：FHIR / DICOM 格式的 PHI 有專屬 transformation pipeline。FHIR resource 的特定欄位（patient name / MRN / birth date）按 HIPAA Safe Harbor 自動遮罩、DICOM image 的 metadata 跟 burned-in text 都可 redact。Healthcare 場景的 PHI 治理跟一般 PII 不同 — 不能直接 mask 全部、要保留 clinical utility（年齡轉年齡段、ZIP 保留前三碼）。

**跟 BigQuery column-level encryption**：BigQuery 原生支援 AEAD encryption function、可用 KMS-managed key 對 column 做 cell-level encryption。DLP 可在 ingestion 階段先 tokenize、BigQuery query 階段配合 column-level security 做 access-time decryption。是「detection（DLP）+ classification（policy tag）+ encryption（AEAD）+ access control（column-level security）」的完整 stack。

## 排錯與失敗快速判讀

- **DLP scan 找不到明顯 PII**：infoType 沒 enable / 預定義 infoType 對 organization-specific 格式不認 — 加 custom infoType + hotword、跑 sample scan 驗證 coverage
- **FP rate 太高 / findings 淹沒**：infoType 太寬 / hotword 沒設 — 加 likelihood threshold（VERY_LIKELY / LIKELY）、custom infoType 加 hotword 限縮 context
- **Scan cost 暴衝**：每次都 full scan 整個 dataset / 沒分層 — 改 sample scan（每 dataset 1%）+ 高敏感 dataset 才 full scan + streaming scan 守 write path
- **Inspection Job 跑超久 / timeout**：dataset 過大 / 沒 partition — 切 partition by date、Job concurrency 提高、避免單 Job 跨整個 organization
- **Transformation 後 analyst 無法工作**：mask / redact 全部、保留不下 utility — 改 FPE / tokenization 保留 join 能力、k-anonymity 保留 statistical utility
- **Findings table 自己變成 PII 洩漏面**：findings 含 sample value（預設 quotable）、findings table 無獨立 IAM — 設定 `includeQuote: false`、findings table 走獨立 dataset + 嚴格 IAM
- **DLP service account 權限太大 / 沒 audit**：service account 能讀全 organization PII、用 long-lived key — 改 Workload Identity Federation + short-lived credential + Cloud Audit Log 監控 DLP API call

## 何時改走其他服務

| 需求形狀                                | 改走                                                                                        |
| --------------------------------------- | ------------------------------------------------------------------------------------------- |
| Microsoft 365 / Office docs 為主        | [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)        |
| AWS-only + S3 為 PII 儲存層             | AWS Macie                                                                                   |
| 只要 access control 不要 transformation | [Cloud-native data policy](/backend/07-security-data-protection/vendors/cloud-data-policy/) |
| Secret / credential scanning（非 PII）  | GitGuardian / Gitleaks                                                                      |
| Data lineage / catalog                  | Dataplex / Atlan / Collibra                                                                 |
| KMS / key management for FPE            | [Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)          |
| SIEM ingestion of DLP findings          | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / Chronicle                  |

## 不在本頁內的主題

- 預定義 infoType 完整 list 跟各自 detection 邏輯（150+ 種、見官方 [InfoType reference](https://cloud.google.com/dlp/docs/infotypes-reference)）
- Cloud DLP for Healthcare 的 FHIR / DICOM 完整 pipeline 細節
- BigQuery column-level security / policy tag 的 policy 設計（屬 Data Governance 章節）
- GDPR / HIPAA / PCI 合規逐條對應（屬 [7.8 資料駐留與刪除證據鏈](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/) 跟 [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/) 章節）
- Differential privacy 的數學定義跟 epsilon budget 設計

## 案例回寫

Google DLP 在 07 案例庫沒有直接 vendor-level 事件、但所有資料外洩 / 敏感資料治理 case 都是 DLP 控制覆蓋率的對照：

| 案例                                                                                                                                          | 跟 Google DLP 的關係（對照啟示）                                                                                                                          |
| --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)     | 資料平台 export 流程應該有 DLP scan gate — query result 含批量 PII / 整 table dump 直接 alert 或自動 redact、不是事後審 audit log                         |
| [Mailchimp 2023 Support Tool Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/mailchimp-2023-support-tool-abuse/) | 客服工具的客戶資料 export 應走 DLP Inspect API、單次 export 超過 N 筆 PII 或含 credential 直接擋住 + 觸發 alert、不靠 rate limit 一招                     |
| [LastPass 2022 Backup Chain](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/)               | Backup bucket 應該獨立 DLP scan、含 credential / token 的 backup 自動 quarantine 到獨立 bucket + 不同 IAM、不是跟 dev backup 同 bucket 同 IAM             |
| [Data Protection and Masking Governance (section)](/backend/07-security-data-protection/data-protection-and-masking-governance/)              | Google DLP 是 transformation 工具的代表、章節原則對應 mask / FPE / tokenization / k-anonymity 的選用判讀                                                  |
| [Data Residency Deletion and Evidence Chain (section)](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)      | DLP findings 是 deletion 證據鏈的一部分 — 哪些 PII 在哪些 dataset、deletion 後是否 re-scan verified、findings history 是 GDPR right-to-erasure 的稽核證據 |

## 下一步路由

- 上游：[7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)、[7.11 資料駐留、刪除與證據鏈](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)
- 平行：[Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)、[Cloud-native data policy](/backend/07-security-data-protection/vendors/cloud-data-policy/)
- 上下游 IAM：[Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)（DLP service account 治理）、[Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)（FPE / tokenization key）
- SIEM 路由：[Splunk](/backend/07-security-data-protection/vendors/splunk/)（DLP findings 進 SIEM correlation）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（DLP alert → IR handoff）
- 官方：[Google Cloud Sensitive Data Protection Documentation](https://cloud.google.com/sensitive-data-protection/docs)
