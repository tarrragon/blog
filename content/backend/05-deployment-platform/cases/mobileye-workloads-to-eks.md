---
title: "5.C4 Mobileye：Workloads 遷移到 EKS"
date: 2026-05-07
description: "大規模工作負載遷移到 managed Kubernetes 的分段治理案例。"
weight: 4
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是把 workload 遷移從基礎設施作業改成服務可用性作業。

## 觀察

Mobileye 將大規模工作負載遷移到 EKS。遷移動機集中在運維一致性與可用性治理——原有環境中不同團隊各自維護部署流程，升級節奏、監控覆蓋、容量規劃的標準不統一。遷移目標是用 managed 平台統一這些操作基線，讓各團隊可以專注在 workload 本身。

遷移範圍涵蓋多種 workload 類型：API 服務、資料處理 pipeline、ML 推論服務。這些 workload 的啟動時間、資源需求、drain 條件差異顯著，同一套遷移策略無法直接套用。

## 判讀

工作負載遷移若缺乏分段驗證，容易在切流時放大依賴與資源風險。這個判讀的具體含義是：workload 從舊平台搬到新平台時，表面上看 pod 跑起來了、health check 通過了，但依賴路徑（資料庫連線、cache endpoint、queue consumer 註冊）可能還指向舊環境。這類錯位在小流量時不明顯，放大流量後才暴露延遲升高或認證失敗。

另一個判讀是容量假設需要重新驗證。舊平台的 resource request/limit、HPA 設定是在舊環境的 node type、網路拓樸下校準的。新平台的 node 規格、storage driver、CNI 可能不同，原本的容量假設可能過鬆或過緊。

## 策略

1. **分批遷移 workload、保留觀測對照**：先遷移影響面小、依賴單純的 workload（如內部工具、非關鍵 API）。新舊平台同時跑相同 workload 時，比較 error rate、latency、資源使用率。觀測對照是驗證的基礎——沒有對照就無法判斷新平台行為是否符合預期。
2. **明確定義每批次切換與回退條件**：每批遷移前寫下「什麼條件算成功」和「什麼條件觸發回退」。成功條件用 SLI 偏差衡量（error rate 不超過基線 + N%、p99 latency 不超過基線 + M ms）。回退條件要可操作——回退腳本事先驗證、DNS/LB 規則切回路徑事先測試。
3. **新平台先驗證容量與恢復節奏**：在新平台上跑容量測試，確認 HPA 觸發、node scale-up、pod scheduling 的時間符合預期。恢復節奏驗證包含模擬 node 失效後 pod 重新調度的時間、模擬 deployment rollback 的完成時間。
4. **workload 類型分群遷移**：API 服務、batch job、ML 推論的遷移順序與驗證條件不同。API 服務看延遲與錯誤率；batch job 看完成時間與資料正確性；ML 推論看推論延遲與 GPU 資源分配。混在一批遷移會讓驗證條件模糊。

## 回退判讀

這類遷移的回退判讀重點是「回退到舊平台時，舊平台是否仍在可服務狀態」。遷移進行中若舊平台的資源已被縮減（node 數降低、monitoring 設定已移除），回退路徑就失效。穩定做法是在該批 workload 的新平台觀測窗口結束前，舊平台維持原規模不動。

## 下一步路由

回 [5.2 kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/) 看分階段平台遷移的流量切換節奏。回 [5.6 platform lifecycle contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 看不同 workload 類型的 lifecycle 差異。回 [6.19 reliability readiness review](/backend/06-reliability/reliability-readiness-review/) 看遷移前的可靠性評估。

## 引用源

- [Mobileye migration to Amazon EKS](https://aws.amazon.com/solutions/case-studies/mobileye-amazon-eks/)（原始 URL 已失效，內容基於骨架與通用工程知識擴充）
