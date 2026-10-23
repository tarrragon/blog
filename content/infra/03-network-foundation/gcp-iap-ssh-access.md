---
title: "GCP VM 的 SSH 管理通道：從 default-allow-ssh 改走 IAP TCP forwarding"
date: 2026-10-23
description: "GCP 預設網路自帶的防火牆規則、IAP TCP forwarding 的連線路徑與來源範圍、切換到 IAP 的指令，以及 IAM 授權範圍、OS Login、Cloud NAT 與 Private Google Access、Serial Console、Organization Policy 與稽核紀錄在 GCP 上的設定"
weight: 5
tags: ["infra", "network", "gcp", "ssh", "iap", "firewall"]
---

這篇整理 GCP Compute Engine 上管理員登入 VM 的 SSH 通道，從防火牆對 `0.0.0.0/0` 開 22 port 改成走 Identity-Aware Proxy（IAP）TCP forwarding 的設定與指令。範圍從專案裡已經有 VM、而且用的是預設網路（`default` network）開始。

管理通道為什麼要收斂、它拆成哪幾層、各層有哪些與廠商無關的做法，在[伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證與救援入口](/infra/03-network-foundation/management-access-channel/)。本篇是那套模型在 GCP 上的一種組合：

| 管理通道的層 | 本篇在 GCP 上的做法                                       |
| ------------ | --------------------------------------------------------- |
| 網路可達性   | 防火牆只放行 IAP 的來源位址段，VM 移除外部 IP             |
| 通道授權     | Google 帳號加 IAM role `roles/iap.tunnelResourceAccessor` |
| 主機登入驗證 | OS Login，依 Google 帳號與 IAM 決定登入與 sudo            |
| 救援入口     | Serial Console                                            |

Google 帳號在這個組合裡是通道授權那一層的身分來源。換成其他 IdP 或其他廠商時，那一層換掉，其餘的設計方式不變。

## 預設網路自帶的防火牆規則

GCP 在建立專案時會自動建一個叫 `default` 的 auto-mode VPC，並在上面預先建好四條入站規則。這四條規則的設計目標是讓第一次用 GCP 的人開完 VM 就連得上，所以來源範圍放得很寬。

| 規則名稱                 | 放行內容                    | 來源範圍       |
| ------------------------ | --------------------------- | -------------- |
| `default-allow-ssh`      | tcp:22                      | `0.0.0.0/0`    |
| `default-allow-rdp`      | tcp:3389                    | `0.0.0.0/0`    |
| `default-allow-icmp`     | ICMP                        | `0.0.0.0/0`    |
| `default-allow-internal` | 同網路內所有協定、所有 port | `10.128.0.0/9` |

這四條規則的 priority 都是 65534，只比 VPC 隱含的「拒絕所有入站」規則（65535）高一級，所以任何 priority 數字較小的規則都能蓋過它們。它們也沒有指定 target tag，作用對象是這個網路裡的每一台 VM。

只收掉 `default-allow-ssh` 會留下兩個暴露面。`default-allow-rdp` 讓每一台 Windows VM 的遠端桌面對整個網際網路開放，而 RDP 預設接受密碼登入，被暴力嘗試的代價比 SSH 高。`default-allow-internal` 讓同一個網路裡的 VM 之間不受任何 port 限制，一台 VM 被入侵之後，攻擊者從那台機器能直接連到其他 VM 的資料庫埠與管理埠，這種擴散方式叫橫向移動（lateral movement）。另外，這四條自動建立的規則預設沒有開啟 firewall rules logging，被掃描或被連入都不會留下紀錄。管理 port 對外開放的風險（sshd 漏洞、金鑰的生命週期、RDP 的密碼登入）與廠商無關，見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈對外開放管理 port 的實際風險〉。

CIS Google Cloud Platform Foundation Benchmark 的 3.1 條因此建議專案裡不保留 `default` 網路，改用自己規劃 subnet 的 custom-mode VPC。已經有服務跑在 `default` 網路上的專案，可以先收斂這四條規則，搬遷網路排進另一次變更。

列出專案目前在 `default` 網路上的規則：

