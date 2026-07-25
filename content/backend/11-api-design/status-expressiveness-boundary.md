---
title: "Status 裝不下的東西：部分成功、延遲失敗、gateway 歧義"
date: 2026-07-04
description: "單一 status 表達不了部分成功、延遲失敗與 gateway 歧義時怎麼辦：把狀態下放 body 讓中介層變盲、或收窄語意保持 status 恆為真"
weight: 21
tags: ["backend", "api-design", "error-contract"]
---

status code 是整條 HTTP 鏈上被最多角色消費的一個欄位：consumer 的分支邏輯、中介層的 retry 與快取、監控的錯誤率圖表、全部只看這一格。它的表達力邊界因此是契約設計的硬約束 —— 有三種情況、一個 status 放不下事實：多個獨立結果（部分成功）、跨越時間的結果（先接受後失敗）、無法確定的結果（gateway 分不出上游做了沒）。本文攤開三種邊界、以及每種邊界下兩端各要扛什麼。本文掛在 [11.11 雙向契約](/backend/11-api-design/error-bidirectional-contract/)。

## 裝不下多個結果：部分成功的兩條路線

批次操作 5 筆裡 3 成功 2 失敗、一個 status 表達不了。規範與大廠給了方向相反的兩條路線、對照著讀最清楚。

WebDAV 的 207 Multi-Status 是「下放」路線：頂層回 207、每個資源的真實狀態放進 body 的 multistatus 結構、規範明文接收方「needs to consult the contents of the multistatus response body」、207 可以同時用在全成功、部分成功、全失敗（見 [11.C64](/backend/11-api-design/cases/status-207-multistatus-rfc4918/)）。這條路線換到表達力、代價由 consumer 端整條鏈承擔：generic client 與中介層（retry、快取、監控）只看 status line、207 對它們一律是成功 —— 部分失敗只有讀得懂 body schema 的 client 看得到、監控圖表上這批半失敗的請求全是綠的。業界更常見的下放形態其實是 200 加 per-item errors（Elasticsearch 的 bulk API、GraphQL 的 errors 欄位都是這條路）：中介層盲化問題與 207 同構、而且連 207 那個「非常規 status」的警示訊號都沒有。

Google AIP 是「收窄」路線、而且立場寫得很硬：AIP-193 明文「APIs should not support partial errors」—— 部分錯誤把錯誤碼搬進 response body、consumer 就得寫專用錯誤處理、通用機制全部失效（見 [11.C65](/backend/11-api-design/cases/status-google-aip-partial-success/)）。批次方法的配套規則是一條原子性階梯：同步批次必須原子（全成或全敗、讓單一 status 恆為真；唯讀批次更直接禁止部分成功）；寫入批次要部分成功、必須升級成非同步 operation、失敗明細結構化進 metadata 的 `failed_requests` map、且 request 要帶 `return_partial_success` 讓 consumer 顯式 opt-in。

兩條路線的差異正是雙向契約的分野：207 把解析責任**默默**推給 consumer（收到的人自己發現要讀 body）；AIP 把同一份責任變成**顯式同意**（consumer 用 opt-in flag 聲明「我會處理部分失敗」、provider 才回部分成功）。設計判準由此而來 —— 部分成功的設計題是「consumer 有沒有明知道自己要處理它」、能不能做反而其次；讓中介層誤判的表達方式（200 或 207 包部分失敗、但消費端沒有 opt-in）是把成本外部化的形態。

## 裝不下時間軸：202 之後才失敗

202 Accepted 的規範定位是刻意不承諾。RFC 9110 原文：「The 202 response is intentionally noncommittal」、且「There is no facility in HTTP for re-sending a status code from an asynchronous operation」（見 [11.C66](/backend/11-api-design/cases/status-202-noncommittal-rfc9110/)）—— 一旦回了 202、HTTP 協定不再提供任何管道通知最終失敗。status 只描述「收到當下」、描述不了「之後會不會成」。

責任移轉因此是 202 的內建性質、兩端都要有對應動作。provider 端：202 的回應要指向一個 status monitor（規範用「ought to」、實務上是 Operation resource —— 可輪詢的長時操作資源、設計見 [11.C44 AIP-151](/backend/11-api-design/cases/longrun-google-aip151/) 與 [11.7 的長時操作段](/backend/11-api-design/collection-interface-design/)）—— 只回 202 不給查詢入口、等於把「結果去哪了」變成 consumer 的問題。consumer 端：把 202 當終局成功、最終失敗就靜默消失 —— 拿到 202 的正確做法是記下 operation 入口、把「確認終局」排進自己的流程。同一個時間軸問題在 webhook 方向更隱蔽：先回 2xx ack、背景處理才失敗 —— ack 的是「收到」、不是「處理成功」、對帳兜底因此是 consumer 的常備件（見 [webhook 對外承諾](/backend/11-api-design/styles/realtime/realtime-webhook-contract/)）。

## 裝不下不確定性：502/504 的 retry 歧義

RFC 9110 對 502 與 504 的定義只描述 gateway 自己的觀察：收到無效回應（502）、沒收到及時回應（504）—— 規範沒有任何欄位區分「上游根本沒收到請求」與「上游執行了、只是回應沒回來」（見 [11.C67](/backend/11-api-design/cases/status-502-504-gateway-ambiguity/)）。

這個缺口的工程後果（此為從定義出發的推導、非 spec 明文）：connect timeout（請求沒送到、重送安全）跟 read timeout（請求已執行、重送非冪等操作會重複執行）在 consumer 端拿到同一個 504、而兩者的 retry 安全性相反。status 在這裡不是裝不下多個結果、是裝不下「連 gateway 自己都不知道」的不確定性 —— 補強手段全在 status 之外：操作設計成冪等、或帶 [idempotency key](/backend/knowledge-cards/idempotency-key/) 讓重送安全（[11.8](/backend/11-api-design/api-idempotency-design/) 主寫）、上游做去重。consumer 收到 502/504 的判讀規則因此很短：不確定上游做了沒、就當作做了 —— 除非操作冪等或帶了 key、否則重送前先查。

## 三種邊界的共同判準

三種邊界指向同一條設計原則：status 是給整條鏈看的最低契約、它裝不下的資訊要嘛收窄語意讓它恆為真（原子批次）、要嘛在 status 之外建立顯式的補充通道（operation resource、opt-in 的部分失敗結構、idempotency key）—— 而不是把資訊藏進只有一方讀得懂的地方、讓另一端與中介層在不知情下做錯決策。

## 下一步路由

- 雙向契約的框架：[11.11 Status 與錯誤的雙向契約](/backend/11-api-design/error-bidirectional-contract/)
- 拿到模糊 status 之後的重試合判：[接收方的重試決策](/backend/11-api-design/consumer-retry-decision/)
- 重送安全的機制：[11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/)
- 長時操作的查詢入口：[11.7 集合介面設計](/backend/11-api-design/collection-interface-design/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
