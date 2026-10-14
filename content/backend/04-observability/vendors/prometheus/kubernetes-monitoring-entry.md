---
title: "在 Kubernetes 上接上監控：kube-prometheus-stack 的元件、ServiceMonitor 與 PrometheusRule 的選取、節點標籤、儀表板 sidecar、Alertmanager 的預設路由、控制平面的讀取與單節點叢集的資源用量"
date: 2026-10-13
description: "在 Kubernetes 上以 kube-prometheus-stack 接上監控：chart 裝了哪些元件與 CRD，讀取對象與告警規則改以 ServiceMonitor、PrometheusRule 宣告之後由誰轉成 Prometheus 的設定，release 標籤決定哪些宣告會被選中，主機標籤改成節點標籤，儀表板經由 ConfigMap 與 sidecar 載入，Alertmanager 預設不送任何通知，以及控制平面元件只綁本機時讀不到的原因、單節點叢集上的資源用量與記憶體不足時的表現"
weight: 19
tags: ["backend", "observability", "vendor", "prometheus", "kubernetes"]
---

> 這一篇屬於 [Prometheus](/backend/04-observability/vendors/prometheus/) 的實作系列。[單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 與 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/) 在 Docker Compose 上以檔案寫讀取對象（scrape target）的清單、規則與儀表板；這一篇把同一件事搬到 Kubernetes 上。Kubernetes 的元件與物件（[Pod](/backend/knowledge-cards/pod/)、Deployment、[Service](/backend/knowledge-cards/kubernetes-service/)、[namespace](/backend/knowledge-cards/namespace/)）見 [Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/)。

這一篇整理在 Kubernetes 叢集裡以 kube-prometheus-stack 這個 Helm chart 接上監控之後，讀取對象、告警規則與儀表板各自怎麼宣告，以及哪些宣告會被忽略而不報錯。範圍從 chart 裝好開始，Helm 本身的用法見 [Helm](/infra/knowledge-cards/helm/)。文中的行為在 macOS（Apple Silicon）上的 kind 0.33（Kubernetes v1.37）實測，chart 是 kube-prometheus-stack 92.3.0（Prometheus Operator v0.94.1、Grafana 13.2.3），以 Helm 4.3 安裝；kind 是在一台電腦上以容器模擬節點的工具，見 [單機練習用的 Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/local-practice-clusters/)。

## kube-prometheus-stack 裝了什麼

在 Docker Compose 上，監控的每一個元件都是自己寫進 compose 檔的服務，讀取清單是 Prometheus 設定檔裡的 `scrape_configs`。kube-prometheus-stack 把這些打包成一個 chart，一次裝進叢集：

- **Prometheus Operator**：一個常駐的控制程式，監看叢集裡描述監控的物件，把它們轉成 Prometheus 與 Alertmanager 的設定檔。
- **Prometheus 與 Alertmanager**：本身也由 Operator 依 `Prometheus`、`Alertmanager` 這兩種自訂物件（CRD，見下方）建立，以 StatefulSet 執行。
- **Grafana**：附 29 個預設儀表板，資料來源已經指向這個 Prometheus。
- **node-exporter**：以 DaemonSet 在每個節點跑一份，對應 Compose 上的 node_exporter。
- **kube-state-metrics**：讀 Kubernetes API，把 Deployment 的期望與實際副本數、Pod 的狀態這類叢集物件的狀態輸出成指標。
- **預設的告警規則**：實測 35 組、250 條，涵蓋節點、kubelet、API server 與上面這些元件；其中包括一條永遠成立的 `Watchdog`。

容器的 CPU 與記憶體不另外裝 cAdvisor：每個節點的 kubelet 內建 cAdvisor，chart 附的讀取設定直接讀 kubelet。

chart 預設不替 Prometheus 與 Alertmanager 建 PersistentVolumeClaim（`prometheus.prometheusSpec.storageSpec` 與 `alertmanager.alertmanagerSpec.storage` 都是空的），資料寫在 Pod 自己的暫存目錄裡。Pod 被重新排到別的節點或重建時，指標的歷史、Alertmanager 的靜音與通知紀錄一起消失；Prometheus 的保留期間預設 `10d`。正式叢集在這兩個值寫 `volumeClaimTemplate`，指定叢集裡可用的 StorageClass：