```bash
# 列出 default 網路上的所有防火牆規則，確認哪些自動規則還在
gcloud compute firewall-rules list --filter="network:default"
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

`35.235.240.0/20` 是 Google 文件公開的 IAP TCP forwarding 來源範圍，Google 不在公開網際網路上廣播這段位址的路由，所以外部主機無法偽造這個來源連進 VM。IPv6 的 VM 要另外放行 `2600:2d00:1:7::/64`。這兩段位址是 Google 定義的規格值，每個專案都相同，可以直接寫進防火牆規則；Google 調整範圍時以 [IAP TCP forwarding 文件](https://cloud.google.com/iap/docs/using-tcp-forwarding)為準。

IAP 的通道也有成本：所有位元組都經過 Google 的轉送，傳大檔案的速度比直連慢，大量傳檔適合改用 Cloud Storage 當中轉。IAP API 要在專案上啟用（`gcloud services enable iap.googleapis.com`），沒啟用時開通道會直接失敗。

## 切換到 IAP 時避免把自己鎖在外面的順序

刪掉 `default-allow-ssh` 的那一刻起，所有從公開網際網路來的 SSH 連線都會被拒絕，包括管理員自己的那一條。所以 IAP 的防火牆規則與 IAM 權限要在舊規則還在的時候建好並實際連通，才刪舊規則；這個順序的推導見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈切換管理通道時避免把自己鎖在外面〉。

### 建立只放行 IAP 來源的防火牆規則

新規則只開 SSH 需要的 tcp:22，並用 target tag 限定作用的 VM。只寫 `--source-ranges` 而省略 `--rules` 與 `--target-tags` 的寫法會讓 IAP 來源連得到網路裡每一台 VM 的每一個 port，等於把 `default-allow-internal` 的寬度複製給 IAP。

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

- `<network-name>`：VM 所在的 VPC 名稱，預設網路就是 `default`，自建網路用 `gcloud compute networks list` 查。
- `<ssh-via-iap-tag>`：自己取的 network tag 名稱，例如 `ssh-iap`。只有帶這個 tag 的 VM 會套用這條規則，所以要再對每台需要 SSH 的 VM 加上 tag：`gcloud compute instances add-tags <instance-name> --zone=<zone> --tags=<ssh-via-iap-tag>`。
- `--enable-logging`：讓這條規則的放行紀錄寫進 Cloud Logging，之後稽核誰在什麼時候從 IAP 連進來要用到。
- `--source-ranges` 與 `--rules` 是固定值，Windows VM 要用 RDP 時另建一條 `--rules=tcp:3389` 的規則，同樣限定 tag。

有 IPv6 VM 的網路再建一條同樣內容、來源改成 `2600:2d00:1:7::/64` 的規則。

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
- `--condition` 的 `expression` 可以再加 `destination.ip == "<vm-internal-ip>"` 把範圍縮到特定 VM。

使用 `gcloud compute ssh` 的帳號另外需要讀取 VM 資訊的 Compute Engine 權限，以及 OS Login 那一節說明的登入權限。

### 用 IAP 實際連一次

```bash
# 透過 IAP 通道 SSH 進 VM
gcloud compute ssh <instance-name> --zone=<zone> --tunnel-through-iap
```

`<instance-name>` 與 `<zone>` 用 `gcloud compute instances list` 查。`--tunnel-through-iap` 讓 `gcloud` 改走 IAP 而不連 VM 的外部 IP；VM 還有外部 IP 而且舊規則還在時，少了這個參數的連線走的是舊路徑，測試結果就驗證不到新通道。每個管理員都用自己的帳號連過一次，才代表 IAM 與 tag 都設對了。

### 刪除對外開放的規則

```bash
# 新通道確認可用之後，刪掉對全網際網路開放的 SSH 與 RDP 規則
gcloud compute firewall-rules delete default-allow-ssh default-allow-rdp
```

`default-allow-internal` 要先確認 VM 之間實際需要哪些 port（應用連資料庫、節點之間的叢集通訊）再改成具體的規則，直接刪掉會中斷那些服務之間的連線。`default-allow-icmp` 影響 `ping` 這類診斷，保留與否依團隊的除錯習慣決定。

用 Terraform 等 IaC 工具管防火牆的專案，這些改動要寫回程式碼，否則下一次 `apply` 會把規則建回來（[drift](/infra/knowledge-cards/drift/)）。

## IAP 的 IAM 授權範圍：誰拿得到通道

改走 IAP 之後，VM 的連線權限改由 IAM 決定，所以 IAM policy 的寬度就是 SSH 的暴露面。三個地方會讓這個範圍在不知不覺中變大：

- **專案層級的基本角色**：Owner 這一類基本角色涵蓋的權限非常廣。綁定之前先用 `gcloud projects get-iam-policy <project-id>` 列出目前持有基本角色的成員，再用 IAM 的 Policy Troubleshooter 確認某個帳號實際拿不拿得到 `iap.tunnelInstances.accessViaIAP`，以查詢結果為準。
- **整批授權**：把 `roles/iap.tunnelResourceAccessor` 綁給 `domain:` 或大型群組，等於讓整個組織的帳號都能開通道。綁給負責維運的群組，並用 IAM Conditions 限定 port 與 VM。
- **服務帳號**：CI 或自動化工具用的服務帳號若持有通道權限，它的金鑰外洩就等同一把能連進所有 VM 的鑰匙。GCP 上這類帳號用 Workload Identity Federation 取得短期憑證，原理與 AWS 的 OIDC 相同，見[模組二：身分與存取憑證地基](/infra/02-identity-credentials/)。

通道授權改用 Google 帳號之後，帳號被釣魚，攻擊者就能從 IAP 開通道。GCP 上的對應設定是在 Google Workspace 或 Cloud Identity 強制兩步驟驗證，管理員帳號優先用硬體安全金鑰；需要再收緊時，Context-Aware Access 可以在 IAM 綁定上加 access level 條件，例如只允許公司管理的裝置或特定網段的連線開通道。

## SSH 金鑰在 GCP 上的管理位置：metadata 與 OS Login

GCP 上把 SSH 公鑰交給 VM 有兩種方式，分別對應[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)裡的靜態公鑰與由中央服務動態提供公鑰。metadata 金鑰把公鑰寫在專案或 VM 的 metadata 裡，VM 上的 guest agent 讀出來寫進 `authorized_keys`；它和 Google 帳號沒有連動，成員離職後要有人記得去 metadata 刪掉他的公鑰。OS Login 讓 VM 依 Google 帳號與 IAM 決定誰能登入：持有 `roles/compute.osLogin` 的帳號能以一般使用者登入，持有 `roles/compute.osAdminLogin` 的帳號另外拿得到 sudo，帳號停用或角色移除之後登入權限立即消失。

```bash
# 在專案層級啟用 OS Login，專案內的 VM 改依 IAM 決定登入權限
gcloud compute project-info add-metadata --metadata enable-oslogin=TRUE

