---
title: "GCP 上由 MIG 與 GKE 管理的 VM 的管理存取：instance template、node pool、kubectl debug 與控制平面存取"
date: 2026-10-23
description: "VM 由 managed instance group 或 GKE node pool 管理時，管理通道的設定為什麼要寫在 instance template 與 node pool 而不是逐台修改、MIG 救援用重建、退回 template 與 Serial Console 各自適用的情形、GKE 的控制平面與節點兩個存取面、kubectl debug 取代節點 SSH 的權限邊界（RBAC 與 Pod Security Admission），以及 GKE 控制平面三種端點（authorized networks、DNS-based endpoint 與 private endpoint）的差別"
weight: 2
aliases: ["/infra/03-network-foundation/gke-mig-management-access/"]
tags: ["infra", "network", "gcp", "gke", "kubernetes", "ssh", "iap"]
---

這篇處理 GCP 上兩種由 template 自動建立與重建 VM 的環境，其中 GKE 是 Google Kubernetes Engine，GCP 託管的 Kubernetes 服務：managed instance group（[MIG](/infra/knowledge-cards/managed-instance-group/)，依 instance template 自動建立、修復與縮放一組 VM）與 GKE 的 node pool（一組共用同一份設定的叢集節點，GKE 在底下用 MIG 管理它們）。範圍是在這兩種環境裡套用 [GCP VM 的 SSH 與 RDP 管理通道](/infra/cloud-providers/gcp/gcp-iap-ssh-access/)的三項設定：[IAP](/infra/knowledge-cards/identity-aware-proxy/)（Identity-Aware Proxy，GCP 依 IAM 權限轉送 SSH 連線的代理）、[OS Login](/infra/knowledge-cards/os-login/)（讓 VM 的登入帳號與公鑰由 Google 帳號與 IAM 決定）與移除外部 IP：這些設定為什麼要寫在 template 與 node pool、怎麼判斷一台 VM 屬不屬於 MIG、MIG 的幾種救援各自適用的情形、GKE 的兩個存取面、`kubectl debug node` 的權限邊界，以及 GKE 另外要管的 [控制平面（control plane）](/backend/knowledge-cards/control-plane/)存取。建新 template 與 canary 滾動更新、重建與主機金鑰的比對、除錯 namespace、node pool 設定與控制平面端點切換的逐步指令與實跑結果，在 [GCP 上 MIG 與 GKE 管理存取的實測紀錄](/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/)。管理通道拆成網路可達性、通道授權與主機登入驗證三層的模型見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## autohealing、滾動更新與擴增後消失的逐台設定：network tag、OS Login metadata 與外部 IP

MIG 裡的每一台 VM 都由 instance template 建出來。有幾種時機 MIG 會依 template 重建或替換一台 VM，原本開機磁碟上的修改都不會留下：自動修復（autohealing，[健康檢查](/backend/knowledge-cards/health-check/)失敗時重建）、[滾動更新](/backend/knowledge-cards/rolling-update/)（rolling update，換成新版 template），以及 GKE 的節點升級與節點自動修復；[autoscaler](/backend/knowledge-cards/autoscaling/) 擴增台數時則直接依 template 新建。新建的 VM 只帶著 template 裡的設定，所以單台 VM 上做的修改——`gcloud compute instances add-tags` 加的 [network tag](/infra/knowledge-cards/network-tag/)（貼在 VM 上的標籤，防火牆規則用它選出要套用的 VM）、`add-metadata` 設的 `enable-oslogin`、登入之後 `useradd` 建的救援帳號、`delete-access-config` 移除的外部 IP——都只活到那台 VM 被重建為止，新加進來的 VM 則從一開始就沒有。

這種消失沒有任何通知。重建通常發生在半夜的自動修復或下一次擴增，而只放行 IAP 來源的防火牆規則靠 network tag 選 VM：新建的 VM 沒有那個 tag，這條規則就套不到它。收斂管理通道時通常也已經刪掉 `default-allow-ssh`（GCP 預設網路裡放行任何來源連 22 port 的規則），兩者加在一起，新 VM 上沒有任何一條規則放行 SSH，它就從管理通道上消失了。所以這兩種環境的做法是：**管理通道的設定寫在建立 VM 的那一份設定裡**（MIG 的 instance template、GKE 的 node pool 設定、或映像檔），逐台的 `gcloud compute instances` 指令只用在臨時查看。

