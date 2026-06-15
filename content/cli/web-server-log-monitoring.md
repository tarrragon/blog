---
title: "終端機看 nginx 請求：GoAccess、ngxtop 與何時該用 pipeline 而非 TUI"
date: 2026-06-15
draft: false
description: "在終端機即時看 nginx／web 伺服器請求的工具：GoAccess 即時儀表板、ngxtop top 風格，含 log 格式對齊的 gotcha；以及「當下排查用 TUI、持續監控用 metrics pipeline」的使用時機分界。"
tags: ["cli", "tui", "nginx", "goaccess", "ngxtop", "observability", "remote"]
---

Web 伺服器日誌監控工具把 nginx／Apache 的 access log 解析成終端機可讀的請求統計，讓遠端 SSH 進去的那台機器上，能即時看到現在誰在打、打哪些路徑、回什麼狀態碼、吃多少頻寬。它跟系統監控（`btop` 看 CPU／記憶體）的差別在於觀測對象：系統監控看主機資源，這類看的是 HTTP 請求流。

本文承接 [終端機圖形化工具總覽](/cli/cli-graphical-tools-overview/) 的 TUI 工具脈絡，屬監控的 web 請求子題。但比起工具本身，更該先分清的是「什麼時候用終端機看請求、什麼時候不該」，這放在最後一節。

## GoAccess：即時請求儀表板

`GoAccess` 把 access log 解析成全螢幕的即時儀表板，責任是把一份 log 變成可讀的請求分析：狀態碼分布、top 請求路徑、不重複訪客、頻寬、回應時間、訪客的 OS 與瀏覽器。它既能開互動 TUI，也能輸出 HTML／CSV／JSON 報表。

驗證它解析的正確性可以走非互動模式 — 餵一份 nginx access log、指定格式、輸出報表：

```bash
goaccess access.log --log-format=COMBINED -o report.html
```

`--log-format=COMBINED` 是對應 nginx 標準 combined 格式的預設。實測對一份 13 筆請求的 log，GoAccess 正確分出 9 筆 2xx、4 筆 4xx，並列出 top 路徑（`/` 佔多數、`/missing` 等 404）、訪客 host、user-agent 與頻寬。互動模式（不加 `-o`）則是同一份資料的全螢幕即時版，連線中持續更新。

## ngxtop：top 風格的請求即時表

`ngxtop` 把 access log 做成 `top` 風格的即時表，責任是用最精簡的版面看「現在最熱的請求路徑與其狀態碼分布」。它比 GoAccess 輕、聚焦在請求路徑與狀態碼，適合快速掃一眼。

```bash
ngxtop -l access.log --no-follow
```

`--no-follow` 處理現有 log 後就退出（預設會持續跟隨新進的 log）。

這裡有一個實測會撞到的 gotcha：**ngxtop 的 log 格式要跟實際的 nginx log_format 完全對上，否則它靜默回 0 records**。nginx 官方 image 的預設 log_format 在標準 combined 之後多了一個 `"$http_x_forwarded_for"` 欄位，ngxtop 的預設格式不含它，結果就是「跑得起來、但一筆都沒解析到」。對策是用 `-f` 餵實際的格式：

```bash
ngxtop -l access.log --no-follow \
  -f '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for"'
```

格式對上後，ngxtop 正確處理 13 筆、分出 9 筆 2xx 與 4 筆 4xx，跟 GoAccess 的結果一致。相較之下 GoAccess 的 `--log-format=COMBINED` 對尾端多出的欄位較寬容。判讀訊號很明確：ngxtop 顯示 0 records 時，先懷疑的是格式沒對上，而非沒有流量。

## 何時用終端機看請求、何時不該

工具會用之後，真正該分清的是使用時機。監控 nginx 請求依目的走兩條完全不同的路。

當下排查與 ad-hoc 觀測，用終端機。情境是「伺服器現在很忙，進去看誰在打」「某個 endpoint 的 5xx 突然變多，即時看是哪一條」。這時 GoAccess／ngxtop／`tail -f access.log` 直接在那台機器上看當下狀況，是遠端 SSH 除錯的日常，也是這類 TUI 工具的主場。

持續的生產監控，不用終端機。沒有人 24 小時盯著 GoAccess。生產環境的請求監控走 pipeline：指標面用 nginx 的 `stub_status`（基礎）或 VTS 模組／`nginx-prometheus-exporter`（細到 per-status、per-upstream 的請求率），由 Prometheus 抓、Grafana 畫儀表板並設告警；日誌面把 access log 送到 Loki／ELK／Datadog 之類做查詢與長期保存。

分界濃縮成一句：終端機 TUI 答「這台機器現在怎樣」，pipeline 答「趨勢如何、超標叫我」。所以請求一直都有被監控，只是持續監控的那份在 Prometheus 與日誌平台、不在終端機。生產 pipeline 的設計（metrics、dashboard、SLO、告警與 vendor 選型）屬後端觀測性的範圍，見 [可觀測性平台](/backend/04-observability/)；當排查升級成事故、需要止血與復盤的協作流程時，見 [事故處理與復盤](/backend/08-incident-response/)。

## 下一步路由

- 系統資源（CPU／記憶體／磁碟）的即時監控：[TUI 監控工具](/cli/tui-monitoring-tools/)。
- 把即時觀測擺進可持久化的多工器 pane：[tmux 基礎](/cli/tmux-persistence-and-basics/)。
- 這類工具在遠端工具分類中的定位：[終端機圖形化工具總覽](/cli/cli-graphical-tools-overview/)。
