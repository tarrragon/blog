---
title: "Resource Limit"
tags: ["資源限制", "Resource Limit"]
date: 2026-04-24
description: "說明服務可使用的 CPU、memory 與相關資源上限如何影響行為"
weight: 135
---

Resource Limit 的核心概念是「限制一個服務實例可使用多少 CPU、memory 或其他運行資源」。它會直接影響啟動、排程、延遲、穩定性與故障型態，當成單純的部署參數會低估其影響面。 可先對照 [Retention](/backend/knowledge-cards/retention/)。

## 跟其他概念的關係

Resource Limit 位在 container、runtime、deployment platform 與 scheduler 之間。它決定服務在資源不足時是被 throttling、被拒絕排程，還是因記憶體超限而被終止。 可先對照 [Retention](/backend/knowledge-cards/retention/)。

## 可觀察訊號

系統需要 resource limit 的訊號是：

- 多個 instance 需要共享固定主機資源
- 單一服務可能因記憶體成長或 CPU 尖峰影響其他服務（共用資源的干擾從哪裡看得到見 [Noisy Neighbor](/backend/knowledge-cards/noisy-neighbor/)；上限之外還有保留資源、分機、專用實體機等更深的隔離層級，見 [共用主機的資源競爭](/devops/operations/05-capacity-planning/shared-host-contention/)〈隔離的層級與代價〉）
- 平台需要用上限保護整體節點穩定性

## 接近真實網路服務的例子

Kubernetes container limit、單機 systemd service 的 cgroup 限制、worker pool 的 CPU 上限或 memory cap，都屬於 resource limit 的問題。

## 判斷條件與後果

Resource Limit 的判斷看兩組區分與一組連動。request 是 scheduler 排程時保留的量，limit 是執行時的上限；request 設得低於實際用量時，scheduler 會把超出節點實際容量的 instance 排到同一個節點，資源競爭到執行時才出現。CPU 超過上限時程序被 throttling，表現是延遲上升而程序還活著；memory 超過上限時程序因 OOM 被終止，表現是重啟與進行中的請求失敗，兩種故障的排查方向不同。上限的數值跟實際流量、cache 大小、啟動成本與重試行為連動：啟動時的 CPU 尖峰或 cache 暖機的記憶體成長超過上限時，instance 在啟動階段就被 throttle 或終止，它的流量經由重試轉到剩下的 instance，剩下的 instance 也更接近上限。
