---
title: "Oracle Cloud 私有子網路 Ubuntu 主機的實測紀錄：套件來源的出站（NAT gateway、路由與 NSG）、序列主控台的連線，以及被回收之後的重建"
date: 2026-10-26
description: "要在 Oracle Cloud 沒有公開 IP 的私有子網路裡跑一台 Ubuntu 主機、讓它裝得到套件更新，或要經由序列主控台看主機的開機過程，或主機被閒置回收、停止或刪除之後要照原樣重建，或想知道 NAT gateway 要不要另外付費、開機磁碟扣掉多少區塊磁碟額度、合計超過 200 GB 時放不進額度的那一顆怎麼算時，查實際跑過的指令、錯誤原文、重建腳本與每一步的讀法"
weight: 6
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "ubuntu", "serial-console", "network", "free-tier", "hands-on"]
---

> **事件說明**：2026-10-26（本篇沒有標 UTC 的日期與時刻都是台北時間），在 Oracle Cloud 的 `ap-batam-1` 區域，從一台 macOS 開發機用 OCI CLI 操作。tenancy 以 Free Tier 註冊，2026-10-27 確認它已經是付費帳戶（升級的日期這次沒有記錄）。主機是 A1 機型（`VM.Standard.A1.Flex`，1 OCPU、6 GB），映像檔是 `Canonical-Ubuntu-24.04-aarch64-2026.09.18-0`，放在既有的私有子網路裡、沒有公開 IP，經由 Bastion 的 port forwarding session 登入。當時在做的操作是：在雲端主機上確認 Ubuntu 的自動更新預設與核心更新前後的重開機判斷，並實際連一次序列主控台。2026-10-27 凌晨另外跑了重建腳本，並終止了重建腳本建出的 `verify-ubuntu-rebuild`；接著把 `verify-ubuntu` 停止、啟動，在三種狀態下各跑一次重建腳本，用 `oci limits` 與 usage API 查區塊磁碟額度與帳務，凌晨最後照刪除順序收掉 `verify-ubuntu` 的 NAT gateway 與 NSG。2026-10-27 上午又做了三件事：對 `verify-ubuntu` 重跑重建腳本，讓它重建 NAT gateway 與 NSG；用重建腳本新建一台開機磁碟 60 GB 的 `verify-ubuntu-60g`，建立期間對同一個名稱再跑一份腳本；以及在網頁主控台的 Limits, quotas and usage 頁讀區塊磁碟的用量；中午前用 usage API 查到那一台開機磁碟的計費項目之後，終止了 `verify-ubuntu-60g`。

這篇記錄在 Oracle Cloud 的私有子網路裡建一台 Ubuntu 24.04 主機之後，讓它連得到套件來源、連上序列主控台，以及主機不見之後怎麼照原樣重建。各節依序是：

- 前置條件：沿用 [Oracle Cloud 建立主機的實測紀錄：建立前的檢查、前置網路、主控台各分頁的 Always Free 設定值、等效的 CLI 指令、容量不足的重送、Bastion 工作階段逾時、Run Command 補公鑰的嘗試與重建後經由 port forwarding 登入](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/)（下文稱「建主機那篇」）建好的 compartment、VCN、私有子網路、service gateway、Bastion 與金鑰。
- 建 Ubuntu 24.04 主機，經由 port forwarding session 登入。
- 只接了 service gateway 的私有子網路裡，apt 連不到套件來源的錯誤原文與成因。
- 加上 NAT gateway、路由規則與只掛在這台主機上的出站 NSG（network security group：套在個別網卡上的一組防火牆規則）之後，`apt-get update` 成功。
- 序列主控台：產生 RSA 金鑰、建立序列主控台連線（instance console connection）、把官方的連線字串改寫成 ssh 的 ProxyJump 設定，以及看到的開機輸出。
- 主機被閒置回收、停止或刪除之後：怎麼發現、哪些資源會留下、主機與序列主控台連線的重建腳本（含用 `BOOT_GB` 指定開機磁碟大小）、每一步的讀法、同一個名稱同時跑兩份腳本的結果與會建出第二台主機的空窗、重建之後要重做的事與耗時。
- 費用與額度（A1 的免費量、開機磁碟從區塊磁碟額度扣掉多少與用量的查法、合計超過 200 GB 時放不進剩餘額度的那一顆磁碟整顆不算免費額度、網頁主控台 Limits, quotas and usage 頁與 CLI 的對照、在價目表與帳務明細裡找 NAT gateway 收費項目的結果），以及刪除這組資源的順序與實際刪除時的錯誤訊息（NSG 還掛在網卡上時的 412，NAT gateway 還被路由表指著時外層 400、內含 409）。

主機上量到的自動更新預設、核心更新前後的 `needrestart -b` 與 `reboot-required`，寫在 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)（下文稱「維護篇」）〈會老化的軟體：各條更新管道與更新後的重開機〉，這裡只寫在 Oracle Cloud 上建立與連線的操作。本篇自己的 OCID 與 IP 一律是佔位值：OCID 用 `oci ... list` 查，私有 IP 用 `oci compute instance list-vnics` 查；錯誤原文裡的位址是 Canonical 鏡像站的。

## 前置條件：沿用 Oracle Cloud 建立主機實測紀錄的網路、Bastion 與金鑰

這次沿用建主機那篇〈進建立頁之前：compartment、VCN、閘道與 private subnet〉建好的資源，沒有另建網路：

- **compartment 與 VCN**：放實驗資源的 compartment，以及裡面的 VCN。
- **私有子網路**：這台主機要放的子網路。它的路由表一開始只有一條規則，目的地是 Oracle 服務網路，出口是 service gateway；security list 的出站規則也只放行 Oracle 服務網路與子網路內部。路由規則裡的目的地是一個名稱而不是位址範圍，這個名稱依區域而不同（這次的值是 `all-hsg-services-in-oracle-services-network`），用 `oci network service list` 查，名稱帶「All」的那一筆的 `cidr-block` 欄就是它。
- **Bastion**：目標子網路是上面那個私有子網路，client CIDR 是開發機對外的 IP（/32）。開發機的對外 IP 換了之後，來源不在 client CIDR 裡，經由 Bastion 的 ssh 連線建立不起來，要先改 client CIDR（從 client CIDR 的作用推論；這次開發機的 IP 沒有變過，沒有看到實際的錯誤訊息）。
- **兩把金鑰**：登入主機用的金鑰（建立主機時放進去，重建腳本裡的檔名是 `verify-a1-key`），以及建 Bastion session 用的金鑰（檔名 `session_key`）。兩把都是建主機那篇建的：session 用的那一把照〈建立 Bastion 與 managed SSH session〉用 `ssh-keygen` 另產，登入主機的那一把是〈建主機：Oracle Linux 映像加 --ssh-authorized-keys-file〉另產、跟 session 那一把分開的一組，兩把分開的理由寫在那一節。
- **OCI CLI 的登入**：session token 登入，有效期約 1 小時，到期時重跑 `oci session authenticate --region <區域> --profile-name DEFAULT`，做法見 [從本機用 OCI CLI 操作 Oracle Cloud：session token 登入、時效與 API 簽章金鑰](/infra/cloud-providers/oracle-cloud/cli-session-login/)。`<區域>` 填區域的識別碼（這次是 `ap-batam-1`），`oci iam region-subscription list` 列得出 tenancy 訂閱的區域（這一條沒有實跑）。

下文的 CLI 指令裡，`<compartment 的 OCID>` 這類佔位值換成自己的。這次把重建腳本要用的值存在一個 `ids.env` 裡，腳本開頭 `source` 一次；每個鍵與查法如下（值是建立資源時從回傳記下的，查法的子命令只確認過 `--help` 存在，沒有逐一實跑）：

| 鍵       | 內容                                 | 查法                                                                   |
| -------- | ------------------------------------ | ---------------------------------------------------------------------- |
| `C`      | compartment 的 OCID                  | `oci iam compartment list`                                             |
| `V`      | VCN 的 OCID                          | `oci network vcn list -c <compartment 的 OCID>`                        |
| `SG`     | service gateway 的 OCID              | `oci network service-gateway list -c <compartment 的 OCID>`            |
| `SGCIDR` | service gateway 路由規則的目的地名稱 | `oci network service list`，名稱帶「All」那一筆的 `cidr-block`         |
| `RT`     | 私有子網路的路由表的 OCID            | `oci network route-table list -c <compartment 的 OCID> --vcn-id <VCN>` |
| `SN`     | 私有子網路的 OCID                    | `oci network subnet list -c <compartment 的 OCID> --vcn-id <VCN>`      |
| `B`      | Bastion 的 OCID                      | `oci bastion bastion list -c <compartment 的 OCID>`                    |

## 建 Ubuntu 24.04 主機與經由 port forwarding 登入

建立指令跟建主機那篇〈等效的 CLI 指令〉相同，換成 Ubuntu 24.04 的映像檔，建立時放登入用的公鑰：

```bash
# 查 Ubuntu 24.04、相容 A1 的映像檔，取建立時間最新的那一個（實跑）
oci compute image list -c <compartment 的 OCID> --operating-system "Canonical Ubuntu" \
  --operating-system-version "24.04" --shape VM.Standard.A1.Flex \
  --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output
# 建主機（實跑；這次第一次送出就成功，容量不足時用建主機那篇的重送腳本）
oci compute instance launch -c <compartment 的 OCID> --availability-domain <可用網域> \
  --display-name verify-ubuntu --shape VM.Standard.A1.Flex --shape-config '{"ocpus":1,"memoryInGBs":6}' \
  --image-id <映像檔的 OCID> --subnet-id <私有子網路的 OCID> --assign-public-ip false \
  --ssh-authorized-keys-file <登入用公鑰的路徑> \
  --agent-config '{"pluginsConfig":[{"name":"Bastion","desiredState":"ENABLED"}]}' \
  --is-pv-encryption-in-transit-enabled true \
  --instance-options '{"areLegacyImdsEndpointsDisabled":true}'
# 查主機的狀態（重建腳本裡同一條查詢實跑過）：印 PROVISIONING 時隔一陣子再查，印 RUNNING 才往下做
oci compute instance get --instance-id <launch 印出的主機 OCID> --query 'data."lifecycle-state"' --raw-output
```

這次的映像檔是 `Canonical-Ubuntu-24.04-aarch64-2026.09.18-0`。建立請求在送出之後約 4 秒回傳主機的 OCID，下一次查狀態時（約 20 秒後）已經是 `RUNNING`。建立指令裡各參數這次的取值與換掉之後的結果：

- `--availability-domain`：可用網域的完整名稱帶有 tenancy 專屬的前綴，用 `oci iam availability-domain list` 查；`ap-batam-1` 只有一個可用網域，沒有別的值可選。
- `--shape-config`：1 OCPU、6 GB。改大會多用 A1 的運算額度，合計超出免費量之後的結果依帳號狀態而定（〈費用與額度：A1、開機磁碟、出站流量與 NAT gateway〉）；這次沒有比較其他規格。
- `--assign-public-ip false`：主機只有私有 IP，所以登入一定要經過 Bastion；換成公開 IP 的做法在下面的〈建主機與登入的其他做法：映像檔、公開 IP、VPN 與 managed SSH session〉。
- `--agent-config` 打開 Bastion plugin：plugin 是 managed SSH session 的前提，而這台只用 port forwarding session 登入，port forwarding 不經過 plugin，所以關掉它時登入照樣走得通（從兩種 session 的機制推論，這次沒有關掉 plugin 實跑）；打開它留著改用 managed SSH session 的可能，這台的組合為什麼用不了 managed SSH session 見下面的其他做法。
- `--is-pv-encryption-in-transit-enabled true`：開機磁碟在主機與儲存之間的傳輸加密。用這個值，沒有比較其他值；CLI 不給時預設是 false，跟網頁主控台的預設不同（建主機那篇〈等效的 CLI 指令〉）。
- `--instance-options` 的 `areLegacyImdsEndpointsDisabled`：主機只能用第二版的中繼資料服務（IMDSv2；中繼資料服務是什麼見 [Instance Metadata Service（實例中繼資料服務）](/infra/knowledge-cards/instance-metadata-service/)，Oracle Cloud 的這個選項與第二版的差別見 [代理程式、中繼資料服務、初始化腳本、維護行為與標籤](/infra/cloud-providers/vm-options/management/)〈中繼資料服務與 Authorization header〉）。用這個值，沒有比較其他值；這台主機的 cloud-init 在這個設定下照樣讀到了公鑰（下面登入那一段的 `status: done`）。

主機的私有 IP 由子網路配發，建立之後才知道。私有 IP 掛在主機的 [VNIC（虛擬網路卡）](/infra/knowledge-cards/vnic/)（virtual network interface card：主機的虛擬網路卡，私有 IP 與後面〈加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG〉的 NSG 都掛在它上面）上，所以用列出 VNIC 的子命令查：

```bash
oci compute instance list-vnics --instance-id <主機的 OCID> --query 'data[0]."private-ip"' --raw-output
```

接著建一個指向這個 IP、22 port 的 port forwarding session（實跑；建立 session 的 work request 約 1 分鐘後是 `SUCCEEDED`）：

```bash
oci bastion session create-port-forwarding --bastion-id <Bastion 的 OCID> \
  --target-private-ip <主機的私有 IP> --target-port 22 \
  --ssh-public-key-file <session 用公鑰的路徑> --session-ttl 3600 --display-name verify-ubuntu-pf \
  --wait-for-state SUCCEEDED --wait-for-state FAILED --max-wait-seconds 600 \
  --query 'data.resources[0].identifier' --raw-output
```

這個 Bastion 建立時把 session 的最長時效（`max-session-ttl`）設成 3600 秒，`--session-ttl` 填更大的值時以 `InvalidParameter` 失敗，所以 session 最長 1 小時，過了要重建。自己的 Bastion 設了多少，用 `oci bastion bastion get --bastion-id <Bastion 的 OCID> --query 'data."max-session-ttl-in-seconds"'` 查（這一條沒有實跑）。上限可以用 `oci bastion bastion update --bastion-id <Bastion 的 OCID> --max-session-ttl <秒數>` 調高（`--help` 列得出這個選項，沒有實跑；可以調到多少這次沒有查證）：換到的是 session 少重建幾次，付出的是 session 用的私鑰外洩時，拿到的人能用比較久。登入用一份 ssh 設定檔，把 Bastion 當跳板（`ProxyJump`）：

```text
# ssh-ubuntu.conf：<session 的 OCID> 是上一條印出的值，<…路徑> 換成自己的
Host verify-bastion-u
  HostName host.bastion.<區域>.oci.oraclecloud.com
  User <session 的 OCID>
  IdentityFile <session 用私鑰的路徑>
  IdentitiesOnly yes

Host verify-ubuntu
  HostName <主機的私有 IP>
  User ubuntu
  IdentityFile <登入用私鑰的路徑>
  IdentitiesOnly yes
  ProxyJump verify-bastion-u
  UserKnownHostsFile <這台專用的 known_hosts 路徑>
  StrictHostKeyChecking accept-new
```

```bash
ssh -F ssh-ubuntu.conf verify-ubuntu 'cloud-init status --wait; cloud-init status; uptime'
```

這次第一次連線印出 `status: done` 與 `up 1 min`：主機開機約 1 分鐘之後，cloud-init 的首次開機設定已經跑完，預設帳號 `ubuntu` 也有了公鑰。Ubuntu 映像檔的預設帳號是 `ubuntu`，Oracle Linux 是 `opc`，`User` 那一行要跟著映像檔改。`UserKnownHostsFile` 指向這台專用的檔案，主機重建之後 host key 會換，清掉這個檔就好，不必動 `~/.ssh/known_hosts`。

`StrictHostKeyChecking accept-new` 讓 ssh 第一次連線時自動記下主機的 host key，之後 key 變了就拒絕連線。換到的是腳本裡的 ssh 不會停在「要不要信任這把 key」的提問；代價是第一次連線沒有比對指紋，那一刻連到的若不是這台主機，它的 key 也會被記下。要比對指紋時，照建主機那篇〈結果：停在 CREATING 約 15 分鐘後轉成 DELETED〉的做法用 console history 讀開機輸出，cloud-init 產生 host key 時把指紋印在裡面。預設值 `ask` 每台新主機第一次連線都要人回答，無人值守的腳本會停住（依 `ssh_config` 的說明，沒有實跑）。

設定檔的 `ProxyJump` 寫法以外，也可以在本機開一個轉送的 port 再連 `localhost`，兩種寫法的指令都在建主機那篇〈建 port forwarding session 並經由本機的轉送登入〉。

### 建主機與登入的其他做法：映像檔、公開 IP、VPN 與 managed SSH session

