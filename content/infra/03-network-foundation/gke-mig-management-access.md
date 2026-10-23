---
title: "GCP 上由 MIG 與 GKE 管理的 VM 的管理存取：instance template、node pool、kubectl debug 與控制平面存取"
date: 2026-10-23
description: "VM 由 managed instance group 或 GKE node pool 管理時，管理通道的設定為什麼要寫在 instance template 與 node pool 而不是逐台修改、IAP 規則與 OS Login 在這兩種環境的設定位置、MIG 救援改用重建的取捨、GKE 節點用 kubectl debug 取代 SSH 的做法與 RBAC 及 Pod Security 的權限邊界，以及 GKE 控制平面的存取（authorized networks、DNS-based endpoint 與 private endpoint）"
weight: 7
tags: ["infra", "network", "gcp", "gke", "kubernetes", "ssh", "iap"]
---

這篇處理 GCP 上兩種由 template 自動建立與重建 VM 的環境，其中 GKE 是 Google Kubernetes Engine，GCP 託管的 Kubernetes 服務：managed instance group（[MIG](/infra/knowledge-cards/managed-instance-group/)，依 instance template 自動建立、修復與縮放一組 VM）與 GKE 的 node pool（一組共用同一份設定的叢集節點，GKE 在底下用 MIG 管理它們）。範圍是在這兩種環境裡套用 [GCP VM 的 SSH 與 RDP 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/)的三項設定：[IAP](/infra/knowledge-cards/identity-aware-proxy/)（Identity-Aware Proxy，GCP 依 IAM 權限轉送 SSH 連線的代理）、[OS Login](/infra/knowledge-cards/os-login/)（讓 VM 的登入帳號與公鑰由 Google 帳號與 IAM 決定）與移除外部 IP；那一篇的指令以單台 VM 為對象，這一篇說明同樣的設定在這兩種環境要改寫在哪裡，以及 GKE 另外要管的 [控制平面（control plane）](/backend/knowledge-cards/control-plane/)存取。管理通道拆成網路可達性、通道授權與主機登入驗證三層的模型見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## autohealing、滾動更新與擴增後消失的逐台設定：network tag、OS Login metadata 與外部 IP

MIG 裡的每一台 VM 都由 instance template 建出來。有幾種時機 MIG 會刪掉一台 VM、再依 template 建一台新的：自動修復（autohealing，[健康檢查](/backend/knowledge-cards/health-check/)失敗時重建）、[滾動更新](/backend/knowledge-cards/rolling-update/)（rolling update，換成新版 template），以及 GKE 的節點升級與節點自動修復；[autoscaler](/backend/knowledge-cards/autoscaling/) 擴增台數時則直接依 template 新建。新建的 VM 只帶著 template 裡的設定，所以單台 VM 上做的修改——`gcloud compute instances add-tags` 加的 [network tag](/infra/knowledge-cards/network-tag/)（貼在 VM 上的標籤，防火牆規則用它選出要套用的 VM）、`add-metadata` 設的 `enable-oslogin`、登入之後 `useradd` 建的救援帳號、`delete-access-config` 移除的外部 IP——都只活到那台 VM 被重建為止，新加進來的 VM 則從一開始就沒有。

這種消失沒有任何通知。重建通常發生在半夜的自動修復或下一次擴增，而只放行 IAP 來源的防火牆規則靠 network tag 選 VM：新建的 VM 沒有那個 tag，這條規則就套不到它。收斂管理通道時通常也已經刪掉 `default-allow-ssh`（GCP 預設網路裡放行任何來源連 22 port 的規則），兩者加在一起，新 VM 上沒有任何一條規則放行 SSH，它就從管理通道上消失了。所以這兩種環境的做法是：**管理通道的設定寫在建立 VM 的那一份設定裡**（MIG 的 instance template、GKE 的 node pool 設定、或映像檔），逐台的 `gcloud compute instances` 指令只用在臨時查看。

