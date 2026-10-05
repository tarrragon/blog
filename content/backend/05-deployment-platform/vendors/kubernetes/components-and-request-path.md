---
title: "Kubernetes 的元件與請求路徑：控制平面、節點、Pod、Deployment、Service 與 Ingress"
date: 2026-10-05
description: "從 Docker Compose 的使用經驗出發，說明 Kubernetes 用期望狀態與控制迴圈管理容器的方式、控制平面與節點上各元件的責任、Deployment、ReplicaSet 與 Pod 三層工作負載、一個外部 HTTP 請求經過 Ingress 與 Service 抵達 Pod 的路徑和每一段出問題時的訊號，以及節點故障後的重建時間與這套模型在什麼規模下划算"
weight: 2
tags: ["backend", "deployment", "kubernetes", "deep-article"]
---

這篇從已經會用 Docker Compose 的角度，整理 Kubernetes 由哪些元件組成、送出一份設定檔之後由誰做了什麼，以及一個外部 HTTP 請求怎麼從 Ingress 走到容器。範圍是單一叢集裡的無狀態服務，資料庫這類有狀態服務、持久儲存與存取權限不在本篇範圍。文中的輸出取自兩個本機叢集：kind 建立的 Kubernetes v1.37 叢集，以及 k3d 建立的 k3s v1.35 叢集（Ingress 與請求路徑的實驗）；在本機起叢集的方法見 [單機練習用的 Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/local-practice-clusters/)。

## Compose 與 Kubernetes 管理容器的方式

[Docker Compose](/backend/05-deployment-platform/vendors/docker/docker-compose/) 讀一份宣告式的 `docker-compose.yml`，在 `docker compose up` 執行的當下比對檔案與目前的容器，把缺的建起來、變了的重建。指令結束之後，Compose 就不再比對容器的數量與設定：容器的行程結束時，由 Docker daemon 依 `restart` 設定在同一台機器上重啟同一個容器；被刪掉的容器不會被補回來，healthcheck 失敗也不觸發重啟。整台機器停機時，沒有任何元件會把那些容器搬到別台機器上。

Kubernetes 管理的對象是一組機器組成的**叢集**（cluster），每台機器叫一個**節點**（node）。使用者送進叢集的同樣是**期望狀態**：例如「`web` 這個服務要有三個副本、用這個 image、每個副本最多用 0.2 個 CPU」。差別在 Kubernetes 把這份期望狀態存起來之後，由一組持續運作的程式反覆比對「現在實際有什麼」與「期望有什麼」，發現不一致就動手修正：副本少了就補，節點停機了就把副本排到別的節點上。

兩者跑容器的方式相同：同一個 image、同一種 container runtime（實際拉 image、建立容器的程式，例如 containerd）。差別在比對發生的時機：Compose 只在下指令時比對一次，Kubernetes 一直在比對。這個「持續比對、發現落差就修正」的程式結構，叫做**控制迴圈**（[Control Loop](/backend/knowledge-cards/control-loop/)）。Docker 自己的 Swarm 模式也讀 compose 格式的檔案、持續維持副本數，是 Docker 生態裡另一個做持續比對的引擎。

## 期望狀態與控制迴圈

Kubernetes 裡的每一種管理對象（服務的副本數、網路入口、設定值）都是一個**物件**（object），用 YAML 描述。一個物件有兩個部分：`spec` 是期望狀態，由使用者寫；`status` 是實際狀態，由 Kubernetes 的元件回報。`kubectl apply -f web.yaml` 做的事只有一件：把檔案裡的物件送到 API server（控制平面的讀寫入口，〈控制平面與節點上的元件〉表裡的 kube-apiserver）存起來。它不建立任何容器，建立容器是後續各個控制迴圈的工作。

一個三副本的 `web` 服務（它的 Deployment 內容見〈工作負載的三層：Deployment、ReplicaSet 與 Pod〉一節）跑起來之後，手動刪掉其中一個 Pod（Pod 是容器的執行單位，同一節說明），控制迴圈的反應會留在事件紀錄裡：

