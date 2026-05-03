---
title: "6.12 Idempotency 與 Replay 驗證"
date: 2026-05-01
description: "把重試、重播與冪等性從口頭約定變成可驗證屬性"
weight: 12
---

## 大綱

- 為何 idempotency 是分散式系統一級屬性：retry / failover / replay 的前提
- idempotency key 的設計：來源、生命週期、儲存
- exactly-once 是幻象、at-least-once + idempotent 才實際
- replay 驗證：從 log / event store 重播能否得到相同最終狀態
- 跟 [03 message-queue](/backend/03-message-queue/) 的關係：consumer idempotency 是延伸專題
- payment / order / messaging 的 idempotency 模式差異
- 跟 [6.4 chaos](/backend/06-reliability/chaos-testing/) 的整合：注入重複訊息驗證冪等
- 反模式：idempotency 只靠 DB unique constraint、無 key 設計；retry 後副作用重複；replay 路徑從未驗證

## 概念定位

[Idempotency](/backend/knowledge-cards/idempotency/) 與 replay 驗證是把重試、重播與副作用控制變成可驗證屬性，責任是讓 at-least-once 與 failover 不會把系統推向重複執行。

這一頁處理的是分散式系統的重複輸入問題。只要有 retry、補償或訊息重送，冪等性就不是優化項，而是正確性前提。

## 核心判讀

判讀 idempotency 時，先看 key 的生命週期，再看 replay 是否能落在同一狀態。

重點訊號包括：

- idempotency key 是否由 server 可控、可追蹤
- replay 路徑是否與 production 對齊
- late retry 是否會被誤視為新請求
- 重複副作用是否能靠狀態機吸收

## 案例對照

- [Stripe](/backend/06-reliability/cases/stripe/_index.md)：交易流程需要嚴格控制重複請求。
- [GitHub](/backend/08-incident-response/cases/github/_index.md)：webhook / event replay 經常直接暴露冪等缺口。
- [Slack](/backend/08-incident-response/cases/slack/_index.md)：訊息與通知類流程特別依賴重複輸入控制。

## 下一步路由

- 03 message-queue：consumer 端冪等設計
- 06.4 chaos：注入重複訊息驗證
- 06.7 DR：replay 作為回復手段的前提

## 判讀訊號

- 用戶被重複扣款 / 重複建立資源、靠人工對帳發現
- retry policy 開啟後事故變嚴重、不敢開 retry
- replay 從 event store 跑一次、結果跟 production 不同
- idempotency key 從 client 端帶上來、無 server 端 fallback
- key TTL 過短、晚到的 retry 變成新請求

## 交接路由

- 03 message-queue：consumer idempotency 實作
- 06.4 chaos：注入重複訊息 / 故障 retry 場景
- 06.7 DR：replay 作為回復手段的前提
- 07 資安：idempotency key 不可被預測 / 偽造
