---
title: "6.4 chaos testing"
date: 2026-04-23
description: "整理 broker、DB、network 與節點故障演練"
weight: 4
---

## 大綱

- [broker](/backend/knowledge-cards/broker/) outage
- [database](/backend/knowledge-cards/database/) latency
- node restart
- network [jitter](/backend/knowledge-cards/jitter/)

## 判讀訊號

- chaos experiment 只測 happy path 的故障
- broker / DB / network 故障無自動演練、靠真事故學
- chaos 暴露問題沒修、紀錄堆積
- production chaos 只在低流量時段跑、訊號失真
- 故障注入工具跟 production 不同 stack、結果不可信

## 交接路由

- 06.7 DR / rollback：chaos 暴露的回復路徑問題
- 06.12 idempotency / replay：注入重複訊息驗證冪等
- 06.14 dependency budget：對依賴注入故障驗證 budget
