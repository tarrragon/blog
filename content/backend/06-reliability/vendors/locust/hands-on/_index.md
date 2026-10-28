---
title: "Locust 的實作紀錄"
date: 2026-10-28
description: "要在本機用 Docker 照著跑一次 Locust：locustfile、headless 執行與 CSV、exit code、quitting 事件裡的門檻判定與 master、worker 的分散執行時讀"
weight: 2
tags: ["backend", "reliability", "vendor", "locust", "hands-on"]
---

這個資料夾收用 Locust 實際操作的紀錄：前置條件、每一步的指令與輸出、遇到的錯誤與除錯過程、量到的值。gate 的判斷寫在上一層的 [Locust 在效能 regression gate 的用法](/backend/06-reliability/vendors/locust/locust-performance-regression-gate/)，容量探測的判斷寫在 [Locust 在容量探測的用法](/backend/09-performance-capacity/vendors/locust/locust-capacity-probing/)，這裡的文章連回去，不重寫。

## 章節文章

| 文章                                                   | 操作                                                                                                                                |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| [Locust 在本機跑負載測試的實測紀錄](locust-local-lab/) | 受測服務、locustfile、headless 執行與 CSV、內建的 exit code、quitting 事件裡的門檻判定、--reset-stats 與 on_start、master 與 worker |