```bash
# 刪掉一個 Pod，不等它結束就回到 shell；Pod 名稱換成 kubectl get pods 列出的其中一個
kubectl delete pod web-8649b5b67b-p6f7v --wait=false
# 列出 ReplicaSet 產生的事件，依最後發生時間排序，只看最後三筆
kubectl get events --field-selector involvedObject.kind=ReplicaSet --sort-by=.lastTimestamp | tail -3
```

```text
42s   Normal   SuccessfulCreate   replicaset/web-8649b5b67b   Created pod: web-8649b5b67b-xggll
42s   Normal   SuccessfulCreate   replicaset/web-8649b5b67b   Created pod: web-8649b5b67b-k6h6m
4s    Normal   SuccessfulCreate   replicaset/web-8649b5b67b   Created pod: web-8649b5b67b-2s8h8
```

第一欄是事件發生到現在經過的時間。前兩行是服務剛建立時的紀錄，最後一行是刪除之後產生的：ReplicaSet controller（維持 Pod 數量的控制迴圈）看到期望三個、實際剩兩個，於是建立 `web-8649b5b67b-2s8h8`。沒有任何人下「重新建立」的指令。

這個模型帶來一個讀輸出時的性質：**`kubectl apply` 回報成功，只代表期望狀態存進去了**。image 拉不到、資源不夠排不上節點，都發生在 apply 之後，要從物件的 `status` 與事件去看。

## 控制平面與節點上的元件

叢集裡的程式分成兩群。**控制平面**（control plane）負責保存期望狀態與做決策，**節點**負責實際跑容器。kind（用 Docker 容器扮演節點的本機叢集工具）建立的單節點叢集裡，兩群都住在同一個節點上。系統元件放在名為 `kube-system` 的 namespace 裡——namespace 是叢集裡劃分物件名稱的範圍，同一個 namespace 裡名稱不能重複，沒指定時用的是 `default`，見 [Namespace](/backend/knowledge-cards/namespace/)。用 `-n` 指定 namespace 列出系統元件：

```bash
# 列出 kube-system 這個 namespace 裡的 Pod
kubectl get pods -n kube-system
```

```text
NAME                                        STATUS
coredns-559f6c778d-bmnv7                    Running
coredns-559f6c778d-fczld                    Running
etcd-lab-control-plane                      Running
kindnet-qnvwg                               Running
kube-apiserver-lab-control-plane            Running
kube-controller-manager-lab-control-plane   Running
kube-proxy-q6gsp                            Running
kube-scheduler-lab-control-plane            Running
```

| 元件                                                    | 所在位置     | 責任                                                                                     |
| ------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------- |
| kube-apiserver                                          | 控制平面     | 叢集唯一的讀寫入口；`kubectl` 與其他元件都透過它讀寫物件                                 |
| etcd                                                    | 控制平面     | 保存全部物件的鍵值資料庫，期望狀態與實際狀態都存在這裡                                   |
| kube-scheduler                                          | 控制平面     | 替還沒有節點的 Pod 挑一個節點，依據是資源需求、節點剩餘資源與排程限制                    |
| kube-controller-manager                                 | 控制平面     | 執行各種內建的控制迴圈（ReplicaSet、Deployment、節點健康、EndpointSlice 等）             |
| kubelet                                                 | 每個節點     | 讀取排到本節點的 Pod，叫 container runtime 建立容器，執行健康檢查、重啟容器並回報狀態    |
| container runtime                                       | 每個節點     | 實際拉 image、跑容器（kind 的節點用 containerd）                                         |
| kube-proxy                                              | 每個節點     | 依 Service 的後端清單在節點上寫入封包轉送規則，讓送往 Service 虛擬 IP 的封包抵達後端 Pod |
| CoreDNS                                                 | 叢集內的 Pod | 叢集內的 DNS，把 Service 名稱解析成 Service 的 IP                                        |
| CNI（Container Network Interface）外掛，kind 用 kindnet | 每個節點     | 替每個 Pod 配 IP，讓不同節點上的 Pod 彼此連得到                                          |

