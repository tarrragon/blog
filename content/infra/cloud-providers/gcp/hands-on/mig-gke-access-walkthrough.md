---
title: "GCP 上 MIG 與 GKE 管理存取的實測紀錄：instance template 與 canary 滾動更新、重建與主機金鑰、kubectl debug 的 namespace、node pool 設定與控制平面端點的切換"
date: 2026-10-25
description: "要把 IAP 的 tag、OS Login 與移除外部 IP 套到 MIG 或 GKE 上，想照一次實跑過的順序做、看每一步換一種做法的結果時讀；也用在 MIG 重建之後 SSH 出現 REMOTE HOST IDENTIFICATION HAS CHANGED、kubectl debug 停在等待，或關掉 GKE 控制平面的 IP 端點之前要確認每個人都改連的時候"
weight: 2
tags: ["infra", "network", "gcp", "gke", "kubernetes", "ssh", "iap", "hands-on"]
---

實測日期是 2026-10-24，在 GCP 測試專案 `blog-verify-20261024`（zone `asia-east1-b`）上：MIG 用 Debian 12 的 e2-micro，GKE 是 zonal 的 Standard 叢集（版本 1.36.4-gke、Container-Optimized OS 節點）；控制平面的 IAM 檢查另外用第二個帳號的 access token 驗證。`kubectl debug node` 與 Pod Security Admission 另外在本機的 kind（Kubernetes v1.37.0、kubectl v1.37.1）上實跑。

這篇記錄把 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/)（下文稱 IAP 實作文章）的三項設定（IAP 用的 network tag、OS Login、移除外部 IP）套到 MIG 與 GKE 上的實際操作。內容依操作的順序是：建一份帶這三項設定的新 instance template，先讓一台 VM 換成新版（canary）再讓整組更新；用 `recreate-instances` 重建一台壞掉的 VM、比對重建之後換掉的主機金鑰；template 本身寫錯時退回上一版；在 GKE 上建一個專門給節點除錯用的 namespace，用 `kubectl debug node` 查看節點；node pool 的 private nodes、network tag 與 OS Login；控制平面的 authorized networks，以及改連 DNS-based endpoint、關掉 IP 端點的兩步切換。每一步寫出這次的取值與實測結果，以及沒做或換一種做法時的結果；替代做法與沒做時的結果沒有另外標註的是這次實測看到的，照官方文件推出的寫出文件，推論的寫明沒有實跑。逐台設定為什麼在這兩種環境裡會消失、MIG 救援的取捨、GKE 的兩個存取面、`kubectl debug node` 的權限邊界，以及控制平面的 authorized networks、DNS-based endpoint 與 private endpoint 三種存取方式的差別，寫在 [GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/infra/cloud-providers/gcp/gke-mig-management-access/)（下文稱概念篇），這裡不重寫。

MIG 與 GKE 由 Terraform 這類 IaC 管理時，下面的 `gcloud` 修改要改寫在程式碼裡，CLI 上只執行 `describe` 這類讀取用的指令；這篇的指令在沒有 IaC 的環境照著執行，有 IaC 的環境把它們當成欄位對照。instance template 不能修改、又被 MIG 引用著，所以 IaC 改 template 時，取代的順序要另外設成先建新的再刪舊的（Terraform 是 `name_prefix` 搭配 `lifecycle { create_before_destroy = true }`），否則先刪舊 template 的那一步會因為它還在使用中而失敗；canary 對應 `google_compute_instance_group_manager` 的兩個 `version` 區塊。這一段是推論，這次沒有用 Terraform 實跑。

## 建新的 instance template：現行設定照抄，再加 tag、OS Login 與不配外部 IP

instance template 建立之後不能修改，`instance-templates create` 從預設值開始建、不沿用舊 template 的任何設定，所以先把現行 template 讀出來，逐項帶進新的那一份。這三項設定為什麼要寫進 template、不能在 VM 上逐台改，見概念篇〈autohealing、滾動更新與擴增後消失的逐台設定：network tag、OS Login metadata 與外部 IP〉。

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

