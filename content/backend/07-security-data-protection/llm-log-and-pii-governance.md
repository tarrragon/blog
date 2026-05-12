---
title: "LLM Log 與 PII 治理"
date: 2026-05-12
description: "production LLM 服務的 prompt log 累積、PII 偵測與過濾、保留期限與合規對齊"
tags: ["backend", "security", "llm", "log", "pii", "privacy", "compliance"]
weight: 94
---

本章的責任是把 LLM 服務的 prompt log / response log / context cache 在累積、儲存、保留、刪除四個階段的 PII 治理拆成可操作的判讀。通用詞彙見 backend [pii](/backend/knowledge-cards/pii/)、[data-masking](/backend/knowledge-cards/data-masking/)、[data-classification](/backend/knowledge-cards/data-classification/)、[audit-log](/backend/knowledge-cards/audit-log/) 卡；模型輸出虛構 PII 的特殊議題見 [hallucination](/llm/knowledge-cards/hallucination/) 卡。一般資料保護跟 masking 流程沿用 [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/) 跟 [7.8 資料居住地、刪除與證據鏈](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)、本章聚焦 LLM 場景下的特殊性：prompt 含豐富使用者意圖、response 可能 hallucinate 出 PII、KV cache 跟 context cache 是非典型 log 載體。

## 本章寫作邊界

本章聚焦 production LLM 服務的 log / cache / context 中的 PII 治理特殊性。個人 dev 場景的隱私資料流見 [0.7 隱私資料流](/llm/00-foundations/privacy-data-flow/)；通用資料保護見 7.4；資料居住地與刪除證據鏈見 7.8。

## 本章 threat scope

**In-scope**：prompt log 累積的 PII、response log 中模型 hallucinate 出的 PII、context cache 跟 KV cache 中的殘留、跨地區資料居住地對應、log 保留期限與刪除證據。

**Out-of-scope**（路由到他章）:

- 通用資料保護與 masking → [7.4 data-protection-and-masking-governance](../data-protection-and-masking-governance/)
- 資料居住地與刪除證據鏈 → [7.8 data-residency-deletion-and-evidence-chain](../data-residency-deletion-and-evidence-chain/)
- 通用 audit log → 通用 [audit-log knowledge-card](/backend/knowledge-cards/audit-log/)
- multi-tenant log 隔離 → [llm-multi-tenant-isolation](../llm-multi-tenant-isolation/)
- 偵測訊號 → [llm-as-service-detection-coverage](../llm-as-service-detection-coverage/)

## 從本章到實作

- **Mechanism**：問題節點表 → knowledge-card。
- **Delivery**：交接路由 → `05-deployment-platform / 08-incident-response`。

## LLM 服務的 log 載體

LLM 服務累積的 log / cache 比一般 service 多幾類載體：

| 載體                  | 內容                                                   | 隱私敏感度                         |
| --------------------- | ------------------------------------------------------ | ---------------------------------- |
| Request log（API 層） | endpoint、status、tenant、latency                      | 一般、跟普通 API service 一致      |
| Prompt log            | 完整 prompt 內容（含 system / context / user message） | 高、含使用者意圖、可能含 PII       |
| Response log          | LLM 完整輸出                                           | 高、可能 hallucinate 出 PII        |
| Tool call log         | tool name、arguments、result                           | 高、tool 參數可能含 sensitive 內容 |
| KV cache              | 推論時的 attention 暫存                                | 中、跨 request 殘留可能洩漏        |
| Context cache / RAG   | 持久化的 context、embedding cache                      | 高、含原始文件內容                 |
| Telemetry / metric    | tokens / cost / model / latency 等聚合                 | 一般、用 tenant tag 隔離           |

跟一般 service 的差異點：**Prompt log / Response log 是新類別**、它們含的不是 API meta-data、是使用者實際的「想法 / 內容」、隱私敏感度遠高於一般 API log。

## 分析模型

LLM log 治理依四個階段分析：

1. **累積階段**：哪些載體會累積什麼內容、累積速率多大。
2. **儲存階段**：儲存位置（DB / S3 / SIEM）、加密、訪問權。
3. **保留階段**：保留期限、保留期內的訪問規則。
4. **刪除階段**：刪除觸發條件、刪除證據鏈、合規對應。

## 判讀流程

判讀流程的責任是把「LLM 服務的 log」轉成「合規可審計的 log」。

1. 先盤點所有 log / cache 載體跟對應內容。
2. 再確認 PII 偵測 / masking 在累積階段是否生效。
3. 接著確認儲存跟訪問權跟一般資料保護一致。
4. 最後確認保留期限跟刪除證據鏈跟資料居住地對齊。

## 問題節點（案例觸發式）

| 問題節點                      | 判讀訊號                                                 | 風險後果                            | 前置控制面                                                                                         |
| ----------------------------- | -------------------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------- |
| Prompt log 含 PII 未 mask     | 使用者貼信用卡 / 身分證號、log 完整保留                  | 隱私洩漏、合規違規（GDPR / HIPAA）  | [data-protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)    |
| Response 含 hallucinated PII  | LLM 生成虛構電話 / 地址、log 保留                        | 模型「虛構」也算 PII 處理、合規範圍 | [data-protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)    |
| KV cache 跨 request 殘留 PII  | inference engine 沒清 cache、下個 request 的 dump 看得到 | tenant 間隱私洩漏                   | [llm-multi-tenant-isolation](/backend/07-security-data-protection/llm-multi-tenant-isolation/)     |
| Context cache 跨 session 重用 | 同 user 的 long context cache 被其他 session 共用        | 個人 prompt 洩漏到其他 session      | [data-protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)    |
| 保留期限跟資料居住地不一致    | log 跨地區複製、不同地區保留期限不一                     | 合規對應失效、刪除無法執行          | [data-residency](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/) |
| 刪除證據鏈缺失                | 客戶要求刪除、無法證明已刪除所有副本                     | 合規違規、客戶投訴升級              | [audit-log](/backend/knowledge-cards/audit-log/)                                                   |
| Vendor 政策跟自家政策衝突     | 用雲端 LLM、vendor log 30 天、自家承諾 7 天              | 對外承諾無法兌現                    | [vendor-contract](/backend/knowledge-cards/contract/)                                              |