表裡的 kubelet 與 container runtime 不在上面的 Pod 清單裡，因為它們直接跑在節點上，本身不是 Pod。清單會隨發行版不同：k3s（把控制平面元件併成單一行程的精簡發行版）的叢集在 `kube-system` 底下看不到 etcd 與 kube-apiserver 的 Pod；雲端託管的 Kubernetes（EKS、GKE、AKS）由雲端業者代管控制平面，使用者看不到 etcd、kube-apiserver、kube-scheduler、kube-controller-manager 的 Pod，CoreDNS、kube-proxy 與 CNI 仍以 Pod 出現在 `kube-system` 裡，屬於使用者要管理的附加元件。元件的責任分工在這些發行版之間相同。

這張表裡唯一保存狀態的是 etcd，其餘元件都可以重啟，重啟之後從 API server 讀回物件就能接續工作。所以控制平面要多副本時，etcd 的資料是最需要保護的那一份。

## 工作負載的三層：Deployment、ReplicaSet 與 Pod

**Pod** 是 Kubernetes 排程與執行的最小單位：一個 Pod 包含一個或多個容器，同一個 Pod 裡的容器共用網路（同一個 IP、可以用 `localhost` 互連），一定排在同一個節點上。Pod 裡的容器掛掉時，kubelet 依 Pod 的 `restartPolicy`（預設 `Always`）在原地重啟它；Pod 本身被刪除、被驅逐或所在節點故障時，替補的是一個新名字、新 IP 的 Pod，所以其他服務不能記住某個 Pod 的 IP。詳見 [Pod](/backend/knowledge-cards/pod/)。

直接建立的 Pod 沒有控制迴圈負責，它被刪除或節點故障之後不會有新的 Pod 補上。所以 Pod 一般由上層物件建立，上層物件靠**標籤**（label，附在物件上的 `key=value`）找到自己的 Pod：

- **ReplicaSet** 維持「帶某組標籤的 Pod 有 N 個」，少了就用它的 Pod 範本建立，多了就刪除。它只管數量：已經存在的 Pod 內容和範本不同，它不會去改。
- **Deployment** 管理 ReplicaSet。Pod 範本（例如 image）改變時，Deployment 建立一個新的 ReplicaSet，逐步調高新 ReplicaSet 的副本數、調低舊的，這就是 [Rolling Update](/backend/knowledge-cards/rolling-update/)。舊的 ReplicaSet 留著、副本數為零，回退時調回來就好。

一份可以實際部署的 Deployment：

```yaml
apiVersion: apps/v1 # 這種物件所屬的 API 版本，依 kind 填固定值
kind: Deployment
metadata:
  name: web # 這個 Deployment 的名稱，指令用它指名
spec:
  replicas: 3 # 期望的 Pod 數量
  selector:
    matchLabels:
      app: web # 這個 Deployment 管哪些 Pod：帶 app=web 標籤的
  template: # Pod 範本，改了這一段就會觸發滾動更新
    metadata:
      labels:
        app: web # 範本產生的 Pod 帶這個標籤，必須符合上面的 selector
    spec:
      containers:
        - name: whoami
          image: traefik/whoami:v1.11 # 示範用的小服務，回應自己的主機名稱
          ports:
            - containerPort: 80
          readinessProbe: # 判斷這個 Pod 能不能接流量
            httpGet:
              path: /health
              port: 80
            periodSeconds: 2 # 每 2 秒檢查一次
            failureThreshold: 1 # 失敗一次就標成未就緒
          resources:
            requests: # 排程時保留的量，scheduler 依此挑節點
              cpu: 50m # m 是千分之一個 CPU，50m = 0.05 個 CPU
              memory: 32Mi
            limits: # 執行時的上限，超過記憶體上限會被終止
              cpu: 200m
              memory: 64Mi
```

