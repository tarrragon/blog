---
title: "錯誤回報的回饋迴路：request-id、trace 與呈現回報分工"
date: 2026-07-04
description: "consumer 收到錯誤之後怎麼跟 provider 溝通：error 要帶什麼定位鉤子、同一個錯誤怎麼分別投影給使用者與回報、持續錯誤什麼時候該升級"
weight: 24
tags: ["backend", "api-design", "error-contract"]
---

錯誤處理的最後一段是溝通：consumer 收到錯誤、自己處理不了、要回頭問 provider ——「幾點幾分、我呼叫你的什麼 API、拿到什麼錯」。這段對話的品質完全由契約決定：error 帶了可定位的識別符、一句「[request-id](/backend/knowledge-cards/request-id/) 是 X」就能讓 provider 直接調出該次請求的全鏈紀錄；沒帶、consumer 只能用時間與操作描述、provider 在 log 海裡撈 —— debug 成本被推給兩端的人力。不給定位鉤子的成因要分兩種：沒人要求過是優先序問題、提了常能補上；要求了也不修、才是地位不對等的形態 —— 平台省一個欄位、每個 consumer 每次排錯多付幾小時。這種不對等的整體判讀框架在 [11.11 雙向契約](/backend/11-api-design/error-bidirectional-contract/)。

## 定位鉤子：request-id 與 trace 的契約

回饋迴路的最小契約是每個錯誤回應帶一個唯一識別符。成熟先例都這麼做：Stripe 在錯誤物件附 `request_log_url`（直達該次請求的 dashboard 紀錄、見 [11.C36](/backend/11-api-design/cases/error-stripe-error-object/)）、GitHub 的 webhook 每次投遞帶 `X-GitHub-Delivery` GUID（見 [11.C61](/backend/11-api-design/cases/webhook-github-no-retry/)）、RFC 9457 的 `instance` 欄位（識別該次 problem occurrence 的 URI）可承擔類似角色（見 [11.C35](/backend/11-api-design/cases/error-rfc9457-problem-details/)）。契約的兩半：provider 承諾這個 id 在自己的 log 與 trace 系統裡查得到、且保留得比 consumer 的排錯周期長（多久、寫進文件）；consumer 的義務是把它記進自己的錯誤 log —— 收到錯誤時丟棄 id、回報時就退回「大概幾點」。

id 能定位「單跳」、trace 才能定位「全鏈」。一個請求跨五個服務、provider 的第一層 log 只能看到自己這一跳 —— 要從 consumer 回報的識別符追到深處哪個服務出錯、靠的是 [trace context](/backend/knowledge-cards/trace-context/) 的傳播義務：W3C Trace Context 規定收到 `traceparent` header 的服務 MUST 往 outgoing request 傳、[trace-id](/backend/knowledge-cards/trace-id/) 全鏈不變（見 [11.C76](/backend/11-api-design/cases/trace-w3c-trace-context/)）。這條 MUST 是回饋迴路的規範地基 —— 任何一跳斷掉傳播、consumer 手上的 id 就只能追到斷點。同一份規範也內建信任邊界：security boundary 可以 restart trace（provider 不必信外部給的 trace-id）、無效 id MUST ignore —— 對外的 API 通常回自己生成的 request-id 給 consumer、內部用 trace-id 關聯、兩者在 gateway 對接（此對接模式為常見實務、非規範明文）。trace 系統本身的建置屬 [04 可觀測性](/backend/04-observability/)（主流實作生態是 OpenTelemetry）、本文只收契約面：id 要不要給、給了承諾什麼。

## 同一個錯誤、兩種投影：呈現與回報

錯誤內容要分受眾投影、而且兩種投影的組成幾乎相反。給終端使用者呈現的：友善、可行動、不含技術細節（AIP-193 的 `LocalizedMessage` 層、見 [11.C75](/backend/11-api-design/cases/errorchain-aip193-error-content/)）—— 使用者不需要知道是哪個服務的哪類錯誤、需要知道「現在能做什麼」。回報給 provider 的：機器碼（type/code 或 reason/domain）、request-id 或 trace-id、時間戳 —— 全是使用者不需要、定位卻缺一不可的欄位。

實務上最常見的組合是「generic 訊息加識別符」：畫面上顯示友善訊息與一個錯誤編號、使用者回報時唸出編號即可。要標明的邊界：OWASP 的 error handling 指南只要求 generic response 加 server-side log、沒有規範「回傳識別符給使用者」這一段（見 [11.C77](/backend/11-api-design/cases/errorchain-owasp-error-handling/)）—— 這個組合是業界常見實務、識別符部分的規範根據是 Trace Context 與各 vendor 的 request-id 慣例、不是 OWASP。consumer 端的落地判準：錯誤呈現層跟錯誤上報層分開寫 —— 呈現層消費 LocalizedMessage 類欄位、上報層把完整 error 物件（含 id）送進自己的 log 與監控、兩層各取所需、不互相污染。

## 什麼時候該升級：偶發與持續的判讀

回報值不值得、看錯誤的節奏。consumer 端要能區分三種：偶發（單一請求失敗、retry 成功：分散式系統的日常、記 log 不動作）；持續（同一類錯誤連續出現、retry 無效、circuit breaker 開始跳：該檢查是自己的用法錯還是對方壞了）；異常放大（錯誤率突然跳升 —— 對照 provider 的 status page、確認是不是對方的事故）。這條判讀線的量化工具（錯誤率、[SLO](/backend/knowledge-cards/sli-slo/)、告警閾值）屬 [04 可觀測性](/backend/04-observability/) 的範圍、契約面的要求只有一條：provider 要有一個 consumer 查得到的健康狀態出口（[status page](/backend/knowledge-cards/status-page/) 或 [health endpoint](/backend/knowledge-cards/health-check/)）—— 沒有它、每個 consumer 在事故時都會打 support 問「是不是你們壞了」、支援量在最糟的時刻放大。

provider 側的鏡像責任：把 consumer 的回報當訊號源。同一個 request-id 被多個 consumer 回報、比監控告警更早指出問題；回報的摩擦越低（id 好找、回報入口明確）、這個訊號源越有效 —— 讓 consumer 好回報、是 provider 給自己買的免費監控。

## 下一步路由

- 雙向契約的框架：[11.11 Status 與錯誤的雙向契約](/backend/11-api-design/error-bidirectional-contract/)
- 錯誤內容的受眾分層：[錯誤傳播與信任邊界](/backend/11-api-design/error-propagation-trust-boundary/)
- trace 傳播的機制面：[4.3 tracing 與 context link](/backend/04-observability/tracing-context/)
- error rate 與 SLO 的訊號設計：[4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/)
- 診斷欄位的觀測動機（本篇契約欄位的另一半）：[4.19 Debuggability by Design](/backend/04-observability/debuggability-by-design/)
- 錯誤格式的欄位設計：[11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