- **改用 Oracle Linux 映像檔**：Oracle Linux 的套件庫在 Oracle 的服務網路裡，只接 service gateway 的私有子網路就更新得到（從映像檔的套件庫設定與這個子網路的路由推論，這次沒有在這個子網路的 Oracle Linux 主機上跑 dnf 對照），〈加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG〉那些設定就不需要。代價是 Oracle Linux 10 的代理程式沒有 Bastion plugin，managed SSH session 用不了，只能用 port forwarding session（建主機那篇〈重建：Oracle Linux 映像加建立時放公鑰，經由 port forwarding session 登入〉）。
- **給主機公開 IP**：`--assign-public-ip true` 並把主機放進有 internet gateway 的公開子網路，主機自己就連得到套件來源，也可以直接 SSH，不需要 Bastion 與 NAT。代價是 22 port 對外暴露，要靠 security list 或 NSG 收窄來源（概念見 [Security Group](/infra/knowledge-cards/security-group/)）；這次沒有實跑這種做法。只開給開發機的公開 IP（/32）也能把來源收窄到一個位址，Bastion 比它多給了三件事：誰能開 session 由 IAM 政策決定，不只看來源 IP；主機在網際網路上沒有位址可以連；session 到時效就自己失效。公開 IP 這條路另外有一個重建時的代價：主機被刪除重建之後，臨時配發的公開 IP 會換一個，ssh 設定與允許清單都要跟著改（依公開 IP 的配發方式推論，這次沒有實跑）。三層各自的做法與取捨見 [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/)〈網路可達性的做法：管理 port 對誰開放〉。
- **改用 VPN 或 Tailscale 這類 overlay 網路登入**：主機上裝 VPN 的用戶端，從開發機經由 VPN 連進來，不需要 Bastion session 的 1 小時時效。這台主機的 NSG 只開出站 TCP 80 與 443，Tailscale 這類需要 UDP 直連的工具，推論會退到經由 443 的中繼伺服器轉送，延遲比直連高；這一點沒有查證，也沒有實跑。網路可達性那一層的比較在同一篇〈網路可達性的做法：管理 port 對誰開放〉。
- **managed SSH session 代替 port forwarding**：Ubuntu 24.04 的代理程式有 Bastion plugin，但官方〈Known Issues for Bastion〉寫明，Arm 架構的 A1 機型上、作業系統不是 Oracle Linux 的主機不支援 managed SSH session（理由是這類主機上的 Bastion plugin 沒有正確啟用）。建主機那篇〈建立之後：Bastion managed SSH session 逾時的排查〉在 A1 加 Ubuntu 上實測三次都逾時，所以這次只有 port forwarding 行得通。

## 只接 service gateway 的私有子網路：apt 連到套件來源時的錯誤原文與成因

主機建好之後，apt 在這個子網路裡連不到套件來源。這次 `apt-get update` 失敗時的輸出沒有留下，下面附的是同一台主機上 `apt-get install` 下載套件時的錯誤原文（實跑；IPv6 位址那幾行省略）：

```text
E: Failed to fetch http://ap-batam-1-ad-1.clouds.ports.ubuntu.com/ubuntu-ports/pool/main/... Cannot initiate the connection to ap-batam-1-ad-1.clouds.ports.ubuntu.com:80 (2620:2d:4002:1::10a). - connect (101: Network is unreachable) ... Could not connect to ap-batam-1-ad-1.clouds.ports.ubuntu.com:80 (91.189.91.103), connection timed out
E: Unable to fetch some archives, maybe run apt-get update or try with --fix-missing?
```

錯誤原文裡的兩種錯誤分別出自 IPv6 與 IPv4 兩條連線：

- **`Network is unreachable`（IPv6）**：主機的核心沒有任何通往網際網路的 IPv6 路由，`connect()` 立刻回錯誤碼 101（`ENETUNREACH`），封包沒有離開主機。序列主控台記下的開機輸出裡，cloud-init 印出的 IPv6 路由表只有 `fe80::/64`、`local` 與 `multicast` 三條，都只到這張網卡本身。
- **`connection timed out`（IPv4）**：封包送得出主機，回應沒有回來。這個子網路的路由表沒有任何一條規則把網際網路的位址送到出口，security list 的出站規則也沒有放行網際網路；兩項都沒有放行，是哪一項先擋下封包，這次沒有分開實測（推論）。

錯誤原文裡的主機名 `ap-batam-1-ad-1.clouds.ports.ubuntu.com` 是 Canonical 替雲端區域設的鏡像站；加上出站之後成功的輸出裡，`-security` 那幾行的來源是 `ports.ubuntu.com`。所以這個映像檔把一般的套件來源設成區域鏡像、把安全更新設成 `ports.ubuntu.com`（從兩份輸出與 Ubuntu 雲端映像檔的預設來源設定推論，這次沒有讀主機上的來源設定檔）。兩個主機都在 Oracle 的服務網路之外，而 service gateway 只轉送目的地是 Oracle 服務網路的封包，所以這台主機兩個都連不到。

這個失敗本身沒有訊號：`apt-get update` 的錯誤在背景排程裡只寫進 log，自動更新的 timer 照常觸發，什麼都裝不到。把 `apt-get update` 的輸出丟掉、只看 `apt list --upgradable` 時，連不到套件來源的主機會列出零個待裝的套件，看起來跟已經是最新的主機一樣；這次第一次探測就是這樣，加上出站之後同一台主機有 60 個安全更新待裝。所以私有子網路的主機上，讀自動更新的結果要讀它的 log（`/var/log/unattended-upgrades/`），不能只看有沒有待裝的套件。

## 加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG

要讓這台主機連得到網際網路上的套件來源而不給它公開 IP，出站要經過 [NAT Gateway](/infra/knowledge-cards/nat/)：主機送出的封包由 NAT gateway 換成它自己的公開 IP，回應的封包再換回來，網際網路上的主機連不進來。拿掉公開 IP 之後的出站需求怎麼處理（NAT，以及存取同一家業者的服務時不經過 NAT 的私有端點）、各自怎麼計費，寫在 [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/)〈移除公開 IP 之後的出站路徑〉；這一節是其中 NAT 那一條在 Oracle Cloud 上的實作。加出站要動三項設定：NAT gateway、路由表與 NSG。路由規則要填 NAT gateway 的 OCID，所以 NAT gateway 先建、路由表後改；NSG 跟前兩項沒有依賴，放在哪個位置做都可以。

```bash
# 1. 建 NAT gateway（實跑）
oci network nat-gateway create -c <compartment 的 OCID> --vcn-id <VCN 的 OCID> --display-name verify-nat \
  --wait-for-state AVAILABLE --query data.id --raw-output
# 2. 路由表加 0.0.0.0/0 → NAT（實跑）；update 是整份替換，原本那條 service gateway 的規則要一起寫
oci network route-table update --rt-id <私有子網路路由表的 OCID> --force --wait-for-state AVAILABLE --route-rules '[
 {"destination":"<Oracle 服務網路的目的地名稱>","destinationType":"SERVICE_CIDR_BLOCK","networkEntityId":"<service gateway 的 OCID>"},
 {"destination":"0.0.0.0/0","destinationType":"CIDR_BLOCK","networkEntityId":"<NAT gateway 的 OCID>"}]'
# 確認路由（沒有實跑）：該看到兩條，0.0.0.0/0 指向 NAT gateway 的 OCID，service gateway 那一條也還在
oci network route-table get --rt-id <私有子網路路由表的 OCID> \
  --query 'data."route-rules"[].{destination:destination,target:"network-entity-id"}' --output table
# 3. 建只有出站 TCP 80、443 的 NSG，掛到這台主機的 VNIC（實跑）
oci network nsg create -c <compartment 的 OCID> --vcn-id <VCN 的 OCID> --display-name verify-ubuntu-egress \
  --wait-for-state AVAILABLE --query data.id --raw-output
oci network nsg rules add --nsg-id <NSG 的 OCID> --security-rules '[
 {"direction":"EGRESS","protocol":"6","destination":"0.0.0.0/0","destinationType":"CIDR_BLOCK","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":80,"max":80}}},
 {"direction":"EGRESS","protocol":"6","destination":"0.0.0.0/0","destinationType":"CIDR_BLOCK","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":443,"max":443}}}]'
# 確認規則（沒有實跑）：該看到兩列 EGRESS，port 分別是 80 與 443
oci network nsg rules list --nsg-id <NSG 的 OCID> \
  --query 'data[].{direction:direction,port:"tcp-options"."destination-port-range".min}' --output table
# 查這台主機的 VNIC 的 OCID（實跑），再把 NSG 掛上去
oci compute instance list-vnics --instance-id <主機的 OCID> --query 'data[0].id' --raw-output
oci network vnic update --vnic-id <主機的 VNIC 的 OCID> --nsg-ids '["<NSG 的 OCID>"]' --force
# 確認掛上（沒有實跑）：印出的 OCID 清單裡有 <NSG 的 OCID>
oci network vnic get --vnic-id <主機的 VNIC 的 OCID> --query 'data."nsg-ids"'
```

- **路由表**：決定封包往哪個出口送。規則依目的地比對，Oracle 服務網路的位址仍走 service gateway，其餘的（`0.0.0.0/0`）走 NAT gateway。`<Oracle 服務網路的目的地名稱>` 是原本那條規則的目的地，查法在〈前置條件：沿用 Oracle Cloud 建立主機實測紀錄的網路、Bastion 與金鑰〉的私有子網路那一項。`route-table update --route-rules` 會用給的清單取代整份規則，`--force` 略過取代之前的確認提示。只寫 NAT 那一條的話，service gateway 那一條就被刪掉，主機連 Oracle 服務網路的流量（Oracle Cloud Agent 的回報這類）改走 NAT gateway 到公開端點（從路由的比對方式推論，沒有實跑只寫一條的結果）。
- **NSG**：決定這張網卡（VNIC）放行哪些封包，概念見 [Security Group](/infra/knowledge-cards/security-group/)。這個子網路的 security list 只放行 Oracle 服務網路與子網路內部的出站，有路由也送不出去，所以要再放行一條。這一條放在 NSG：security list 套在整個子網路上，同一個子網路裡的其他主機（這次有一台 Oracle Linux 主機）會一起多出網際網路的出站。NSG 只套在掛上它的 VNIC，影響範圍只有這一台。Oracle Cloud 對一張網卡取 security list 與 NSG 兩邊規則的聯集，任何一邊放行就放行（[網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/)〈防火牆規則的位置與合併方式〉），所以「只開 80 與 443」成立的前提是這個子網路的 security list 一直不放行網際網路的出站；有人之後在 security list 加了全開的出站規則，這台主機的出站也跟著全開。規則裡的 `"protocol":"6"` 是 TCP 在 IANA 協定號碼表上的號碼；規則是有狀態的（`isStateless: false`），回應的封包自動放行，不必另寫入站規則。
- **只開 80 與 443**：`apt-get update` 的輸出顯示 Ubuntu 的套件來源是 `http://`（80），套件的完整性由 apt 另外驗簽章；443 留給用 HTTPS 的來源（snap 與第三方套件庫這類）。只開這兩個 port 時 `apt-get update` 成功，名稱解析沒有另外放行；名稱解析走 VCN 內建的 DNS，在 VCN 裡面，不經過這兩條出站規則（從 VCN 的 DNS 設計推論，這次沒有讀主機上的解析設定）。

`vnic update --nsg-ids` 同樣是整份取代，`--force` 同樣略過確認提示：VNIC 原本掛著別的 NSG 時，要把原本的那幾個一起寫進清單。三樣都做完之後，同一條指令成功（實跑）：

```text
Get:55 http://ports.ubuntu.com/ubuntu-ports noble-security/multiverse arm64 c-n-f Metadata [456 B]
Fetched 39.9 MB in 9s (4371 kB/s)
```

這一次下載 39.9 MB 花了 9 秒，速率 4371 kB/s。`apt list --upgradable` 列出 79 行，其中 60 個來自 `-security`，包括新的核心。這個映像檔建立之後公開的漏洞，在主機第一次開機時都還沒修補，所以新建的主機先手動跑一次更新並重開機：

```bash
sudo unattended-upgrade   # 裝 -security 的更新（實跑，402 秒）
sudo systemctl reboot     # 換上新核心（實跑）
```

`unattended-upgrade` 跑完升級了 64 個套件，比 `-security` 的 60 個多 4 個。這 4 個的來源這次沒有查；一個可能是新核心以新的套件名稱安裝，新安裝的套件不會列在 `apt list --upgradable` 裡（推論）。待裝的數量依映像檔建立的日期到建主機那一天之間公開了多少更新而變，換一個映像檔或換一天建，數字就不同。核心更新前後的重開機判斷在維護篇〈會老化的軟體：各條更新管道與更新後的重開機〉。

### 出站的其他做法：security list、建主機時就掛 NSG、限縮出站的目的地與不加出站

- **把出站規則加在 security list**：效果是整個子網路的主機都能出站。同一個子網路只有這一台主機、或每一台本來就要更新時，這樣設定比較少；代價是之後放進這個子網路的主機也自動有網際網路出站（從 security list 套用的範圍推論，沒有實跑）。
- **建主機時就掛上 NSG**：`oci compute instance launch` 有 `--nsg-ids`（`--help` 確認過，沒有實跑），建立時就把出站 NSG 掛在主機的 VNIC 上。換到的是主機首次開機時就有出站，重建腳本裡掛 NSG 那一步（第 6 步）也不必另外做；付出的是 NAT gateway、路由與 NSG 都要在建主機之前做好，順序從「先建主機、再加出站」變成「先加出站、再建主機」。
- **限縮出站的目的地**：三種做法都把出站從「任何位址的 80 與 443」收窄。NSG 的規則只收 CIDR，可以只放行 Canonical 鏡像站的網段，代價是鏡像站的位址會變，位址換了之後更新又會逾時（推論，沒有查證）；在有出站的子網路自架一台 forward proxy，依網域篩選，私有子網路的主機只連它；或在 VCN 裡自建一台 apt 的快取代理（例如 apt-cacher-ng），私有子網路的主機只連那一台，另外還能控制更新的內容。後兩種適合主機多的環境，代價是多一台要維護的主機（推論，沒有實跑）。
- **不加出站**：主機永遠裝不到套件更新，自動更新的 timer 照常觸發、什麼都裝不到；只適合用完即刪、不需要更新的實驗。

## 序列主控台：RSA 金鑰、建立連線、ProxyJump 設定與看到的開機輸出

序列主控台（[Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/)）讀的是主機的虛擬序列埠，不經過主機的網路與 sshd，sshd 設定改壞、防火牆擋住、新核心開不了機時，仍看得到開機輸出。Oracle Cloud 的做法是替主機建一個序列主控台連線（instance console connection），它只收 RSA 公鑰：

```bash
# 產生 RSA 金鑰；序列主控台連線不收 ed25519（依 Oracle Cloud 文件〈Instance Console Connections〉，沒有拿 ed25519 實試）
ssh-keygen -q -t rsa -b 3072 -N '' -C verify-console -f <序列主控台私鑰的路徑>
# 建序列主控台連線（實跑，回傳時已是 ACTIVE）
oci compute instance-console-connection create --instance-id <主機的 OCID> \
  --ssh-public-key-file <序列主控台私鑰的路徑>.pub --wait-for-state ACTIVE
# 取得官方的連線字串
oci compute instance-console-connection list -c <compartment 的 OCID> --instance-id <主機的 OCID> \
  --query 'data[0]."connection-string"' --raw-output
```

這次的序列主控台連線用完就刪，平時不留。序列主控台是救援入口，繞過平時登入主機的控制點，所以照 [Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/)〈設計責任〉的「平時保持關閉、救援時才開啟、用完關回去」：要排查時跑〈被回收之後的重建：怎麼發現、留下與消失的資源、重建腳本〉裡序列主控台連線的重建腳本建一條（這次實跑約 15 秒），排查完用下面這條刪掉（腳本結尾會印出代入了連線 OCID 的同一條）：

```bash
# 刪掉序列主控台連線（實跑）：--wait-for-state 等的是連線本身的狀態
oci compute instance-console-connection delete --instance-console-connection-id <連線的 OCID> \
  --force --wait-for-state DELETED
```

2026-10-27 對 `verify-ubuntu` 那條連線實跑這一條：CLI 印出 `Action completed. Waiting until the resource has entered state: ('DELETED',)`，exit 0，10 秒；之後 `instance-console-connection list` 只列出這一條，狀態是 `DELETED`，主機本身仍是 `RUNNING`。

`ssh-keygen` 的 `-N ''` 讓私鑰不設保護密碼（passphrase），重建腳本可以不經互動使用它；代價是拿到這個私鑰檔的人就連得上這台主機的序列主控台。這個代價跟上面「連線只在排查時存在」一起看：連線平時不存在，私鑰外洩時，拿到的人還要等下一次有人建連線、而且要在刪掉之前用它，能用的時間窗只剩排查那一段；連線一直留著的話，同一把沒有保護密碼的私鑰隨時都連得上。檔案仍然只給自己讀（`ssh-keygen` 產生的私鑰權限是 600）。設了保護密碼的話，每次連線要輸入它，或先把私鑰交給 `ssh-agent`，這次沒有比較這種做法。

官方的連線字串是一條 ssh 指令，外面再包一層 ssh 當跳板，形狀是 `ssh -o ProxyCommand='ssh -W %h:%p -p 443 <連線的 OCID>@instance-console.<區域>.oci.oraclecloud.com' <主機的 OCID>`。`ProxyCommand` 讓 ssh 在本機執行一條任意的指令，把它的輸入輸出當成連線；`ProxyJump` 由 ssh 自己經由跳板轉送連線，不在本機執行別的指令，效果相同。`ProxyJump` 這一欄只接受跳板的使用者、主機與 port，有人改寫這一欄時，改得到的只有跳板的位址；`ProxyCommand` 那一欄被改寫時，換上的是會在本機執行的指令。改寫成 `ProxyJump` 時：跳板主機是 `instance-console.<區域>.oci.oraclecloud.com` 的 443 port，使用者名稱是連線的 OCID；目的地的「主機名稱」是主機的 OCID，使用者名稱同樣是連線的 OCID。