# 對單一 VM 啟用（VM 層級的設定會蓋過專案層級）
gcloud compute instances add-metadata <instance-name> --zone=<zone> \
  --metadata enable-oslogin=TRUE
```

OS Login 與 IAP 是互補的兩層：IAP 的 IAM 權限決定是否允許開通道，OS Login 的 IAM 權限決定進入通道之後是否允許登入、是否取得 sudo。VM 以服務帳號身分執行時，登入的使用者另外需要那個服務帳號的 `roles/iam.serviceAccountUser`。OS Login 也可以加上登入時的兩步驟驗證（metadata 設 `enable-oslogin-2fa=TRUE`），讓每一次 SSH 登入都多一次帳號驗證。

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

`<region>` 是 VM 所在 zone 去掉最後的字母那一段，例如 zone `asia-east1-b` 對應 region `asia-east1`；VM 分布在幾個 region 就要各建一組。`--nat-all-subnet-ip-ranges` 讓這個 region 裡所有 subnet 都走這個 NAT，只想讓部分 subnet 出站時改用 `--nat-custom-subnet-ip-ranges` 逐一列出。

VM 要存取 Cloud Storage、Artifact Registry 這類 Google API 時，subnet 開啟 Private Google Access 就能用內部 IP 連到 Google API，不必經過 Cloud NAT：

```bash
# 讓 subnet 內沒有外部 IP 的 VM 用內部路徑存取 Google API
gcloud compute networks subnets update <subnet-name> \
  --region=<region> --enable-private-ip-google-access
