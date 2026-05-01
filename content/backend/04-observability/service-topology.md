---
title: "4.13 Service Topology 與 Dependency Map"
date: 2026-05-01
description: "把跨服務依賴從文件變成自動發現的觀測訊號"
weight: 13
---

## 大綱

- 為何依賴拓撲需要獨立節點：人工維護的依賴圖永遠過時
- 拓撲訊號的來源：trace（4.3）、service mesh（mTLS / sidecar）、network flow log
- 服務 graph 的維度：呼叫頻率、latency、錯誤率、版本
- 依賴變化告警：新增依賴、刪除依賴、依賴方向反轉
- blast radius 分析：上游失效時下游影響範圍預測
- 跟 [4.3 tracing](/backend/04-observability/tracing-context/) 的分工：trace 是單 request、topology 是統計聚合
- 跟 [05 deployment platform](/backend/05-deployment-platform/) 的整合：service mesh 部署
- 反模式：架構圖只在 wiki 上、跟實際不一致；新依賴上線無 review；拓撲圖無法回答「這服務掛了誰受影響」

## 判讀訊號

- 事故時無法快速回答「誰呼叫這服務」
- 新服務接入無依賴 review、出事後才發現連結
- 架構文件跟實際呼叫關係漂移、半年沒更新
- service mesh 部署但拓撲訊號未被使用
- 循環依賴存在但無人發現

## 交接路由

- 04.3 tracing：拓撲訊號的原始來源
- 05 部署：service mesh 配置
- 06.5 pre-mortem：依賴失效路徑分析
- 06.14 dependency budget：拓撲是依賴可靠性評估的資料來源
- 08.9 事故型態庫：cascading failure 型態的拓撲依據
