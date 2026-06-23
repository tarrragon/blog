---
title: "5.4 service discovery"
date: 2026-04-23
description: "整理 endpoint discovery 與 DNS"
weight: 4
tags: ["backend", "deployment", "service-discovery"]
---

服務發現（[service discovery](/backend/knowledge-cards/service-discovery/)）的核心責任是讓服務在變動環境中仍能找到正確目標實例。它處理的是定位與可用集合，不處理業務設定判斷；這個邊界清楚後，部署切換與故障回退才可預期。

## DNS 與 registry

service discovery 常見兩種路徑：DNS 查詢與 service registry。DNS 提供簡化解析路徑，適合標準服務發現；registry 提供更細節的實例狀態與元資料，適合複雜路由與多租戶治理。

選擇重點是變更頻率與一致性需求。實例變動頻繁或跨區路由複雜時，registry 能提供更細控制；穩定內網服務可優先 DNS 路徑降低操作成本。

### DNS-based Discovery 的運作與限制

Kubernetes Service 的 ClusterIP 模式是最常見的 DNS-based discovery：kube-dns / CoreDNS 回覆一個虛擬 IP，kube-proxy 用 iptables / IPVS 做 L4 負載均衡到實際 pod IP。Headless Service（`clusterIP: None`）則直接回傳所有 pod IP 的 A record，讓客戶端自行選擇目標。

DNS-based discovery 的限制來自 DNS 本身的語意：

1. **TTL 與快取**：DNS 回應帶 TTL，客戶端和中間 resolver 會快取。當 pod 被摘除但 DNS 快取尚未過期，客戶端仍會嘗試連到已不存在的 IP。Kubernetes CoreDNS 的 Service TTL 預設 30 秒，但客戶端語言 runtime 可能有自己的 DNS cache（JVM `networkaddress.cache.ttl` 預設 30 秒、有些版本預設 -1 代表永不過期）。
2. **無健康資訊**：DNS A record 不帶健康狀態。回覆的 IP 可能對應已經 not-ready 但尚未被 endpoint controller 移除的 pod。這個時間窗口取決於 kubelet sync 頻率與 endpoint controller 的反應速度。
3. **無權重 / 元資料**：DNS 不原生支援流量權重、版本標記、區域偏好。需要這些能力時要靠 service mesh 或 client-side load balancing。

DNS 路徑的工程價值在於零侵入——任何能解析 DNS 的程式碼都自動取得 discovery 能力，不需要額外 SDK 或 sidecar。缺點是控制粒度只到 IP 層，無法表達更豐富的路由語意。

### Registry-based Discovery 的運作模式

Service registry（Consul、etcd、Eureka、Nacos）維護 key-value store，每個 service instance 主動註冊自己的地址、metadata 與健康狀態。Client 透過 registry API 或 local agent 取得可用 instance 清單。

Registry 的工程價值在於提供 DNS 無法表達的元資料：instance 的版本、區域、權重、標籤都可以作為路由條件。代價是所有 service 都需要 registry 連線邏輯（SDK 或 sidecar），且 registry 本身成為基礎設施依賴——registry 不可用時，新 instance 無法註冊、現有 instance 無法被發現。

Registry 跟 DNS 不互斥。常見做法是 registry 作為 source of truth，再用 DNS interface 對外提供查詢（Consul DNS Interface、CoreDNS 的 etcd plugin）。這讓簡單場景走 DNS、複雜路由走 registry API、兩者共用同一份 instance 清單。

### 選擇判讀框架

| 需求                          | DNS-based                 | Registry-based                |
| ----------------------------- | ------------------------- | ----------------------------- |
| instance 變動頻率低、路由簡單 | 適合：低維護、零侵入      | 過度設計                      |
| 需要權重路由或版本切流        | 不適合：DNS 不帶權重      | 適合：metadata + 路由規則     |
| 需要跨叢集 / 跨區域 discovery | 需要外部 DNS 配合（困難） | 適合：registry federation     |
| 服務用多語言實作              | 適合：任何語言都能解 DNS  | 需要每個語言的 SDK 或 sidecar |
| 需要即時健康反映              | 受 TTL 限制、有延遲窗口   | 適合：health check 即時更新   |

## endpoint discovery

[Internal Endpoint](/backend/knowledge-cards/internal-endpoint/) discovery 的責任是維持可連線目標集合。這包含註冊、健康檢查、摘除、重建後回註冊。服務端 readiness 與 discovery 健康判斷要對齊，否則會出現不可服務實例仍被路由的情況。

endpoint 變更需要可追溯訊號，讓事故期間能快速判讀是路由失真、註冊延遲，還是下游本身不可用。

### 註冊時序與 Readiness 對齊