instance template 建立之後不能修改，改設定的方式是建一份新的 template，再讓 MIG 滾動更新到新版；`instance-templates create` 從預設值開始建、不沿用舊 template 的任何設定，所以新 template 要把現行設定逐項帶上，漏掉的欄位會回到預設值。新版先讓一台 VM 換上（[canary](/backend/knowledge-cards/canary-release/)），驗證通過再讓整組更新，template 寫錯時才只壞一台；建新 template 與 canary 的指令在 [GCP 上 MIG 與 GKE 管理存取的實測紀錄](/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/) 的〈建新的 instance template：現行設定照抄，再加 tag、OS Login 與不配外部 IP〉與〈先讓一台 VM 換成新 template（canary），再讓整組更新〉。MIG 與 GKE 多半由 Terraform 這類 [IaC](/infra/knowledge-cards/iac/) 工具管理，這時 template 與 node pool 的修改都改在程式碼裡：在 CLI 上建的 template、改的 node pool 設定，下一次 apply 會依程式碼改回去，這種程式碼與實際狀態的落差叫 [drift](/infra/knowledge-cards/drift/)，過渡期的做法見[兩套真相並存的過渡期操作](/infra/takeover/partial-iac-dual-truth-operation/)。

要判斷一台 VM 屬不屬於 MIG，看它的 metadata（掛在 VM 上的鍵值設定，VM 內的程式與有讀取權限的帳號都讀得到）有沒有 `created-by` 這個鍵（值是那個 MIG 的資源路徑）。這個鍵由 MIG 在建立 VM 時寫入，VM 被移出 MIG（abandon）之後仍然留著，所以它標出的是建立這台 VM 的 MIG；要確認 VM 現在是否仍是那個 MIG 的成員，用 `gcloud compute instance-groups managed list-instances <mig-name> --zone=<zone>` 列出 MIG 目前的 VM 來對照。GKE 節點帶著 `goog-gke-node` 標籤。下面的指令用 `jq`（命令列的 JSON 處理工具）從 `gcloud` 的 JSON 輸出取出這個鍵，要先在本機裝好；`gcloud` 讀的是目前設定的專案，要查別的專案時加 `--project=<project-id>`：

```bash
# 列出 VM 與它所屬的 MIG（第二欄是 - 的就是單獨建立的 VM）
gcloud compute instances list --format=json \
  | jq -r '.[] | [.name, (first((.metadata.items // [])[] | select(.key=="created-by") | .value) // "-")] | @tsv'
```

GKE 的節點同樣是 MIG 的成員，這條指令會把它們列成屬於某個名稱是 `gke-...-grp` 的 MIG。這類 MIG 由 GKE 管理：對它們建 template、滾動更新或 `recreate-instances`，改動會被 GKE 覆蓋或讓叢集狀態不一致，`recreate-instances` 也不會先把節點上的 Pod 移走。帶著 `goog-gke-node` 標籤的 VM 改走本篇 GKE 的幾節：設定改在 node pool，單一節點壞掉時用 `kubectl drain` 移走 Pod，再交給 GKE 的節點自動修復。

## MIG 的救援：重建、退回舊版 template 與 Serial Console 各自適用的情形

單台 VM 的救援入口是 Serial Console 加一個事先建好的本機救援帳號（[Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/)）。MIG 裡的 VM 多了兩條路，各自適用的情形不同：

- **依 template 重建那一台**（`recreate-instances`）：一台 VM 連不上、而原因是那台 VM 自己壞了（sshd 設定改壞、磁碟滿）時，讓 MIG 依 template 重建它，比從 Serial Console 進去修快，也不必替每台 VM 維護救援密碼。重建的前提是 VM 上沒有只存在那一台的狀態：資料寫在外接的資料庫、物件儲存或另外掛載的磁碟上，VM 本身隨時可以丟。VM 上有不能丟的狀態時，MIG 的 stateful 設定把指定的磁碟、IP 與 metadata 標為要保留；狀態多到每台都不一樣時，它更適合當單獨的 VM 管理。
- **退回上一版 template**：重建修不好的是 template 本身的錯（tag 寫錯、啟動腳本有錯），重建出來的每一台都一樣壞，這種錯要整組退回上一版，所以舊版 template 留到新版驗證完之後再刪。
- **Serial Console**：需要登入一台壞掉的 VM 查原因、保留現場做事後分析時仍然可用。救援帳號的帳號與密碼雜湊要在建立[映像檔](/backend/knowledge-cards/immutable-image/)時寫進去（用 Packer 這類建映像檔的工具，或在一台 VM 上建好帳號再把磁碟做成自訂映像檔），而不是寫進 template 的 startup-script，因為 startup-script 存在 metadata 裡，任何有讀取 metadata 權限的人都看得到，把密碼寫在那裡等於公開。寫進映像檔的代價是整組 VM 共用同一組密碼雜湊，要輪替就要重做映像檔、再滾動更新一次。