要判斷一台 VM 屬不屬於 MIG，看它的 metadata（掛在 VM 上的鍵值設定，VM 內的程式與有讀取權限的帳號都讀得到）有沒有 `created-by` 這個鍵（值是那個 MIG 的資源路徑）；GKE 節點帶著 `goog-gke-node` 標籤。下面的指令用 `jq`（命令列的 JSON 處理工具）從 `gcloud` 的 JSON 輸出取出這個鍵，要先在本機裝好；`gcloud` 讀的是目前設定的專案，要查別的專案時加 `--project=<project-id>`：

```bash
# 列出 VM 與它所屬的 MIG（第二欄是 - 的就是單獨建立的 VM）
gcloud compute instances list --format=json \
  | jq -r '.[] | [.name, (first((.metadata.items // [])[] | select(.key=="created-by") | .value) // "-")] | @tsv'
```

GKE 的節點同樣是 MIG 的成員，這條指令會把它們列成屬於某個名稱是 `gke-...-grp` 的 MIG。這類 MIG 由 GKE 管理：對它們執行下面 MIG 兩節的 `instance-templates create`、`rolling-action` 或 `recreate-instances`，改動會被 GKE 覆蓋或讓叢集狀態不一致，`recreate-instances` 也不會先把節點上的 Pod 移走。帶著 `goog-gke-node` 標籤的 VM 改走本篇 GKE 的幾節：設定改在 node pool，單一節點壞掉時用 `kubectl drain` 移走 Pod，再交給 GKE 的節點自動修復。

## MIG：把 tag、OS Login 與外部 IP 寫進 instance template

MIG 與 GKE 多半由 Terraform 這類 [IaC](/infra/knowledge-cards/iac/)（Infrastructure as Code，用程式碼描述雲端資源、由工具套用）工具管理。先確認這組 MIG 與叢集是不是由 IaC 建的（程式碼庫裡有沒有對應的資源定義）：是的話，本節與後面 node pool 的修改都改在程式碼裡，CLI 上只執行 `describe` 這類讀取用的指令——在 CLI 上建的 template、改的 node pool 設定，下一次 apply 會依程式碼改回去，這種程式碼與實際狀態的落差叫 [drift](/infra/knowledge-cards/drift/)，過渡期的做法見[兩套真相並存的過渡期操作](/infra/takeover/partial-iac-dual-truth-operation/)。下面的 `gcloud` 指令在沒有 IaC 的環境照著執行；有 IaC 的環境把它們當成欄位對照，看程式碼裡要改哪幾個欄位。

instance template 建立之後不能修改，改設定的方式是建一份新的 template，再讓 MIG 滾動更新到新版。`instance-templates create` 從預設值開始建，不會沿用舊 template 的任何設定，所以先把現行 template 讀出來，逐項帶進新的那一份：

```bash
# 讀出現行 template 的完整設定，新 template 要逐項帶上
gcloud compute instance-templates describe <current-template-name> --format=yaml

# 建一份新的 instance template：現行設定照抄，再加上 IAP 用的 tag、啟用 OS Login、不配外部 IP
gcloud compute instance-templates create <new-template-name> \
  --machine-type=<machine-type> \
  --image-family=<image-family> --image-project=<image-project> \
  --boot-disk-size=<boot-disk-size> \
  --network=<network-name> --subnet=<subnet-name> --region=<region> \
  --service-account=<service-account-email> --scopes=<scopes> \
  --labels=<labels> \
  --tags=<ssh-via-iap-tag> \
  --metadata=enable-oslogin=TRUE \
  --metadata-from-file=startup-script=<startup-script-file> \
  --no-address
```

