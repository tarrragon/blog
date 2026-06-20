---
title: "模組二：水平擴展"
date: 2026-06-20
description: "一個實例不夠時怎麼加第二個 — stateless 設計、shared storage、session 處理的工程約束"
weight: 2
tags: ["devops", "horizontal-scaling", "stateless", "shared-storage", "session"]
---

回答「怎麼從一個實例變成多個實例」。水平擴展的前提是服務 stateless — 每個實例可以獨立處理任何請求。

## 待寫章節

- [ ] Stateless 設計原則（狀態放 DB / cache / 外部儲存、不放 process memory）
- [ ] Session 處理（sticky session / session store / JWT stateless）
- [ ] Shared storage 的選型（NFS / S3 / DB — 不同 workload 的適合方案）
- [ ] 擴展的觸發訊號和縮回條件
- [ ] 垂直擴展 vs 水平擴展的判斷（什麼時候加 CPU、什麼時候加實例）

## 跨分類引用

- ← [devops 模組一 負載平衡](/devops/01-load-balancing/)：LB 是水平擴展的前提
- → [monitoring 模組四 Collector](/monitoring/04-collector/)：Collector 的 stateless 設計讓多實例可行
- → [backend 資料庫](/backend/01-database/)：Shared storage 的 DB 選型
