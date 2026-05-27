---
title: "Freshness Token"
date: 2026-05-27
description: "DB write 後返回的版本 token、後續 read 帶 token、保證 read 看到的資料 ≥ token 版本、解 DB + cache 跨層 read-after-write"
weight: 360
---

Freshness token 的核心概念是「write 完成後 DB 返回一個版本 token、後續 read 帶這個 token、中間任何一層（cache / replica / proxy）必須回傳 ≥ token 版本的資料、否則 bypass 回 source of truth」。它的責任是把 read-after-write 一致性從單一 DB 內部、延伸到 application 跟 cache 之間的跨層協議。可先對照 [Session Consistency](/backend/knowledge-cards/session-consistency/)。

## 概念位置

Freshness token 出現在「application 在 DB 前面加 cache、但 cache 跟 DB 不同步」的場景。跟 [Session Consistency](/backend/knowledge-cards/session-consistency/) 區分：後者是 DB 內部的 causal session、保證同一 session 看得到自己剛寫的；freshness token 是跨層協議、把「保證讀到自己剛寫的」從 DB 內延伸到包含 cache 的整條 read path。跟 [Stale Read](/backend/knowledge-cards/stale-read/) 是症狀與防護機制的對應 — stale read 是現象、freshness token 是用版本門檻防止它。跟 [Cache Invalidation](/backend/knowledge-cards/cache-invalidation/) 互補 — 後者由 write 端 push 失效、freshness token 由 read 端 pull 版本檢查、兩者可同時部署。

## 可觀察訊號與例子

需要 freshness token 的訊號是「DB 寫成功、user 立刻 read、cache 還回舊資料」。[9.C36 Coinbase MongoDB](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) 揭露具體機制：在 MongoDB + Memcached 三層架構下、users 服務直接撐 1.5M reads/sec（含 cache、users 服務應用層觀察口徑）。write 成功時 DB 返回 token（含 OCC version / clusterTime）、client 後續 read 帶 token、server 保證返回 ≥ token 版本、必要時 bypass cache 直接打 DB。

## 設計責任

設計時要先區分 token 的 *語意層級* — 是 application 自行管理（如 Coinbase 自建協議、把 version 寫進 token）、還是 SDK 內建（如 Cosmos DB session token 自動跨 service 傳遞）。若同時部署多種 cache 層（CDN / application cache / DB read replica）、token 要能穿透所有層、否則最弱的一層會破壞保證。Token 過期或不可用時的 fallback 行為（bypass cache 直接讀 primary）要明示寫進設計、不能讓 user 在 token 失效時悄悄讀到舊資料。