套用之後列出三層物件：

```bash
kubectl apply -f web.yaml
# 一次列出三種物件；-o wide 多印出 Pod 的 IP 與所在節點
kubectl get deployment,replicaset,pod -o wide
```

```text
NAME                  READY   UP-TO-DATE   AVAILABLE
deployment.apps/web   3/3     3            3

NAME                             DESIRED   CURRENT   READY
replicaset.apps/web-8649b5b67b   3         3         3

NAME                       READY   STATUS    IP
pod/web-8649b5b67b-k6h6m   1/1     Running   10.244.0.7
pod/web-8649b5b67b-p6f7v   1/1     Running   10.244.0.6
pod/web-8649b5b67b-xggll   1/1     Running   10.244.0.5
```

ReplicaSet 的名稱是 Deployment 名稱接上 Pod 範本的雜湊值（`8649b5b67b`），Pod 名稱再接上自己的亂數。改了 image 再看一次，會出現一個新雜湊值的 ReplicaSet，舊的那一個 `DESIRED` 變成 0。

Deployment 管哪些 Pod，由 `selector` 和範本的 `labels` 比對決定，Kubernetes 不靠名稱前綴辨認誰是誰的 Pod。Service 也用同一種標籤比對找 Pod。

## Service：一組 Pod 的固定入口

Pod 的 IP 會隨著重建而改變，數量也會隨擴縮而改變，所以呼叫它們的程式需要一個不變的位址。Kubernetes 的 **Service** 物件提供這個位址（下文的 Service 都指這個物件，一般語意照常寫「服務」）：它用標籤選出一組 Pod，給它們一個固定的虛擬 IP（ClusterIP）與 DNS 名稱。詳見 [Kubernetes Service](/backend/knowledge-cards/kubernetes-service/)。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web # DNS 名稱的來源：同一個 namespace 內用 web，跨 namespace 至少寫到 web.default（完整形式 web.default.svc.cluster.local）
spec:
  selector:
    app: web # 選出帶 app=web 標籤的 Pod
  ports:
    - port: 80 # Service 對外的埠
      targetPort: 80 # 轉到 Pod 的哪個埠
```

Deployment 與 Service 可以放在同一個檔案，兩段 YAML 之間用一行 `---` 分隔；少了分隔線，後一段的欄位會蓋掉前一段，只會建出其中一個物件。

Service 選出的 Pod 位址，由 EndpointSlice controller（kube-controller-manager 裡的一個控制迴圈）寫成 **EndpointSlice** 物件，每個位址附帶一個 `ready` 狀態。每個節點上的 kube-proxy 讀 EndpointSlice，在節點上寫入封包轉送規則，讓送往 ClusterIP 的封包改送到其中一個 ready 的 Pod。從叢集裡另一個 Pod 連 `web` 九次，看請求落在哪幾個 Pod：

```bash
# 起一個帶 curl 的 Pod 當用戶端
kubectl run curl --image=curlimages/curl:8.11.1 --restart=Never --command -- sleep 3600
# 在它裡面連 web 九次，統計每個 Pod 回應了幾次
kubectl exec curl -- sh -c 'for i in 1 2 3 4 5 6 7 8 9; do curl -s web/ | grep Hostname; done' | sort | uniq -c
```

```text
   3 Hostname: web-8649b5b67b-k6h6m
   2 Hostname: web-8649b5b67b-p6f7v
   4 Hostname: web-8649b5b67b-xggll
