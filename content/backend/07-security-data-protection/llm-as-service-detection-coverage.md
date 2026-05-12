---
title: "LLM Service 偵測訊號覆蓋"
date: 2026-05-12
description: "production LLM 服務的 detection 訊號設計：tool call 異常模式、prompt injection 觸發徵兆、abuse 跟濫用模式、跟既有 detection-coverage 框架的接合"
tags: ["backend", "security", "llm", "detection", "monitoring", "abuse"]
weight: 95
---

本章的責任是把 LLM 服務的異常行為訊號、納入 [7.13 偵測覆蓋與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 的既有偵測框架。LLM 服務的偵測訊號跟一般 service 的差異在「需要看 prompt / response / tool call 三個語意層」、不只是 traffic 跟 error rate；LLM-specific 訊號的關鍵範例是 [refusal rate](/llm/knowledge-cards/refusal-rate/)、通用 alerting 詞彙見 [alert](/backend/knowledge-cards/alert/)、[alert-fatigue](/backend/knowledge-cards/alert-fatigue/)、[symptom-based-alert](/backend/knowledge-cards/symptom-based-alert/) 卡。本章聚焦這層特殊性、通用偵測流程沿用 7.13。

## 本章寫作邊界

本章聚焦 production LLM 服務的偵測訊號設計：tool call 異常、prompt injection 觸發徵兆、abuse 模式、cost / token 異常、模型行為偏移。通用偵測平台選型與 SIEM / SOAR 整合屬 `04-observability` 跟 7.13。

## 本章 threat scope

**In-scope**：LLM 服務的特殊偵測訊號（prompt / response / tool call 語意層）、agent 行為異常、abuse / 濫用模式、cost 異常、模型 drift。

**Out-of-scope**（路由到他章）：

- 通用偵測覆蓋與訊號治理 → [7.13 detection-coverage-and-signal-governance](../detection-coverage-and-signal-governance/)
- 偵測平台 → `04-observability`
- IR 工作流 → [7.10 incident-case-to-control-workflow](../incident-case-to-control-workflow/)
- agent prompt injection 後果 → [llm-prompt-injection-in-agent](../llm-prompt-injection-in-agent/)
- log / PII 治理 → [llm-log-and-pii-governance](../llm-log-and-pii-governance/)

## 從本章到實作

- **Mechanism**：問題節點表 → knowledge-card。
- **Delivery**：交接路由 → `04-observability` 偵測平台、`08-incident-response` IR 流程。

## LLM 服務的偵測語意層

一般 service 的偵測訊號集中在 traffic / error / latency / auth event；LLM 服務增加了三個語意層：

1. **prompt 語意層**：使用者輸入的內容模式、prompt 長度分布、特殊 token / pattern 出現頻率。
2. **response 語意層**：模型輸出的內容類型、refusal rate、輸出長度分布、tool call 出現模式。
3. **tool call 序列層**：agent 場景下、tool call 順序、頻率、跨 tool 依賴模式。

這三層的訊號通常無法用傳統 monitoring stack 直接抓、需要 LLM-specific 的 telemetry pipeline。

## 分析模型

LLM 服務偵測依四個層次設計訊號：

1. **traffic 層**：跟一般 service 一致、QPS / latency / error rate / auth event。
2. **content 層**：prompt 跟 response 的語意特徵（長度、token 類型、敏感詞）。
3. **behavior 層**：tool call 序列、agent loop 步數、cross-service call pattern。
4. **cost 層**：token / call 累積、cost 異常（單一 tenant 突然暴增、cost-per-result 飆高）。

## 判讀流程

判讀流程的責任是把「能偵測一般服務異常的偵測平台」擴成「能偵測 LLM 特殊異常的偵測平台」。

1. 先盤點現有偵測平台覆蓋哪些訊號類別、哪些是 LLM-specific 缺漏。
2. 再設計 LLM-specific 訊號的採集路徑（log → metric → alert）。
3. 接著定義 baseline 跟 anomaly threshold、避免假陽性過高。
4. 最後交接到 IR 流程、確認 alert 能對應到具體處置動作。

## 問題節點（案例觸發式）

| 問題節點                 | 判讀訊號                                                 | 風險後果                             | 前置控制面                                                                                                                 |
| ------------------------ | -------------------------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| tool call 序列異常       | 同一 session 內 tool call 暴增、跨 tool 跳躍頻繁         | injection 觸發 agent 進入非預期 loop | [detection-coverage-and-signal-governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) |
| Refusal rate 突然下降    | 模型開始接受原本拒絕的 prompt                            | 對齊被繞過、injection 攻擊在進行     | [symptom-based-alert](/backend/knowledge-cards/symptom-based-alert/)                                                       |
| token usage 異常飆升     | 單一 tenant cost 跳一個量級                              | abuse / DoS / 自動化攻擊             | [rate-limit](/backend/knowledge-cards/rate-limit/)                                                                         |
| prompt 含 injection 模式 | "ignore previous instructions" / 大量 system prompt 字樣 | 已知 injection 模式試探              | [symptom-based-alert](/backend/knowledge-cards/symptom-based-alert/)                                                       |
| response 含 PII 模式     | 模型輸出含信用卡 / 身分證號碼 pattern                    | 訓練資料洩漏 / hallucinate PII       | [data-protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)                            |
| 跨 tenant pattern 相似性 | 不同 tenant 同時出現相似異常 prompt                      | 協同攻擊 / botnet                    | [symptom-based-alert](/backend/knowledge-cards/symptom-based-alert/)                                                       |
| 模型 drift               | 同 prompt 在不同時段 response 品質明顯變化               | 模型版本切換問題 / vendor 端變動     | [contract-test](/backend/knowledge-cards/contract/)                                                                        |

## 常見風險邊界

風險邊界的責任是界定何時 LLM 偵測覆蓋已進入高壓狀態。

- tool call 序列、refusal rate、token usage 任一缺乏 baseline 時、代表 content / behavior / cost 層偵測不足。
- prompt injection 已知 pattern 沒列入 alert 時、代表已知威脅未覆蓋。
- 跨 tenant 模式分析缺失時、代表協同攻擊偵測能力不足。
- alert 沒對應到 IR 處置動作時、代表偵測與處置斷層。

## LLM 場景的特殊判讀

LLM 服務偵測相對一般 service 偵測的特殊性：

1. **訊號是非結構化的**：prompt / response 是自由文字、不是 status code 跟 endpoint name；偵測 pipeline 需要 NLP / embedding 等手段、不只是 grep / regex。
2. **baseline 漂移**：使用者行為跟 LLM 使用模式持續演進、baseline 比一般 service 更需要 rolling window 更新。
3. **「正常」prompt 跟「injection」prompt 的邊界模糊**：教 LLM 寫 prompt injection 教材的使用者、prompt 內容跟攻擊者的測試 prompt 形式上類似；偵測需要結合 intent 跟 context。
4. **cost-based detection 是 LLM 特有的 strong signal**：傳統 service 的「cost」對應 infra、容易被視為運維議題；LLM service 的 token cost 直接連結到 abuse、cost 異常本身是強訊號。
5. **跨 tenant 相關性分析**：協同攻擊跟 botnet 在 LLM 服務上、可能用相同 prompt 在不同帳號試探；跨 tenant pattern 分析比一般 service 更有用。
6. **模型 vendor 是 third-party 失敗點**：vendor 端的模型更新、API 限流、政策變更會直接影響服務行為；需要 vendor-side 訊號（status page、release notes）納入偵測範圍。

## 訊號設計的核心原則

1. **traffic 層沿用既有監控**：QPS / latency / error rate / 5xx、跟一般 service 一致、用既有平台。
2. **content 層需建 NLP pipeline**：prompt 長度分布、敏感詞 detector、injection pattern detector、response PII detector。
3. **behavior 層追蹤 tool call 序列**：每個 session 的 tool call DAG、跟 baseline 比對。
4. **cost 層做 tenant-scoped baseline**：每個 tenant 的 token / cost 用 rolling baseline、突破 threshold 觸發 alert。
5. **跨 tenant pattern 用 embedding 相似性**：用 prompt embedding 做相似性分析、找協同攻擊。
6. **vendor-side 訊號納入**：vendor status page、release notes、incident 公告應該 watch、作為 external signal source。

## 案例觸發參考

LLM 服務偵測的公開案例累積中、值得追蹤的方向：

- 大型 LLM vendor 的 abuse detection pipeline 公開介紹
- prompt injection 攻擊在 production agent 場景的真實案例
- token usage abuse 的 botnet 案例

LLM-specific 偵測案例累積後會補入 `red-team/cases/llm-detection/`。一般偵測案例見 [7.13 detection-coverage-and-signal-governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)。

> **事實查核註**：LLM 服務的偵測 baseline、attack pattern、defense 工具都在快速演進、本章列舉的訊號類型為 2026 年 5 月常見社群實踐、具體 threshold、tooling、commercial product 依時段變化、引用前以最新研究跟產品文件為準。

## 引用標準

| 標準             | 版本 / 年份 | 適用場景                                    |
| ---------------- | ----------- | ------------------------------------------- |
| MITRE ATLAS      | continuous  | AI 系統威脅戰術 / 偵測戰術 reference        |
| OWASP LLM Top 10 | 2025        | LLM application security 通用 reference     |
| NIST AI RMF      | 1.0 (2023)  | AI 系統風險偵測 reference                   |
| MITRE ATT&CK     | continuous  | 一般系統威脅戰術、部分適用 LLM 服務基礎設施 |

引用版本與 cadence 規則見 [security-citation-currency-and-precision](/report/security-citation-currency-and-precision/)。Last reviewed: 2026-05-12。

## 下一步路由

- 通用偵測覆蓋：[7.13 detection-coverage-and-signal-governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 偵測平台：`04-observability`
- agent prompt injection 後果：[llm-prompt-injection-in-agent](/backend/07-security-data-protection/llm-prompt-injection-in-agent/)
- log / PII 治理：[llm-log-and-pii-governance](/backend/07-security-data-protection/llm-log-and-pii-governance/)
- 事件案例工作流：[7.10 incident-case-to-control-workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)