```

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

GCP 的 Serial Console 透過 VM 的虛擬序列埠提供登入，不經過網路與 sshd，在防火牆 tag 漏加、sshd 設定改壞、磁碟滿導致 sshd 起不來時當作救援入口。

Serial Console 的互動登入預設關閉，對單一 VM 開啟用 metadata `serial-port-enable=TRUE`，存取權限由 IAM 控制。登入走 VM 內的本機帳號密碼，救援用帳號要在 VM 還正常時就建好；救援入口平時保持關閉的理由見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈救援入口：管理通道斷掉時的備用路徑〉。

## 組織層級的護欄：Organization Policy 與階層式防火牆

前面的改動只作用在一個專案上，下一個新建的專案仍然會自動長出 `default` 網路與那四條規則。要讓這件事在整個組織裡不再發生，在 Organization Policy 設定這幾個 constraint：

- `compute.skipDefaultNetworkCreation`：新專案不再自動建立 `default` 網路。
- `compute.vmExternalIpAccess`：只允許列在清單上的 VM 持有外部 IP，其餘 VM 建立時帶外部 IP 會被拒絕。
- `compute.requireOsLogin`：組織內的 VM 一律啟用 OS Login，專案層級無法關掉。

階層式防火牆政策（hierarchical firewall policy）套用在組織或資料夾上，優先於專案層級的 VPC 防火牆規則評估。在那一層寫一條「拒絕 `0.0.0.0/0` 連到 tcp:22 與 tcp:3389」，並在它之前放行 `35.235.240.0/20`，專案裡就算有人再建一條對外開放 22 port 的規則也不會生效。

這一層的改動影響組織內每一個專案，先套用在一個測試用的資料夾，確認既有服務沒有依賴被擋掉的路徑，再擴大範圍。

## 稽核與偵測：firewall log、IAP audit log 與 Security Command Center

GCP 上查「誰在什麼時候透過 IAP 連進哪台 VM」與「組織裡是否出現新的對外開放 22 port 的規則」，分別靠下面三個來源。

- **firewall rules logging**：前面建規則時加的 `--enable-logging` 讓每一次放行寫進 Cloud Logging，紀錄裡有來源 IP、目的 VM 與 port。
- **IAP 的 Data Access audit log**：在 IAM 的 Audit Logs 設定裡為 IAP 開啟 Data Access 紀錄，每一次開通道都會留下發起的帳號與目標 VM。firewall log 只看得到來源是 IAP 的位址段，要知道是哪個人，得靠這份紀錄。
- **Security Command Center**：它的 Security Health Analytics 會持續掃描組織內的防火牆規則，`OPEN_SSH_PORT` 與 `OPEN_RDP_PORT` 這兩類 finding 對應的就是對外開放 22 與 3389 的規則，可以接告警。

AWS 環境的同類稽核流程見 [Security Group 稽核與清理](/infra/03-network-foundation/security-group-audit-cleanup/)，找出 `0.0.0.0/0` 規則與判斷是否合規的方法在兩朵雲上相同。

## 延伸閱讀：管理通道的設計模型、網路分層、IAM 權限設計與 SSH 金鑰

- → [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證與救援入口](/infra/03-network-foundation/management-access-channel/)：本篇每一節對應的那一層，以及跳板機、VPN、代理程式反向連線、SSH 短期憑證這些 GCP 以外的做法與選擇條件
- → [網路地基 — VPC、subnet 分層與 security group 設計](/infra/03-network-foundation/vpc-subnet-security-group/)：最小開放原則與 subnet 分層，本篇的防火牆規則是同一套原則在 GCP 上的寫法
- → [Security Group 稽核與清理](/infra/03-network-foundation/security-group-audit-cleanup/)：AWS 上找出 `0.0.0.0/0` 規則與安全刪除的流程
- → [模組二：身分與存取憑證地基](/infra/02-identity-credentials/)：通道授權改由 IAM 決定之後，權限範圍與短期憑證的設計
