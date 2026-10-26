---
title: "GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄：盤點、救援入口、IAP 規則與 IAM、停用舊規則驗證、OS Login 啟用與移除外部 IP"
date: 2026-10-25
description: "要把 GCP 專案裡對 0.0.0.0/0 開放 22 與 3389 port 的預設規則換成只放行 IAP，想照一次實跑過的順序做、看每一步沒做或換一種做法的結果時讀；也用在停用舊規則之後連不上、OS Login 啟用後有人登不進去，或拿掉外部 IP 之後要確認出站走了 Cloud NAT 的時候"
weight: 1
tags: ["infra", "network", "gcp", "ssh", "rdp", "iap", "firewall", "hands-on"]
---

實測日期是 2026-10-24，在 GCP 測試專案 `blog-verify-20261024`（zone `asia-east1-b`，`default` 網路）上，對一台 Debian 12 的 e2-micro 與一台 Windows Server 2022 的 e2-medium，用本機的 `gcloud` 照這一篇的順序操作；IAM 條件與 OS Login 角色另外用第二個 Google 帳號登入驗證。

這篇記錄把 VM 的管理員登入從防火牆對 `0.0.0.0/0` 開放 22 與 3389 port，改成走 IAP TCP forwarding 的實際操作。內容依操作的順序是：切換前盤點依賴舊規則的連線；準備並實際登入一次救援入口（Serial Console 與本機救援帳號）；啟用 IAP API、開啟 IAP 的稽核紀錄、建立只放行 IAP 來源的防火牆規則與 network tag；授予開通道的 IAM 權限；停用舊規則、用 IAP 驗證新規則；刪除對外開放的規則；收斂 `default-allow-internal` 與 `default-allow-icmp`；啟用 OS Login；建 Cloud NAT 並移除外部 IP。每一步寫出這次的取值與實測結果，以及沒做或換一種做法時的結果；替代做法與沒做時的結果沒有另外標註的是這次實測看到的，照官方文件推出的寫出文件，推論的寫明沒有實跑。IAP 的連線路徑、預設規則為什麼要換、切換的順序為什麼這樣排、IAM 授權的範圍、連不上時的依層判讀、OS Login 與 Cloud NAT 的機制，寫在 [GCP VM 的 SSH 與 RDP 管理通道：從預設的全開規則改走 IAP TCP forwarding](/infra/cloud-providers/gcp/gcp-iap-ssh-access/)（下文稱概念篇），這裡不重寫。

這一篇的指令以單台 VM 為對象。由 MIG 或 GKE 管理的 VM，同樣的設定改寫在 instance template 與 node pool 上，做法在 [GCP 上 MIG 與 GKE 管理存取的實測紀錄](/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/)；Shared VPC 的 service project、用 Terraform 管理的專案，指令要改寫在別的位置；新專案從零開始則可以跳過盤點與停用驗證。這幾種環境的調整見概念篇開場之後「另外四種環境要先調整做法再往下讀」那一段。

## 切換前的盤點：依賴舊規則的連線

`default-allow-ssh` 放行的不只是管理員本人的 SSH：CI 或部署腳本用外部 IP 直連 VM、Ansible 這類[組態管理](/infra/knowledge-cards/configuration-management/)工具、監控程式的探測、第三方廠商的維護連線，都可能經過這條規則，而預設規則沒有開 logging，手上沒有紀錄可以查出它們。盤點分兩步。先對舊規則開啟 logging，列出經過它的候選來源：

```bash
# 對舊規則開啟 logging，之後每一次放行都會寫進 Cloud Logging
gcloud compute firewall-rules update default-allow-ssh --enable-logging
gcloud compute firewall-rules update default-allow-rdp --enable-logging

# 觀察一段時間後，列出經由舊規則連進來的來源 IP 與次數（RDP 把規則名稱換成 default-allow-rdp）
gcloud logging read \
  'logName:"compute.googleapis.com%2Ffirewall" AND jsonPayload.rule_details.reference:"default-allow-ssh"' \
  --freshness=7d --format="value(jsonPayload.connection.src_ip)" | sort | uniq -c
```

`--freshness=7d` 是查詢往回看的時間長度，依自己的部署週期調整，要涵蓋到一次完整的部署與排程工作。實際依賴這條規則的連線，要從 VM 上的成功登入紀錄找（理由見概念篇〈切換到 IAP 的順序〉）：

```bash
# 在 Linux VM 上列出這段期間成功的 SSH 登入：帳號、來源 IP 與金鑰指紋
sudo journalctl -u ssh -u sshd --since "7 days ago" | grep "Accepted publickey"
```

