---
title: "Oracle Cloud 建立主機的實測紀錄：前置網路、主控台各分頁的 Always Free 設定值、等效的 CLI 指令、容量不足的重送與 Bastion 工作階段逾時"
date: 2026-10-24
description: "在 Oracle Cloud 建立一台 Always Free 的 A1 Ubuntu 主機時，前置的 compartment、VCN 與閘道怎麼建，主控台各分頁填了什麼、為什麼這樣填，等效的 CLI 指令與它跟主控台預設值的差異，Oracle Cloud Agent 各 plugin 的用途，容量不足時 CLI 自己的重送、限流門檻與依回應碼調整間隔的重送腳本，建好之後建立 Bastion、managed SSH session 建立逾時的排查與 A1 加 Ubuntu 不支援的官方說明，以及刪除這組資源的順序"
weight: 5
aliases: ["/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/"]
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "vm", "free-tier"]
---

實測日期是 2026-10-24 與 2026-10-25，區域 `ap-batam-1`，帳號是 Oracle Cloud 的 Free Tier，在本機用 OCI CLI 與主控台建立一台 A1 Ubuntu 24.04 主機，再從本機經由 Bastion 建立登入的工作階段。

這篇記錄在 Oracle Cloud 建立一台主機的實際操作，目標是 Always Free 額度內、沒有公開 IP、之後經由 Bastion 服務登入的 A1 Ubuntu 主機。Bastion 是 Oracle Cloud 代管的登入服務：建立 Bastion 時指定一個目標 subnet，它替那個 subnet 裡沒有公開 IP 的主機開有時效的 SSH 工作階段（session）；這次要用的 managed SSH session 這種工作階段，由主機上 Oracle Cloud Agent 的 Bastion plugin 在建立工作階段時把一把公鑰臨時放進主機。工作階段的種類與需要的條件見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。內容依操作的順序是：前置的 compartment、VCN、service gateway 與 private subnet；主控台建立頁 Basic information、Security、Networking、SSH keys、Storage、Management 各分頁的取值與理由，含 Oracle Cloud Agent 各 plugin 的用途；等效的 CLI 指令；按下 Create 之後的容量不足，CLI 自己的重送、這個帳號量到的限流門檻與依回應碼調整間隔的重送腳本；主機建好之後建立 Bastion 與 managed SSH session、工作階段建立逾時的排查與官方列出的成因；以及刪除這組資源的順序。每個欄位背後的概念連到 [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/) 底下對應的那一篇，這裡只寫 Oracle Cloud 的欄位、這次的取值與實際跑過的指令。

## 進建立頁之前：compartment、VCN、閘道與 private subnet

建立頁上的網路欄位只能選已經存在的 VCN 與 subnet，或讓主控台建一個新的（新建的那個會帶一份對網際網路開放 22 port 的預設規則，見〈Networking：VCN、subnet 與公開 IP〉）。這次先用 OCI CLI 建好下面幾項，建立頁上一律選既有的。CLI 的登入方式見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)，主控台上的對應頁面是 Identity & Security → Identity → Compartments 與 Networking → Virtual cloud networks。