- `<current-template-name>`：MIG 目前用的 template，`gcloud compute instance-groups managed describe <mig-name> --zone=<zone>` 的 `instanceTemplate` 欄。
- `<new-template-name>`：新 template 的名稱，自己取；template 不能改名也不能改內容，常見的做法是名稱帶版本或日期。
- `--machine-type`、`--image-family`、`--image-project`、`--boot-disk-size`、`--network`、`--subnet`、`--region`、`--service-account`、`--scopes`、`--labels`、`--metadata-from-file=startup-script=`：照 `describe` 讀出來的值填，`describe` 裡還有其他欄位（額外的磁碟、GPU、其他 metadata 鍵）也要對應的旗標一起帶上。漏掉的欄位會回到預設值，常見的後果是 VM 換成預設的服務帳號而失去存取權限，或啟動腳本沒有執行。`--region` 是 `--subnet` 所在的 region。`describe` 的欄位與旗標不是一對一：映像在 `disks[].initializeParams.sourceImage`，多半是一個特定映像的完整路徑而不是 family，這時改用 `--image=<sourceImage 的值>` 取代 `--image-family` 與 `--image-project`；startup-script 在 `metadata.items` 裡 `key: startup-script` 的 `value`，先把它存成檔案再交給 `--metadata-from-file`；regional 的 template 讀取時 `describe` 要加 `--region=<region>`。
- `--tags=<ssh-via-iap-tag>`：與 [GCP VM 的 SSH 與 RDP 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/)〈啟用 IAP API、開啟稽核紀錄並建立只放行 IAP 來源的防火牆規則〉那條規則的 `--target-tags` 相同的 tag。新 template 只帶這裡列出的 tag，所以現行 template 已經有的其他 tag（`describe` 輸出的 `tags.items`，例如負載平衡器健康檢查用的）要一起列進來，逗號分隔。
- `--metadata=enable-oslogin=TRUE`：讓這個 template 建出的 VM 都啟用 OS Login；專案層級已經啟用時可以省略。
- `--no-address`：不配外部 IP。MIG 對外提供服務時，流量入口應該已經在負載平衡器上，VM 本身不需要外部 IP；這一點要先確認，`gcloud compute backend-services list --format="table(name, backends[].group)"` 的 `backends` 欄要有這個 MIG。服務若是靠 VM 的外部 IP 對外，canary 那一台只是收不到流量、不容易察覺，整組更新之後服務就斷了。出站改由 Cloud NAT 承接（見那一篇的〈拿掉外部 IP 之後的出站路徑：Cloud NAT 與 Private Google Access〉），所以 Cloud NAT 要在滾動更新之前建好。已經存在的 VM 在滾動更新把它換成新版時才失去外部 IP。

建好之後，先只讓一台 VM 換成新 template 驗證（這種先放一小部分出去試的做法叫 [canary](/backend/knowledge-cards/canary-release/)），再讓整組更新：

```bash
# 先讓一台 VM 用新 template（canary），其餘維持現行 template
gcloud compute instance-groups managed rolling-action start-update <mig-name> \
  --version=template=<current-template-name> \
  --canary-version=template=<new-template-name>,target-size=1 \
  --zone=<zone>

# 那一台驗證通過之後，讓整組換成新 template
gcloud compute instance-groups managed rolling-action start-update <mig-name> \
  --version=template=<new-template-name> --zone=<zone>
```

- `--version=template=`：canary 那一行放**現行**的 template，代表其餘 VM 維持原狀；整組更新那一行放新的 template。兩行的 `--version` 放的 template 相反。
- `--canary-version=template=<new-template-name>,target-size=1`：讓一台 VM 換成新 template；`target-size` 也可以寫百分比（`10%`）。
- `<mig-name>`、`--zone`：MIG 的名稱與所在 zone，`gcloud compute instance-groups managed list` 查得到；VM 分散在一個 region 的多個 zone 的 regional MIG，把 `--zone` 換成 `--region`。

`start-update` 送出之後 MIG 在背景替換 VM，指令本身不等它完成。用下面兩條確認替換做完、並找出 canary 那一台：

```bash
# 等到每台 VM 都換成指定的版本才返回
gcloud compute instance-groups managed wait-until <mig-name> --version-target-reached --zone=<zone>

# 列出 MIG 裡的 VM 與各自用的 template，INSTANCE_TEMPLATE 欄是新 template 的那一台就是 canary
gcloud compute instance-groups managed list-instances <mig-name> --zone=<zone>
```