```

每行開頭的數字是那個 Pod 回應的次數，九個請求分散到三個 Pod。

### readiness 失敗的 Pod 在 EndpointSlice 裡的狀態與流量去向

示範用的 whoami 接受對 `/health` 送 POST 來指定它之後回應的狀態碼，可以用來讓一個 Pod 的健康檢查失敗：

```bash
# 讓指定 IP 的 Pod 之後的 /health 都回 500；IP 從 kubectl get pods -o wide 取
kubectl exec curl -- curl -s -X POST -d 500 http://10.244.0.7/health
# 列出 web 這個 Service 的每個後端位址與 ready 狀態
kubectl get endpointslices -l kubernetes.io/service-name=web \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]} ready={.conditions.ready}{"\n"}{end}'
```

readiness probe 每兩秒檢查一次、失敗一次就判定未就緒，所以兩秒內 kubelet 把那個 Pod 標成未就緒，EndpointSlice controller 把它的 `ready` 改成 `false`，之後的請求只到另外兩個 Pod：

```text
NAME                   READY   STATUS    RESTARTS
web-8649b5b67b-k6h6m   0/1     Running   0
web-8649b5b67b-p6f7v   1/1     Running   0
web-8649b5b67b-xggll   1/1     Running   0

10.244.0.6 ready=true
10.244.0.5 ready=true
10.244.0.7 ready=false
```

那個 Pod 的位址仍在 EndpointSlice 裡，只是標成未就緒；狀態仍是 `Running`、重啟次數是 0。readiness probe 的結果只決定**接不接流量**。重啟容器的是 kubelet，觸發條件之一是 liveness probe 失敗：liveness probe 檢查的是程式還活不活著（例如卡死、不再回應），失敗時 kubelet 重啟容器；三種 probe 的分工見 [Probe](/backend/knowledge-cards/probe/)、[Readiness](/backend/knowledge-cards/readiness/) 與 [Liveness](/backend/knowledge-cards/health-check-liveness/)。

## Ingress：叢集外的 HTTP 請求進入叢集的位置

ClusterIP 只在叢集內部連得到。讓叢集外的請求進來有幾種方式：

- Service 型別設成 **NodePort**：每個節點開一個 30000–32767 範圍內的埠，連到任一節點的這個埠就進到 Service。
- Service 型別設成 **LoadBalancer**：由雲端業者，或叢集裡的替代實作（例如 MetalLB、本機用的 cloud-provider-kind），建立一個外部負載平衡器，把流量導到節點。
- **Ingress**：用一個物件寫 HTTP 路由規則（哪個 Host、哪個路徑轉到哪個 Service），由叢集裡的一個反向代理統一接收外部流量再分派。

多個 HTTP 服務共用一個對外入口時，Ingress 只需要一個負載平衡器；每個服務各開一個 LoadBalancer 則要付多份成本。

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
spec:
  rules:
    - host: web.localhost # 只處理 Host 標頭是 web.localhost 的請求
      http:
        paths:
          - path: /
            pathType: Prefix # 以 / 開頭的路徑都符合
            backend:
              service:
                name: web # 轉到上面那個名為 web 的 Service
                port:
                  number: 80
```

Ingress 物件本身只是規則，實際接收流量、照規則轉發的是 **Ingress controller**：一個跑在叢集裡的反向代理，例如 Traefik、NGINX 系列（社群的 ingress-nginx，以及 F5 的 NGINX Ingress Controller）、Envoy 系列。它讀 Ingress 物件、產生自己的路由設定。叢集裡登記了哪些 controller，記在 **IngressClass** 物件裡，Ingress 用 `ingressClassName` 指定由哪一個處理。在 kind 叢集裡沒有任何 controller 時，Ingress 物件照樣建立成功，只是沒有程式處理它：

```text
NAME   CLASS    HOSTS           ADDRESS   PORTS
web    <none>   web.localhost             80
```

`ADDRESS` 是空的，`kubectl get ingressclass` 回 `No resources found`。換到內建 Traefik 的 k3s 叢集，同一份 Ingress 的 `CLASS` 是 `traefik`、`ADDRESS` 有值；Host 標頭是 `web.localhost` 的請求分散到三個 Pod，Host 標頭不符合規則的請求（例如 curl 直接連 `localhost:8080` 時送出的 `Host: localhost:8080`）由 Traefik 回 404。詳見 [Ingress](/backend/knowledge-cards/ingress/)。

