---
title: "Oracle Cloud 建立主機的實測紀錄：前置網路、主控台各分頁的 Always Free 設定值、等效的 CLI 指令與容量不足"
date: 2026-10-24
description: "在 Oracle Cloud 主控台建立一台 Always Free 的 A1 Ubuntu 主機時，前置的 compartment、VCN 與閘道怎麼建，Basic information、Security、Networking、SSH keys、Storage 與 Management 各分頁填了什麼、為什麼這樣填，等效的 CLI 指令與它跟主控台預設值的差異，Oracle Cloud Agent 各 plugin 的用途與這次的預設，容量不足、VCN 選單找不到、Bastion plugin 預設關閉這幾個實測遇到的狀況，以及刪除這組資源的順序"
weight: 5
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "vm", "free-tier"]
---

這篇記錄在 Oracle Cloud 主控台建立一台主機的實際設定，目標是 Always Free 額度內、沒有公開 IP、之後經由 Bastion 服務登入的 A1 Ubuntu 主機。Bastion 是 Oracle Cloud 代管的登入服務：它在主機所在的 subnet 裡有一個私有端點，替沒有公開 IP 的主機開有時效的 SSH 工作階段（session），主機與 Bastion 都不需要公開 IP。範圍從建好前置的網路開始，到按下 Create 為止；每個欄位背後的概念連到 [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/) 底下對應的那一篇，這裡只寫 Oracle Cloud 的欄位與這次的取值。實測日期 2026-10-24，區域 `ap-batam-1`。這組設定當天因為容量不足沒有建立成功，所以 Bastion 登入這一段還沒有實測過。

## 進建立頁之前：compartment、VCN、閘道與 private subnet

建立頁上的網路欄位只能選已經存在的 VCN 與 subnet，或讓主控台建一個新的（新建的那個會帶一份對網際網路開放 22 port 的預設規則，見〈Networking：VCN、subnet 與公開 IP〉）。這次先用 OCI CLI 建好下面幾項，建立頁上一律選既有的。CLI 的登入方式見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)，主控台上的對應頁面是 Identity & Security → Identity → Compartments 與 Networking → Virtual cloud networks。

- **compartment `blog-verify`**：tenancy 底下分組資源的容器，實驗用的資源都放在這裡，清理時不碰 root 裡的其他設定。
- **VCN `verify-vcn`**（`10.0.0.0/16`）：主機所在的虛擬網路。
- **service gateway 與路由表 `private-rt`**：私有 subnet 沒有通往網際網路的路由，主機上的 Oracle Cloud Agent 要連到 Oracle 自己的服務端點，經由 service gateway 出去；路由表裡那一條規則把送往 Oracle 服務網段的流量導向 service gateway。官方〈Bastion〉的說明寫明，建立 managed SSH session 之前，VCN 要有一個閘道（service gateway、internet gateway 或 NAT gateway）與通往它的路由規則。

這份網路刻意沒有 NAT 閘道，主機只用來測 Bastion 登入；沒有 NAT 時，主機連不到 Ubuntu 的套件來源，`apt` 更新與安裝都會失敗。要當一般主機用，就另外建一個 NAT 閘道，在路由表加一條通往它的路由，並在 security list 的出站規則放行網際網路。

- **security list `private-sl`**：入站只放行來源是同一個 subnet（`10.0.1.0/24`）的 22 port，因為 Bastion 的私有端點建在這個 subnet 裡，SSH 連線從那裡進來；出站只放行送往 Oracle 服務網段與同一個 subnet 的流量。
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

| 欄位                  | 這次的值                                     | 理由與對應的概念篇                                                                                                                         |
| --------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Name                  | `verify-a1`                                  | 自動產生的 `instance-<日期>-<時間>` 在清單裡認不出用途                                                                                     |
| Create in compartment | `blog-verify`                                | 實驗資源集中在一個 compartment，清理時不碰 root 裡的設定                                                                                   |
| Availability domain   | AD-1                                         | 這一區只有一個 AD，見 [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/)                                           |
| Capacity type         | On-demand                                    | Always Free 的額度只算在 on-demand 這種容量上；preemptible 會被收回，見 [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/) |
| Fault domain          | Let Oracle choose the best fault domain      | 單一台主機指定故障域沒有好處，還會縮小可用容量                                                                                             |
| Image                 | Canonical Ubuntu 24.04（build 2026.09.18-0） | Oracle 維護的平台映像，架構跟著機型選 aarch64                                                                                              |
| Shape                 | `VM.Standard.A1.Flex`，1 OCPU、6 GB          | Always Free 的 A1 上限是 2 OCPU、12 GB，先用一半，另一半留給第二台主機；之後要加大不必重建，代價是重開機                                   |

