---
title: "單機練習用的 Kubernetes：kind、k3d 與 minikube 的節點模擬方式、預設元件、主機連線與單機上量得到和量不到的行為"
date: 2026-10-05
description: "比較 kind、k3d、minikube 三種在一台電腦上起 Kubernetes 叢集的工具：節點怎麼用容器模擬、預設附了哪些元件以及缺少時在哪裡現形、主機的 image 與網路怎麼接進叢集，以及節點共用同一台電腦這件事讓哪些 Kubernetes 行為量得到、哪些量不到，最後是三者的閒置開銷與適合練習的對象"
weight: 3
tags: ["backend", "deployment", "kubernetes", "kind", "k3d", "minikube", "deep-article"]
---

這篇比較三個在一台電腦上起 Kubernetes 叢集的工具 kind、k3d 與 minikube：它們怎麼用容器模擬節點、預設附了哪些元件、主機怎麼連進叢集，以及節點共用同一台電腦這件事讓哪些 Kubernetes 行為量不到。本篇直接使用 Kubernetes 的元件與物件名詞：節點上的 kubelet 與 container runtime、控制平面、[Pod](/backend/knowledge-cards/pod/)、ReplicaSet、Deployment、[Service](/backend/knowledge-cards/kubernetes-service/)（含 LoadBalancer 型別）、EndpointSlice、[Ingress](/backend/knowledge-cards/ingress/) 與 [readiness probe](/backend/knowledge-cards/readiness/)，以及描述這些物件的 YAML 檔（manifest），它們的責任與彼此的關係在 [Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/) 說明。文中的輸出取自 macOS（Apple Silicon）上的 kind 0.33（Kubernetes v1.37）、k3d 5.9（k3s v1.35）與 minikube 1.39（Kubernetes v1.37）。

## kind、k3d 與 minikube 把叢集放在哪裡

三個工具的共同做法是**用容器扮演節點**：每個 Kubernetes 節點是一個 Docker 容器，容器裡再跑 kubelet 與 container runtime，Pod 的容器在節點容器裡面再建一層。所以一台電腦上可以有多個節點，而它們都由同一個 Docker daemon 建立，共用這台電腦的 CPU 與記憶體。三個工具的差別在節點容器裡跑的是哪一種 Kubernetes、預設附了哪些元件：

| 項目                         | kind                                                            | k3d                                             | minikube（Docker driver）                  |
| ---------------------------- | --------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------ |
| 節點裡的 Kubernetes          | 上游版（Kubernetes 專案發行的原版），控制平面元件各自是一個 Pod | k3s（精簡發行版），控制平面元件併在同一個行程裡 | 上游版                                     |
| 建立叢集時的容器             | 每個節點一個                                                    | 每個節點一個，加一個負責對應主機埠的代理容器    | 每個節點一個                               |
| 節點容器的資源上限           | 不設，節點看得到 Docker 能用的全部資源                          | 不設                                            | 設上限，用 `--cpus`、`--memory` 調整       |
| 預設附的 Ingress controller  | 沒有                                                            | Traefik                                         | 沒有，`ingress` addon 裝的是 ingress-nginx |
| 預設附的 metrics-server      | 沒有                                                            | 有                                              | 沒有，`metrics-server` addon 開啟          |
| 本機 build 的 image 送進叢集 | `kind load docker-image`                                        | `k3d image import`                              | `minikube image load`                      |
| 多節點                       | 設定檔列出各節點                                                | `--agents` 指定 worker 節點數，或寫在設定檔     | `--nodes` 指定節點數                       |

表裡幾個名詞先說明：**Traefik** 是一個反向代理，k3s 把它裝成叢集的 Ingress controller；**metrics-server** 是收集各 Pod CPU 與記憶體用量的元件，HorizontalPodAutoscaler 與 `kubectl top` 都讀它的資料；**addon** 是 minikube 可以一鍵安裝的附加元件；**worker 節點**是只跑工作負載、不跑控制平面元件的節點；minikube 的 **driver** 決定節點用什麼建出來，Docker driver 用容器，另有幾種 driver 用虛擬機。本篇只比較 Docker driver，讓三者的條件相同。Docker Desktop 與 OrbStack 這類 Docker 桌面程式也內建 Kubernetes，在程式的設定裡開關，適合只想要一個現成叢集、不需要調整元件的情形。

### 每個節點回報的容量

節點容器沒有資源上限時，每個節點都回報 Docker 能用的全部資源。在 kind 建立的三節點叢集（一個控制平面、兩個 worker）上列出每個節點的容量：