社群維護的 ingress-nginx 已經結束維護，Ingress API 本身沒有被棄用，維護狀態的時間點與官方公告見 [Ingress](/backend/knowledge-cards/ingress/)。官方建議新的設計改用 **Gateway API**：它把 Ingress 的單一物件拆成 Gateway（入口本身，通常由平台團隊管理）與 HTTPRoute（路由規則，由各服務團隊管理）。Ingress 只能用 annotation（物件 metadata 裡的自由鍵值，由各 controller 自行解讀）表達的功能，例如依標頭分流、依權重分流，在 Gateway API 裡是標準欄位。所以選入口元件時，controller 有沒有支援 Gateway API 是一個比較項目。

## 一個請求的完整路徑與每一段的失敗訊號

把 Ingress、Service 與 Pod 串起來，一個從瀏覽器送出的請求依序經過：

1. **叢集外的入口**：本機叢集是一個對應到主機的埠，雲端是 LoadBalancer。請求抵達某個節點。
2. **Ingress controller 的 Pod**：依 Host 與路徑比對 Ingress 規則，查出目標 Service。
3. **Service 與 EndpointSlice**：controller 從 EndpointSlice 取得 ready 的 Pod 位址。Traefik 與 ingress-nginx 預設直接連 Pod 位址，不經過 ClusterIP。
4. **Pod**：容器處理請求並回應。

排查一個錯誤回應時，先分辨它是誰產生的。Ingress controller 自己產生的回應有固定的內容，例如 Traefik 的 503 本文是 `no available server`、502 本文是 `Bad Gateway`；Pod 裡的應用程式自己回的錯誤（例如過載時回 503），controller 會原樣轉給用戶端。應用程式自己回的錯誤代表路徑上的物件都正常，要去看應用程式的日誌。

由 controller 產生的錯誤，路徑上幾種不同的故障從外面看可能相同，要靠路徑上每一段對應的物件狀態分辨。下表「叢集裡沒有 Ingress controller」那一列在 kind 叢集上觀察，其餘各列在 k3s 叢集（Traefik）上實際做出來：

| 情形                                                          | 外部看到的回應                         | 分辨方式                                                                                                                   |
| ------------------------------------------------------------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 叢集裡沒有 Ingress controller                                 | 沒有程式依這份規則轉發，請求到不了服務 | `kubectl get ingress` 的 `ADDRESS` 是空的，`kubectl get ingressclass` 沒有資源                                             |
| 請求的 Host 不符合任何規則                                    | Traefik 回 404                         | 比對請求的 Host 標頭與 `kubectl get ingress` 的 `HOSTS` 欄                                                                 |
| Service 的 selector 打錯，選不到任何 Pod                      | Traefik 回 503 `no available server`   | `kubectl get endpointslices -l kubernetes.io/service-name=web` 的 `ENDPOINTS` 是空的                                       |
| Pod 都在，但全部 readiness 失敗                               | Traefik 回 503 `no available server`   | EndpointSlice 有位址，但每個都是 `ready=false`；`kubectl get pods` 的 READY 是 `0/1`                                       |
| Pod 都 ready，但 Service 的 `targetPort` 不是容器實際監聽的埠 | Traefik 回 502 `Bad Gateway`           | EndpointSlice 的位址都是 ready，而它的 `PORTS` 欄和應用程式實際監聽的埠不同（看應用程式的設定，或 readiness probe 打的埠） |
| 新版 image 拉不到                                             | 舊版 Pod 繼續服務，回應正常            | `kubectl get pods` 有一個 `ImagePullBackOff`（拉取失敗、等待後重試）的新 Pod，滾動更新停住不前進                           |

selector 打錯與全部未就緒從外面看都是 503，而兩者的處理方向不同：一個要改 Service，一個要查應用程式為什麼健康檢查失敗。EndpointSlice 是兩種情形分岔的位置：位址是空的代表 Service 選不到 Pod，有位址但都不 ready 代表 Pod 本身沒通過檢查。

