---
title: "Load Average（負載平均）"
date: 2026-10-12
description: "看到 uptime 或 node_load1 的數字、要判斷主機是不是在排隊時，查 load average 算的是什麼、除以核心數怎麼讀、Linux 為什麼把等磁碟的行程也算進去，以及在虛擬機與容器裡量到的值代表誰"
weight: 469
tags: ["backend", "capacity-planning", "observability", "knowledge-card"]
---

Load average 是一段時間內處於可執行狀態的平均行程數：正在用 CPU 的，加上在佇列裡等 CPU 的。Linux 另外把處於不可中斷睡眠（D 狀態，通常是在等磁碟讀寫）的行程也算進去，所以 Linux 的 load 同時反映 CPU 與磁碟的排隊。`uptime` 與 `/proc/loadavg` 給的三個數字是 1 分鐘、5 分鐘、15 分鐘的指數平均，node_exporter 以 `node_load1`、`node_load5`、`node_load15` 輸出。它是 [USE Method](/backend/knowledge-cards/use-method/) 裡 Saturation 的代表訊號之一。

## 概念位置

load 本身是行程數，要除以核心數才讀得出意思；它和 [CPU Steal Time](/backend/knowledge-cards/cpu-steal-time/) 量的是不同的現象，被虛擬化層拿走的 CPU 時間不會讓 load 升高：

| load 除以核心數 | 讀法                                                                   |
| --------------- | ---------------------------------------------------------------------- |
| 小於 1          | 每顆核心平均不到一個可執行的行程，沒有排隊                             |
| 1 左右          | 核心剛好被用滿                                                         |
| 大於 1          | 有行程在排隊；例如 8 顆核心、load 55，平均每顆核心有六個以上的行程在等 |

核心數在 macOS 用 `sysctl -n hw.ncpu`、Linux 用 `nproc` 查。Prometheus 裡的寫法是 `node_load1 / count without (cpu, mode) (node_cpu_seconds_total{mode="idle"})`。

load 高而 CPU 使用率不高時，多半是磁碟在排隊：Linux 的 load 含 D 狀態的行程。要把 CPU 與磁碟的排隊分開，看 `rate(node_cpu_seconds_total{mode="iowait"}[5m])`，或在實體 Linux 主機上看 PSI（`node_pressure_cpu_waiting_seconds_total` 與 io 那一組）。

## 可觀察訊號與例子

- **虛擬機裡的 load 只代表虛擬機**：macOS 上的 Docker 跑在一台 Linux 虛擬機裡，Mac 被其他程式吃到 load 55 時，虛擬機裡的 load 除以核心數可以只有 0.3 到 1.3。排隊的是 Mac 上的程式，虛擬機只是分到的 CPU 時間變少，見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)〈監控所在層看不到的範圍〉。雲端虛擬機被其他租戶搶走 CPU 的那一部分，記在 [CPU Steal Time](/backend/knowledge-cards/cpu-steal-time/)，不在 load 裡。
- **容器裡看到的 load 是整台主機的**：`/proc/loadavg` 沒有依容器分開，在容器裡跑 `uptime` 看到的是主機（或虛擬機）的值，不是那個容器自己的排隊。
- **load 1 分鐘的值跳動大**：它是指數平均，短暫的批次工作就能拉高；判斷持續的飽和看 5 分鐘、15 分鐘的值，或在告警規則加 `for`。

## 設計責任

拿 load 判斷主機飽和時，先寫下量到的是哪一層（主機、虛擬機或容器）、核心數是哪一層的核心數；告警門檻寫成除以核心數之後的值（例如 1.5），並註明 Linux 的 load 含等磁碟的行程。壓測或效能比較的紀錄附上當時主機本身的 load 與核心數，見 [共用主機的資源競爭](/operations/05-capacity-planning/shared-host-contention/)〈容量估算〉。
