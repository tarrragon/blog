---
title: "GCP VM 的 SSH 與 RDP 管理通道：從預設的全開規則改走 IAP TCP forwarding"
date: 2026-10-23
description: "GCP 預設網路自帶的防火牆規則、IAP TCP forwarding 的連線路徑與來源範圍、切換前的盤點與救援準備、SSH 與 RDP 改走 IAP 並停用舊規則驗證的指令，以及 IAM 授權範圍、OS Login 的啟用與還原、Cloud NAT 與 Private Google Access、Organization Policy、階層式防火牆與稽核紀錄在 GCP 上的設定"
weight: 5
tags: ["infra", "network", "gcp", "ssh", "iap", "firewall"]
---

這篇整理 GCP Compute Engine 上管理員登入 VM 的通道（Linux 的 SSH、Windows 的 RDP），從防火牆對 `0.0.0.0/0` 開放 22 與 3389 port 改成走 Identity-Aware Proxy（IAP）TCP forwarding 的設定與指令。範圍從專案裡已經有 VM、而且用的是預設網路（`default` network）開始；自建網路上手寫的全開規則，處理方式相同，只要把指令裡的網路名稱與規則名稱換成自己的。IAP 這一類代理服務的共通機制見 [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/)。

管理通道為什麼要收斂、它拆成哪幾層、各層有哪些與廠商無關的做法，在[伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/)。本篇是那套模型在 GCP 上的一種組合：

| 管理通道的層 | 本篇在 GCP 上的做法                                       |
| ------------ | --------------------------------------------------------- |
| 網路可達性   | 防火牆只放行 IAP 的來源位址段，VM 移除外部 IP             |
| 通道授權     | Google 帳號加 IAM role `roles/iap.tunnelResourceAccessor` |
| 主機登入驗證 | Linux 用 OS Login；Windows 用 VM 上的 Windows 帳號        |

三層之外的救援入口用 Serial Console，它是繞過這三層的另一條路徑。

這個組合假設組織的身分提供者（identity provider，IdP）是 Google 帳號：IAP 與 OS Login 都依 Google 的 IAM 判斷。組織用的是 Microsoft Entra ID、Okta 這類其他 IdP 時，通道授權要換成能接那個 IdP 的代理服務，網路可達性也跟著那個代理走（防火牆改放行它的位址段，或改用不開入站 port 的反向連線）；本篇的 Cloud NAT、移除外部 IP 與救援入口的做法仍然適用。

## 預設網路自帶的防火牆規則

專案第一次啟用 Compute Engine API 時，GCP 會自動建一個叫 `default` 的 auto-mode VPC，並在上面預先建好四條入站規則。這四條規則的設計目標是讓第一次用 GCP 的人開完 VM 就連得上，所以來源範圍放得很寬。

| 規則名稱                 | 放行內容                            | 來源範圍       |
| ------------------------ | ----------------------------------- | -------------- |
| `default-allow-ssh`      | tcp:22                              | `0.0.0.0/0`    |
| `default-allow-rdp`      | tcp:3389                            | `0.0.0.0/0`    |
| `default-allow-icmp`     | ICMP                                | `0.0.0.0/0`    |
| `default-allow-internal` | 同網路內 TCP、UDP 所有 port 與 ICMP | `10.128.0.0/9` |

GCP 的防火牆規則依 priority 數字由小到大評估。這四條的 priority 是 65534，只排在 VPC 隱含的「拒絕所有入站」規則（65535）前面，所以自己建立的規則（不指定時是 1000）都會比它們先被評估。它們也沒有指定 target tag（防火牆規則用來挑選作用對象的標記），作用對象是這個網路裡的每一台 VM。

只收掉 `default-allow-ssh` 會留下兩個暴露面。`default-allow-rdp` 讓每一台 Windows VM 的遠端桌面對整個網際網路開放，而 RDP 預設接受密碼登入。`default-allow-internal` 讓同一個網路裡的 VM 之間不受 port 限制，一台 VM 被入侵之後，攻擊者從那台機器能直接連到其他 VM 的資料庫 port 與管理 port，這種擴散方式叫[橫向移動（lateral movement）](/backend/knowledge-cards/lateral-movement/)。另外，這四條自動建立的規則預設沒有開啟 firewall rules logging，防火牆這一層不會留下被掃描或被連入的紀錄。管理 port 對外開放的風險（sshd 漏洞、金鑰的生命週期、RDP 的密碼登入）與廠商無關，見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈對外開放管理 port 的實際風險〉。

