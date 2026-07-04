---
title: "11.9 對外流量語意"
date: 2026-07-03
description: "rate limit 對消費者承諾什麼、429 與 Retry-After 怎麼設計、配額 header 該不該信 — 限流作為契約的語意設計"
weight: 9
tags: ["backend", "api-design", "rate-limit"]
---

限流的執行機制在 gateway、限流的對外語意在契約 — 本章收後者。消費者面對限流時要回答的問題全部來自介面設計：怎麼知道額度多少、怎麼知道快用完了、被擋之後等多久重試。執行面的 token bucket、分散式計數器屬 [05 部署平台](/backend/05-deployment-platform/) 的入口層範圍（該模組現有章節尚未主寫限流實作、屬其 backlog）；本章的問題是這些機制對外承諾成什麼語意。

## 承諾邊界：配額資訊是預警、不是保證

限流語意的第一條設計原則是明確劃出承諾邊界。IETF 的 RateLimit header draft（active、v11、引用需標狀態）把配額資訊拆成兩個 header — `RateLimit-Policy`（靜態政策：quota、window、partition key）與 `RateLimit`（動態剩餘量）— 並明文「client MUST NOT assume 正配額保證下一請求會被服務」（見 [11.C42](/backend/11-api-design/cases/ratelimit-ietf-header-fields/)）。兩個設計都值得借用：政策與即時狀態拆開、政策可快取、狀態逐請求變動；informational only 條款把配額 header 定位成禮貌性預警而非 SLA — 服務端保留在異常流量下提前收緊的權利、消費者的正確姿勢是把 429 處理寫對、而非精算剩餘配額。

## 429 與 Retry-After：被擋之後的契約

拒絕本身也是介面。可承諾的最小集合：status 用 429（讓消費者與中介層知道「可重試、但要等」、跟終態 4xx 區分、錯誤分類見 [11.4](/backend/11-api-design/error-model-design/)）；`Retry-After` 給等待時間、且服務端說到做到 — 消費者等滿再來就該被服務、否則 Retry-After 淪為裝飾、消費者退回盲目退避。GitHub 的文件在這條上有可指出的語意瑕疵：超限回 403 或 429、文件未明確劃分兩者的使用時機（見 [11.C43](/backend/11-api-design/cases/ratelimit-github-primary-secondary/)）— 消費者要同時處理兩種 status、分支邏輯多一倍。設計新 API 時可直接採納的判準：拒絕的 status 只用一個。

消費端的配套是 backoff 加 jitter（完整的重試合判、集體層去同步與 retry 預算、主寫在 [接收方的重試決策](/backend/11-api-design/consumer-retry-decision/)）— 限流語意跟冪等語意在消費端匯合：429 之後的重送、要嘛操作本身冪等、要嘛帶 idempotency key（[11.8](/backend/11-api-design/api-idempotency-design/)）。

## 單一維度擋不住真實濫用

GitHub 的雙層限流揭露配額設計的一個實證：primary limit（每小時總額度）之外、還有 secondary limits — 並發上限、單端點吞吐、CPU 時間、內容建立速率（見 [11.C43](/backend/11-api-design/cases/ratelimit-github-primary-secondary/)）。存在本身就是判讀：單一維度的請求計數擋不住真實濫用模式 — 額度內的高並發、額度內的單端點轟炸、額度內的重查詢。設計配額時從「要保護什麼資源」反推維度、而非從「一小時幾次」起手。

同一案例也記錄了 header 命名的遷移期現實：GitHub 的 `x-ratelimit-*` 是前標準時代的事實慣例、與 IETF 標準命名並存 — 新 API 該出標準 header、消費端 SDK 仍要能讀 x- 系、兩者會共存很久。

## 成本模型：per-request 假設的破裂

「一個請求算一次」的配額假設、在請求成本不是常數的風格下失效。GitHub 的 GraphQL API 為此建立 point system：依 query 的展開規模計算成本、配額按點數計、另設結構上限當靜態防線、且成本對消費者可預估可查詢（參數細節與機制展開主寫在 [GraphQL 執行成本與攻擊面](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/)、案例 [11.C19](/backend/11-api-design/cases/graphql-github-cost-rate-limiting/)）。判準層的收穫有兩條：請求成本變動大的介面（GraphQL、批次、重查詢）、配額要計成本而非計次；成本模型本身要對消費者透明可預估 — 消費者無法預估成本、就無法設計合規的 client。執行成本的機制細節（resolver 展開、N+1、persisted queries）主寫在 [GraphQL 執行成本與攻擊面](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/)。

## 常見設計錯誤

- **限流回 500**：消費者把它當服務故障告警、但成因是自身超額 — 語意錯位、429 才能觸發正確的消費端行為。
- **Retry-After 不準**：等滿再來還是被擋、消費者棄用該 header、生態退化成盲目重試。
- **配額只在文件、不在 header**：消費者無法程式化管理額度、只能在被擋下後才發現額度邊界。
- **無 burst 設計**：嚴格平滑限流把正常的批次行為（頁面載入拉 10 個資源）也擋掉 — 政策要區分持續超額與瞬時尖峰。

## 下一步路由

- 執行機制與 gateway 層：[05 部署平台與網路入口](/backend/05-deployment-platform/)、[5.3 Load Balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)（限流實作章屬 05 backlog）
- 高峰期的容量面：[9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)
- 429 後的重送安全：[11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
