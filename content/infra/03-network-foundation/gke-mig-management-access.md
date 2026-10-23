---
title: "GCP 上由 MIG 與 GKE 管理的 VM 的管理存取：instance template、node pool、kubectl debug 與控制層存取"
date: 2026-10-23
description: "VM 由 managed instance group 或 GKE node pool 管理時，管理通道的設定為什麼要寫在 instance template 與 node pool 而不是逐台修改、IAP 規則與 OS Login 在這兩種環境的設定位置、救援改用重建而非登入的取捨、GKE 節點用 kubectl debug 取代 SSH 的做法與權限邊界，以及 GKE 控制層的存取（authorized networks 與 DNS-based endpoint）"
weight: 7
tags: ["infra", "network", "gcp", "gke", "kubernetes", "ssh", "iap"]
---

這篇處理 GCP 上兩種「VM 不是一台一台手動建的」環境：managed instance group（MIG，依 instance template 自動建立、修復與縮放一組 VM）與 GKE 的 node pool（GKE 用 MIG 管理叢集節點）。範圍是在這兩種環境裡套用 [GCP VM 的 SSH 與 RDP 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/)那一篇的 IAP、OS Login 與移除外部 IP；那一篇的指令以單台 VM 為對象，這一篇說明同樣的設定在這兩種環境要改寫在哪裡、以及 GKE 多出來的那一層控制層存取。管理通道拆成網路可達性、通道授權與主機登入驗證三層的模型見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## 逐台修改為什麼會消失：VM 由 template 重建

MIG 裡的每一台 VM 都由 instance template 建出來。MIG 在幾種時機會刪掉一台 VM、再依 template 建一台新的：自動修復（autohealing，健康檢查失敗時重建）、縮放（autoscaler 加減台數）、滾動更新（換成新版 template），以及 GKE 的節點升級與節點自動修復。新建的 VM 只帶著 template 裡的設定，所以單台 VM 上做的修改——`gcloud compute instances add-tags` 加的 network tag、`add-metadata` 設的 `enable-oslogin`、登入之後 `useradd` 建的救援帳號、`delete-access-config` 移除的外部 IP——都只活到那台 VM 被重建為止。

這種消失沒有任何通知。重建通常發生在半夜的自動修復或下一次縮放，而 IAP 規則靠 network tag 選 VM：新建的 VM 沒有那個 tag，IAP 規則就套不到它，而舊的全開規則若已經刪掉，那台 VM 就從管理通道上消失了。所以這兩種環境的規則是：**管理通道的設定寫在建立 VM 的那一層**（MIG 的 instance template、GKE 的 node pool 設定、或映像檔），逐台的 `gcloud compute instances` 指令只用在臨時查看。

要判斷一台 VM 屬不屬於 MIG，看它的 metadata 有沒有 `created-by` 這個鍵（值是那個 MIG 的資源路徑）；GKE 節點的名稱以 `gke-` 開頭，並帶著 `goog-gke-node` 標籤：

```bash
# 列出 VM 與它所屬的 MIG（第二欄是 - 的就是單獨建立的 VM）
gcloud compute instances list --format=json \
  | jq -r '.[] | [.name, (first((.metadata.items // [])[] | select(.key=="created-by") | .value) // "-")] | @tsv'
```

## MIG：把 tag、OS Login 與外部 IP 寫進 instance template

instance template 建立之後不能修改，改設定的方式是建一份新的 template，再讓 MIG 滾動更新到新版。新 template 裡一次寫進 IAP 需要的 tag、OS Login 與不配外部 IP：

```bash
# 建一份新的 instance template：帶 IAP 用的 tag、啟用 OS Login、不配外部 IP
gcloud compute instance-templates create <new-template-name> \
  --machine-type=<machine-type> \
  --image-family=<image-family> --image-project=<image-project> \
  --network=<network-name> --subnet=<subnet-name> --region=<region> \
  --tags=<ssh-via-iap-tag> \
  --metadata=enable-oslogin=TRUE \
  --no-address

# 讓 MIG 滾動更新到新版 template
gcloud compute instance-groups managed rolling-action start-update <mig-name> \
  --version=template=<new-template-name> --zone=<zone>
```