CIS Google Cloud Platform Foundation Benchmark 的 3.1 條因此建議專案裡不保留 `default` 網路，改用自己規劃 subnet 的 custom-mode VPC。已經有服務跑在 `default` 網路上的專案，可以先收斂這四條規則，搬遷網路排進另一次變更。

列出專案目前在 `default` 網路上的規則，`--format` 讓 `gcloud` 把來源範圍與 target tag 兩欄加進輸出（預設表格沒有這兩欄）：

```bash
# 列出 default 網路上的防火牆規則，含來源範圍、放行內容與 target tag
gcloud compute firewall-rules list --filter="network:default" \
  --format="table(name,priority,sourceRanges.list():label=SRC_RANGES,allowed[].map().firewall_rule().list():label=ALLOW,targetTags.list():label=TARGET_TAGS,disabled)"
```

輸出裡要看 `SRC_RANGES` 欄是 `0.0.0.0/0` 的列，以及 `TARGET_TAGS` 欄是空白的列——空白代表規則套用到整個網路的每一台 VM。從 Security Command Center 的 `OPEN_SSH_PORT` 或 `OPEN_RDP_PORT` finding 進來的，finding 裡寫著被標記的那條規則的資源名稱，以那個名稱替換本篇指令裡的 `default-allow-ssh`；網路不是 `default` 時，把 `--filter` 裡的網路名稱一起換掉。

## IAP TCP forwarding 的連線路徑與來源範圍

IAP TCP forwarding 是 GCP 的身分感知代理：管理員的 `gcloud` 先用 HTTPS 連到 Google 的 IAP 端點，IAP 檢查這個 Google 帳號有沒有開通道的 IAM 權限，通過之後由 IAP 從 `35.235.240.0/20` 這段位址連到 VM 的內部 IP 與指定 port，再把兩端的位元組來回轉送。

一條連線因此由兩個元件各檢查一次，分別對應通道授權與主機登入驗證：

| 驗證位置 | 由誰檢查                                | 檢查什麼                                                                   |
| -------- | --------------------------------------- | -------------------------------------------------------------------------- |
| IAP 端點 | Google IAM                              | 這個 Google 帳號在這個 VM 上有沒有 `iap.tunnelInstances.accessViaIAP` 權限 |
| VM 內部  | Linux 上的 sshd／Windows 的遠端桌面服務 | SSH 金鑰在不在授權清單裡（metadata 金鑰或 OS Login）／Windows 帳號密碼     |

IAP 只決定是否允許開通道，開了通道之後登入 VM 仍然要過 VM 自己的認證，所以兩者要分開設定、分開稽核。

