---
title: "5.C1 Tradeshift：self-managed Kubernetes 遷移到 EKS"
date: 2026-05-07
description: "零停機平台遷移的分段策略案例。"
weight: 1
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是把平台遷移從「搬家」改寫成「流量與依賴分段切換」。

## 觀察

Tradeshift 從 self-hosted Kubernetes 遷移到 Amazon EKS，legacy 叢集上運行 409 個 service。遷移以零停機為硬性前提，且要求對應用程式碼零修改——遷移的複雜度由平台層吸收，服務團隊不改程式碼。

遷移採用 parallel cluster 架構：新舊叢集同時運行，透過 Linkerd service mesh 的 multi-cluster 能力橋接。Linkerd 在新叢集中建立 mirrored service（帶叢集後綴），讓跨叢集服務呼叫對應用層透明。流量切換用 Linkerd 的 traffic splitting policy 分批控制，不需要修改個別服務的路由邏輯。

跨叢集延遲實測：從 EKS 叢集存取 legacy 叢集的 gateway，P50=2ms、P95=8ms、P99=9ms。這個延遲水平足以支撐遷移期的跨叢集服務呼叫，但對延遲敏感的路徑仍需要在同一叢集內完成切換才能消除這層額外延遲。

## 判讀

這類遷移的難點在跨叢集服務依賴與流量切換，Kubernetes API 相容性反而是最容易處理的部分。Linkerd multi-cluster 在這個案例中解決了三個問題：跨叢集 service discovery（mirrored service 自動同步）、流量分批控制（traffic splitting 不改應用碼）、遷移期 rollback（切回舊叢集只需調整 traffic split 比例）。

409 個 service 的遷移不是一次完成——service 之間有依賴關係，遷移順序要按依賴拓樸規劃。被多個服務依賴的基礎 service（auth、config）通常最後遷移或在兩邊都保留，避免跨叢集呼叫成為所有服務的共同瓶頸。

遷移期最大的隱性風險是「跨叢集延遲累積」。單次跨叢集呼叫 P99=9ms 看似可接受，但一條請求路徑如果串接 5 個跨叢集呼叫，累積延遲可達 45ms。遷移規劃要把服務依賴鏈上的跨叢集呼叫次數納入切換順序考量。

## 策略

1. **建立 parallel cluster + mesh bridge**：新叢集用 EKS 建立，Linkerd multi-cluster 連接新舊叢集，mirrored service 讓跨叢集呼叫透明。
2. **按依賴拓樸排序遷移批次**：葉子服務（無下游依賴）先遷，基礎服務最後遷或雙邊保留。每批遷移後驗證跨叢集延遲是否在可接受範圍。
3. **Traffic splitting 分批切流量**：每個服務遷移後，用 traffic split 從 0% 開始逐步把流量導向新叢集。觀察 per-service error rate 與 latency，確認穩定後提高比例。
4. **保留 rollback 路徑**：舊叢集服務不立即下線，traffic split 隨時可切回 100% 舊叢集。rollback 操作是調整 split 比例，不需要重新部署。
5. **遷移完成後拆除 mesh bridge**：所有服務切換完成且穩定觀測後，移除跨叢集 Linkerd 連線，舊叢集下線。

## 可回寫的章節段落

- [5.2 分階段平台遷移](/backend/05-deployment-platform/kubernetes-deployment/#分階段平台遷移)：traffic split 的分批切換與回退策略
- [5.4 跨叢集 Discovery](/backend/05-deployment-platform/service-discovery/)：Linkerd mirrored service 是跨叢集 discovery 的 service mesh federation 做法
- [6.8 Release Gate](/backend/06-reliability/release-gate/)：每批切換的放行條件與停損訊號

## 引用源

- [Tradeshift migration to EKS without downtime using Linkerd](https://aws.amazon.com/blogs/containers/tradeshifts-migration-to-amazon-eks-without-downtime-using-linkerd/)
