---
title: "Resource Limit"
tags: ["資源限制", "Resource Limit"]
date: 2026-04-24
description: "說明服務可使用的 CPU、memory 與相關資源上限如何影響行為"
weight: 134
---

Resource Limit 的核心概念是「限制一個服務實例可使用多少 CPU、memory 或其他運行資源」。它不是單純的部署參數，而是會直接影響啟動、排程、延遲、穩定性與故障型態的約束。

## 概念位置

Resource Limit 位在 container、runtime、deployment platform 與 scheduler 之間。它決定服務在資源不足時是被 throttling、被拒絕排程，還是因記憶體超限而被終止。

## 可觀察訊號

系統需要 resource limit 的訊號是：

- 多個 instance 需要共享固定主機資源
- 單一服務可能因記憶體成長或 CPU 尖峰影響其他服務
- 平台需要用上限保護整體節點穩定性

## 接近真實網路服務的例子

Kubernetes container limit、單機 systemd service 的 cgroup 限制、worker pool 的 CPU 上限或 memory cap，都屬於 resource limit 的問題。

## 設計責任

設計時要區分 request 與 limit、理解 throttling 與 OOM 的差異，並把上限調整和實際流量、cache、啟動成本與重試行為一起看。Resource Limit 的目標是保護系統穩定，而不是只追求把數字填滿。