```text
# ssh-console.conf
Host verify-console-gw
  HostName instance-console.<區域>.oci.oraclecloud.com
  Port 443
  User <連線的 OCID>
  IdentityFile <序列主控台私鑰的路徑>
  IdentitiesOnly yes
  UserKnownHostsFile <序列主控台專用的 known_hosts 路徑>
  StrictHostKeyChecking accept-new
  HostKeyAlgorithms +ssh-rsa
  PubkeyAcceptedAlgorithms +ssh-rsa

Host verify-console
  HostName <主機的 OCID>
  User <連線的 OCID>
  ProxyJump verify-console-gw
  IdentityFile <序列主控台私鑰的路徑>
  IdentitiesOnly yes
  UserKnownHostsFile <序列主控台專用的 known_hosts 路徑>
  StrictHostKeyChecking accept-new
  HostKeyAlgorithms +ssh-rsa
  PubkeyAcceptedAlgorithms +ssh-rsa
```

```bash
# -tt 讓 ssh 配一個終端機，序列埠的輸出才會照原樣顯示；離開時先按 Enter，再輸入 ~.
ssh -tt -F ssh-console.conf verify-console
```

`HostKeyAlgorithms +ssh-rsa` 與 `PubkeyAcceptedAlgorithms +ssh-rsa` 兩行是預防性的：連線用 RSA 金鑰，新版 OpenSSH 預設不接受 `ssh-rsa` 簽章，這次沒有比較拿掉這兩行的結果。

連上之後先印出一段 Oracle Cloud 的說明，接著是主機目前的序列埠輸出。這次連著序列主控台讓主機重開機（在另一個終端機經由 Bastion 執行 `sudo systemctl reboot`），依序看到關機時 systemd 停止各個 unit、`reboot: Restarting system`、韌體的 `Oracle AAVMF Version: 20260902` 與載入的 UEFI 模組、核心的 `Linux version 6.17.0-…-oracle`，核心開始開機之後約 27 秒在 `ttyAMA0` 印出 `Ubuntu 24.04.5 LTS verify-ubuntu ttyAMA0` 與登入提示。只看開機卡在哪一步（核心、檔案系統、cloud-init）時，不必登入就看得到。

登入作業系統要一個設了密碼的使用者。這台主機的 `ubuntu` 帳號，`passwd -S ubuntu` 印出的狀態是 `L`（密碼鎖定），這次也沒有替任何使用者設密碼，所以登入那一步沒有做。

### 序列主控台的其他做法：在序列主控台登入作業系統、console history、Cloud Shell 與 VNC

- **事先設一個救援帳號的密碼**：序列主控台出現登入提示時就能登入，sshd 壞掉時從這裡修。代價是主機多了一個密碼登入的帳號，要同時確認 sshd 不接受密碼登入（`sshd -T` 印 `passwordauthentication no`），密碼只在序列主控台上有效。GCP 上照這個做法實際登入過，步驟在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄：盤點、救援入口、IAP 規則與 IAM、停用舊規則驗證、OS Login 啟用與移除外部 IP](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/)〈準備救援入口：Serial Console 與本機救援帳號〉；三家業者的條件比較在維護篇〈會老化的軟體：各條更新管道與更新後的重開機〉。
- **只讀開機輸出的快照（console history）**：`oci compute console-history capture` 擷取一份開機輸出的唯讀快照，不必建連線、不必產生 RSA 金鑰，也不能輸入；只要知道開機停在哪一步、或讀 host key 的指紋時夠用。建主機那篇〈結果：停在 CREATING 約 15 分鐘後轉成 DELETED〉用過這兩條指令。
- **從網頁主控台的 Cloud Shell 連**：網頁主控台的主機頁面有「Launch Cloud Shell connection」，在瀏覽器裡開連線，不必在本機產生金鑰與設定檔（依 Oracle Cloud 文件〈Instance Console Connections〉，沒有實跑）。
- **VNC 連線**：同一個序列主控台連線另有 VNC 的連線字串，看的是圖形畫面，Linux 伺服器映像檔沒有圖形介面時跟序列埠看到的相同（依同一份文件，沒有實跑）。

## 被回收之後的重建：怎麼發現、留下與消失的資源、重建腳本

Always Free 的主機在連續 7 天內 CPU 使用率（取第 95 百分位）、網路使用率、記憶體使用率（只算 A1）三項都低於 20% 時，Oracle 可能回收它，規則與官方沒寫的部分在 [Oracle Cloud 的帳號結構與 home region：tenancy、Always Free 的範圍與主控台登入欄位](/infra/cloud-providers/oracle-cloud/account-and-home-region/)（下文稱「帳號篇」）〈Always Free 的額度與它綁在 home region 上的範圍〉。這台主機平常沒有負載，三項都落在條件裡；官方沒有寫這條規則對付費帳戶適不適用，這個 tenancy 已經是付費帳戶，所以無法確定這台是否會被回收。官方也沒有寫回收之後主機是停止還是刪除、會不會通知，所以重建的做法要兩種情形都涵蓋。

這次沒有做回收發生之前的對策，只準備了回收之後的重建。事前的對策有三種，這次都沒有實作：

- **維持負載**：讓三項使用率之一一直高於 20%，主機就不落在回收條件裡。官方條款怎麼看待專門為了避開回收而製造的負載，這次沒有查證。
- **用 Events 或 Monitoring 告警**：主機狀態改變時通知自己，回收發生的當下就知道。回收是否發出可以訂閱的事件，這次沒有查證。
- **定期備份開機磁碟**：回收之後可以從備份還原，裝過的更新與設定都在。暫停、停止、終止主機各自會留下哪些資源，比較見 [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/operations/09-host-lifecycle/suspend-and-resume-service/)〈暫停時保留的範圍：只停服務、停止主機、終止主機、全部刪除〉；那一篇的〈恢復上線前要重新確認的漂移〉另外寫了主機不是照計畫暫停時（被閒置回收這類）要拿什麼當比對的基準。

**發現主機不見了**：經由 Bastion 登入失敗時（port forwarding session 建不出來、或 ssh 逾時），先查主機的狀態：

```bash
oci compute instance get --instance-id <主機的 OCID> --query 'data."lifecycle-state"' --raw-output
oci compute instance list -c <compartment 的 OCID> --display-name verify-ubuntu \
  --query 'data[].{id:id,state:"lifecycle-state"}'
```

- 印 `RUNNING`：主機還在，問題在 Bastion、session 過期或開發機的 IP 換了（Bastion 的 client CIDR）。
- 印 `STOPPED`：主機被停止，開機磁碟、VNIC 與私有 IP 都還在，啟動之後回到 `RUNNING`；啟動也可能失敗，例如 A1 容量不足時（推論，這次沒有遇到）。
- 印 `TERMINATED`、或 `get` 回 404、`list` 找不到：主機被刪除，要重建。開機磁碟是否一起刪掉，官方沒有寫，到 Block Storage → Boot Volumes 查。舊磁碟還在時有兩種處理：拿它重建主機（`oci compute instance launch` 以 `--source-boot-volume-id <開機磁碟的 OCID>` 代替 `--image-id`，沒有實跑），裝過的更新與設定都還在；或刪掉它，釋放它佔的區塊磁碟額度。主機終止時開機磁碟的預設去留見 [磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)〈刪除（終止）主機時開機磁碟的預設去留〉。

**兩種情形各自留下與消失的資源**。格內寫「實跑」的是主動操作時看到的，不是回收：停止那一欄的是 2026-10-27 主動停止 `verify-ubuntu` 再啟動時看到的，刪除那一欄的是主動終止 `verify-ubuntu-rebuild` 時看到的。格內沒寫「實跑」的，停止那一欄依停止主機的機制推論，刪除那一欄依終止主機的機制推論。回收實際做的是停止還是刪除，這次沒有遇到：

| 資源                                                   | 主機被停止                                                                                                                                                                                                                                    | 主機被刪除                                                           |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| compartment、VCN、私有子網路、service gateway、Bastion | 留下                                                                                                                                                                                                                                          | 留下                                                                 |
| NAT gateway、路由規則、NSG 與它的規則                  | 留下（主動停止時實跑）                                                                                                                                                                                                                        | 留下                                                                 |
| 主機、它的 VNIC 與私有 IP                              | 留下，啟動之後私有 IP 不變（主動停止時實跑）                                                                                                                                                                                                  | 消失；重建的主機拿到新的私有 IP                                      |
| NSG 掛在 VNIC 上的關係                                 | 留下（主動停止時實跑）                                                                                                                                                                                                                        | 跟著 VNIC 消失，要重新掛                                             |
| 開機磁碟與上面裝過的更新                               | 留下（主動停止時實跑）                                                                                                                                                                                                                        | 指定刪除時一起刪掉（主動終止時實跑，不是回收）；回收時的去留官方沒寫 |
| 序列主控台連線                                         | 平時沒有；排查時建的那一條用完就刪                                                                                                                                                                                                            | 變成 `DELETED`（主動終止時實跑，不是回收）；平時本來就沒有           |
| port forwarding session                                | 1 小時後本來就會失效                                                                                                                                                                                                                          | 同左                                                                 |
| 本機的 ssh 設定與 known_hosts                          | 不用改；例外是 `host-<名稱>.env` 還沒有記下這台主機時（主機不是重建腳本建的，例如照〈建 Ubuntu 24.04 主機與經由 port forwarding 登入〉手動建的），重建腳本第一次跑會清空 known_hosts 一次，下一次登入自動重新記下（見下面重建腳本的實跑結果） | IP 與 host key 都換了，要重寫                                        |

**重建腳本**：下面這支腳本把「停止就啟動、不見就重建」與之後要重新接上的每一項資源與設定寫在一起。每一步先查後建，重跑不會重複建立；例外是 port forwarding session，它最長 1 小時就失效，所以每次都新建一個。每一步至少印一行「已存在」「新建」「啟動」「重送」或「改寫」；任何一條 `oci` 指令失敗，腳本就停下來，印出那條指令寫在 stderr 的內容，不會把失敗當成「查無結果」往下走。它的每一個建立指令都是〈建 Ubuntu 24.04 主機與經由 port forwarding 登入〉與〈加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG〉兩節實跑過的那一條，先查後建與錯誤處理的部分是新加的。

這支腳本改過三個版本，雲端實跑與測試各自用的是其中一版：

- **沒有等待迴圈的版本**：沒有 `wait_state`，也沒有等待 VNIC 的迴圈。
- **加上等待迴圈的版本**：加上 `wait_state` 與等待 VNIC 的迴圈。
- **現在這一版**：下面這一版。在加上等待迴圈的版本之外，加了依主機狀態分支、重送迴圈的改寫（只重送 500 與 429）、依主機是否為同一台決定 known_hosts 的去留、路由目的地改讀 `ids.env` 的 `SGCIDR`，以及每一條 `oci` 失敗就停下來的錯誤處理（含路由表裡有其他規則時停下來、NAT gateway 與 NSG 已存在時也記進 `ids.env`）。2026-10-27 上午另外加了指定開機磁碟大小的 `BOOT_GB`，只動到建立請求那一行（加上 `BOOT_ARGS` 的展開）、開頭變數區組 `BOOT_ARGS` 的一行，以及檔頭的用法註解（改寫一行、加兩行；單位的說明是實跑之後才補上的，執行的程式碼沒有變）；當天凌晨 `STOPPED`、`STOPPING`、`STARTING` 那幾次跑的是加 `BOOT_GB` 之前的版本，那幾條路徑不經過建立請求，下表一律算在現在這一版。

雲端實跑是 2026-10-27 在同一個 tenancy 上跑的；假的 `oci` 是一支依劇本回傳主機狀態與建立請求回應、也能讓單一種呼叫失敗的指令，搭配一支不等待、只記下秒數的假 `sleep`。兩者的結果都在腳本之後。序列主控台連線的重建腳本也列在同一張表；它在雲端跑的是訊息還寫「主控台連線」、還沒有錯誤處理與換金鑰處理的前一版：

| 路徑                                                                                        | 在雲端實跑過                                                                                                                                                                                                                                                                                                                                 | 用假的 `oci` 測過             |
| ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| 主機已經是 `RUNNING`                                                                        | 現在這一版（重建 NAT gateway 與 NSG 那一次）；較早還跑過沒有等待迴圈的版本                                                                                                                                                                                                                                                                   | 現在這一版                    |
| 找不到同名主機，新建                                                                        | 現在這一版從送出建立請求跑到結束（`BOOT_GB=60`；不給 `BOOT_GB` 的新建只有較早的兩個版本跑過，見下面「名稱不存在，較早的兩個版本」那一項）                                                                                                                                                                                                    | 現在這一版                    |
| 主機 `STOPPED`、`STOPPING`、`STARTING`                                                      | 現在這一版                                                                                                                                                                                                                                                                                                                                   | 現在這一版                    |
| 主機 `PROVISIONING`                                                                         | 現在這一版（另一份腳本正在建同名主機時）                                                                                                                                                                                                                                                                                                     | 現在這一版                    |
| 主機停在其他狀態（`TERMINATING`）、或狀態讀不出                                             | 沒有                                                                                                                                                                                                                                                                                                                                         | 現在這一版                    |
| 建立請求回 500 或 429 後重送、回 400 或 401、讀不出回應碼、OCID 前有警告、查不到映像檔      | 沒有（雲端那一次第一次送出就成功）                                                                                                                                                                                                                                                                                                           | 現在這一版                    |
| NAT gateway 與 NSG 新建、路由表少了 0.0.0.0/0 那一條                                        | 現在這一版                                                                                                                                                                                                                                                                                                                                   | 現在這一版                    |
| VNIC 已經掛著其他 NSG                                                                       | 沒有                                                                                                                                                                                                                                                                                                                                         | 現在這一版                    |
| 路由表裡有其他規則                                                                          | 沒有                                                                                                                                                                                                                                                                                                                                         | 現在這一版                    |
| 主機跟上次記下的不是同一台                                                                  | 現在這一版，`host-<名稱>.env` 還沒有記下主機的情形（`STOPPED` 那一次）                                                                                                                                                                                                                                                                       | 現在這一版                    |
| 查詢或寫入的 `oci` 失敗（查主機、啟動、查 NAT、讀與改路由表、讀與加 NSG 規則、讀與改 VNIC） | 沒有                                                                                                                                                                                                                                                                                                                                         | 現在這一版                    |
| `instance action`、`wait_state` 實際等待的時間                                              | `instance action` 等到 `RUNNING`：現在這一版，`STOPPED`、`STOPPING` 兩次，從腳本開始到印出「啟動」各約 9 秒；`wait_state` 的 10 秒輪詢：新建主機時跑到（路徑跑到是實跑；輪詢的次數從時間戳推論），印出「新建」主機（送出建立請求之前）到印出「已 RUNNING」約 50 秒，同一段時間碰到 `PROVISIONING` 的另一份腳本也在輪詢；900 秒逾時：沒有跑到 | 不適用（假的 `sleep` 不等待） |
| 序列主控台連線：沒有 `ACTIVE` 的連線就建                                                    | 前一版                                                                                                                                                                                                                                                                                                                                       | 現在這一版                    |
| 序列主控台連線：已有連線就沿用、新產生金鑰時換掉舊連線、找不到主機、`oci` 失敗              | 沒有                                                                                                                                                                                                                                                                                                                                         | 現在這一版                    |