每一行的格式是 `Accepted publickey for <user> from <ip> ... <金鑰指紋>`，用帳號與金鑰指紋就認得出是哪個人或哪個自動化工具。Windows VM 看事件檢視器的安全性紀錄裡事件 ID 4624、登入類型 10（遠端互動，也就是 RDP）的事件。找出來的非人員來源要先改走 IAP 才能停用舊規則：CI 與自動化工具用服務帳號開 IAP 通道，一般 `ssh` 的工具照概念篇〈IAP TCP forwarding 的連線路徑與來源範圍〉的 `ProxyCommand` 改設定。

- **沒做時**：停用舊規則的那一刻，依賴它的 CI、監控與廠商連線跟管理員的一起被拒；這些失敗出現在部署或排程執行時，不一定在切換當下被看到（從規則的作用推論，這次沒有實跑）。
- **替代做法**：觀察期縮短或省略，換到的是切換提早，付出的是只盤點到觀察期內發生過的連線，一個月跑一次的排程會漏掉；只看防火牆紀錄、不看 VM 上的登入紀錄，換到的是不必登入每一台 VM，付出的是 CI 這類來源 IP 每次不同的連線認不出來（兩者都從紀錄的形狀推論，這次沒有實跑）。

## 準備救援入口：Serial Console 與本機救援帳號

[Serial Console](/infra/knowledge-cards/serial-console/) 透過 VM 的虛擬序列埠提供登入，不經過 VM 的網路設定與 sshd，在防火牆 tag 漏加、sshd 設定改壞、OS Login 設錯、磁碟滿導致 sshd 起不來時當作救援入口。它用 VM 內的本機帳號密碼登入，與 metadata 金鑰、OS Login 都無關，所以救援帳號要在 VM 還正常時就建好：

```bash
# 在每台 Linux VM 上建一個設了密碼的本機救援帳號（RHEL 系把 sudo 群組換成 wheel）
sudo useradd -m rescue && sudo passwd rescue && sudo usermod -aG sudo rescue

# 確認 sshd 仍然只收金鑰，救援帳號的密碼只在 Serial Console 上有效
sudo sshd -T | grep -i passwordauthentication
```

`rescue` 是自己取的帳號名稱。密碼用密碼管理工具逐台隨機產生、存在團隊的密碼庫，不同 VM 不共用同一組；持有救援密碼的人離開團隊時，逐台輪替。`sshd -T` 印出 sshd 實際生效的設定，那一行要是 `passwordauthentication no`，否則救援帳號的密碼也能從 SSH 登入。Windows VM 的序列主控台（Special Administration Console）用 Windows 的本機管理員帳號登入，要事先確認那個帳號的密碼在手上。

Serial Console 的互動登入預設關閉，平時保持關閉，救援時才對單一 VM 開啟：

```bash
# 救援時對單一 VM 開啟 Serial Console 並連上
gcloud compute instances add-metadata <instance-name> --zone=<zone> --metadata serial-port-enable=TRUE
gcloud compute connect-to-serial-port <instance-name> --zone=<zone>

# 救援結束後關回去
gcloud compute instances add-metadata <instance-name> --zone=<zone> --metadata serial-port-enable=FALSE
```

`<instance-name>` 與 `<zone>` 用 `gcloud compute instances list` 查，第一欄是 VM 名稱、第二欄是 zone。建好救援帳號之後，對一台 VM 照上面的指令開啟、用 `rescue` 登入並執行一次 `sudo -v` 確認 sudo 可用，再關回去；這次在 Debian 12 的 VM 上實跑，登入與 sudo 都成功。Windows VM 的 SAC 這次沒有實跑。

- **沒做時**：停用舊規則、或之後啟用 OS Login 時任何一項設錯，VM 沒有不經過網路與 sshd 的入口；剩下的路是在 metadata 設 `startup-script`（Linux）或 `windows-startup-script-ps1`（Windows）、重開機以 root 或 SYSTEM 執行來建帳號或改回設定，或把開機磁碟卸下掛到另一台 VM 修改，兩條都要重開機（Compute Engine 的啟動腳本與救援文件，這次沒有實跑）。
- **替代做法**：
  - 救援帳號寫進自訂映像檔，換到的是新建的 VM 一開始就有，付出的是密碼雜湊在每台 VM 上相同、要輪替就要重做映像（推論，這次沒有實跑）。
  - 靠 startup-script 臨時建帳號，換到的是平時不留密碼，付出的是救援時要重開機，而且 startup-script 存在 metadata 裡，有讀取權限的人都看得到內容（Compute Engine 的 metadata 文件，這次沒有實跑）。
  - 組織強制了 `compute.disableSerialPortAccess` 時，救援名單要有能對專案解除這條政策的人，見 [GCP VM 的 SSH 與 RDP 管理通道](/infra/cloud-providers/gcp/gcp-iap-ssh-access/) 的〈組織層級的護欄：Organization Policy 與階層式防火牆〉。

## 啟用 IAP API、開啟稽核紀錄並建立只放行 IAP 來源的防火牆規則