endpoint 的註冊時機是 discovery 穩定性的關鍵變數。註冊太早（服務尚未 ready 就被加入可用集合）會導致客戶端打到未就緒實例；註冊太晚（服務已 ready 但尚未被 discovery 看到）會導致容量不足。

Kubernetes 的做法是把 endpoint 跟 readinessProbe 綁定：readiness pass 才把 pod IP 加入 Endpoints 物件。這個設計讓 readiness 定義直接決定 discovery 行為。但 readiness probe 的判斷到 Endpoints 更新之間仍有延遲（endpoint controller sync 週期 + kube-proxy rules 更新），這個延遲窗口內的行為要理解：

- Pod 剛從 not-ready 變 ready：endpoint controller 需要同步周期把 pod IP 加入 Endpoints → kube-proxy 更新 iptables / IPVS → 流量才會到。期間該 pod 不接流量但已可服務。
- Pod 從 ready 變 not-ready：同樣有延遲。期間客戶端仍可能打到已 not-ready 的 pod。drain 設計要覆蓋這段窗口。

### 摘除節奏與 Drain 的配合

endpoint 摘除不是瞬時的。從 pod 標記 not-ready 到所有 client 停止向它送流量，中間經過多個同步步驟。這段時間內，被摘除的 pod 仍會收到流量。

穩定做法是在 preStop hook 加入短暫等待（通常 5-15 秒），讓 endpoint 更新有時間傳播到所有 kube-proxy / envoy，然後再開始 graceful shutdown。這段 preStop 等待是 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 中 drain 總窗口（短 API 通常 5-30 秒）的 endpoint 傳播子區間，drain 總窗口還要覆蓋 preStop 之後的在途請求收斂時間。

### 跨叢集 Discovery 的挑戰

對應 [5.C1 Tradeshift self-managed K8s → EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/)：揭露「遷移難點通常在跨叢集服務依賴與流量切換、不在 Kubernetes API 本身」。跨叢集 discovery 是遷移期的核心難題——服務 A 在新叢集、服務 B 在舊叢集，A 要能找到 B。

跨叢集 discovery 的常見做法：

1. **外部 DNS + 加權路由**：兩個叢集的 service 都註冊到外部 DNS（Route 53、Cloud DNS），用權重控制流量比例。簡單但粒度粗，只能整體切、不能 per-service 切。
2. **Service mesh federation**：Istio multi-cluster、Linkerd multi-cluster 把跨叢集 endpoint 統一管理。粒度細、可以 per-service 切流量，但引入 mesh 的複雜度。
3. **Application-level routing**：應用自己管理多叢集 endpoint（通常透過 config 或 feature flag），切換時改 config。最靈活但最手動，適合遷移期的過渡方案。

遷移期最危險的狀態是「服務切過去了、discovery 沒切過去」——新叢集的服務 A 仍透過舊 discovery 找舊叢集的 B，跨網路延遲從微秒級跳到毫秒級，或在網路分區時完全斷開。discovery 切換要跟服務切換同批規劃。

## failure fallback

[fallback](/backend/knowledge-cards/fallback/) 在 discovery 層的責任是縮小定位失敗影響。常見策略包含本地快取最後可用集合、區域優先回退、受控重試與短暫降級。

fallback 設計要明確停止條件。長期依賴過期 endpoint 快取會造成隱性錯誤累積，事故期反而更難收斂。

### Fallback 的三層防線

discovery 故障的 fallback 可分三層，每層有不同的代價與風險：

**第一層：本地 endpoint 快取**。Client 維持最後一次成功查詢的 endpoint 清單。discovery 服務不可用時，繼續用快取 endpoint。風險是快取中的 endpoint 可能已經下線或不健康。有效期要設上限——超過 N 分鐘的快取視為不可信，進入第二層。

**第二層：區域降級**。本區域的 endpoint 全部不可用時，降級到其他區域的 endpoint。代價是跨區延遲增加。風險是其他區域也可能因為同源故障而不可用。降級時要觀測跨區延遲是否在 SLO 內，超出則進第三層。

**第三層：服務降級**。discovery 完全失效時，服務本身降級——返回快取回應、靜態頁面、或明確的錯誤訊息。這一層的設計責任落在應用的 [fallback](/backend/knowledge-cards/fallback/) 策略，discovery 只負責提供「目前無可用 endpoint」的訊號。

三層防線的共同原則是每一層都有明確的進入條件和退出條件。進入 fallback 不是終點——要持續嘗試恢復正常路徑，fallback 狀態持續時間要被觀測和告警。

## 判讀訊號

