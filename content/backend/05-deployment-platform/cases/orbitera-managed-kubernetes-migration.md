---
title: "5.C3 Orbitera：遷移到 Managed Kubernetes"
date: 2026-05-07
description: "平台重置時如何讓產品不中斷地完成編排層轉換。"
weight: 3
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是說明平台遷移的關鍵在服務連續性與能力重建，單次技術替換只是其中一步。

## 觀察

Orbitera 原本在 AWS 上以 EC2 為基礎運行 monolithic 架構，使用 EC2 + S3 + RDS + RedShift 組合。被 Google Cloud 收購後，在產品持續運作的前提下遷移到 Google Kubernetes Engine（GKE），同時從 monolith 重構為 microservices 架構。

遷移後的架構運行在 multi-zone 配置下，每個 zone 維持 3 個 replica，確保單一 zone 故障時服務不中斷。整合 Cloud SQL（取代 RDS）、Google 的 load balancer、Stackdriver（觀測）。遷移完成後取得的操作能力包含 on-demand scaling、快速部署到新 region/zone、以及快速 rollback 失敗的 build。

## 判讀

跨平台遷移本質是能力遷移：部署、觀測、恢復與團隊流程都需要同步重建。Orbitera 的遷移同時改變了兩個維度——平台（AWS → GCP）和架構（monolith → microservices）。雙維度同時改變放大了遷移風險，但也讓團隊避免了「先遷平台再拆架構」的兩階段成本。

這個案例揭露的隱性工作量在「能力對等重建」。原本在 AWS 上已經建好的觀測（CloudWatch → Stackdriver）、資料庫操作（RDS → Cloud SQL）、load balancing 都要在新平台上重新建立並驗證。這些能力不會隨著 workload 遷移自動出現——需要明確的 checklist 和驗證流程。

monolith → microservices 的架構重構改變了 runtime 的基本假設。Monolith 的 readiness 是單一進程啟動完成；microservices 的 readiness 涉及多個服務之間的依賴就緒。[5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 的 readiness 設計取捨在這類重構後需要重新定義——哪些是必要依賴、哪些是可降級依賴，從 monolith 時代的「全部在同一個進程」變成需要顯式判斷。

Multi-zone HA（3 replicas/zone）是遷移後 managed 平台提供的基線能力。在 self-managed 環境下實現相同程度的跨 zone 冗餘需要大量手動配置（zone-aware scheduling、cross-zone load balancing）；managed 平台把這些收進平台層，團隊精力從「維持 HA 運作」轉向「定義 HA 目標」。

## 策略

1. **先驗證新平台的最小可行服務**：選擇一個依賴少、風險低的服務在 GKE 上完成完整 deployment cycle（build → deploy → observe → rollback），驗證 CI/CD pipeline、觀測整合、rollback 路徑都可運作。
2. **建立能力對等 checklist**：列出舊平台已有的操作能力（觀測、告警、backup、secret 管理、log 收集），逐一確認新平台有對應方案且經過驗證。未對等的能力是遷移的 blocking 條件。
3. **逐步搬遷核心工作負載**：按依賴關係排序遷移批次，保留舊平台的回切路徑。每批遷移後在新平台上跑 load test 驗證容量與恢復能力。
4. **把平台能力納入日常治理節奏**：遷移完成不是終點——GKE 版本升級、node pool 更新、Cloud SQL 維護窗口都要進入團隊的日常操作流程，避免遷移後進入「只部署不維護」的狀態。

## 可回寫的章節段落

- [5.1 Container Runtime — 遷移期的 Runtime 穩定性](/backend/05-deployment-platform/container-runtime/)：monolith → microservices 改變 image 建置策略與啟動行為
- [5.6 Platform Lifecycle Contract — 遷移期的 Lifecycle 重新驗證](/backend/05-deployment-platform/platform-lifecycle-contract/)：readiness 條件在架構重構後需重新定義
- [6.7 DR/Rollback Rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)：遷移後的回退路徑驗證

## 引用源

- [Why we migrated Orbitera to managed Kubernetes on Google Cloud Platform](https://cloud.google.com/blog/products/gcp/why-we-migrated-orbitera-to-managed-kubernetes-on-google-cloud-platform/)
