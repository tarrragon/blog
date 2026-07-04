---
title: "11.4 錯誤模型設計"
date: 2026-07-03
description: "錯誤該分幾類、格式怎麼定才有演化空間、機器判讀跟人類訊息怎麼分工 — 錯誤作為契約一級公民的設計判準"
weight: 4
tags: ["backend", "api-design", "error-model"]
---

錯誤模型是契約的一級公民：消費者的重試邏輯、監控的告警規則、前端的使用者訊息、全部建立在錯誤回應的結構上。錯誤格式一旦被依賴、變更成本跟正常回應完全相同（承諾成本結構見 [11.1](/backend/11-api-design/api-boundary-responsibility/)）、常見的失衡是設計精力集中在成功路徑、錯誤格式在第一個 handler 裡即興決定 — 之後每個新錯誤都在複製那次即興。本章收 producer 側的分類與格式設計；consumer 收到錯誤之後怎麼判讀、重試、回報、收在 [11.11 Status 與錯誤的雙向契約](/backend/11-api-design/error-bidirectional-contract/)。

## 第一刀：可重試與終態

錯誤分類的第一個維度是對消費者行為的指示：這個錯誤重試有沒有用。可重試（服務暫時失效、限流、鎖衝突）指示消費者退避後重送；終態（參數錯誤、權限拒絕、業務規則拒絕）指示消費者停止重試、走修正或人工路徑。這一刀切錯的代價是雙向的：終態錯誤被標成可重試、消費者的 retry 迴圈空轉壓垮服務；可重試被標成終態、暫時性故障變成使用者眼中的永久失敗。

HTTP status 承擔這一刀的粗分類（4xx 終態、5xx 與 429 可重試、見 [11.3](/backend/11-api-design/resource-modeling-operation-semantics/) 的 status 承諾段）、錯誤 body 承擔細分類。兩層要一致 — body 說可重試、status 給 400、中介層跟 SDK 只看 status、消費者的兩層邏輯就互相矛盾。

## 格式設計：標準與自訂並存的現實

錯誤格式有現行標準、也有大廠自成一格的成熟先例、兩者的設計目標一致：機器可判讀、人類可理解、格式可演化。

RFC 9457 定義 `application/problem+json`：`type`（URI）、`title`、`status`、`detail`、`instance` 五個核心成員、允許 extension members 且要求 client 忽略不認識的欄位（見 [11.C35](/backend/11-api-design/cases/error-rfc9457-problem-details/)）。兩個設計值得單獨理解：`type` 用 URI 而非字串 enum、把錯誤種類的命名空間外部化、跨團隊不撞名；「client MUST ignore unknown extensions」是格式的演化條款 — 服務端可以加欄位而不破壞既有消費者、等同錯誤模型的開放封閉原則。

Stripe 的錯誤物件早於這個標準自成一格、分層思路可以直接借用：`type` 承擔路由層（哪類錯誤、走哪條處理分支）、`code` 承擔分支層（細粒度機器碼）、`param` 加 `message` 承擔 UI 層（哪個欄位錯、給人看什麼）、三個正交欄位讓消費者各層各取所需（見 [11.C36](/backend/11-api-design/cases/error-stripe-error-object/)）。這個模型還藏著一個結構訊號：`idempotency_error` 是四個 type 之一 — 冪等衝突在支付 API 是預期常態、錯誤模型要為它保留一級位置（冪等語意主寫在 [11.8](/backend/11-api-design/api-idempotency-design/)）。

選標準還是自訂的判準：新 API 從 RFC 9457 起手、拿到現成的演化條款與工具生態；既有 API 有自訂格式且被大量依賴、遷移本身就是 breaking change、務實做法是把 9457 的兩個設計（type 命名空間化、未知欄位忽略條款）補進自訂格式、而非換格式。

## 錯誤狀態下的系統行為

錯誤模型的最後一段責任是「錯誤發生時、系統還敢做什麼」。Twilio 2013 年計費事故的教訓落在這：關鍵狀態讀不到、自動扣款卻繼續跑、演變成重複扣款（事故時序與冪等閘門的抽象、主寫在 [11.8 的反例段](/backend/11-api-design/api-idempotency-design/)）。落到錯誤模型的通用判準：關鍵狀態讀寫失敗的錯誤處理、預設要往「拒絕服務」收斂、而非「帶著壞狀態繼續」— 錯誤分類表裡要有一類「狀態不可信、停止副作用」、它的處理路徑跟一般 5xx 不同。

## 常見設計錯誤

- **業務失敗包 200**：觀測與重試鏈失真、修法見 [11.3 的 status 承諾段](/backend/11-api-design/resource-modeling-operation-semantics/)。
- **錯誤碼用連續數字**：`code: 1047` 無命名空間、跨服務撞號、grep 不到語意 — 用可讀字串或 URI。
- **message 當機器介面**：消費者 parse 錯誤訊息文字做分支、訊息改字就是 breaking change — 機器分支一律走 type / code。
- **錯誤格式沒有演化條款**：第一版沒宣告「未知欄位忽略」、之後每次加欄位都無法確認安全性 — 條款從第一版就寫進文件。

## 爭論地圖與下一步

本章的分類與格式判準、以 HTTP transport 承載 status 語意為前提。錯誤格式的跨風格交鋒（RFC 9457、envelope 包裝、GraphQL 的 200-with-errors 慣例）是掛在本章的爭論深度文章 backlog（見 [模組頁](/backend/11-api-design/) 章節規劃）— GraphQL 把 transport 層 status 跟業務錯誤解耦的做法、在該文攤開、本章不展開。

- 可重試錯誤的消費端行為設計：[11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/)、[6.12 冪等與重放驗證](/backend/06-reliability/idempotency-replay/)
- 限流錯誤（429）的完整語意：[11.9 對外流量語意](/backend/11-api-design/external-traffic-semantics/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