```yaml
# helm install 時以 -f 傳入的值檔；standard 換成 kubectl get storageclass 列出的名稱
prometheus:
  prometheusSpec:
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: standard
          accessModes: [ReadWriteOnce]
          resources: {requests: {storage: 2Gi}}
alertmanager:
  alertmanagerSpec:
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: standard
          accessModes: [ReadWriteOnce]
          resources: {requests: {storage: 1Gi}}
```

實測在 kind 上以這份值安裝，Operator 替兩者各建一個 PersistentVolumeClaim，兩個都進入 `Bound`。容量依保留期間與活躍序列數估算，估法見 [Prometheus 容量規劃與故障模式](/backend/04-observability/vendors/prometheus/capacity-failure-modes/)。

Operator 監看的物件是 chart 安裝的 CRD（Custom Resource Definition，讓 Kubernetes API 多認得一種物件），實測裝了十種，其中最常直接寫的是三種：

| 物件             | 宣告的內容                                                                                 | Compose 上對應的位置                            |
| ---------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------- |
| `ServiceMonitor` | 讀哪些 Service 背後的 Pod、讀哪個連接埠與路徑                                              | `prometheus.yml` 的 `scrape_configs` 與目標清單 |
| `PodMonitor`     | 不經過 Service，直接以 Pod 的標籤選讀取對象                                                | 同上                                            |
| `PrometheusRule` | 告警規則與預先算好結果的規則（[recording rule](/backend/knowledge-cards/recording-rule/)） | `rules/*.yml`                                   |

這三種物件由服務自己的團隊放在服務所在的 namespace，和 Deployment、Service 一起部署：ServiceMonitor 預設只選同一個 namespace 裡的 Service，放到別的 namespace（例如集中放在 `monitoring`）時要另寫 `spec.namespaceSelector`，否則它選不到任何 Service，也不報錯。Operator 把全叢集的這些物件收集起來，產生一份 Prometheus 設定。讀取清單因此跟著部署走，和 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/) 裡由部署工具產生目標清單是同一個想法，只是產生清單的程式從部署工具換成 Operator。

## ServiceMonitor 與 release 標籤

以一個輸出 `/metrics` 的範例服務來看。服務以一個 Deployment 跑兩個 Pod，前面有一個 Service，Service 的連接埠取名為 `web`；ServiceMonitor 以標籤選中這個 Service，指定讀 `web` 這個連接埠：

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

`metadata.labels` 那一行決定這個 ServiceMonitor 會不會被讀到。chart 建立的 `Prometheus` 物件以 `release: <release 名稱>` 這個標籤選 ServiceMonitor、PodMonitor 與 PrometheusRule，三種物件各自要帶這個標籤才會被選中，所在的 namespace 不限：

```sh
# monitoring 換成安裝 chart 時指定的 namespace
kubectl -n monitoring get prometheus -o jsonpath='{.items[0].spec.serviceMonitorSelector}'
# {"matchLabels":{"release":"kps"}}
```

輸出是 `{}` 時，選取條件是全部選中，標籤不影響。

