---
title: "Idempotency Key（冪等鍵）"
date: 2026-07-20
description: "同一操作重送時該由誰生成識別碼、存多久、衝突怎麼回——冪等性質的對外契約落地機制"
weight: 413
---

Idempotency key 是消費者為每次操作生成的唯一識別碼，服務端用這個 key 記住該次操作的執行結果，同 key 重送時直接回傳同樣的結局，不再重複執行副作用。它是 [Idempotency](/backend/knowledge-cards/idempotency/) 這個系統性質在 API 邊界落地的具體機制——idempotency 卡回答「同操作執行多次為何要結果一致」，idempotency key 卡回答「這個一致性用什麼機制對外承諾」，兩者互補而非重疊。

## 概念位置

Idempotency key 目前是業界事實標準先行、正式標準停滯的典型：IETF 的 Idempotency-Key header draft 推進到第 7 版後過期，各家服務的條款因此逐家不同、這類跨服務差異落在 [API Contract](/backend/knowledge-cards/api-contract/) 的相容性議題——沒有正式標準時、契約細節只能靠每家自己的文件承諾。條款差異落在三個維度：header 命名（不同服務用不同的自訂 header 名稱）、replay 語意（回「首次結局的快照」還是「前次請求的最新狀態」，後者對非同步操作更友善但失去 exactly-once 回應保證）、保存期精確度（有的服務承諾具體時數，有的只寫模糊的一段時間）。整合外部 API 時，拿一家的語意假設去用另一家的 idempotency key，容易踩錯。

## 可觀察訊號與例子

Stripe 的 idempotency key 回傳首次結局的快照——同 key 重送永遠拿到跟第一次一模一樣的回應；PayPal 的 `PayPal-Request-Id` 回傳前次請求的最新狀態，這個差異在對接非同步操作（例如狀態會持續更新的退款流程）時特別容易讓消費者端誤判。冪等的適用範圍不只在對外 header——2013 年 Twilio 的計費事故裡，內部自動重試的扣款邏輯在餘額為零、扣款成功、但餘額寫不回去的循環中對約 1.4% 客戶重複扣款，本質是冪等閘門缺席：扣款的觸發條件在執行後沒有被消除，等效於無限重放的非冪等操作。

## 判讀方式

設計自己的 idempotency key 契約時，前述三個維度就是條款檢查表：明確 key 由誰生成、明確重送回什麼、明確同 key 不同參數時怎麼回應（衝突處理，避免 key 被誤當 session 重複使用）。判讀既有系統缺陷的訊號是客訴重複扣款或重複下單都發生在請求逾時之後——代表消費者在結果不明時重送、而冪等鍵機制缺位或沒有強制要求。
