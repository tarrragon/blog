---
title: "Grafana"
date: 2026-06-26
description: "開源的監控視覺化平台，從 Prometheus / Loki / Elasticsearch 等資料源建立 dashboard"
weight: 47
tags: ["infra", "knowledge-cards"]
---

Grafana 是開源的監控視覺化平台。它本身不收集或儲存資料——它連接外部資料源（[Prometheus](/infra/knowledge-cards/prometheus/)、Loki、Elasticsearch、MySQL 等），提供查詢介面和可自訂的儀表板。

## 概念位置

Grafana 在監控體系裡負責「讓指標和 log 變成人可以讀的畫面」。Prometheus 收集指標、Loki 收集 log、Grafana 把兩者的資料用圖表、表格、熱力圖呈現。不同角色看不同 dashboard——DevOps 看資源健康、開發者看應用指標、管理層看 SLA 達成率。

## 可觀察訊號

系統需要 Grafana 的訊號是：已經有 Prometheus 或其他資料源在收集指標，但需要一個視覺化介面來建 dashboard、設告警（Grafana 也有自己的告警功能）、分享給團隊。如果只需要 CLI 查詢，PromQL 直接在 Prometheus 跑就好。

## 設計責任

使用 Grafana 時要決定：dashboard 的組織（按服務、按環境、按角色）、資料源的連線設定、使用者權限（viewer / editor / admin）、告警通知管道（email / Slack / webhook）。斷網環境裡 Grafana 的 plugin 需要離線安裝（`grafana-cli --pluginUrl` 指向本地檔案）。

## 鄰卡

- [Prometheus](/infra/knowledge-cards/prometheus/)：Grafana 最常見的 metrics 資料源
