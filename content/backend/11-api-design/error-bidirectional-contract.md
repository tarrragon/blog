---
title: "11.11 Status 與錯誤的雙向契約"
date: 2026-07-04
description: "status 與錯誤是兩端的合作契約：provider 該讓 consumer 知道什麼、consumer 收到錯誤怎麼判讀與回報、以及單邊設計怎麼把成本外部化給對方"
weight: 11
tags: ["backend", "api-design", "error-contract"]
---

status code 與錯誤回應是 provider 與 consumer 之間的合作契約、不是 provider 單方的輸出格式。兩端理論上是合作對象 —— provider 要 consumer 正確使用服務、consumer 要 provider 給出可判讀的行為指示 —— 但商業上常因地位不對等、由強勢一方片面從自己的需求設計、把成本外部化給對方：平台不給 debug 資訊、消費者只能猜；消費者盲目重試、provider 在過載時被自己的用戶打垮。本章立這份契約的雙向判準；每個設計決策的判別問題是「這是在解決問題、還是把成本推給對方」。

status 語意的粗承諾在 [11.3](/backend/11-api-design/resource-modeling-operation-semantics/)、錯誤格式設計在 [11.4](/backend/11-api-design/error-model-design/)、限流語意在 [11.9](/backend/11-api-design/external-traffic-semantics/) —— 本章不重述這三章的 producer 側設計、收的是它們共同缺的另一半：consumer 端拿到之後怎麼辦、以及兩端對彼此的期望怎麼寫進契約。

## 兩端各自期望什麼

consumer 對錯誤回應的期望收斂成四件：**可判讀的行為指示**（這個錯誤重試有沒有用、要等多久 —— 對應 11.4 的第一刀「可重試與終態」分類、11.9 的 Retry-After）；**可分支的機器碼**（程式能走 switch、不用 parse 人類訊息 —— 對應 11.4 的 type/code 層）；**可自助的 debug 入口**（error 帶 request-id 或 trace id、回報時引用它就能被定位）；**穩定性**（錯誤格式與語意的變更跟正常回應一樣是 breaking change、對應 [11.6](/backend/11-api-design/backward-compatibility-discipline/)）。

provider 對 consumer 的期望同樣具體：守 retry 紀律（退避間隔加隨機抖動、有上限、對過載退讓）；快速 ack（多快看 vendor 明文、如 GitHub 的 10 秒、Slack 的 3 秒）、把慢邏輯移出回應路徑；用 event id 去重、不依賴投遞順序（webhook 場景、見 [realtime 流派層](/backend/11-api-design/styles/realtime/realtime-webhook-contract/)）；把機器分支寫在 type/code 上、不 parse message 文字 —— consumer 把人類可讀欄位當契約、之後 provider 改個錯字都變 breaking change（[Hyrum's Law](/backend/knowledge-cards/hyrums-law/)（一切可觀察行為終將被依賴）的錯誤版、案例見 [11.C75](/backend/11-api-design/cases/errorchain-aip193-error-content/) 的 message 穩定性條款）。

這兩張清單合起來是本章的骨架：契約寫得好、兩張清單都成立；寫得偏、一邊的成本變成另一邊的日常。

## 成本外部化的判讀訊號

單邊設計的產物有固定形態、兩個方向都有。provider 側轉嫁：業務失敗包 200（把「讀 body 才知道成敗」的解析成本推給 consumer、順便讓自己的錯誤率圖表失真、見 [11.3 判讀訊號](/backend/11-api-design/resource-modeling-operation-semantics/)）；不給機器可讀 code（分支成本推給 consumer 去 parse message）；不給 request-id（debug 成本推給 consumer 與自己的 support 團隊）；用兩種 status 表達同一件事且不明文劃分時機（GitHub 超限回 403 或 429、consumer 分支邏輯雙倍、見 [11.C43](/backend/11-api-design/cases/ratelimit-github-primary-secondary/)、語意判準主寫在 [11.9](/backend/11-api-design/external-traffic-semantics/)）；完全不重試的 webhook（重試責任整包轉給 consumer 自建排程、見 [11.C61](/backend/11-api-design/cases/webhook-github-no-retry/)）。最後一項要再切一刀：GitHub 把不重試寫進文件、附補投 API 與投遞狀態查詢 —— 明文轉移是可規劃的契約條款、跟默默轉嫁（不明說、consumer 事後才發現）是兩回事；判讀的重點在「對方知不知道自己接了這筆成本」、不在成本移動本身。

consumer 側轉嫁：盲目 retry 把恢復成本推回 provider —— 失敗源於過載時、retry 是持續攻擊（AWS 內部元件把錯誤率推到 55% 的實例、見 [11.C70](/backend/11-api-design/cases/retry-dynamodb-2015-storm/)；retry 行為常繼承自 SDK 預設而非顯式選擇、審自己依賴堆疊的預設值也是 consumer 的義務）；多層各自 retry、三層各三次在底層疊成 64 次嘗試（見 [11.C69](/backend/11-api-design/cases/retry-sre-book-cascading-failures/)）；parse message 文字做分支、把自己的穩定性押在 provider 不改字上。

判讀方法：看到任何一項、先問成本被推到哪一端、再回對應的深度文章找修法。

## 深度議題分流

雙向契約的複雜度集中在幾個議題、各有一篇深度文章：

**status 裝不下的東西**。單一 status 有三種表達力邊界：裝不下多個結果（部分成功）、裝不下時間軸（202 之後才失敗）、裝不下不確定性（504 分不出「沒送到」還是「執行了」）。兩條處理路線 —— 把狀態表下放 body、或收窄語意保持單一 status 恆為真 —— 在 [status 表達力邊界](/backend/11-api-design/status-expressiveness-boundary/) 攤開。

**收到錯誤之後重不重試**。這是 consumer 最頻繁的決策、也是雙向責任最典型的場景：單一請求層看 status 加冪等合判、集體層要 backoff 加 jitter 防同步波、架構層要決定 retry 放哪一層、配 retry budget 與 circuit breaker。完整判準在 [接收方的重試決策](/backend/11-api-design/consumer-retry-decision/)。

**錯誤跨服務怎麼傳**。A 呼叫 B、B 呼叫 C、C 掛了 —— B 同時是 consumer 跟 provider、要決定透傳還是轉譯、以及錯誤細節暴露多少（機器可讀 vs 攻擊偵察面的張力）。在 [錯誤傳播與信任邊界](/backend/11-api-design/error-propagation-trust-boundary/)。

**收到錯誤之後怎麼溝通**。consumer 拿 request-id 或 trace id 回報、provider 承諾用它定位 —— 這條回饋迴路是雙向 debug 契約、也是地位不對等最常見的缺口（不給 id、consumer 只能用「大概幾點、大概什麼操作」描述問題）。在 [錯誤回報的回饋迴路](/backend/11-api-design/error-feedback-loop/)。

## 下一步路由

- 錯誤格式的 producer 側設計：[11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)
- status 承諾的地基：[11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/)
- 429 與配額語意：[11.9 對外流量語意](/backend/11-api-design/external-traffic-semantics/)
- 重送安全的冪等機制：[11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/)
- 同一批診斷欄位的觀測動機：[4.19 Debuggability by Design](/backend/04-observability/debuggability-by-design/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