```bash
#!/bin/bash
# 主機被回收、停止或刪除之後，把 verify-ubuntu 這一組恢復成可以登入、連得到套件來源的狀態：
#   主機（不存在就建、停止就啟動）→ 私有 IP 與 VNIC → NAT gateway → 私有子網路路由的 0.0.0.0/0 規則
#   → 出站 NSG 與它的兩條規則 → NSG 掛到這台的 VNIC → port forwarding session → ssh 設定與 known_hosts。
# 每一步先查後建，重跑不會重複建立（例外是 port forwarding session，每次都新建一個）；
#   每一步至少印一行「已存在」「新建」「啟動」「重送」或「改寫」。任何一條 oci 失敗就停下來，印出它的 stderr。
# 用法：./rebuild-ubuntu.sh [主機名稱]（預設 verify-ubuntu）。新建主機時，環境變數 BOOT_GB 指定開機磁碟大小，
#   單位跟 boot-volume list 的 size-in-gbs 相同（60 建出 60 GiB）；不給就用映像檔的預設大小
#   （Ubuntu 24.04 的 size-in-gbs 是 47）。需要 ids.env 的 C（compartment）、V（VCN）、
#   SG（service gateway）、SGCIDR（service gateway 路由規則的目的地名稱）、RT（私有子網路的路由表）、
#   SN（私有子網路）、B（Bastion）。
# 整個 VCN 共用的 NAT gateway 與 NSG 記在 ids.env；只屬於這一台的值（主機、session）記在 host-<名稱>.env，
#   ssh 設定與 known_hosts 也依名稱各一份，所以給不同名稱重跑不會蓋掉另一台的紀錄。
# 結束碼：0 完成；2 登入過期、查不到映像檔、主機停在無法處理的狀態或其他無法繼續的錯誤；
#   3 建立主機的回應讀不出回應碼（請求可能已經成功），重跑之前先用 instance list 確認沒有同名主機；
#   4 建立主機的回應碼不是 500、429、401（400 參數錯誤這類），照印出的訊息改好再跑。
set -uo pipefail
# OCI CLI 是 Python 程式；PYTHONWARNINGS=ignore 關掉 Python 直譯器印的警告，不讓警告行混進要解析的輸出
export OCI_CLI_AUTH=security_token PYTHONWARNINGS=ignore
D=$(cd "$(dirname "$0")" && pwd)
source "$D/ids.env"
NAME=${1:-verify-ubuntu}
AD="<可用網域>"
KEY="$D/verify-a1-key.pub"
NAT_NAME=verify-nat
NSG_NAME=verify-ubuntu-egress
HOSTENV="$D/host-${NAME}.env"
CONF="$D/ssh-${NAME}.conf"
KNOWN="$D/known_hosts_${NAME}"
BOOT_ARGS=(); [[ -n "${BOOT_GB:-}" ]] && BOOT_ARGS=(--boot-volume-size-in-gbs "$BOOT_GB")
NEW=0
ERR=$(mktemp "${TMPDIR:-/tmp}/rebuild-ubuntu.XXXXXX"); trap 'rm -f "$ERR"' EXIT
ts() { date +%m-%d\ %H:%M:%S; }
say() { echo "$(ts) [$1] $2"; }
die() { echo "$(ts) [錯誤] $1" >&2; exit "${2:-2}"; }
# 查詢與寫入用的包裝：stderr 存進 $ERR 那個暫存檔，濾掉兩種不是結果的提示行（Python 的 SyntaxWarning，
#   與 CLI 建議改用 `oci -i` 的 Interactive mode 那一行），結束碼照 oci 自己的回傳。
#   CLI 的 --query 結果是空的時候 stdout 什麼都不印，所以空字串要搭配結束碼 0 才代表查無結果
q() {
  local out rc
  out=$(oci "$@" 2>"$ERR"); rc=$?
  [[ -n "$out" ]] && grep -v -e SyntaxWarning -e 'Interactive mode' <<<"$out"
  return $rc
}
# q 失敗時停下來，印出 oci 寫在 stderr 的內容
fail() { die "${1}失敗：$(tr '\n' ' ' < "$ERR")"; }
# 把「鍵=值」記進 ids.env；已經有同樣的一行就不重複寫
record() { grep -qx "$1=$2" "$D/ids.env" || echo "$1=$2" >> "$D/ids.env"; }
# instance get 沒有 --wait-for-state，所以自己每 10 秒查一次狀態，最多等 900 秒
wait_state() {
  local want=$1 i cur
  for ((i = 0; i < 90; i++)); do
    cur=$(q compute instance get --instance-id "$IID" --query 'data."lifecycle-state"' --raw-output) || fail "查主機狀態"
    [[ "$cur" == "$want" ]] && return 0
    sleep 10
  done
  die "主機等了 900 秒仍是 ${cur:-查不到}，沒有變成 $want"
}

# 0. 登入：session token 過期時後面每一條都會失敗，先擋下來
oci session validate --profile DEFAULT >/dev/null 2>&1 \
  || die "CLI session 過期，先跑 oci session authenticate --region <區域> --profile-name DEFAULT"

# 1. 主機：依名稱找還沒終止的那一台，依狀態決定跳過、啟動或建立
LAST_IID=$(grep '^IID=' "$HOSTENV" 2>/dev/null | tail -1 | cut -d= -f2)
IID=$(q compute instance list -c "$C" --display-name "$NAME" \
  --query "data[?\"lifecycle-state\"!='TERMINATED'] | [0].id" --raw-output) || fail "查同名主機"
STATE=""
# 查詢成功而且結果是空的，才代表沒有同名主機；查得到主機而狀態讀不出來時，不當成「不存在」去建第二台
if [[ -n "$IID" ]]; then
  [[ "$IID" == ocid1.instance* ]] || die "查同名主機回了不是主機 OCID 的值：$IID"
  STATE=$(q compute instance get --instance-id "$IID" --query 'data."lifecycle-state"' --raw-output) || fail "查主機狀態"
  [[ -z "$STATE" ]] && die "查得到主機 ${IID}，卻讀不出它的狀態"
fi
case "$STATE" in
  RUNNING) say 已存在 "主機 ${NAME}（RUNNING）" ;;
  STOPPED)
    q compute instance action --instance-id "$IID" --action START --wait-for-state RUNNING --max-wait-seconds 900 >/dev/null \
      || fail "啟動主機（STOPPED → RUNNING）"
    say 啟動 "主機 ${NAME}（STOPPED → RUNNING）" ;;
  STARTING|PROVISIONING)
    wait_state RUNNING
    say 已存在 "主機 ${NAME}（等到 RUNNING）" ;;
  STOPPING)
    wait_state STOPPED
    q compute instance action --instance-id "$IID" --action START --wait-for-state RUNNING --max-wait-seconds 900 >/dev/null \
      || fail "啟動主機（STOPPING → RUNNING）"
    say 啟動 "主機 ${NAME}（STOPPING → RUNNING）" ;;
  "")
    # 找不到還沒終止的同名主機：只有這種情形才建立
    IMG=$(q compute image list -c "$C" --operating-system "Canonical Ubuntu" --operating-system-version "24.04" \
      --shape VM.Standard.A1.Flex --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output) || fail "查映像檔"
    [[ "$IMG" == ocid1.image* ]] || die "查不到 Ubuntu 24.04 的 A1 映像檔：${IMG:-查詢結果是空的}"
    IMGNAME=$(q compute image get --image-id "$IMG" --query 'data."display-name"' --raw-output) || fail "查映像檔名稱"
    say 新建 "主機 ${NAME}，映像檔 $IMGNAME"
    # 容量不足時重送：間隔從 120 秒起，429 加倍（上限 600），其他回應每次縮 10 秒、最低 60 秒，±15 秒抖動
    back=120 n=0 last_refresh=0                     # 0：開跑時先延長一次 token
    while :; do
      n=$((n+1))
      # session token 一小時過期，每 30 分鐘（1800 秒）延長一次，重送跑得再久也不會在中途過期
      if (( $(date +%s) - last_refresh >= 1800 )); then
        oci session refresh --profile DEFAULT >/dev/null 2>&1 || die "token refresh 失敗，重跑 oci session authenticate"
        last_refresh=$(date +%s)
      fi
      out=$(oci --no-retry compute instance launch -c "$C" --availability-domain "$AD" --display-name "$NAME" \
        --shape VM.Standard.A1.Flex --shape-config '{"ocpus":1,"memoryInGBs":6}' \
        --image-id "$IMG" --subnet-id "$SN" --assign-public-ip false ${BOOT_ARGS[@]+"${BOOT_ARGS[@]}"} \
        --ssh-authorized-keys-file "$KEY" \
        --agent-config '{"pluginsConfig":[{"name":"Bastion","desiredState":"ENABLED"}]}' \
        --is-pv-encryption-in-transit-enabled true \
        --instance-options '{"areLegacyImdsEndpointsDisabled":true}' \
        --query data.id --raw-output 2>&1)
      # 輸出前面可能夾著 CLI 的警告，所以在整段輸出裡找 OCID，不只比對開頭
      id=$(grep -o 'ocid1\.instance\.[^" ]*' <<<"$out" | head -1)
      if [[ -n "$id" ]]; then IID=$id; break; fi
      status=$(grep -o '"status": [0-9]*' <<<"$out" | head -1 | grep -o '[0-9]*$')
      # 設定檔錯誤、網路中斷這類失敗沒有回應碼；請求也可能已經在 Oracle 那一端成功，所以不重送
      [[ -z "$status" ]] && die "讀不出回應碼，先用 oci compute instance list -c <compartment> --display-name $NAME 確認沒有同名主機再重跑：$out" 3
      [[ "$status" == 401 ]] && die "401，重跑 oci session authenticate"
      # 只有 500（容量不足）與 429（限流）等一段時間可能變好；400 這類代表請求本身有誤，重送也是同一個結果
      [[ "$status" != 500 && "$status" != 429 ]] \
        && die "建立請求回 ${status}，不重送：$(grep -o '"message": "[^"]*"' <<<"$out" | head -1)" 4
      if [[ "$status" == 429 ]]; then back=$(( back * 2 > 600 ? 600 : back * 2 )); else back=$(( back - 10 < 60 ? 60 : back - 10 )); fi
      wait=$(( back - 15 + RANDOM % 31 ))
      say 重送 "第 $n 次 ${status}：$(grep -o '"message": "[^"]*"' <<<"$out" | head -1)，${wait} 秒後再送"
      sleep "$wait"
    done
    echo "IID=$IID" >> "$HOSTENV"
    # 新主機的 host key 是新的，舊紀錄留著的話 ssh 會因為 host key 不符而拒絕連線
    : > "$KNOWN"; NEW=1
    wait_state RUNNING
    say 新建 "主機 $NAME 已 RUNNING（第 $n 次送出成功）" ;;
  *)
    # TERMINATING、MOVING、CREATING_IMAGE 這類狀態，或上面沒有列出的狀態：不猜下一步，停下來
    die "主機 ${NAME} 的狀態是 ${STATE}，這支腳本不處理這個狀態；等它變成 RUNNING、STOPPED 或 TERMINATED 再重跑" ;;
esac
# 查到的主機跟 host-<名稱>.env 最後記下的不是同一台時（例如在別處重建過），舊的 host key 紀錄對不上，也清掉
if [[ "$NEW" != 1 && "$IID" != "$LAST_IID" ]]; then
  echo "IID=$IID" >> "$HOSTENV"; : > "$KNOWN"; NEW=1
fi

# 2. 私有 IP 與 VNIC：重建之後兩者都會換
# 剛 RUNNING 的主機，VNIC 的掛載紀錄可能還沒出現，最多等 120 秒
for ((i = 0; i < 12; i++)); do
  VNIC=$(q compute instance list-vnics --instance-id "$IID" --query 'data[0].id' --raw-output) || fail "查 VNIC"
  [[ "$VNIC" == ocid1.vnic* ]] && break
  sleep 10
done
[[ "$VNIC" == ocid1.vnic* ]] || die "等了 120 秒仍查不到主機的 VNIC：$VNIC"
IP=$(q compute instance list-vnics --instance-id "$IID" --query 'data[0]."private-ip"' --raw-output) || fail "查私有 IP"
say 已存在 "VNIC 與私有 IP $IP"

# 3. NAT gateway：VCN 裡同名而 AVAILABLE 的那一個；已存在或新建都記進 ids.env
NAT=$(q network nat-gateway list -c "$C" --vcn-id "$V" \
  --query "data[?\"display-name\"=='$NAT_NAME' && \"lifecycle-state\"=='AVAILABLE'] | [0].id" --raw-output) || fail "查 NAT gateway"
if [[ "$NAT" == ocid1.natgateway* ]]; then say 已存在 "NAT gateway $NAT_NAME"
else
  NAT=$(q network nat-gateway create -c "$C" --vcn-id "$V" --display-name "$NAT_NAME" \
    --wait-for-state AVAILABLE --query data.id --raw-output) || fail "建 NAT gateway"
  [[ "$NAT" == ocid1.natgateway* ]] || die "建不出 NAT gateway：$NAT"
  say 新建 "NAT gateway $NAT_NAME"
fi
record NAT "$NAT"

# 4. 路由：私有子網路的路由表要有 service gateway 那一條與 0.0.0.0/0 → NAT；update 是整份替換，所以兩條一起寫。
#   路由表裡還有這兩條以外的規則時，改寫會把它們刪掉，所以先數，有就停下來
OTHER=$(q network route-table get --rt-id "$RT" \
  --query "data.\"route-rules\"[?destination!='0.0.0.0/0' && destination!='$SGCIDR'].destination" --raw-output) || fail "讀路由表"
OTHER=$(tr -d '[]" \n' <<<"$OTHER")
[[ -n "$OTHER" ]] && die "路由表裡有 0.0.0.0/0 與 service gateway 以外的規則（目的地 ${OTHER}），先把它們加進這一步的 --route-rules 再跑"
HAS=$(q network route-table get --rt-id "$RT" \
  --query "data.\"route-rules\"[?destination=='0.0.0.0/0' && \"network-entity-id\"=='$NAT'] | length(@)" --raw-output) || fail "讀路由表"
if [[ "$HAS" == 1 ]]; then say 已存在 "路由 0.0.0.0/0 → $NAT_NAME"
else
  q network route-table update --rt-id "$RT" --force --wait-for-state AVAILABLE --route-rules "[
 {\"destination\":\"$SGCIDR\",\"destinationType\":\"SERVICE_CIDR_BLOCK\",\"networkEntityId\":\"$SG\"},
 {\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$NAT\"}]" >/dev/null \
    || fail "改寫路由表"
  say 改寫 "路由表加上 0.0.0.0/0 → ${NAT_NAME}（service gateway 那一條保留）"
fi

# 5. 出站 NSG：只有出站 TCP 80、443 兩條規則；已存在或新建都記進 ids.env
NSGU=$(q network nsg list -c "$C" --vcn-id "$V" \
  --query "data[?\"display-name\"=='$NSG_NAME' && \"lifecycle-state\"=='AVAILABLE'] | [0].id" --raw-output) || fail "查 NSG"
if [[ "$NSGU" == ocid1.networksecuritygroup* ]]; then say 已存在 "NSG $NSG_NAME"
else
  NSGU=$(q network nsg create -c "$C" --vcn-id "$V" --display-name "$NSG_NAME" \
    --wait-for-state AVAILABLE --query data.id --raw-output) || fail "建 NSG"
  [[ "$NSGU" == ocid1.networksecuritygroup* ]] || die "建不出 NSG：$NSGU"
  say 新建 "NSG $NSG_NAME"
fi
record NSGU "$NSGU"
for port in 80 443; do
  N=$(q network nsg rules list --nsg-id "$NSGU" \
    --query "data[?direction=='EGRESS' && \"tcp-options\".\"destination-port-range\".min==\`$port\`] | length(@)" --raw-output) \
    || fail "讀 NSG 的規則"
  if [[ "$N" -ge 1 ]]; then say 已存在 "NSG 出站 TCP $port"
  else
    q network nsg rules add --nsg-id "$NSGU" --security-rules "[{\"direction\":\"EGRESS\",\"protocol\":\"6\",
\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"isStateless\":false,
\"tcpOptions\":{\"destinationPortRange\":{\"min\":$port,\"max\":$port}}}]" >/dev/null \
      || fail "加 NSG 出站 TCP $port 的規則"
    say 新建 "NSG 出站 TCP $port"
  fi
done

# 6. 把 NSG 掛到這台主機目前的 VNIC；--nsg-ids 是整份替換，所以保留 VNIC 原本掛著的其他 NSG
CUR=$(q network vnic get --vnic-id "$VNIC" --query 'data."nsg-ids"' --raw-output) || fail "讀 VNIC 的 NSG 清單"
CUR=$(tr -d '[]" \n' <<<"$CUR")
if [[ ",$CUR," == *",$NSGU,"* ]]; then say 已存在 "NSG 掛在 VNIC 上"
else
  LIST=$(echo "$CUR,$NSGU" | sed 's/^,//' | awk -F, '{for(i=1;i<=NF;i++) printf "%s\"%s\"", (i>1?",":""), $i}')
  q network vnic update --vnic-id "$VNIC" --nsg-ids "[$LIST]" --force >/dev/null || fail "改寫 VNIC 的 NSG 清單"
  say 改寫 "VNIC 的 NSG 清單加上 $NSG_NAME"
fi

# 7. port forwarding session：指向這台現在的私有 IP 與 22 port；session 最長 1 小時，每次重跑都開新的
SPFU=$(q bastion session create-port-forwarding --bastion-id "$B" \
  --target-private-ip "$IP" --target-port 22 \
  --ssh-public-key-file "$D/session_key.pub" --session-ttl 3600 --display-name "$NAME-pf" \
  --wait-for-state SUCCEEDED --wait-for-state FAILED --max-wait-seconds 600 \
  --query 'data.resources[0].identifier' --raw-output | tail -1) || fail "建 port forwarding session"
[[ "$SPFU" == ocid1.bastionsession* ]] || die "建不出 port forwarding session：$SPFU"
echo "SPF=$SPFU" >> "$HOSTENV"
say 新建 "port forwarding session（1 小時後失效）"

# 8. ssh 設定：整份由範本產生；known_hosts 只在主機那一步（第 1 步）換了一台主機時清空（新建，
#   或查到的主機跟 host-<名稱>.env 最後記下的不同），同一台主機還在時保留
cat > "$CONF" <<EOF
# 由 rebuild-ubuntu.sh 產生：經 Bastion 的 port forwarding session 登入 $NAME
Host ${NAME}-bastion
  HostName host.bastion.<區域>.oci.oraclecloud.com
  User $SPFU
  IdentityFile $D/session_key
  IdentitiesOnly yes

Host $NAME
  HostName $IP
  User ubuntu
  IdentityFile $D/verify-a1-key
  IdentitiesOnly yes
  ProxyJump ${NAME}-bastion
  UserKnownHostsFile $KNOWN
  StrictHostKeyChecking accept-new
EOF
if [[ "$NEW" == 1 ]]; then say 改寫 "ssh 設定 ${CONF}；known_hosts 已清空（換了一台主機）"
else say 改寫 "ssh 設定 ${CONF}；known_hosts 保留"; fi
echo "下一步：ssh -F $CONF $NAME 'cloud-init status --wait; uptime'"
```

腳本放在跟 `ids.env`、金鑰同一個目錄執行。要依環境換或確認的位置：

