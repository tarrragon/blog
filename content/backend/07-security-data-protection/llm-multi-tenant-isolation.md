---
title: "LLM 多租戶推論隔離"
date: 2026-05-12
description: "production LLM 服務的多租戶隔離：KV cache 不共享、log / model artifact 隔離、跨用戶 prompt 洩漏面"
tags: ["backend", "security", "llm", "multi-tenant", "isolation", "kv-cache"]
weight: 92
---

本章的責任是把 LLM 推論服務的多租戶隔離問題拆成可操作的判讀節點。LLM 服務的隔離議題在一般 multi-tenant 隔離（compute / network / data、見 [tenant-boundary](/backend/knowledge-cards/tenant-boundary/)）之上、多了 [KV cache](/llm/knowledge-cards/kv-cache/)（特別是 [prefix cache](/llm/knowledge-cards/prefix-cache/) 重用）、prompt log、model artifact 訪問權三個 LLM-specific 層、本章聚焦這些差異。一般 multi-tenant 隔離原則沿用 [7.2 身分授權邊界](/backend/07-security-data-protection/identity-access-boundary/) 跟 [7.4 供應鏈](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)。

## 本章寫作邊界

本章聚焦 production LLM 推論的多租戶 isolation 特殊性。team / 個人 dev 場景的「多人共用本地 server」見 [llm/6.5 跨進 production 的 routing 中樞](/llm/06-security/routing-to-production-security/)；通用 IAM / 服務間信任邊界見 7.2。

## 本章 threat scope

**In-scope**：KV cache 跨租戶洩漏、prompt log 隔離、模型 artifact 訪問權、batch 推論的順序敏感性、tenant-scoped rate limit、共用 GPU 上的記憶體殘留。

**Out-of-scope**（路由到他章）：

- 通用 IAM / 服務間信任 → [7.2 identity-access-boundary](../identity-access-boundary/)
- [workload identity](/backend/knowledge-cards/workload-identity/) → [7.7 workload-identity-and-federated-trust](../workload-identity-and-federated-trust/)
- log / PII 治理 → [llm-log-and-pii-governance](../llm-log-and-pii-governance/)
- model artifact 供應鏈 → [llm-deployment-supply-chain](../llm-deployment-supply-chain/)
- 入口治理 → [7.3 entrypoint-and-server-protection](../entrypoint-and-server-protection/)

## 從本章到實作

- **Mechanism**：問題節點表 → knowledge-card → 看具體機制。
- **Delivery**：交接路由 → `05-deployment-platform / 06-reliability / 08-incident-response`。

## LLM 多租戶隔離的三個 LLM-specific 層

跟一般 service 的多租戶隔離（compute / network / data）相比、LLM 推論服務多了三個層次：

1. **KV cache 層**：[KV cache](/llm/knowledge-cards/kv-cache/) 是推論時的 attention 暫存、跨 request 可能重用（prefix cache、shared prefix optimization）；跨租戶共用 cache 是直接的資料洩漏面。
2. **prompt log 層**：production LLM 服務通常會 log prompt + response 用於 debug / billing / abuse detection；log 的隔離與保留期限直接影響跨租戶洩漏風險。
3. **model artifact 訪問權**：production 可能部署多個 fine-tuned 模型（如 customer-specific 模型）、模型本身是 sensitive artifact、訪問權要對齊 IAM。

## 分析模型

production LLM 推論的多租戶隔離依四個層次分析：

1. **memory 層**：GPU VRAM、CPU RAM 中的 KV cache 跟模型權重、跨 request / 跨租戶的殘留與共享邊界。
2. **storage 層**：模型 artifact、prompt log、context cache 在儲存層的隔離。
3. **identity 層**：tenant identity 怎麼帶到 inference call、rate limit / quota 怎麼按租戶分。
4. **observability 層**：metric / log / trace 中的 tenant tag、跨租戶分析的允許範圍。

## 判讀流程

判讀流程的責任是把「能服務多個租戶的 LLM 服務」轉成「租戶間資料不互相洩漏的 LLM 服務」。

1. 先確認 tenant identity 從 API gateway 到 inference call 的傳遞路徑。
2. 再確認 KV cache、prompt log、model artifact 各自的隔離邊界。
3. 接著確認 GPU 記憶體中的跨 request 殘留是否清理。
4. 最後交接到偵測流程、確認跨租戶異常能被識別。

## 問題節點（案例觸發式）