| 訊號                               | 判讀重點                              | 對應動作                             |
| ---------------------------------- | ------------------------------------- | ------------------------------------ |
| 服務延遲上升且下游錯誤分布不均     | 路由到不可用或高負載實例              | 檢查註冊健康、刷新 endpoint 集合     |
| 節點重啟後短時間大量 5xx           | 註冊與 readiness 時序不對齊           | 延後註冊時機、收斂就緒條件           |
| 跨區呼叫比例異常升高               | 區域內可用集合失真或容量不足          | 檢查區域路由策略、恢復本地優先       |
| discovery 查詢成功但連線失敗率升高 | endpoint 新鮮度不足或 DNS 快取漂移    | 縮短 TTL、加入主動刷新               |
| fallback 命中率長期偏高            | 主路徑失效被掩蓋                      | 啟動故障調查、限制 fallback 存活時間 |
| 擴容後新 pod 遲遲不接流量          | endpoint 註冊延遲或 kube-proxy 同步慢 | 檢查 endpoint controller 延遲        |
| 遷移期跨叢集延遲突增               | discovery 沒切過去、跨網路打舊叢集    | 規劃 discovery 切換與服務切換同批    |

## 常見誤區

Service discovery 跟 DNS 設定的混淆，會讓註冊時序、健康判斷與摘除節奏的缺口在平時被忽略。這類缺口在平時不明顯，通常在切版、擴縮容或區域異常時集中爆發。

把 fallback 命中率視為穩定指標也容易誤判。fallback 長期偏高代表主路徑問題被遮蔽，應回頭檢查 endpoint 新鮮度與註冊健康，而不是只放寬重試。

把 DNS TTL 設成 0 試圖取得即時一致性，會大幅增加 DNS 查詢量。DNS 的設計前提是快取——TTL 0 在高流量服務下會讓 DNS server 成為瓶頸。穩定做法是設合理 TTL（5-30 秒）搭配 client-side 主動刷新。

把 JVM 的 DNS cache 當成 OS 的 DNS TTL——JVM `networkaddress.cache.ttl` 的預設值在不同版本不同（有些版本是 30 秒、有些是永不過期）。容器化部署時要顯式設定，避免 pod IP 變了但 JVM 還在打舊 IP。

## 定位邊界

service discovery 專注「找到可用實例」。當問題進入設定分發、版本切換、策略開關，責任轉到 [Config Rollout](/backend/knowledge-cards/config-rollout/) 與部署策略章節。邊界分明能避免故障排查時把不同控制面混為一談。

discovery 跟 load balancing 的邊界：discovery 回答「有哪些 endpoint 可用」，load balancing 回答「在可用 endpoint 中選哪一個」。DNS round-robin 把兩者混在一起，registry-based 方案通常把兩者分開，讓 LB 策略（round-robin、least-connection、consistent hash）在 discovery 結果之上獨立運作。

## 案例回寫

發現與定位鏈路可用 [5.C3 Orbitera：managed K8s migration](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/) 回寫。先看遷移期間實例註冊、摘除與 DNS/registry 同步節奏，再對照本章判讀 endpoint 新鮮度與 fallback 壽命是否合理。

[5.C1 Tradeshift self-managed K8s → EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) 從跨叢集角度支撐：揭露遷移期的 discovery 挑戰——「難點在跨叢集服務依賴與流量切換」。遷移期 discovery 要處理新舊叢集的 endpoint 共存、切換時序、回退路徑。

這些案例主要支撐「定位集合新鮮度」與「跨叢集 discovery 同步」判讀。不直接支撐 LB 連線 timeout 或 runtime 建置一致性；若問題在連線生命週期或映像漂移，應轉到 5.3 或 5.1。

遇到「查詢成功但連線失敗率高」時，應拆成註冊時序、TTL 與快取刷新三條線同步驗證，避免把定位問題誤判成下游異常，再把證據分流到 [8.18 Incident Intake & Evidence Triage](/backend/08-incident-response/incident-intake-evidence-triage/)。

## 跨模組路由

1. 與 5.2 的交接：實例註冊與可用判定回到 [Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。
2. 與 5.3 的交接：路由目標與流量合約回到 [load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。
3. 與 5.6 的交接：endpoint 註冊時序與 readiness 的對齊回到 [Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)。
4. 與 5.7 的交接：discovery 與 control plane boundary 的分責回到 [Traffic、Config 與 Control Plane Boundary](/backend/05-deployment-platform/traffic-config-control-plane-boundary/)。
5. 與 4.13 的交接：依賴拓樸與發現信號回到 [Service Topology 與 Dependency Map](/backend/04-observability/service-topology/)。
6. 與 8.18 的交接：定位故障的證據分流回到 [Incident Intake & Evidence Triage](/backend/08-incident-response/incident-intake-evidence-triage/)。

## 下一步路由

要把發現機制放進流量契約，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。要看部署切換如何影響可用集合，接著讀 [5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。要看 discovery 在 control plane 邊界中的定位，接著讀 [5.7 Traffic、Config 與 Control Plane Boundary](/backend/05-deployment-platform/traffic-config-control-plane-boundary/)。