- **compartment `blog-verify`**：tenancy 底下分組資源的容器，實驗用的資源都放在這裡，清理時不碰 root 裡的其他設定。
- **VCN `verify-vcn`**（`10.0.0.0/16`，位址範圍的寫法見 [CIDR](/infra/knowledge-cards/cidr/) 卡）：主機所在的虛擬網路。
- **service gateway 與路由表 `private-rt`**：私有 subnet 沒有通往網際網路的路由，主機上的 Oracle Cloud Agent 要連到 Oracle 自己的服務端點，經由 service gateway 出去；路由表裡那一條規則把送往 Oracle 服務網段的流量導向 service gateway。managed SSH session 對閘道與路由的要求見 [登入](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉，這次在其中選了 service gateway。

這份網路刻意沒有 NAT 閘道，主機只用來測 Bastion 登入；沒有 NAT 時，主機連不到 Ubuntu 的套件來源，`apt` 更新與安裝都會失敗。要當一般主機用，就另外建一個 NAT 閘道，在路由表加一條通往它的路由，並在 security list 的出站規則放行網際網路。

- **security list `private-sl`**：入站只放行來源是同一個 subnet（`10.0.1.0/24`）的 22 port，因為 Bastion 的目標 subnet 設成這個 subnet，經由 Bastion 的 SSH 連線從這個 subnet 進來；出站只放行送往 Oracle 服務網段與同一個 subnet 的流量。
- **subnet `private-subnet`**（`10.0.1.0/24`）：建立時設定禁止公開 IP，並掛上上面的路由表與 security list。

```bash
# 以下每條都以 --wait-for-state 等資源建好，再用 --query 取出新資源的 OCID 給下一條用
oci iam compartment create --compartment-id <tenancy 的 OCID> --name blog-verify --description "<用途說明>"
oci network vcn create -c <compartment 的 OCID> --cidr-blocks '["10.0.0.0/16"]' --display-name verify-vcn --dns-label verifyvcn
oci network service-gateway create -c <compartment 的 OCID> --vcn-id <VCN 的 OCID> --services '[{"serviceId":"<All Services 的 service ID>"}]'
oci network route-table create -c <compartment 的 OCID> --vcn-id <VCN 的 OCID> --display-name private-rt \
  --route-rules '[{"destination":"<All Services 的網段>","destinationType":"SERVICE_CIDR_BLOCK","networkEntityId":"<service gateway 的 OCID>"}]'
oci network subnet create -c <compartment 的 OCID> --vcn-id <VCN 的 OCID> --cidr-block 10.0.1.0/24 --display-name private-subnet \
  --dns-label priv --prohibit-public-ip-on-vnic true --route-table-id <路由表的 OCID> --security-list-ids '["<security list 的 OCID>"]'
```

- `<All Services 的 service ID>` 與 `<All Services 的網段>`：用 `oci network service list` 查，名稱帶「All」的那一筆就是 Oracle 全部服務的網段，service gateway 與路由規則都指向它。
- security list 用 `oci network security-list create` 建，入站與出站規則以 JSON 給，內容照上面清單的那兩條。
- `--prohibit-public-ip-on-vnic true`：這個 subnet 裡的網卡不能指派公開 IP，也就是 private subnet。
- 網段 `10.0.0.0/16` 與 `10.0.1.0/24` 是這次選的私有位址，換成自己規劃的也可以，security list 的來源要跟著改成 subnet 的網段。

## Basic information：名稱、compartment、位置、映像檔與機型

| 欄位                  | 這次的值                                     | 理由與對應的概念篇                                                                                                                                                                                                   |
| --------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name                  | `verify-a1`                                  | 自動產生的 `instance-<日期>-<時間>` 在清單裡認不出用途                                                                                                                                                               |
| Create in compartment | `blog-verify`                                | 實驗資源集中在一個 compartment，清理時不碰 root 裡的設定                                                                                                                                                             |
| Availability domain   | AD-1                                         | 這一區只有一個 AD，見 [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/)                                                                                                                     |
| Capacity type         | On-demand                                    | 官方 Always Free 頁列額度時沒有提到 preemptible，選它時額度怎麼算查不到原文；preemptible 會被收回，見 [機型與映像檔：CPU 架構、核心與記憶體、計費模式與作業系統](/infra/cloud-providers/vm-options/shape-and-image/) |
| Fault domain          | Let Oracle choose the best fault domain      | 單一台主機指定故障域沒有好處，還會縮小可用容量                                                                                                                                                                       |
| Image                 | Canonical Ubuntu 24.04（build 2026.09.18-0） | Oracle 維護的平台映像，架構跟著機型選 aarch64                                                                                                                                                                        |
| Shape                 | `VM.Standard.A1.Flex`，1 OCPU、6 GB          | Always Free 的 A1 上限是 2 OCPU、12 GB，先用一半，另一半留給第二台主機；之後要加大不必重建，代價是重開機                                                                                                             |

「Change shape」的視窗依處理器分欄。這一區的 Ampere 欄有 `VM.Standard.A1.Flex` 並標示 Always Free-eligible；AMD 欄只列出 `VM.Standard.E5.Flex`，Always Free 的 `VM.Standard.E2.1.Micro` 不在清單上。E5.Flex 不在免費額度內，選了之後的結果依帳號狀態而定（試用中由試用金支付、試用結束而沒有升級的帳號建不了、付費帳戶照一般價格計費），見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉；區域之間提供的機型不同，見同一篇的〈E2.1.Micro 在各區域的供應：服務配額表與 404 錯誤〉。

## Security：Shielded instance

Secure Boot、Measured Boot、Trusted Platform Module 三項預設都是 Disabled，這次維持關閉。三項在建立之後不能改，要測試這個功能時另外建一台；判斷要不要開見 [安全開機：Secure Boot、Measured Boot 與 TPM](/infra/cloud-providers/vm-options/shielded-boot/)。

## Networking：VCN、subnet 與公開 IP

| 欄位                                     | 這次的值                                  | 理由                                                                    |
| ---------------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| Primary network                          | Select existing virtual cloud network     | 用前置步驟建好的 VCN，避開新建 VCN 帶的預設規則                         |
| Virtual cloud network compartment        | `blog-verify`                             | VCN 建在這個 compartment，選單只列出這一欄選定的 compartment 裡的 VCN   |
| Virtual cloud network                    | `verify-vcn`                              | 前置步驟建的 VCN                                                        |
| Subnet                                   | Select existing subnet → `private-subnet` | 禁止公開 IP 的 subnet，主機不暴露在網際網路上                           |
| Private IPv4 address                     | Automatically assign                      | 單一台主機不需要固定位址                                                |
| Automatically assign public IPv4 address | 關閉                                      | private subnet 不允許公開 IP，開關是灰的                                |
| VNIC name                                | 留空                                      | 顯示用，之後可以改                                                      |
| DNS record                               | Yes                                       | 同一個 VCN 裡的其他主機可以用名稱連它                                   |
| Use network security groups              | No                                        | 入站規則只用 subnet 的 security list 管，這台主機不需要另外的網卡層規則 |

這一頁實測卡住的地方是 VCN 下拉選單：它只列出「Virtual cloud network compartment」那一欄選定的 compartment 裡的 VCN，而那一欄預設停在 root compartment。`verify-vcn` 建在 `blog-verify`，所以要先把那一欄切過去，選單裡才會出現它。

選「Create new virtual cloud network」時，主控台會一起建一份「Default Security List for <VCN 名稱>」。當天實測一個新建的 VCN，這份預設規則的入站部分是：

- TCP 22（SSH），來源 `0.0.0.0/0`，也就是網際網路上的任何位址
- ICMP type 3 code 4（Path MTU Discovery 需要的封包），來源 `0.0.0.0/0`
- ICMP type 3，來源是 VCN 自己的位址範圍

出站是全部放行。Subnet 沒有另外指定 security list 時套用的就是這一份，所以在新建的公開 subnet 裡建一台有公開 IP 的主機，那台主機的 SSH port 一建好就對整個網際網路開放。官方文件把 TCP 22 那一條規則寫成允許「authorized source IP addresses」，而預設填的來源是 `0.0.0.0/0`，等於任何位址都算在內；官方建議把來源收緊。這份規則跟 NSG 怎麼合併，以及為什麼 NSG 裡不寫 22 port 的規則時，22 port 的連線照樣由這份 security list 放行通過，見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/) 的〈防火牆規則的位置與合併方式〉。