IAP 端點以 API 的形式在專案上開關，沒有啟用時，`--tunnel-through-iap` 的連線在 IAP 端點那一步就開不起來：

```bash
# 啟用 IAP API（每個專案一次）
gcloud services enable iap.googleapis.com
```

同一步在 Google Cloud 控制台的「IAM 與管理 > 稽核記錄」為 Cloud Identity-Aware Proxy 開啟 Data Access 紀錄裡的「管理員讀取」（`ADMIN_READ`）類型。開通道時 IAP 檢查的權限 `iap.tunnelInstances.accessViaIAP` 歸在這個類型，每一次開通道會留下一筆方法名稱為 `AuthorizeUser` 的紀錄。開啟之後經由 IAP 連一次，查到這次連線的紀錄才算開對了類型（`protoPayload.resourceName` 是 VM 的執行個體 ID）：

```bash
gcloud logging read 'protoPayload.serviceName="iap.googleapis.com" AND protoPayload.methodName="AuthorizeUser"' \
  --freshness=1h --format="value(timestamp,protoPayload.authenticationInfo.principalEmail,protoPayload.resourceName)"
```

也在同一步確認所有要開通道的 Google 帳號都已強制兩步驟驗證，理由見概念篇〈IAP 的 IAM 授權範圍：誰拿得到通道〉最後兩段。

- **沒做時**（不開 `ADMIN_READ`）：開通道的帳號與目標 VM 沒有 VM 以外的紀錄，事後調查只剩 Admin Activity 裡的設定變更與 VM 上的 sshd 紀錄；開啟之前的通道紀錄查不回來（Cloud Audit Logs 文件，這次沒有實跑）。
- **替代做法**：只開「資料讀取」（`DATA_READ`）實測過：連了十次左右，紀錄零筆。兩種都開，換到的是不必判斷權限歸在哪一類，付出的是紀錄量與費用增加（推論，這次沒有量）。

新規則只開需要的 port，並用 target tag 限定作用的 VM：

```bash
# 放行 IAP 的 IPv4 來源連到帶指定 tag 的 Linux VM 的 22 port
gcloud compute firewall-rules create allow-ssh-from-iap \
  --network=<network-name> \
  --direction=INGRESS \
  --action=allow \
  --rules=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --target-tags=<ssh-via-iap-tag> \
  --enable-logging

# 有 Windows VM 時，另建一條放行 3389 port 的規則，用另一個 tag
gcloud compute firewall-rules create allow-rdp-from-iap \
  --network=<network-name> \
  --direction=INGRESS \
  --action=allow \
  --rules=tcp:3389 \
  --source-ranges=35.235.240.0/20 \
  --target-tags=<rdp-via-iap-tag> \
  --enable-logging
```

- `allow-ssh-from-iap`、`allow-rdp-from-iap`：規則名稱，自己取，同一個專案裡不能重複。
- `<network-name>`：VM 所在的 VPC 名稱，預設網路就是 `default`，自建網路用 `gcloud compute networks list` 查。
- `<ssh-via-iap-tag>`、`<rdp-via-iap-tag>`：自己取的 [network tag](/infra/knowledge-cards/network-tag/) 名稱，例如 `ssh-iap`、`rdp-iap`。SSH 與 RDP 用不同的 tag，Linux VM 就不會被順便開了 3389。
- `--enable-logging`：讓防火牆把這條規則的每一次放行寫進 Cloud Logging，驗證新規則與之後稽核都要用到。
- `--source-ranges=35.235.240.0/20`：Google 公開的 IAP 來源位址段，每個專案都相同；`--rules` 依通道填要開的 port（SSH 是 `tcp:22`、RDP 是 `tcp:3389`）。這兩條規則沒有寫 `--priority`，預設是 1000（實測），比 `default-allow-ssh` 的 65534 先被評估。

自建的 custom-mode VPC 有 IPv6 VM 時，再建一條名稱不同（例如 `allow-ssh-from-iap-v6`）、`--source-ranges=2600:2d00:1:7::/64`、其餘引數相同的規則。接著對每台 VM 加上對應的 tag，VM 分布在不同 zone 時逐台以各自的 `--zone` 執行：

```bash
gcloud compute instances add-tags <instance-name> --zone=<zone> --tags=<ssh-via-iap-tag>
gcloud compute instances add-tags <windows-instance-name> --zone=<zone> --tags=<rdp-via-iap-tag>
```