# 比對新舊兩份的設定：差異只該是刻意改的 tag、enable-oslogin 與 accessConfigs
diff <(gcloud compute instance-templates describe <current-template-name> --format="yaml(properties)") \
     <(gcloud compute instance-templates describe <new-template-name> --format="yaml(properties)")
```

- `<current-template-name>`：MIG 目前用的 template，`gcloud compute instance-groups managed describe <mig-name> --zone=<zone>` 的 `instanceTemplate` 欄。
- `<new-template-name>`：新 template 的名稱，自己取；template 不能改名也不能改內容，常見的做法是名稱帶版本或日期。
- `--machine-type`、`--image-family`、`--image-project`、`--boot-disk-size`、`--network`、`--subnet`、`--region`、`--service-account`、`--scopes`、`--labels`、`--metadata-from-file=startup-script=`：照 `describe` 讀出來的值填，`describe` 裡還有其他欄位（額外的磁碟、GPU、其他 metadata 鍵）也要對應的旗標一起帶上。`--region` 是 `--subnet` 所在的 region。`describe` 的欄位與旗標不是一對一：映像在 `disks[].initializeParams.sourceImage`，值可能是一個特定映像的完整路徑，也可能是 `.../images/family/<family>` 這種 family 的路徑（實測：用 `--image-family` 建的 template 讀出來是 `.../images/family/debian-12`），兩種都可以原樣交給 `--image=<sourceImage 的值>`，取代 `--image-family` 與 `--image-project`；服務帳號在 `serviceAccounts[].email`，template 用的是 Compute Engine 預設服務帳號時這一欄顯示 `default` 而不是 email（實測），原樣寫成 `--service-account=default`，建出的 template 用的仍是同一個預設服務帳號；startup-script 在 `metadata.items` 裡 `key: startup-script` 的 `value`，先把它存成檔案再交給 `--metadata-from-file`；regional 的 template 讀取時 `describe` 要加 `--region=<region>`。
- `--tags=<ssh-via-iap-tag>`：與 IAP 規則的 `--target-tags` 相同的 tag。新 template 只帶這裡列出的 tag，所以現行 template 已經有的其他 tag（`describe` 輸出的 `tags.items`，例如負載平衡器健康檢查用的）要一起列進來，逗號分隔。
- `--metadata=enable-oslogin=TRUE`：讓這個 template 建出的 VM 都啟用 OS Login；專案層級已經啟用時可以省略。
- `--no-address`：不配外部 IP。先確認流量入口已經在負載平衡器上，`gcloud compute backend-services list --format="table(name, backends[].group)"` 的 `backends` 欄要有這個 MIG。這一點只能事先查：服務若是靠 VM 的外部 IP 對外，〈先讓一台 VM 換成新 template（canary），再讓整組更新〉換上新版的那一台只是收不到流量、不容易察覺，canary 這一步驗不出來，整組更新之後服務就斷了。出站改由 Cloud NAT 承接，所以 Cloud NAT 要在滾動更新之前建好。已經存在的 VM 在滾動更新把它換成新版時才失去外部 IP。

這次用 `--service-account=default` 建的新 template，與現行 template 的 `properties` 比對，只差刻意改的 tag、`enable-oslogin` 與 `accessConfigs`。

- **沒做時**（漏帶 `describe` 裡的欄位）：漏掉的欄位回到預設值，常見的後果是 VM 換成預設的服務帳號而失去存取權限，或啟動腳本沒有執行（從 `create` 由預設值開始建這一點推論，這次沒有實跑）；上面的 `diff` 會把漏掉的欄位列出來。
- **替代做法**：
  - 用 `gcloud compute instance-templates create <new-template-name> --source-instance=<instance-name> --source-instance-zone=<zone>` 從一台現有的 VM 產生 template，換到的是不必逐項抄旗標；付出的是這條指令只能另外覆寫磁碟的定義，tag、OS Login 與 `--no-address` 要再以它為基礎建第二份，而來源 VM 有靜態外部 IP 時，那個位址會被抄進 template（Compute Engine〈Create instance templates〉，這次沒有實跑）。
  - 在專案層級設 `enable-oslogin=TRUE`、不寫進 template，換到的是 template 少一個鍵，付出的是 template 的行為依賴專案的設定，搬到別的專案就變了（推論，這次沒有實跑）。

## 先讓一台 VM 換成新 template（canary），再讓整組更新

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
- `--canary-version=template=<new-template-name>,target-size=1`：讓一台 VM 換成新 template；`target-size` 也可以寫百分比（`10%`），條件是 MIG 有 10 台以上（Compute Engine〈Rolling out updates〉）。
- `<mig-name>`、`--zone`：MIG 的名稱與所在 zone，`gcloud compute instance-groups managed list` 查得到；regional MIG 把 `--zone` 換成 `--region`。

`start-update` 送出之後 MIG 在背景替換 VM，指令本身不等它完成。用下面兩條確認替換做完、並找出 canary 那一台：

```bash
# 等到每台 VM 都換成指定的版本才返回
gcloud compute instance-groups managed wait-until <mig-name> --version-target-reached --zone=<zone>

