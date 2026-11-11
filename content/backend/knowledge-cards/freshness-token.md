---
title: "Freshness Token"
date: 2026-05-27
description: "DB write 後返回的版本 token、後續 read 帶 token、保證 read 看到的資料 ≥ token 版本、解 DB + cache 跨層 read-after-write"
weight: 361
---

Freshness token 的核心概念是「write 完成後 DB 返回一個版本 token、後續 read 帶這個 token、中間任何一層（cache / replica / proxy）必須回傳 ≥ token 版本的資料、否則 bypass 回 source of truth」。它的責任是把 read-after-write 一致性從單一 DB 內部、延伸到 application 跟 cache 之間的跨層協議。可先對照 [Session Consistency](/backend/knowledge-cards/session-consistency/)。

## 跟其他概念的關係

Freshness token 出現在「application 在 DB 前面加 cache、但 cache 跟 DB 不同步」的場景。跟 [Session Consistency](/backend/knowledge-cards/session-consistency/) 區分：後者是 DB 內部的 causal session、保證同一 session 看得到自己剛寫的；freshness token 是跨層協議、把「保證讀到自己剛寫的」從 DB 內延伸到包含 cache 的整條 read path。跟 [Stale Read](/backend/knowledge-cards/stale-read/) 是症狀與防護機制的對應 — stale read 是現象、freshness token 是用版本門檻防止它。跟 [Cache Invalidation](/backend/knowledge-cards/cache-invalidation/) 互補 — 後者由 write 端 push 失效、freshness token 由 read 端 pull 版本檢查、兩者可同時部署。

## 可觀察訊號與例子

需要 freshness token 的訊號是「DB 寫成功、user 立刻 read、cache 還回舊資料」。[Coinbase MongoDB](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) 揭露具體機制：在 MongoDB + Memcached 三層架構下、users 服務直接撐 1.5M reads/sec（含 cache、users 服務應用層觀察口徑）。write 成功時 DB 返回 token（含 OCC version / clusterTime）、client 後續 read 帶 token、server 保證返回 ≥ token 版本、必要時 bypass cache 直接打 DB。

## 判斷條件與後果

Freshness token 的保證取決於 read path 上每一層是否都檢查 token。同時有 CDN、application cache 與 DB read replica 時，任何一層不檢查就回傳舊版本，使用者在那一層讀不到自己剛寫的資料，其他層的檢查也補不回來。token 的語意層級決定檢查由誰實作：application 自行管理時（Coinbase 自建協議、把 version 寫進 token），每一層的檢查由團隊自己寫；SDK 內建時（Cosmos DB 的 session token 自動跨 service 傳遞），傳遞由 SDK 負責，SDK 以外的自建 cache 層仍然沒有檢查。token 過期或不可用時，設計裡沒有寫明 fallback 行為的話，讀取照一般路徑走 cache，使用者在沒有任何訊號的情況下讀到舊資料；寫明為 bypass cache 直接讀 primary 時，代價是那段期間 primary 多出這些讀取的負載。
