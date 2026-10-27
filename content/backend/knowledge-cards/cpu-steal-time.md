---
title: "CPU Steal Time（被虛擬化層拿走的 CPU 時間）"
date: 2026-10-12
description: "雲端虛擬機的服務沒有改動、CPU 用量也不高卻變慢時，查 steal time 記的是什麼、怎麼從 node_exporter 算出比例、什麼環境量不到它，以及升高時的處置"
weight: 470
tags: ["backend", "capacity-planning", "observability", "knowledge-card"]
---

CPU steal time 是虛擬機想用 CPU、而虛擬化層（hypervisor）把那段時間分給同一台實體機上其他虛擬機的時間。Linux 虛擬機在 `/proc/stat` 的 steal 欄記錄它，`top` 顯示為 `st`，node_exporter 以 `node_cpu_seconds_total{mode="steal"}` 輸出。它是虛擬機裡少數能看到「虛擬機之外的競爭」的訊號，[Noisy Neighbor](/backend/knowledge-cards/noisy-neighbor/) 在雲端虛擬機上的主要證據就是它。

## 概念位置

`node_cpu_seconds_total{mode="steal"}` 是只增不減的累計秒數，要用 `rate()` 換成一段時間的比例：

```promql
# 每顆核心平均有多少比例的時間被分給別的虛擬機（0.1 代表一成）
avg without (cpu, mode) (rate(node_cpu_seconds_total{mode="steal"}[5m]))
```

它和 [Load Average](/backend/knowledge-cards/load-average/) 量的是不同的現象：被拿走的 CPU 時間不會讓虛擬機裡的行程變多，所以 steal 升高時虛擬機的 load 不一定升高。主機飽和的告警規則因此同時看兩者。

容器用完自己的 CPU 上限而被暫停（CPU throttling，`container_cpu_cfs_throttled_seconds_total`）是另一件事：成因是那個容器的配額，不是虛擬機之外的競爭，見 [Resource Limit](/backend/knowledge-cards/resource-limit/)。

## 可觀察訊號與例子

- **比例持續高於平常、各服務一起變慢而 CPU 用量不高**：同一台實體機上的其他租戶在用 CPU。
- **序列存在而值恆為 0**：有些虛擬化環境不提供 steal。macOS 上 OrbStack 的 Linux 虛擬機就是這樣，Mac 被其他程式吃到 load 55 以上時，steal 仍是 0，虛擬機裡沒有指標直接指出這個競爭，見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)。
- **可突發型機型**：AWS 的 T 系列在 standard 模式下 CPU 額度用完只剩基準效能，unlimited 模式額度用完會繼續突發並另外計費；額度剩多少要看雲端自己的監控（CloudWatch 的 `CPUCreditBalance`），虛擬機裡看不到，見 [共用主機的資源競爭](/devops/operations/05-capacity-planning/shared-host-contention/)〈容量估算〉。

## 設計責任

部署在雲端虛擬機上的服務，主機飽和的判斷要包含 steal 的比例；先確認環境確實提供它（比例在負載變化時會動，而不是恆為 0）。steal 長期偏高時的處置在虛擬機之外：換非突發型的機型、換主機，或在其他租戶的干擾不可接受時改用專用主機。
