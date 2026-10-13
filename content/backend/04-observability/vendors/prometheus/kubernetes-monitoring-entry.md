---
title: "在 Kubernetes 上接上監控：kube-prometheus-stack 的元件、ServiceMonitor 與 PrometheusRule 的選取、儀表板 sidecar 與控制平面的讀取"
date: 2026-10-13
description: "在 Kubernetes 上以 kube-prometheus-stack 接上監控：chart 裝了哪些元件與 CRD，讀取對象與告警規則改以 ServiceMonitor、PrometheusRule 宣告之後由誰轉成 Prometheus 的設定，release 標籤決定哪些宣告會被選中，主機標籤改成節點標籤，儀表板經由 ConfigMap 與 sidecar 載入，以及控制平面元件只綁本機時讀不到的原因與單機叢集上的資源用量"
weight: 18
tags: ["backend", "observability", "vendor", "prometheus", "kubernetes"]
---

> 這一篇屬於 [Prometheus](/backend/04-observability/vendors/prometheus/) 的實作系列。[單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 與 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/) 在 Docker Compose 上以檔案寫讀取對象（scrape target）的清單、規則與儀表板；這一篇把同一件事搬到 Kubernetes 上。Kubernetes 的元件與物件（Pod、Deployment、Service、namespace）見 [Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/)。

這一篇整理在 Kubernetes 叢集裡以 kube-prometheus-stack 這個 Helm chart 接上監控之後，讀取對象、告警規則與儀表板各自怎麼宣告，以及哪些宣告會被忽略而不報錯。範圍從 chart 裝好開始，Helm 本身的用法見 [Helm](/infra/knowledge-cards/helm/)。文中的行為在 macOS（Apple Silicon）上的 kind 0.33（Kubernetes v1.37）實測，chart 是 kube-prometheus-stack 92.3.0（Prometheus Operator v0.94.1、Grafana 13.2.3），以 Helm 4.3 安裝；kind 是在一台電腦上以容器模擬節點的工具，見 [單機練習用的 Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/local-practice-clusters/)。

## kube-prometheus-stack 裝了什麼

在 Docker Compose 上，監控的每一個元件都是自己寫進 compose 檔的服務，讀取清單是 Prometheus 設定檔裡的一段。kube-prometheus-stack 把這些打包成一個 chart，一次裝進叢集：

- **Prometheus Operator**：一個常駐的控制程式，監看叢集裡描述監控的物件，把它們轉成 Prometheus 與 Alertmanager 的設定檔。
- **Prometheus 與 Alertmanager**：本身也由 Operator 依 `Prometheus`、`Alertmanager` 這兩種物件建立，以 StatefulSet 執行。
- **Grafana**：附 30 個預設儀表板，資料來源已經指向這個 Prometheus。
- **node-exporter**：以 DaemonSet 在每個節點跑一份，對應 Compose 上的 node_exporter。
- **kube-state-metrics**：讀 Kubernetes API，把 Deployment 的期望與實際副本數、Pod 的狀態這類叢集物件的狀態輸出成指標。
- **預設的告警規則**：實測 36 組、251 條，涵蓋節點、kubelet、API server 與上面這些元件；其中包括一條永遠成立的 `Watchdog`。

容器的 CPU 與記憶體不另外裝 cAdvisor：每個節點的 kubelet 內建 cAdvisor，chart 附的讀取設定直接讀 kubelet。

Operator 監看的物件是 chart 安裝的 CRD（Custom Resource Definition，讓 Kubernetes API 多認得一種物件），實測裝了十種，其中最常直接寫的是三種：

| 物件             | 宣告的內容                                                                                 | Compose 上對應的位置                            |
| ---------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------- |
| `ServiceMonitor` | 讀哪些 Service 背後的 Pod、讀哪個連接埠與路徑                                              | `prometheus.yml` 的 `scrape_configs` 與目標清單 |
| `PodMonitor`     | 不經過 Service，直接以 Pod 的標籤選讀取對象                                                | 同上                                            |
| `PrometheusRule` | 告警規則與預先算好結果的規則（[recording rule](/backend/knowledge-cards/recording-rule/)） | `rules/*.yml`                                   |

