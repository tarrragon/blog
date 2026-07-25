---
title: "5.2 Kubernetes 部署策略"
date: 2026-04-23
description: "整理 deployment、probe 與 rolling update"
weight: 2
tags: ["backend", "deployment", "kubernetes"]
---

Kubernetes 部署策略（Kubernetes deployment strategy）的核心責任是把服務版本切換做成可預測流程。Deployment 把副本數、健康訊號、流量承接、設定變更與回退條件組成同一條交付路徑。

## deployment、replica 與 rollout

Deployment 的責任是宣告目標狀態：期望副本數、版本、更新策略。rollout 的責任是把現況收斂到目標狀態，並在過程中維持可服務能力。這兩者分開理解後，才能在異常時判斷是目標設定問題，還是收斂過程問題。

rolling update 常用來降低單次切換風險。rolling update 的判讀重點是批次大小與節奏：每批新增多少新副本、每批回收多少舊副本、每批觀察多長時間。這些參數以服務容量曲線與回退時間目標校準、名稱本身只是工具標籤、不是判讀條件。

## probe 對齊服務生命週期

[probe](/backend/knowledge-cards/probe/) 要對齊服務生命週期，不同 probe 有不同責任：

1. [startup probe](/backend/knowledge-cards/startup-probe/)：確認服務啟動完成，避免慢啟動服務被過早重啟。
2. [readiness](/backend/knowledge-cards/readiness/) probe：確認服務可安全接流量。
3. liveness probe：確認服務仍可維持基本運作，必要時觸發重建。

probe 設計若只回傳固定成功，rollout 期間會出現「容器在線但服務未就緒」的流量抖動。穩定做法是讓 readiness 反映依賴就緒條件，例如資料庫連線池、必要配置、關鍵背景任務狀態。

### Startup probe 設計注意事項

startup probe 跟 `initialDelaySeconds` 解決同一個問題（避免慢啟動服務被 liveness 殺掉），但機制不同。`initialDelaySeconds` 是 liveness / readiness probe 的延遲啟動——在等待期間 probe 完全不跑，無法觀測啟動進度。startup probe 在啟動期間持續探測，一旦成功就交棒給 liveness / readiness，啟動失敗時能更快偵測到。

startup probe 的總容忍時間 = `failureThreshold × periodSeconds`。例如 `failureThreshold: 30, periodSeconds: 10` 給服務 300 秒啟動窗口。設計時先量測服務在最差情境下的啟動時間（冷啟動 + image pull + 依賴連線建立），再加 20-30% headroom 作為總容忍時間。

### Readiness probe 的深度選擇

readiness probe 的檢查深度決定它能攔截多少「可啟動但不可服務」的狀態。三個常見層級：

1. **Port check**（TCP probe）：確認進程在監聽。最淺，無法偵測依賴未就緒。適合依賴簡單、啟動快的服務。
2. **Dependency check**（HTTP endpoint 檢查必要依賴）：確認資料庫連線池、cache 連線可用。涵蓋多數「啟動完但依賴不通」的場景。常用做法是在 `/ready` endpoint 內驗證必要依賴的連線狀態。
3. **Deep health**（業務路徑驗證）：執行一次簡化的業務查詢確認端到端通路。最深但代價最高——probe 本身消耗資源，且可能被下游延遲拖慢導致 readiness 抖動。

依賴分類（必要 / 可降級 / 觀測）的判讀框架見 [5.6 Readiness 設計的核心取捨](/backend/05-deployment-platform/platform-lifecycle-contract/)。

## config rollout 與版本相容

[Config Rollout](/backend/knowledge-cards/config-rollout/) 需要和應用版本一起治理。設定先行、版本後行，或版本先行、設定後行，都要保留相容窗口。相容窗口存在時，才有漸進 rollout 與快速回退空間。

跨版本配置遷移要先定義停止條件：錯誤率上升、延遲尖峰、關鍵路徑失敗或下游壓力超標。停止條件明確後，部署決策才能一致。

### N-1 相容與 Feature Flag Gating