重建之後要知道的一件事是主機金鑰換了：重建在原地換掉開機磁碟，VM 沿用原本的名稱與執行個體 ID，而 `gcloud compute ssh` 在本機用 `compute.<instance-id>` 記錄主機金鑰，所以第一次連線會出現 `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` 並拒絕連線。這個警告也是中間人攻擊時會看到的訊息，處理方式是先用不經過這條 SSH 連線的來源（guest attributes 回報的[主機金鑰](/infra/knowledge-cards/ssh-host-key/)；guest attributes 是 VM 寫回 metadata server、可以經由 GCP API 讀取的鍵值，要事先設 `enable-guest-attributes=TRUE`）確認新的金鑰確實來自這台 VM，再移除舊紀錄，不關掉主機金鑰檢查。重建與退回的指令、重建做完的確認方式與主機金鑰的比對，在 [GCP 上 MIG 與 GKE 管理存取的實測紀錄](/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/) 的〈重建一台壞掉的 VM：recreate-instances 與重建之後的主機金鑰〉與〈template 本身寫錯時退回上一版〉；Serial Console 的開啟與救援帳號的登入，在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈準備救援入口：Serial Console 與本機救援帳號〉。

## GKE 的存取面：控制平面與節點

GKE 叢集有兩個不同的存取面，設計時要分開處理：

- **控制平面**：Kubernetes 的 API server，`kubectl` 連的就是它。日常的部署、查 log、進 [Pod](/backend/knowledge-cards/pod/) 執行指令都經過它，這是 GKE 上的主要管理通道。
- **節點（node）**：跑工作負載的 VM。節點的作業系統要登入的情形很少：GKE 管理節點的映像檔、升級與修復，節點本身也是隨時可以丟的。

多數團隊在 GKE 上不需要節點的 SSH：查 Pod 的狀況用 `kubectl logs`、`kubectl exec`，查節點的狀況先看 Cloud Logging 裡的節點紀錄，需要看到節點作業系統時用 `kubectl debug node`。所以在 GKE 上收斂管理通道時，工作集中在控制平面的存取，節點的 SSH 盡量關掉。

GKE 有兩種叢集模式：Standard 由使用者管理 node pool 與節點設定；Autopilot 由 GKE 管理節點，使用者只管工作負載。〈kubectl debug node 的權限邊界：RBAC 與 Pod Security Admission〉裡建專用 namespace 與節點 SSH 的做法只適用於 Standard。

## kubectl debug node 的權限邊界：RBAC 與 Pod Security Admission

`kubectl debug node/<node-name>` 在指定的節點上建一個 Pod，把節點的根目錄掛在 Pod 的 `/host`，讓管理員經由 Kubernetes API 看到節點的作業系統，不需要節點開 SSH；進到 Pod 之後 `chroot /host`（把行程的根目錄換成 `/host`），之後執行的指令看到的是節點的檔案系統。不加 `--profile` 時，較新的 kubectl 用預設的 `general` profile（舊版的預設是 `legacy`），除錯 Pod 已經以 root 執行、共用節點的行程、網路與 IPC 的 Linux namespace，讀寫節點的檔案、用 `crictl` 列出節點上的容器都做得到；`--profile=sysadmin` 以[特權容器（privileged container）](/backend/knowledge-cards/privileged-container/)執行，多給的是需要額外 Linux capability（核心把 root 權限拆成的個別權限項）的操作。