實測同一個 ServiceMonitor 先不帶這個標籤套用，等了 4 分鐘，Prometheus 的設定裡沒有它，Operator 沒有報錯，ServiceMonitor 物件上也沒有任何狀態欄位說明它沒被選中；補上 `release: kps` 之後，範例服務的兩個 Pod 都出現在讀取對象裡。所以 ServiceMonitor 寫好而讀取對象沒出現時，先核對這個標籤與 `serviceMonitorSelector`，以及 ServiceMonitor 與 Service 是否在同一個 namespace、`endpoints.port` 寫的名稱與 Service 的連接埠名稱是否一致、`selector` 的標籤選不選得到 Service；這幾種錯都不報錯，讀取對象有沒有被產生，在 Prometheus 網頁的 Service discovery 頁面看（見 [Relabeling](/backend/knowledge-cards/relabeling/) 的〈可觀察訊號與例子〉）。在叢集裡開 Prometheus 的網頁看讀取對象，以 `kubectl -n monitoring port-forward svc/<Service 名稱> 9090` 把它轉到本機的 9090；Service 名稱含 release 名稱，以 `kubectl -n monitoring get svc` 查。chart 的值 `prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues` 設成 `false` 時，選取條件改成全部選中：實測以這個值升級之後，`serviceMonitorSelector` 變成 `{}`，一個不帶標籤的 ServiceMonitor 出現在 Operator 產生的設定裡。這個值只管 ServiceMonitor，同次升級之後 `ruleSelector` 仍是 `{"matchLabels":{"release":"kps"}}`；PodMonitor 與 PrometheusRule 各有自己的 `podMonitorSelectorNilUsesHelmValues`、`ruleSelectorNilUsesHelmValues`。

PrometheusRule 同樣如此：不帶標籤的規則等了 2 分鐘沒有載入，補上標籤之後 30 秒出現在 Prometheus 的規則清單。chart 另外裝了一個驗證規則的 admission webhook（API server 在接受物件之前先送去檢查的服務），PromQL 寫錯時 `kubectl apply` 當場被拒，訊息指出是哪一組、哪一條規則與錯在第幾個字元：

```text
The "prometheusrules" is invalid: : 7:11: group "shop", rule 1, "ShopTargetDown":
could not parse expression: 1:55: parse error: unexpected identifier "up"
```

Compose 上要自己跑 `promtool check rules` 才擋得住的錯誤，在 Kubernetes 上由這個 admission webhook 在套用時擋下；而標籤不對的規則語法正確，通過檢查，然後被靜默忽略。

## 主機標籤改成節點標籤

ServiceMonitor 產生的讀取對象帶著這些標籤：`namespace`、`service`、`pod`、`container`、`endpoint`、`job`（預設是 Service 的名稱）與 `instance`（Pod 的 IP 與連接埠）。沒有代表節點的標籤。

Compose 上的告警與抑制都依 `host` 分組，一台主機飽和只壓下同一台主機上的症狀。在 Kubernetes 上，「主機」是節點，Pod 會被排到任何一個節點上、重建之後換節點，所以節點不能寫死在清單裡，要從服務發現的資訊取。ServiceMonitor 的 `relabelings` 與 `metricRelabelings` 就是 Prometheus 的 `relabel_configs` 與 `metric_relabel_configs`（見 [Relabeling](/backend/knowledge-cards/relabeling/)），欄位名稱改成 camelCase（`sourceLabels`、`targetLabel`）；服務發現給的 `__meta_kubernetes_pod_node_name` 是 Pod 所在的節點：

```yaml
  endpoints:
    - port: web
      interval: 15s
      relabelings:
        - sourceLabels: [__meta_kubernetes_pod_node_name]
          targetLabel: node
```

實測改了 ServiceMonitor 之後 41 秒，查詢結果裡的序列帶上 `node`：Operator 重新產生設定，Prometheus 的 Pod 裡負責重新載入設定的 config-reloader 容器讓它重新載入。改標籤同時產生了新的序列：同一個 Pod 在幾分鐘內查得到兩條 `up`，一條沒有 `node`、一條有，舊的那條在約 5 分鐘沒有新的樣本之後被 Prometheus 判為過期才消失，序列的歷史在改標籤的那一刻斷成兩段。所以 `node` 這類分組用的標籤，最好在服務第一次套用 ServiceMonitor 時就寫進去（前一節的範例要接上監控時，就先加上這一段 `relabelings`）；之後再改的話，面板與告警依這個標籤分組時，改標籤之前的資料落在舊的那一組、之後的落在新的那一組，在保留期間內有一次接不起來的斷點。

寫告警與抑制時以 `node` 取代 Compose 上的 `host`。另一種做法是不改讀取設定，在查詢時以 `kube_pod_info` 把 `node` 接上去（`* on (namespace, pod) group_left(node) kube_pod_info`），用在 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 的〈依原因抑制：主機飽和時壓下各服務變慢〉那類抑制規則時，服務的序列以這個方式接上 `node`；兩者的差別在讀取時加的標籤每一條序列本身就帶著，查詢時接的則每一條規則都要寫一次。