版本相容窗口的操作基線是 N-1 相容：版本 N 的程式碼可以處理版本 N-1 的設定，反之亦然。這讓 rollback 從「版本 + config 必須同時回退」降級成「版本先回退、config 稍後再處理」，回退操作的原子性要求降低。

N-1 相容的實作通常搭配 feature flag gating：新功能在程式碼中預設關閉，先部署程式碼（版本 N 上線但新功能 off），確認版本穩定後再開啟 feature flag。這讓版本部署跟功能啟用分成兩個獨立決策，rollback 時只需關 flag 而不必回退版本。

N-1 相容窗口的壽命要有明確終點。長期維護雙版本相容會累積技術債——舊欄位不能刪、舊路徑不能移除。穩定做法是在 rollout 完成 + 觀測確認穩定後設定移除 deadline，把 N-1 相容視為暫時性保護而非永久設計。設定注入方式與版本追蹤見 [5.1 配置注入方式與取捨](/backend/05-deployment-platform/container-runtime/)。

## Autoscaling 與部署策略協同

[autoscaling](/backend/knowledge-cards/autoscaling/) 在部署期間扮演容量緩衝角色。部署批次若超過服務可承受變動幅度，autoscaling 會被動補償並延長收斂時間。穩定做法是讓 rollout 節奏與容量策略同時設計：先保證服務穩態，再提高切換速度。

長連線服務或有大量背景任務的 workload，通常需要比 stateless API 更保守的 rollout 策略，並額外搭配 drain 與 reconnect 設計。

擴縮策略的演進需要版本化跟可回放。對應 [5.C6 Airbnb K8s 叢集擴縮演進](/backend/05-deployment-platform/cases/airbnb-kubernetes-cluster-scaling-evolution/)：揭露「擴縮策略版本化跟可回放」「不同 workload 區分擴縮政策」「容量治理跟事故指標綁定」三個方向。以下基於通用工程知識展開。

可重複套用的做法：

1. **擴縮策略進 IaC**：HPA / VPA / Karpenter / Cluster Autoscaler 的配置都進 git、變更走 release flow、避免手動調整在事故後被遺忘。IaC + 自動化的 ownership 邊界見 [5.7 [control plane](/backend/knowledge-cards/control-plane/) boundary](/backend/05-deployment-platform/traffic-config-control-plane-boundary/)。
2. **workload 分群擴縮**：stateless API、長連線服務、batch job、background worker 對擴縮的需求不同。把不同 workload 用不同 namespace + 不同 autoscaler policy 隔離，避免一套規則套全部。
3. **擴縮事件接事故指標**：HPA 觸發、scale-up 延遲、scale-down 過快、cluster autoscaler 加 node 失敗，都該在事故 timeline 上可見。回到 [4.13 service topology](/backend/04-observability/service-topology/) 的擴縮事件 vs 事故區分。

## 分階段平台遷移