- **`<可用網域>`**（`oci iam availability-domain list` 查）與兩處 **`<區域>`**（查法在〈前置條件：沿用 Oracle Cloud 建立主機實測紀錄的網路、Bastion 與金鑰〉的 CLI 登入那一項）。
- **`--profile DEFAULT`**：`oci session authenticate` 時取的 profile 名稱，另外取了名字就兩處都換。
- **`NAT_NAME` 與 `NSG_NAME`**：要跟〈加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG〉建 NAT gateway 與 NSG 時用的名稱相同。名稱不同的話，腳本依名稱找不到既有的那一份，會再建一份 NAT gateway 與 NSG。
- **規格與映像檔**：`--shape-config` 的 1 OCPU、6 GB，以及查映像檔的 `"Canonical Ubuntu"`、`"24.04"`、`VM.Standard.A1.Flex` 三個篩選字串；換成別的作業系統時，產生 ssh 設定那一步的 `User ubuntu` 也要跟著換（Oracle Linux 是 `opc`）。
- **`BOOT_GB`**：只在新建主機時有作用，寫在指令前面（`BOOT_GB=60 ./rebuild-ubuntu.sh <主機名稱>`）。不給時開機磁碟是映像檔的預設大小，Ubuntu 24.04 扣區塊磁碟額度 47 GB；給了之後新主機的開機磁碟就是這個大小，`60` 實際建出 60 GiB（`lsblk -b` 讀到 64424509440 位元組，實跑）。`--boot-volume-size-in-gbs`、`size-in-gbs` 與額度用量寫的 GB，數值上都是 GiB（帳務明細與價目表的「GB」是哪一種沒有查）；映像檔預設的「50 GB」是十進位的 50.0 GB，也就是 46.6 GiB、`size-in-gbs` 47，所以 `BOOT_GB=50` 已經比預設大、扣 50（從 60 的實跑推論，50 沒有試）。主控台建立頁自訂大小的下限是 50 GB，出處見 [磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)〈開機磁碟的大小〉；給小於 50 的值時 CLI 回什麼，這次沒有試。加大之後，Ubuntu 的根目錄在開機時自動延伸到整顆磁碟（`df -h /` 讀到 58G）；換成別的映像檔時，檔案系統可能要另外延伸（Oracle Linux 的 `oci-growfs` 這類工具），否則多出的容量用不到（沒有實跑）。加大之前先讀免費額度還剩多少（`total-free-storage-gb-regional` 的 `available`，額度算的是開機磁碟與區塊磁碟的合計，指令在〈費用與額度：A1、開機磁碟、出站流量與 NAT gateway〉）：新磁碟比 `available` 大時，這一顆放不進剩餘額度，整顆不算免費額度。
- **`--session-ttl 3600`**：不能大於 Bastion 的 session 上限，查法在〈建 Ubuntu 24.04 主機與經由 port forwarding 登入〉。
- **金鑰的檔名**：`verify-a1-key`（登入主機）與 `session_key`（Bastion session）；序列主控台連線的重建腳本另外用 `console_rsa`，不存在時以 RSA 3072 位元（`-b 3072`）產生。
- **`ids.env` 裡七個鍵的值**。

`ids.env` 的鍵與查法在〈前置條件：沿用 Oracle Cloud 建立主機實測紀錄的網路、Bastion 與金鑰〉的表，格式是一行一個 `鍵=值`（例如 `C=<compartment 的 OCID>`），腳本開頭 `source` 它。NAT gateway 與 NSG 不論是已存在還是腳本新建的，腳本都把它們的 OCID 以 `NAT=` 與 `NSGU=` 記進檔尾，已經有同樣的一行就不重複寫，所以跑過一次之後，〈刪除這組資源的順序〉要填的值都在這個檔裡。`host-<名稱>.env` 是這一台主機的紀錄：腳本每次新建主機或 session 就在檔尾多加一行 `IID=` 或 `SPF=`，同一個鍵出現好幾次時，最後一行才是現在有效的值。腳本只讀它最後一行的 `IID=`，拿來跟這次查到的主機比對：不是同一台時（新建，或主機在別處重建過），舊的 host key 紀錄對不上，腳本就清空 known_hosts 並補記這次的 `IID=`。檔案裡還沒有任何一行 `IID=` 時（主機不是重建腳本建的，例如照〈建 Ubuntu 24.04 主機與經由 port forwarding 登入〉手動建的，或是腳本較早的版本建的），腳本拿空字串比對，同樣判成不是同一台、清空一次。

兩支腳本都假設 CLI 用 session token 登入（〈前置條件：沿用 Oracle Cloud 建立主機實測紀錄的網路、Bastion 與金鑰〉的 CLI 登入那一項）。改用 API 簽章金鑰的話，拿掉三處：`export` 那一行的 `OCI_CLI_AUTH=security_token`、開頭的 `oci session validate` 檢查，以及重建腳本重送迴圈裡每 1800 秒跑一次的 `oci session refresh`；拿掉之後 CLI 改用設定檔裡的 API 簽章金鑰（沒有實跑）。

重建腳本改寫路由表時，`--route-rules` 只寫 service gateway 與 NAT gateway 兩條，前提是這張路由表原本只有 service gateway 那一條（加上之前跑腳本時加進去的 0.0.0.0/0 那一條）。改寫之前，腳本先列出這兩條以外的規則，列得出任何一條就停下來，印出那幾條的目的地：`route-table update` 是整份替換，沒寫進 `--route-rules` 的規則會被刪掉。這時把那幾條規則加進腳本裡的 `--route-rules`，再重跑。

**輸出的讀法**：主機那一步（第 1 步）依查到的狀態印不同的行：

- **主機已經是 `RUNNING`**：印「已存在」。
- **主機被停止（`STOPPED`）**：印「啟動」（`STOPPED → RUNNING`）。`STOPPING` 時先等到 `STOPPED` 再啟動，`STARTING`、`PROVISIONING` 時等到 `RUNNING` 再印「已存在」。啟動失敗時（例如容量不足，推論）印出 `instance action` 的錯誤並以 2 結束。`STOPPED`、`STOPPING`、`STARTING`、`PROVISIONING` 四條在雲端跑過（結果在下面「在雲端實跑的結果」的「名稱不存在、同時另一份腳本碰到 `PROVISIONING`」與「主機 `STOPPED`、`STOPPING`、`STARTING`」兩項）；啟動失敗只用假的 `oci` 測過。
- **找不到還沒終止的同名主機**：印「新建」與映像檔名稱，容量不足（500）或被限流（429）時中間會有幾行「重送」（例：`[重送] 第 1 次 500："message": "Out of host capacity."，112 秒後再送`，這一行出自假的 `oci`）。建立請求回 500、429、401 以外的回應碼時（例如 `<可用網域>` 沒換掉而回 400），腳本印出回應碼與 `message` 就以 4 結束，不重送：這類回應代表請求本身有誤，重送幾次都是同一個結果，照訊息改好參數再跑。
- **主機停在其他狀態**（`TERMINATING`、`MOVING`、`CREATING_IMAGE` 這類）：腳本不猜下一步，印出狀態並以 2 結束，等它變成 `RUNNING`、`STOPPED` 或 `TERMINATED` 再重跑。

之後的各步，「已存在」代表那一項不必動，「新建」與「改寫」代表腳本這一次在雲端建了或改了資源：

- **VNIC 與私有 IP**（第 2 步）：一律印「已存在」與私有 IP；主機重建過時這個 IP 是新的。
- **NAT gateway**（第 3 步）與 **NSG 和它的兩條規則**（第 5 步）：VCN 裡已經有同名的就印「已存在」；只有第一次跑、或有人刪掉了它們時才印「新建」。
- **路由**（第 4 步）：已經有 0.0.0.0/0 指向 NAT gateway 那一條就印「已存在」；印「改寫」代表路由表被整份替換成 service gateway 與 NAT gateway 兩條，也就是先前少了 0.0.0.0/0 那一條，或它指向別的出口。
- **NSG 掛到 VNIC**（第 6 步）：印「改寫」代表 VNIC 原本沒有掛這個 NSG，主機重建之後的新 VNIC 一定走這一條。
- **port forwarding session**（第 7 步）：每次都印「新建」。
- **ssh 設定**（第 8 步）：每次都印「改寫」，並註明 known_hosts 是保留還是清空；清空代表這次的主機跟 `host-<名稱>.env` 最後記下的不是同一台，或那個檔案還沒有記下任何一台（主機不是重建腳本建的；實跑結果在下面的 `STOPPED` 那一項）。

任何一步印「錯誤」時腳本以 2 結束（建立請求被拒的 4 在上一項），錯誤那一行寫出是哪一步；`oci` 失敗時，冒號後面接的是那條指令寫在 stderr 的內容。修好之後重跑整支腳本即可，前面已經完成的步驟會印「已存在」。例外是建立請求的回應讀不出回應碼（exit 3）：設定檔錯誤、網路中斷都會走到這裡，而網路中斷時請求可能已經在 Oracle 那一端成功，所以重跑之前先用 `oci compute instance list -c <compartment 的 OCID> --display-name <主機名稱>` 確認沒有還在的同名主機。

**在雲端實跑的結果**（「主機已經是 `RUNNING`，沒有等待迴圈的版本」與「名稱不存在，較早的兩個版本」兩項跑的是上面三個版本裡較早的兩個，其餘都是現在這一版；各項用的版本寫在項目裡）：

- **NAT gateway 與 NSG 都不存在**（現在這一版，2026-10-27 09:32，跑的是 `./rebuild-ubuntu.sh`，不給名稱就是 `verify-ubuntu`；它的 NAT gateway 與 NSG 已在凌晨照〈刪除這組資源的順序〉刪掉）。exit 0，全程 32 秒。主機那一步印「已存在」（`RUNNING`），NAT gateway 印「新建」，路由印「改寫」（加上 0.0.0.0/0 → NAT gateway `verify-nat`，名稱是腳本的 `NAT_NAME`；保留 service gateway 那一條），NSG 與它的出站 TCP 80、443 兩條規則都印「新建」，掛 NSG 那一步印「改寫」；新的 NAT gateway 與 NSG 的 OCID 以新的一行接在 `ids.env` 檔尾。登入之後 `apt-get update` 下載 3982 kB，`curl https://archive.ubuntu.com/ubuntu/` 回 200，出站恢復。從 NAT gateway 那一行到掛 NSG 那一行共 14 秒，NAT gateway 與 NSG 的 `create` 帶的 `--wait-for-state AVAILABLE` 各約 3 秒（從 log 的時間戳推論）。
- **名稱不存在、同時另一份腳本碰到 `PROVISIONING`**（現在這一版，2026-10-27 09:33，接在上一項之後，所以 NAT gateway 與 NSG 已經存在）。先在背景跑一份新建主機的腳本（下面稱「新建的那一份」），本機另開一個 shell 迴圈查同名主機的狀態，查到 `PROVISIONING` 就對同一個名稱再跑一份（下面稱「建立中才開跑的那一份」）。這個迴圈是測試用的，不屬於重建腳本：

  ```bash
  # 迴圈裡的 oci 跟重建腳本一樣用 session token 登入
  export OCI_CLI_AUTH=security_token
  # 新建的那一份：放到背景跑，開機磁碟 60 GB；APID 記下它的程序編號
  BOOT_GB=60 ./rebuild-ubuntu.sh verify-ubuntu-60g > new.log 2>&1 &
  APID=$!
  # 新建的那一份還在跑時，每次查完等 3 秒再查（這次實際約 4 秒一次）；
  # 查到 PROVISIONING 就跑建立中才開跑的那一份。新建的那一份提早結束（例如建立請求回 400）時迴圈跟著結束
  while kill -0 "$APID" 2>/dev/null; do
    st=$(oci compute instance list -c <compartment 的 OCID> --display-name verify-ubuntu-60g \
      --query 'data[?"lifecycle-state"!=`TERMINATED`] | [0]."lifecycle-state"' --raw-output 2>/dev/null)
    [[ "$st" == PROVISIONING ]] && { ./rebuild-ubuntu.sh verify-ubuntu-60g > provisioning.log 2>&1; break; }
    sleep 3
  done
  wait "$APID"
  ```

  新建的那一份開跑後第 6 秒，迴圈還查不到主機；第 10 秒查到 `PROVISIONING`，建立中才開跑的那一份隨即開跑。這一台讓區塊磁碟的合計變成 201，60 GB 那一顆整顆不算免費額度（〈費用與額度：A1、開機磁碟、出站流量與 NAT gateway〉的「合計超過 200 GB 時」），所以照做這個測試會多出一顆不在免費額度裡的磁碟；這台在帳務明細出現它的計費項目之後，於 2026-10-27 11:58 終止，開機磁碟一起刪除（work request 65 秒 `SUCCEEDED`），區塊磁碟的兩條用量都回到 141；帳務的結果在〈費用與額度：A1、開機磁碟、出站流量與 NAT gateway〉的「合計超過 200 GB 時」。
  - **新建的那一份**：建立請求第一次送出就成功，exit 0，全程 87 秒。從印出「新建」主機（送出建立請求之前）到印出「已 RUNNING」約 50 秒。建立請求不帶 `--wait-for-state`，這段時間由 `wait_state` 每 10 秒查一次狀態，所以它輪詢了好幾次，建立中才開跑的那一份的 `wait_state` 在同一段時間也一樣（從時間戳與腳本推論，腳本不記每一次查詢）。這兩份腳本的 `wait_state` 是它的輪詢第一次在雲端實際等待，先前幾次都在第一次查詢就拿到目標狀態。網路那幾步都印「已存在」，掛 NSG 那一步印「改寫」（新主機的 VNIC），port forwarding session 從上一行到印出「新建」17 秒，ssh 設定印「known_hosts 已清空（換了一台主機）」。
  - **建立中才開跑的那一份**：查到主機是 `PROVISIONING`，走進 `STARTING|PROVISIONING` 那一條等到 `RUNNING`；它的 log 第一行（主機那一步）在新建的那一份印出「已 RUNNING」之後 4 秒印出「已存在」（等到 `RUNNING`），沒有再送建立請求，tenancy 裡只有一台 `verify-ubuntu-60g`。之後各步都印「已存在」，連掛 NSG 那一步也是（新建的那一份在 3 秒前掛上了），exit 0，全程 80 秒。建立中才開跑的那一份開跑時，新建的那一份已經把新主機的 `IID=` 寫進 `host-verify-ubuntu-60g.env`，所以建立中才開跑的那一份判成同一台，印「known_hosts 保留」（從它印「保留」、這個檔只有一行 `IID=`，以及腳本在開頭讀上一次的 `IID` 推得）。兩份腳本各建了一個 port forwarding session，`host-verify-ubuntu-60g.env` 因此有兩行 `SPF=`，ssh 設定是後寫的這一份。
  - **登入之後**：照產生的 ssh 設定登入，`cloud-init status --wait` 正常結束（輸出沒有留下），`apt-get update` 照常連到套件來源；`df -h /` 印出根目錄 58G。
  - **兩份同時跑的邊界**：這次只驗了後一份在 `PROVISIONING` 出現之後才開跑的情形。新建的那一份查到沒有同名主機之後、新主機在 `instance list` 查得到之前有一段空窗（這次迴圈在新建的那一份開跑後第 6 秒還查不到，空窗本身多長沒有量），後一份的查詢落在這段空窗時，結果是空的，會再送一次建立請求，建出第二台同名主機，A1 用量與開機磁碟額度都多扣一台主機的量。NAT gateway 與 NSG 是整個 VCN 共用、同樣依名稱先查後建：兩份腳本（名稱不同也一樣）在它們還不存在時同時跑，會各建一份，`ids.env` 記下兩行、`source` 時取後一行，路由表的「改寫」互相覆蓋，路由可能指向沒有記下的那一份。這兩種都是依腳本邏輯推論，沒有實跑；這次實跑時 NAT gateway 與 NSG 已經存在。所以同一個 VCN 一次只跑一份重建腳本。
  - **建立中的主機沒有變成 `RUNNING`**：`wait_state` 只比對 `RUNNING`，建立失敗、主機從 `PROVISIONING` 變成 `TERMINATED` 時，兩份腳本都會等滿 900 秒，再以「沒有變成 RUNNING」結束，訊息裡的狀態是最後一次查到的值（依腳本邏輯推論，沒有實跑）。
  - **不給 `BOOT_GB` 的新建**：在雲端只有較早的兩個版本跑過；現在這一版不給 `BOOT_GB` 時 `BOOT_ARGS` 是空陣列，建立請求那一行展開空陣列的寫法只用假的 `oci` 與本機的 bash 3.2 測過（寫法的理由在下面「腳本裡幾處寫法的理由」的 `BOOT_ARGS` 那一項）。

