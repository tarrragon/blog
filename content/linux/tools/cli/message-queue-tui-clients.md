---
title: "終端機訊息佇列客戶端：Kafka 的 kaskade/yozefu/ktea 與 Redis 的 iredis"
date: 2026-06-16
draft: false
description: "要在終端機連 Kafka／Redis broker 瀏覽 topic 與消費訊息、挑對應的 TUI 客戶端、或搞懂訊息佇列客戶端為何多半綁單一 broker 協議時回來讀"
tags: ["cli", "tui", "message-queue", "kafka", "redis", "kaskade", "yozefu", "iredis", "remote"]
---

終端機訊息佇列客戶端把 broker 的 topic、partition、consumer group 與訊息內容做成可導航的文字介面，讓遠端只有終端機時也能瀏覽訊息流、消費單一 topic、看消費進度，取代把連線資訊餵給桌面工具（Kafka 的 Conduktor、Redis 的 RedisInsight）的需求。它跟 broker 自帶的純指令工具（`kafka-topics.sh`、`rabbitmqctl`、`redis-cli`）互補：指令工具適合腳本與一次性查詢，TUI 適合「邊看 topic 清單邊翻訊息內容」這種互動探索。

本文承接 [終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/) 的訊息佇列客戶端分類。broker 端的純指令操作與 vendor 選型見 [Kafka](/backend/03-message-queue/vendors/kafka/)、[Redis Streams](/backend/03-message-queue/vendors/redis-streams/)、[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) 服務頁。

## 跟 SQL 客戶端最大的不同：多半綁單一 broker 協議

訊息佇列 TUI 幾乎都綁定單一 broker 協議，這是選型要先認清的一點，也跟 SQL 客戶端剛好相反。[SQL 客戶端](/linux/tools/cli/sql-database-clients/) 一個工具靠 adapter 連 Postgres、MySQL、SQLite 多種資料庫；訊息佇列這邊，Kafka 的 TUI 說的是 Kafka protocol、不認 AMQP，RabbitMQ 的 TUI 走 management API、也不讀 Kafka topic。能同時連多種 broker 的工具是少數例外（見後文 queuepeek）。

所以選型順序是先定 broker、再挑該 broker 生態的工具。實機盤點下來，Kafka 的 TUI 生態最成熟（多個活躍專案、安裝管道齊全），Redis 有強的增強型 REPL，RabbitMQ 與跨 broker 工具仍在早期。

## 兩種範式：全螢幕 TUI 與增強型 REPL

訊息佇列客戶端沿用跟 SQL 客戶端同一組範式區分。全螢幕 TUI（`kaskade` / `yozefu` / `ktea`）把 topic 清單、訊息內容、consumer 狀態排進多個面板，鍵盤導航瀏覽；增強型 REPL（`iredis`）仍是一行行打指令，但加上補全、語法高亮與型別感知輸出，是原生 client 的升級版。

選哪種看工作型態：要在多個 topic 間翻訊息、看 partition 與 consumer group 全貌，用全螢幕 TUI；要快速接上跑幾條指令、或塞進腳本，用增強型 REPL。

## Kafka 全螢幕 TUI：kaskade、yozefu、ktea

Kafka 有三個定位不同的全螢幕 TUI，互動模型與連線設定各異。

`kaskade`（Python、Textual 寫，實測 4.0.7）分 admin 與 consumer 兩個子命令，連線參數走 `-b`。`kaskade admin -b localhost:9092` 進管理模式，實測連上 broker 後渲染出 topics 面板，欄位是 name、partitions、replicas、in sync、groups、members、records，一頁看完叢集的 topic 全貌。`kaskade consumer -b localhost:9092 -t orders --from-beginning` 進消費模式翻單一 topic 的訊息，`-v json` 與 `-v registry` 切 payload 解碼方式，後者配 `--registry url=http://localhost:8081` 接 Schema Registry。SSL / SASL 不走 `-b`，要用 `--config security.protocol=SSL` 逐項帶或 `--config-file kafka.properties` 餵設定檔。

`yozefu`（Rust 寫、binary 名是 `yozf`，MAIF 維護）主打跨 topic 的搜尋查詢，把找特定 record 當成核心場景。它的查詢語言是 SQL 風的，預設 `initial_query` 是 `from end - 10`（從尾端往回取 10 筆），search filter 還能用 WebAssembly 自訂（`create-filter` / `import-filter` 子命令）。連線走 config 模型而非純 flag：`yozf config` 會印出設定（檔案在 `~/Library/Application Support/io.maif.yozefu/config.json`），每個 cluster 在裡面定義 `bootstrap.servers`、`security.protocol` 與 schema registry，再用 `yozf -c <cluster> -t <topics>` 指定要連哪個。

