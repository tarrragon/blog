---
title: "模組二：水平擴展"
date: 2026-06-20
description: "一個實例不夠時怎麼加第二個 — stateless 設計、shared storage、session 處理的工程約束"
weight: 2
tags: ["devops", "horizontal-scaling", "stateless", "shared-storage", "session"]
---

回答「怎麼從一個實例變成多個實例」。水平擴展的前提是服務 stateless — 每個實例可以獨立處理任何請求。這個模組是「規模成長」路線的第二站，接在負載平衡（模組一）之後——有了 LB 把流量分進來，還要讓每個實例都能接任何請求。

## 章節

| 章節                                                                           | 回答什麼問題                                  |
| ------------------------------------------------------------------------------ | --------------------------------------------- |
| [Stateless 設計原則](/devops/02-horizontal-scaling/stateless-design/)          | 什麼破壞無狀態、隱式狀態怎麼抓、定時 job 例外 |
| [Session 處理](/devops/02-horizontal-scaling/session-handling/)                | sticky / session store / 無狀態 token、一致性 |
| [Shared storage 選型](/devops/02-horizontal-scaling/shared-storage-selection/) | DB / KV / 物件儲存怎麼選、讀路徑與連線瓶頸    |
| [擴展的觸發與縮回](/devops/02-horizontal-scaling/scaling-triggers/)            | 觸發訊號分層、縮回為何要先 drain              |
| [垂直與水平擴展的判斷](/devops/02-horizontal-scaling/vertical-vs-horizontal/)  | 用「能不能無狀態」當判斷樞紐                  |

## 跨分類引用

- ← [devops 模組一 負載平衡](/devops/01-load-balancing/)：LB 是水平擴展的前提
- → [monitoring 模組四 Collector](/monitoring/04-collector/)：Collector 的 stateless 設計讓多實例可行
- → [backend 資料庫](/backend/01-database/)：Shared storage 的 DB 選型
- → [backend 擴展軸](/backend/09-performance-capacity/scaling-axes/)：垂直 / 水平取捨與 AKF Scale Cube 的完整拆解