- **主機 `STOPPED`、`STOPPING`、`STARTING`**（現在這一版，2026-10-27 對 `verify-ubuntu` 連跑四次，`STARTING` 試了兩次；每次之前用 `oci compute instance action --instance-id <主機的 OCID> --action STOP` 或 `--action START` 讓主機落在那個狀態）。四次都是 exit 0，網路設定那幾步都印「已存在」，port forwarding session 每次都印「新建」。各次全程的秒數不同，差在 API 回應的快慢：port forwarding session 那一行以外，log 各行的時間戳之間都不到 10 秒，沒有任何一步走進 `sleep`，而 port forwarding session 那一行就從 8 秒到 22 秒不等。下面的「從腳本開始到這一行」是用 log 最後一行的時間減去全程秒數推算的，時間戳只到秒，誤差約 1 秒：
  - **`STOPPED`**：先帶 `--wait-for-state STOPPED` 停機，6 秒回 `STOPPED`。腳本全程 28 秒，第一行印「啟動」（`STOPPED → RUNNING`），從腳本開始到這一行約 9 秒，`instance action` 的 START 等到 `RUNNING` 包含在內。登入時 `uptime` 是 `up 0 min`，`cloud-init status --wait` 回 `done`，`apt-get update` 照常連到套件來源。
  - **`STOPPING`**：送出 STOP 不帶 `--wait-for-state`，CLI 回傳時是 `STOPPING`，再查一次仍是 `STOPPING`，接著跑腳本。腳本查到 `STOPPING`，全程 35 秒，第一行印「啟動」（`STOPPING → RUNNING`），從腳本開始到這一行約 9 秒。這 9 秒裡有登入檢查、查主機、查狀態、`wait_state` 的查詢與 START 共五次 API 呼叫，`wait_state` 要是睡過一次 10 秒就不可能少於 10 秒，所以它第一次查時主機已經是 `STOPPED`，沒有進 `sleep`（從時間戳推論）。
  - **`STARTING`**：試了兩次，第二次才走到這條分支。兩次都是主機停好之後送出 START 不帶 `--wait-for-state`。第一次在送出 START 與跑腳本之間多查了一次狀態（回 `STARTING`），腳本開始時主機已經是 `RUNNING`，第一行印「已存在」（`RUNNING`），全程 21 秒，走的是主機已經是 `RUNNING` 的那一條；從腳本開始到第一行只有約 2 秒，所以 `STARTING` 在多查的那一次之後幾秒內就變成 `RUNNING`（推論，沒有量 `STARTING` 維持多久）。第二次送出 START 之後立刻跑腳本：腳本查到 `STARTING`，進 `wait_state` 之後第一次查就已經是 `RUNNING`，沒有進到兩次查詢之間的 10 秒 `sleep`（從腳本開始到第一行只有約 4 秒推論）；全程 55 秒，第一行印「已存在」（等到 `RUNNING`）。
  - **VNIC 的等待迴圈**：四次的 VNIC 那一行都在主機那一行之後 3 到 9 秒內印出，主機沒有換過、VNIC 一直掛著，迴圈第一次查就拿到，沒有進 `sleep`（從時間戳推論）。
  - **known_hosts**：`STOPPED` 那一次印「known_hosts 已清空（換了一台主機）」，而主機是同一台。`verify-ubuntu` 是手動建的，之後只跑過腳本較早的版本（那一版只在新建主機時記 `IID`），`host-verify-ubuntu.env` 裡只有 session 的紀錄、沒有 `IID` 那一行，腳本拿空字串跟查到的 OCID 比，判成不同，同時寫進這一行；之後三次都印「保留」。下面假的 `oci` 測試表裡「主機 `STOPPED`」那一列印「保留」，是因為那一組測試的 `host-<名稱>.env` 已經記著同一台的 `IID`。清空之後，ssh 設定的 `StrictHostKeyChecking accept-new` 讓下一次登入重新記下這台的 host key（`Permanently added '<私有 IP>' (ED25519)`），登入沒有受影響；主機沒有重裝，host key 應該沒換，但清空之前的紀錄已經是空的，沒有舊的 key 可以比對。

- **主機已經是 `RUNNING`，沒有等待迴圈的版本**：exit 0，全程 34 秒；主機那一步到掛 NSG 那一步都印「已存在」，port forwarding session 的建立佔了其中約 17 秒，最後兩行是 session 的「新建」與 ssh 設定的「改寫」。照產生的 `ssh-verify-ubuntu.conf` 登入之後，`apt-get update` 照常連到 Ubuntu 的套件來源。
- **名稱不存在，較早的兩個版本**（2026-10-27 凌晨建 `verify-ubuntu-rebuild`）：建立請求第一次送出就成功。沒有等待迴圈的版本在印出「已 RUNNING」之後，接著以「查不到主機的 VNIC」結束（exit 2）；加上等待迴圈的版本從主機已經是 `RUNNING` 的狀態接著跑，exit 0，80 秒：掛 NSG 那一步印「改寫」，替新主機的 VNIC 掛上出站 NSG；port forwarding session 這一次要 64 秒才變成 `SUCCEEDED`，比既有主機的那一次長。登入時主機已開機 3 分鐘，`cloud-init status --wait` 立刻回 `done`，`apt-get update` 9 秒下載 39.9 MB，速率 4468 kB/s。

**用假的 `oci` 測的結果**（現在這一版；假的 `sleep` 只記秒數，所以秒數是腳本算出來要等的值。重送前的等待依回應碼調整，再加減 15 秒的隨機抖動，每次跑的值不同）。主機那一步與建立請求的情形：

| 情形                                      | 結束碼 | 建立請求送出次數 | 記下的等待                   | known_hosts |
| ----------------------------------------- | ------ | ---------------- | ---------------------------- | ----------- |
| 名稱不存在，新主機先回 `PROVISIONING`     | 0      | 1                | `wait_state` 等 10 秒一次    | 清空        |
| 名稱不存在，加 `BOOT_GB=60`               | 0      | 1                | `wait_state` 等 10 秒一次    | 清空        |
| 主機已經是 `RUNNING`                      | 0      | 0                | 無                           | 保留        |
| 主機 `STOPPED`                            | 0      | 0                | 無（`instance action` 啟動） | 保留        |
| 主機 `TERMINATING`                        | 2      | 0                | 無                           | 保留        |
| 建立請求先回 500、第二次成功              | 0      | 2                | 重送前 95–125 秒，之後 10 秒 | 清空        |
| 建立請求的輸出在 OCID 前面多一行警告      | 0      | 1                | `wait_state` 等 10 秒一次    | 清空        |
| 建立請求的輸出讀不出回應碼                | 3      | 1                | 無                           | 保留        |
| 主機 `PROVISIONING`、再查一次變 `RUNNING` | 0      | 0                | `wait_state` 等 10 秒一次    | 保留        |
| 主機 `STOPPING`、再查一次變 `STOPPED`     | 0      | 0                | 無（`instance action` 啟動） | 保留        |
| 建立請求回 401                            | 2      | 1                | 無                           | 保留        |
| 建立請求回 400                            | 4      | 1                | 無                           | 保留        |
| 建立請求先回 500、第二次回 400            | 4      | 2                | 重送前 95–125 秒             | 保留        |
| 主機 `STARTING`、再查一次變 `RUNNING`     | 0      | 0                | 無                           | 保留        |
| 主機查得到、狀態讀不出                    | 2      | 0                | 無                           | 保留        |
| 建立請求連回兩次 429、第三次成功          | 0      | 3                | 重送前約 240 與 480 秒       | 清空        |
| 查不到映像檔                              | 2      | 0                | 無                           | 保留        |
| 主機 `RUNNING`，但跟上次記下的不是同一台  | 0      | 0                | 無                           | 清空        |

加 `BOOT_GB=60` 的那一列，假的 `oci` 記下的建立請求帶著 `--boot-volume-size-in-gbs 60`；沒有給 `BOOT_GB` 的那幾列，建立請求裡沒有這個選項。每一種會送出建立請求的情形，第一次送出之前都先延長了一次 token（`last_refresh=0`）；回 400 的兩種情形印出的 `message` 是假的 `oci` 自己編的，Oracle 實際回的訊息這次沒有看過。查不到映像檔時，錯誤那一行是「查不到 Ubuntu 24.04 的 A1 映像檔：查詢結果是空的」。

網路設定那幾步的情形，以及讓單一種 `oci` 呼叫失敗的情形（主機都已經是 `RUNNING`）：

| 情形                                               | 結束碼 | 結果                                                                            |
| -------------------------------------------------- | ------ | ------------------------------------------------------------------------------- |
| NAT gateway 與 NSG 都不存在、路由表少一條          | 0      | 新建 NAT gateway、NSG 與兩條規則，改寫路由表與 VNIC；兩者的 OCID 記進 `ids.env` |
| 路由表少了 0.0.0.0/0 那一條                        | 0      | 改寫路由表，寫進去的 service gateway 目的地是 `ids.env` 裡 `SGCIDR` 的值        |
| 路由表裡有 0.0.0.0/0 與 service gateway 以外的規則 | 2      | 不改寫，印出那條規則的目的地                                                    |
| VNIC 已經掛著另外兩個 NSG                          | 0      | `vnic update` 的 `--nsg-ids` 是原本那兩個加上出站 NSG                           |
| 查同名主機失敗                                     | 2      | 不建第二台；印出假的 `oci` 寫在 stderr 的錯誤                                   |
| 啟動主機（`STOPPED` 時）失敗                       | 2      | 不印「啟動」，印出錯誤                                                          |
| 查 NAT gateway 失敗                                | 2      | 不建第二個 NAT gateway                                                          |
| 讀路由表失敗、改寫路由表失敗                       | 2      | 讀取失敗時不改寫；改寫失敗時不印「改寫」                                        |
| 讀 NSG 的規則失敗、加 NSG 規則失敗                 | 2      | 讀取失敗時不加規則；加規則失敗時不印「新建」                                    |
| 讀 VNIC 的 NSG 清單失敗、改寫 VNIC 失敗            | 2      | 讀取失敗時不改寫，原本掛著的 NSG 不會被替換掉；改寫失敗時不印「改寫」           |

這幾種失敗，腳本在加上錯誤處理之前都照樣往下走：查同名主機失敗時當成找不到主機，再建一台；啟動或寫入失敗時照樣印「啟動」「改寫」「新建」；讀路由表或 VNIC 失敗時照樣整份替換，刪掉原本的規則或 NSG（審查時用同一支假的 `oci` 重現過）。假的 `oci` 測的是腳本的分支與結束碼，測不到雲端的回應格式與等待時間。

序列主控台連線的重建腳本（下面那一支）用同一支假的 `oci` 測了這幾種情形：主機已有 `ACTIVE` 的連線時印「已存在」、不呼叫 `create`，設定檔填的是那條既有連線的 OCID（exit 0）；沒有時呼叫一次 `create`、印「新建」（exit 0）；金鑰不存在、而主機已有 `ACTIVE` 的連線時，產生新金鑰、刪掉舊連線、再建一條（exit 0）；以上三種結束時印出的「用完就刪」那條 `delete`，代入的都是這次設定檔裡用的那條連線的 OCID；找不到 `RUNNING` 的同名主機時印「找不到 RUNNING 的 verify-ubuntu，先跑 rebuild-ubuntu.sh」並以 2 結束；查主機、查連線、建連線任一條失敗時印出錯誤並以 2 結束。

腳本裡幾處寫法的理由：

- **`q` 保留結束碼與 stderr**：OCI CLI 3.95.1 在 `--query` 的結果是空的時候，stdout 沒有輸出、結束碼是 0，只在 stderr 印 `Query returned empty result, no output to show.`（讀 CLI 套件的 `cli_util.py` 確認的）；查詢失敗時 stdout 同樣是空的。所以空字串本身分不出「查無結果」與「查詢失敗」，要看結束碼：`q` 把 stderr 存進暫存檔、照原樣回傳 `oci` 的結束碼，呼叫的地方失敗就以 `fail` 停下來並印出 stderr。主機那一步只有在查詢成功、結果又是空的時候，才進建立分支。
- **主機的狀態由 `wait_state` 自己查**：`oci compute instance get` 沒有 `--wait-for-state`，帶了這個選項時 CLI 印出 `Error: No such option '--wait-for-state'.` 就結束；沒有等待迴圈的版本把 stderr 丟掉，這個錯誤沒有印出來，腳本在主機還沒 `RUNNING` 時就往下走。哪些子命令有這個選項用 `oci <子命令> --help` 查，這次查到有的是 `compute instance launch`、`compute instance action`、`compute instance terminate`、`network nat-gateway create`、`network route-table update`、`network nsg create`、`network vnic update`、`bastion session create-port-forwarding` 與 `compute instance-console-connection create`；沒有的是 `compute instance get`、`compute instance list-vnics`、`network nsg rules add` 與 `network nsg rules list`。VNIC 另外等最多 120 秒：剛送出建立請求約 5 秒的主機，`list-vnics` 在雲端實跑時回過空值（那一版的等待沒有作用，當時主機可能還沒到 `RUNNING`）。
- **變數後面直接接中文的位置寫成 `${NAME}`**：macOS 的 `/bin/bash`（3.2.57）把變數名後面緊接的全形字元讀成變數名的一部分，`"主機 $NAME（RUNNING）"` 在 `set -u` 之下以 `NAME�: unbound variable` 結束。訊息裡的 `�` 不是文章的亂碼：bash 把全形括號「（」的 UTF-8 編碼（三個位元組）的第一個位元組當成變數名的一部分，照原樣印出那一個位元組，終端機顯示不出單獨一個位元組，就印成 `�`。用 `LC_ALL=C grep -n '\$[A-Za-z_][A-Za-z0-9_]*[^ -~]' <腳本>` 找得出這類位置，這一版跑這條是 0 行。
- **`BOOT_ARGS` 展開成 `${BOOT_ARGS[@]+"${BOOT_ARGS[@]}"}`**：同一個 bash 3.2.57 在 `set -u` 之下展開空陣列 `"${BOOT_ARGS[@]}"` 時，以 `BOOT_ARGS[@]: unbound variable` 結束（實跑）。沒有給 `BOOT_GB` 時陣列是空的。展開寫在 `out=$(oci …)` 的命令替換裡，照一般寫法，命令替換印出 `BOOT_ARGS[@]: unbound variable` 之後回傳空字串，腳本照樣往下走、讀不出回應碼，以 3 結束，訊息要讀者去查同名主機，看起來像網路中斷（依腳本結構與本機 bash 3.2 的最小重現推得，整支腳本沒有用一般寫法跑過）。重建既有主機的路徑走不到那一行，只測既有主機時看不出來。`${A[@]+…}` 在陣列有元素時才展開後面那一段，空陣列就什麼都不印。

**序列主控台連線的重建腳本**：主機沒有 `ACTIVE` 的序列主控台連線才建，並產生跟〈序列主控台：RSA 金鑰、建立連線、ProxyJump 設定與看到的開機輸出〉相同寫法的 `ssh-console.conf`：

```bash
#!/bin/bash
# 替主機建序列主控台連線（instance console connection），並產生 ssh-console.conf。
# 主機已經有 ACTIVE 的連線就沿用；沒有就用 console_rsa.pub 建一條（金鑰不存在時先產生 RSA 3072，
#   這時既有的連線登記的是舊的公鑰，先刪掉再建）。
# 官方給的連線字串在 ssh 外面再包一層 ssh 當跳板；這裡寫成等價的 ProxyJump 設定，不在本機執行任意命令。
# 連線只在排查時存在：要排查時跑這支建一條，用完以結尾印出的 delete 指令刪掉。
# 用法：./rebuild-console.sh [主機名稱]（預設 verify-ubuntu）。連線：ssh -tt -F ssh-console.conf verify-console
# 結束碼：0 完成；2 登入過期、找不到主機、oci 失敗（印出它的 stderr）或建不出連線。
set -uo pipefail
# OCI CLI 是 Python 程式；PYTHONWARNINGS=ignore 關掉 Python 直譯器印的警告，不讓警告行混進要解析的輸出
export OCI_CLI_AUTH=security_token PYTHONWARNINGS=ignore
D=$(cd "$(dirname "$0")" && pwd)
source "$D/ids.env"
NAME=${1:-verify-ubuntu}
REGION=<區域>
CONF="$D/ssh-console.conf"
KNOWN="$D/known_hosts_console"
ERR=$(mktemp "${TMPDIR:-/tmp}/rebuild-console.XXXXXX"); trap 'rm -f "$ERR"' EXIT
ts() { date +%m-%d\ %H:%M:%S; }
say() { echo "$(ts) [$1] $2"; }
die() { echo "$(ts) [錯誤] $1" >&2; exit 2; }
# 查詢與寫入用的包裝：stderr 存進 $ERR 那個暫存檔，濾掉兩種不是結果的提示行（Python 的 SyntaxWarning，
#   與 CLI 建議改用 `oci -i` 的 Interactive mode 那一行），結束碼照 oci 自己的回傳。
#   CLI 的 --query 結果是空的時候 stdout 什麼都不印，所以空字串要搭配結束碼 0 才代表查無結果
q() {
  local out rc
  out=$(oci "$@" 2>"$ERR"); rc=$?
  [[ -n "$out" ]] && grep -v -e SyntaxWarning -e 'Interactive mode' <<<"$out"
  return $rc
}
# q 失敗時停下來，印出 oci 寫在 stderr 的內容
fail() { die "${1}失敗：$(tr '\n' ' ' < "$ERR")"; }

oci session validate --profile DEFAULT >/dev/null 2>&1 \
  || die "CLI session 過期，先跑 oci session authenticate --region $REGION --profile-name DEFAULT"

IID=$(q compute instance list -c "$C" --display-name "$NAME" \
  --query "data[?\"lifecycle-state\"=='RUNNING'] | [0].id" --raw-output) || fail "查 RUNNING 的主機"
[[ "$IID" == ocid1.instance* ]] || die "找不到 RUNNING 的 ${NAME}，先跑 rebuild-ubuntu.sh"

# 序列主控台連線只收 RSA 公鑰
NEWKEY=0
if [[ ! -f "$D/console_rsa" ]]; then
  ssh-keygen -q -t rsa -b 3072 -N '' -C verify-console -f "$D/console_rsa" || die "產生 RSA 金鑰失敗"
  NEWKEY=1; say 新建 "RSA 金鑰 console_rsa"
else say 已存在 "RSA 金鑰 console_rsa"; fi

CID=$(q compute instance-console-connection list -c "$C" --instance-id "$IID" \
  --query "data[?\"lifecycle-state\"=='ACTIVE'] | [0].id" --raw-output) || fail "查序列主控台連線"
# 剛產生新金鑰時，既有的連線登記的是舊的公鑰，用新私鑰連不上：先刪掉它，再用新的公鑰建一條
if [[ "$NEWKEY" == 1 && "$CID" == ocid1.instanceconsoleconnection* ]]; then
  q compute instance-console-connection delete --instance-console-connection-id "$CID" --force \
    --wait-for-state DELETED >/dev/null || fail "刪掉用舊公鑰建的序列主控台連線"
  say 改寫 "刪掉用舊公鑰建的序列主控台連線"
  CID=""
fi
if [[ "$CID" == ocid1.instanceconsoleconnection* ]]; then say 已存在 "序列主控台連線"
else
  CID=$(q compute instance-console-connection create --instance-id "$IID" \
    --ssh-public-key-file "$D/console_rsa.pub" --wait-for-state ACTIVE --query data.id --raw-output | tail -1) \
    || fail "建序列主控台連線"
  [[ "$CID" == ocid1.instanceconsoleconnection* ]] || die "建不出序列主控台連線：$CID"
  say 新建 "序列主控台連線"
fi

cat > "$CONF" <<EOF
# 由 rebuild-console.sh 產生：$NAME 的序列主控台。官方連線字串的跳板改寫成 ProxyJump。
Host verify-console-gw
  HostName instance-console.$REGION.oci.oraclecloud.com
  Port 443
  User $CID
  IdentityFile $D/console_rsa
  IdentitiesOnly yes
  UserKnownHostsFile $KNOWN
  StrictHostKeyChecking accept-new
  HostKeyAlgorithms +ssh-rsa
  PubkeyAcceptedAlgorithms +ssh-rsa

Host verify-console
  HostName $IID
  User $CID
  ProxyJump verify-console-gw
  IdentityFile $D/console_rsa
  IdentitiesOnly yes
  UserKnownHostsFile $KNOWN
  StrictHostKeyChecking accept-new
  HostKeyAlgorithms +ssh-rsa
  PubkeyAcceptedAlgorithms +ssh-rsa
EOF
: > "$KNOWN"
say 改寫 "$CONF 與 known_hosts_console"
echo "連線：ssh -tt -F $CONF verify-console（離開：先按 Enter，再輸入 ~.）"
# 序列主控台連線是救援入口，平時不留：排查完就刪
echo "用完就刪：oci compute instance-console-connection delete --instance-console-connection-id $CID --force --wait-for-state DELETED"
```