## SSH keys

這次選 No SSH keys，目的是驗證主機完全不放金鑰時，managed SSH session 這條路本身走不走得通；managed SSH session 在主機有放公鑰時照樣能用，只是那樣就驗不出這件事。選了之後主機裡不放任何長期有效的公鑰，登入改用 Bastion 的 managed SSH session，由主機上的 Bastion plugin 臨時放進一把公鑰。Oracle Cloud 對這個選項的說明是選了之後就不能再提供公鑰，所以這條路要求〈Management：Oracle Cloud Agent 與其他進階選項〉那一節的 Bastion plugin 一定打開。這次刻意不留退路，代價在〈建立之後：Bastion managed SSH session 逾時的排查〉那一節出現：工作階段的建立逾時之後，主機上沒有任何 SSH 登入的入口，要查原因只剩 Run Command 或重建主機。第一次建主機、還沒走通 Bastion 時先放自己的公鑰、改用不經過 plugin 的 SSH port forwarding session 登入的做法與它的前提，見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。

## Storage

開機磁碟維持映像檔的預設大小（50 GB）、效能等級 Balanced、Use in-transit encryption 為 Enabled、不指定自己的加密金鑰，不另外建立區塊磁碟。50 GB 在 Always Free 的 200 GB 額度內。要記住的是刪除這台主機時，終止對話框裡的「Permanently delete the attached boot volume」預設不勾，不勾的話開機磁碟會留下來繼續佔著額度，見 [磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)。

## Management：Oracle Cloud Agent 與其他進階選項

Oracle Cloud Agent 的每一項功能是一個 plugin。官方列出的 plugin 與這次建立頁上的預設值：

| Plugin                          | 做什麼                                                                                                                                                           | 這次的預設 |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Compute Instance Monitoring     | 回報主機的健康、容量與效能指標給 Monitoring 服務                                                                                                                 | 開啟       |
| Custom Logs Monitoring          | 把主機上的自訂日誌送進 Logging 服務                                                                                                                              | 開啟       |
| Compute Instance Run Command    | 從主控台或 API 在主機裡執行腳本，用來遠端設定與排錯                                                                                                              | 開啟       |
| Cloud Guard Workload Protection | 官方說明只寫一種用途：自訂映像沒有啟用 Oracle Cloud Agent 時，讓使用者自己管理 Cloud Guard 的 Instance Security 代理程式的更新；平台映像上它做什麼，說明頁沒有寫 | 開啟       |
| Bastion                         | 讓 Bastion 服務對沒有公開 IP 的主機建立 managed SSH session                                                                                                      | 關閉       |
| Block Volume Management         | 替主機設定區塊磁碟的連線                                                                                                                                         | 關閉       |
| OS Management Hub Agent         | 管理與監看作業系統的更新與修補                                                                                                                                   | 關閉       |
| Vulnerability Scanning          | 掃描主機上的弱點，例如需要更新的套件                                                                                                                             | 關閉       |
| Management Agent                | 替有整合 Management Agent 的 OCI 服務收集作業系統、應用程式與基礎設施的資料（可觀測性、日誌、組態、容量與健康狀態）                                              | 關閉       |
| High Performance Computing      | 給 HPC 機型的運算叢集用                                                                                                                                          | 關閉       |
| Fleet Application Management    | 替 Fleet Application Management 服務執行並監看應用程式的盤點（discovery）與修補                                                                                  | 關閉       |
| Oracle Java Management Service  | 監看 Java Management 服務所管理的主機上的 Java 部署                                                                                                              | 關閉       |