原因那一側的 node-exporter 序列也要有 `node`。chart 92.3.0 的 node-exporter 預設沒有 relabelings，它的 `instance` 是節點的 IP 加連接埠，與 `kube_pod_info` 的節點名稱對不起來；在 chart 的值 `prometheus-node-exporter.prometheus.monitor.relabelings` 寫一條與上面相同的規則（`__meta_kubernetes_pod_node_name` 寫進 `node`），node-exporter 跑在每個節點上的那個 Pod 所在的節點就是它量的節點：

```yaml
prometheus-node-exporter:
  prometheus:
    monitor:
      relabelings:
        - sourceLabels: [__meta_kubernetes_pod_node_name]
          targetLabel: node
```

實測以這份值安裝之後，node-exporter 的 `up` 帶著 `node="<叢集名稱>-control-plane"`。chart 附的其他讀取設定裡，kubelet 預設就帶 `node`，API server、CoreDNS、kube-state-metrics、控制平面元件與監控元件自己的讀取對象都沒有；寫規則之前以 `count by (job) (up{node=""})` 查一次，列出來的 job 就是還沒有 `node` 的讀取對象。

## 儀表板經由 ConfigMap 與 sidecar 載入

ConfigMap 是存放設定資料的 Kubernetes 物件，Secret 是存放私密資料的同類物件，兩者都能掛進 Pod 或由程式經 Kubernetes API 讀取。chart 附的 Grafana 旁邊跑著一個 sidecar 容器（同一個 Pod 裡、負責輔助工作的另一個容器），它監看全叢集帶 `grafana_dashboard: "1"` 標籤的 ConfigMap 與 Secret，把裡面的 JSON 寫進 Grafana 讀取儀表板的目錄，再呼叫 Grafana 的重新載入 API。儀表板因此可以和服務放在同一個 namespace、跟著服務部署：

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

實測套用之後 23 秒，儀表板出現在 Grafana；刪掉 ConfigMap 之後 6 秒，儀表板從 Grafana 消失；這段延遲是 sidecar 察覺 ConfigMap 變更、寫檔、再讓 Grafana 重新載入的時間。從 ConfigMap 載入的儀表板是佈建（provisioned）的儀表板，chart 的佈建設定寫 `allowUiUpdates: false`：Grafana 的 API 對這個儀表板回 `canSave: true`，實際以 API 存檔時被拒，訊息是 `Cannot save provisioned dashboard`。所以在介面上調好的儀表板要匯出 JSON、改回 ConfigMap，這和 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 的〈Grafana：以檔案佈建資料來源與儀表板〉以檔案佈建儀表板的流程相同，只是檔案換成 ConfigMap。

資料來源也是同一個機制，標籤換成 `grafana_datasource: "1"`。

開 Grafana 看儀表板時，以 `kubectl -n monitoring port-forward svc/<release 名稱>-grafana 3000:80` 把它轉到本機的 3000（chart 附的 Grafana 的 Service 連接埠是 80）；admin 的帳號與密碼在 chart 建立的同名 Secret 裡（鍵是 `admin-user` 與 `admin-password`），以 `kubectl -n monitoring get secret <release 名稱>-grafana -o jsonpath='{.data.admin-password}' | base64 -d` 讀出。實測 release 名稱是 `kps` 時，Service 與 Secret 分別是 `kps-grafana`，以這組帳號密碼經由轉出來的 3000 登入成功；release 名稱不同時以 `kubectl -n monitoring get svc,secret` 查。要讓沒有叢集權限的人看儀表板，選擇條件與認證的位置見 [Grafana 的對外存取](/backend/04-observability/vendors/prometheus/grafana-external-access/)；那一篇的代理在 Kubernetes 上換成叢集的 Ingress，這裡沒有涵蓋。

