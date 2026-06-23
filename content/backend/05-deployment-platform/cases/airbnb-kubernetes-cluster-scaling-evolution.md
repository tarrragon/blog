---
title: "5.C6 Airbnb：Kubernetes 叢集擴縮演進"
date: 2026-05-07
description: "從手動擴縮走向自動化容量治理的部署平台案例。"
weight: 6
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是說明部署平台演進常來自容量治理需求。

## 觀察

Airbnb 的叢集擴縮經歷了多個演進階段。早期是手動調整 node 數量——工程師根據流量預測或事故壓力臨時加 node、事後忘記縮回。中期引入 Cluster Autoscaler，讓 node 數量跟 pending pod 連動。後期隨工作負載類型分化（stateless API、長連線服務、batch job、ML 訓練），單一 autoscaler policy 無法覆蓋所有場景，開始分群治理。

這個演進路徑的共同主題是「每當流量型態或 workload 組成改變，原本的擴縮策略就會在某個量級開始失效」。擴縮策略的有效期跟服務演進速度成反比。

## 判讀

叢集擴縮若停留在人工流程，面對高波動流量會放大成本與可用性風險。人工擴縮的問題有兩面：反應太慢（流量已衝高但 node 還沒加上來）和撤退太慢（流量已回落但多餘 node 繼續燒錢）。自動化解決反應速度，但引入新的判讀問題——autoscaler 的參數設定本身需要治理。

HPA 觸發閾值設太低會造成 pod 數量頻繁抖動；Cluster Autoscaler 的 scale-down delay 設太短會在流量波動時反覆 add/remove node，增加 pod eviction 頻率。這些參數的調校要依 workload 類型分群——API 服務的擴縮節奏跟 batch job 完全不同。

另一個判讀是擴縮策略跟事故指標要綁定。autoscaler 的動作（scale-up trigger、scale-down execution、node provision latency）如果不在事故 timeline 上可見，事故團隊無法分辨「是 autoscaler 來不及」還是「是應用本身有問題」。

## 策略

1. **擴縮策略版本化與可回放**：HPA / VPA / Cluster Autoscaler / Karpenter 的配置進 git，變更走 release flow。每次調參都有 commit 紀錄，事故後可以追溯「這次 scale-down 過快是因為哪次參數變更」。版本化的另一個價值是可回放——新的擴縮配置在 staging 環境用歷史流量 replay 驗證後，再推到 production。
2. **workload 分群擴縮**：stateless API 用 CPU / RPS-based HPA、batch job 用 queue depth-based HPA、長連線服務用 connection count-based 自訂 metric。不同 workload 類型放在不同 namespace，各自有獨立的 autoscaler policy。避免一套 HPA 規則套全部 workload。
3. **容量治理與事故指標綁定**：HPA 觸發事件、Cluster Autoscaler 的 scale-up / scale-down 事件、node provision latency 都送進事故 timeline（可用 Kubernetes event exporter 或 custom metric）。事故 timeline 上看到「HPA 觸發後 3 分鐘 node 才 ready」就能直接判斷「容量補充太慢」而非「應用有 bug」。

## 回退判讀

擴縮策略變更的回退比應用版本回退簡單——改 HPA / autoscaler 的 config 就好。風險在於回退後的舊策略可能已經跟當前 workload 型態不匹配（workload 成長了、流量特性變了）。穩定做法是回退後立刻進入觀察窗口，確認舊策略在當前流量下仍然有效。

## 下一步路由

回 [5.2 kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/) 看 autoscaling 與部署策略協同。回 [5.6 platform lifecycle contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 看不同 workload 的 lifecycle 差異如何影響擴縮設計。回 [6.9 capacity & cost](/backend/06-reliability/capacity-cost/) 看容量規劃的完整框架。

## 引用源

- [Dynamic Kubernetes Cluster Scaling at Airbnb](https://airbnb.tech/infrastructure/dynamic-kubernetes-cluster-scaling-at-airbnb/)（原始 URL 已失效，內容基於骨架與通用工程知識擴充）
