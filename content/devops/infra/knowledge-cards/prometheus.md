---
title: "Prometheus"
date: 2026-06-26
description: "開源的 metrics 收集與告警系統，用 pull 模式從 target 拉取指標，斷網環境的預設監控方案"
weight: 46
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/prometheus/"]
---

Prometheus 是開源的 metrics 收集與告警系統。它用 pull 模式運作——定期從被監控的 target（應用程式、伺服器、資料庫）的 HTTP endpoint 拉取指標，存進本地的時序資料庫，之後交給 [Grafana](/devops/infra/knowledge-cards/grafana/) 做視覺化查詢。

## 跟其他概念的關係

Prometheus 在 infra 監控層負責「收集與儲存指標」。它搭配 [Grafana](/devops/infra/knowledge-cards/grafana/) 做視覺化（Prometheus 自己的 UI 只有基礎的 query 介面）、搭配 Alertmanager 做告警路由（Prometheus 偵測異常、Alertmanager 決定通知誰）。斷網環境裡它是取代 Datadog / New Relic 的預設方案——不需要連外、self-hosted、社群龐大。

## 可觀察訊號

系統需要 Prometheus 的訊號是：需要追蹤隨時間變化的數值指標（CPU 使用率、request 延遲、佇列深度、錯誤率），且這些指標要能查詢歷史趨勢和設定告警閾值。如果只需要 log（文字紀錄），Loki 或 ELK 更適合；Prometheus 處理的是結構化的數值 metrics。

## 判斷條件與後果

Prometheus 把每次拉取的指標寫進本地時序資料庫，target 數量、拉取頻率與保留天數一起決定磁碟用量，告警也建立在同一份資料上。scrape interval 決定指標的時間解析度（程式預設 1 分鐘，官方範例設定寫 15 秒）：間隔越短，越少漏掉短暫的尖峰，代價是同樣的 target 數量下樣本數成倍增加。retention 預設 15 天，超過的資料被刪除，更早的趨勢就查不到。target 用靜態設定列出時，新加的主機或服務沒有寫進設定就不會被拉取；用 service discovery 時，新的 target 自動加入。告警規則的評估窗口太短時，一次短暫的波動就觸發告警；太長時，持續的故障要過完整個窗口才通知。斷網環境裡所有資料留在本地磁碟，沒有雲端儲存可以自動擴充，磁碟容量要依 target 數量、拉取頻率與保留天數事先估算。

## 鄰卡

- [Grafana](/devops/infra/knowledge-cards/grafana/)：視覺化 Prometheus 的指標