這個做法的權限邊界有兩道。[Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/) 決定誰能用它：在除錯 Pod 所在的 [namespace](/backend/knowledge-cards/namespace/) 要有 `pods` 的 `create`（建 Pod）、`list` 與 `watch`（kubectl 用 watch 等 Pod 進入執行狀態）、`delete`（用完刪掉），以及 `pods/attach` 的 `create`（`-it` 在 Pod 建好之後附加到它的終端機），這幾項綁在那個 namespace 的 RoleBinding；另外要有 `nodes` 的 `get`，節點不屬於任何 namespace，這一項要用 ClusterRoleBinding 授予。少了 `list` 或 `watch` 時 Pod 已經建好，kubectl 卻停在等待；少了 `pods/attach` 時 Pod 建得出來卻進不去；兩種情形都會留下一個在跑的除錯 Pod。

能在節點上建除錯 Pod 的帳號，用預設的 `general` profile 就能以 root 讀寫節點的檔案，所以這組權限只給負責維運的群組。[Pod Security Admission](/backend/knowledge-cards/pod-security-admission/) 決定那個 namespace 是否接受這類 Pod：`kubectl debug node` 用 `general` 或 `sysadmin` profile 建的 Pod 帶著主機的網路、行程與 IPC 的 Linux namespace（hostNetwork、hostPID、hostIPC）與主機目錄掛載（hostPath），namespace 設了 `pod-security.kubernetes.io/enforce=baseline` 或 `restricted` 時，這幾項都會讓除錯 Pod 被拒絕；用 `--profile=baseline` 或 `restricted` 建的除錯 Pod 不帶這些設定，建得進這類 namespace，但看不到節點的檔案。反過來，沒有設這個 label 的 namespace（包括 `default`）在 GKE Standard 上預設接受特權 Pod，所以任何能在 `default` 建 Pod 的帳號，現在就能用這個方法以 root 操作節點。做法是把一般工作負載的 namespace 都設成 `baseline` 以上，節點除錯集中到一個刻意保留為 `privileged` 等級、而且只有維運群組能建 Pod 的 namespace，由叢集管理員事先建好；建法與使用的指令在 [GCP 上 MIG 與 GKE 管理存取的實測紀錄](/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/) 的〈GKE 節點除錯：建專用的 namespace，用 kubectl debug node 查看節點〉。GKE Autopilot 預設拒絕特權 Pod（只有列入允許清單的合作夥伴工作負載例外），也不提供節點 SSH，查節點層的狀況靠 Cloud Logging 裡的節點紀錄與 GKE 主控台的節點狀態。

節點仍要 SSH 時（GKE Standard），單台 VM 的三項設定搬到 node pool 上：節點不配外部 IP 的 private nodes（先要有 Cloud NAT，換成內部 IP 之後節點的出站都經過它）、node pool 的 network tag（`node-pools update --tags` 整組取代使用者設定的 tag，GKE 自建的 tag 不受影響），以及 OS Login。Autopilot 叢集不能用 OS Login，因為節點由 GKE 管理。專案層級的 `enable-oslogin=TRUE` 是否套用到 GKE Standard 的節點，GKE 自己的兩份文件寫法相反：OS Login 的設定頁說專案層的設定套用到專案裡所有既有與新建的 VM，node pool 的管理頁則寫 OS Login 在 GKE 節點上被明確停用，所以啟用之後經由 IAP 實際登入一個節點，以登入後的帳號判斷。三項設定的指令在 [GCP 上 MIG 與 GKE 管理存取的實測紀錄](/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/) 的〈node pool：private nodes、network tag 與 OS Login〉。

## GKE 控制平面的存取：authorized networks、DNS-based endpoint 與 private endpoint

控制平面的 API server 預設有一個公開的 IP 端點，任何地方都連得到，靠 Kubernetes 的認證（通道授權）與 [Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/)（主機登入驗證那一層的對應）擋下沒有權限的請求——在管理通道的模型裡，這等於網路可達性全開，與 `0.0.0.0/0` 開 22 port 是同一種狀態。收窄網路可達性的做法有三種：

