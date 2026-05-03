---
title: "4.17 Telemetry Data Quality"
date: 2026-05-02
description: "把 missing signal、schema drift、sampling bias 與 timestamp skew 變成資料品質問題"
weight: 17
---

## 大綱

- telemetry data quality 的責任：確認觀測資料本身可信
- 缺漏類型：missing signal、partial trace、dropped log、stale metric
- 漂移類型：schema drift、label drift、service name drift、semantic convention drift
- 偏誤類型：[sampling](/backend/knowledge-cards/sampling/) bias、low-traffic bias、high-cardinality truncation
- 時間類型：clock skew、ingest delay、out-of-order event、timezone mismatch
- 品質指標：completeness、freshness、consistency、accuracy、coverage
- 跟 04.11 telemetry pipeline 的分工：pipeline 看路徑，data quality 看資料可信度
- 反模式：dashboard 看起來正常但資料少一半；trace sample 漏掉錯誤；timestamp 導致 timeline 錯序

Telemetry data quality 的核心是把「觀測資料失真」當成一級事件。服務事故判讀建立在觀測資料上，資料品質不穩時，團隊可能花大量時間修系統之外的問題，最後才發現錯的是資料語意或時間對齊。

## 概念定位

Telemetry data quality 是把觀測資料當成資料產品治理的能力，責任是讓 log、metric、trace 與 alert 的判讀建立在可信資料上。

這一頁處理的是資料可信度。訊號存在不等於訊號可信；缺漏、漂移、偏誤與時間錯位都會讓事故判讀走向錯誤路徑。

資料品質治理最有效的做法是把品質指標產品化：讓 completeness、freshness、drift、sampling coverage 也進 dashboard 與告警，而不是只在事故後人工比對。

## 核心判讀

判讀 telemetry data quality 時，先看資料是否完整與新鮮，再看不同訊號之間是否能互相對齊。

重點訊號包括：

- log / metric / trace 是否有 coverage 與 drop rate
- schema 是否有版本與 drift 偵測
- sampling 是否保留錯誤、高延遲與低流量樣本
- timestamp 是否能支援 [incident timeline](/backend/knowledge-cards/incident-timeline/) 還原
- dashboard 是否標示資料延遲、缺口與查詢範圍

| 品質面向 | 最小可用判準                 | 失真後果                    |
| -------- | ---------------------------- | --------------------------- |
| 完整性   | drop rate、coverage 可被量測 | 事故定位依賴不完整證據      |
| 一致性   | 欄位語意與命名跨服務一致     | 事件鏈無法拼接              |
| 代表性   | sampling 覆蓋高風險樣本      | 錯誤被平均化，誤判風險      |
| 時間性   | timestamp 與 delay 可追蹤    | timeline 錯序，決策先後顛倒 |

## 判讀訊號

- 同一事故在 log、metric、trace 中呈現不同時間線
- service name / region / tenant label 在不同系統拼不起來
- 低流量服務的錯誤被 sampling 稀釋
- pipeline drop 發生但 dashboard 沒提示資料缺口
- post-incident review 發現判讀基於不完整資料

常見場景是「圖看起來穩，但資料在悄悄掉」。例如 ingest 層 partial drop 後 error rate 下降，看似健康，實際是訊號少了高風險區段。這類情況若沒有資料品質指標，會讓事故決策建立在錯誤安全感上。

## 交接路由

- 04.1 log schema：治理欄位漂移
- 04.7 cardinality / cost：處理高維度截斷與成本取捨
- 04.11 telemetry pipeline：追查 drop、delay 與 ingest 問題
- 04.14 anomaly detection：避免模型學到偏誤資料
- 08.19 incident decision log：標記事中判讀使用的資料品質限制
