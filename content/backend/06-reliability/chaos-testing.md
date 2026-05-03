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

## 概念定位

[Chaos test](/backend/knowledge-cards/chaos-test/) 是在可控條件下主動注入故障，驗證系統是否能在真實依賴失效時維持 steady state 與可接受的 [blast radius](/backend/knowledge-cards/blast-radius/)。

這一頁關心的是失效時系統怎麼退化。沒有先定義 steady state，chaos 只會變成故障展示，不會變成判讀工具。

## 核心判讀

判讀 chaos 的重點是對控制面、資料面與依賴鏈的回復能力做驗證，而不是單純證明服務死過一次。

重點訊號包括：

- 是否先定義 steady state 與成功條件
- 故障是否真的落在常見依賴與控制點
- [blast radius](/backend/knowledge-cards/blast-radius/) 是否可量測、可縮限
- recovery path 是否能在演練後被重播

## 案例對照

- [Netflix](/backend/06-reliability/cases/netflix/_index.md)：把故障注入變成可靠性文化的一部分。
- [Meta](/backend/06-reliability/cases/meta/_index.md)：大規模平台需要驗證控制面故障。
- [AWS S3](/backend/08-incident-response/cases/aws-s3/_index.md)：依賴與區域邊界的故障影響要先被量測。
- [Cloudflare](/backend/08-incident-response/cases/cloudflare/_index.md)：edge / control-plane 分離下的回復能力值得獨立驗證。

## 下一步路由

- 6.7 DR 演練：把 recovery path 變成可重播流程
- 6.14 dependency budget：把外部故障風險納入設計
- 08.9 事故型態庫：把 chaos 發現的 pattern 抽象化

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