找到 canary 那一台之後，經由 IAP 連進去，確認 OS Login 登得進去、出站經過 Cloud NAT（驗證方式同單台 VM 那一篇）。整組更新之後同樣用 `wait-until` 等它完成。整組更新時另外可以加 `--max-surge=1 --max-unavailable=0`：每一批先多建一台新的、再刪一台舊的，更新期間可用台數不減少，但這兩個旗標只控制每一批的速度，更新仍會把整組換完。regional MIG 的 `--max-surge` 用固定數字時不能小於 VM 分布的 zone 數（分布在三個 zone 就至少是 3）。

## MIG 的救援：recreate-instances、退回舊版 template 與 Serial Console

單台 VM 的救援入口是 Serial Console 加一個事先建好的本機救援帳號（[Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/)）。MIG 裡的 VM 多了一條更便宜的路：一台 VM 連不上、而原因是那台 VM 自己壞了（sshd 設定改壞、磁碟滿），刪掉它讓 MIG 依 template 重建，比從 Serial Console 進去修快，也不必替每台 VM 維護救援密碼：

```bash
# 依 template 重建一台 VM：MIG 會刪掉它，再依 MIG 目前的版本設定建一台新的
gcloud compute instance-groups managed recreate-instances <mig-name> \
  --instances=<instance-name> --zone=<zone>
```

`<instance-name>` 是要重建的那台 VM，`gcloud compute instance-groups managed list-instances <mig-name> --zone=<zone>` 列出 MIG 裡的 VM。重建的前提是 VM 上沒有只存在那一台的狀態：資料寫在外接的資料庫、物件儲存或另外掛載的磁碟上，VM 本身隨時可以丟。這也是 MIG 適合的工作負載本來就有的性質；VM 上有不能丟的狀態時有兩條路：MIG 的 stateful 設定（stateful policy 或 per-instance config）把指定的磁碟、IP 與 metadata 標為要保留，`recreate-instances` 重建時會沿用它們；狀態多到每台都不一樣時，它更適合當單獨的 VM 管理，而不是放進 MIG。

canary 期間重建的 VM 用哪一版，由 MIG 依兩個版本各自的 `target-size` 分配，不一定是原本那一版。

重建修不好的是 template 本身的錯：新版 template 的 tag 寫錯、啟動腳本有錯，重建出來的每一台都一樣壞。這種錯要退回上一版 template，所以舊版 template 留到新版驗證完之後再刪：

```bash
# 退回上一版 template：整組換回舊版
gcloud compute instance-groups managed rolling-action start-update <mig-name> \
  --version=template=<previous-template-name> --zone=<zone>
```

`<previous-template-name>` 是新版之前那一份 template 的名稱，`gcloud compute instance-templates list` 列得出來。需要登入一台壞掉的 VM 查原因時（例如要保留現場做事後分析），Serial Console 仍然可用；救援帳號的帳號與密碼雜湊要在建立[映像檔](/backend/knowledge-cards/immutable-image/)時寫進去（用 Packer 這類建映像檔的工具，或在一台 VM 上建好帳號再把磁碟做成自訂映像檔），而不是寫進 template 的 startup-script，因為 startup-script 存在 metadata 裡，任何有讀取 metadata 權限的人都看得到，把密碼寫在那裡等於公開。

## GKE 的存取面：控制平面與節點

GKE 叢集有兩個不同的存取面，設計時要分開處理：

- **控制平面**：Kubernetes 的 API server，`kubectl` 連的就是它。日常的部署、查 log、進 [Pod](/backend/knowledge-cards/pod/) 執行指令都經過它，這是 GKE 上的主要管理通道。
- **節點（node）**：跑工作負載的 VM。節點的作業系統要登入的情形很少：GKE 管理節點的映像檔、升級與修復，節點本身也是隨時可以丟的。