# 列出 MIG 裡的 VM 與各自用的 template，INSTANCE_TEMPLATE 欄是新 template 的那一台就是 canary
gcloud compute instance-groups managed list-instances <mig-name> --zone=<zone>
```

實測 `wait-until` 在替換做完之後才返回，`list-instances` 的 `INSTANCE_TEMPLATE` 欄只有一台是新 template。找到 canary 那一台之後，經由 IAP 連進去，確認 OS Login 登得進去、出站經過 Cloud NAT（驗證方式見 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈建 Cloud NAT 並移除外部 IP〉）。整組更新之後同樣用 `wait-until` 等它完成。

- **沒做時**（不經過 canary、直接整組更新）：template 的 tag 或 OS Login 寫錯時，整組 VM 一起連不上（照滾動更新的作用推論，這次沒有實跑）。
- **替代做法**：
  - 只改 tag 與 metadata 時加 `--minimal-action=refresh`：Compute Engine〈Rolling out updates〉寫明 refresh 不停止 VM，可以套用 metadata、labels、tags 這類項目，換到的是 VM 不重建、主機金鑰不變；付出的是 `--no-address` 移除外部 IP 不在那份清單上，很可能仍要重建（照官方文件推出，這次沒有實跑）。
  - `--type=opportunistic` 只在 VM 重建或擴增時才套用新 template，換到的是不主動中斷任何一台，付出的是組內新舊混雜，舊的 VM 一直沒有新的 tag（照官方文件推出，這次沒有實跑）。
  - 整組更新時加 `--max-surge=1 --max-unavailable=0`，每一批先多建一台新的、再刪一台舊的（實測先建後刪），換到的是更新期間可用台數不減少，付出的是多一台 VM 的費用，而且這兩個旗標只控制速度，更新仍會把整組換完。regional MIG 的 `--max-surge` 用固定數字時，GCP 只接受 0 或不小於 zone 數的值，錯誤訊息是 `has to be either 0 or at least equal to the number of zones`，所以分布在兩個以上 zone 的 regional MIG，`--max-surge=1` 會被拒絕。

## 重建一台壞掉的 VM：recreate-instances 與重建之後的主機金鑰

一台 VM 連不上、而原因是那台 VM 自己壞了（sshd 設定改壞、磁碟滿），讓 MIG 依 template 重建它：

```bash
# 依 template 重建一台 VM：開機磁碟換成依 MIG 目前的版本設定新建的一顆，VM 重新開機
gcloud compute instance-groups managed recreate-instances <mig-name> \
  --instances=<instance-name> --zone=<zone>