## 常見風險邊界

風險邊界的責任是界定何時 LLM log 治理已進入高壓狀態。

- Prompt log 含未 mask 的 PII 時、代表 PII 治理在累積階段失效。
- KV cache / context cache 跨 tenant 共用時、代表 isolation 失效（亦見 [llm-multi-tenant-isolation](/backend/07-security-data-protection/llm-multi-tenant-isolation/)）。
- log 保留期限跟資料居住地政策不一致時、代表治理流程不收斂。
- 客戶刪除請求無法產生證據鏈時、代表合規對應失效。

## LLM 場景的特殊判讀

LLM log 治理相對一般資料保護的特殊性：

1. **Prompt 跟 Response 比 API log 隱私敏感度高一個量級**：一般 API log 主要記 endpoint / status / latency、prompt log 記的是使用者實際「在問什麼」、Response log 是模型「在說什麼」。
2. **模型 hallucinate 的 PII 也是 PII**：LLM 生成虛構的姓名 / 電話 / 地址、即使不對應真人、也屬於 PII 處理範圍、需要對應的 masking 跟保留政策。
3. **KV cache 是非典型 log 載體**：傳統 log 治理工具不掃 GPU memory / RAM cache、但這些 cache 可能跨 request / 跨 tenant 殘留 PII；需要 inference engine 配合做 cache 清理。
4. **RAG context 是雙向載體**：RAG 既把 corpus 注入 prompt（corpus 中的 PII 進 log）、也把 user query 注入 corpus（user query 變 future retrieval 的對象）；治理範圍要覆蓋雙向。
5. **vendor 政策直接影響合規承諾**：用雲端 LLM 時、vendor 的 log 保留政策（如 30 天 abuse log）直接限制自家對下游客戶能承諾的最短保留期、合約鏈要對齊。
6. **abuse detection 跟 PII 治理的張力**：abuse detection 需要 log prompt（看 abuse pattern）、PII 治理要求 minimize、兩者要在 mask 後 detection 跟全文 detection 中找平衡。

## 防禦設計的核心原則

1. **累積階段做 PII detection + masking**：log 寫入前過 PII detector、敏感欄位 mask 或不 log。
2. **儲存階段加密 + 訪問權對齊 IAM**：跟一般敏感資料一致。
3. **保留期限明確 + 自動刪除**：用 policy-driven 自動 lifecycle、不依賴人工。
4. **KV cache / context cache 跨 tenant 清理**：inference engine 配合、tenant boundary 明確。
5. **刪除證據鏈**：客戶刪除請求觸發時、產生 audit trail、能證明已刪除所有副本（包含 backup / log archive）。
6. **vendor 政策對齊**：用雲端 LLM 時、vendor 的條款拉進自家政策一致審視。

## 案例觸發參考

LLM log 治理的公開案例累積中、值得追蹤的方向：

- 大型 LLM vendor 的 log 政策變更引發的合規震盪
- 模型 hallucinate 出真人 PII 的訴訟案例
- KV cache 跨用戶洩漏的 incident 報告

LLM-specific 案例累積後會補入 `red-team/cases/llm-log-pii/`。一般資料保護案例見 [7.4 data-protection-and-masking-governance](/backend/07-security-data-protection/data-protection-and-masking-governance/) 跟 [7.8 data-residency-deletion-and-evidence-chain](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)。

> **事實查核註**：LLM log / PII 議題的具體 incident 跟法律判例累積還在早期、各 vendor 政策跟監管要求依時段快速變化、建議引用前以最新的監管文件（GDPR、CCPA、AI Act 等）跟 vendor 當前政策為準。

## 引用標準

| 標準                   | 版本 / 年份 | 適用場景                               |
| ---------------------- | ----------- | -------------------------------------- |
| GDPR                   | 2016/679    | 歐盟 PII 治理                          |
| CCPA / CPRA            | 2020 / 2023 | 加州 PII 治理                          |
| EU AI Act              | 2024        | AI 系統 PII 處理特殊規定               |
| NIST Privacy Framework | 1.0 (2020)  | 隱私治理 reference                     |
| OWASP LLM Top 10       | 2025        | LLM06 Sensitive Information Disclosure |

引用版本與 cadence 規則見 [security-citation-currency-and-precision](/report/security-citation-currency-and-precision/)。Last reviewed: 2026-05-12。

## 下一步路由

- 通用資料保護：[7.4 data-protection-and-masking-governance](/backend/07-security-data-protection/data-protection-and-masking-governance/)
- 資料居住地與刪除：[7.8 data-residency-deletion-and-evidence-chain](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)
- 多租戶 isolation：[llm-multi-tenant-isolation](/backend/07-security-data-protection/llm-multi-tenant-isolation/)
- 偵測訊號：[llm-as-service-detection-coverage](/backend/07-security-data-protection/llm-as-service-detection-coverage/)
- 事件案例工作流：[7.10 incident-case-to-control-workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)
