---
title: "JMeter 的實作紀錄"
date: 2026-10-28
description: "要在本機用 Docker 照著跑一次 JMeter：test plan、CLI mode、JTL 與 dashboard、JMeter 之外的門檻判定與 remote testing 時讀"
weight: 2
tags: ["backend", "reliability", "vendor", "jmeter", "hands-on"]
---

這個資料夾收用 JMeter 實際操作的紀錄：前置條件、每一步的指令與輸出、遇到的錯誤與除錯過程、量到的值。gate 的判斷寫在上一層的 [JMeter 在效能 regression gate 的用法](/backend/06-reliability/vendors/jmeter/jmeter-performance-regression-gate/)，容量探測的判斷寫在 [JMeter 在容量探測的用法](/backend/09-performance-capacity/vendors/jmeter/jmeter-capacity-probing/)，這裡的文章連回去，不重寫。

## 章節文章

| 文章                                                   | 操作                                                                                                                                               |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| [JMeter 在本機跑負載測試的實測紀錄](jmeter-local-lab/) | 自建 image、手寫 test plan、CSV Data Set、CLI mode 與 JTL、dashboard 與 statistics.json、JMeter 之外的門檻判定、remote testing 的 client 與 server |