`<區域>` 換成自己的區域識別碼；`ids.env` 只用到 `C`。這支腳本每次都清空 `known_hosts_console`，下一次連線時由 `StrictHostKeyChecking accept-new` 重新記下跳板與目的地的 host key；代價跟〈建 Ubuntu 24.04 主機與經由 port forwarding 登入〉那一段寫的相同，第一次連線沒有比對指紋。這份檔案不依主機名稱分檔，給不同主機跑時共用同一份。`console_rsa` 不存在而這次新產生時，主機上既有的 `ACTIVE` 連線登記的是舊的公鑰，新私鑰連不上，所以腳本先刪掉那條連線再用新公鑰建一條。對新建的 `verify-ubuntu-rebuild` 實跑的是前一版：訊息還寫「主控台連線」、還沒有錯誤處理與換金鑰處理，建連線的步驟跟現在相同。結果是 exit 0，15 秒，印「已存在」（RSA 金鑰）、「新建」（序列主控台連線）與「改寫」（設定檔）。照設定檔連上之後印出 Oracle 對序列主控台連線的說明文字；本機用 `alarm` 讓 ssh 在 25 秒後結束，這段時間裡沒有按 Enter，所以登入提示沒有出現。

**重建之後要重做的事**，依順序：

1. `ssh -F ssh-verify-ubuntu.conf verify-ubuntu 'cloud-init status --wait; uptime'`（設定檔名依主機名稱）：等首次開機設定跑完（這次約 1 分鐘）。
2. 主機被刪除重建時，映像檔又是建立那一天的版本：照〈加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG〉最後那兩條，`sudo unattended-upgrade` 之後 `sudo systemctl reboot`（這次 402 秒、升級 64 個套件），才把映像檔之後的安全更新補上。只是被停止再啟動時，更新還在，不必重做。
3. 序列主控台連線平時不留，重建之後不必另外建。要排查時才跑序列主控台連線的重建腳本，再 `ssh -tt -F ssh-console.conf verify-console`；排查完用腳本結尾印出的那條 `delete` 刪掉。

**耗時**：這次量到的是單步的時間，建立請求送出到回傳約 4 秒，約 20 秒後的下一次查詢時主機已經是 `RUNNING`，cloud-init 約 1 分鐘，port forwarding session 約 1 分鐘，`unattended-upgrade` 402 秒，核心開始開機到登入提示約 27 秒。重建腳本在主機還在時 34 秒跑完，主機停止、停止中、啟動中三種狀態各 28、35、55 秒（差在各步 API 的回應與 port forwarding session 的快慢）；名稱不存在的那一次，那一版沒有等待主機的狀態，建立請求到 `RUNNING` 的確切時間沒有量到（2 分 30 秒後重跑時已經是 `RUNNING`），之後接上網路與登入的部分 80 秒，其中 port forwarding session 佔 64 秒；這一版從建主機那一步一次跑到底的時間沒有量。A1 容量不足時，建立那一步要重送，時間取決於區域當時的容量，重送的間隔與限流門檻在建主機那篇〈重送建立請求：CLI 自己的重送、限流門檻與重送腳本〉。

### 重建的其他做法：用 IaC 描述這組資源、建立時交給 cloud-init 升級、只靠手動

- **用 Terraform 描述主機與網路**：主機被刪除之後 `terraform apply` 就重建，`plan` 也會列出被刪掉的資源；回收這種狀況剛好是 [Infrastructure as Code (IaC)](/infra/knowledge-cards/iac/) 擅長處理的 [Drift（設定漂移）](/infra/knowledge-cards/drift/)：宣告的狀態與實際不一致。代價是要先把已經用 CLI 建好的資源匯入 state（做法見 [Unmanaged Resource 批次 Import 工作流](/infra/takeover/partial-iac-bulk-import/)）；這次沒有做。
- **建立時交給 cloud-init 升級套件**：`oci compute instance launch` 的 `--user-data-file` 放一份 cloud-config，讓 cloud-init 在首次開機時就跑套件升級（cloud-config 的 `package_upgrade: true`），重建之後不必再手動跑 `unattended-upgrade`。前提是主機首次開機時已經有出站，所以要搭配上面〈出站的其他做法：security list、建主機時就掛 NSG、限縮出站的目的地與不加出站〉的「建主機時就掛上 NSG」。官方提醒初始化腳本裡不要放會觸發重開機的指令，否則可能讓主機建立失敗（[代理程式、中繼資料服務、初始化腳本、維護行為與標籤](/infra/cloud-providers/vm-options/management/)〈初始化腳本〉），所以 cloud-config 只升級、不重開機，換上新核心的那一次重開機留到登入之後手動做，或由重建腳本在主機變成 `RUNNING`、cloud-init 跑完之後再觸發。這一項沒有實跑。
- **只靠手動照〈建 Ubuntu 24.04 主機與經由 port forwarding 登入〉與〈加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG〉兩節重做**：步驟都在本篇，不需要腳本；代價是每一步的 OCID 要重查，漏掉 NSG 掛到新 VNIC 這一步時，主機看起來建好了，`apt-get update` 卻又回到逾時，而且沒有任何錯誤訊息指出原因。

## 費用與額度：A1、開機磁碟、出站流量與 NAT gateway

- **A1**：帳號篇記錄的 Always Free 額度是每月 1,500 OCPU 小時與 9,000 GB 小時（相當於 2 OCPU、12 GB 整月開著）。2026-10-26 讀到的 Oracle 的 Compute 價目頁（頁名這次沒有記下）寫的是「Each paid tenancy gets the first 3,000 OCPU hours and 18,000 GB hours per month for free」，對象是付費 tenancy，相當於 4 OCPU、24 GB 整月開著。這個 tenancy 是付費帳戶：重建腳本實跑之前，同一個 tenancy 已經有三台各 1 OCPU、6 GB 的 A1 主機在跑（2026-10-27 用 `oci compute instance list` 查到 `verify-a1-ol`、`verify-origin`、`verify-ubuntu` 三台是 `RUNNING`），腳本建出的第四台讓合計變成 4 OCPU、24 GB，剛好等於付費 tenancy 每月的免費量，建立沒有被擋下。試用結束那一刻、A1 合計超過 2 OCPU、12 GB 就全部停用的規則，只管沒有升級的帳號（帳號篇〈Always Free 的額度與它綁在 home region 上的範圍〉）；付費帳戶超出免費量的部分照一般價格計費（帳號篇〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉）。免費量是帳務的規則，能建出幾個 OCPU 由 compute 的 service limit 決定，兩者是分開的：查法跟下面開機磁碟那一項同一組，`oci limits definition list -c <tenancy 的 OCID> --service-name compute` 先找出 A1 的 OCPU 與記憶體限制名稱，再用 `oci limits resource-availability get` 帶那個名稱與 `--availability-domain <可用網域>` 查（兩條都沒有實跑）。超出免費量時，停止主機對 OCPU 與記憶體費用的影響見 [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/operations/09-host-lifecycle/suspend-and-resume-service/)〈暫停期間仍在計費的資源〉；停止的主機的開機磁碟照樣佔著區塊磁碟額度。
- **開機磁碟**：每台的開機磁碟從 Always Free 的 200 GB 區塊磁碟額度裡扣；放不進剩餘額度的那一顆整顆在額度外（下面「合計超過 200 GB 時」）。這顆磁碟有三種寫法：序列主控台記下的開機輸出寫 `[sda] 97677312 512-byte logical blocks: (50.0 GB/46.6 GiB)`；`oci bv boot-volume list` 對 `verify-ubuntu` 回 `size-in-mbs` 47694，正好是 97677312 × 512 位元組換成 MiB；同一條回的 `size-in-gbs` 是 47，是 46.6 GiB 進位。另外兩台 Oracle Linux 主機的 `size-in-mbs` 是 47719，換成 GiB 同樣是 46.6，`size-in-gbs` 同樣是 47。每顆磁碟的大小與額度的用量用下面三條查（2026-10-27 實跑）。`<tenancy 的 OCID>` 是最上層 compartment（root）的 OCID，`~/.oci/config` 裡 `tenancy=` 那一行就是它。這次的 compartment 直接建在 root 底下，所以 `oci iam compartment get --compartment-id <compartment 的 OCID> --query 'data."compartment-id"' --raw-output` 印出的上一層也是 tenancy 的 OCID（實跑，跟 `tenancy=` 的值相同）；compartment 是巢狀的時候，這條印出的是另一個 compartment，要讀 `~/.oci/config`。

  ```bash
  # 列出每顆還沒終止的開機磁碟與它的大小；<可用網域> 是建主機時用的那一個
  oci bv boot-volume list -c <compartment 的 OCID> --availability-domain <可用網域> \
    --query 'data[?"lifecycle-state"!=`TERMINATED`].{name:"display-name",gb:"size-in-gbs",mb:"size-in-mbs"}' --output table
  # 列出區塊儲存的限制名稱；區域層的免費額度叫 total-free-storage-gb-regional，
  # 可用網域層另有一個 total-free-storage-gb，這個 tenancy 兩者的上限都是 200。
  # 付費 tenancy 合計超過 200 時兩者都沒有擋下建立，放不進的那顆磁碟不算進兩者的 used（下面「合計超過 200 GB 時」）
  oci limits definition list -c <tenancy 的 OCID> --service-name block-storage --all \
    --query 'data[].{name:name,desc:description,scope:"scope-type"}' --output table
  # 查用量：used 是已經扣掉的量，available 是還剩的量。
  # 查可用網域層那一個時，--limit-name 換成 total-free-storage-gb，並加 --availability-domain <可用網域>
  oci limits resource-availability get -c <tenancy 的 OCID> --service-name block-storage \
    --limit-name total-free-storage-gb-regional
  ```

  2026-10-27 終止 `verify-ubuntu-rebuild` 之後查，剩三台主機時回 `"used": 141`、`"available": 59`，可用網域層那一個查出來的數字相同。這個 tenancy 裡只有這一個 compartment（`oci iam compartment list -c <tenancy 的 OCID> --compartment-id-in-subtree true --all` 只列出它），它與 root 底下都沒有開機磁碟以外的區塊磁碟（兩處的 `oci bv volume list -c <…的 OCID>` 都列不出任何一顆，root 底下也沒有開機磁碟；都是實跑），而 141 正好是三顆 `size-in-gbs` 47 的合計；三顆的 MiB 加起來是 139.8 GiB，總和進位會是 140，所以進位是每一顆各自做的。由此推論額度扣的數字就是每顆磁碟的 `size-in-gbs`：照預設大小建的主機，每台扣 47（額度以 GB 標示，數值是 46.6 GiB 進位），不是 50。照這個推算，終止 `verify-ubuntu-rebuild` 之前四台同時存在時合計扣 188，額度還剩 12（四台同時存在時沒有查用量，那台照同一個映像檔與預設大小算 47）。

  **合計超過 200 GB 時**（2026-10-27 09:33 實跑）：在扣了 141 的狀態下，用重建腳本以 `BOOT_GB=60` 建 `verify-ubuntu-60g`（建出 60 GiB，`size-in-gbs` 60；這裡的 GB 數值上都是 GiB，見〈被回收之後的重建：怎麼發現、留下與消失的資源、重建腳本〉的 `BOOT_GB` 那一項），三顆 47 加一顆 60 合計 201。建立請求沒有被擋下，主機照常建好（這個 tenancy 沒有設 compartment quota；用 quota 替區塊儲存另設上限、讓超額的建立被擋下的做法，這次沒有試）。之後免費額度的用量與全部區塊磁碟的合計（`total-storage-gb`，上面的指令沒有查的第三條限制）不再相同：

  | 限制                             | 範圍     | 上限   | used | 代表的量                         |
  | -------------------------------- | -------- | ------ | ---- | -------------------------------- |
  | `total-free-storage-gb-regional` | 區域     | 200    | 141  | 算進 Always Free 額度的磁碟合計  |
  | `total-free-storage-gb`          | 可用網域 | 200    | 141  | 同上，以可用網域計               |
  | `total-storage-gb`               | 可用網域 | 61,440 | 201  | 全部區塊磁碟的合計，含付費的磁碟 |

  表裡的可用網域是 availability domain，區域裡的一個資料中心（跨業者的概念見 [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/) 卡）；主控台的 Scope 選單在這個區域只列出一個可用網域，兩條免費額度的數字因此相同（推論）。免費額度的 used 停在 141：60 GB 那一顆整顆算在免費額度之外。假如只有超出的 1 GB 在額度外，used 會是 200。主機 `RUNNING` 之後 4 分鐘起，每 2 分鐘查一次、共 6 次（約 10 分鐘），免費額度每次都是 141，而同一批查詢裡的 `total-storage-gb` 每次都是 201、已經算進這一顆，所以 141 不是還沒更新的值（推論）。Oracle 的 [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) 頁（2026-10-27 讀）對區塊磁碟的寫法跟這個結果一致：它舉的例子是四顆 50 GB 的 Always Free 磁碟加一顆 50 GB 的付費磁碟，刪掉其中一顆 Always Free 磁碟、空出額度之後，服務會自動把那顆付費磁碟轉成 Always Free（原文「When you have available Always Free capacity, Block Volume automatically tries to transition an existing paid resource to an Always Free resource」）。原文描述的轉換對象是整顆資源（paid resource），所以免費與否以整顆判定（從這一句推得，頁面沒有逐字寫；例子裡的剩餘額度是 0，單看例子分不出整顆與超出量兩種算法）。照這一句，這次的狀態下刪掉一顆 47 的免費磁碟，剩餘額度從 59 變成 106，放得下 60，這顆就可能轉成免費（推論，沒有實測）。這次被判在額度外的是建立時放不進的那一顆；之後刪掉磁碟、重新分配時會選哪一顆轉成免費，頁面沒有寫。同一頁也寫了「Although it is possible to mix paid and Always Free resources, Oracle does not recommend this」，所以合計快到 200 時，先刪掉不用的舊磁碟再建，比讓一顆磁碟落到額度外單純。帳務明細也是整顆計費（2026-10-27 實跑）。用 usage API 依 `skuName`、`skuPartNumber`、`resourceId` 分組、逐小時（`--granularity HOURLY`）讀，這顆磁碟在 UTC 02 時那一小時記成兩個付費的項目：`Block Volume - Storage`（數量 0.0806）與 `Block Volume - Performance Units`（數量 0.806）。0.0806 正好是 60 GB 乘上 1 小時、除以一個月 744 小時，代表整顆 60 GB 都照價計費，不是只有超出的 1 GB；0.806 是同一顆磁碟的 60 GB 乘上 Balanced 等級的每 GB 10 個效能單位（VPU）再除以 744。同一小時其他三顆免費的開機磁碟記在 `Block Volume - Free`，數量各 0.0632（47 ÷ 744），金額 0，而且沒有效能單位的項目。兩個付費項目一小時合計約 0.0047，幣別是這個帳戶的 SGD（新加坡幣）。所以合計快到 200 時，下一顆放不進剩餘額度的磁碟是整顆照價計費：剩 59 時建一顆 60 GB，付費的是 60 GB 不是 1 GB。

  這筆項目出現的時間也量到了：磁碟在 UTC 01:33 建立，01 時那一小時的明細裡沒有它（那一小時只存在 27 分鐘；之後有沒有補上，這次沒有再查）；02 時那一小時的明細，UTC 03:27 查還沒有，03:57 查已經有了，也就是那一小時結束後 1 到 2 小時之間出現。每 30 分鐘查一次時，查到的最新一筆依序是 00、01、01、02 時那一小時，逐小時明細大約落後 2 小時。

  `total-storage-gb` 要帶 `--availability-domain` 查，寫法跟上面查可用網域層免費額度那一條相同，只換 `--limit-name`：

  ```bash
  # 全部區塊磁碟的合計（含付費的磁碟）；跟免費額度的 used 相減，就是不在免費額度裡的 GB 數
  oci limits resource-availability get -c <tenancy 的 OCID> --service-name block-storage \
    --limit-name total-storage-gb --availability-domain <可用網域>
  ```

  **網頁主控台的同一組數字**：Governance & Administration → Tenancy Management → Limits, quotas and usage 頁（路徑在 [Oracle Cloud 主控台導覽：頂端列、導覽選單的分類、清單頁的 compartment 篩選器與常用頁面的路徑](/infra/cloud-providers/oracle-cloud/console-navigation/)），篩選條件的 Service 選 Block Volume 之後，2026-10-27 10 時前後讀到的數字跟 CLI 相同。這次開啟時篩選條件的 Scope 是區域（`ap-batam-1`，沒有試過換瀏覽器或換使用者時是否相同），這時只列出 `total-free-storage-gb-regional`（頁上的描述是 Free Tier Volume Quota (GB) in the Region）與兩項備份數量的限制（`backup-count`、`free-backup-count`），前者的 Service Limit、Usage、Available 三欄分別顯示 200、141、59；全部區塊磁碟的合計要把 Scope 換成可用網域才列出來，`total-free-storage-gb`（Free Volume Size (GB)）顯示 200、141、59，`total-storage-gb`（Volume Size (GB)）顯示 61,440、201、61,239。只看區域範圍時，看不到不在免費額度裡的那 60 GB。