手上是從 Grafana 匯出的 JSON 檔時，以 `kubectl -n shop create configmap shop-dashboard --from-file=shop.json` 建 ConfigMap，再 `kubectl -n shop label configmap shop-dashboard grafana_dashboard=1` 加上標籤（`shop` 與檔名換成自己的）；實測加上標籤之後約 4 秒，儀表板出現在 Grafana。

儀表板的 JSON 改寫成 YAML 檔、以 `kubectl apply` 更新時，JSON 很大就要加 `--server-side`。預設的 client-side apply 把整份物件另存一份在 `kubectl.kubernetes.io/last-applied-configuration` 這個 annotation 裡，而 Kubernetes 限制一個物件的 annotation 合計不超過 262144 位元組。實測一份約 300 KB 的 ConfigMap 以 `kubectl apply` 套用被拒，訊息是 `metadata.annotations: Too long: may not be more than 262144 bytes`；同一份加上 `--server-side` 套用成功。`kubectl create` 不寫這個 annotation，所以第一次以 `create` 建立不受這個限制。

## chart 預設的 Alertmanager 路由：不送任何通知

Alertmanager 的路由與 receiver 寫在 chart 的 `alertmanager.config` 值裡。chart 預設的設定把所有告警送到一個不通知的 `null` receiver，Watchdog 也另有一條子路由送到 `null`，所以裝好之後沒有任何通知送出。

要接通知時改寫這個值。子路由與 receiver 的寫法和 Compose 上相同，見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)，有三處要依 chart 的預設調整：

- **Watchdog 那條子路由**：chart 預設只寫了 matchers 與 receiver，時間參數沿用上層的 `group_wait: 30s`、`group_interval: 5m`、`repeat_interval: 12h`。只把 receiver 換成心跳監看服務（監控以外、接收心跳並在心跳中斷時通知的外部服務，例如 healthchecks.io）時，心跳每 12 小時才送一次，心跳監看服務會一直判定告警鏈停了；要照那一篇〈Watchdog：告警鏈本身的心跳〉的設定一併寫上 `group_wait: 0s`、`group_interval: 1m`、`repeat_interval: 5m`；實測照這組參數，心跳的間隔是 5 分 54 秒與 6 分 02 秒，接近 `repeat_interval` 加一個 `group_interval` 的 6 分鐘，遠小於週期加寬限的 10 分鐘。Watchdog 規則 chart 已經有，不必另加。
- **分組與範本裡的 `host`**：Compose 的設定依 `host` 分組，ntfy 與 Slack 的標題也讀 `host`，而 Kubernetes 上的序列沒有這個標籤，分組只剩依 `alertname` 一個標籤，標題顯示 `<no value>`。改用 `node`，或 chart 預設分組用的 `namespace`。
- **`severity` 是 `info` 與 `none` 的告警**：chart 的預設規則有這兩級（info 例如 `CPUThrottlingHigh`，none 例如 `InfoInhibitor`），Compose 的路由會把沒有子路由接走的都送到最上層的 receiver，它們因此推到手機。替這兩級另開一條送到 `null` 的子路由，排在 Watchdog 那一條之後，否則同樣是 `none` 的 Watchdog 會先被它接走。

`routes` 與 `receivers` 在 Helm 的值裡是清單，自己寫的清單整份取代 chart 的預設，所以 `null` receiver 與送到它的子路由要一起寫進去；`inhibit_rules` 同理，自己寫了抑制規則，chart 預設的抑制規則就不在了，而沒寫的鍵（例如上層的 `group_by`、`group_wait`）沿用 chart 的值。通知送失敗的告警 chart 也附了，不必另寫規則：`AlertmanagerFailedToSendAlerts`（warning）在 15 分鐘內失敗的比例超過 1% 並持續 5 分鐘時成立，同時成立的還有 critical 的 `AlertmanagerClusterFailedToSendAlerts`，條件相同而以整個 Alertmanager 叢集計算，只跑一份 Alertmanager 時兩條一起成立。它們同樣要另走一條不經過同一個通知服務的路，照〈通知送不出去的偵測〉開子路由時，`matchers` 換成 `alertname=~"Alertmanager(Cluster)?FailedToSendAlerts"`，兩條一起接走；只寫前一條的名稱時，critical 的那一條落到 critical 的子路由，走的正是送不出去的那條管道。

