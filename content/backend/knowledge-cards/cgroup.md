---
title: "cgroup（控制群組）"
date: 2026-10-12
description: "設定容器的 CPU 與記憶體上限、讀 cAdvisor 的指標、或查容器為什麼被暫停與結束時，查 cgroup 是什麼、v1 與 v2 的差別，以及 Docker 與 Kubernetes 的參數各自對應到它的哪個控制檔"
weight: 471
tags: ["backend", "capacity-planning", "isolation", "knowledge-card"]
---

cgroup（control group）是 Linux 核心替一組行程記帳與設限的機制：把行程放進一個群組，核心就會統計這個群組用了多少 CPU、記憶體與磁碟讀寫，並依群組的設定限制或分配它們。容器的資源限制都建立在它上面：Docker 的 `--cpus`、`--memory` 與 Kubernetes 的 requests、limits，最後都寫成某個 cgroup 的控制檔；cAdvisor 讀 cgroup 的統計，輸出每個容器的用量，見 [Prometheus Exporter](/backend/knowledge-cards/prometheus-exporter/)。

## 概念位置

現在的發行版多半用 cgroup v2（單一階層，控制檔都在 `/sys/fs/cgroup/<群組>/` 下）；舊的 v1 每種資源各有一個階層、檔名不同。v2 的常用控制檔與它們的上層參數：

| 控制檔                     | 作用                                                                     | Docker／Kubernetes 的參數             |
| -------------------------- | ------------------------------------------------------------------------ | ------------------------------------- |
| `cpu.max`                  | CPU 上限：每個週期最多用多少時間，用完就暫停到下個週期（CPU throttling） | `--cpus`；limits.cpu                  |
| `cpu.weight`               | 搶 CPU 時的相對權重，不搶時不生效                                        | `--cpu-shares`；requests.cpu 換算而來 |
| `memory.max`               | 記憶體上限，超過時核心在群組內結束行程（OOM）                            | `--memory`；limits.memory             |
| `memory.low`、`memory.min` | 記憶體保留：主機吃緊時盡量（low）或一定（min）不回收這個群組的記憶體     | `--memory-reservation` 對應 low       |
| `io.max`、`io.weight`      | 磁碟讀寫的上限與權重，效果依磁碟與排程器而定                             | `--device-read-bps` 等                |

各層級的隔離能做到什麼、做不到什麼，見 [共用主機的資源競爭](/devops/operations/05-capacity-planning/shared-host-contention/)〈隔離的層級與代價〉；單一容器的值怎麼定，見 [Resource Limit](/backend/knowledge-cards/resource-limit/)。

## 可觀察訊號與例子

- **cAdvisor 只有 cgroup 的雜湊 id、沒有容器名稱**：cgroup 只認得一個 id，容器名稱與標籤要問容器執行環境（containerd）才知道，見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)〈Docker 跑在虛擬機裡時 cAdvisor 缺容器名稱〉。
- **延遲升高而主機的 CPU 不滿**：容器碰到 `cpu.max` 被暫停，`container_cpu_cfs_throttled_seconds_total` 升高（它在過載時呈現的週期性停頓見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)）。
- **容器被結束、退出碼 137**：超過 `memory.max`，見 [OOM killer 與退出碼 137](/linux/dotfile/knowledge-cards/oom-exit-code-137/)。

## 設計責任

設定容器的限制前，先確認主機用的是 cgroup v1 還是 v2（`stat -fc %T /sys/fs/cgroup` 回 `cgroup2fs` 是 v2），文件裡的控制檔名稱與指標依版本不同。限制寫進部署設定，不在主機上手動改控制檔。
