---
title: "接收方的重試決策：從單一請求到 retry 風暴"
date: 2026-07-04
description: "收到錯誤之後重不重試：從單請求的 status 加冪等合判、集體的去同步責任、到 retry 預算與斷路閘門"
weight: 22
tags: ["backend", "api-design", "error-contract"]
---

重試是 consumer 收到錯誤後最頻繁的決策、也是雙向契約裡責任交纏最深的一條：retry 對 consumer 是自保（提高單一請求的表觀成功率）、對 provider 是額外負載 —— 失敗稀少時這筆交換成立、失敗源於過載時、同一個行為變成持續攻擊。這個決策因此分三層、每層的判準不同：單一請求層問「這個錯誤重送安全嗎」、集體層問「大家一起重送會發生什麼」、架構層問「重試這件事該由誰做、配多少預算」。三層的上層框架 —— 兩端期望與成本外部化 —— 在 [11.11 雙向契約](/backend/11-api-design/error-bidirectional-contract/)。

## 單一請求層：status、method、冪等的合判

「該不該重試」是三個輸入的合判、status 只是其中之一。status 給第一刀：4xx 終態停止重試、5xx 與 429 可重試（分類判準見 [11.4](/backend/11-api-design/error-model-design/)、429 的等待語意見 [11.9](/backend/11-api-design/external-traffic-semantics/)）。method 與冪等給第二刀：可重試的 status 不等於重送安全 —— GET 與 PUT 有冪等承諾、直接重送；POST 沒有、重送可能重複執行、要嘛操作帶 idempotency key（[11.8](/backend/11-api-design/api-idempotency-design/)）、要嘛先查再送。第三刀是不確定性：502/504 分不出上游「沒收到」還是「執行了」、兩種情況 retry 安全性相反（見 [11.C67](/backend/11-api-design/cases/status-502-504-gateway-ambiguity/)）—— 判讀規則是「不確定就當作做了」、非冪等又沒帶 key 的操作、重送前先查狀態。

這一層的 provider 義務對應存在：用不同的 code 把可重試與不可重試分開（Google SRE Book 的明文建議、見 [11.C69](/backend/11-api-design/cases/retry-sre-book-cascading-failures/)）、Retry-After 說到做到（見 11.9）。provider 標示含糊、consumer 的合判就從第一刀開始就錯。

## 集體層：各自理性、集體災難

單一 consumer 的合理重試、乘上所有 consumer 就變質。兩個機制疊加：第一是 retry 放大 —— 100 QPS 的失敗、每個都重試一次就變 200 QPS、再放大成 300 QPS、「fewer and fewer requests are able to succeed on their first attempt」（SRE Book 原文、見 C69）；第二是同步波 —— 所有 client 用相同的 [exponential backoff](/backend/knowledge-cards/exponential-backoff/)、退避後會在同一時刻一起回來、每一波都是對 provider 的同步衝擊。

去同步是 consumer 的集體契約責任。Marc Brooker 的實測給了量化根據（模擬情境是 OCC（樂觀並發控制）寫入競爭、非 HTTP retry、結論可遷移）：N 個 client 競爭時總工作量隨 N² 成長、無 jitter 的純 exponential backoff 是「the clear loser」、100 個競爭 client 下加 jitter 讓呼叫量減半以上、Full Jitter（`sleep = random(0, min(cap, base * 2^attempt))`）總工作量最少（見 [11.C68](/backend/11-api-design/cases/retry-brooker-backoff-jitter/)）。判準很直接：backoff 解決「等多久」、[jitter](/backend/knowledge-cards/jitter/) 解決「別一起回來」—— 兩者都是 consumer 對 provider 的義務、不是可選優化。