`35.235.240.0/20` 是 Google 文件公開的 IAP TCP forwarding 來源範圍，裡面包含 IAP 轉送時使用的全部位址。IPv6 的 VM 要另外放行 `2600:2d00:1:7::/64`；auto-mode 的 `default` 網路只有 IPv4 subnet，IPv6 的規則只在自建、開了 dual-stack subnet 的 custom-mode VPC 上用得到。這兩段位址是 Google 定義的規格值，每個專案都相同，可以直接寫進防火牆規則；Google 調整範圍時以 [IAP TCP forwarding 文件](https://cloud.google.com/iap/docs/using-tcp-forwarding)為準。

IAP 通道的代價在傳輸速度：所有位元組都經過 Google 的轉送，傳大檔案比直連慢，大量傳檔適合改用 Cloud Storage 當中轉。

## 切換前的盤點：舊規則現在放行了哪些連線

`default-allow-ssh` 放行的不只是管理員本人的 SSH。CI 或部署腳本用外部 IP 直連 VM、Ansible 這類設定管理工具、監控程式的探測、第三方廠商的維護連線，都可能經過這條規則，而刪掉它的那一刻，這些連線會和管理員的一起被拒絕。預設規則又沒有開 logging，所以手上沒有紀錄可以查出它們。

盤點的做法是先對舊規則開啟 logging，觀察一段涵蓋完整部署週期的時間，再從紀錄裡列出所有來源 IP：

```bash
# 對舊規則開啟 logging，之後每一次放行都會寫進 Cloud Logging
gcloud compute firewall-rules update default-allow-ssh --enable-logging
gcloud compute firewall-rules update default-allow-rdp --enable-logging

# 觀察一段時間後，列出經由舊規則連進來的來源 IP 與次數
gcloud logging read \
  'logName:"compute.googleapis.com%2Ffirewall" AND jsonPayload.rule_details.reference:"default-allow-ssh"' \
  --freshness=7d --format="value(jsonPayload.connection.src_ip)" | sort | uniq -c
```

`--freshness=7d` 是查詢往回看的時間長度，依自己的部署週期調整，要涵蓋到一次完整的部署與排程工作。來源 IP 裡不是管理員電腦的那些，要先改走 IAP 才能停用舊規則：CI 與自動化工具用服務帳號開 IAP 通道（`gcloud compute ssh --tunnel-through-iap` 同樣適用於服務帳號），權限範圍見〈IAP 的 IAM 授權範圍：誰拿得到通道〉。

## 切換到 IAP 的順序

`default-allow-ssh` 的來源 `0.0.0.0/0` 本身就涵蓋 IAP 的位址段，所以舊規則還在的時候，經由 IAP 的連線成功，可能是舊規則放行的，證明不了新規則寫對了。驗證新規則因此要先停用舊規則；而停用舊規則的那一刻，從公開網際網路來的 SSH 與 RDP 都會被拒絕，包括管理員自己的連線。舊規則掩蓋新規則、停用舊規則會切斷公開來源的連線，切換的順序由這兩點決定：救援入口（下一節的 Serial Console 與救援帳號）要在停用之前準備好，新規則與 IAM 權限要在停用之前建好，確認新路徑可用才刪除舊規則。與廠商無關的推導見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈切換管理通道時避免把自己鎖在外面〉。

### 準備救援入口：Serial Console 與救援帳號

GCP 的 [Serial Console](/infra/knowledge-cards/serial-console/) 透過 VM 的虛擬序列埠提供登入，不經過 VM 作業系統的網路設定與 sshd，在防火牆 tag 漏加、sshd 設定改壞、OS Login 設錯、磁碟滿導致 sshd 起不來時當作救援入口。它用 VM 內的本機帳號密碼登入，與 metadata 金鑰、OS Login 都無關，所以救援帳號要在 VM 還正常時就建好：

```bash
# 在每台 Linux VM 上建一個設了密碼的本機救援帳號（RHEL 系把 sudo 群組換成 wheel）
sudo useradd -m rescue && sudo passwd rescue && sudo usermod -aG sudo rescue
```

`rescue` 是自己取的帳號名稱，密碼存在團隊的密碼管理工具裡。Windows VM 的序列主控台（Special Administration Console）用 Windows 的本機管理員帳號登入，同樣要事先確認那個帳號的密碼在手上。

Serial Console 的互動登入預設關閉，平時保持關閉，救援時才對單一 VM 開啟：

```bash
# 救援時對單一 VM 開啟 Serial Console 並連上
gcloud compute instances add-metadata <instance-name> --zone=<zone> --metadata serial-port-enable=TRUE
gcloud compute connect-to-serial-port <instance-name> --zone=<zone>

# 救援結束後關回去
gcloud compute instances add-metadata <instance-name> --zone=<zone> --metadata serial-port-enable=FALSE
```

`<instance-name>` 與 `<zone>` 用 `gcloud compute instances list` 查，第一欄是 VM 名稱、第二欄是 zone。連 Serial Console 需要能修改這台 VM 的權限（例如 `roles/compute.instanceAdmin.v1`）。救援入口平時保持關閉的理由見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈救援入口：管理通道斷掉時的備用路徑〉。

### 啟用 IAP API 並建立只放行 IAP 來源的防火牆規則

IAP 端點以 API 的形式在專案上開關，沒有啟用時，`--tunnel-through-iap` 的連線在 IAP 端點那一步就開不起來：

```bash
# 啟用 IAP API（每個專案一次）
gcloud services enable iap.googleapis.com
```

新規則只開需要的 port，並用 target tag 限定作用的 VM。把 `--rules` 寫成 `all` 並省略 `--target-tags`，IAP 來源就連得到網路裡每一台 VM 的每一個 port，等於把 `default-allow-internal` 的寬度複製給 IAP。

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

各引數要填的內容：

- `allow-ssh-from-iap`、`allow-rdp-from-iap`：規則名稱，自己取，同一個專案裡不能重複。
- `<network-name>`：VM 所在的 VPC 名稱，預設網路就是 `default`，自建網路用 `gcloud compute networks list` 查。
- `<ssh-via-iap-tag>`、`<rdp-via-iap-tag>`：自己取的 network tag 名稱，例如 `ssh-iap`、`rdp-iap`。network tag 是掛在 VM 上的標記，防火牆規則的 target tag 比對的就是它，所以只有帶這個 tag 的 VM 會套用這條規則。SSH 與 RDP 用不同的 tag，Linux VM 就不會被順便開了 3389。
- `--enable-logging`：讓防火牆把這條規則的每一次放行寫進 Cloud Logging，驗證新規則與之後稽核都要用到。
- `--source-ranges` 與 `--rules` 是固定值。這兩條規則沒有寫 `--priority`，預設是 1000，比 `default-allow-ssh` 的 65534 先被評估。

自建的 custom-mode VPC 有 IPv6 VM 時，再建一條名稱不同（例如 `allow-ssh-from-iap-v6`）、`--source-ranges=2600:2d00:1:7::/64`、其餘引數相同的規則。

接著對每台 VM 加上對應的 tag：

```bash
# 對 Linux VM 加上 SSH 用的 tag、對 Windows VM 加上 RDP 用的 tag
gcloud compute instances add-tags <instance-name> --zone=<zone> --tags=<ssh-via-iap-tag>
gcloud compute instances add-tags <windows-instance-name> --zone=<zone> --tags=<rdp-via-iap-tag>
```

VM 分布在不同 zone 時，逐台以各自的 `--zone` 執行。

### 授予開通道的 IAM 權限

開通道的權限是 IAM role `roles/iap.tunnelResourceAccessor`。下面的指令把它綁在專案層級，並用 IAM Conditions 限定可以連的 port；條件的寫法依環境選一種：

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
```

- `<project-id>`：VM 所在的專案 ID，用 `gcloud config get-value project` 查目前設定的是哪一個。
- `<admin-email>`：要給權限的人的 Google 帳號；給一群人時把 `user:` 換成 `group:` 加 Google Group 的位址，人員異動就在群組裡處理，不必改 IAM。
- `<vm-internal-ip>`：VM 的內部 IP，`gcloud compute instances list` 的 `INTERNAL_IP` 欄查得到。
- `title`：這個條件的顯示名稱，自己取，會出現在 IAM 頁面上，用來辨認這條綁定。

Linux VM 的 `gcloud compute ssh` 還需要 VM 端的登入權限，而它依 OS Login 有沒有啟用而不同。還沒啟用 OS Login 時，`gcloud compute ssh` 會把管理員的公鑰寫進專案或 VM 的 metadata，所以非 Owner 的帳號需要修改 metadata 的權限（例如 `roles/compute.instanceAdmin.v1`），VM 掛著服務帳號時另外需要那個服務帳號的 `roles/iam.serviceAccountUser`。已經啟用 OS Login 時，改由 OS Login 的登入角色決定，授予方式見本篇〈SSH 金鑰在 GCP 上的管理位置：metadata 與 OS Login〉。兩種情形都需要讀取 VM 與專案資訊的權限（例如 `roles/compute.viewer`）。

### 停用舊規則，用 IAP 驗證新規則

先在舊規則還在時，每一位管理員各自經由 IAP 連一次，確認 IAM 權限：

```bash
# Linux：透過 IAP 通道 SSH 進 VM
gcloud compute ssh <instance-name> --zone=<zone> --tunnel-through-iap

# Windows：把 VM 的 3389 port 經 IAP 轉到本機，再用 RDP 用戶端連 localhost:3389
gcloud compute start-iap-tunnel <windows-instance-name> 3389 --local-host-port=localhost:3389 --zone=<zone>
```

加上 `--tunnel-through-iap` 時，`gcloud` 改走 IAP、不連 VM 的外部 IP；VM 還有外部 IP 時，少了這個參數的連線走的是舊路徑。這一輪連線驗證的是 IAM：IAP 端點會拒絕沒有權限的帳號。防火牆規則與 tag 這一輪驗不到，因為舊規則的 `0.0.0.0/0` 也放行 IAP 的位址段。

接著停用舊規則（規則仍在，只是不生效），由一位管理員對 Linux 與 Windows 各一台 VM 再連一次：

```bash
# 停用舊規則，再經由 IAP 連一次（Windows 照上面的 start-iap-tunnel 再連一次）
gcloud compute firewall-rules update default-allow-ssh --disabled
gcloud compute firewall-rules update default-allow-rdp --disabled
gcloud compute ssh <instance-name> --zone=<zone> --tunnel-through-iap
```

這一次連得上，代表放行連線的是新規則，因為涵蓋 IAP 位址段的舊規則已經停用；這個推論的前提是專案裡沒有其他來源涵蓋 `35.235.240.0/20` 的允許規則，〈預設網路自帶的防火牆規則〉那一節列出規則的指令可以確認這一點。新規則與 tag 是同一個 VPC 網路裡所有 VM 共用的設定，所以 Linux 與 Windows 各驗一台，就驗過了這條規則與 tag 對同類 VM 的效果；IAM 權限則是每個人各自的，由前一輪每位管理員各連一次驗過。新規則建立時加了 `--enable-logging`，也可以查防火牆紀錄確認命中的是哪一條規則：

```bash
# 查最近一小時經由 IAP 規則放行的連線
gcloud logging read \
  'logName:"compute.googleapis.com%2Ffirewall" AND jsonPayload.rule_details.reference:"allow-ssh-from-iap"' \
  --freshness=1h --limit=10
```

連不上時，用下面的指令把舊規則恢復，回頭查 tag 是否加在 VM 上、新規則的網路與 port 是否正確。防火牆規則透過 GCP 的 API 修改，SSH 連不上也改得回來：

```bash
# 只在停用後連不上時執行：恢復舊規則
gcloud compute firewall-rules update default-allow-ssh --no-disabled
gcloud compute firewall-rules update default-allow-rdp --no-disabled
```

### 刪除對外開放的規則

```bash
# SSH 與 RDP 都在舊規則停用的狀態下驗證過之後，刪掉這兩條規則
gcloud compute firewall-rules delete default-allow-ssh default-allow-rdp
```

刪除之後才發現有漏掉的連線來源時，可以照原樣把規則建回來，再回頭處理：

```bash
# 緊急恢復：重建與預設規則相同內容的 SSH 規則
gcloud compute firewall-rules create default-allow-ssh --network=default \
  --direction=INGRESS --action=allow --rules=tcp:22 --source-ranges=0.0.0.0/0 --priority=65534
```

`default-allow-internal` 要先確認 VM 之間實際需要哪些 port（應用連資料庫、節點之間的叢集通訊）再改成具體的規則，直接刪掉會中斷那些服務之間的連線。改法是為每一組需要的連線各建一條規則，例如應用連 PostgreSQL：

```bash
# 只放行帶 app tag 的 VM 連到帶 db tag 的 VM 的 5432 port
gcloud compute firewall-rules create allow-app-to-db --network=default \
  --direction=INGRESS --action=allow --rules=tcp:5432 \
  --source-tags=<app-tag> --target-tags=<db-tag>
```

`<app-tag>`、`<db-tag>` 是自己取的 tag，加在應用與資料庫 VM 上；`tcp:5432` 換成實際的服務 port。每一組需要的連線都建好之後，再刪 `default-allow-internal`。`default-allow-icmp` 的處理看用途：監控或除錯流程會用 `ping` 確認 VM 存活時，保留並把來源縮到內部網段與監控主機（`gcloud compute firewall-rules update default-allow-icmp --source-ranges=10.128.0.0/9,<monitoring-host-ip>/32`）；沒有這種用途就一起刪除。

用 Terraform 等 IaC 工具管防火牆的專案，這些新增、修改與刪除都要寫回程式碼；IaC 工具下一次執行 apply 時，會依程式碼把仍然存在的規則建回來（[drift](/infra/knowledge-cards/drift/)）。

## IAP 的 IAM 授權範圍：誰拿得到通道

改走 IAP 之後，VM 的連線權限改由 IAM 決定，所以 IAM policy 的寬度就是 SSH 與 RDP 的暴露面。三個地方會讓這個範圍在不知不覺中變大：

- **專案層級的基本角色**：Owner 這一類基本角色涵蓋開通道的權限，而且不受 IAM Conditions 限制。綁定之前先用 `gcloud projects get-iam-policy <project-id>` 列出目前持有基本角色的成員，再用 IAM 的 Policy Troubleshooter 確認某個帳號實際拿不拿得到 `iap.tunnelInstances.accessViaIAP`；`get-iam-policy` 只列出直接綁定，群組與繼承來的權限以 Policy Troubleshooter 的結果為準。
- **整批授權**：把 `roles/iap.tunnelResourceAccessor` 綁給 `domain:` 或大型群組，等於讓整個組織的帳號都能開通道。綁給負責維運的群組，並用 IAM Conditions 限定 port 與 VM。
- **服務帳號**：CI 或自動化工具用的服務帳號若持有通道權限，它的金鑰外洩就等同一把能連進所有 VM 的鑰匙。GCP 上這類帳號用 Workload Identity Federation 取得短期存取憑證，不發長期金鑰；原理與 AWS 上用 OIDC 換取 IAM role 短期憑證的做法相同，見[身分與存取憑證地基 — IAM 模型、OIDC 短期憑證與權限邊界設計](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)的〈OIDC：給 CI/CD 的短期憑證〉。

通道授權改用 Google 帳號之後，帳號被釣魚，攻擊者就能從 IAP 開通道。GCP 上的對應設定是在 Google Workspace 或 Cloud Identity 對能開通道的帳號強制兩步驟驗證，管理員帳號用硬體安全金鑰或 passkey 這類防釣魚的方式——一次性驗證碼會在釣魚頁面上被一起騙走。需要再收緊時，Context-Aware Access 可以在 IAM 綁定上加 access level 條件（Access Context Manager 定義的一組連線條件，例如只允許公司管理的裝置或特定網段）。

## SSH 金鑰在 GCP 上的管理位置：metadata 與 OS Login

GCP 上把 SSH 公鑰交給 Linux VM 有兩種方式，分別對應[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)〈主機登入驗證的做法：SSH 金鑰怎麼發、怎麼收回〉裡的靜態公鑰與由中央服務動態提供公鑰：metadata 金鑰寫在專案或 VM 的 metadata（掛在專案或 VM 上的鍵值設定）裡，由 VM 上的 guest agent（GCP 映像檔內建、把 metadata 同步進 VM 的常駐程式）寫進 `authorized_keys`；[OS Login](/infra/knowledge-cards/os-login/) 依 Google 帳號與 IAM role 決定誰能登入、能不能用 sudo。兩者的機制與差別見 OS Login 卡，這一節處理啟用的順序與還原。

啟用 OS Login 之後，VM 不再接受 metadata 裡的金鑰，原本靠 metadata 金鑰登入的管理員會立刻連不進去。所以啟用之前先把登入角色授予每一位管理員；VM 掛著服務帳號時（`gcloud compute instances describe` 輸出的 `serviceAccounts` 欄不是空的，用主控台建立的 VM 預設會掛上 Compute Engine 預設服務帳號），每一位管理員另外需要那個服務帳號的 `roles/iam.serviceAccountUser`，否則啟用之後連不進去：

```bash
# 授予管理員 OS Login 的登入角色：一般登入與含 sudo 的兩種擇一
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<admin-email> --role=roles/compute.osLogin
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<admin-email> --role=roles/compute.osAdminLogin

# 查 VM 掛的服務帳號，並授予管理員使用它的權限
gcloud compute instances describe <instance-name> --zone=<zone> \
  --format="get(serviceAccounts[0].email)"
gcloud iam service-accounts add-iam-policy-binding <service-account-email> \
  --member=user:<admin-email> --role=roles/iam.serviceAccountUser
```

接著先對一台 VM 啟用，讓每一位非 Owner 的管理員各自用自己的帳號連通並確認 sudo 可用，再做專案層級。先在單一 VM 上啟用，是讓角色漏授這類錯誤只鎖住那一台；Owner 本身持有全部權限，只由 Owner 驗證會看不出漏授。

```bash
# 先對單一 VM 啟用，連通確認
gcloud compute instances add-metadata <instance-name> --zone=<zone> --metadata enable-oslogin=TRUE

# 確認之後在專案層級啟用（VM 層級的設定會蓋過專案層級）
gcloud compute project-info add-metadata --metadata enable-oslogin=TRUE

# 連不上時還原（修改 metadata 走 API，不需要登入 VM）
gcloud compute instances add-metadata <instance-name> --zone=<zone> --metadata enable-oslogin=FALSE
gcloud compute project-info add-metadata --metadata enable-oslogin=FALSE
```

單一 VM 上的 `enable-oslogin=TRUE` 在專案層級也啟用之後可以留著，兩者的值相同。OS Login 只作用在 Linux VM，Windows VM 的登入仍由 Windows 帳號決定。

OS Login 也可以要求登入時的兩步驟驗證（metadata 設 `enable-oslogin-2fa=TRUE`），讓每一次 SSH 登入都多一次 Google 帳號的第二因素。設定之前要確認每一位管理員的 Google 帳號都已啟用兩步驟驗證，沒有啟用的帳號會登不進去；同樣先對單一 VM 設定驗證，連不上時改回 `FALSE`。

帳號停用或角色移除之後，下一次登入就會失敗；已經建立的工作階段不受影響，處理離職或帳號外洩時，管理員要另外登入 VM 結束那個使用者的工作階段（systemd 的發行版用 `sudo loginctl terminate-user <username>`，`<username>` 是 OS Login 由 Google 帳號轉成的使用者名稱）。

## 拿掉外部 IP 之後的出站路徑：Cloud NAT 與 Private Google Access

Cloud NAT 承接沒有外部 IP 的 VM 往外的連線，`apt update`、`docker pull`、呼叫第三方 API 都靠它；它和 AWS 的 NAT Gateway 承擔同一件事，機制見 [NAT](/infra/knowledge-cards/nat/)。Cloud NAT 建在 Cloud Router（GCP 管理 VPC 路由的元件）上，以 region 為單位生效：

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

VM 要存取 Cloud Storage、Artifact Registry 這類 Google API 時，subnet 開啟 Private Google Access 就能用內部 IP 連到 Google API，不必經過 Cloud NAT，也不另收費：

```bash
# 讓 subnet 內沒有外部 IP 的 VM 用內部路徑存取 Google API
gcloud compute networks subnets update <subnet-name> \
  --region=<region> --enable-private-ip-google-access
```

`<subnet-name>` 用 `gcloud compute networks subnets list --filter="region:<region>"` 查；`default` 網路在每個 region 各有一個名為 `default` 的 subnet，VM 分布在幾個 region 就對每個 region 各執行一次。

移除外部 IP 之前確認兩件事。對外提供服務的 VM（網站、API）要先把流量入口換到負載平衡器，否則移除的當下服務就中斷，入口層的設計見[流量入口層 — 請求怎麼從使用者到達應用](/infra/03-network-foundation/traffic-entry-layer/)。只做管理用途的 VM，要先經由 IAP 連進去實際跑一次出站的指令（例如 `sudo apt update` 或 `curl -I https://example.com`）確認 Cloud NAT 通了。外部 IP 設定在 VM 網卡的 access config 上，`delete-access-config` 要靠名稱指定移除哪一個，而這個名稱依 VM 建立的方式不同，所以先查出來：

```bash
# 查 VM 第一張網卡的 access config 名稱
gcloud compute instances describe <instance-name> --zone=<zone> \
  --format="get(networkInterfaces[0].accessConfigs[0].name)"

# 用查到的名稱移除外部 IP
gcloud compute instances delete-access-config <instance-name> --zone=<zone> \
  --access-config-name="<access-config-name>"
```

移除之後，這台 VM 只剩 IAP 一條管理路徑，連線一律加 `--tunnel-through-iap`。

## 組織層級的護欄：Organization Policy 與階層式防火牆

`default` 網路與 `default-allow-ssh`、`default-allow-rdp` 這些預設規則，每個新建的專案都會重新長出來，所以單一專案的收斂只保護那一個專案。要讓組織裡的新專案不再帶著這些規則，在 Organization Policy 設定下面幾個 constraint。這一節的指令需要專案屬於一個 Organization 資源，執行者要有組織層級的權限（`roles/orgpolicy.policyAdmin` 與 `roles/compute.orgFirewallPolicyAdmin`）。

- `compute.skipDefaultNetworkCreation`：新專案不再自動建立 `default` 網路。
- `compute.vmExternalIpAccess`：只允許列在清單上的 VM 持有外部 IP，其餘 VM 建立時帶外部 IP 會被拒絕。
- `compute.requireOsLogin`：新建的專案與 VM 啟用 OS Login，任何層級都無法用 metadata 把它關掉；既有 VM 是否已啟用要另外盤點，而既有的管理員要先拿到 OS Login 的登入角色。
- `compute.disableSerialPortAccess`：關閉 Serial Console 的存取，讓救援入口平時保持關閉；救援時由持有組織政策權限的人對那個專案解除。

```bash
# 在組織層級強制布林型的 constraint（skipDefaultNetworkCreation、requireOsLogin、disableSerialPortAccess 同一種寫法）
gcloud resource-manager org-policies enable-enforce compute.skipDefaultNetworkCreation \
  --organization=<org-id>

# 救援時，對單一專案解除 Serial Console 的限制
gcloud resource-manager org-policies disable-enforce compute.disableSerialPortAccess \
  --project=<project-id>
```

`<org-id>` 用 `gcloud organizations list` 查。`compute.vmExternalIpAccess` 是清單型的 constraint，要用政策檔列出允許的 VM，寫法以 Organization Policy 文件為準。

階層式防火牆政策（hierarchical firewall policy）套用在組織或資料夾上，優先於專案的 VPC 防火牆規則評估。政策裡的規則依 priority 數字由小到大評估，命中 `allow` 或 `deny` 就停止，專案的規則不會再被看到；命中 `goto_next` 則把這條連線交給下一層（最終是專案的 VPC 規則）判斷。所以規則的相對 priority 決定結果：

- 交給專案判斷的 IAP 規則（來源 `35.235.240.0/20`，有 IPv6 VM 時加上 `2600:2d00:1:7::/64`；tcp:22 與 tcp:3389；動作 `goto_next`）priority 要比拒絕規則小，否則 IAP 的流量先被拒絕規則擋下。它用 `goto_next` 而不用 `allow`：`allow` 會讓 IAP 的位址段直接通到組織內每一台 VM，繞過專案用 target tag 做的收斂。
- VM 之間或從 VPN 進來的 SSH 需要保留時，它們的來源（內部網段、VPN 的位址段）同樣要有一條 priority 比拒絕規則小的 `goto_next` 規則，因為拒絕規則的 `0.0.0.0/0` 也涵蓋內部位址。
- 拒絕 `0.0.0.0/0` 連到 tcp:22 與 tcp:3389 的規則只涵蓋 IPv4，IPv6 要另寫一條拒絕 `::/0` 的規則，這兩條拒絕規則之間沒有先後依賴。

```bash
# 建立組織層級的防火牆政策，加入規則，再關聯到一個資料夾（之後再關聯到組織）
gcloud compute firewall-policies create --short-name=<policy-name> --organization=<org-id>

gcloud compute firewall-policies rules create 100 --firewall-policy=<policy-name> \
  --organization=<org-id> --direction=INGRESS --action=goto_next \
  --src-ip-ranges=35.235.240.0/20 --layer4-configs=tcp:22,tcp:3389

gcloud compute firewall-policies rules create 1000 --firewall-policy=<policy-name> \
  --organization=<org-id> --direction=INGRESS --action=deny \
  --src-ip-ranges=0.0.0.0/0 --layer4-configs=tcp:22,tcp:3389

gcloud compute firewall-policies associations create --firewall-policy=<policy-name> \
  --organization=<org-id> --folder=<folder-id>
```

`100`、`1000` 是規則的 priority，只要 `goto_next` 那幾條比拒絕規則小就行，中間留空號給之後要插入的規則。`<policy-name>` 是自己取的政策名稱。`--folder=<folder-id>` 把政策關聯到一個資料夾；組織與資料夾層級的政策影響其下每一個專案，先關聯到一個測試用的資料夾，確認既有服務沒有依賴被擋掉的路徑，再關聯到組織（拿掉 `--folder`）。

## 稽核與偵測：firewall log、Cloud Audit Logs 與 Security Command Center

三個來源各自記錄的是不同的事件：

- **firewall rules logging**：建規則時加的 `--enable-logging` 讓防火牆把每一次放行寫進 Cloud Logging，紀錄裡有來源 IP、目的 VM、port 與命中的規則名稱；查詢方式見〈停用舊規則，用 IAP 驗證新規則〉。經由 IAP 的連線，來源 IP 都是 IAP 的位址段，從這份紀錄看不出是哪個人。
- **Cloud Audit Logs**：在主控台「IAM 與管理 > 稽核記錄」裡為 Cloud Identity-Aware Proxy 開啟 Data Access 的資料讀取紀錄之後，每一次開通道都會留下發起的帳號與目標 VM——要知道是哪個人，靠的是這份紀錄。它只記錄開啟之後的連線，所以要在需要調查之前就開。開啟 Serial Console 的 metadata 修改屬於 Admin Activity 紀錄，預設就有。
- **Security Command Center**：它的 Security Health Analytics 會持續掃描組織內的防火牆規則，`OPEN_SSH_PORT` 與 `OPEN_RDP_PORT` 這兩類 finding 對應的就是對外開放 22 與 3389 的規則；規則刪除或縮小來源之後，下一次掃描會把對應的 finding 標為已解決。

AWS 上同類的盤點流程見 [Security Group 稽核與清理](/infra/03-network-foundation/security-group-audit-cleanup/)：兩邊都是先列出來源是 `0.0.0.0/0` 的規則，逐條確認有沒有服務依賴，再刪除或縮小來源。

## 延伸閱讀：與廠商無關的設計模型與 VPC 的分層規則

- → [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/)：跳板機、VPN、代理程式反向連線、SSH 憑證這些 GCP 以外的做法，以及依身分系統、主機位置與人員流動選擇組合的條件
- → [網路地基 — VPC、subnet 分層與 security group 設計](/infra/03-network-foundation/vpc-subnet-security-group/)：VPC 與 subnet 的分層與最小開放原則，本篇的防火牆規則是同一套原則在 GCP 上的寫法