```

`<instance-name>` 是要重建的那台 VM，`gcloud compute instance-groups managed list-instances <mig-name> --zone=<zone>` 列出 MIG 裡的 VM。實測重建在稽核紀錄裡是一次 `instances.update`（沒有 delete 與第二次 insert），VM 沿用原本的名稱與執行個體 ID，`gcloud compute instances describe` 的建立時間也不變，所以確認重建做完要看開機磁碟：MIG 建的 VM 開機磁碟預設與 VM 同名，`gcloud compute disks describe <instance-name> --zone=<zone> --format="value(creationTimestamp)"` 印出的時間落在重建的那一刻，就代表磁碟已經換新。canary 期間重建的 VM 用哪一版，由 MIG 依兩個版本各自的 `target-size` 分配，實測重建的那一台沿用了原版本。

重建之後第一次 `gcloud compute ssh` 出現 `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` 並拒絕連線（實測），原因與這個警告為什麼不能直接略過，見 [GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/infra/cloud-providers/gcp/gke-mig-management-access/) 的〈MIG 的救援：重建、退回舊版 template 與 Serial Console 各自適用的情形〉。比對的來源是 VM 回報到 guest attributes 的主機金鑰，專案或 template 的 metadata 要事先設了 `enable-guest-attributes=TRUE`（專案層用 `gcloud compute project-info add-metadata --metadata enable-guest-attributes=TRUE`）：

```bash
# 讀出 VM 回報的 ED25519 主機金鑰指紋，與警告訊息裡 "The fingerprint for the ED25519 key sent by the remote host is" 下一行的 SHA256 值比對
gcloud compute instances get-guest-attributes <instance-name> --zone=<zone> \
  --query-path=hostkeys/ssh-ed25519 --format="value(value)" \
  | awk '{print "ssh-ed25519 " $1}' | ssh-keygen -lf -

# 兩個指紋相同之後，移除這台 VM 的舊紀錄，再用 gcloud compute ssh 連線
ssh-keygen -R compute.<instance-id> -f ~/.ssh/google_compute_known_hosts
```

`<instance-id>` 是 `gcloud compute instances describe <instance-name> --zone=<zone> --format="value(id)"` 印出的數字。`ssh-keygen -R` 會把原本的檔案備份成同目錄的 `google_compute_known_hosts.old`。實測啟用 guest attributes 之後，gcloud 不會自動更新已經存在的 known_hosts 紀錄，讀出的 ED25519 指紋與警告裡的一致，移除舊紀錄之後即可連線。兩個指紋不同時不要移除，先確認連到的 IP 仍是這台 VM 的位址，以及連線是否經過了 IAP 以外的代理；兩項都正常而指紋仍不同時，改從 [Serial Console](/infra/knowledge-cards/serial-console/) 登入 VM、讀 `/etc/ssh/ssh_host_ed25519_key.pub` 的指紋再比一次。警告寫的是 ECDSA 時，指令裡的 `ED25519` 與 `ssh-ed25519` 分別換成 `ECDSA` 與 `ecdsa-sha2-nistp256`。

- **沒做時**（不設 `enable-guest-attributes`）：重建之後沒有不經過這條 SSH 連線的地方可以比對主機金鑰，只剩從 Serial Console 登入讀指紋，或不比對就移除舊紀錄；不比對就移除，等於關掉主機金鑰檢查（推論，這次沒有實跑）。
- **替代做法**：
  - 從 Serial Console 登入修那台 VM，換到的是保留現場，付出的是要事先在映像檔裡放救援帳號（救援帳號的密碼雜湊寫在映像檔裡，不寫進 template 的 startup-script，理由與共用密碼雜湊的代價見概念篇〈MIG 的救援：重建、退回舊版 template 與 Serial Console 各自適用的情形〉）；登入與 sudo 的做法見 IAP 實作文章的〈準備救援入口：Serial Console 與本機救援帳號〉。
  - VM 上有不能丟的狀態時，MIG 的 stateful 設定（stateful policy 或 per-instance config）把指定的磁碟、IP 與 metadata 標為要保留，`recreate-instances` 重建時會沿用它們（Compute Engine〈Stateful MIGs〉，這次沒有實跑）。

## template 本身寫錯時退回上一版

重建修不好的是 template 本身的錯：新版 template 的 tag 寫錯、啟動腳本有錯，重建出來的每一台都一樣壞。這種錯要退回上一版 template，所以舊版 template 留到新版驗證完之後再刪：

```bash
# 退回上一版 template：整組換回舊版；canary 期間執行時，只有 canary 那幾台被換回
gcloud compute instance-groups managed rolling-action start-update <mig-name> \
  --version=template=<previous-template-name> --zone=<zone>