多數團隊在 GKE 上不需要節點的 SSH：查 Pod 的狀況用 `kubectl logs`、`kubectl exec`，查節點的狀況先看 Cloud Logging 裡的節點紀錄，需要看到節點作業系統時用 `kubectl debug node`，做法在本篇的〈GKE 節點的存取：kubectl debug、private nodes 與 node pool 的 tag〉一節。所以在 GKE 上收斂管理通道時，工作集中在控制平面的存取，節點的 SSH 盡量關掉。

GKE 有兩種叢集模式：Standard 由使用者管理 node pool 與節點設定；Autopilot 由 GKE 管理節點，使用者只管工作負載。下面節點那一節的大部分做法只適用於 Standard。

## GKE 節點的存取：kubectl debug、private nodes 與 node pool 的 tag

`kubectl debug node` 在指定的節點上建一個 Pod，把節點的根目錄掛在 Pod 的 `/host`，讓管理員經由 Kubernetes API 看到節點的作業系統，不需要節點開 SSH：

```bash
# 在指定節點上開一個除錯用的 Pod，節點的根目錄掛在 /host
kubectl debug node/<node-name> -it --image=ubuntu --profile=sysadmin --namespace=<namespace>

# 進到 Pod 之後，切換到節點的根目錄，像登入節點一樣查看
chroot /host
```

- `<node-name>`：節點名稱，`kubectl get nodes` 的第一欄。
- `--image=ubuntu`：除錯 Pod 用的映像檔，換成組織允許、帶著除錯工具的映像檔。
- `--profile=sysadmin`：讓除錯 Pod 以[特權容器（privileged container）](/backend/knowledge-cards/privileged-container/)執行，`chroot /host`（把行程的根目錄換成 `/host`，之後執行的指令看到的是節點的檔案系統）需要這個權限；不加時 Pod 起得來，但存取不了節點的大部分資源。
- `--namespace=<namespace>`：除錯 Pod 建在哪個 [namespace](/backend/knowledge-cards/namespace/)。不給時落在 kubeconfig 目前設定的 namespace（通常是 `default`）；要用哪一個、怎麼建，見下面權限邊界那一段。

這個 Pod 用完不會自動刪除，結束後用 `kubectl delete pod <debug-pod-name> --namespace=<namespace>` 刪掉（`kubectl get pods --namespace=<namespace>` 找名稱以 `node-debugger-` 開頭的那一個）。

`kubectl debug node` 的權限邊界有兩道。[Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/) 決定誰能用它：在除錯 Pod 所在的 namespace 要有 `pods` 的 `create`（建 Pod）、`get`（等 Pod 起來）、`delete`（用完刪掉），以及 `pods/attach` 的 `create`（`-it` 在 Pod 建好之後附加到它的終端機），這幾項綁在那個 namespace 的 RoleBinding；另外要有 `nodes` 的 `get`，節點不屬於任何 namespace，這一項要用 ClusterRoleBinding 授予。少了 `pods/attach` 時 Pod 建得出來卻進不去；能在節點上建特權 Pod 的帳號，實質上就能以 root 操作那個節點，所以這個權限只給負責維運的群組。[Pod Security Admission](/backend/knowledge-cards/pod-security-admission/) 決定那個 namespace 接不接受特權 Pod：namespace 設了 `pod-security.kubernetes.io/enforce=baseline` 或 `restricted` 時，除錯 Pod 會被拒絕。反過來，沒有設這個 label 的 namespace（包括 `default`）在 GKE Standard 上預設接受特權 Pod，所以任何能在 `default` 建 Pod 的帳號，現在就能用這個方法以 root 操作節點。做法是把一般工作負載的 namespace 都設成 `baseline` 以上，節點除錯集中到一個刻意保留為 `privileged` 等級、而且只有維運群組能建 Pod 的 namespace，這個 namespace 由叢集管理員事先建好：

```bash
# 建一個專門給節點除錯用的 namespace，並允許特權 Pod
kubectl create namespace <namespace>
kubectl label namespace <namespace> pod-security.kubernetes.io/enforce=privileged
```