官方的 plugin 說明頁對 Custom Logs Monitoring 在 A1 上的支援前後不一致：頁面上的註記寫它不支援 A1 機型，同一頁的代理程式版本紀錄（1.29.0）寫已經支援 Arm 處理器。這次維持建立頁的預設（開啟）：這個 plugin 只負責把日誌送進 Logging，要在 Logging 服務裡設定收哪些日誌之後才開始收，費用依收進來的日誌量計算（官方〈Custom Logs〉）；沒有設定時它不影響主機建立與登入。

這次要改的只有一項：**把 Bastion 打開**。沒有放 SSH 金鑰的主機，SSH 登入只能經由 Bastion 的 managed SSH session，而這個 plugin 預設關閉；不經過 SSH 的其他入口見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈建立之後加金鑰與金鑰遺失時的入口〉。漏開時不必重建，主機建好之後可以在主機頁面的 Oracle Cloud Agent 分頁打開，官方說明最多 10 分鐘生效。

其餘維持預設，理由各自如下：

- **Authorization header：Enabled**。這是建立頁對 Ubuntu 的預設，而官方列出支援中繼資料第二版的平台映像只有 Oracle Linux 系列，Ubuntu 不在清單上。2026-10-25 建好的主機開著這個選項，代理程式照常回報各 plugin 的狀態；managed SSH session 的建立逾時時，暫時改成允許第一版也一樣逾時，所以這個選項不是那次失敗的成因，見〈建立之後：Bastion managed SSH session 逾時的排查〉。cloud-init 從中繼資料讀出公鑰寫進 `authorized_keys` 這一段，這台選了 No SSH keys 驗不到，要另一台放了公鑰的主機驗。要怎麼確認見 [代理程式、中繼資料服務、初始化腳本、維護行為與標籤](/infra/cloud-providers/vm-options/management/) 的〈中繼資料服務與 Authorization header〉。
- **Live migration：讓 Oracle 選擇**、**Restart after infrastructure maintenance：Enabled**：實驗機能接受維護時被遷移或重開。
- **不放初始化腳本、不加標籤**：這台主機只用來測登入，沒有要預先裝的軟體。

## 等效的 CLI 指令

同一組設定用 OCI CLI 建立：

```bash
oci compute instance launch \
  --compartment-id <compartment 的 OCID> \
  --availability-domain <AD 名稱，例如 XXXX:AP-BATAM-1-AD-1> \
  --display-name verify-a1 \
  --shape VM.Standard.A1.Flex --shape-config '{"ocpus":1,"memoryInGBs":6}' \
  --image-id <Ubuntu 24.04 aarch64 映像檔的 OCID> \
  --subnet-id <private subnet 的 OCID> \
  --assign-public-ip false \
  --agent-config '{"pluginsConfig":[{"name":"Bastion","desiredState":"ENABLED"}]}' \
  --is-pv-encryption-in-transit-enabled true \
  --instance-options '{"areLegacyImdsEndpointsDisabled":true}' \
  --auth security_token
```

- `--compartment-id`、`--subnet-id`：compartment 與 subnet 的 OCID，在主控台各自的詳細頁複製，或用 `oci iam compartment list` 與 `oci network subnet list --compartment-id <compartment 的 OCID>` 查。OCID 是 Oracle Cloud 給每個資源的唯一識別碼，說明見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)。
- `--availability-domain`：AD 的完整名稱帶有 tenancy 專屬的前綴，用 `oci iam availability-domain list` 查，不能只寫 `AD-1`。
- `--shape-config`：`ocpus` 與 `memoryInGBs` 對應 Basic information 表裡 Shape 那一列的 1 OCPU、6 GB。
- `--image-id`：映像檔的 OCID 每個區域不同、每次更新都會換，用 `oci compute image list --compartment-id <tenancy 的 OCID> --operating-system "Canonical Ubuntu" --operating-system-version "24.04" --shape VM.Standard.A1.Flex` 查最新的那一個。這裡的 `--compartment-id` 填 tenancy 的 OCID 而不是實驗用的 compartment，因為平台映像列在 tenancy 的 root 層；指令加上 `--shape VM.Standard.A1.Flex` 之後，CLI 只回傳跟 A1 相容的 aarch64 映像檔。
- `--agent-config`：只列出要改的 plugin，其餘維持預設。這裡把 Bastion 設成 `ENABLED`。
- `--is-pv-encryption-in-transit-enabled true` 與 `--instance-options '{"areLegacyImdsEndpointsDisabled":true}'`：前者對應 Storage 段的 in-transit encryption，後者對應 Management 段的 Authorization header（只允許中繼資料第二版）。這兩項在主控台是預設開啟，CLI 不給時，官方的 CLI 參考寫明 in-transit encryption 的預設值是 false，所以要跟主控台一致就要明確帶上。2026-10-24 背景重試用的指令一開始沒有這兩行，之後才補上。
- `--auth security_token`：用 session token 登入時每條指令都要帶，不帶會報設定檔缺 `user`；用 API 簽章金鑰時拿掉。在主控台的 Cloud Shell 裡跑時也拿掉，Cloud Shell 裡的 CLI 用 Cloud Shell 自己的驗證，沒有本機的 session 設定。
- 沒有給 `--ssh-authorized-keys-file`，等同主控台的 No SSH keys。