```

`<previous-template-name>` 是新版之前那一份 template 的名稱，`gcloud compute instance-templates list` 列得出來。這次實測退回成功。Compute Engine〈Rolling out updates〉寫明沒有專門的退回指令，退回就是送一次指向舊 template 的更新。

- **沒做時**（新版一驗證就刪掉舊 template）：退回時要用 `describe` 讀過的舊設定重建一份 template，而舊 template 已經刪掉、讀不到了（從 template 不能修改、刪了就沒有這兩點推論，這次沒有實跑）。

## GKE 節點除錯：建專用的 namespace，用 kubectl debug node 查看節點

節點除錯集中在一個刻意保留為 `privileged` 等級、只有維運群組能建 Pod 的 namespace，由叢集管理員事先建好：

```bash
# 建一個專門給節點除錯用的 namespace，並允許特權 Pod
kubectl create namespace <namespace>
kubectl label namespace <namespace> pod-security.kubernetes.io/enforce=privileged
```

`<namespace>` 自己取，例如 `node-debug`；建好之後只把 [GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/infra/cloud-providers/gcp/gke-mig-management-access/) 的〈kubectl debug node 的權限邊界：RBAC 與 Pod Security Admission〉列的那組 `pods` 與 `pods/attach` 權限綁給維運群組。接著在這個 namespace 裡對節點開除錯 Pod：

```bash
# 在指定節點上開一個除錯用的 Pod，節點的根目錄掛在 /host
kubectl debug node/<node-name> -it --image=ubuntu --profile=sysadmin --namespace=<namespace>

# 進到 Pod 之後，切換到節點的根目錄，像登入節點一樣查看
chroot /host
```

- `<node-name>`：節點名稱，`kubectl get nodes` 的第一欄。
- `--image=ubuntu`：除錯 Pod 用的映像檔，換成組織允許、帶著除錯工具的映像檔。
- `--profile=sysadmin`：讓除錯 Pod 以[特權容器（privileged container）](/backend/knowledge-cards/privileged-container/)執行，多給的是需要額外 Linux capability 的操作，例如用 `nsenter` 進入節點 PID 1 的 namespace、掛載檔案系統；只查看檔案與 log 時，預設的 `general` profile 就夠了（`kubectl debug --help` 的 `--profile` 說明寫著預設值）。
- `--namespace=<namespace>`：除錯 Pod 建在上面建好的那個 namespace；不給時落在 kubeconfig 目前設定的 namespace（通常是 `default`）。

這個 Pod 用完不會自動刪除，結束後用 `kubectl delete pod <debug-pod-name> --namespace=<namespace>` 刪掉（`kubectl get pods --namespace=<namespace>` 找名稱以 `node-debugger-` 開頭的那一個）。實測 GKE 上未設 label 的 `default` 接受除錯 Pod、設了 `baseline` 的 namespace 拒絕；kind 上 `privileged` 的 namespace 接受。

- **沒做時**（不建專用 namespace）：沒有設 Pod Security label 的 namespace（包括 `default`）在 GKE Standard 上接受特權 Pod，任何能在 `default` 建 Pod 的帳號都能用這個方法以 root 操作節點。少了 `list` 或 `watch` 權限時，Pod 已經建好而 kubectl 停在等待、反覆印出 `cannot list resource "pods"`；少了 `pods/attach` 時 Pod 建得出來卻進不去；兩種都會留下一個在跑的除錯 Pod，要用 `kubectl delete pod` 刪掉（kind 上實跑）。
- **替代做法**：
  - 用 `--profile=baseline` 或 `restricted`，換到的是建得進 `baseline` 以上的 namespace，付出的是看不到節點的檔案。
  - 查節點層的狀況先看 Cloud Logging 裡的節點紀錄，換到的是不必在節點上開任何 Pod，付出的是只看得到已經送進 Logging 的紀錄（推論，這次沒有實跑）。GKE Autopilot 預設拒絕特權 Pod，也不提供節點 SSH，只剩這一條（GKE〈Autopilot overview〉，這次沒有實跑）。

## node pool：private nodes、network tag 與 OS Login

節點仍要 SSH 時（GKE Standard），把 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的三項設定搬到 node pool 上：

```bash
# 既有 node pool 改成節點只有內部 IP（GKE 依升級策略逐批重建節點）
gcloud container node-pools update <pool-name> --cluster=<cluster-name> --location=<location> --enable-private-nodes