- **沒做時**（漏加 tag）：停用舊規則之後，IAP 回 `4003`（failed to connect to backend），Connectivity Tests 指出擋下它的是 `default-deny-ingress`。
- **替代做法**：
  - 省略 `--target-tags`，換到的是不必逐台加 tag，付出的是 IAP 來源連得到網路裡每一台 VM 的 22 port（照規則的作用推論，這次沒有實跑）。
  - 把 `--rules` 寫成 `all`，換到的是不必列 port，付出的是 IAP 來源連得到每一台 VM 的每一個 port，等於把 `default-allow-internal` 的寬度複製給 IAP（照規則的作用推論，這次沒有實跑）。
  - 改用 `--target-service-accounts` 以服務帳號選 VM，換到的是 tag 不能被持有 VM 修改權限的人隨手加上（能編輯 VM 的人改得了它的 tag），付出的是同一個服務帳號的 VM 全部一起套用，而且 VM 換服務帳號要停機（VPC 防火牆規則文件，這次沒有實跑）。

## 授予開通道的 IAM 權限

開通道的權限是 IAM role `roles/iap.tunnelResourceAccessor`。下面的指令把它綁在專案層級，並用 IAM Conditions（在角色綁定上附加條件，條件成立時這個綁定才生效）限定可以連的 port 或期限；條件的寫法依環境選一種：

```bash
# 只有 Linux VM：條件限定只能連 22 port
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<admin-email> \
  --role=roles/iap.tunnelResourceAccessor \
  --condition='expression=destination.port == 22,title=iap-ssh-only'

# 同時有 Windows VM：條件放行 22 與 3389
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<admin-email> \
  --role=roles/iap.tunnelResourceAccessor \
  --condition='expression=destination.port == 22 || destination.port == 3389,title=iap-ssh-rdp'

# 只允許連特定一台 VM 的 22 port
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<admin-email> \
  --role=roles/iap.tunnelResourceAccessor \
  --condition='expression=destination.port == 22 && destination.ip == "<vm-internal-ip>",title=iap-ssh-one-vm'

# 外包或臨時存取：到期之後綁定自動失效
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<contractor-email> \
  --role=roles/iap.tunnelResourceAccessor \
  --condition='expression=destination.port == 22 && request.time < timestamp("<expiry-time>"),title=iap-ssh-until-expiry'
```

- `<project-id>`：VM 所在的專案 ID，用 `gcloud config get-value project` 查目前設定的是哪一個。
- `<admin-email>`、`<contractor-email>`：要給權限的人的 Google 帳號；給一群人時把 `user:` 換成 `group:` 加 Google Group 的位址，CI 這類機器身分換成 `serviceAccount:` 加服務帳號的位址。
- `<vm-internal-ip>`：VM 的內部 IP，`gcloud compute instances list` 的 `INTERNAL_IP` 欄查得到。
- `<expiry-time>`：綁定失效的時間，RFC 3339 格式，例如 `2027-03-31T00:00:00Z`。
- `title`：這個條件的顯示名稱，自己取，會出現在 IAM 頁面上。

這次用第二個帳號實測：沒有這個角色時開通道回 `4033`；條件只放行 22 時連 3389 回 `4033`（Owner 帳號對照回 `4003`，代表 Owner 不受條件限制、而是被防火牆擋下）；限定單一 VM 與過期的條件連續三分鐘回 `4033`，正對照在 75 秒內放行。IAM 綁定從送出到生效約 60 到 120 秒，這段時間內的 `4033` 不代表條件寫錯。

Linux VM 的 `gcloud compute ssh` 另外要 VM 端的登入權限：還沒啟用 OS Login 時，`gcloud compute ssh` 把公鑰寫進專案或 VM 的 metadata（實測寫進專案 metadata），所以非 Owner 的帳號要有修改 metadata 的權限（例如 `roles/compute.instanceAdmin.v1`），VM 掛著服務帳號時另外要那個服務帳號的 `roles/iam.serviceAccountUser`；已經啟用 OS Login 時，改由〈啟用 OS Login：先授角色、單台先行、再做專案層級〉的登入角色決定。兩種情形都要讀取 VM 與專案資訊的權限（例如 `roles/compute.viewer`）。

- **沒做時**：非 Owner 的管理員開通道回 `4033`。Owner 不需要這一步，所以團隊全員都是 Owner 時，這一步看起來不必做，而 IAM Conditions 對 Owner 不生效，條件寫了也限不住任何人（Owner 連 3389 回 `4003` 而不是 `4033`）。
- **替代做法**：不加條件，換到的是指令短、不必維護條件，付出的是持有角色的人連得到專案裡每台 VM 的每個 port（只要防火牆放行）；綁給 `domain:` 或大型群組，換到的是不必逐人授權，付出的是整個組織的帳號都能開通道（兩者都從角色的作用推論，這次沒有實跑）。取捨的判斷見概念篇〈IAP 的 IAM 授權範圍：誰拿得到通道〉。

## 停用舊規則，用 IAP 驗證新規則

先在舊規則還在時，每一位管理員各自用自己的帳號連一次，確認 IAM 權限：

