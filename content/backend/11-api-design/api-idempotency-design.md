---
title: "11.8 API 層冪等設計"
date: 2026-07-03
description: "idempotency key 誰生成、存多久、replay 回什麼、衝突怎麼回 — 對外冪等契約的條款設計與無標準現況"
weight: 8
tags: ["backend", "api-design", "idempotency"]
---

API 層冪等處理一個無法迴避的物理事實：網路請求會在結果不明時中斷、消費者只能重送。POST 這類無冪等承諾的操作（見 [11.3 的 method 承諾段](/backend/11-api-design/resource-modeling-operation-semantics/)）、重送就可能重複執行 — 支付重複扣款、訂單重複建立。冪等鍵機制是對外的補強契約：消費者為每個操作生成唯一 key、服務端保證同 key 的重送拿到同樣結局。本章寫這份契約的條款設計；內部去重的處理實作在 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)、冪等性質的驗證在 [6.12 冪等與重放驗證](/backend/06-reliability/idempotency-replay/)、本章只收對外語意。

## 冪等是協作、三種失敗點是分析骨架

冪等契約由兩端共同履行、server 端的 replay 快取只解一半。Stripe 的設計文章把失敗拆成三個時點 — 連線建立前失敗（重送安全、根本沒到 server）、執行中失敗（server 要決定 replay 什麼）、回應遺失（操作成功了、消費者不知道）— 並明確劃出 client 端的責任：exponential backoff 加 jitter、否則故障當下的集體重試會壓垮服務（見 [11.C38](/backend/11-api-design/cases/idempotency-stripe-design-blog/)）。三個時點是設計冪等機制時的分析骨架：replay 行為要對三種情況分別給出答案。

## 冪等契約的條款清單

冪等契約要承諾的條款有五項；逐條的基準參照是 Stripe 的 API reference — 目前公開文件裡最明確的一份（見 [11.C39](/backend/11-api-design/cases/idempotency-stripe-api-contract/)）：

- **key 由誰生成**：消費者生成、建議 UUIDv4、上限 255 字元 — key 代表「消費者眼中的同一次操作」、只有消費者知道邊界。
- **存多久**：至少 24 小時、逾期同 key 視為新請求 — 保存期是承諾、要明文、消費者據此設計重試窗口。
- **replay 回什麼**：首次請求的 status code 加 body、**包含 500 也照樣快取重放**。這條最容易自建做錯 — 快取的是「該次請求的結局」、而非「成功結果」；只快取成功的實作、會在 server 錯誤後讓同 key 重試觸發第二次執行、冪等保證在最需要它的時刻失效。
- **衝突怎麼回**：同 key 不同參數直接報錯 — key 綁定請求語意、防止被當 session id 濫用。Stripe 的錯誤模型甚至為此保留一級錯誤型別 `idempotency_error`（見 [11.4](/backend/11-api-design/error-model-design/)）。
- **作用範圍**：只限 POST — GET 與 DELETE 的冪等由 method 語意承諾、不需要 key。

## 無標準的現況：條款逐家不同

冪等鍵是「業界事實標準先行、正式標準停滯」的典型。IETF 的 Idempotency-Key header draft 推進到第 7 版後過期、狀態 expired（見 [11.C40](/backend/11-api-design/cases/idempotency-ietf-key-header-draft/)）— 引用它只能引語意骨架、不能宣稱 RFC。後果是各家條款實際有差、對照 PayPal 可見三個維度（見 [11.C41](/backend/11-api-design/cases/idempotency-paypal-request-id/)）：header 命名不同（`PayPal-Request-Id`）；replay 語意不同 — Stripe 回「首次結局快照」、PayPal 回「前次請求的最新狀態」、後者對非同步操作友善、但失去 exactly-once 回應保證；契約精確度不同 — Stripe 承諾 24h、PayPal 的保存期寫「a period of time」。設計自己的 API 時、這三個維度就是條款檢查表；整合外部 API 時、逐家讀條款、拿 Stripe 的語意假設去打 PayPal 會踩錯。

## 反例：冪等閘門缺席的內部迴圈

冪等的適用範圍大於對外 header — 系統內部會自動重試的 side-effect 動作、同樣需要閘門。Twilio 2013 年計費事故的時序（C45 觀察層）：Redis 故障讓餘額資料遺失歸零且無法寫回、auto-recharge 在「餘額為零、扣款成功、餘額寫不回去」的循環中對約 1.4% 客戶重複扣款（見 [11.C45](/backend/11-api-design/cases/idempotency-twilio-billing-postmortem/)、反例）。把事故抽象成冪等語言（判讀層）：扣款的觸發條件在執行後未被消除、等效於無限重放的非冪等操作。通用形式：冪等閘門 = 執行紀錄先寫、後執行副作用；配套的 fail-safe = 狀態寫不進去、就不准產生金流級 side effect。對外的 idempotency key 只是這個通用形式在 API 邊界的特例。

## 判讀訊號

| 訊號                                    | 判讀                                                      |
| --------------------------------------- | --------------------------------------------------------- |
| 客訴重複扣款 / 重複下單、都發生在超時後 | 消費者在結果不明時重送、冪等鍵機制缺位或未強制            |
| replay 快取只存成功結果                 | 「500 也重放」條款缺、server 錯誤後的重試會二次執行       |
| 同 key 被觀察到跨操作重用               | 衝突條款缺（同 key 不同參數要報錯）、key 正在被當 session |
| 文件沒寫 key 保存期                     | 消費者無法設計重試窗口、條款補明文                        |

這四個訊號有共同的檢查入口：把五項條款清單當 checklist 對照自家文件、缺哪條補哪條 — 客訴類訊號（第一列）是條款缺位的滯後指標、等它出現才補、代價已經發生。

## 下一步路由

- 冪等衝突的錯誤表達：[11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)
- retry 節奏與限流的互動：[11.9 對外流量語意](/backend/11-api-design/external-traffic-semantics/)
- 對外冪等的一個實際場景（webhook at-least-once 投遞、用 event ID header 去重）：[webhook 對外承諾](/backend/11-api-design/styles/realtime/realtime-webhook-contract/)
- 何時該重送的消費端合判（status、method、key 三者合判）：[接收方的重試決策](/backend/11-api-design/consumer-retry-decision/)
- 內部交付語意（at-least-once 下的去重處理與驗證）：[3.4 consumer 設計](/backend/03-message-queue/consumer-design/)、[6.12 冪等與重放驗證](/backend/06-reliability/idempotency-replay/)、[Processing Semantics 知識卡](/backend/knowledge-cards/processing-semantics/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
