---
title: "GCP VM 的 SSH 管理通道：從預設的全開 SSH 規則改走 IAP TCP forwarding"
date: 2026-10-23
description: "GCP 預設網路自帶的防火牆規則、IAP TCP forwarding 的連線路徑與來源範圍、切換到 IAP 並驗證新規則的指令，以及 IAM 授權範圍、OS Login 的啟用順序、Cloud NAT 與 Private Google Access、Serial Console、Organization Policy、階層式防火牆與稽核紀錄在 GCP 上的設定"
weight: 5
tags: ["infra", "network", "gcp", "ssh", "iap", "firewall"]
---

這篇整理 GCP Compute Engine 上管理員登入 VM 的 SSH 通道，從防火牆對 `0.0.0.0/0` 開 22 port 改成走 Identity-Aware Proxy（IAP）TCP forwarding 的設定與指令。範圍從專案裡已經有 VM、而且用的是預設網路（`default` network）開始。IAP 這一類代理服務的共通機制見 [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/)。

管理通道為什麼要收斂、它拆成哪幾層、各層有哪些與廠商無關的做法，在[伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證與救援入口](/infra/03-network-foundation/management-access-channel/)。本篇是那套模型在 GCP 上的一種組合：

| 管理通道的層 | 本篇在 GCP 上的做法                                       |
| ------------ | --------------------------------------------------------- |
| 網路可達性   | 防火牆只放行 IAP 的來源位址段，VM 移除外部 IP             |
| 通道授權     | Google 帳號加 IAM role `roles/iap.tunnelResourceAccessor` |
| 主機登入驗證 | OS Login，依 Google 帳號與 IAM 決定登入與 sudo            |

三層之外的救援入口用 Serial Console，它是繞過這三層的另一條路徑。

Google 帳號在這個組合裡同時是通道授權與主機登入驗證的身分來源：IAP 與 OS Login 都依同一份 IAM 判斷。組織的 IdP 不是 Google 時，這兩層要一起重新設計；網路可達性（防火牆只放行代理位址、移除外部 IP）與救援入口的做法不受影響。

## 預設網路自帶的防火牆規則

專案第一次啟用 Compute Engine API 時，GCP 會自動建一個叫 `default` 的 auto-mode VPC，並在上面預先建好四條入站規則。這四條規則的設計目標是讓第一次用 GCP 的人開完 VM 就連得上，所以來源範圍放得很寬。

| 規則名稱                 | 放行內容                            | 來源範圍       |
| ------------------------ | ----------------------------------- | -------------- |
| `default-allow-ssh`      | tcp:22                              | `0.0.0.0/0`    |
| `default-allow-rdp`      | tcp:3389                            | `0.0.0.0/0`    |
| `default-allow-icmp`     | ICMP                                | `0.0.0.0/0`    |
| `default-allow-internal` | 同網路內 TCP、UDP 所有 port 與 ICMP | `10.128.0.0/9` |

這四條規則的 priority 都是 65534，只比 VPC 隱含的「拒絕所有入站」規則（65535）高一級，所以任何 priority 數字較小的規則都會先被評估。它們也沒有指定 target tag（防火牆規則用來挑選作用對象的標記），作用對象是這個網路裡的每一台 VM。

只收掉 `default-allow-ssh` 會留下兩個暴露面。`default-allow-rdp` 讓每一台 Windows VM 的遠端桌面對整個網際網路開放，而 RDP 預設接受密碼登入。`default-allow-internal` 讓同一個網路裡的 VM 之間不受 port 限制，一台 VM 被入侵之後，攻擊者從那台機器能直接連到其他 VM 的資料庫 port 與管理 port，這種擴散方式叫[橫向移動（lateral movement）](/backend/knowledge-cards/lateral-movement/)。另外，這四條自動建立的規則預設沒有開啟 firewall rules logging，防火牆這一層不會留下被掃描或被連入的紀錄。管理 port 對外開放的風險（sshd 漏洞、金鑰的生命週期、RDP 的密碼登入）與廠商無關，見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈對外開放管理 port 的實際風險〉。

CIS Google Cloud Platform Foundation Benchmark 的 3.1 條因此建議專案裡不保留 `default` 網路，改用自己規劃 subnet 的 custom-mode VPC。已經有服務跑在 `default` 網路上的專案，可以先收斂這四條規則，搬遷網路排進另一次變更。