`<namespace>` 自己取，例如 `node-debug`；建好之後只把它的 `pods` `create` 權限綁給維運群組。GKE Autopilot 預設拒絕特權 Pod（只有列入允許清單的合作夥伴工作負載例外），也不提供節點 SSH，查節點層的狀況靠 Cloud Logging 裡的節點紀錄與 GKE 主控台的節點狀態。

節點仍要 SSH 時（GKE Standard），把單台 VM 那一篇的做法搬到 node pool 的設定上：

- **節點不配外部 IP**：private nodes 指節點只有內部 IP 的設定。先確認節點所在 subnet 的 region 已經有 [Cloud NAT](/infra/knowledge-cards/nat/)：換成內部 IP 之後節點的出站都經過它，沒有它時節點拉不到外部 registry 的映像，工作負載起不來。新叢集在 `gcloud container clusters create` 加 `--enable-private-nodes`，作為整個叢集的預設；這個設定也可以逐個 node pool 設，既有叢集對每個 node pool 用 `gcloud container node-pools update <pool-name> --cluster=<cluster-name> --location=<location> --enable-private-nodes`，節點只剩內部 IP。既有 node pool 的這項變更由 GKE 依 node pool 的升級策略逐批重建節點，排在可以承受節點輪替的時段做。
- **IAP 規則套到節點**：node pool 的 network tag 用 `gcloud container node-pools update <pool-name> --cluster=<cluster-name> --location=<location> --tags=<tag1>,<tag2>` 設定，這個指令會用給的清單**整組取代**使用者設定的 tag，所以要把現有的 tag 一起列進來（`gcloud container node-pools describe <pool-name> --cluster=<cluster-name> --location=<location>` 的 `config.tags`）。GKE 自動建立的防火牆規則用的是它自己產生的 tag，不受這個指令影響。`<location>` 是叢集所在的 zone 或 region。
- **OS Login**：GKE Standard 支援用 OS Login 控制節點的 SSH，專案層級的 `enable-oslogin=TRUE` 會套用到節點，授權方式見那一篇的〈SSH 金鑰在 GCP 上的管理位置：metadata 金鑰與 OS Login 的啟用順序與還原〉；GKE 的 OS Login 文件註明節點有公開 IP 的叢集不支援，所以這一項的前提是節點已經是 private nodes，順序是先做 private nodes、再啟用 OS Login。

## GKE 控制平面的存取：authorized networks 與 DNS-based endpoint

控制平面的 API server 預設有一個公開的 IP 端點，任何地方都連得到，靠 Kubernetes 的認證（通道授權）與 [Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/)（主機登入驗證那一層的對應）擋下沒有權限的請求——在管理通道的模型裡，這等於網路可達性全開，與 `0.0.0.0/0` 開 22 port 是同一種狀態。收窄網路可達性的做法有 authorized networks、DNS-based endpoint 與 private endpoint：

- **authorized networks**：只允許列出的來源 IP 範圍連到 API server 的 IP 端點，相當於來源 IP 白名單，代價與白名單相同（遠端工作、IP 會變動時要一直改，而且分辨不出個人）。`--master-authorized-networks` 每次都用給的清單整組取代舊清單，執行這條指令的人與 CI 的出口 IP 要列在裡面，漏列時指令一生效 `kubectl` 就連不上；`gcloud` 不經過這個端點，連不上時仍可以用同一條指令改回清單。另外，GCP 擁有的公開 IP（包括其他客戶的 VM）預設也連得到公開端點，要排除時加 `--no-enable-google-cloud-access`。
- **DNS-based endpoint**：叢集多一個專屬的網域名稱端點，請求先經過 Google Cloud、以 IAM 判斷這個帳號能不能連到這個叢集（`container.clusters.connect` 權限，`roles/container.developer` 這類角色裡有），通過之後才轉到 API server。它相當於控制平面前面的身分感知代理：網路可達性與通道授權改由 IAM 承擔，不必維護 IP 清單，GitHub Actions 這類外部 CI 也能用 [workload identity federation](/backend/knowledge-cards/workload-identity/) 換到的身分連進來，不必另架[跳板機](/infra/knowledge-cards/bastion-host/)。
- **private endpoint**：控制平面只留內部 IP 端點（`--enable-private-endpoint`），只有 VPC 內與經 VPN 或 Interconnect 接進 VPC 的來源連得到，可以再加 `--enable-authorized-networks-on-private-endpoint` 收窄到 VPC 內的特定範圍。既有的 private cluster 多半是這種設定，從 VPC 外管理時要經過 VPN 或跳板機；改用 DNS-based endpoint 之後這一層可以拿掉。