```bash
# Linux：透過 IAP 通道 SSH 進 VM
gcloud compute ssh <instance-name> --zone=<zone> --tunnel-through-iap

# Windows：把 VM 的 3389 port 經 IAP 轉到本機的 13389，再用 RDP 用戶端連 localhost:13389
gcloud compute start-iap-tunnel <windows-instance-name> 3389 --local-host-port=localhost:13389 --zone=<zone>
```

加上 `--tunnel-through-iap` 時，`gcloud` 改走 IAP、不連 VM 的外部 IP；VM 還有外部 IP 時，少了這個參數的連線走的是舊路徑。這一次連線驗證的是 IAM：IAP 端點會拒絕沒有權限的帳號。防火牆規則與 tag 這一次驗不到，因為舊規則的 `0.0.0.0/0` 也放行 IAP 的位址段。接著停用舊規則（規則仍在，只是不生效），由一位管理員對 Linux 與 Windows 各一台 VM 再連一次：

```bash
gcloud compute firewall-rules update default-allow-ssh --disabled
gcloud compute firewall-rules update default-allow-rdp --disabled
gcloud compute ssh <instance-name> --zone=<zone> --tunnel-through-iap
```

這一次連得上，代表放行連線的是新規則；前提是專案裡沒有其他來源涵蓋 `35.235.240.0/20` 的允許規則，用概念篇〈預設網路自帶的防火牆規則〉的列出規則指令確認。這次實測停用之後經由 IAP 連得上、不加 `--tunnel-through-iap` 的直連被拒，Windows 經 IAP 的 3389 回了 X.224 Connection Confirm。新規則建立時加了 `--enable-logging`，可以查防火牆紀錄確認命中的是哪一條規則：

```bash
# 查最近一小時經由 IAP 規則放行的連線
gcloud logging read \
  'logName:"compute.googleapis.com%2Ffirewall" AND jsonPayload.rule_details.reference:"allow-ssh-from-iap"' \
  --freshness=1h --limit=10
```

規則剛開啟 logging 的最初幾分鐘，紀錄裡的 `rule_details` 可能是空的（實測前兩筆沒有、約五分鐘後的三筆有），照本節的順序正好落在這段時間，所以上面這條查不到不代表新規則沒有命中。這時改用來源 IP 查，結果與 `rule_details` 是否已經填入無關；驗 RDP 的規則時把 `22` 換成 `3389`：

```bash
gcloud logging read \
  'logName:"compute.googleapis.com%2Ffirewall" AND ip_in_net(jsonPayload.connection.src_ip, "35.235.240.0/20") AND jsonPayload.connection.dest_port=22' \
  --freshness=1h --limit=10 \
  --format="value(timestamp,jsonPayload.connection.src_ip,jsonPayload.rule_details.reference)"
```

連不上時，用下面的指令把舊規則恢復，再照概念篇〈IAP 通道連不上時的依層判讀〉找出是哪一層；防火牆規則透過 GCP 的 API 修改，SSH 連不上也改得回來：

```bash
gcloud compute firewall-rules update default-allow-ssh --no-disabled
gcloud compute firewall-rules update default-allow-rdp --no-disabled
```

`4003` 時要用 Connectivity Tests 查是哪一條規則或政策擋下：`gcloud network-management connectivity-tests create <test-name> --source-ip-address=35.235.240.1 --destination-instance=projects/<project-id>/zones/<zone>/instances/<instance-name> --destination-port=22 --protocol=TCP`，`<test-name>` 自己取，`--source-ip-address` 只收單一 IP，取 IAP 位址段裡的任一個。

- **主控台的 SSH 按鈕**（SSH-in-browser）：官方〈Connect to Linux VMs using IAP〉寫明它只在 VM 沒有外部 IP 時才走 IAP。所以 VM 還帶外部 IP 時，停用舊規則之後，用主控台按鈕的人連不上，而 `--tunnel-through-iap` 驗起來是通的，這不代表新規則壞了；外部 IP 移除之後，主控台按鈕改走 IAP（照官方文件推出，這次沒有實跑）。盤點時把用主控台按鈕登入的人一起找出來，切換期間請他們改用 `--tunnel-through-iap`。
- **沒做時**（只在舊規則還在時驗證）：連得上的那一次可能是舊規則放行的，tag 漏加或規則寫錯都測不出來，要到刪除舊規則之後才發現（照規則的作用推論，這次沒有實跑）。
- **替代做法**：
  - 不停用、只查防火牆紀錄裡命中的規則名稱，換到的是驗證期間外部來源照常連得到，付出的是要等 `rule_details` 填入，而且兩條規則都放行時紀錄記的是先被評估的那一條（推論，這次沒有在兩條並存時查）。
  - 直接刪除舊規則再驗證，換到的是少一步，付出的是出錯時要重建規則，重建時可能寫錯；停用的規則用 `--no-disabled` 一行恢復原樣。

## 刪除對外開放的規則