這三種物件由服務自己的團隊放在服務所在的 namespace，和 Deployment、Service 一起部署；Operator 把全叢集的這些物件收集起來，產生一份 Prometheus 設定。讀取清單因此跟著部署走，和 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/) 裡由部署工具產生目標清單是同一個想法，只是產生清單的程式換成 Operator。

## ServiceMonitor 與 release 標籤

以一個輸出 `/metrics` 的範例服務來看。服務有一個 Service，連接埠命名為 `web`；ServiceMonitor 以標籤選中這個 Service，指定讀 `web` 這個連接埠：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: example-app
  namespace: shop
  labels:
    release: kps           # kps 是 helm install 時取的 release 名稱，換成自己的
spec:
  selector:
    matchLabels: {app: example-app}    # 選中帶這個標籤的 Service
  endpoints:
    - port: web                        # Service 上連接埠的名稱，不是號碼
      interval: 15s
```

`metadata.labels` 那一行決定這個 ServiceMonitor 會不會被讀到。chart 建立的 `Prometheus` 物件只選帶 `release: <release 名稱>` 標籤的 ServiceMonitor、PodMonitor 與 PrometheusRule，namespace 不限：

```sh
# monitoring 換成安裝 chart 時指定的 namespace
kubectl -n monitoring get prometheus -o jsonpath='{.items[0].spec.serviceMonitorSelector}'
# {"matchLabels":{"release":"kps"}}
```

實測同一個 ServiceMonitor 先不帶這個標籤套用，等了 4 分鐘，Prometheus 的設定裡沒有它，Operator 沒有報錯，ServiceMonitor 物件上也沒有任何狀態欄位說明它沒被選中；補上 `release: kps` 之後，兩個 Pod 都出現在讀取對象裡。所以 ServiceMonitor 寫好而讀取對象沒出現時，先核對的是這個標籤與 `serviceMonitorSelector`。chart 的值 `prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues` 設成 `false` 時，選取條件改成全部選中，這是 chart 文件寫的做法，這次沒有實測。

PrometheusRule 同樣如此：不帶標籤的規則等了 2 分鐘沒有載入，補上標籤之後 30 秒出現在 Prometheus 的規則清單。chart 另外裝了一個驗證規則的 admission webhook（API server 在接受物件之前先送去檢查的服務），PromQL 寫錯時 `kubectl apply` 當場被拒，訊息指出是哪一組、哪一條規則與錯在第幾個字元：

```text
The "prometheusrules" is invalid: : 7:11: group "shop", rule 1, "ShopTargetDown":
could not parse expression: 1:55: parse error: unexpected identifier "up"
```

Compose 上要自己跑 `promtool check rules` 才擋得住的錯誤，在 Kubernetes 上由這個 admission webhook 在套用時擋下；而標籤不對的規則語法正確，通過檢查，然後被靜默忽略。

## 主機標籤改成節點標籤

ServiceMonitor 產生的讀取對象帶著這些標籤：`namespace`、`service`、`pod`、`container`、`endpoint`、`job`（預設是 Service 的名稱）與 `instance`（Pod 的 IP 與連接埠）。沒有代表節點的標籤。

Compose 上的告警與抑制都依 `host` 分組，一台主機飽和只壓下同一台主機上的症狀。在 Kubernetes 上，「主機」是節點，Pod 會被排到任何一個節點上、重建之後換節點，所以節點不能寫死在清單裡，要從服務發現的資訊取。ServiceMonitor 的 `relabelings` 就是 Prometheus 的 `relabel_configs`（見 [Relabeling](/backend/knowledge-cards/relabeling/)），服務發現給的 `__meta_kubernetes_pod_node_name` 是 Pod 所在的節點：

```yaml
  endpoints:
    - port: web
      interval: 15s
      relabelings:
        - sourceLabels: [__meta_kubernetes_pod_node_name]
          targetLabel: node