主控台與 CLI 的差別在錯誤訊息的可讀性：主控台的 Change shape 視窗只列出這一區有的機型，並把跟所選映像檔架構不相容的機型標成不可選；這次用 CLI 送出這一區沒有的 E2.1.Micro，回的是 `404 NotAuthorizedOrNotFound`，這個錯誤碼怎麼讀與怎麼查一區有哪些機型，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈E2.1.Micro 在各區域的供應：服務配額表與 404 錯誤〉。

## 按下 Create 之後的結果：容量不足

主控台回的訊息是：

```text
Out of capacity for shape VM.Standard.A1.Flex in availability domain AD-1. Create the instance in a different availability domain or try again later.
```

意思是這個 AD 裡跑 A1 的實體主機當下沒有空出這個規格需要的資源；同一段時間用 CLI 送出的請求回的是 `InternalError: Out of host capacity.`，偶爾是 `429 TooManyRequests`（請求太頻繁被限流）。訊息建議的換 AD 在這一區不存在（只有一個 AD），fault domain 這次已經是讓 Oracle 選，規格 1 OCPU、6 GB 只用了額度的一半，還能再改小。容量不足時全部的退路與哪幾項會計費，列在 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈A1 容量不足時的退路〉；這次的帳號只用免費額度，選的是隔一段時間再試。

2026-10-24 的重送紀錄：先以 90 秒的間隔送了九次，前三次收到 429、後六次是容量不足；之後改成每 5 分鐘一次，到當天晚上仍然是容量不足。兩種回應碼的讀法見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈A1 容量不足時的退路〉裡「等一段時間再試」那一項。

## 重送建立請求：CLI 自己的重送、限流門檻與重送腳本

2026-10-25 改用下面這支腳本重送，從 10:32 開始，第 16 次（11:00）建立成功。這一天量到的兩件事決定了腳本的間隔怎麼設：

- **OCI CLI 在一條指令裡會自己重送**：`oci` 預設會在同一條指令裡重送失敗的請求，`oci --help` 對 `--max-retries` 的說明是多數指令最多送 7 次（哪些回應碼算可以重送，`--help` 沒有列）。所以外層迴圈每「試一次」，送到 API 的是一連串請求，前一天以 90 秒間隔送、前三次就收到 429，跟這一點對得上。指令加上全域選項 `--no-retry` 之後，一次嘗試只送一個請求，間隔才完全由外層迴圈決定。
- **這個帳號的限流門檻**：只送單一請求的那一輪共 16 次，收到 `429 Too many requests for the user` 的有 2 次，這兩次送出之前，腳本分別等了 75 秒與 67 秒；其餘 13 次送出之前等了 76 到 171 秒，回的都是容量不足。前一輪以 46 秒的等待送，第三次就收到 429。訊息裡的「for the user」代表限流按使用者計算，同一個使用者並行開幾個迴圈，只會更快被限流。門檻依帳號與 API 而定，這是這個帳號這一天的量測；腳本因此不寫死間隔，而是依回應碼調整。

```bash
#!/bin/bash
# 容量不足時重送建立主機的請求，建立成功或認證失效時結束
set -uo pipefail
export OCI_CLI_AUTH=security_token
C="<compartment 的 OCID>"; SN="<private subnet 的 OCID>"; IMG="<映像檔的 OCID>"; AD="<AD 的完整名稱>"
back=120 last_refresh=0                               # 0：開跑時先延長一次 token
while :; do
  if (( $(date +%s) - last_refresh >= 1800 )); then   # session token 一小時過期，每 30 分鐘延長一次
    oci session refresh --profile DEFAULT >/dev/null 2>&1 || { echo "token 無法延長，重新登入"; exit 2; }
    last_refresh=$(date +%s)
  fi
  out=$(oci --no-retry compute instance launch -c "$C" --availability-domain "$AD" --display-name verify-a1 \
    --shape VM.Standard.A1.Flex --shape-config '{"ocpus":1,"memoryInGBs":6}' --image-id "$IMG" \
    --subnet-id "$SN" --assign-public-ip false \
    --agent-config '{"pluginsConfig":[{"name":"Bastion","desiredState":"ENABLED"}]}' \
    --is-pv-encryption-in-transit-enabled true --instance-options '{"areLegacyImdsEndpointsDisabled":true}' \
    --query data.id --raw-output 2>&1)
  id=$(grep -o 'ocid1\.instance\.[^" ]*' <<<"$out" | head -1)   # 輸出前面可能夾著 CLI 的警告
  if [[ -n "$id" ]]; then echo "建立成功：$id"; exit 0; fi
  status=$(grep -o '"status": [0-9]*' <<<"$out" | head -1 | grep -o '[0-9]*$')
  case "$status" in
    "")  echo "讀不出回應碼，停下來看輸出：$out"; exit 3 ;;   # 設定檔錯誤、網路錯誤這類沒有回應碼的失敗
    401) echo "認證失效，重新登入"; exit 2 ;;
    429) back=$(( back * 2 > 600 ? 600 : back * 2 )) ;;   # 被限流：間隔加倍，上限 600 秒
    *)   back=$(( back - 10 < 60 ? 60 : back - 10 )) ;;   # 其他回應（容量不足）：每次縮 10 秒，下限 60 秒
  esac
  echo "$(date +%H:%M:%S) ${status:-?}，約 ${back} 秒後再送"
  sleep $(( back - 15 + RANDOM % 31 ))                   # 加 ±15 秒的隨機抖動
done
```