刪除之前，列出還沒帶 tag 的 VM，兩份清單都要是空的（只有 Linux 或只有 Windows 時，查對應的那一份）：

```bash
gcloud compute instances list --filter="NOT tags.items=<ssh-via-iap-tag>"
gcloud compute instances list --filter="NOT tags.items=<rdp-via-iap-tag>"
```

清單裡出現的是另一種作業系統的 VM 時合理（Linux VM 本來就不帶 RDP 的 tag），其餘的要先補上 tag 再刪規則。專案裡還沒有任何 VM 帶 tag 時，`gcloud` 會先印一行 `WARNING: The following filter keys were not present in any resource : tags.items`，下面列出的 VM 清單仍然正確（實測）。

```bash
gcloud compute firewall-rules delete default-allow-ssh default-allow-rdp
```

刪除之後才發現有漏掉的連線來源時，照原樣把規則建回來，再回頭處理（實測建得回來）：

```bash
gcloud compute firewall-rules create default-allow-ssh --network=default \
  --direction=INGRESS --action=allow --rules=tcp:22 --source-ranges=0.0.0.0/0 --priority=65534 --enable-logging
gcloud compute firewall-rules create default-allow-rdp --network=default \
  --direction=INGRESS --action=allow --rules=tcp:3389 --source-ranges=0.0.0.0/0 --priority=65534 --enable-logging
```

- **沒做時**（停用之後不刪）：停用的規則不放行任何連線，效果與刪除相同；留著的代價是有人用 `--no-disabled` 一行就恢復全開（照規則的作用推論，這次沒有實跑）。Security Command Center 的 `OPEN_SSH_PORT` finding 是否把停用的規則算進去，這次沒有確認。
- **替代做法**：用 `gcloud compute firewall-rules update default-allow-ssh --source-ranges=<固定的管理網段>` 把來源收窄、不刪除，換到的是保留一條直連的路，付出的是這條路的授權仍然是來源 IP，分辨不出人（取捨見 [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/) 的〈網路可達性的做法：管理 port 對誰開放〉，這次沒有實跑）。

## 收斂 default-allow-internal 與 default-allow-icmp

`default-allow-internal` 要先確認 VM 之間實際需要哪些 port（應用連資料庫、節點之間的叢集通訊）再改成具體的規則。改法是為每一組需要的連線各建一條規則，例如應用連 PostgreSQL：

```bash
gcloud compute firewall-rules create allow-app-to-db --network=default \
  --direction=INGRESS --action=allow --rules=tcp:5432 \
  --source-tags=<app-tag> --target-tags=<db-tag>
```

`<app-tag>`、`<db-tag>` 是自己取的 tag，加在應用與資料庫 VM 上；`tcp:5432` 換成實際的服務 port。每一組需要的連線都建好之後，再刪 `default-allow-internal`。`default-allow-icmp` 的處理看用途：監控或除錯流程會用 `ping` 確認 VM 存活時，保留並把來源縮到內部網段與監控主機（`gcloud compute firewall-rules update default-allow-icmp --source-ranges=10.128.0.0/9,<monitoring-host-ip>/32`，`<monitoring-host-ip>` 是發 ping 的監控主機的 IP）；沒有這種用途就一起刪除。這一節的指令這次沒有實跑。

- **沒做時**：同一個網路裡的 VM 之間不受 port 限制，一台 VM 被入侵之後能直接連到其他 VM 的資料庫與管理 port；管理通道本身不受影響，所以這一步可以排進另一次變更（照規則的作用推論，這次沒有實跑）。
- **替代做法**：直接刪除 `default-allow-internal`，換到的是一步收完，付出的是 VM 之間的服務連線當場中斷；整個網路改成自己規劃的 custom-mode VPC，換到的是預設規則一次清掉，付出的是 VM 要搬網路，見概念篇〈預設網路自帶的防火牆規則〉（兩者都是推論，這次沒有實跑）。

## 啟用 OS Login：先授角色、單台先行、再做專案層級

啟用 OS Login 之後，VM 不再接受 metadata 裡的金鑰（實測：metadata 金鑰被拒），順序為什麼是先授角色、單台先行，見 [GCP VM 的 SSH 與 RDP 管理通道](/infra/cloud-providers/gcp/gcp-iap-ssh-access/) 的〈SSH 金鑰在 GCP 上的管理位置：metadata 金鑰與 OS Login 的啟用條件〉。先把登入角色授予每一位管理員與每一個要登入 VM 的服務帳號；VM 掛著服務帳號時，每一個登入者另外需要那個服務帳號的 `roles/iam.serviceAccountUser`：