私密的網址以 Secret 交給 Alertmanager：在 `alertmanager.alertmanagerSpec.secrets` 列出 Secret 的名稱，Operator 把它掛在 Alertmanager 的 `/etc/alertmanager/secrets/<Secret 名稱>/` 底下，`url_file` 指到那裡。

實測在 kind 上以叢集裡一個記錄請求的 HTTP 服務當作通知的接收端，照上面三處調整寫了 `alertmanager.config`，以 `alertmanager.alertmanagerSpec.secrets` 交進四個網址檔。Operator 產生的設定裡，沒寫的 `group_wait`、`group_interval`、`repeat_interval` 與 chart 預設的 `inhibit_rules` 都在；一組永遠成立的合成規則套用之後約 70 秒，critical 與 warning 各收到一則，severity 是 `info` 的那一則沒有送出。把 critical 的網址檔改成連不上的位址之後，下一則 critical 告警在三次重試後失敗，失敗之後約 5 分 30 秒，兩條送失敗的告警成立：`AlertmanagerFailedToSendAlerts` 經由它自己的子路由送達，`AlertmanagerClusterFailedToSendAlerts` 在只寫前一條名稱時落到 critical 的子路由。

## 控制平面元件的 metrics 綁定位址與讀取失敗

裝好之後，Prometheus 的讀取對象裡有四個一直讀不到：controller-manager（連接埠 10257）、scheduler（10259）、etcd 的 metrics（2381）與 kube-proxy（10249），錯誤是 `connection refused`。到 kind 的節點容器裡看，這四個程式都只聽 `127.0.0.1`：

```sh
docker exec <叢集名稱>-control-plane ss -ltn   # kind 的節點是一個容器，名稱是叢集名稱加 -control-plane
# 127.0.0.1:2381  127.0.0.1:10257  127.0.0.1:10259  127.0.0.1:10249
```

kind 以 kubeadm 建立控制平面，kubeadm 預設把這幾個元件的 metrics 端點綁在本機；Prometheus 在 Pod 網路裡，連的是節點的 IP，所以連不上。預設的告警規則因此各自成立一條：`KubeControllerManagerInstanceUnreachable`、`KubeSchedulerInstanceUnreachable`、`KubeProxyInstanceUnreachable`、`TargetDown`，以及 critical 的 `etcdInsufficientMembers`。一裝好就有 critical 告警成立，而叢集本身是正常的。

以 kubeadm 新建的叢集（kind 也是）在建立時改這幾個綁定位址：

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

以這份設定重建之後，四個程式都改聽所有介面；從叢集裡的一個 Pod 連過去，etcd 與 kube-proxy 回 200，controller-manager 與 scheduler 回 403（連得上，要帶認證才讀得到）。chart 附的讀取設定替 controller-manager 與 scheduler 帶著 Prometheus 的 ServiceAccount 憑證去讀，所以在這個叢集上裝好監控之後，四個讀取對象的 `up` 都是 1；裝好 15 分鐘後，上面那幾條控制平面的告警與 `etcdInsufficientMembers` 都沒有成立。綁到所有介面也讓節點網路上的其他程式連得到這些端點，正式叢集要搭配網路政策或防火牆限制來源。

已經在跑、不能重建的 kubeadm 叢集，改的是控制平面節點上 `/etc/kubernetes/manifests/` 裡 kube-controller-manager、kube-scheduler 與 etcd 的靜態 Pod 檔（kubelet 偵測到檔案變更會自己重啟它們），以及 `kube-system` 裡 `kube-proxy` 這個 ConfigMap 的 `metricsBindAddress`，改完重啟 kube-proxy 的 DaemonSet。之後的 `kubeadm upgrade` 會以叢集的 ClusterConfiguration 重寫靜態 Pod 檔，所以同一組設定也要寫進 `kube-system` 的 `kubeadm-config` ConfigMap。這一段沒有實測。k3s 與 k3d 不經過 kubeadm，控制平面元件合在同一個程序裡，綁定位址以 k3s 的啟動參數設定，這裡沒有涵蓋。