- 四個佔位值的查法與〈等效的 CLI 指令〉那一節相同；`--display-name verify-a1` 是主機在清單上的名稱，換成自己要的名稱時，〈重複建立的風險〉那一項查同名主機的指令也跟著換；`--shape-config` 到 `--instance-options` 是那一節的同一組設定，`--no-retry` 是寫在子命令之前的全域選項。
- **間隔的調整方式**：收到 429 時間隔加倍，其他回應每次縮 10 秒，所以間隔會在「剛好不被限流」的附近來回。被限流的期間就算剛好有容量空出來也送不進去，所以把頻率壓在門檻下、讓請求能長時間穩定地送，比把間隔縮到最短更有機會碰上容量釋出的那一刻。120、600、60 這三個值是起點、上限與下限，換帳號時從 120 起跑，讓腳本自己往門檻靠。
- **抖動（jitter）**：每次的等待多加 ±15 秒的隨機值，讓送出的時間點不落在固定的週期上。間隔加倍的退避做法見 [Exponential Backoff](/backend/knowledge-cards/exponential-backoff/) 卡，那張卡把 jitter 列為退避要一起搭配的一項；抖動對這次搶到容量有沒有影響，這次沒有量。
- **驗證方式**：`export OCI_CLI_AUTH=security_token` 等同每條指令都帶 `--auth security_token`。`--profile DEFAULT` 填 `oci session authenticate` 時取的 profile 名稱，沒有另外取名時就是 `DEFAULT`。
- **判斷建立成功的方式**：輸出裡找得到 `ocid1.instance.` 開頭的 OCID 就算成功。標準錯誤併進了 `$out`，CLI 在 OCID 之前印出警告時（例如設定檔權限的警告），整段輸出就不是以 OCID 開頭；只比對開頭的話，已經建成的這一次會被當成失敗、再送一次，建出第二台。
- **結束條件**：建立成功（exit 0）、session token 無法再延長或收到 401（exit 2）、輸出裡讀不出回應碼（exit 3，設定檔或網路錯誤這類，重送也不會好）。`last_refresh=0` 讓腳本開跑時先延長一次 token，開跑時 token 只剩不到 30 分鐘也不會在第一次延長之前過期。session token 一次登入最長延到 24 小時，超過就要重跑 `oci session authenticate`，見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)；要讓腳本跑超過一天，改用 API 簽章金鑰，並拿掉 `OCI_CLI_AUTH` 與延長 token 的那一段。
- **重複建立的風險**：建立成功就結束，所以收得到回應時，同一支腳本不會建出第二台。收不到回應的情形擋不住：建立請求在 Oracle 那一端已經成功、回應卻因為網路中斷沒有回到本機，這一次會落進讀不出回應碼的分支而結束（exit 3）。所以腳本以 exit 3 結束、或要再次執行之前，先用 `oci compute instance list -c <compartment 的 OCID> --display-name verify-a1` 確認沒有還在的同名主機。

2026-10-25 實際跑的版本另外在開跑前查一次有沒有同名主機、把每次的結果寫進紀錄檔，重送與間隔的邏輯跟上面相同；上面這一份用一支假的 `oci` 指令跑過四組回應，確認每個分支的間隔與結束碼：依序回 500、429、500 與成功（間隔 110、220、210 秒，exit 0）、先在標準錯誤印警告再印 OCID（只送一次，exit 0）、回一段沒有回應碼的錯誤（exit 3）、回 401（exit 2）；四組都在第一次送出之前先延長了一次 token。

## 建立之後：Bastion managed SSH session 逾時的排查

這一節的指令跟腳本一樣用 session token 驗證：先在 shell 裡 `export OCI_CLI_AUTH=security_token`，或每條指令加 `--auth security_token`，兩種寫法等效。

### 建立 Bastion 與 managed SSH session