`ktea`（Go 寫，Homebrew 0.8.0）同樣是 config-based，cluster 連線設定走首次啟動的互動流程而非命令列旗標。啟動旗標有 `-debug` 與 `-plain-fonts`，後者在終端機沒裝 NerdFonts、圖示顯示成亂碼時關掉圖示。本機裝起來、啟動旗標確認過，cluster 連線與深層瀏覽走互動設定流程、未逐步驗證。

判讀：要一頁看完 topic / consumer group 狀態、或邊看邊消費，選 `kaskade`；要在大量 topic 裡用查詢撈特定 record，選 `yozefu` 的搜尋模型；`ktea` 是另一個 Go 單 binary 選擇、偏好互動式設定 cluster 的可評估。

## 增強型 REPL：iredis（Redis 與 Redis Streams）

`iredis`（Python 寫，實測 1.16.1）是 `redis-cli` 的增強版，補上指令補全、語法高亮與型別感知輸出，手感仍是 REPL。它跟 dbcli 家族的 `pgcli` / `litecli` 同一類定位。實測非互動可跑，把指令用管線餵進去就回結果：`echo "DBSIZE" | iredis -h localhost -p 6390`，適合塞腳本。

它對 Redis Streams（[03 的 vendor 之一](/backend/03-message-queue/vendors/redis-streams/)）的檢視特別省事。`peek <key>` 會先看型別再自動取值，string 顯示 strlen 與內容、stream 走 `XINFO`；實測對一個 stream 跑 `XINFO STREAM` 直接回 length、last-generated-id 等欄位，不必先 `TYPE` 再決定下哪個讀取指令。它是通用 Redis client、不是 stream 專用工具，但 Redis Streams 的 consumer group 操作（`XPENDING`、`XCLAIM`、`XINFO GROUPS`）都在這套指令補全範圍內。

## RabbitMQ 與跨 broker：生態仍在早期

RabbitMQ 與「一個工具連多種 broker」這兩塊目前缺乏可直接安裝驗證的成熟工具，列出供參考、本機未實機驗證。

> RabbitMQ 的 TUI 候選有 `rabbitui`（走 RabbitMQ management API）與 `rabbithole`（帶 exchange / binding 的 topology browser、支援 Protobuf 解碼）。兩者都不在 Homebrew 與 crates.io 的發佈管道，本機未安裝驗證。在缺 TUI 的情況下，RabbitMQ 的互動瀏覽仍以內建的 Management UI（web，預設 15672 埠）為主，純終端機則回到 `rabbitmqctl` 與 `rabbitmqadmin`。

> 跨 broker 的 `queuepeek`（Rust 寫，宣稱同時連 RabbitMQ、Kafka、MQTT）對應 SQL 類裡 `usql` 的「一個工具連多種後端」定位。本機 `cargo install queuepeek` 在編譯 `rdkafka-sys`（綁定原生 librdkafka）階段失敗、未能驗證。

## gotcha（實測）

- `yozefu` 預設帶一個名為 `localhost` 的 cluster、指向 `localhost:9092`。連非預設 port（例如本機測試的 9093）要先 `yozf configure` 改掉 `bootstrap.servers`，直接用 flag 覆寫不會生效。
- `kaskade` 的 `-b` 只接 bootstrap server；SSL / SASL 等安全設定一律走 `--config key=value` 或 `--config-file`，混在 `-b` 裡會被當成 broker 位址。
- `ktea` 的 `-plain-fonts`：終端機沒裝 NerdFonts 時圖示會顯示成亂碼方塊，加這個旗標關掉圖示就恢復可讀。

## 同類其他選擇

Redis 的全螢幕 TUI（如 `redis-tui`）與其他 Kafka TUI（如 `kafka-tui`）未在本輪實機驗證、列出供參考。Kafka TUI 這塊專案數量較多，挑選時以發佈管道（Homebrew / pip / crates.io 直接可裝）與維護活躍度篩選，不追求窮舉。

## 下一步路由

- broker 端純指令工具與 vendor 選型：[Kafka](/backend/03-message-queue/vendors/kafka/)、[Redis Streams](/backend/03-message-queue/vendors/redis-streams/)、[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) 服務頁。
- 同範式的資料庫客戶端對照：[終端機 SQL 客戶端](/linux/tools/cli/sql-database-clients/)。
- 把客戶端擺進可持久化的多工器 pane：[tmux 基礎](/linux/tools/cli/tmux-persistence-and-basics/)。
- 訊息佇列客戶端在遠端工具分類中的定位：[終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/)。