列出專案目前在 `default` 網路上的規則，`--format` 把來源範圍與 target tag 兩欄加進輸出（預設表格沒有這兩欄）：

```bash
# 列出 default 網路上的防火牆規則，含來源範圍、放行內容與 target tag
gcloud compute firewall-rules list --filter="network:default" \
  --format="table(name,priority,sourceRanges.list():label=SRC_RANGES,allowed[].map().firewall_rule().list():label=ALLOW,targetTags.list():label=TARGET_TAGS,disabled)"
```

輸出裡要看 `SRC_RANGES` 欄是 `0.0.0.0/0` 的列，以及 `TARGET_TAGS` 欄是空白的列——空白代表規則套用到整個網路的每一台 VM。

## IAP TCP forwarding 的連線路徑與來源範圍

IAP TCP forwarding 是 GCP 的身分感知代理：管理員的 `gcloud` 先用 HTTPS 連到 Google 的 IAP 端點，IAP 檢查這個 Google 帳號有沒有開通道的 IAM 權限，通過之後由 IAP 從 `35.235.240.0/20` 這段位址連到 VM 的內部 IP 與指定 port，再把兩端的位元組來回轉送。

一條 SSH 連線因此由兩個元件各檢查一次，分別對應通道授權與主機登入驗證：

| 驗證位置 | 由誰檢查     | 檢查什麼                                                                   |
| -------- | ------------ | -------------------------------------------------------------------------- |
| IAP 端點 | Google IAM   | 這個 Google 帳號在這個 VM 上有沒有 `iap.tunnelInstances.accessViaIAP` 權限 |
| VM 內部  | VM 上的 sshd | 連線帶來的 SSH 金鑰在不在授權清單裡（metadata 金鑰或 OS Login）            |

IAP 只決定是否允許開通道，開了通道之後登入 VM 仍然要過 sshd 的金鑰認證，所以兩者要分開設定、分開稽核。