Bastion 在 2026-10-24 主機還沒建成時就先建好，建立 Bastion 只需要目標 subnet 存在：

```bash
oci bastion bastion create -c <compartment 的 OCID> --bastion-type STANDARD --target-subnet-id <private subnet 的 OCID> \
  --name verifybastion --client-cidr-list '["<本機的公開 IP>/32"]' --max-session-ttl 3600 --wait-for-state SUCCEEDED
```

- `--target-subnet-id`：Bastion 替哪一個 subnet 裡的主機開工作階段。Bastion 在這個 subnet 裡放一個私有端點，從那裡連主機的 22 port，所以〈進建立頁之前〉的 security list 放行來源是同一個 subnet 的 22 port。
- `--client-cidr-list`：允許從哪些位址連到 Bastion，填本機目前的公開 IP 加 `/32`。這個參數整份取代既有的清單；本機的 IP 變了（家用網路重新撥號之後常見）就用 `oci bastion bastion update --bastion-id <Bastion 的 OCID> --client-cidr-list '["<新的公開 IP>/32"]'` 換掉，2026-10-25 就換過一次。這一項影響的是連線，不影響工作階段的建立。
- `--max-session-ttl 3600`：這個 Bastion 上工作階段的最長時效（秒），建工作階段時的 `--session-ttl` 不能超過它。
- 這次用 tenancy 的管理員帳號操作，沒有另外建 IAM 政策；一般使用者建 Bastion 與工作階段需要的政策，這篇沒有寫。

主機在 2026-10-25 11:00 建立，11:04 主機頁面的 Oracle Cloud Agent 回報 Bastion plugin 是 `RUNNING`。代理程式回報得了 plugin 狀態，代表代理程式本身在只允許中繼資料第二版（Authorization header 開著）的設定下照常運作。接著建 managed SSH session：

```bash
oci bastion session create-managed-ssh --bastion-id <Bastion 的 OCID> --target-resource-id <主機的 OCID> \
  --target-os-username ubuntu --target-private-ip <主機的私有 IP> \
  --ssh-public-key-file <這次工作階段用的公鑰> --session-ttl 3600
```

- `--target-os-username ubuntu`：Ubuntu 平台映像的預設使用者，Oracle Linux 是 `opc`。
- `--target-private-ip`：用 `oci compute instance list-vnics --instance-id <主機的 OCID> --query 'data[0]."private-ip"' --raw-output` 查。
- `--ssh-public-key-file`：只給這一次工作階段用的公鑰（例如用 `ssh-keygen -t rsa -b 4096 -f <檔名>` 另產一組），plugin 在工作階段期間把它放進主機，連線時用對應的私鑰。
- `--session-ttl 3600`：工作階段的時效（秒），上限是 Bastion 的 `--max-session-ttl`。

### 結果：停在 CREATING 約 15 分鐘後轉成 DELETED

三次建立的工作階段都停在 `CREATING` 約 15 分鐘，接著轉成 `DELETED`，`lifecycle-details` 是空的。失敗的原因記在建立工作階段的 work request 上；work request 是 Oracle Cloud 記錄一次非同步操作的進度與錯誤的物件：

```bash
# 取這個 compartment 裡最近一次建立工作階段的 work request，再讀它的錯誤
oci bastion work-request list -c <compartment 的 OCID> --all \
  --query 'data[?"operation-type"==`CREATE_SESSION`] | sort_by(@, &"time-accepted")[-1].id' --raw-output
oci bastion work-request-error list --work-request-id <上一條印出的 work request OCID>
```

- `--query` 只留操作類型是 `CREATE_SESSION` 的 work request，依受理時間排序後取最後一筆。同一個 compartment 裡還有建立 Bastion、更新允許清單、刪除工作階段的 work request，只取清單第一筆的話可能取到那些。

三次讀到的都是同兩則訊息：`End host agent didn't respond back on session status in time` 與 `End host agent hasn't responded back within max allowed time`，也就是 Bastion 服務等不到主機上的 plugin 回報工作階段的狀態。三次之間各改了一個條件，排除了兩個成因：

| 次數 | 建立時間 | 跟前一次的差別                                                       | 結果           | 排除的成因                  |
| ---- | -------- | -------------------------------------------------------------------- | -------------- | --------------------------- |
| 1    | 11:04    | plugin 剛轉成 `RUNNING` 就建                                         | 約 15 分鐘逾時 | 無                          |
| 2    | 11:21    | plugin 已經跑了 17 分鐘                                              | 約 15 分鐘逾時 | plugin 剛啟動、還沒同步     |
| 3    | 11:52    | 暫時打開中繼資料第一版（`areLegacyImdsEndpointsDisabled:false`）再建 | 約 15 分鐘逾時 | plugin 只能讀中繼資料第一版 |

第三次之後把設定改回只允許第二版（`oci compute instance update --instance-id <主機的 OCID> --instance-options '{"areLegacyImdsEndpointsDisabled":true}'`，不必重開機）。