託管的 Kubernetes（EKS、GKE、AKS）由雲端供應商管理控制平面，controller-manager、scheduler 與 etcd 多半不讓使用者直接讀，chart 的對應讀取設定只會一直失敗；這時在 chart 的值裡把 `kubeControllerManager.enabled`、`kubeScheduler.enabled`、`kubeEtcd.enabled` 設成 `false`，控制平面的狀態改看供應商提供的指標。kube-proxy 跑在使用者自己的節點上，託管叢集也一樣，它是否只綁本機依供應商的設定而定；它的讀取對象仍然失敗時，查該供應商 kube-proxy 設定的 `metricsBindAddress`，改不了就把 `kubeProxy.enabled` 設成 `false`。

## 單節點叢集上的資源用量與記憶體不足時的表現

裝好之後量這一組在叢集裡的記憶體（`container_memory_working_set_bytes`，依 Pod 加總）：Grafana 421 MB、Prometheus 355 MB、Alertmanager 58 MB、Operator 40 MB、kube-state-metrics 23 MB、node-exporter 19 MB，合計約 916 MB；kind 的節點容器整個約 2 GB。Prometheus 的活躍序列是 57,572 條，叢集裡只有一個節點、一個範例服務，這些幾乎全部來自 kubelet、API server 與預設的規則所需的指標，是 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 那一整組（約九千條）的六倍多。這些數字只代表這個單節點叢集，自己的叢集以同一個查詢量出自己的數字。

單機上的叢集與主機上其他的程式共用記憶體，記憶體不足時的表現不像記憶體問題。主機開始大量換頁之後，etcd 的寫入逾時，API server、controller-manager 與 scheduler 反覆重啟；依賴 API server 的 Operator 與 kube-state-metrics 連不上它而進入 CrashLoopBackOff（容器反覆啟動失敗、重啟間隔逐次拉長的狀態）；存活探針逾時又讓 kubelet 重啟更多容器，增加負載；預設規則 `KubeAPIErrorBudgetBurn` 以 critical 成立。這一串故障看起來各自獨立，共同的原因在主機。實測在一台 16 GB 的 Mac 上，同時跑著另一組 Docker 服務時，第一次安裝就以 `etcdserver: request timed out` 失敗，接著出現上面每一種故障；當時主機的 swap 用到 13 GB，系統負載（[load average](/backend/knowledge-cards/load-average/)）到 90，而 CPU 使用率並不高。

所以在單節點叢集上看到 etcd 逾時或控制平面反覆重啟時，先在主機上看記憶體與 swap（macOS 是 `sysctl vm.swapusage` 與 `vm_stat`，Linux 是 `free` 與 `vmstat`），排除主機的記憶體不足再查叢集。主機的記憶體不足時，停掉主機上其他吃記憶體的程式，再重新啟動 kind 的節點容器，叢集會自己恢復；實測半小時內所有 Pod 回到 Ready。

## 延伸閱讀：Compose 上的對應做法、Relabeling、Alertmanager 的通知與單機練習叢集

- 讀取對象、規則與儀表板以檔案管理時的寫法，見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/)；目標清單跟著部署走、主機標籤與主機消失的偵測，見 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/)。
- `relabelings` 在什麼時間點執行、讀得到哪些標籤、為什麼來源標籤不存在時目標標籤會整個消失，見 [Relabeling](/backend/knowledge-cards/relabeling/)。
- chart 附的 `Watchdog` 要接到外部的心跳監看服務才有作用，Alertmanager 的路由與通知見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)，接心跳監看服務的設定在〈Watchdog：告警鏈本身的心跳〉，心跳監看服務的挑選、`/fail` 與送失敗通知的路由見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/)。叢集裡的監控與叢集共用失效域，需要叢集以外的觀察者，理由見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)。
- kind、k3d 與 minikube 各自怎麼模擬節點、閒置時用多少資源，見 [單機練習用的 Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/local-practice-clusters/)。