```bash
# 列出每個節點回報的 CPU 數與記憶體
kubectl get nodes -o custom-columns=NAME:.metadata.name,CPU:.status.capacity.cpu,MEM:.status.capacity.memory
```

三個節點回報的 CPU 數與記憶體完全相同，每一個都等於這台電腦給 Docker 的總量。排程器把三個節點的容量加起來當成叢集的容量，得到的是實際資源的三倍，所以它最多會排進資源需求合計達實際資源三倍的 Pod，而這些 Pod 搶的是同一批 CPU。回報的數字隨各自機器的 Docker 設定不同，在自己的叢集上跑一次這條指令就知道。

### 主機與節點各自的 image 儲存

主機上的 Docker 與節點容器裡的 container runtime 各有自己的 image 儲存。在主機上 `docker build` 出 `lab/hello:dev` 之後直接部署，節點在自己的儲存裡找不到這個 image，於是去 Docker Hub 拉，而 Docker Hub 上沒有它，Pod 停在 `ImagePullBackOff`（拉取失敗、等待一段時間後重試的狀態）：

```text
Failed to pull image "lab/hello:dev": failed to resolve reference "docker.io/lab/hello:dev":
pull access denied, repository does not exist or may require authorization
```

三個工具各有一條指令把 image 從主機複製進節點的儲存，對應比較表裡「本機 build 的 image 送進叢集」那一列：

```bash
kind load docker-image lab/hello:dev --name lab   # --name 指定叢集名稱，複製到這個叢集的每個節點
k3d image import lab/hello:dev -c lab             # -c 指定叢集名稱
minikube image load lab/hello:dev -p lab          # -p 指定 profile，也就是 minikube 對叢集的稱呼
```

複製進去之後還有一個條件：Kubernetes 對 `latest` 標籤（以及沒寫標籤）的預設拉取策略是 `Always`，每次建立容器都向 registry 拉，不看節點上有沒有，所以 `lab/hello:latest` 複製進去之後仍然拉不到。明確的版本標籤（例如 `dev`）的預設策略是 `IfNotPresent`，節點上有就直接用；用 `latest` 時要在 Pod 範本裡把 `imagePullPolicy` 設成 `IfNotPresent`。

### 缺 Ingress controller 或 metrics-server 時的現形位置：Ingress 的 ADDRESS 與 HPA 的 TARGETS

比較表裡「預設附的 Ingress controller」與「預設附的 metrics-server」兩列，決定了同一份設定在三個工具上能不能動。缺元件時，物件照樣建立成功，只是沒有程式處理它，現形的位置在物件的狀態欄位。

在 kind 叢集套用 Ingress，`kubectl get ingress` 的 `CLASS` 是 `<none>`、`ADDRESS` 是空的，因為叢集裡沒有任何 Ingress controller。k3d 的同一份 Ingress 由 Traefik 處理、`ADDRESS` 有值；minikube 要先開啟 `ingress` addon。

在 kind 叢集建立 HorizontalPodAutoscaler（HPA，依指標自動調整副本數的物件），`TARGETS` 欄停在 `<unknown>`，副本數不會變：

```text
NAME   REFERENCE        TARGETS              MINPODS   MAXPODS   REPLICAS
web    Deployment/web   cpu: <unknown>/50%   2         6         3
```

`kubectl describe hpa web` 的事件寫著 `unable to fetch metrics from resource metrics API`：HPA 讀的 CPU 使用率來自 metrics-server，kind 沒有附這個元件，`kubectl top pods` 也回 `Metrics API not available`。k3d 預設附了 metrics-server，minikube 用 addon 開啟，kind 要另外安裝。HPA 另一個前提是 Pod 範本寫了 `resources.requests.cpu`，它的百分比是相對於這個請求量計算的。

minikube 的 `ingress` addon 安裝的是社群的 ingress-nginx controller，這個專案已經結束維護，維護狀態與替代方案見 [Ingress](/backend/knowledge-cards/ingress/)。在本機練習 Ingress 的寫法不受影響，正式環境的 controller 另外選擇。

## 主機連進叢集的方式：port-forward、k3d 的埠對應與 minikube tunnel

macOS 與 Windows 上的 Docker 把容器放在一台虛擬機裡，主機通常連不到節點容器的 IP；Linux 上的 Docker 直接跑在主機上，節點容器的 IP 從主機連得到。所以在 macOS 與 Windows 上，叢集裡的服務要靠某種通道或埠對應才連得進去，三個工具各自用不同的方式補上這一段。部分 Docker 桌面程式會把容器 IP 路由到主機，那時直接連節點 IP 也通，但這個行為隨 Docker 的實作而不同，換一台機器不一定成立。

