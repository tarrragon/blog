---
title: "11.3 資源建模與操作語意"
date: 2026-07-03
description: "endpoint 該建模成資源還是動作、HTTP method 與 status 承諾了什麼、available actions 由誰計算 — 建模決策的判準"
weight: 3
tags: ["backend", "api-design", "modeling"]
---

資源建模的核心決策是把業務操作對映成介面詞彙的方式。同一個「取消訂單」、可以建模成資源狀態的變更（`PATCH /orders/{id}` 帶 `status: cancelled`）、子資源的建立（`POST /orders/{id}/cancellation`）、或動作端點（`POST /orders/{id}/cancel`）— 三種寫法都在真實 API 裡大量存在、差異在演進空間、快取語意、跟消費者的心智模型。本章給建模決策的判準；本章的來源偏論證型（定義與判別法）、企業建模實作的公開案例在案例庫標為缺口、操作層展開以通用工程知識補充。

## 資源與表徵是兩層

資源建模的第一個概念區分是資源（resource）與表徵（representation）：資源是被命名的概念實體、表徵是它在某次回應裡的具體格式。這個區分出自 REST 論文的 uniform interface 子約束 manipulation through representations — client 透過表徵操作資源（約束清單見 [11.C1](/backend/11-api-design/cases/rest-fielding-dissertation-ch5/)、定義展開依論文原文）。工程意義：同一個資源可以有多種表徵（完整版、列表精簡版、不同版本的形狀）、表徵的形狀可以演進而資源身分不變 — URL 命名的是資源、欄位設計的是表徵、兩層的變更紀律不同。把這兩層混在一起的常見症狀是「加一個欄位要開一個新 endpoint」。

## 資源導向與動作導向的取捨

兩種建模方向各有成立情境、判準是操作的語意複雜度與演進預期。

資源導向把業務操作收斂成「對某個名詞的狀態操作」：建立、讀取、更新、刪除、加上狀態欄位變更。收益是介面詞彙統一 — 消費者學會一個資源的操作方式、就會操作所有資源；快取、權限、審計都能按資源粒度統一處理。成本是有些操作硬塞進名詞會失真：「重算報表」「合併帳號」「試算價格」這類操作沒有自然的資源對應。

動作導向（RPC 式端點）直接命名操作。收益是語意直白、參數自由；成本是介面詞彙發散 — 每個動作都是新詞彙、消費者要逐個學、橫切能力（快取、重試語意、權限）要逐個處理。

務實的判準是混用、但混用要有規則：預設資源導向、動作導向保留給「狀態機轉換有業務儀式」的操作（下單、退款、發布）、且動作端點的回應仍回到資源表徵（回訂單、不回裸 ack）。這條規則讓橫切能力至少在回應側保持統一。跨資源的操作（轉帳、合併）建議建模成獨立資源（transfer、merge job）— 操作本身有生命週期、有查詢需求、有失敗狀態時、它就值得一個名詞。

## HTTP method 與 status 是承諾、不只是慣例

method 與 status 的選用向中介層與消費者承諾了行為性質、選錯的代價由基礎設施收取。GET 承諾安全（無副作用）— proxy 與瀏覽器會據此重試、預取、快取；PUT 承諾冪等 — client 可以直接重送、無需判斷前次結果；POST 兩者都沒承諾、所以需要冪等鍵機制補強（[11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/) 主寫）。status 同理：2xx 對監控承諾成功、4xx 承諾「錯在請求、重試無用」（限流的 429 是明確例外、可重試但要等、見 [11.9](/backend/11-api-design/external-traffic-semantics/)）、5xx 承諾「錯在服務、可以重試」— 把業務失敗包在 200 裡回傳、等於對整條觀測與重試鏈說謊、錯誤率圖表從此失真。錯誤語意的完整設計是 [11.4 錯誤模型設計](/backend/11-api-design/error-model-design/) 的主題、本章只立「status 是給機器的承諾」這條判準；單一 status 裝不下的情況（部分成功、202 之後才失敗、504 歧義）在 [Status 裝不下的東西](/backend/11-api-design/status-expressiveness-boundary/) 展開。

## Available actions 由誰計算

資源當下可做什麼操作、有兩種回答方式 — 這是 hypermedia 爭論落到建模層的具體形式。htmx 的 HATEOAS essay 用透支帳戶做對照：HTML 表徵在透支時只回 deposit 連結、業務狀態直接編碼在可用操作裡、client 零業務知識；JSON 表徵回 `status: "overdrawn"` 欄位、client 靠文件理解語意跟下一步（見 [11.C5](/backend/11-api-design/cases/rest-htmx-hateoas-html-necessity/)）。由此得到的操作型判別法：**available actions 由 server 算完放進 response、還是 client 讀狀態欄位自己算** — 前者是 hypermedia 路線、後者是業界主流的 JSON API 路線。

判準層的建議：machine-to-machine 的 JSON API 走 client 自算是務實預設（消費者是程式、本來就要讀文件寫死邏輯）；但「狀態欄位 + 文件」的組合要把狀態機明文化 — 狀態列舉、每個狀態下的合法操作、非法操作回什麼錯誤。hypermedia 路線的完整論證與反方立場、收在 [Hypermedia 與 HATEOAS 復興](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)。

Richardson 成熟度模型可以當這個決策的定位工具：Level 1（資源化）、Level 2（method 與 status 語意正確）、Level 3（hypermedia controls）。一手來源自己標注它是理解工具、非 REST 認證（見 [11.C3](/backend/11-api-design/cases/rest-fowler-richardson-maturity-model/)）。用它描述「我們的 API 在哪、要不要往上」是合法用法、拿它當合規檢查表是誤用 — 完整的實用讀法與誤用邊界、主寫在 [Richardson 成熟度的實用讀法](/backend/11-api-design/styles/rest/richardson-maturity-practical-reading/)。

## 判讀訊號

| 訊號                               | 判讀                                              |
| ---------------------------------- | ------------------------------------------------- |
| 新功能反覆長出 `/doSomething` 端點 | 缺混用規則、動作導向變成預設、橫切能力開始發散    |
| 業務失敗回 200 + `success: false`  | status 承諾失效、觀測與重試鏈失真、往錯誤模型章修 |
| 消費者問「這個狀態下能不能呼叫 X」 | 狀態機沒明文化、補狀態 × 操作對照表、比加欄位優先 |
| GET 端點被發現有副作用             | method 承諾違約、中介層重試會放大傷害、最高優先修 |

四個訊號的損害半徑不同、排查順序從半徑最大的開始：GET 副作用會被中介層自動放大、屬立即修；200 包業務失敗污染整條觀測鏈、次之；端點增生與狀態機未明文是設計債、按迭代節奏收。

## 邊界

本章的建模判準以 HTTP+JSON 風格為主要語境。gRPC 與 GraphQL 的建模單位（service/method、type/field）有各自的紀律、收在對應流派層；事件式介面的建模（event schema）屬 [03 訊息佇列](/backend/03-message-queue/) 的範圍。

## 下一步路由

- 資料層的結構設計：[1.2 Schema 設計](/backend/01-database/schema-design/)（資源表徵與資料表是兩層、交接處看這篇）
- 風格還沒定、先回：[11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)
- 承諾框架：[11.1 API 作為服務邊界的責任](/backend/11-api-design/api-boundary-responsibility/)
- 名詞層：[Request-Response Protocol](/backend/knowledge-cards/request-response-protocol/)、[API Contract](/backend/knowledge-cards/api-contract/) 知識卡
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
