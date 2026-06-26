---
title: "Prometheus"
date: 2026-06-26
description: "開源的 metrics 收集與告警系統，用 pull 模式從 target 拉取指標，斷網環境的預設監控方案"
weight: 46
tags: ["infra", "knowledge-cards"]
---

Prometheus 是開源的 metrics 收集與告警系統。它用 pull 模式運作——定期從被監控的 target（應用程式、伺服器、資料庫）的 HTTP endpoint 拉取指標，存進本地的時序資料庫。

## 概念位置

Prometheus 在 infra 監控層負責「收集與儲存指標」。它搭配 [Grafana](/infra/knowledge-cards/grafana/) 做視覺化（Prometheus 自己的 UI 只有基礎的 query 介面）、搭配 Alertmanager 做告警路由（Prometheus 偵測異常、Alertmanager 決定通知誰）。斷網環境裡它是取代 Datadog / New Relic 的預設方案——不需要連外、self-hosted、社群龐大。

## 可觀察訊號

系統需要 Prometheus 的訊號是：需要追蹤隨時間變化的數值指標（CPU 使用率、request 延遲、佇列深度、錯誤率），且這些指標要能查詢歷史趨勢和設定告警閾值。如果只需要 log（文字紀錄），Loki 或 ELK 更適合；Prometheus 處理的是結構化的數值 metrics。

## 設計責任

使用 Prometheus 時要決定：scrape interval（多久拉一次、預設 15 秒）、retention（資料保留多久、預設 15 天）、哪些 target 要監控（service discovery 或靜態設定）、告警規則的閾值和評估窗口。斷網環境的額外考量是 storage capacity——所有資料留在本地磁碟、沒有 cloud auto-scale。

## 鄰卡

- [Grafana](/infra/knowledge-cards/grafana/)：視覺化 Prometheus 的指標