主機開機時的序列主控台輸出可以不登入就讀，用來確認開機與代理程式的啟動：

```bash
oci compute console-history capture --instance-id <主機的 OCID> --wait-for-state SUCCEEDED --query data.id --raw-output
oci compute console-history get-content --instance-console-history-id <上一條印出的 OCID> --length 10000000 --file <存檔的路徑>
```

- `--wait-for-state SUCCEEDED`：擷取是非同步的作業，等它完成再讀內容；不等的話，緊接著的 `get-content` 可能讀到還沒擷取完的內容。
- `--length 10000000`：要讀的位元組數。官方說明一次擷取最多 1 MB，填一個比 1 MB 大的數字就是讀全部。

這次的輸出（1576 行）裡，cloud-init 在開機 63 秒時完成，`oracle-cloud-agent`（Ubuntu 上是 snap 套件）有啟動，`ssh.socket` 在監聽；`no authorized SSH keys fingerprints found for user ubuntu` 是選了 No SSH keys 的預期結果。序列主控台輸出不含 plugin 的日誌。

### 成因：A1 加 Ubuntu 是官方列出的不支援組合

Oracle 官方〈Known Issues for Bastion〉的第一條寫明，用 Arm 架構的 Ampere A1 機型建立、而且作業系統不是 Oracle Linux（例如 Ubuntu）的主機，不支援 managed SSH session；原文的理由是這類主機上的 Bastion plugin 沒有正確啟用（「isn't properly enabled on some Arm-based instances」），所以建立工作階段會失敗。這台正是 A1 加 Ubuntu 24.04。主控台上的 plugin 狀態是 `RUNNING`，跟原文說的「沒有正確啟用」在主控台上看不出差別，所以 plugin 的狀態不能當成這條路走得通的證據。官方給的替代做法是改用 SSH port forwarding session。同一頁的另一條是 Ubuntu 上的 Oracle Cloud Agent 低於 1.11 版時 managed SSH session 也會失敗（處置是在主機上跑 `sudo snap refresh oracle-cloud-agent`），這一條要登入主機才查得到版本。

上面那張表的三次是在查到這一條之前做的。官方〈Managed SSH Session Creation Failed〉列的成因，對這台的狀況是：代理程式與 Bastion plugin 都在跑；VCN 有 service gateway 與路由，缺 gateway 時 plugin 的狀態會是 `INVALID`，這台不是；`ubuntu` 是存在的使用者；sshd 設定那一項，這台沒有 SSH 登入的入口可以查。建 managed SSH session 之前先讀 Known Issues 那一頁，確認機型與作業系統的組合有支援，三次各 15 分鐘的等待就可以省掉。

### 這台主機接下來的登入入口

Port forwarding session 不經過 plugin，主機的登入驗證仍然是主機上的 sshd 與 `authorized_keys`；這台建立時選了 No SSH keys，主機裡沒有任何公鑰，所以 port forwarding session 建得起來也登不進去。要讓這台登得進去，可走的路是：

- **Compute Instance Run Command**：從 API 在主機上執行指令，把公鑰寫進 `authorized_keys`，再用 port forwarding session 登入。要另外建 dynamic group（依規則把主機本身當成 IAM 主體的群組）與允許它執行指令的 IAM 政策，這次沒有做。
- **重建主機**：重建時放自己的公鑰、改用 port forwarding session；或改用 Oracle Linux 映像，A1 加 Oracle Linux 是 managed SSH session 支援的組合。兩種都要重新搶 A1 的容量。

截至 2026-10-25，這台主機的 Bastion 登入還沒有走通。

## 刪除這組資源的順序

實驗結束要清掉時，順序跟建立時相反，因為每一項資源被後面建的資源依賴著：

1. 終止主機，在終止對話框勾選「Permanently delete the attached boot volume」，開機磁碟才會一起刪掉。
2. 刪除 Bastion（`oci bastion bastion delete --bastion-id <Bastion 的 OCID>`）。Bastion 的私有端點在目標 subnet 裡，Bastion 還在時 subnet 刪不掉；它的工作階段隨 Bastion 一起失效。
3. 刪除 subnet。subnet 裡還有主機或網卡時刪不掉。
4. 刪除 subnet 用過的路由表與 security list。
5. 刪除 service gateway。
6. 刪除 VCN。
7. 刪除 compartment。官方〈Deleting a Compartment〉寫明 compartment 要先清空所有資源（包括掛在它上面的權限政策）才能刪除，刪除是非同步的工作，狀態會先變成 Deleting。

這個順序還沒有實際跑過（截至 2026-10-25 主機還在），各項刪不掉時，看錯誤訊息指出的那一項依賴、先刪它。

要讓這組資源可以重建、清掉也不心疼，改用 IaC 描述它們，見 [IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)；已經用主控台或 CLI 建好的資源要收進 IaC，做法見 [Unmanaged Resource 批次 Import 工作流](/infra/takeover/partial-iac-bulk-import/)。