- `<new-template-name>`：新 template 的名稱，自己取；template 不能改名也不能改內容，常見的做法是名稱帶版本或日期。
- `--machine-type`、`--image-family`、`--image-project`、`--network`、`--subnet`：照抄現行 template 的值，用 `gcloud compute instance-templates describe <current-template-name>` 讀出來；這一步只想改管理通道，其餘設定維持原樣。
- `--region`：`--subnet` 所在的 region。
- `--tags=<ssh-via-iap-tag>`：與 GCP 篇〈啟用 IAP API、開啟稽核紀錄並建立只放行 IAP 來源的防火牆規則〉那條規則的 `--target-tags` 相同的 tag。現行 template 已經有其他 tag（例如負載平衡器健康檢查用的）時一起列進來，逗號分隔。
- `--metadata=enable-oslogin=TRUE`：讓這個 template 建出的 VM 都啟用 OS Login；專案層級已經啟用時可以省略。
- `--no-address`：不配外部 IP。MIG 對外提供服務時，流量入口應該已經在負載平衡器上，VM 本身不需要外部 IP；出站改由 Cloud NAT 承接（GCP 篇〈拿掉外部 IP 之後的出站路徑〉）。
- `<mig-name>`、`--zone`：MIG 的名稱與所在 zone，`gcloud compute instance-groups managed list` 查得到；regional MIG 把 `--zone` 換成 `--region`。

滾動更新會逐批刪掉舊 VM、建新 VM，新 VM 一建好就帶著新設定。這也是驗證的時機：先只更新一台（加 `--max-surge=1 --max-unavailable=0`，或先用 `--canary-version` 讓一小部分 VM 用新 template），經由 IAP 連進那一台、確認 OS Login 與出站都正常，再讓整組更新。

## MIG 的救援：重建比登入便宜

單台 VM 的救援入口是 Serial Console 加一個事先建好的本機救援帳號。MIG 裡的 VM 多了一條更便宜的路：一台 VM 連不上、而原因是那台 VM 自己壞了（sshd 設定改壞、磁碟滿），把它刪掉讓 MIG 依 template 重建，比從 Serial Console 進去修快，也不必替每台 VM 維護救援密碼：

```bash
# 依 template 重建一台 VM：MIG 會刪掉它並建一台同名的新 VM
gcloud compute instance-groups managed recreate-instances <mig-name> \
  --instances=<instance-name> --zone=<zone>
```

重建的前提是 VM 上沒有只存在那一台的狀態：資料寫在外接的資料庫、物件儲存或另外掛載的磁碟上，VM 本身隨時可以丟。這也是 MIG 適合的工作負載本來就有的性質；VM 上有不能丟的狀態時，它更適合當單獨的 VM 管理，而不是放進 MIG。

重建修不好的是 template 本身的錯：新版 template 的 tag 寫錯、啟動腳本有錯，重建出來的每一台都一樣壞。這種錯要退回上一版 template（`rolling-action start-update` 指定舊版的 template 名稱），所以舊版 template 留到新版驗證完之後再刪。真的要登入一台壞掉的 VM 查原因時（例如要保留現場做事後分析），Serial Console 仍然可用；救援帳號要寫進映像檔，而不是寫進 template 的 startup-script，因為 metadata 裡的內容任何有讀取 metadata 權限的人都看得到，把密碼寫在那裡等於公開。

## GKE：兩個要管的存取面

GKE 叢集有兩個不同的存取面，設計時要分開處理：

- **控制層（control plane）**：Kubernetes API server，`kubectl` 連的就是它。日常的部署、查 log、進 pod 執行指令都經過它，這是 GKE 上的主要管理通道。
- **節點（node）**：跑工作負載的 VM。節點的作業系統要登入的情形很少——GKE 管理節點的映像檔、升級與修復，節點本身也是隨時可以丟的。

多數團隊在 GKE 上不需要節點的 SSH：查 pod 的問題用 `kubectl logs`、`kubectl exec`，查節點的問題先看 Cloud Logging 裡的節點紀錄，真的要看到節點作業系統時用〈GKE 節點的存取：kubectl debug、private nodes 與 node pool 的 tag〉的 `kubectl debug node`。所以 GKE 上的管理通道收斂，重點在控制層，節點的 SSH 則是盡量關掉。

## GKE 節點的存取：kubectl debug、private nodes 與 node pool 的 tag

`kubectl debug node` 在指定的節點上建一個 pod，把節點的根目錄掛在 pod 的 `/host`，讓管理員經由 Kubernetes API 看到節點的作業系統，不需要節點開 SSH：

```bash
# 在指定節點上開一個除錯用的 pod，節點的根目錄掛在 /host
kubectl debug node/<node-name> -it --image=ubuntu --profile=sysadmin

# 進到 pod 之後，切換到節點的根目錄，像登入節點一樣查看
chroot /host
```