放大失控的終點是 [retry 風暴](/backend/knowledge-cards/retry-storm/)。AWS 官方定義：「the network can quickly become saturated with new and retried requests… This can result in a retry storm」（見 [11.C72](/backend/11-api-design/cases/retry-aws-guidance-budget/)）。代表案例是 DynamoDB 2015 事故：metadata 服務過載後、逾時的 storage server 自我下線再重試、錯誤率推到 55%、且風暴成形後系統不自癒 —— 復原靠人工暫停請求讓 provider 喘息（見 [11.C70](/backend/11-api-design/cases/retry-dynamodb-2015-storm/)）。這個案例的 consumer 是 AWS 自己的內部元件：retry 變攻擊是任何 caller 的結構性行為、不是外部用戶不守規矩。

## 架構層：retry 放哪一層、配多少預算

多層服務各自 retry 會疊乘：三層各重試 3 次、最底層收到 64 次嘗試（SRE Book、見 C69）。盤點層數時要把 infra 層的隱形 retry 算進去 —— service mesh 的預設 retry policy、SDK 內建的重試（AWS SDK 預設就會重試）都是最常被漏算的一層。retry 因此是要在架構層分配的預算、不是每層的預設行為 —— AWS 的分層建議：低層服務 retry 上限 0 到 1 次、把重試委派給上層（見 C72）、收斂的方向通常是最接近業務語意的外層（它才知道這個操作值不值得再試）；SRE Book 的程序級預算：per-request 上限之外、再設 server-wide [retry budget](/backend/knowledge-cards/retry-budget/)（例如每程序每分鐘 60 次）—— 預算耗盡就不再重試、把「retry 是否過量」從逐請求的局部判斷變成程序級的資源帳。這一層還有一個更上游的預算是剩餘時間：[deadline](/backend/knowledge-cards/deadline/) 傳播下、剩的時間不夠跑完一次重試、retry 是純浪費 —— 重不重試之前先看還剩多久；hedged request、adaptive retry 這類進階形態同屬這層的預算分配問題、本文不展開。

[circuit breaker](/backend/knowledge-cards/circuit-breaker/) 是這一層的閘門、也是 retry 敘事的另一面。Slack 2021 事故給了平衡的實例：網路層恢復後、「plus retries and circuit breaking — got us back to serving」—— retry 加斷路器正是把系統拉回服務狀態的工具（見 [11.C71](/backend/11-api-design/cases/retry-slack-2021-recovery/)）。判讀：consumer 的 retry 是否有害、取決於 provider 當下在「過載中」還是「恢復中」、而 consumer 無法直接觀測這件事 —— circuit breaker 用本地錯誤率推斷代替猜測：斷路時擋住無效重試保護對方、半開時少量探測驗證恢復、恢復後 retry 轉為復原工具。這兩層的 provider 鏡像義務是給出可推斷的訊號：過載時回明確的 429 加等待時間（而非含糊的 5xx、見 11.9）、提供 health endpoint 或 status page 讓斷路器的推斷有依據 —— consumer 的預算與閘門、要有 provider 的訊號才調得準。

## 責任分配表

| 層       | consumer 的義務                                    | provider 的對應義務                             |
| -------- | -------------------------------------------------- | ----------------------------------------------- |
| 單一請求 | status 加冪等合判、不確定就先查                    | code 分開可重試與不可重試、Retry-After 說到做到 |
| 集體     | backoff 加 jitter、per-request 上限                | 過載時給明確的退讓訊號（429 加等待時間）        |
| 架構     | retry 收斂到一層、配 retry budget、circuit breaker | 提供健康訊號讓斷路器有依據                      |

表是索引、每格的成立條件在上文各段。三層合起來的判讀是：重試的每一層都是雙向的 —— consumer 單方面努力擋不住 provider 標示含糊、provider 單方面標清楚也擋不住 consumer 無預算地重送。

## 下一步路由

- 雙向契約的框架：[11.11 Status 與錯誤的雙向契約](/backend/11-api-design/error-bidirectional-contract/)
- 重送安全的機制設計：[11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/)
- 429 與退讓訊號：[11.9 對外流量語意](/backend/11-api-design/external-traffic-semantics/)
- 服務端的過載防護：[06 可靠性](/backend/06-reliability/)、[circuit breaker 知識卡](/backend/knowledge-cards/circuit-breaker/)、[retry budget 知識卡](/backend/knowledge-cards/retry-budget/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