「Change shape」的視窗依處理器分欄。這一區的 Ampere 欄有 `VM.Standard.A1.Flex` 並標示 Always Free-eligible；AMD 欄只列出 `VM.Standard.E5.Flex`，Always Free 的 `VM.Standard.E2.1.Micro` 不在清單上。E5.Flex 不在免費額度內，選了會照一般價格計費。區域之間提供的機型不同，這一點見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)。

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

出站是全部放行。Subnet 沒有另外指定 security list 時套用的就是這一份，所以在新建的公開 subnet 裡建一台有公開 IP 的主機，那台主機的 SSH port 一建好就對整個網際網路開放。官方文件把這一條寫成允許「authorized source IP addresses」，而預設填的來源是 `0.0.0.0/0`，等於任何位址都算在內；官方建議把來源收緊。這份規則跟 NSG 怎麼合併、為什麼只在 NSG 裡不開 22 port 擋不住它，見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/) 的〈防火牆規則的位置與合併方式〉。

## SSH keys

這次選 No SSH keys，目的是驗證主機完全不放金鑰時，managed SSH session 這條路本身走不走得通；managed SSH session 在主機有放公鑰時照樣能用，只是那樣就驗不出這件事。選了之後主機裡不放任何長期有效的公鑰，登入改用 Bastion 的 managed SSH session，由主機上的 Bastion plugin 臨時放進一把公鑰。Oracle Cloud 對這個選項的說明是選了之後就不能再提供公鑰，所以這條路要求〈Management：Oracle Cloud Agent 與其他進階選項〉那一節的 Bastion plugin 一定打開。第一次建主機、還沒走通 Bastion 時，放自己的公鑰比較保險：Bastion 的另一種 session（port forwarding）不經過 plugin，用的是主機自己的 sshd 與那把公鑰，plugin 出問題時還有這條路，見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/)。

## Storage

開機磁碟維持映像檔的預設大小（50 GB）、效能等級 Balanced、Use in-transit encryption 為 Enabled、不指定自己的加密金鑰，不另外建立區塊磁碟。50 GB 在 Always Free 的 200 GB 額度內。要記住的是刪除這台主機時，終止對話框裡的「Permanently delete the attached boot volume」預設不勾，不勾的話開機磁碟會留下來繼續佔著額度，見 [磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)。

## Management：Oracle Cloud Agent 與其他進階選項

Oracle Cloud Agent 的每一項功能是一個 plugin。官方列出的 plugin 與這次建立頁上的預設值：

| Plugin                                                       | 做什麼                                                                      | 這次的預設 |
| ------------------------------------------------------------ | --------------------------------------------------------------------------- | ---------- |
| Compute Instance Monitoring                                  | 回報主機的健康、容量與效能指標給 Monitoring 服務                            | 開啟       |
| Custom Logs Monitoring                                       | 把主機上的自訂日誌送進 Logging 服務                                         | 開啟       |
| Compute Instance Run Command                                 | 從主控台或 API 在主機裡執行腳本，用來遠端設定與排錯                         | 開啟       |
| Cloud Guard Workload Protection                              | 給 Cloud Guard 的工作負載防護用；自訂映像沒有啟用代理程式時另外管理它的更新 | 開啟       |
| Bastion                                                      | 讓 Bastion 服務對沒有公開 IP 的主機建立 managed SSH session                 | 關閉       |
| Block Volume Management                                      | 替主機設定區塊磁碟的連線                                                    | 關閉       |
| OS Management Hub Agent                                      | 管理與監看作業系統的更新與修補                                              | 關閉       |
| Vulnerability Scanning                                       | 掃描主機上的弱點，例如需要更新的套件                                        | 關閉       |
| Management Agent                                             | 替 Oracle 的監控與分析服務收集作業系統與應用程式的資料                      | 關閉       |
| High Performance Computing                                   | 給 HPC 機型的運算叢集用                                                     | 關閉       |
| Fleet Application Management、Oracle Java Management Service | 給 Oracle 的應用程式與 Java 執行環境管理服務用                              | 關閉       |

官方的 plugin 說明頁對 Custom Logs Monitoring 在 A1 上的支援前後不一致：頁面上的註記寫它不支援 A1 機型，同一頁的代理程式版本紀錄（1.29.0）寫已經支援 Arm 處理器。這次維持建立頁的預設（開啟）：這個 plugin 只負責把日誌送進 Logging，要在 Logging 服務裡設定收哪些日誌之後才開始收，費用依收進來的日誌量計算（官方〈Custom Logs〉）；沒有設定時它不影響主機建立與登入。

這次要改的只有一項：**把 Bastion 打開**。沒有放 SSH 金鑰的主機只能經由 Bastion 的 managed SSH session 登入，而這個 plugin 預設關閉。漏開時不必重建，主機建好之後可以在主機頁面的 Oracle Cloud Agent 分頁打開，官方說明最多 10 分鐘生效。

