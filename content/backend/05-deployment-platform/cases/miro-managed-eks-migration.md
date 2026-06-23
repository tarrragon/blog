---
title: "5.C5 Miro：Managed EKS 遷移"
date: 2026-05-07
description: "從自維運平台轉向 managed EKS 的組織與技術協同案例。"
weight: 5
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是說明平台遷移也會改變團隊職責分工。

## 觀察

Miro 從自維運 Kubernetes 遷移到 managed EKS。遷移前的狀態是平台團隊大部分精力花在叢集本身的運維——control plane 升級、node AMI 維護、etcd 備份、安全修補。這些工作是必要的，但它們跟「讓開發者更快交付功能」沒有直接關聯。

遷移後 managed EKS 接管了 control plane 運維。平台團隊的工作重心從「維持叢集跑起來」轉向「定義 release flow、observability convention、developer experience」。這個轉變是 managed 平台的組織層面價值，技術層面的價值（省維運、自動升級）反而是次要的。

## 判讀

平台託管化的價值在讓團隊把心力從底層維護轉到交付效率與可靠性策略。這個判讀成立的前提是組織主動重新定義職責邊界——managed 平台不會自動帶來組織轉型，它只是移除了一類維運負擔。如果平台團隊在遷移後沒有重新定義職責，很容易繼續用舊模式工作（只是工作量少了），錯失把省下的精力轉到更高價值工作的機會。

另一個判讀是 managed 平台引入新的 grey zone。control plane 由供應商管理，但 cluster-internal 元件（CNI、ingress controller、service mesh、cluster DNS）的 ownership 需要顯式界定。Miro 的經驗顯示這些 grey zone 若不在 day-1 處理，後續會在事故時暴露——「以為供應商在管」跟「供應商認為客戶在管」的認知差距，會讓故障排查繞圈。

## 策略

1. **先定義遷移後的平台責任邊界**：列出四層責任矩陣——cluster 層（供應商管）、cluster-internal 層（platform team 管）、application 層（service team 管）、跨層議題（協作）。每層有明確 owner，避免 grey zone。責任矩陣的詳細結構見 [5.7 Managed 平台跟團隊職責邊界](/backend/05-deployment-platform/traffic-config-control-plane-boundary/#managed-平台跟團隊職責邊界)。
2. **以自動化流程取代手動平台操作**：遷移前的手動操作（node 升級、cert rotation、backup restore）在 managed 平台上由供應商或 IaC 接管。剩餘的手動操作（namespace provisioning、resource quota 設定、network policy review）也要自動化或流程化，避免依賴個人經驗。
3. **將 incident 與 release policy 接回平台治理**：managed 平台的 incident 跟 self-managed 不同——control plane 故障由供應商處理，但供應商的 incident 訊號要進入自家的 incident timeline。release policy（升級節奏、canary 比例、rollback 條件）在 managed 平台上仍是 platform team 的責任。

## 回退判讀

從 managed 回退到 self-managed 的成本極高（要重建 control plane 運維能力），因此這類遷移的回退策略通常是「在 managed 平台內回退」而非「回到 self-managed」。具體做法是保留舊叢集一段時間作為 fallback，但同時接受「回到 self-managed 不是選項」的設計假設。

## 下一步路由

回 [5.1 container runtime](/backend/05-deployment-platform/container-runtime/) 看遷移後 runtime 層的變化驗證。回 [5.7 managed 平台與職責邊界](/backend/05-deployment-platform/traffic-config-control-plane-boundary/#managed-平台跟團隊職責邊界) 看職責矩陣的完整結構。回 [5.5 平台與入口威脅建模](/backend/05-deployment-platform/attacker-view-platform-entry-risks/) 看遷移期攻擊面變動。

## 引用源

- [Miro on AWS containers and EKS](https://aws.amazon.com/solutions/case-studies/miro-amazon-eks/)（原始 URL 已失效，內容基於骨架與通用工程知識擴充）