平台遷移的本質是流量跟依賴的分段切換。遷移期內新舊叢集同時存在，rollout 策略要把跨叢集流量切換納入批次節奏、視為連續多批決策。本段聚焦流量 / 依賴切換時序；遷移期的團隊職責邊界重訂見 [5.7 Managed 平台跟團隊職責邊界](/backend/05-deployment-platform/traffic-config-control-plane-boundary/#managed-平台跟團隊職責邊界)。

對應 [5.C1 Tradeshift：self-managed K8s → EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/)：揭露「零停機遷移要把切換做成分段策略」「難點通常在跨叢集服務依賴跟流量切換、不在 Kubernetes API 本身」。對應 [5.C4 Mobileye workloads 遷移](/backend/05-deployment-platform/cases/mobileye-workloads-to-eks/)：揭露「分批遷移 workload、保留觀測對照」「明確切換 / 回退條件」「新平台先驗證容量跟恢復節奏」。以下基於通用工程知識展開。

可重複套用的分階段做法：

1. **新叢集 + 共通配置基線**：先在新叢集上建立跟舊叢集對等的配置基線（namespace、ResourceQuota、NetworkPolicy、Ingress class、storage class），讓 workload 可以無縫部署。
2. **小流量先導服務**：選擇影響面小、依賴單純的服務作為先導，先在新叢集跑完整 deployment cycle（rollout、drain、rollback 驗證）、累積信心後再擴大。
3. **可控流量分批切換**：用 DNS 加權、service mesh 流量切分或 LB 規則把流量分批從舊叢集導到新叢集。每批切換後驗證 SLI 偏差、再進下一批。
4. **每批保留回退路徑**：舊叢集服務不立即下線，保留作為回退目標。回退條件先驗證（rollback script、流量切回 DNS / LB 規則），再開始下一批切換。

延伸 5.C1 揭露的「跨叢集服務依賴是難點」、5.C10 中型組織判讀「服務本身切過去了、但資料面、認證面、觀測面還沒同步」也指向同類問題。跨叢集遷移最容易出的事故是「服務切過去了、依賴沒切過去」。Database、cache、message queue、observability pipeline、auth service 的切換時機要分別規劃，避免應用層在新叢集但仍跨網路打舊叢集的依賴，造成隱性 latency 或單點失效。規模差異下的同類問題見 [5.C10 對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)。

## 大規模 K8s 的設計取捨

K8s 在不同規模下的設計取捨會明顯分歧。小規模叢集追求簡單跟低運維成本，大規模叢集追求隔離跟自動化治理。同一套部署策略放到不同規模會在某個量級開始失效。

對應 [9.C12 Riot Games：246 個 EKS cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)：揭露架構決策從 multi-tenant cluster 改成 single-tenant per game、Karpenter + Terraform 的 cluster 級自動化、35ms 延遲門檻 + Local Zones / Outposts 區域部署（case 中「35ms 反推 region 部署」屬作者判讀層、本章引用此推論）。對應 [9.C34 GCP 130,000-node GKE cluster](/backend/09-performance-capacity/cases/gcp-130k-node-gke-cluster/)：揭露 control plane 極限取決於 storage backend（GCP 用 Spanner 替代 etcd）、AI workload 跟 web workload 容量規劃差異。對應 [9.C33 Maersk + Bosch AKS](/backend/09-performance-capacity/cases/maersk-bosch-azure-aks/)：揭露 Maersk 工程訴求引語「focus on things that makes the most business impact」、傳統產業上 K8s 動機是治理一致性（作者判讀）、適合 single-cluster-multi-namespace。

可重複套用的取捨判讀：

1. **single-tenant per workload vs single-cluster multi-namespace**：高隔離需求（每個 workload 失效不能影響其他）、高延遲敏感度（需 region cluster）→ 多 cluster；治理一致性訴求（統一 release flow、合規邊界）→ 單一 cluster 多 namespace。
2. **Cluster 容量極限取決於 control plane**：data plane（worker nodes）擴容容易、control plane（API server、etcd / storage）擴容難、瓶頸通常在 control plane。etcd 撐 5K-10K node 後吃力、需要替換 storage backend（Spanner / PostgreSQL / 自家 KV）才能撐萬級節點（見 [9.C34](/backend/09-performance-capacity/cases/gcp-130k-node-gke-cluster/)）。control plane 的 ownership 邊界由 [5.7 control plane boundary](/backend/05-deployment-platform/traffic-config-control-plane-boundary/) 處理。
3. **Multi-cluster 治理需要 IaC + 自動化**：Terraform / Crossplane / Cluster API + Karpenter / Cluster Autoscaler 是基本工具。手動管理超過數十個 cluster 不可行。
4. **AI workload 跟 web workload 容量規劃完全不同**：AI workload 短時間爆量創建 Pods（萬級 / 秒）、preempt 頻繁；web workload 節點生命週期長、變動緩。把 web 經驗套到 AI workload 容量規劃會嚴重低估壓力。

關鍵判讀是「先決定 cluster 是隔離單位還是治理單位」。Riot Games 把 cluster 當隔離單位（246 個獨立 cluster），Maersk / Bosch 把 cluster 當治理單位（單 cluster 多 namespace）。同一個工具兩種用法、決定整體運維模型。

對應 [5.C2 Condé Nast：EKS 平台整併與標準化](/backend/05-deployment-platform/cases/conde-nast-platform-modernization-eks/)：揭露多叢集整併到單一控制面的場景、跟 Maersk-Bosch 同屬「治理一致性」取捨方向（治理單位優先於隔離單位）。Condé Nast 的整併路徑是「盤點既有叢集差異 → 建立統一平台基線 → 藍綠或漸進切換業務流量」、對應前面「分階段平台遷移」段的批次節奏。

## 判讀訊號

| 訊號                                                                          | 判讀重點                     | 對應動作                              |
| ----------------------------------------------------------------------------- | ---------------------------- | ------------------------------------- |
| rollout 卡在中段且新副本反覆重啟                                              | probe 與啟動路徑不匹配       | 校正 startup/readiness 探針與超時參數 |
| rollout 完成後延遲與錯誤率短期上升                                            | 批次切換過快或下游未對齊     | 降低批次、延長觀察窗口、回退再重試    |
| config 變更後特定路徑失敗率飆升                                               | 設定與版本相容窗口不足       | 啟動回退配置、補雙軌相容              |
| autoscaling 在部署期間頻繁抖動                                                | 容量閾值與 rollout 節奏衝突  | 分離部署窗口與擴縮窗口、調整資源策略  |
| 長連線服務切版後 [reconnect storm](/backend/knowledge-cards/thundering-herd/) | drain 與連線生命週期控制不足 | 拉長 drain、分批切流、校正 timeout    |
| 跨叢集遷移後特定路徑 latency 升高                                             | 應用切過去但依賴未切、跨網路 | 規劃依賴切換時機、分批一致            |

## 常見誤區

把 Kubernetes 部署看成 YAML 套版，會忽略服務語意差異。相同 deployment 參數在不同服務上，可能代表完全不同風險。

把 probe 當成健康檢查 URL，會讓服務在邊界條件下過早接流量。probe 的工程價值在於反映服務真實可用條件。

把 cluster scale-up 想成「加 node 就好」也是常見誤判。當 cluster 規模超過 control plane 預設邊界，etcd / API server 會先撐不住，加 node 反而加重 control plane 負擔。

## 案例回寫

部署切換語意可用 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) 做回寫。先看事件中的失敗是在 rollout 批次、probe 判斷、還是 drain 時序，再對照本章的 rollout 節奏與停止條件。