image 拉不到的那一列沒有造成中斷，原因在 Deployment 滾動更新的兩個參數。`maxSurge` 是更新期間最多可以比期望數多開幾個 Pod，預設是期望數的 25%、向上取整；`maxUnavailable` 是更新期間最多容許幾個 Pod 不可用，預設也是 25%、向下取整。三副本時 `maxSurge` 是 1、`maxUnavailable` 是 0，所以 Deployment 先多開一個新 Pod，在它 ready 之前一個舊 Pod 都不縮減：

```bash
# 把 web 這個 Deployment 裡名為 whoami 的容器改用一個不存在的標籤
kubectl set image deployment/web whoami=traefik/whoami:no-such-tag
# 回到上一版的 Pod 範本
kubectl rollout undo deployment/web
```

`deployment/web` 是「物件種類/名稱」的寫法。改壞之後狀態停在「三個舊 Pod `Running`、一個新 Pod `ImagePullBackOff`」，`kubectl rollout status deployment/web` 會一直等到 Deployment 的進度期限（`progressDeadlineSeconds`，預設 600 秒）過了才回報失敗。

`rollout undo` 改的是叢集裡 Deployment 的期望狀態，不改本機的設定檔，也不改 `kubectl apply` 留在物件上的紀錄，所以執行時會印出一段提醒。這時叢集與設定檔各持有一份不同的期望狀態，下一次 `kubectl apply` 以設定檔為準，會把設定檔裡那一版重新送回 API server；設定檔裡若是壞的版本，壞版本就回來了。

本機 build 的 image 停在 `ImagePullBackOff` 是另一個成因，見 [單機練習用的 Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/local-practice-clusters/) 的〈主機與節點各自的 image 儲存〉；只在滾動更新期間零星出現的 502 與 504 見〈滾動更新期間的少量錯誤〉。

### 滾動更新期間的少量錯誤

在同一個 k3s 叢集持續送請求並做一次正常的滾動更新，約九十個請求裡出現一個 502 與一個 504。這個 Deployment 沒有設定任何終止前的延遲，而舊 Pod 在 EndpointSlice 裡被標成未就緒，與它收到終止訊號是同時開始、各自進行的，所以 Traefik 更新後端清單之前，有少數請求送到了正在關閉的 Pod。終止訊號是 kubelet 送給容器主程式的 SIGTERM，通知它準備結束；補上這段落差的設定（`preStop` 延遲、應用程式收到 SIGTERM 後繼續處理進行中的請求）見 [Kubernetes Graceful Shutdown](/backend/05-deployment-platform/vendors/kubernetes/graceful-shutdown/)。

## 節點故障的時間線：NotReady 與 Pod 重建

一個節點停止回應後，有兩個時間點要分開看。在 kind 建立的三節點叢集（一個控制平面、兩個 worker 節點，worker 是只跑工作負載的節點）停掉一個 worker：

- **停機後約一分鐘**，控制平面把節點標成 `NotReady`，同時把該節點上所有 Pod 在 EndpointSlice 裡標成 `ready=false`，流量不再送過去。在這之前，送到那些 Pod 的請求會失敗。
- **標成 NotReady 之後再約五分鐘**，那些 Pod 進入 `Terminating`，替補的 Pod 在其他節點上建立。這段等待的機制是 taint 與 toleration：控制平面在 NotReady 的節點加上 taint（節點上的標記，表示 Pod 不該留在這裡），帶這個 taint 的節點上的 Pod 會被驅逐；而 Pod 預設帶兩條 toleration（容忍某個 taint 的宣告），鍵名是 `node.kubernetes.io/not-ready` 與 `node.kubernetes.io/unreachable`，允許它在這種節點上再留 300 秒。用意是避免節點短暫斷線就把整批 Pod 搬走，見 [Taint 與 Toleration](/backend/knowledge-cards/taint-and-toleration/)。