```

實測改了 ServiceMonitor 之後 41 秒，查詢結果裡的序列帶上 `node`：Operator 重新產生設定，Prometheus 旁邊的 config-reloader 讓它重新載入。改標籤同時產生了新的序列：同一個 Pod 在幾分鐘內查得到兩條 `up`，一條沒有 `node`、一條有，舊的那條要等過期才消失，序列的歷史在改標籤的那一刻斷成兩段。標籤因此在服務第一次接上監控時就決定好，之後再改，依這個標籤分組的面板與告警在那一刻前後各自只看到一段。

寫告警與抑制時以 `node` 取代 Compose 上的 `host`。另一種做法是不改讀取設定，在查詢時以 `kube_pod_info` 把 `node` 接上去（`* on (namespace, pod) group_left(node) kube_pod_info`），寫法與 node-exporter 序列的對應見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 的〈依原因抑制：主機飽和時壓下各服務變慢〉；兩者的差別在讀取時加的標籤每一條序列本身就帶著，查詢時接的則每一條規則都要寫一次。chart 附的其他讀取設定（例如 kubelet）各自帶哪些標籤，這次沒有逐一檢查，寫規則之前先在 Prometheus 查一次 `up` 的標籤，確認每個要分組的序列都有 `node`。

## 儀表板經由 ConfigMap 與 sidecar 載入

chart 附的 Grafana 旁邊跑著一個 sidecar 容器（同一個 Pod 裡、負責輔助工作的另一個容器）。它監看全叢集帶 `grafana_dashboard: "1"` 標籤的 ConfigMap 與 Secret，把裡面的 JSON 寫進 Grafana 讀取儀表板的目錄，再呼叫 Grafana 的重新載入 API。儀表板因此可以和服務放在同一個 namespace、跟著服務部署：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: shop-dashboard
  namespace: shop
  labels: {grafana_dashboard: "1"}     # sidecar 只撿這個標籤
data:
  shop.json: |
    {"uid": "shop-overview", "title": "shop 服務總覽", ...}
```

實測套用之後 23 秒，儀表板出現在 Grafana；刪掉 ConfigMap 之後 6 秒，儀表板從 Grafana 消失。從 ConfigMap 載入的儀表板是佈建（provisioned）的儀表板，chart 的佈建設定寫 `allowUiUpdates: false`：Grafana 的 API 對這個儀表板回 `canSave: true`，實際以 API 存檔時被拒，訊息是 `Cannot save provisioned dashboard`。所以在介面上調好的儀表板要匯出 JSON、改回 ConfigMap，這和 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 的〈Grafana：以檔案佈建資料來源與儀表板〉以檔案佈建儀表板的流程相同，只是檔案換成 ConfigMap。

資料來源也是同一個機制，標籤換成 `grafana_datasource: "1"`。

## 控制平面元件的 metrics 綁定位址與讀取失敗

裝好之後，Prometheus 的讀取對象裡有四個一直讀不到：controller-manager（10257）、scheduler（10259）、etcd 的 metrics（2381）與 kube-proxy（10249），錯誤是 `connection refused`。到 kind 的節點容器裡看，這四個程式都只聽 `127.0.0.1`：

```sh
docker exec <叢集名稱>-control-plane ss -ltn   # kind 的節點是一個容器，名稱是叢集名稱加 -control-plane
# 127.0.0.1:2381  127.0.0.1:10257  127.0.0.1:10259  127.0.0.1:10249
```

kind 以 kubeadm 建立控制平面，kubeadm 預設把這幾個元件的 metrics 端點綁在本機；Prometheus 在 Pod 網路裡，連的是節點的 IP，所以連不上。預設的告警規則因此各自成立一條：`KubeControllerManagerInstanceUnreachable`、`KubeSchedulerInstanceUnreachable`、`KubeProxyInstanceUnreachable`、`TargetDown`，以及 critical 的 `etcdInsufficientMembers`。一裝好就有 critical 告警成立，而叢集本身是正常的。

自己以 kubeadm 建的叢集（kind 也是）在建立時改這幾個綁定位址：