```bash
# 做法一：只放行列出的來源 IP 範圍連到控制平面的 IP 端點
gcloud container clusters update <cluster-name> --location=<location> \
  --enable-master-authorized-networks --master-authorized-networks=<cidr1>,<cidr2>

# 做法二的第一步：啟用 DNS-based endpoint，IP 端點仍然開著
gcloud container clusters update <cluster-name> --location=<location> \
  --enable-dns-access

# 做法二的第二步：每個人與每條 CI 都改連網域名稱端點之後，才關掉 IP 端點
gcloud container clusters update <cluster-name> --location=<location> \
  --no-enable-ip-access
```

- `<cidr1>,<cidr2>`：允許的來源 IP 範圍，[CIDR](/infra/knowledge-cards/cidr/) 格式（位址加上斜線後的前綴長度，表示一段範圍），單一個 IP 寫成 `/32`，例如公司對外的固定 IP。
- `--enable-dns-access` 與 `--no-enable-ip-access` 分成兩次執行：兩個旗標寫在同一條指令裡會在啟用的同時關掉 IP 端點，還在用 IP 端點的人與 CI 當場連不上。`--no-enable-ip-access` 關掉的是公開與內部兩個 IP 端點，VPC 內用內部 IP 連 API server 的跳板機、自架 runner 與 Terraform 也在要改的範圍內。
- 確認有沒有改連的方法：每個人與每條 CI 用的 kubeconfig，`kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'` 輸出的是網域名稱而不是 IP。DNS-based endpoint 預設只接受 Google 的 IAM 憑證，CI 或工具若用 kubeconfig 裡靜態的 Kubernetes ServiceAccount token 或 client certificate，要另外在 `clusters update` 加 `--enable-k8s-tokens-via-dns` 或 `--enable-k8s-certs-via-dns`，否則關掉 IP 端點之後它們連不上。關掉之後發現漏了，`gcloud` 不經過這個端點，用 `clusters update --enable-ip-access` 打開回來。
- 改連 DNS-based endpoint 時，每個人在本機執行 `gcloud container clusters get-credentials <cluster-name> --location=<location> --dns-endpoint`，讓 kubeconfig（`kubectl` 讀取叢集位址與憑證的設定檔）指向那個網域名稱。

`kubectl` 通過之後，Kubernetes RBAC 決定這個帳號能做什麼。IAM 與 RBAC 是前後兩道檢查、兩道都要設：缺了 IAM 的 `container.clusters.connect` 連不進叢集，缺了 RBAC 綁定連得進去而什麼都做不了。兩者要一起設計，原則與 [GCP VM 的 SSH 與 RDP 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/)〈IAP 的 IAM 授權範圍：誰拿得到通道〉相同：綁給負責維運的群組，不綁給整個網域。

## 延伸閱讀：單台 VM 的指令、管理通道模型與 IaC 的落差

- → [GCP VM 的 SSH 與 RDP 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/)：本篇沿用的 IAP 規則、IAM 權限、OS Login 與 Cloud NAT 的單台 VM 指令與切換順序
- → [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)：網路可達性、通道授權、主機登入驗證三層的模型，以及不可變基礎設施下平時關閉通道的做法
- → [兩套真相並存的過渡期操作](/infra/takeover/partial-iac-dual-truth-operation/)：MIG 與 GKE 多半由 IaC 管理，在 CLI 上建的 template 與改的 node pool 設定要寫回程式碼