### kubectl 與 context

三個工具建立叢集時，都在 kubeconfig（kubectl 讀的設定檔，預設在 `~/.kube/config`）裡新增一個 **context**，並把它設成目前使用的那一個。context 記錄「連哪個叢集、用哪個身分」，所以之後的 `kubectl` 指令都作用在剛建立的叢集上；同時有多個叢集時，`kubectl config get-contexts` 列出全部、`kubectl config use-context <名稱>` 切換。三個工具建出來的都是標準的 Kubernetes API，所以同一份 manifest 不用改就能套上去：

```bash
# web.yaml 是〈元件與請求路徑〉裡 web 的 Deployment 與 Service，web-ingress.yaml 是它的 Ingress
kubectl apply -f web.yaml -f web-ingress.yaml
```

kubectl 本身是獨立於叢集的用戶端：它連哪個叢集由 context 決定，它是哪個版本由 `PATH` 選中哪一份執行檔決定，兩件事彼此無關。Docker 桌面程式、Homebrew 與各工具可能各自裝了一份 kubectl，`which -a kubectl` 會列出不只一個，排在 `PATH` 前面的那一份才是實際執行的。`kubectl version` 同時印出 kubectl 本身（Client Version）與叢集（Server Version）的版本，Kubernetes 支援的兩者差距是前後一個 minor 版本。

### kind：kubectl 建立的通道

```bash
# 建立名為 lab 的單節點叢集；新增的 context 叫 kind-lab
kind create cluster --name lab
# 把主機的 8080 埠轉到叢集裡 web 這個 Service 的 80 埠；指令持續執行，Ctrl-C 結束
kubectl port-forward svc/web 8080:80
```