# 讀出現有的 tag，再用整份清單設定（這個指令整組取代使用者設定的 tag）
gcloud container node-pools describe <pool-name> --cluster=<cluster-name> --location=<location> --format="value(config.tags)"
gcloud container node-pools update <pool-name> --cluster=<cluster-name> --location=<location> --tags=<tag1>,<tag2>
```

- `<pool-name>`、`<cluster-name>`：`gcloud container node-pools list --cluster=<cluster-name> --location=<location>` 與 `gcloud container clusters list` 查得到。`<location>` 是叢集所在的 zone 或 region。
- `--enable-private-nodes`：先確認節點所在 subnet 的 region 已經有 Cloud NAT，換成內部 IP 之後節點的出站都經過它；沒有它時節點拉不到外部 registry 的映像，工作負載起不來。GKE 依 node pool 的升級策略逐批重建節點，所以排在可以承受節點輪替的時段做。新叢集在 `gcloud container clusters create` 加 `--enable-private-nodes` 作為整個叢集的預設。實測既有 node pool 的這項變更重建了節點，出站走 Cloud NAT、tag 保留。
- `--tags=<tag1>,<tag2>`：實測整組取代（gcloud 的確認提示也這樣寫），GKE 自動建立的防火牆規則用的 tag 保留，節點沒有重建。

OS Login 的授權方式同單台 VM，見 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈啟用 OS Login：先授角色、單台先行、再做專案層級〉。專案層級的 `enable-oslogin=TRUE` 是否套用到 GKE Standard 的節點，GKE 自己的兩份文件寫法相反，所以啟用之後經由 IAP 實際登入一個節點確認：登入後執行 `whoami`，看到的是由 Google 帳號 email 轉換而來的 OS Login 帳號，才表示這個 node pool 的節點套用了 OS Login；看到的是 metadata 金鑰對應的本機帳號，代表節點沒有套用，SSH 仍由 metadata 金鑰控制。這次在 1.36.4-gke 的節點上看到的是 OS Login 帳號，這是單一版本的觀察。

- **沒做時**（只在單一節點上 `add-tags`）：節點升級或自動修復重建之後 tag 消失，IAP 規則套不到它（照概念篇〈autohealing、滾動更新與擴增後消失的逐台設定：network tag、OS Login metadata 與外部 IP〉的機制推論，這次沒有實跑）。
- **替代做法**：不開節點 SSH、只用 `kubectl debug node`，換到的是不必維護節點的 tag、OS Login 與 IAP 規則，付出的是能建除錯 Pod 的帳號就等於節點的 root，權限邊界移到 RBAC 與 Pod Security Admission。

## 控制平面：authorized networks，或改連 DNS-based endpoint 再關掉 IP 端點

```bash
# authorized networks：只放行列出的來源 IP 範圍連到控制平面的 IP 端點
gcloud container clusters update <cluster-name> --location=<location> \
  --enable-master-authorized-networks --master-authorized-networks=<cidr1>,<cidr2>