`35.235.240.0/20` 是 Google 文件公開的 IAP TCP forwarding 來源範圍，裡面包含 IAP 轉送時使用的全部位址；IPv6 的 VM 要另外放行 `2600:2d00:1:7::/64`。這兩段位址是 Google 定義的規格值，每個專案都相同，可以直接寫進防火牆規則；Google 調整範圍時以 [IAP TCP forwarding 文件](https://cloud.google.com/iap/docs/using-tcp-forwarding)為準。

IAP 的通道也有成本：所有位元組都經過 Google 的轉送，傳大檔案的速度比直連慢，大量傳檔適合改用 Cloud Storage 當中轉。IAP API 要在專案上啟用（`gcloud services enable iap.googleapis.com`）。

## 切換到 IAP 時避免把自己鎖在外面的順序

刪掉 `default-allow-ssh` 的那一刻起，所有從公開網際網路來的 SSH 連線都會被拒絕，包括管理員自己的那一條。所以 IAP 的防火牆規則與 IAM 權限要在舊規則還在的時候建好，先停用舊規則驗證新規則，確認之後才刪；這個順序的推導見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈切換管理通道時避免把自己鎖在外面〉。

### 建立只放行 IAP 來源的防火牆規則

新規則只開 SSH 需要的 tcp:22，並用 target tag 限定作用的 VM。把 `--rules` 寫成 `all` 並省略 `--target-tags`，IAP 來源就連得到網路裡每一台 VM 的每一個 port，等於把 `default-allow-internal` 的寬度複製給 IAP。

```bash
# 放行 IAP 的 IPv4 來源連到帶指定 tag 的 VM 的 22 port
gcloud compute firewall-rules create allow-ssh-from-iap \
  --network=<network-name> \
  --direction=INGRESS \
  --action=allow \
  --rules=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --target-tags=<ssh-via-iap-tag> \
  --enable-logging
```

各引數要填的內容：

- `allow-ssh-from-iap`：規則名稱，自己取，同一個專案裡不能重複。
- `<network-name>`：VM 所在的 VPC 名稱，預設網路就是 `default`，自建網路用 `gcloud compute networks list` 查。
- `<ssh-via-iap-tag>`：自己取的 network tag 名稱，例如 `ssh-iap`。network tag 是掛在 VM 上的標記，防火牆規則的 target tag 比對的就是它，所以只有帶這個 tag 的 VM 會套用這條規則。
- `--enable-logging`：讓這條規則的放行紀錄寫進 Cloud Logging，驗證新規則與之後稽核誰從 IAP 連進來都要用到。
- `--source-ranges` 與 `--rules` 是固定值。Windows VM 要用 RDP 時另建一條 `--rules=tcp:3389` 的規則，同樣限定 tag。
- 這條規則沒有寫 `--priority`，預設是 1000，比 `default-allow-ssh` 的 65534 先被評估。

有 IPv6 VM 的網路再建一條規則，名稱換一個（例如 `allow-ssh-from-iap-v6`），`--source-ranges` 改成 `2600:2d00:1:7::/64`，其餘引數相同。

接著對每台需要 SSH 的 VM 加上 tag：

```bash
# 對 VM 加上 network tag，讓上面那條規則作用到它
gcloud compute instances add-tags <instance-name> --zone=<zone> --tags=<ssh-via-iap-tag>
```

`<instance-name>` 與 `<zone>` 用 `gcloud compute instances list` 查，第一欄是 VM 名稱、第二欄是 zone。

### 授予開通道的 IAM 權限

開通道的權限是 IAM role `roles/iap.tunnelResourceAccessor`。下面的指令把它綁在專案層級，並用 IAM Conditions 把可以連的 port 限定為 22：

```bash
# 授予指定成員透過 IAP 開通道的權限，條件限定只能連 22 port
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<admin-email> \
  --role=roles/iap.tunnelResourceAccessor \
  --condition='expression=destination.port == 22,title=iap-ssh-only'
```

- `<project-id>`：VM 所在的專案 ID，用 `gcloud config get-value project` 查目前設定的是哪一個。
- `<admin-email>`：要給權限的人的 Google 帳號；給一群人時把 `user:` 換成 `group:` 加 Google Group 的位址，人員異動就在群組裡處理，不必改 IAM。
- `--condition` 的 `expression` 可以再加 `destination.ip == "<vm-internal-ip>"` 把範圍縮到特定 VM；`title` 是這個條件的顯示名稱，自己取，會出現在 IAM 頁面上，用來辨認這條綁定。

使用 `gcloud compute ssh` 的帳號另外需要讀取 VM 與專案資訊的權限（例如 `roles/compute.viewer`），以及 OS Login 的登入角色，授予方式見本篇〈SSH 金鑰在 GCP 上的管理位置：metadata 與 OS Login〉。

### 用 IAP 實際連一次，並停用舊規則驗證新規則

```bash
# 透過 IAP 通道 SSH 進 VM
gcloud compute ssh <instance-name> --zone=<zone> --tunnel-through-iap
```

`--tunnel-through-iap` 讓 `gcloud` 改走 IAP 而不連 VM 的外部 IP；VM 還有外部 IP 時，少了這個參數的連線走的是舊路徑。

這次連線驗證的是 IAM：IAP 端點會拒絕沒有權限的帳號。新的防火牆規則與 tag 它驗不到，因為 `default-allow-ssh` 的來源 `0.0.0.0/0` 也涵蓋 IAP 的位址段，tag 漏加或新規則寫錯時，這條連線照樣由舊規則放行。驗證新規則的做法是先停用舊規則，再連一次：

```bash
# 停用舊規則（規則仍在，只是不生效）
gcloud compute firewall-rules update default-allow-ssh --disabled

# 再透過 IAP 連一次；連不上就把舊規則恢復
gcloud compute ssh <instance-name> --zone=<zone> --tunnel-through-iap
gcloud compute firewall-rules update default-allow-ssh --no-disabled
```

最後一行只在連不上時執行。防火牆規則透過 GCP 的 API 修改，SSH 連不上也還原得回來。另一種驗證方式是在 Cloud Logging 查這次連線的 firewall log，確認命中的是 `allow-ssh-from-iap`；新規則的 priority 比舊規則先被評估，tag 正確時紀錄會落在新規則上。每個管理員都用自己的帳號在舊規則停用的狀態下連過一次，才代表 IAM 與 tag 都設對了。

### 刪除對外開放的規則

```bash
# 新規則確認可用之後，刪掉對全網際網路開放的 SSH 與 RDP 規則
gcloud compute firewall-rules delete default-allow-ssh default-allow-rdp
```

`default-allow-internal` 要先確認 VM 之間實際需要哪些 port（應用連資料庫、節點之間的叢集通訊）再改成具體的規則，直接刪掉會中斷那些服務之間的連線。`default-allow-icmp` 的處理看用途：監控或除錯流程會用 `ping` 確認 VM 存活時保留，但把來源改成內部網段與監控主機；沒有這種用途就一起刪除。

用 Terraform 等 IaC 工具管防火牆的專案，這些改動要寫回程式碼，否則下一次 `apply` 會把規則建回來（[drift](/infra/knowledge-cards/drift/)）。

## IAP 的 IAM 授權範圍：誰拿得到通道

改走 IAP 之後，VM 的連線權限改由 IAM 決定，所以 IAM policy 的寬度就是 SSH 的暴露面。三個地方會讓這個範圍在不知不覺中變大：

- **專案層級的基本角色**：Owner 這一類基本角色涵蓋開通道的權限，而且不受 IAM Conditions 限制。綁定之前先用 `gcloud projects get-iam-policy <project-id>` 列出目前持有基本角色的成員，再用 IAM 的 Policy Troubleshooter 確認某個帳號實際拿不拿得到 `iap.tunnelInstances.accessViaIAP`，以查詢結果為準。
- **整批授權**：把 `roles/iap.tunnelResourceAccessor` 綁給 `domain:` 或大型群組，等於讓整個組織的帳號都能開通道。綁給負責維運的群組，並用 IAM Conditions 限定 port 與 VM。
- **服務帳號**：CI 或自動化工具用的服務帳號若持有通道權限，它的金鑰外洩就等同一把能連進所有 VM 的鑰匙。GCP 上這類帳號用 Workload Identity Federation 取得短期存取憑證，原理與 AWS 上用 OIDC 換取 IAM role 短期憑證的做法相同，見[身分與存取憑證地基 — IAM 模型、OIDC 短期憑證與權限邊界設計](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)的〈OIDC：給 CI/CD 的短期憑證〉。

通道授權改用 Google 帳號之後，帳號被釣魚，攻擊者就能從 IAP 開通道。GCP 上的對應設定是在 Google Workspace 或 Cloud Identity 強制兩步驟驗證，管理員帳號優先用硬體安全金鑰；需要再收緊時，Context-Aware Access 可以在 IAM 綁定上加 access level 條件，例如只允許公司管理的裝置或特定網段的連線開通道。

## SSH 金鑰在 GCP 上的管理位置：metadata 與 OS Login

GCP 上把 SSH 公鑰交給 VM 有兩種方式，分別對應[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)〈主機登入驗證的做法：SSH 金鑰怎麼發、怎麼收回〉裡的靜態公鑰與由中央服務動態提供公鑰。metadata 金鑰把公鑰寫在專案或 VM 的 metadata（掛在專案或 VM 上的鍵值設定）裡，VM 上的 guest agent 讀出來寫進 `authorized_keys`；它和 Google 帳號沒有連動，成員離職後要有人記得去 metadata 刪掉他的公鑰。[OS Login](/infra/knowledge-cards/os-login/) 讓 VM 依 Google 帳號與 IAM 決定誰能登入：持有 `roles/compute.osLogin` 的帳號能以一般使用者登入，持有 `roles/compute.osAdminLogin` 的帳號另外拿得到 sudo。帳號停用或角色移除之後，下一次登入就會失敗；已經建立的工作階段不受影響，要另外在 VM 上中斷。

啟用 OS Login 之後，VM 不再接受 metadata 裡的金鑰，原本靠 metadata 金鑰登入的管理員會立刻連不進去。所以啟用前先把登入角色授予每一位管理員，再對一台 VM 啟用、連通並確認 sudo 可用，最後才做專案層級：

```bash
# 授予管理員 OS Login 的登入角色（需要 sudo 時改用 roles/compute.osAdminLogin）
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:<admin-email> --role=roles/compute.osLogin

# 先對單一 VM 啟用，用 gcloud compute ssh --tunnel-through-iap 連通確認
gcloud compute instances add-metadata <instance-name> --zone=<zone> \
  --metadata enable-oslogin=TRUE

# 確認之後在專案層級啟用（VM 層級的設定會蓋過專案層級）
gcloud compute project-info add-metadata --metadata enable-oslogin=TRUE
```

VM 以服務帳號身分執行時，登入的使用者另外需要那個服務帳號的 `roles/iam.serviceAccountUser`。OS Login 的登入角色要與 IAP 的通道角色分開授予：OS Login 的角色決定是否允許登入與使用 sudo，IAP 的角色決定是否允許開通道。OS Login 也可以加上登入時的兩步驟驗證（metadata 設 `enable-oslogin-2fa=TRUE`），讓每一次 SSH 登入都多一次帳號驗證。

## 拿掉外部 IP 之後的出站路徑：Cloud NAT 與 Private Google Access

VM 改走 IAP 之後可以移除外部 IP，而沒有外部 IP 的 VM 預設連不到網際網路，`apt update`、`docker pull`、呼叫第三方 API 都會逾時。GCP 上的出站做法是 Cloud NAT，它和 AWS 的 NAT Gateway 承擔同一件事，機制見 [NAT](/infra/knowledge-cards/nat/)。Cloud NAT 建在 Cloud Router 上，以 region 為單位生效：

```bash
# 在 VM 所在的 region 建 Cloud Router，再在上面建 Cloud NAT
gcloud compute routers create <router-name> \
  --network=<network-name> --region=<region>

gcloud compute routers nats create <nat-name> \
  --router=<router-name> --region=<region> \
  --auto-allocate-nat-external-ips \
  --nat-all-subnet-ip-ranges
```

- `<router-name>` 與 `<nat-name>`：自己取的資源名稱。
- `<region>`：VM 所在 zone 去掉最後的字母那一段，例如 zone `asia-east1-b` 對應 region `asia-east1`；VM 分布在幾個 region 就要各建一組。
- `--auto-allocate-nat-external-ips`：讓 GCP 自動配發出站用的外部 IP，這些 IP 可能變動。外部服務要求來源 IP 白名單時，改用預留的靜態 IP，以 `--nat-external-ip-pool` 指定。
- `--nat-all-subnet-ip-ranges`：讓這個 region 裡所有 subnet 都走這個 NAT，只想讓部分 subnet 出站時改用 `--nat-custom-subnet-ip-ranges` 逐一列出。

VM 要存取 Cloud Storage、Artifact Registry 這類 Google API 時，subnet 開啟 Private Google Access 就能用內部 IP 連到 Google API，不必經過 Cloud NAT，也不另收費：

```bash
# 讓 subnet 內沒有外部 IP 的 VM 用內部路徑存取 Google API
gcloud compute networks subnets update <subnet-name> \
  --region=<region> --enable-private-ip-google-access
```

`<subnet-name>` 用 `gcloud compute networks subnets list --filter="region:<region>"` 查。

出站路徑通了之後再移除外部 IP。外部 IP 設定在 VM 網卡的 access config 上，access config 的名稱要先查出來：

```bash
# 查 VM 第一張網卡的 access config 名稱
gcloud compute instances describe <instance-name> --zone=<zone> \
  --format="get(networkInterfaces[0].accessConfigs[0].name)"

# 用查到的名稱移除外部 IP
gcloud compute instances delete-access-config <instance-name> --zone=<zone> \
  --access-config-name="<access-config-name>"
```

對外提供服務的 VM（網站、API）移除外部 IP 之後，流量入口改由負載平衡器承接，入口層的設計見[流量入口層 — 請求怎麼從使用者到達應用](/infra/03-network-foundation/traffic-entry-layer/)。

## 救援入口：Serial Console

GCP 的 [Serial Console](/infra/knowledge-cards/serial-console/) 透過 VM 的虛擬序列埠提供登入，不經過 VM 作業系統的網路設定與 sshd，在防火牆 tag 漏加、sshd 設定改壞、磁碟滿導致 sshd 起不來時當作救援入口。

Serial Console 的互動登入預設關閉，對單一 VM 開啟用 metadata `serial-port-enable=TRUE`，存取權限由 IAM 控制。登入走 VM 內的本機帳號密碼，救援用帳號要在 VM 還正常時就建好；救援入口平時保持關閉的理由見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈救援入口：管理通道斷掉時的備用路徑〉。

## 組織層級的護欄：Organization Policy 與階層式防火牆

收斂 `default-allow-*` 規則、改走 IAP 這些改動只作用在一個專案上，下一個新建的專案仍然會自動長出 `default` 網路與 `default-allow-ssh`、`default-allow-rdp` 這些預設規則。要讓這件事在整個組織裡不再發生，在 Organization Policy 設定這幾個 constraint：

- `compute.skipDefaultNetworkCreation`：新專案不再自動建立 `default` 網路。
- `compute.vmExternalIpAccess`：只允許列在清單上的 VM 持有外部 IP，其餘 VM 建立時帶外部 IP 會被拒絕。
- `compute.requireOsLogin`：新建的專案與 VM 預設啟用 OS Login，任何層級都無法用 metadata 把它關掉；既有 VM 是否已啟用，要另外盤點。
- `compute.disableSerialPortAccess`：關閉 Serial Console 的存取；救援時再對特定專案解除，讓救援入口平時保持關閉。

階層式防火牆政策（hierarchical firewall policy）套用在組織或資料夾上，優先於專案的 VPC 防火牆規則評估，而它的規則命中 `allow` 或 `deny` 就停止評估，專案的規則不會再被看到。所以在組織或資料夾的政策裡依序寫三條：

1. 來源 `35.235.240.0/20`、tcp:22 與 tcp:3389、動作 `goto_next`：把 IAP 的流量交給專案的 VPC 規則依 tag 判斷。這一條用 `allow` 的話，IAP 的位址段會直接被放行到組織內每一台 VM，前面用 target tag 做的收斂全部被繞過。
2. 拒絕 `0.0.0.0/0` 連到 tcp:22 與 tcp:3389。
3. IPv6 另寫一條拒絕 `::/0` 的規則，`0.0.0.0/0` 只涵蓋 IPv4。

`0.0.0.0/0` 也涵蓋內部位址，VM 之間或從 VPN 進來的 SSH 需要的話，要在拒絕規則之前另外用 `goto_next` 交給專案規則。組織與資料夾層級的政策影響其下每一個專案，先套用在一個測試用的資料夾，確認既有服務沒有依賴被擋掉的路徑，再擴大範圍。

## 稽核與偵測：firewall log、IAP audit log 與 Security Command Center

GCP 上查「誰在什麼時候透過 IAP 連進哪台 VM」「誰開了 Serial Console」與「組織裡是否出現新的對外開放 22 port 的規則」，分別靠下面三個來源。

- **firewall rules logging**：建規則時加的 `--enable-logging` 讓每一次放行寫進 Cloud Logging，紀錄裡有來源 IP、目的 VM、port 與命中的規則名稱。
- **Cloud Audit Logs**：在 IAM 的 Audit Logs 設定裡為 IAP 開啟 Data Access 紀錄，每一次開通道都會留下發起的帳號與目標 VM；firewall log 只看得到來源是 IAP 的位址段，要知道是哪個人，得靠這份紀錄。開啟 Serial Console 的 metadata 修改與連線也記在 audit log 裡。
- **Security Command Center**：它的 Security Health Analytics 會持續掃描組織內的防火牆規則，`OPEN_SSH_PORT` 與 `OPEN_RDP_PORT` 這兩類 finding 對應的就是對外開放 22 與 3389 的規則，可以接告警。

AWS 環境的盤點方式見 [Security Group 稽核與清理](/infra/03-network-foundation/security-group-audit-cleanup/)：在 AWS 與 GCP 上都是先列出來源是 `0.0.0.0/0` 的規則，逐條確認有沒有服務依賴，再刪除或縮小來源。

## 延伸閱讀：管理通道的設計模型、網路分層與 IAM 權限設計

- → [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證與救援入口](/infra/03-network-foundation/management-access-channel/)：本篇每一節對應的那一層，以及跳板機、VPN、代理程式反向連線、SSH 憑證這些 GCP 以外的做法與選擇組合的條件
- → [網路地基 — VPC、subnet 分層與 security group 設計](/infra/03-network-foundation/vpc-subnet-security-group/)：最小開放原則與 subnet 分層，本篇的防火牆規則是同一套原則在 GCP 上的寫法
- → [Security Group 稽核與清理](/infra/03-network-foundation/security-group-audit-cleanup/)：AWS 上找出 `0.0.0.0/0` 規則與安全刪除的流程
- → [身分與存取憑證地基 — IAM 模型、OIDC 短期憑證與權限邊界設計](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)：通道授權改由 IAM 決定之後的最小權限，以及機器身分換取短期存取憑證的做法