- **authorized networks**：只允許列出的來源 IP 範圍連到 API server 的 IP 端點，相當於來源 IP 白名單，代價與白名單相同（遠端工作、IP 會變動時要一直改，而且分辨不出個人）。清單每次都整組取代，執行指令的人與 CI 的出口 IP 漏列時 `kubectl` 當場連不上，而 `gcloud` 不經過這個端點，連不上時仍可以改回。設了 authorized networks 之後，GCP 上其他客戶的 VM 的外部 IP 是否放行，由叢集的 Google Cloud 外部 IP 存取設定決定（`gcpPublicCidrsAccessEnabled`，要明確設定過一次才會出現在 `describe` 的輸出裡）。
- **DNS-based endpoint**：叢集多一個專屬的網域名稱端點，請求先經過 Google Cloud、以 IAM 判斷這個帳號能不能連到這個叢集（`container.clusters.connect` 權限，`roles/container.developer` 這類角色裡有），通過之後才轉到 API server。它相當於控制平面前面的身分感知代理：網路可達性與通道授權改由 IAM 承擔，不必維護 IP 清單，GitHub Actions 這類外部 CI 也能用 [workload identity federation](/backend/knowledge-cards/workload-identity/) 換到的身分連進來，不必另架[跳板機](/infra/knowledge-cards/bastion-host/)。啟用之後 IP 端點仍然開著，每個人與每條 CI 都改連網域名稱端點之後才關掉 IP 端點；兩步分開是因為關掉 IP 端點的那一刻，還在用它的人與 CI 當場連不上。
- **private endpoint**：控制平面只留內部 IP 端點（`--enable-private-endpoint`），只有 VPC 內與經 VPN 或 Interconnect 接進 VPC 的來源連得到，可以再加 `--enable-authorized-networks-on-private-endpoint` 收窄到 VPC 內的特定範圍。既有的 private cluster 多半是這種設定，從 VPC 外管理時要經過 VPN 或跳板機；改用 DNS-based endpoint 之後這一層可以拿掉。

三種做法的指令、兩步切換的確認方式與實跑結果，在 [GCP 上 MIG 與 GKE 管理存取的實測紀錄](/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/) 的〈控制平面：authorized networks，或改連 DNS-based endpoint 再關掉 IP 端點〉。

一個 `kubectl` 請求要通過兩次檢查。連進叢集的檢查是 IAM 的 `container.clusters.connect`：經 DNS-based endpoint 連線時缺了它，請求在進到 API server 之前就被 Google 的前端以 `403 Forbidden` 擋下。請求進到 API server 之後，API server 再判斷這個帳號是否有權限執行這個請求（例如列出節點），這項授權檢查在 GKE 上由 IAM 與 Kubernetes RBAC 共同決定，兩者任一個允許就放行：IAM 的 Kubernetes 物件權限（例如 `container.nodes.list`，`roles/container.developer` 這類角色裡有）或 RBAC 的 Role 與 RoleBinding。只拿到 `container.clusters.connect`（例如 `roles/container.clusterViewer`）的帳號連得進叢集，列出節點時會收到 `nodes is forbidden: User "<email>" cannot list resource "nodes"`，訊息後面寫著它要的 IAM 權限名稱。IAM 與 RBAC 的授權要一起設計，原則與 [GCP VM 的 SSH 與 RDP 管理通道](/infra/cloud-providers/gcp/gcp-iap-ssh-access/)〈IAP 的 IAM 授權範圍：誰拿得到通道〉相同：綁給負責維運的群組，不綁給整個網域。

## 延伸閱讀：逐步的實作、單台 VM 的做法、管理通道模型與 IaC 的落差

- → [GCP 上 MIG 與 GKE 管理存取的實測紀錄](/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/)：新 template 與 canary、重建與主機金鑰、退回 template、除錯 namespace、node pool 設定與控制平面端點切換的逐步指令、實跑結果，以及每一步換一種做法時的結果
- → [GCP VM 的 SSH 與 RDP 管理通道](/infra/cloud-providers/gcp/gcp-iap-ssh-access/)：本篇沿用的 IAP 規則、IAM 權限、OS Login 與 Cloud NAT 在單台 VM 上的機制與切換順序
- → [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)：網路可達性、通道授權、主機登入驗證三層的模型，以及不可變基礎設施下平時關閉通道的做法
- → [兩套真相並存的過渡期操作](/infra/takeover/partial-iac-dual-truth-operation/)：MIG 與 GKE 多半由 IaC 管理，在 CLI 上建的 template 與改的 node pool 設定要寫回程式碼