```bash
# 授予管理員 OS Login 的登入角色：一般登入與含 sudo 的兩種擇一
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<admin-email> --role=roles/compute.osLogin
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<admin-email> --role=roles/compute.osAdminLogin

# CI 或自動化工具的服務帳號同樣要授予（需要 sudo 時改用 osAdminLogin）
gcloud projects add-iam-policy-binding <project-id> \
  --member=serviceAccount:<ci-service-account-email> --role=roles/compute.osLogin

# 查 VM 掛的服務帳號，並授予登入者使用它的權限
gcloud compute instances describe <instance-name> --zone=<zone> \
  --format="get(serviceAccounts[0].email)"
gcloud iam service-accounts add-iam-policy-binding <service-account-email> \
  --member=user:<admin-email> --role=roles/iam.serviceAccountUser
```

`<ci-service-account-email>` 是 CI 或自動化工具開通道用的服務帳號，`<service-account-email>` 是上一條 `describe` 查出來、VM 掛的那個服務帳號，兩者不同。這次用第二個帳號實測：缺 `serviceAccountUser` 時 `Permission denied (publickey)`，補上之後 20 秒內登入；`osLogin` 不能 sudo、`osAdminLogin` 可以。

接著先對一台 VM 啟用，讓每一位非 Owner 的管理員各自用自己的帳號連通並確認 sudo 可用，CI 也對這台跑一次部署，再做專案層級：

```bash
# 先對單一 VM 啟用，連通確認
gcloud compute instances add-metadata <instance-name> --zone=<zone> --metadata enable-oslogin=TRUE

# 確認之後在專案層級啟用（VM 層級的設定會蓋過專案層級）
gcloud compute project-info add-metadata --metadata enable-oslogin=TRUE

# 連不上時還原（修改 metadata 走 API，不需要登入 VM）
gcloud compute instances add-metadata <instance-name> --zone=<zone> --metadata enable-oslogin=FALSE
gcloud compute project-info add-metadata --metadata enable-oslogin=FALSE
```

專案層級啟用之後再盤點兩件事。VM 層級設了 `enable-oslogin=FALSE` 的 VM 會蓋過專案設定、仍然讀 metadata 金鑰（實測），用下面這條列出它們的名稱，逐台改成 `TRUE` 或移除這個鍵：

```bash
gcloud compute instances list --format=json \
  | jq -r '.[] | select(any(.metadata.items[]?; .key=="enable-oslogin" and (.value|ascii_downcase)=="false")) | .name'
```

專案 metadata 的 `ssh-keys` 仍然留著前任與現任成員的公鑰，OS Login 一旦還原成 `FALSE` 它們就又能用，確認全部 VM 都啟用之後用 `gcloud compute project-info remove-metadata --keys=ssh-keys` 清掉（實測）。

- **沒做時**（不啟用 OS Login）：登入驗證仍是 metadata 裡的公鑰，寫在專案 metadata 的公鑰對專案裡每台 VM 都生效，成員離職時漏刪一把，那把金鑰就持續能登入整個專案（OS Login 文件，這次沒有實跑）。
- **替代做法**：
  - 直接在專案層級啟用、不經過單台，換到的是少一輪驗證，付出的是角色漏授時鎖住的是整個專案的每一台 VM；只由 Owner 驗證，看不出漏授，因為 Owner 持有全部權限（推論，這次沒有實跑）。
  - 改用 SSH 憑證（OpenSSH CA），換到的是主機不全在 GCP 時也能用同一套，付出的是要維運 CA，見 [OpenSSH 內建 CA 的 SSH 憑證導入](/infra/03-network-foundation/openssh-ca-setup/)。
  - 再加 `enable-oslogin-2fa=TRUE` 要求每次登入多一次第二因素，同樣先對單一 VM 設定驗證，連不上時改回 `FALSE`。付出的是每一位登入者的 Google 帳號都要先啟用兩步驟驗證，沒有啟用的會登不進去；而 OS Login 文件寫明兩步驟驗證不套用在服務帳號上，CI 這類登入者不受它約束（OS Login 文件，這次沒有實跑）。換到的是帳號密碼或本機的 refresh token 外洩時，登入還要第二因素（推論，這次沒有實跑）。

## 建 Cloud NAT 並移除外部 IP

Cloud NAT 承接沒有外部 IP 的 VM 往外的連線，建在 Cloud Router 上，以 region 為單位生效。哪些出站連線改由 Cloud NAT 承接、哪些改走 Private Google Access，以及出站的驗證為什麼要在移除外部 IP 之後做，見概念篇〈拿掉外部 IP 之後的出站路徑：Cloud NAT 與 Private Google Access〉。

```bash
# 在 VM 所在的 region 建 Cloud Router，再在上面建 Cloud NAT（出站 IP 自動配發）
gcloud compute routers create <router-name> \
  --network=<network-name> --region=<region>
gcloud compute routers nats create <nat-name> \
  --router=<router-name> --region=<region> \
  --auto-allocate-nat-external-ips \
  --nat-all-subnet-ip-ranges

# 外部服務要求來源 IP 白名單時：先預留靜態 IP，NAT 改用它出站
gcloud compute addresses create <nat-ip-name> --region=<region>
gcloud compute routers nats create <nat-name> \
  --router=<router-name> --region=<region> \
  --nat-external-ip-pool=<nat-ip-name> \
  --nat-all-subnet-ip-ranges
```