kind 沒有附 Ingress controller，也不替叢集建立對外的埠對應，所以最直接的連法是 `kubectl port-forward`：kubectl 經由 API server 建一條通道，主機的 8080 埠收到的連線從這條通道送進去。指定 `svc/web` 時，kubectl 從 Service 選出的 Pod 裡挑一個建立通道，所有連線都送到那一個 Pod，不經過 Service 的分派，也不經過 Ingress，適合確認單一服務能不能回應。kind 官方文件建議要練 Ingress 時另外執行 [cloud-provider-kind](https://github.com/kubernetes-sigs/cloud-provider-kind)：它在主機上替叢集提供 LoadBalancer 型別的 Service，從 0.9.0 版起直接支援 Ingress 與 Gateway API；在 macOS 與 WSL2 上要用 `sudo` 執行，因為它要在主機上建立網路對應。

kind 的多節點叢集寫在設定檔裡，〈單機上量得到與量不到的行為〉裡的節點故障實驗用的就是這種叢集：

```yaml
# kind-multi.yaml，用 kind create cluster --name multi --config kind-multi.yaml 建立
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker # 每一列是一個節點容器，要幾個 worker 就列幾列
  - role: worker
```

節點容器的名稱是「叢集名稱-角色」，例如 `multi-control-plane`、`multi-worker`、`multi-worker2`。

### k3d：代理容器對應的主機埠

```bash
# 建立名為 lab 的叢集，並把主機的 8080 埠對應到叢集入口的 80 埠
k3d cluster create lab -p "8080:80@loadbalancer"
```

k3d 除了節點容器，還多建一個代理容器。`-p` 的格式是「主機埠:容器埠@要對應的容器」，`@loadbalancer` 指的就是這個代理容器：Docker 把主機的 8080 埠接到它，它再把流量轉給叢集裡的 Traefik。所以主機直接連 `localhost:8080` 就進到 Ingress，請求的 Host 標頭決定符合哪一條規則：

```bash
# Host 標頭是 web.localhost，符合 Ingress 規則，轉到 web 的 Pod
curl -H 'Host: web.localhost' http://localhost:8080/
# curl 預設送出 Host: localhost:8080，不符合任何規則，Traefik 回 404
curl http://localhost:8080/
```

8080 是示範用的主機埠，主機上已經被別的程式佔用時，換一個沒在用的埠。

### minikube：tunnel 補上的路由

```bash
# 用 Docker driver 建立名為 lab 的叢集；profile 名稱也是 context 的名稱
minikube start --driver=docker --profile lab
# 讓 LoadBalancer 型別的 Service 與 Ingress 從主機的 127.0.0.1 連得到；持續執行
minikube tunnel -p lab
# 只連單一 Service 時，印出一個從主機可連的 127.0.0.1 網址；終端也要保持開著
minikube service web -p lab --url
```

minikube 的做法是在主機上執行一個持續運作的程式，補上主機到節點的路由。`minikube tunnel` 讓 LoadBalancer 型別的 Service 與 Ingress 從主機的 `127.0.0.1` 連得到，啟用 `ingress` addon 時 minikube 也會提示要跑它；`minikube service` 只開一條到單一 Service 的通道。兩者在 macOS 的 Docker driver 上都要讓終端保持開著。minikube 第一次啟動要下載節點 image 與一份預先打包的 Kubernetes 元件，耗時取決於網路，之後再建立叢集直接用快取。

## 單機上量得到與量不到的行為

單機叢集跑的是完整的 Kubernetes 元件，所以控制迴圈、排程、Service 的流量分派、probe 這些**機制**的行為與正式叢集相同。差別在節點不是獨立的機器：它們共用同一組 CPU、同一個作業系統核心、同一塊磁碟。判斷一個實驗在單機上有沒有意義，看那個實驗量的是機制，還是量容量與故障的獨立性。

**量得到的是機制**：

- **自我修復**：刪掉 Pod，ReplicaSet 在幾秒內補一個新的。
- **readiness 摘除**：讓一個 Pod 的健康檢查失敗，它在 EndpointSlice 裡被標成未就緒，請求不再送過去，Pod 也不會被重啟。
- **滾動更新與回退**：改 image 觀察新舊 ReplicaSet 交接；改成不存在的 image 標籤，觀察更新停住而舊版繼續服務，再用 `kubectl rollout undo` 回退。
- **Ingress 路由**：依 Host 與路徑分流到不同 Service，以及各種設定錯誤時 controller 回的狀態碼。
- **節點故障的時間線**：在 kind 的三節點叢集用 `docker stop multi-worker` 停掉一個 worker 節點容器，約一分鐘後節點變成 `NotReady`，它上面的 Pod 同時在 EndpointSlice 裡被標成未就緒；再約五分鐘，那些 Pod 才在另一個 worker 上重建。兩個時間點的機制見 [元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/) 的〈節點故障的時間線：NotReady 與 Pod 重建〉。觀察服務有沒有中斷時，請求要從 Ingress 入口（kind 要先自行安裝 controller）或叢集裡的用戶端 Pod 送，`kubectl port-forward` 只連一個 Pod，那個 Pod 剛好在被停的節點上時會量出假中斷；停的節點也要避開 Ingress controller 所在的那一個：controller 只有一個副本時（例如 k3d 預設的 Traefik），它所在的節點停了，整個入口都會斷。
- **HPA 的運作**：在 k3d 叢集上設定 HPA，再從另一個 Pod 用 16 個迴圈持續送請求，HPA 依 CPU 使用率把副本加上去，概念見 [Autoscaling](/backend/knowledge-cards/autoscaling/)：

  ```bash
  # CPU 使用率（相對於 requests.cpu）超過 50% 就加副本，副本數維持在 2 到 6 之間
  # 較舊版本的 kubectl 把 --cpu=50% 寫成 --cpu-percent=50
  kubectl autoscale deployment web --cpu=50% --min=2 --max=6
  # 起一個名為 load 的 Pod，在裡面開 16 個迴圈持續請求 web；它沒有設 CPU 上限，會用掉這台電腦大量的 CPU
  kubectl run load --image=busybox:1.37 --restart=Never -- \
    sh -c 'for j in $(seq 1 16); do (while true; do wget -q -O /dev/null http://web/; done) & done; wait'
  # 觀察使用率與副本數
  kubectl get hpa web
  ```

  一分鐘內 `TARGETS` 顯示 `cpu: 335%/50%`，副本從 3 個加到上限 6 個。

**量不到的是容量與獨立性**：

- **擴充帶來的吞吐量上限**：上面的 HPA 實驗證明了「負載上升時副本會被加上去」這個機制，量不到「加副本能讓服務多處理多少流量」。這個實驗裡每個 Pod 的 CPU limit 是 0.2 個 CPU，副本從 3 個加到 6 個，可用的 CPU 從 0.6 個變成 1.2 個，吞吐量確實會上升；但再往上加，總量最多就是這台電腦的 CPU，之後六個或十個 Pod 分的都是同一批 CPU。正式叢集加副本時，排程器會把新 Pod 放到別台還有空間的機器，必要時再加節點，總容量跟著機器數成長，這條路在單機上不存在。所以在單機叢集上壓測，量到的是這台電腦扣掉叢集元件開銷之後的上限。
- **節點故障的獨立性**：停掉一個節點容器只模擬了「kubelet 失聯」。真實的節點故障包含磁碟損壞、網路分區、整個可用區斷線，而單機的各個節點共用同一個作業系統核心與磁碟，主機出問題時全部一起受影響。
- **跨機器的網路延遲**：節點之間的網路是同一台電腦裡的虛擬網路，量不到跨機器、跨可用區的延遲實際的分布與抖動；在節點容器的網路介面上人工注入延遲，得到的是自己設定的值。

所以單機叢集適合學 Kubernetes 的操作模型、驗證 manifest 與 probe 設定、在 CI 裡跑需要 Kubernetes 的整合測試。壓測結果裡可以帶到別的環境的，是單一 Pod 在固定 CPU limit 下的吞吐量，前提是量的時候這台電腦的 CPU 沒有用滿，而且目標環境的 CPU 架構與單核效能和這台電腦相近（CPU limit 是每段時間可用的 CPU 時間，不是固定的算力，換了 CPU 型號要在目標環境重量一次）；叢集的總吞吐量帶不走。在同一台電腦上比較兩個版本或兩種實作時，一次只跑一個受測服務、兩者設相同的 requests 與 limits，負載產生器若也在這台電腦上，它用掉的 CPU 要寫進結果的說明裡，否則量到的差距可能來自資源分配，而不是受測的那一項。

## kind、k3d 與 minikube 的閒置開銷與適合練習的對象

在同一台電腦上量叢集剛建立、還沒部署服務時的記憶體，三者都在數百 MiB 到 1GiB 的量級：kind 與 k3d 的單節點相近（k3d 的數字已包含 Traefik 與 metrics-server），minikube 較高；多節點時，每個 worker 的開銷遠低於控制平面。實際數字隨版本與機器不同，用 `docker stats --no-stream` 在自己的機器上量。macOS 上叢集能用的總量是 Docker 虛擬機的記憶體設定，`docker stats` 量的是容器，不含虛擬機本身的開銷，記憶體小的電腦先確認這個上限夠不夠，不夠就調高；k3d 不練 Ingress 時，可以用 `k3d cluster create lite --k3s-arg "--disable=traefik@server:*"` 建立不含 Traefik 的叢集，閒置記憶體明顯較低。壓測時叢集元件與受測服務共用資源，這筆開銷要寫進結果的說明裡。

三個工具的機制相同，差別在預設元件與設定方式，選擇看要練習的對象：

- 要貼近上游 Kubernetes 的元件組成、在 CI 裡起叢集跑測試：kind。它原本是 Kubernetes 專案用來測試自身的工具；代價是 Ingress controller 與 metrics-server 要自己補。
- 要開箱就有 Ingress 與 HPA 可以練：k3d。k3s 換掉了部分上游元件，行為細節與上游有差異時，以要部署的正式環境為準。
- 要用 addon 一鍵開啟元件、需要 dashboard、或要用虛擬機當節點：minikube。
- 要練叢集本身的建置、升級與 etcd 備份：三個工具都替使用者做完了這一層，要改用多台虛擬機，以 kubeadm 或 k3s 自己建叢集。每台虛擬機有自己的作業系統核心，一個節點的核心或 kubelet 出問題不會波及其他節點，主機的硬體與磁碟仍然共用。

CI 裡跑需要 Ingress 的整合測試時，kind 與 k3d 兩條都成立，分岔在測試要驗的是誰的行為：要驗與正式環境同一個 Ingress controller 的行為（annotation、預設逾時、錯誤回應），用 kind，或用 k3d 加 `--disable=traefik@server:*` 之後裝那一個 controller；只驗 Ingress 規則與 Service 的串接，k3d 預設的 Traefik 就夠。

## 延伸閱讀：元件、部署策略、Compose 與正式環境的平台

- 本篇用到的 Pod、Service、EndpointSlice、Ingress 各自負責什麼，以及請求在它們之間的路徑：[Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/)。
- 在單機叢集上練的滾動更新與 probe，要決定批次節奏、加上 liveness 與 startup probe 的判斷：[5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。
- 單機上只需要把幾個容器串起來、不需要 Kubernetes 的控制迴圈時，Compose 的寫法與它的適用範圍：[Docker Compose：多 service dev 環境編排](/backend/05-deployment-platform/vendors/docker/docker-compose/)。
- 練習完要在雲端上選平台，託管 Kubernetes 與不用 Kubernetes 的託管容器服務怎麼取捨：[運算平台上 IaC — ECS 與 EKS](/infra/05-core-services/compute-ecs-eks/)。