| 問題節點                           | 判讀訊號                                               | 風險後果                                                  | 前置控制面                                                                                      |
| ---------------------------------- | ------------------------------------------------------ | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| KV cache 跨租戶共享                | shared prefix optimization 沒按 tenant key 分桶        | 租戶 A 的 prompt prefix 被租戶 B 看見                     | [data-protection](/backend/07-security-data-protection/data-protection-and-masking-governance/) |
| prompt log 沒分租戶                | 集中 log、查詢時 tenant filter 缺失                    | abuse detection 跨租戶看 prompt 內容、隱私違規            | [audit-log](/backend/knowledge-cards/audit-log/)                                                |
| 共用 GPU 上的記憶體殘留            | 推論完未清 VRAM、下一個 request 可能 dump 到前一個內容 | 同 GPU 上的不同 tenant 之間殘留洩漏                       | [secret-management](/backend/knowledge-cards/secret-management/)                                |
| tenant-scoped rate limit 失效      | 同一 API key 限流、租戶被互相 DoS                      | 大租戶吃光 quota、其他租戶無法用                          | [rate-limit](/backend/knowledge-cards/rate-limit/)                                              |
| model artifact 訪問權混亂          | fine-tuned 模型路徑可被其他 tenant 載入                | 客戶模型被其他客戶使用、模型權重洩漏                      | [identity-access-boundary](/backend/07-security-data-protection/identity-access-boundary/)      |
| batch 推論的 cross-tenant 順序敏感 | dynamic batching 把不同 tenant 的 request 合批         | 一個 tenant 的 OOM / 長 prompt 影響其他 tenant 的 latency | [contract](/backend/knowledge-cards/contract/)                                                  |

## 常見風險邊界

風險邊界的責任是界定何時 LLM 多租戶 isolation 已進入高壓狀態。

- KV cache 共用範圍跨越 tenant 邊界時、代表記憶體層 isolation 失效。
- prompt log 沒帶 tenant tag、或 tag 後仍可跨 tenant 查時、代表 log 層 isolation 不足。
- 模型 artifact 訪問權跟 IAM 解耦時、代表 identity 層 isolation 不足。
- 推論 batch 對 tenant boundary 不敏感時、代表 batch 層的 noisy-neighbor 風險上升。

## LLM 場景的特殊判讀

LLM 多租戶 isolation 相對一般 multi-tenant 服務的特殊性：

1. **KV cache 是有用但敏感的優化**：shared prefix cache（如多 tenant 用同一 system prompt）能省大量 prefill 算力、但跨 tenant 共用就是洩漏。判讀：可以 share 同 tenant 內的 prefix、不能 share 跨 tenant。
2. **prompt log 含豐富使用者意圖**：相比一般 API log 主要記 endpoint / status code、LLM prompt log 記的是「使用者實際在問什麼」、隱私敏感度高得多。
3. **GPU 是稀缺資源、共用比 CPU 多**：production LLM 服務常多 tenant 共用同卡、isolation 比一般 multi-tenant 服務（每 tenant 跑獨立 pod）更難做、需要更細的 batch 跟 memory 管理。
4. **fine-tuned 模型本身是 customer asset**：模型訓練成本高、權重是客戶 IP、訪問權混亂直接是 IP 外洩。
5. **「LLM 記住 cross-tenant 資訊」的疑慮**：使用者常擔心 LLM 把 A tenant 的 prompt「記住」洩漏給 B tenant；對 inference-only 服務（無 fine-tune）這不發生（模型權重 immutable）、有 fine-tune 時要看 training data 隔離。

## 案例觸發參考

LLM 多租戶 isolation 的公開案例累積中、本章先沿用通用 multi-tenant 案例：

- 一般 multi-tenant 隔離案例見 [7.2 身分授權邊界](/backend/07-security-data-protection/identity-access-boundary/)。
- LLM-specific 案例累積後會補入 `red-team/cases/llm-multi-tenant/`。

> **事實查核註**：LLM 多租戶 isolation 的公開事件案例還在早期、社群上有些「LLM A 的 system prompt 被 B 看到」等報告、多數屬 prompt injection 範疇而非 cache 洩漏。建議引用前以最新的 OWASP LLM Top 10 跟具體 vendor 的 incident 公告為準。

## 引用標準

| 標準                                       | 版本 / 年份 | 適用場景                                |
| ------------------------------------------ | ----------- | --------------------------------------- |
| NIST SP 800-207（Zero Trust Architecture） | 2020        | tenant boundary 零信任模型 reference    |
| OWASP LLM Top 10                           | 2025        | LLM application security 通用 reference |
| CSA Cloud Controls Matrix                  | v4 (2021)   | multi-tenant cloud 控制 reference       |

引用版本與 cadence 規則見 [security-citation-currency-and-precision](/report/security-citation-currency-and-precision/)。Last reviewed: 2026-05-12。

## 下一步路由

- 身份授權邊界：[7.2 identity-access-boundary](/backend/07-security-data-protection/identity-access-boundary/)
- log 治理：[llm-log-and-pii-governance](/backend/07-security-data-protection/llm-log-and-pii-governance/)
- agent prompt injection 後果：[llm-prompt-injection-in-agent](/backend/07-security-data-protection/llm-prompt-injection-in-agent/)
- 部署平台：`05-deployment-platform`
- 可靠性：`06-reliability`
