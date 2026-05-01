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