```yaml
# kind 的叢集設定；kind create cluster --name <名稱> --config <這個檔>
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: ClusterConfiguration
        controllerManager:
          extraArgs:
            - {name: bind-address, value: 0.0.0.0}
        scheduler:
          extraArgs:
            - {name: bind-address, value: 0.0.0.0}
        etcd:
          local:
            extraArgs:
              - {name: listen-metrics-urls, value: http://0.0.0.0:2381}
      - |
        kind: KubeProxyConfiguration
        metricsBindAddress: 0.0.0.0:10249
```

以這份設定重建之後，四個程式都改聽所有介面；從叢集裡的一個 Pod 連過去，etcd 與 kube-proxy 回 200，controller-manager 與 scheduler 回 403（連得上、要帶認證，Prometheus 讀取時帶 ServiceAccount 的 token）。這個重建的叢集上沒有再裝一次監控，所以讀取成功與告警解除沒有實測。綁到所有介面也讓節點網路上的其他程式連得到這些端點，正式叢集要搭配網路政策或防火牆限制來源。

託管的 Kubernetes（EKS、GKE、AKS）由雲端供應商管理控制平面，controller-manager、scheduler 與 etcd 多半不讓使用者直接讀，chart 的對應讀取設定只會一直失敗；這時在 chart 的值裡把 `kubeControllerManager.enabled`、`kubeScheduler.enabled`、`kubeEtcd.enabled` 設成 `false`，控制平面的狀態改看供應商提供的指標。

## 單機叢集上的資源用量與過載時的連鎖反應

裝好之後量這一組在叢集裡的記憶體（`container_memory_working_set_bytes`，依 Pod 加總）：Grafana 421 MB、Prometheus 355 MB、Alertmanager 58 MB、Operator 40 MB、kube-state-metrics 23 MB、node-exporter 19 MB，合計約 916 MB；kind 的節點容器整個約 2 GB。Prometheus 的活躍序列是 57,572 條，叢集裡只有一個節點、一個範例服務，這些幾乎全部來自 kubelet、API server 與預設的規則所需的指標，是 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 那一整組（約九千條）的六倍多。

這台 Mac 是 16 GB 記憶體，同時開著其他應用程式與 Docker 上的另一組服務。第一次安裝在 3 分 22 秒時失敗，錯誤是 `etcdserver: request timed out`；之後叢集出現一連串看似各自獨立的故障：

- API server 重啟 5 次、controller-manager 與 scheduler 各重啟十幾次，`kubectl` 偶爾回 `Forbidden`。
- Operator 與 kube-state-metrics 啟動時連不到 API server（`dial tcp 10.96.0.1:443: connect: connection refused`），進入 CrashLoopBackOff。
- node-exporter 與 Grafana 的存活探針逾時，被 kubelet 重啟；重啟又增加負載。
- 預設規則 `KubeAPIErrorBudgetBurn` 以 critical 成立。

這些故障的原因都不在 Kubernetes：Mac 的 swap 用到 13 GB、可用的記憶體只剩幾十 MB，磁碟每秒三千多次 I/O 都在換頁，系統負載（load average）到 90 而 CPU 使用率並不高。在單機叢集上看到 etcd 逾時或控制平面反覆重啟時，先在主機上看記憶體與 swap（macOS 是 `sysctl vm.swapusage` 與 `vm_stat`，Linux 是 `free` 與 `vmstat`），再查叢集。停掉 Docker 上的另一組服務、重新啟動 kind 的節點之後，叢集在半小時內恢復，所有 Pod 回到 Ready。

## 延伸閱讀：Compose 上的對應做法、Relabeling、Alertmanager 的通知與單機練習叢集

- 讀取對象、規則與儀表板以檔案管理時的寫法，見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/)；目標清單跟著部署走、主機標籤與主機消失的偵測，見 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/)。
- `relabelings` 在什麼時間點執行、讀得到哪些標籤、為什麼來源標籤不存在時目標標籤會整個消失，見 [Relabeling](/backend/knowledge-cards/relabeling/)。
- chart 附的 `Watchdog` 要接到外部的心跳服務才有作用，Alertmanager 的路由與通知見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)，接心跳服務的設定在〈Watchdog：告警鏈本身的心跳〉。
- kind、k3d 與 minikube 各自怎麼模擬節點、閒置時用多少資源，見 [單機練習用的 Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/local-practice-clusters/)。