其餘維持預設，理由各自如下：

- **Authorization header：Enabled**。這是建立頁對 Ubuntu 的預設，而官方列出支援中繼資料第二版的平台映像只有 Oracle Linux 系列，Ubuntu 不在清單上。這台主機沒有建成，所以還沒驗到開著這個選項時，cloud-init 寫公鑰與代理程式讀設定是否正常；要怎麼確認見 [代理程式、中繼資料服務、初始化腳本、維護行為與標籤](/infra/cloud-providers/vm-options/management/) 的〈中繼資料服務與 Authorization header〉。
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
- `--is-pv-encryption-in-transit-enabled true` 與 `--instance-options '{"areLegacyImdsEndpointsDisabled":true}'`：前者對應 Storage 段的 in-transit encryption，後者對應 Management 段的 Authorization header（只允許中繼資料第二版）。這兩項在主控台是預設開啟，CLI 不給時，官方的 CLI 參考寫明 in-transit encryption 的預設值是 false，所以要跟主控台一致就要明確帶上。這次背景重試用的指令一開始沒有這兩行，之後才補上。
- `--auth security_token`：用 session token 登入時每條指令都要帶，不帶會報設定檔缺 `user`；用 API 簽章金鑰時拿掉。在主控台的 Cloud Shell 裡跑時也拿掉，Cloud Shell 裡的 CLI 用 Cloud Shell 自己的驗證，沒有本機的 session 設定。
- 沒有給 `--ssh-authorized-keys-file`，等同主控台的 No SSH keys。

主控台與 CLI 的差別在錯誤訊息的可讀性：主控台的 Change shape 視窗只列出這一區有的機型，並把跟所選映像檔架構不相容的機型標成不可選，CLI 送出這一區沒有的機型只回 `404 NotAuthorizedOrNotFound`，這個錯誤碼同時涵蓋權限不足與資源不存在。

## 按下 Create 之後的結果：容量不足

主控台回的訊息是：

```text
Out of capacity for shape VM.Standard.A1.Flex in availability domain AD-1. Create the instance in a different availability domain or try again later.
```

意思是這個 AD 裡跑 A1 的實體主機當下沒有空出這個規格需要的資源；同一段時間用 CLI 送出的請求回的是 `InternalError: Out of host capacity.`，偶爾是 `429 TooManyRequests`（請求太頻繁被限流）。會影響容量的設定是 AD、fault domain 與規格大小：訊息建議換 AD，這一區只有一個 AD 可以換；Compute 的〈Known Issues〉頁另外建議不指定 fault domain（這次已經是讓 Oracle 選）、改用較小的規格，以及建立前用 `CreateComputeCapacityReport` 這個 API 查那個機型當下有沒有容量；官方 Always Free 頁另外列了升級成付費帳戶。試用期間還能用試用金改建不在免費額度內的 x86 機型，代價是試用結束時被回收，各種帳號狀態的結果見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉。這次的帳號只用免費額度，剩下的做法是隔一段時間再試，有人釋出資源時才會短暫空出位置。

這次的重送紀錄：先以 90 秒的間隔送了九次，前三次收到 429、後六次是容量不足；之後改成每 5 分鐘一次，到當天晚上仍然是容量不足。限流的門檻依帳號與 API 而定，間隔要看自己收到的回應碼調整：收到 429 就拉長，收到容量不足才是真的沒有硬體。截至 2026-10-24，這組設定還沒有建立成功。

## 刪除這組資源的順序

實驗結束要清掉時，順序跟建立時相反，因為每一項資源被後面建的資源依賴著：

1. 終止主機，在終止對話框勾選「Permanently delete the attached boot volume」，開機磁碟才會一起刪掉。
2. 刪除 subnet。subnet 裡還有主機或網卡時刪不掉。
3. 刪除 subnet 用過的路由表與 security list。
4. 刪除 service gateway。
5. 刪除 VCN。
6. 刪除 compartment。官方〈Deleting a Compartment〉寫明 compartment 要先清空所有資源（包括掛在它上面的權限政策）才能刪除，刪除是非同步的工作，狀態會先變成 Deleting。

這個順序沒有在這次實測裡跑過（主機沒有建成），各項刪不掉時，看錯誤訊息指出的那一項依賴、先刪它。

要讓這組資源可以重建、清掉也不心疼，改用 IaC 描述它們，見 [IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)；已經用主控台或 CLI 建好的資源要收進 IaC，做法見 [Unmanaged Resource 批次 Import 工作流](/infra/takeover/partial-iac-bulk-import/)。

## 延伸閱讀：建立頁的概念與帳號層的限制

[建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/) 底下各篇是這些欄位背後的 vendor 中立概念，附三家的欄位名稱對照；這台主機為什麼只能建在 `ap-batam-1`、這一區缺哪些機型，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)。
