---
title: "5.C7 Airbnb：Istio 升級治理"
date: 2026-05-07
description: "service mesh 升級在大規模環境下如何保持高可用。"
weight: 7
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是把平台元件升級從一次性作業轉成可重播流程。

## 觀察

Airbnb 在數十個 Kubernetes 叢集、數萬個 pod、數千個 VM 的規模下持續升級 Istio service mesh，峰值流量達數千萬 QPS。團隊累計完成 14 次成功的 Istio 升級。

升級的核心挑戰是規模帶來的協同成本：無法逐一通知每個 workload team 進行升級配合，也無法同時監控所有 workload 的升級狀態。升級策略必須對 workload team 透明——workload 不需要改程式碼或調配置就能完成 proxy 版本切換。

## 判讀

基礎平台元件升級若缺乏分批治理，會形成全域風險放大器。Istio 升級的影響面覆蓋所有跑 sidecar 的服務——一次壞的升級可以讓整個叢集的服務間通訊中斷。這個風險決定了升級策略必須是 canary 模式（小比例先行），而且 canary 的粒度要夠細（namespace 或 workload 級別），才能在問題擴大前攔截。

另一個判讀是升級流程本身要版本化。第一次升級靠資深工程師手動操作可以成功，但這個知識留在個人經驗裡。第二次升級換了人就可能踩到不同的坑。把升級流程固定成可重播的 spec（升級計畫 → 執行 → 驗證 → 確認/回退），讓升級從「英雄行為」變成「例行操作」。

## 策略

1. **Canary upgrade model（兩版本並存）**：採用 Istio 的 canary upgrade 機制，同時跑兩個版本的 Istiod。新版本的 sidecar proxy 跟對應版本的 control plane 配置一起原子部署，避免跨版本相容性問題。透過 revision label 決定每個 namespace 使用哪個版本的 Istiod。
2. **自建工具解耦基礎設施更新與 workload 部署**：團隊開發了 Krispr（mutation framework），在 CI 階段注入 Istio revision label，並在 admission 階段對超過兩週未部署的 pod 重新注入最新 label。這讓 workload 在正常部署流程中自動完成 proxy 升級，不需要額外操作。
3. **rollouts.yml 定義升級批次與比例**：用 spec 檔定義每個環境（staging / production）、每個 namespace pattern 的版本分佈（例如 staging 75% 舊版 / 25% 新版）。比例可以逐步調整——先 5% → 25% → 50% → 100%。每個批次有明確的觀測窗口與停損條件。
4. **VM 升級用 mxrc controller**：Kubernetes 外的 VM workload 用 mxrc controller 根據 rollouts.yml 更新 tag，遵守健康狀態檢查與可用性門檻。VM 的升級通常在兩週內透過自然輪替完成。
5. **升級事件進 incident timeline**：升級期間的短暫錯誤（proxy 重連、配置同步延遲）在事故 timeline 上標記為升級事件，避免被誤判成獨立事故。升級的決策紀錄用 incident decision log 格式，讓下次升級可以回溯上次的判斷依據。

## 升級節奏的收斂

14 次升級的經驗讓升級流程逐步收斂。多數 workload 在正常 deployment 時自動完成 proxy 升級（因為 Krispr 在 admission 階段注入最新 revision）。沒有 regular deployment 的 workload 在四週內透過自然 pod cycling（node 維護、HPA 調整）完成升級。這個四週窗口是可接受的——超過四週未部署的 workload 通常也是低變動、低風險的。

## 回退判讀

Istio 升級的回退是把 revision label 切回舊版本、讓 pod 在下次 restart 時重新注入舊版 sidecar。回退的風險在於回退期間新舊 proxy 混跑，traffic policy 可能不完全一致。穩定做法是先在小範圍驗證回退行為（一個 namespace），確認 traffic policy 一致性後再擴大回退範圍。

## 下一步路由

回 [5.2 kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/) 看 rollout 節奏與 probe 設計。回 [5.7 平台元件升級的可重播流程](/backend/05-deployment-platform/traffic-config-control-plane-boundary/#平台元件升級的可重播流程) 看通用升級框架。回 [8.6 IC handoff](/backend/08-incident-response/ic-handoff-long-incident/) 看升級期事故的指揮交接。

## 引用源

- [Seamless Istio Upgrades at Scale](https://airbnb.tech/infrastructure/seamless-istio-upgrades-at-scale/)
