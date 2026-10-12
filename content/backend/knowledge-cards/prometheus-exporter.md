---
title: "Prometheus Exporter（指標轉接程式）"
date: 2026-10-12
description: "要監控一個不會自己輸出 Prometheus 指標的系統（主機、容器、資料庫、快取、Nginx）時，查 exporter 做什麼、它和應用程式自己開的 /metrics 差在哪，以及 exporter 讀得到資料卻缺標籤、或者讀不到它所在層以外的機器時怎麼發現"
weight: 467
tags: ["backend", "observability", "prometheus", "knowledge-card"]
---

Prometheus exporter 是把某個系統的狀態轉成 Prometheus 指標格式、開一個 HTTP 端點讓 Prometheus 定期來讀（scrape）的程式。被監控的系統本身不必懂 Prometheus：node_exporter 讀 Linux 的 `/proc` 與 `/sys` 輸出主機的 CPU、記憶體與磁碟；cAdvisor 讀 cgroup 輸出每個容器的用量；postgres_exporter 連進 PostgreSQL 查統計視圖；nginx-prometheus-exporter 讀 Nginx 的 `stub_status`。應用程式自己用 client library 開的 `/metrics` 是另一條路：程式直接輸出自己的指標，不經過轉接。

## 概念位置

| 來源                  | 誰輸出指標                                | 指標的名稱由誰決定 | 適用                                             |
| --------------------- | ----------------------------------------- | ------------------ | ------------------------------------------------ |
| exporter              | 在被監控的系統旁另跑的轉接程式            | exporter 的作者    | 第三方系統：主機、容器、資料庫、快取、代理伺服器 |
| 應用程式的 `/metrics` | 程式本身                                  | 自己的團隊         | 自己寫的服務：依路由的延遲、業務事件             |
| Pushgateway           | 短命的工作把結果推過去，Prometheus 再來讀 | 工作的作者         | 跑完就結束、等不到被讀的批次工作                 |

表裡前兩列的分工對應兩種訊號：exporter 多半提供 [USE Method](/backend/knowledge-cards/use-method/) 的資源訊號，應用程式的 `/metrics` 多半提供 [RED Method](/backend/knowledge-cards/red-method/) 的請求訊號。exporter 是 Prometheus 拉取模式（pull）的延伸：Prometheus 主動去讀，所以 exporter 掛掉時 Prometheus 在下一次讀取就知道（`up` 變成 0）。各層的 exporter 怎麼組合，見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)；Prometheus 本身的設定見 [Prometheus](/backend/04-observability/vendors/prometheus/)。

## 可觀察訊號與例子

- **讀得到但分不出是誰**：`up` 是 1、指標有數字，標籤卻缺了用來分辨對象的那一個。實例是 cAdvisor 在 OrbStack 上找不到 containerd 的 socket，每個容器只剩 cgroup 的雜湊 id、沒有容器名稱，依服務分組的查詢全部落空。
- **讀到的是另一台機器**：exporter 只看得到它所在的那一層。macOS 上的 Docker 跑在 Linux 虛擬機裡，裝在 compose 裡的 node_exporter 回報的是虛擬機的 load（2.89），同一時間 Mac 本機的 load 是 55。磁碟則同時看得到兩顆：虛擬機放 Docker 資料的那一顆，以及 OrbStack 以 virtiofs 掛進來的 Mac 磁碟，兩者剩餘空間不同，只看 Docker 資料那一顆會以為空間充足。
- **標籤組合爆量**：exporter 把每個連線、每個查詢都當成一個標籤值輸出時，時間序列的數量暴增，見 [Metric Cardinality](/backend/knowledge-cards/metric-cardinality/)。

## 設計責任

每接上一個 exporter，驗收三件事：Prometheus 讀得到 exporter（`up` 是 1）而且 exporter 連得到它監控的服務（`pg_up`、`redis_up` 這類 exporter 自己輸出的連線狀態是 1）、每一個預期的對象都出現在標籤裡、刻意製造一次它該看到的狀況而數字有反應。另外寫下它裝在哪一層、看不到哪些層，看不到的層改由裝在那一層的 exporter 補上，或在那一層直接檢查（例如在主機上跑 `uptime`）。