- `<router-name>`、`<nat-name>`、`<nat-ip-name>`：自己取的資源名稱。
- `<region>`：VM 所在 zone 去掉最後的字母那一段，例如 zone `asia-east1-b` 對應 region `asia-east1`；VM 分布在幾個 region 就要各建一組。
- `--auto-allocate-nat-external-ips` 讓 GCP 自動配發出站用的外部 IP，這些 IP 可能變動；`--nat-external-ip-pool` 改用預留的靜態 IP。
- `--nat-all-subnet-ip-ranges` 讓這個 region 裡所有 subnet 都走這個 NAT，只想讓部分 subnet 出站時改用 `--nat-custom-subnet-ip-ranges` 逐一列出。

VM 要存取 Cloud Storage、Artifact Registry 這類 Google API 時，subnet 開啟 Private Google Access，就能用內部 IP 連到 Google API，不經過 Cloud NAT：

```bash
gcloud compute networks subnets update <subnet-name> \
  --region=<region> --enable-private-ip-google-access
```

`<subnet-name>` 用 `gcloud compute networks subnets list --filter="region:<region>"` 查；`default` 網路在每個 region 各有一個名為 `default` 的 subnet。

外部 IP 設定在 VM 網卡的 access config 上，`delete-access-config` 要靠名稱指定移除哪一個，而這個名稱依 VM 建立的方式不同，所以先查出來。對外提供服務的 VM 移除之前，要先把流量入口換到負載平衡器；只做管理用途的 VM 可以直接移除。先在一台 VM 上移除、確認，再做其餘的 VM：

```bash
# 查 VM 第一張網卡的 access config 名稱
gcloud compute instances describe <instance-name> --zone=<zone> \
  --format="get(networkInterfaces[0].accessConfigs[0].name)"

# 用查到的名稱移除外部 IP
gcloud compute instances delete-access-config <instance-name> --zone=<zone> \
  --access-config-name="<access-config-name>"
```

移除之後經由 IAP 連進這台 VM，執行 `curl -s https://ifconfig.me` 印出出站時對方看到的來源 IP；那個 IP 列在 `gcloud compute routers get-nat-ip-info <router-name> --region=<region>` 的清單裡，就代表出站走了 Cloud NAT。這次實測 `--auto-allocate-nat-external-ips` 配到的 IP 正好是這台 VM 剛釋放的外部 IP，移除前後 `curl` 印出同一個 IP，`gcloud compute addresses list` 的 `PURPOSE` 欄是 `NAT_AUTO`，所以判斷依據是那份清單，而不是移除前後的 IP 有沒有變。連不到網際網路時，用 `gcloud compute instances add-access-config <instance-name> --zone=<zone>` 把外部 IP 加回去，再回頭查 Cloud NAT 的 region 與 subnet 設定。

- **沒做時**（保留外部 IP）：管理通道已經只放行 IAP，SSH 照樣安全；外部 IP 仍讓 VM 的其他 port 只靠防火牆擋，而防火牆規則一寫寬，那台 VM 就直接暴露（照規則的作用推論，這次沒有實跑）。Security Command Center 有標出帶公開 IP 的資源的 finding 類別，VM 不需要對外時移除之後少一類要處理的 finding（Security Health Analytics 文件）。
- **替代做法**：
  - 反過來先移除 IP、再建 NAT，換到的是驗證不受外部 IP 干擾，付出的是移除到 NAT 建好之間 VM 連不到網際網路，`apt update` 這類操作會失敗（推論，這次沒有實跑）。
  - 不建 Cloud NAT、只開 Private Google Access，換到的是不經過 NAT、不產生 NAT 的閘道時數與資料處理費，付出的是 VM 只連得到 Google API，連不到外部的套件來源與第三方 API（Cloud NAT 定價與 Private Google Access 文件，這次沒有實跑）。
  - 用 `--nat-external-ip-pool` 改用預留的靜態 IP，換到的是外部服務可以把這個固定的 IP 列進白名單；Cloud NAT 定價頁寫明 NAT 使用的外部 IP 不論靜態或自動配發都按 IP 計費，差別在靜態 IP 從 NAT 拿下來之後仍然保留在專案裡、要另外釋放（Cloud NAT 定價與 IP 位址文件，這次沒有實跑）。

移除之後，這台 VM 只剩 IAP 一條管理路徑，連線一律加 `--tunnel-through-iap`；救援入口是〈準備救援入口：Serial Console 與本機救援帳號〉建好的那一條。
