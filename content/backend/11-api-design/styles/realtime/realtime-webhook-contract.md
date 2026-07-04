---
title: "webhook 對外承諾：投遞保證不是預設、consumer 扛一半"
date: 2026-07-04
description: "webhook 是盡力而為的事件推送不是可靠佇列：投遞保證逐 vendor 讀、可靠性責任分一半給 consumer"
weight: 2
tags: ["backend", "api-design", "realtime"]
---

webhook 是 server 主動 POST 到你提供的 URL、把「有事發生了」推給你。它跟[持久連線推送](/backend/11-api-design/styles/realtime/realtime-push-mechanisms/)是不同形狀 —— server 對 server、無持久連線、事件觸發。採用 webhook 的核心判讀不在「怎麼收」、而在「這個 vendor 對投遞承諾了什麼、你要自己扛什麼」；關鍵是每個 vendor 的承諾不一樣、不能假設一個通用行為。[webhook 知識卡](/backend/knowledge-cards/webhook/)是概念定義、本文講的是選型與使用層的承諾判讀。

## 投遞保證不是預設

webhook 不一定會重試 —— 這是採用前最該先確認的承諾。GitHub 明文（文件裡重述兩次）不自動重投失敗的 webhook、失敗條件是 server down 或回應超過 10 秒、補救要你手動重送或自寫排程查 API 補投（見 [11.C61](/backend/11-api-design/cases/webhook-github-no-retry/)）。對照 Stripe：live mode 對失敗投遞重試最多三天、指數退避（見 [11.C60](/backend/11-api-design/cases/webhook-stripe-delivery-contract/)）。同樣叫 webhook、一個試三天、一個一次都不重試。

重試的「形狀」本身就是一條要讀清楚的承諾。四個 vendor 四種形狀：Stripe 的長視窗指數退避、Slack 的固定三次（幾乎立即、1 分鐘後、5 分鐘後、見 [11.C62](/backend/11-api-design/cases/webhook-slack-events-retry/)）、GitHub 的完全不重試、Shopify 連投遞本身都不保證（見 [11.C63](/backend/11-api-design/cases/webhook-shopify-ordering-dedup/)）。假設「webhook 會自動重試到成功」、會讓你漏事件卻不自知。payload 格式層有 CloudEvents 這類標準化嘗試、但它標準化的是事件信封的欄位、不是投遞語意 —— 重試、ack、去重這些承諾仍逐 vendor 各異、還是得逐家讀。

## consumer 要扛的五件事

webhook 把可靠性的一部分交給 consumer 自己扛、有五件事跑不掉。

去重（[冪等](/backend/knowledge-cards/idempotency/)）是第一件。[at-least-once](/backend/knowledge-cards/delivery-semantics/) 的投遞會重複、vendor 明文要你用某個 header 當冪等 key 去重 —— Stripe 用 event ID、Shopify 指定 `X-Shopify-Webhook-Id`、GitHub 給 `X-GitHub-Delivery` GUID。就算 GitHub 不自動重試、手動重投也會重複、去重照樣跑不掉。這條對到 [11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/) 的 consumer 側。

不依賴順序是第二件。ordering 不保證是通則、Stripe 與 Shopify 都明文（Shopify 建議用 `updated_at` 自己排）—— 事件處理邏輯不能假設收到的順序等於發生的順序。

快速 [ack](/backend/knowledge-cards/ack-nack/)（回覆確認收到）是第三件：慢等於失敗。Slack 寫死 3 秒、GitHub 10 秒、超過就算投遞失敗。這逼出「先回 2xx、再背景處理」的拆分、複雜邏輯不能擋在 ack 前面、否則一個慢查詢就讓整批事件被判失敗。

簽章驗證是第四件。webhook 是打到你公開 URL 的請求、要驗它真的來自該 vendor。每個 vendor 一套 HMAC（雜湊訊息鑑別碼）方案（Stripe-Signature、GitHub 的 `X-Hub-Signature-256`、Shopify 的 `X-Shopify-Hmac-Sha256`）—— header 名不同、驗法類似：用雙方共享的 secret 對 body 算一段雜湊、比對請求帶的簽章、對不上就丟。

對帳兜底是第五件。Shopify 文件最直接：投遞不保證、app 可能漏事件、要另備 [reconciliation](/backend/knowledge-cards/data-reconciliation/)（對帳）或 polling 補漏。webhook 是盡力而為的推送、要做到不漏、consumer 得在 webhook 之外自備對帳。

## 採用前要讀完的四個承諾

採一個 vendor 的 webhook 前、把承諾讀成四題：重試是什麼形狀（三天、三次、還是不重試）、ack timeout 幾秒、用哪個 header 去重、投遞保不保證。這四題的答案決定 consumer 端要蓋多少機制 —— 不讀清楚就上、會在漏事件或重複處理時、才發現承諾跟假設的不一樣。本文引的具體數字（三天、3 秒、10 秒、固定三次）是各 vendor 當前的承諾、採用前以官方 docs 現值為準。

反過來當 producer、要決定對外推事件用不用 webhook：適不適合不取決於事件關不關鍵、而取決於 consumer 端能不能補齊冪等與對帳 —— Stripe 用 webhook 推付款這種最關鍵的事件、靠的正是 consumer 側的去重與對帳補到接近可靠。真正把 webhook 排除掉的、是「需要 producer 端就保證有序、durable、可重放」的場景：那種可靠語意 webhook 這種盡力而為的形狀補不出來、該換有 durable 保證的佇列 —— 見 [03 訊息佇列](/backend/03-message-queue/)。

## 下一步路由

- 持久連線的推送機制：[持久連線推送](/backend/11-api-design/styles/realtime/realtime-push-mechanisms/)
- consumer 側的冪等設計：[11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/)
- 要可靠送達與重放的事件語意：[03 訊息佇列](/backend/03-message-queue/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