這個案例主要支撐的是「部署批次與切換時序」判讀，不直接支撐資料庫交易切分或 consumer 冪等；若問題落在提交一致性或重播補償，應轉到 1.3 或 3.4。

若版本已切換但錯誤率延遲上升，先回到 probe 與 config 相容窗口，再把證據欄位接到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 跨模組路由

Kubernetes 部署策略要和觀測、驗證、事故流程同時對齊。

1. 與 5.6 的交接：startup / readiness / liveness / drain 的生命週期定義回到 [Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)。
2. 與 5.1 的交接：image、entrypoint、resource limit 的 runtime 層回到 [container 與 runtime](/backend/05-deployment-platform/container-runtime/)。
3. 與 5.3 的交接：流量承接與退出落在 [load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。
4. 與 5.4 的交接：endpoint 註冊與摘除回到 [service discovery](/backend/05-deployment-platform/service-discovery/)。
5. 與 5.7 的交接：control plane 跟 data plane 邊界落在 [Traffic、Config 與 Control Plane Boundary](/backend/05-deployment-platform/traffic-config-control-plane-boundary/)。
6. 與 4.20 的交接：版本切換證據進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
7. 與 6.8 的交接：放行與停損條件進入 [Release Gate](/backend/06-reliability/release-gate/)。
8. 與 8.19 的交接：部署中止與回退判斷進入 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要把部署與流量切換一起治理，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。要看切換失敗與回退判讀，接著讀 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)。要看大規模 K8s 容量設計，接著讀 [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 跟 [9.C34 GCP 130K-node](/backend/09-performance-capacity/cases/gcp-130k-node-gke-cluster/)。
