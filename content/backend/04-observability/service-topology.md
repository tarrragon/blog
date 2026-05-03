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
- [blast radius](/backend/knowledge-cards/blast-radius/) 分析：上游失效時下游影響範圍預測
- 跟 [4.3 tracing](/backend/04-observability/tracing-context/) 的分工：trace 是單 request、topology 是統計聚合
- 跟 [05 deployment platform](/backend/05-deployment-platform/) 的整合：service mesh 部署
- 反模式：架構圖只在 wiki 上、跟實際流量漂移；新依賴上線缺 review；拓撲圖回答「這服務掛了誰受影響」需要人工追查

## 概念定位

Service topology 是把跨服務依賴從文件轉成可觀測資料的能力，責任是讓團隊能用實際呼叫關係判斷依賴、影響面與變更風險。

這一頁處理的是服務關係圖。trace 解釋單次 request，topology 解釋一段時間內的依賴結構；兩者合起來才能回答「這個服務壞了會影響誰」。

## 核心判讀

判讀 topology 時，先看資料是否來自真實流量，再看依賴變化是否能被治理。

重點訊號包括：

- service graph 是否包含呼叫方向、頻率、latency 與 error rate
- 新增依賴是否能觸發 review 或 alert
- [blast radius](/backend/knowledge-cards/blast-radius/) 是否能從上游 / 下游關係推導
- topology 是否能餵給 dependency budget 與事故型態判讀

## 判讀訊號

- 事故時回答「誰呼叫這服務」需要人工追查
- 新服務接入無依賴 review、出事後才發現連結
- 架構文件跟實際呼叫關係漂移、半年沒更新
- service mesh 部署但拓撲訊號未被使用
- 循環依賴存在但無人發現

## 交接路由

- 04.3 tracing：拓撲訊號的原始來源
- 05 部署：service mesh 配置
- 06.5 pre-mortem：依賴失效路徑分析
- 06.14 dependency budget：拓撲是依賴可靠性評估的資料來源
- 08.9 事故型態庫：[cascading failure](/backend/knowledge-cards/cascading-failure/) 型態的拓撲依據