- **出站流量**：每月前 10 TB 免費（Oracle〈Virtual Cloud Network Pricing〉），這台只拿來下載套件。
- **NAT gateway**：Oracle 的 [Cloud Price List](https://www.oracle.com/cloud/price-list/)（2026-10-27 讀）在 Networking 那一節只列入站流量與出站流量，沒有 NAT gateway 這一項；[Virtual Cloud Network Pricing](https://www.oracle.com/cloud/networking/virtual-cloud-network/pricing/) 頁同樣只寫區域內的流量、對外的出站流量、Dedicated connectivity 與 site-to-site VPN。實際的帳務用 usage API 依服務與 SKU 分組讀（2026-10-27 實跑）。usage API 讀的是網頁主控台 Cost Analysis 頁（Billing & Cost Management → Cost Management → Cost Analysis）背後同一份用量資料，CLI 的服務名是 `usage-api`；SKU 是帳務明細上的計費品項，例如 `Standard - A1`。`--query` 收的是 JMESPath 運算式，上一項 `boot-volume list` 的篩選也是：

  ```bash
  # COST 換成 USAGE 時印的是用量。要看每一項記在哪個資源上，--group-by 加 "resourceId"，
  # --query 的投影也要加 res:"resource-id"，否則表格裡不會多出資源那一欄（兩處都改過的版本實跑過）
  # 起訖填要看的那幾天（UTC），這次只用過日界的整點
  # tenancy 的 OCID 跟上一項 oci limits 用的是同一個。這次 CLI 設定的區域就是 home region，
  # 沒有試從其他區域呼叫 usage API 的結果
  oci usage-api usage-summary request-summarized-usages --tenant-id <tenancy 的 OCID> \
    --time-usage-started 2026-10-24T00:00:00Z --time-usage-ended 2026-10-27T00:00:00Z \
    --granularity DAILY --query-type COST --group-by '["service","skuName"]' \
    --query 'data.items[].{day:"time-usage-started",service:service,sku:"sku-name",cost:"computed-amount",qty:"computed-quantity"}' \
    --output table
  ```

  `verify-nat` 在 2026-10-26 13:18（UTC）建立，同一天 19:11（UTC，台北時間 10-27 03:11）前後刪除，存在約 6 小時，整段都落在明細的 2026-10-26 那一天裡（區間延長到 10-28 重查，明細也只到 10-26）。那一天的明細只有四項：Compute 的 `Standard - A1` 與 `Standard - A1 - Memory`、Block Storage 的 `Block Volume - Free`、Virtual Cloud Network 的 `Outbound Data Transfer Zone 2`，金額都是 0，沒有 NAT gateway 的項目。出站流量那一項以 `resourceId` 分組時有四筆，都記在 VNIC 上；用 `oci network vnic get` 對回去，其中一筆是 `verify-ubuntu` 的 VNIC（它只經 NAT gateway 出站），一筆是有公開 IP 的 `verify-origin`，另外兩筆的 VNIC 已經隨主機刪掉、查不到。所以經 NAT gateway 出去的流量記在送出流量的那台主機的 VNIC 上、照出站流量計，算進每月 10 TB 的免費量（從這一天的明細推論）。`verify-ubuntu` 那一筆是一整天的合計，NAT gateway 建立之前它也經 service gateway 送封包到 Oracle 服務網路，這次沒有把兩段分開，所以沒有確認這一筆裡經 NAT 的流量佔多少，也沒有確認 service gateway 那段是否計入出站流量。這只涵蓋 NAT gateway 存在的那約 6 小時；查詢是在 2026-10-26 19:3x（UTC）做的，那一天還沒結束；逐小時的明細大約落後 2 小時（上面開機磁碟那一項 2026-10-27 量到的），所以那一天最後幾小時的明細當時還沒出來，可能還不完整。`verify-nat` 已經刪除（〈刪除這組資源的順序〉），沒有讀完一個帳單週期的 Cost Analysis；隔幾天用同一條查詢、起訖涵蓋 10-26 重查一次，就能確認那一天的明細補齊之後有沒有多出 NAT gateway 的項目。`Outbound Data Transfer Zone 2` 的 Zone 是帳務替出站流量分的區；價目表依流量的出發地分成北美歐洲英國、亞太日本南美、中東非洲三組，三組的前 10 TB 都免費，Zone 2 對應哪一組這次沒有查。

  所以就兩份價目頁與建立當天的明細來看，NAT gateway 本身沒有收費項目，開一個 NAT gateway 多出的費用只有經它出去的流量，而流量照一般的出站流量計、先扣每月 10 TB 的免費量。這是推論：證據只涵蓋約 6 小時、而且那一天的明細可能還不完整，也沒有讀完一個帳單週期；這次也沒有查 Oracle 的 NAT gateway 文件是否明文寫了收費規則。

## 刪除這組資源的順序

順序跟建立相反，依賴有兩組，兩組之間互不依賴：NSG 要先從 VNIC 拿掉才刪得掉，NAT gateway 要先不再被路由表指著才刪得掉；終止主機時 VNIC 與序列主控台連線跟著消失。指令裡要填的值的來源：`<NAT gateway 的 OCID>` 與 `<NSG 的 OCID>` 是 `ids.env` 的 `NAT` 與 `NSGU`，同一個鍵有好幾行時取最後一行，`source ids.env` 之後用 `$NAT`、`$NSGU` 拿到的就是最後一行的值（重建腳本跑過一次就會記進去；沒跑過的話，用 `oci network nat-gateway list -c <compartment 的 OCID> --vcn-id <VCN 的 OCID> --display-name verify-nat --query 'data[0].id' --raw-output` 與同樣寫法的 `oci network nsg list … --display-name verify-ubuntu-egress` 查，兩條沒有實跑），`<Oracle 服務網路的目的地名稱>` 是 `SGCIDR`，`<路由表的 OCID>` 與 `<service gateway 的 OCID>` 是 `RT` 與 `SG`；`<VNIC 的 OCID>` 用 `oci compute instance list-vnics --instance-id <主機的 OCID> --query 'data[0].id' --raw-output` 查，`<主機的 OCID>` 是 `host-<名稱>.env` 最後一行的 `IID`（沒有這個檔時，用〈被回收之後的重建：怎麼發現、留下與消失的資源、重建腳本〉的 `instance list` 查），`<連線的 OCID>` 用〈序列主控台：RSA 金鑰、建立連線、ProxyJump 設定與看到的開機輸出〉的 `instance-console-connection list` 查（把 `--query` 換成 `'data[0].id'`）。

主機也要一起刪時，先做終止主機那一步（第 6 步），再刪 NSG、改路由表、刪 NAT gateway：VNIC 隨主機一起消失，序列主控台連線變成 `DELETED`，所以從 VNIC 拿掉 NSG 那一步（第 1 步）與刪序列主控台連線那一步（第 5 步）可以省略。留著主機、只收掉出站設定時，做從 VNIC 拿掉 NSG 到刪 NAT gateway 那四步（第 1 到第 4 步）；排查到一半、序列主控台連線還在時，再加刪連線那一步（第 5 步）。第 1 到第 4 步帶的 `--wait-for-state` 讓 CLI 等到這一步的資源回到 `AVAILABLE` 或變成 `TERMINATED` 才回傳，同一組依賴裡，後一步的刪除依賴前一步已經生效（NSG 要先從 VNIC 拿掉才刪得掉，路由表要先不再指著 NAT gateway 它才刪得掉）；2026-10-26 那一次刪除沒有帶，這次帶了，兩種寫法在同一組資源上的差別沒有比較：

1. 把 NSG 從主機的 VNIC 拿掉：`oci network vnic update --vnic-id <VNIC 的 OCID> --nsg-ids '[]' --force --wait-for-state AVAILABLE`。`--nsg-ids` 是整份替換，先用 `oci network vnic get --vnic-id <VNIC 的 OCID> --query 'data."nsg-ids"'` 列出 VNIC 現在掛著的 NSG（2026-10-27 實跑，只列出 `verify-ubuntu-egress` 一個）；清單裡還有別的 NSG 時，`'[]'` 換成去掉 `<NSG 的 OCID>` 之後的清單，否則別的 NSG 會一起被拿掉。NSG 還掛在 VNIC 上時刪不掉：2026-10-27 先試刪 `verify-ubuntu-egress`，`nsg delete` 回 `412 PreconditionFailed`，訊息是 `cannot be deleted since it still has vnics attached to it`；2026-10-26 刪另一組實驗資源的 NSG 時也是同一個回應。
2. 刪 NSG：`oci network nsg delete --nsg-id <NSG 的 OCID> --force --wait-for-state TERMINATED`。
3. 路由表改回只有 service gateway 那一條：`oci network route-table update --rt-id <路由表的 OCID> --force --wait-for-state AVAILABLE --route-rules '[{"destination":"<Oracle 服務網路的目的地名稱>","destinationType":"SERVICE_CIDR_BLOCK","networkEntityId":"<service gateway 的 OCID>"}]'`。路由表還指著 NAT gateway 時，NAT gateway 刪不掉：2026-10-27 在改路由表之前先試刪 `verify-nat`，`nat-gateway delete` 回 `400 InvalidParameter`，訊息裡包著內層的 `409, Conflict`：`The Route Table references the NAT_GATEWAY <NAT gateway 的 OCID>. You must remove the reference to proceed with this operation.`。外層的回應碼是 400 而不是 409，寫腳本或排查的人只看回應碼時，會把它讀成參數錯誤，要讀到 `message` 裡的那一句才知道是路由表的引用。`--route-rules` 是整份替換，路由表裡還有 service gateway 與 0.0.0.0/0 以外的規則時，要把它們一起寫進清單，否則會跟著被刪掉；先用〈加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG〉的 `route-table get` 列出現有的規則。
4. 刪 NAT gateway：`oci network nat-gateway delete --nat-gateway-id <NAT gateway 的 OCID> --force --wait-for-state TERMINATED`。
5. 刪序列主控台連線：`oci compute instance-console-connection delete --instance-console-connection-id <連線的 OCID> --force --wait-for-state DELETED`。連線平時不留（〈序列主控台：RSA 金鑰、建立連線、ProxyJump 設定與看到的開機輸出〉），所以只有排查到一半、連線還在的時候才需要這一步。這一條的 `--wait-for-state` 收的是連線本身的狀態（2026-10-27 實跑，10 秒後 `DELETED`），跟終止主機那一步收 work request 狀態的 `terminate` 不同。主機終止時連線也會跟著變成 `DELETED`（終止主機那一步實跑時看到的）。
6. 終止主機並刪掉開機磁碟：`oci compute instance terminate --instance-id <主機的 OCID> --preserve-boot-volume false --force --wait-for-state SUCCEEDED --wait-for-state FAILED`。`terminate --help` 列出 `--wait-for-state` 只接受 work request 的四種狀態（`ACCEPTED`、`IN_PROGRESS`、`FAILED`、`SUCCEEDED`），所以寫成主機的 `TERMINATED` 時，CLI 會以參數錯誤結束、請求不會送出（從 `--help` 推論，沒有實跑）。

2026-10-27 對重建腳本建出的 `verify-ubuntu-rebuild` 實跑了終止主機那一步：work request 66 秒後 `SUCCEEDED`，主機變成 `TERMINATED`，那台的序列主控台連線變成 `DELETED`；用 `oci bv boot-volume list` 加上 `lifecycle-state != TERMINATED` 的篩選列出開機磁碟時，清單裡已經沒有那顆磁碟。[Oracle Cloud 建立主機的實測紀錄：建立前的檢查、前置網路、主控台各分頁的 Always Free 設定值、等效的 CLI 指令、容量不足的重送、Bastion 工作階段逾時、Run Command 補公鑰的嘗試與重建後經由 port forwarding 登入](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/)（建主機那篇）〈刪除這組資源的順序〉寫的是開機磁碟的狀態變成 `TERMINATED`，篩掉 `TERMINATED` 之後就不在清單裡，兩者不衝突。

同一天留著 `verify-ubuntu`、照從 VNIC 拿掉 NSG 到刪 NAT gateway 那四步（第 1 到第 4 步）收掉它的出站設定（實跑）：四條各在 1 到 2 秒內結束，結束碼都是 0；之後 `nat-gateway get` 與 `nsg get` 都回 `404 NotAuthorizedOrNotFound`，兩者的 `list` 也已經列不出來，路由表剩 service gateway 那一條。主機上的 `apt-get update` 回到〈只接 service gateway 的私有子網路：apt 連到套件來源時的錯誤原文與成因〉那一節的錯誤：IPv6 位址印 `Network is unreachable`，IPv4 位址印 `connection timed out`。刪掉之後，`ids.env` 的 `NAT` 與 `NSGU` 指向已經不存在的資源；重建腳本依名稱查 NAT gateway 與 NSG，查不到 `AVAILABLE` 的同名資源就重建並記下新的 OCID，所以要恢復出站時重跑重建腳本：同一天上午重跑過一次，32 秒重建了 NAT gateway、NSG 與路由，出站恢復（〈被回收之後的重建：怎麼發現、留下與消失的資源、重建腳本〉「NAT gateway 與 NSG 都不存在」那一項）。新的 OCID 以新的一行接在 `ids.env` 檔尾，舊的那一行還在；`source` 時後面那一行蓋過前面的，手動抄值時取最後一行。

**只暫停出站、不刪資源的做法**（三種的暫停動作都沒有實跑；前兩種恢復時重建腳本走的「改寫」分支，在 NAT gateway 與 NSG 都不存在的那一次實跑過，第三種依 `--help` 與重建腳本的邏輯推論）：NAT gateway 本身看來沒有收費項目（〈費用與額度：A1、開機磁碟、出站流量與 NAT gateway〉），刪掉它換到的主要是帳號裡不留下沒在用的資源，代價是重建之後 NAT gateway 與 NSG 的 OCID 都換了，NAT gateway 的出站 IP 也會換：在第三方服務用這個 IP 做白名單的話，白名單要跟著改（`nat-gateway create --public-ip-id <保留公開 IP 的 OCID>` 可以讓重建的 NAT gateway 沿用一個保留的公開 IP，沒有實跑，保留 IP 是否收費沒有查）。只想暫停時有三種做法：

- **只拿掉路由表的 0.0.0.0/0 那一條**：做第 3 步就好。要恢復時重跑重建腳本，路由那一步查到少了 0.0.0.0/0，會印「改寫」補回來。
- **只把 NSG 從 VNIC 拿掉**：做第 1 步就好。security list 不放行網際網路出站（〈加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG〉），所以出站跟著斷掉。要恢復時重跑重建腳本，掛 NSG 那一步查到 VNIC 沒有掛它，會印「改寫」重新掛上。
- **`oci network nat-gateway update --nat-gateway-id <NAT gateway 的 OCID> --block-traffic true`**：NAT gateway 停止轉送流量，路由與 NSG 都不動。要恢復時要另外跑同一條、帶 `--block-traffic false`：重建腳本只依名稱與 `AVAILABLE` 找 NAT gateway，被設成擋流量的 NAT gateway 仍然是 `AVAILABLE`，腳本每一步都印「已存在」、以 0 結束，出站卻還是不通，`apt-get update` 回到逾時，沒有任何訊息指出原因。

各項刪不掉時，看錯誤訊息指出的那一項依賴、先刪它。網路、Bastion 與 compartment 的刪除順序在建主機那篇〈刪除這組資源的順序〉。

## 延伸閱讀：建主機的前置網路、閒置回收的規則、序列主控台的比較、主機上的更新與 NAT 閘道的計費

- [Oracle Cloud 建立主機的實測紀錄：建立前的檢查、前置網路、主控台各分頁的 Always Free 設定值、等效的 CLI 指令、容量不足的重送、Bastion 工作階段逾時、Run Command 補公鑰的嘗試與重建後經由 port forwarding 登入](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/)：本篇沿用的 compartment、VCN、私有子網路、service gateway、Bastion 與重送腳本
- [Oracle Cloud 的帳號結構與 home region：tenancy、Always Free 的範圍與主控台登入欄位](/infra/cloud-providers/oracle-cloud/account-and-home-region/)：Always Free 的額度、閒置回收與試用結束時超額的規則
- [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)：這台主機上量到的自動更新預設、核心更新前後的重開機判斷，以及三家業者序列主控台的條件
- [雲端免費額度與小型主機的收費比較：試用金與固定額度、計費單位、區域限制、試用結束後的處置、出站流量與查價項目](/infra/cloud-providers/pricing-comparison/)：AWS 與 Google Cloud 的 NAT 閘道計費、三家的出站流量額度