# DNS-based endpoint 的啟用：IP 端點仍然開著
gcloud container clusters update <cluster-name> --location=<location> \
  --enable-dns-access

# 關掉 IP 端點：每個人與每條 CI 都改連網域名稱端點之後才執行
gcloud container clusters update <cluster-name> --location=<location> \
  --no-enable-ip-access
```

- `<cidr1>,<cidr2>`：允許的來源 IP 範圍，[CIDR](/infra/knowledge-cards/cidr/) 格式，單一個 IP 寫成 `/32`。實測以 Private Service Connect 建立的叢集拒絕文件範例用的保留網段 `203.0.113.0/24`，錯誤訊息寫明只接受在網際網路上可路由的範圍。`--master-authorized-networks` 每次都整組取代舊清單，執行這條指令的人與 CI 的出口 IP 要列在裡面：實測漏列時指令一生效 `kubectl` 就逾時，`gcloud` 不經過這個端點，用同一條指令改回清單就恢復。
- `--enable-dns-access` 與 `--no-enable-ip-access` 分成兩次執行：寫在同一條指令裡會在啟用的同時關掉 IP 端點，還在用 IP 端點的人與 CI 當場連不上。`--no-enable-ip-access` 關掉的是公開與內部兩個 IP 端點，VPC 內用內部 IP 連 API server 的跳板機、自架 runner 與 Terraform 也在要改的範圍內。

改連 DNS-based endpoint 時，每個人在本機執行 `gcloud container clusters get-credentials <cluster-name> --location=<location> --dns-endpoint`，讓 kubeconfig 指向那個網域名稱。確認有沒有改連：每個人與每條 CI 用的 kubeconfig，`kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'` 輸出的是網域名稱而不是 IP。DNS-based endpoint 預設只接受 Google 的 IAM 憑證，CI 或工具若用 kubeconfig 裡靜態的 Kubernetes ServiceAccount token 或 client certificate，要另外在 `clusters update` 加 `--enable-k8s-tokens-via-dns` 或 `--enable-k8s-certs-via-dns`。

實測：DNS endpoint 的兩步切換不受 IP 清單限制；`--no-enable-ip-access` 之後 IP 端點逾時（對照組：開啟且來源在清單內時 HTTP 401），DNS 照常；`clusters update --enable-ip-access` 恢復。用第二個帳號以 `--token` 帶入它的 access token：沒有 IAM 角色時 DNS endpoint 回 Google 前端的 403 HTML；只有 `roles/container.clusterViewer` 時進到 API server，列節點回 `cannot list resource "nodes"`，訊息裡寫著它要的 IAM 權限 `container.nodes.list`。

- **沒做時**（維持公開端點、不設任何限制）：任何地方都連得到 API server，只靠 Kubernetes 的認證與 RBAC 擋下沒有權限的請求，等於網路可達性全開（照 GKE〈Access the control plane〉推出，這次沒有在公開端點上量）。
- **替代做法**：
  - authorized networks 換到的是設定一條指令，付出的是 IP 會變動時要一直改、分辨不出個人；設了之後，GCP 上其他客戶的外部 IP 是否放行由 `--enable-google-cloud-access`／`--no-enable-google-cloud-access` 決定。實測沒碰過這兩個旗標時，`describe` 沒有 `gcpPublicCidrsAccessEnabled` 欄位，這時實際是否放行沒有驗證；變更可能要幾個小時才生效（GKE 文件，這次沒有實跑）。
  - private endpoint（`--enable-private-endpoint`）換到的是控制平面只剩內部 IP，付出的是從 VPC 外管理時要經過 VPN 或跳板機（GKE 文件，這次沒有實跑）。三種端點的比較見概念篇〈GKE 控制平面的存取：authorized networks、DNS-based endpoint 與 private endpoint〉。