- `<node-name>`：節點名稱，`kubectl get nodes` 的第一欄。
- `--image=ubuntu`：除錯 pod 用的映像檔，換成組織允許、帶著除錯工具的映像檔。
- `--profile=sysadmin`：讓除錯 pod 以 privileged 權限執行，`chroot /host` 需要這個權限；不加時 pod 起得來，但存取不了節點的大部分資源。

這個 pod 用完不會自動刪除，結束後用 `kubectl delete pod <debug-pod-name>` 刪掉（`kubectl get pods` 找名稱以 `node-debugger-` 開頭的那一個）。`kubectl debug node` 的權限邊界由 Kubernetes 的 RBAC 決定：能在節點上建 privileged pod 的帳號，實質上就能以 root 操作那個節點，所以這個權限只給負責維運的群組，而叢集的 Pod Security 設定若禁止 privileged pod，這個做法也跟著不能用。GKE Autopilot 不允許 privileged pod，也不提供節點 SSH，節點完全由 GKE 管理，查節點層的問題只能靠 Cloud Logging 與 GKE 的工具。

節點仍要 SSH 時（GKE Standard），把 GCP 篇的做法搬到 node pool 層：

- **節點不配外部 IP**：建叢集時加 `--enable-private-nodes`，節點只有內部 IP；節點出站改走 Cloud NAT。
- **IAP 規則套到節點**：node pool 的 network tag 用 `gcloud container node-pools update <pool-name> --cluster=<cluster-name> --tags=<tag1>,<tag2>` 設定，這個指令會用給的清單**整組取代**現有的 tag，所以要把現有的 tag 一起列進來（`gcloud container node-pools describe` 的 `config.tags`）。GKE 自動建立的防火牆規則用的是它自己產生的 tag，不受這個指令影響。
- **OS Login**：GKE Standard 支援用 OS Login 控制節點的 SSH，專案層級的 `enable-oslogin=TRUE` 會套用到節點，授權方式與 GCP 篇〈SSH 金鑰在 GCP 上的管理位置〉相同；GKE 的 OS Login 文件註明節點有公開 IP 的叢集不支援，所以這一項與 private nodes 一起做。

## GKE 控制層的存取：authorized networks 與 DNS-based endpoint

控制層的 API server 預設有一個公開的 IP 端點，任何地方都連得到，靠 Kubernetes 的認證與 RBAC 擋下沒有權限的請求——在管理通道的模型裡，這等於網路可達性全開、只靠後面兩層在擋，與 `0.0.0.0/0` 開 22 port 是同一種狀態。收窄網路可達性有兩種做法：

- **authorized networks**：只允許列出的來源 IP 範圍連到 API server 的 IP 端點，相當於來源 IP 白名單，代價與白名單相同（遠端工作、IP 會變動時要一直改，而且分辨不出個人）。
- **DNS-based endpoint**（建立或更新叢集時加 `--enable-dns-access`）：叢集多一個專屬的網域名稱端點，請求先經過 Google Cloud、以 IAM 判斷這個帳號能不能連到這個叢集，通過之後才轉到 API server。它相當於控制層前面的身分感知代理：網路可達性與通道授權改由 IAM 承擔，不必維護 IP 清單，GitHub Actions 這類外部 CI 也能用 workload identity federation 換到的身分直接連，不必另架跳板機。

兩者可以並用，也可以只留 DNS-based endpoint、關掉 IP 端點的公開存取。`kubectl` 的認證之後還有 Kubernetes RBAC 決定這個帳號能做什麼，相當於主機登入驗證那一層；IAM 角色（例如 `roles/container.developer`）與 RBAC 綁定要一起設計，原則與 GCP 篇〈IAP 的 IAM 授權範圍：誰拿得到通道〉相同：綁給負責維運的群組，不綁給整個網域。

## 延伸閱讀：單台 VM 的指令、管理通道模型與 IaC 的落差

- → [GCP VM 的 SSH 與 RDP 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/)：本篇沿用的 IAP 規則、IAM 權限、OS Login 與 Cloud NAT 的單台 VM 指令與切換順序
- → [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)：網路可達性、通道授權、主機登入驗證三層的模型，以及不可變基礎設施下平時關閉通道的做法
- → [兩套真相並存的過渡期操作](/infra/takeover/partial-iac-dual-truth-operation/)：MIG 與 GKE 多半由 IaC 管理，在 CLI 上建的 template 與改的 node pool 設定要寫回程式碼，否則下一次 apply 會改回去