從停機到 Pod 在別的節點上重建，合計約六分鐘。這段期間服務少了那個節點上的副本，所以副本數要留餘量，讓剩下的節點在 Pod 重建前容得下全部流量。標成 NotReady 之前那一分鐘的失敗請求，靠兩種設定縮小影響：用 Pod 範本的 `topologySpreadConstraints` 把副本分散到不同節點，讓一個節點停機只帶走其中幾個副本（排程器預設的分散是軟性的，各節點的副本數可以差到 3、排不下時照樣排，要確定副本落在不同節點就寫 `maxSkew: 1` 的條件）；在 Ingress controller 設定重試（例如 Traefik 的 retry middleware），讓連不上失聯 Pod 的請求重新經過負載平衡再送一次，多數情況會落到另一個 Pod。判定連不上要等連線逾時，所以這些請求的回應時間會被拉長。

## Kubernetes 這套模型的成本與適用規模

控制平面本身要資源：kind 建立的單節點叢集在還沒部署任何服務時，記憶體用量就在數百 MiB 的量級（實際數字隨版本與機器不同，用 `docker stats` 量自己的叢集），雲端託管的控制平面多半另有固定費用。學習與維運的成本更大：物件種類多、設定以 YAML 描述、出問題時要跨 Pod、ReplicaSet、EndpointSlice、Ingress 多種物件找原因。

這些成本換到的能力分成兩層。機器故障時把 Pod 搬到別台機器、把副本分散到不同機器、由排程器把新副本放到還有空間的機器上，這一層要在機器超過一台時才發揮作用。只有一台機器時，Kubernetes 仍多給三件事：滾動更新時等新 Pod ready 才收掉舊的、readiness 失敗時自動把那個 Pod 摘出流量，以及依負載增減副本（上限是這台機器的資源）；`docker compose up` 換版時會先停掉舊容器，Docker 的 restart 也不看 healthcheck，單機部署要求換版不中斷時，這兩件事要在 Compose 加反向代理的組合裡另外補。也有團隊因此在單機上直接跑單節點的 k3s，常見於門市、工廠這類邊緣環境。單機上服務的生命週期還可以交給 systemd 或 Docker 的 restart policy，三者的分工見 [Process supervisor 選型](/operations/04-service-health/process-supervisor-selection/)；Compose 的界線見 [Docker Compose 的〈容量：compose 到哪裡為止〉](/backend/05-deployment-platform/vendors/docker/docker-compose/#容量compose-到哪裡為止)。在雲端上要不要用 Kubernetes，還有不用 Kubernetes 的託管容器平台可選，取捨見 [運算平台上 IaC — ECS 與 EKS](/infra/05-core-services/compute-ecs-eks/)。自管兩三台機器而不想付 Kubernetes 的學習成本時，Docker Swarm 沿用 compose 檔、提供跨節點的副本維持與滾動更新，能力範圍比 Kubernetes 窄。

## 延伸閱讀：本機叢集、部署策略、發布批次與終止序列

- 要在自己的電腦上把本篇的例子跑一遍，以及哪些行為在單機上量不出來：[單機練習用的 Kubernetes：kind、k3d 與 minikube](/backend/05-deployment-platform/vendors/kubernetes/local-practice-clusters/)。
- 本篇的 Deployment 只用了 readiness probe 與預設的滾動更新，要加上 liveness 與 startup probe、決定批次節奏與 config 版本相容：[5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。
- 本篇的滾動更新只靠 readiness 決定要不要換下一批，不看錯誤率或延遲；要改成先放一小批流量給新版、看指標再決定放行或回退：[5.8 Deployment Rollout with Drain and Rollback](/backend/05-deployment-platform/deployment-rollout-drain-rollback/) 與 [Canary Release](/backend/knowledge-cards/canary-release/)。
- 本篇在滾動更新時量到的少量 502 與 504，要從 Pod 的終止序列處理：[Kubernetes Graceful Shutdown](/backend/05-deployment-platform/vendors/kubernetes/graceful-shutdown/)。
