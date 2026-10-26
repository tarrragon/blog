---
title: "Oracle Cloud 建立主機的實測紀錄：建立前的檢查、前置網路、主控台各分頁的 Always Free 設定值、等效的 CLI 指令、容量不足的重送、Bastion 工作階段逾時、Run Command 補公鑰的嘗試與重建後經由 port forwarding 登入"
date: 2026-10-24
description: "要在 Oracle Cloud 建一台沒有公開 IP、經由 Bastion 登入的 Always Free A1 主機，想照一次實測重做、看建立頁每一欄的取值與換一種做法的結果時讀；也用在建立請求一直回容量不足、managed SSH session 建立逾時，或沒放公鑰的主機想用 Run Command 救援、Oracle Linux 10 的主機上找不到 Bastion plugin、想改用 port forwarding session 登入的時候"
weight: 5
aliases: ["/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/"]
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "vm", "free-tier"]
---

實測日期是 2026-10-24 與 2026-10-25，區域 `ap-batam-1`，帳號是 Oracle Cloud 的 Free Tier，在本機用 OCI CLI 與主控台建立一台 A1 Ubuntu 24.04 主機，再從本機經由 Bastion 建立登入的工作階段；2026-10-25 下午另外用 Run Command 對同一台主機送指令；同一天晚上另建一台 A1 Oracle Linux 10.2 主機，建立時放公鑰，經由 Bastion 的 port forwarding session 登入。

這篇記錄在 Oracle Cloud 建立一台主機的實際操作，目標是 Always Free 額度內、沒有公開 IP、之後經由 Bastion 服務登入的 A1 Ubuntu 主機。Bastion 是 Oracle Cloud 代管的登入服務：建立 Bastion 時指定一個目標 subnet，它替那個 subnet 裡沒有公開 IP 的主機開有時效的 SSH 工作階段（session）；這次要用的 managed SSH session 這種工作階段，由主機上 Oracle Cloud Agent 的 Bastion plugin 在建立工作階段時把一把公鑰臨時放進主機。工作階段的種類與需要的條件見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。內容依操作的順序是：建立之前的檢查（哪些設定建好就改不了、登入路徑上每個服務支援哪些機型與作業系統、登入路徑要有兩條、各自依賴哪些元件、容量稀缺時怎麼選設定）；前置的 compartment、VCN、service gateway 與 private subnet；主控台建立頁 Basic information、Security、Networking、SSH keys、Storage、Management 各分頁的取值與理由，含 Oracle Cloud Agent 各 plugin 的用途；等效的 CLI 指令；按下 Create 之後的容量不足，CLI 自己的重送、這個帳號量到的限流門檻與依回應碼調整間隔的重送腳本；主機建好之後建立 Bastion 與 managed SSH session、工作階段建立逾時的排查與官方列出的成因；用 Run Command 補公鑰時建立的 dynamic group 與 IAM 政策、送指令與讀結果的指令，以及 `ocarun` 沒有 sudo 的結果；這台主機剩下的登入入口；改用 Oracle Linux 映像、建立時放公鑰重建一台：建立之前依作業系統版本查可用的 plugin、指定大版本查映像、Oracle Linux 10.2 主機上沒有 Bastion plugin 的結果，以及經由 port forwarding session 登入與比對主機金鑰的指令；以及刪除這組資源的順序。每一節除了這次的取值，也寫出那一步沒做時會看到什麼、有哪些替代做法與各自換到什麼。每個欄位背後的概念連到 [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/) 底下對應的那一篇，這裡只寫 Oracle Cloud 的欄位、這次的取值與實際跑過的指令。

這次的實測沒有在建立之前做那幾項檢查，結果是主機建好之後登不進去：managed SSH session 逾時三次，Run Command 執行得了指令卻沒有 sudo，主機又沒有公鑰。所以〈建立之前的檢查：套在這台主機上的查法與結果〉是事後補上的檢查，最後是照那幾項檢查重建一台才登入成功。

## 建立之前的檢查：套在這台主機上的查法與結果

這些檢查的判斷依據在 [建立主機之前的檢查](/infra/cloud-providers/vm-options/pre-launch-checks/)，這一節是套在這台主機（A1、Ubuntu 24.04、private subnet、經由 Bastion 登入）上的查法與結果。這些檢查排在進建立頁之前，因為結果會改變建立頁上的選擇：映像檔、SSH keys 欄位與要打開的 plugin。

**建好就改不了的設定**。用 CLI 讀修改主機的說明，找出建立後不能改的欄位：

```bash
oci compute instance update --help | sed -n '/--metadata/,/--extended-metadata/p'
```

說明裡寫明 `user_data` 與 `ssh_authorized_keys` 建立後不能改，送出修改的請求會被拒絕。這台的設定裡落在這一種的是 SSH keys（選了 No SSH keys）、初始化腳本（沒放）、映像檔（Ubuntu；替換開機磁碟只能換同一個發行版）與 Shielded instance（Secure Boot、Measured Boot、Trusted Platform Module 都關閉）。指令裡 `sed -n` 的範圍從 `--metadata` 印到下一個選項 `--extended-metadata`，這是本機這一版 CLI 的選項順序；版本不同、順序不同時，把結束的 pattern 換成 `--metadata` 之後的那一個選項。

**登入路徑上各服務的支援組合**。這台規劃的 managed SSH session、不經過 plugin 的 port forwarding session，與事後想用的 Run Command，在官方文件上的結果：

| 服務                                        | 要讀的文件或查詢                                       | A1 加 Ubuntu 的結果                                              |
| ------------------------------------------- | ------------------------------------------------------ | ---------------------------------------------------------------- |
| Bastion managed SSH session                 | 〈Known Issues for Bastion〉第一條                     | 不支援                                                           |
| Bastion plugin 在這個作業系統版本上可不可用 | `oci instance-agent available-plugins get`（依版本查） | 2026-10-25 查 Ubuntu 24.04 有；這一層不分機型，A1 的限制看上一列 |
| Bastion SSH port forwarding session         | 同 managed SSH session；它不經過 plugin                | 支援，條件是主機裡有公鑰                                         |
| Compute Instance Run Command                | Run Command 說明頁的支援映像清單                       | 清單上沒有 Ubuntu；實測執行得了指令，而 `ocarun` 沒有 sudo       |

這幾項在建立之前都查得到，Run Command 要事先替 `ocarun` 設 sudo、第一次建主機先放公鑰比較保險這兩點，[登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 也有寫。2026-10-25 的建立沿用 2026-10-24 寫好的重送腳本，腳本的參數寫在讀這些文件之前，重新啟動時沒有再對一次。Known Issues 只寫到作業系統，沒有寫版本，而同一個作業系統的不同版本可用的 plugin 不同：後來重建時，2026-10-25 查到 Oracle Linux 10 確定沒有 Bastion plugin，9 與 8 的結果跟查不到時的回應相同、分不出來；這份清單隨代理程式的版本更新，要在建立當下自己查一次，查法見〈建立之前查映像檔版本與它可用的 plugin〉。

**兩條登入路徑各自依賴的元件**。這台只規劃了 managed SSH session 一條，它依賴 Bastion plugin 與支援範圍，而這次最沒有把握的正是這兩項。不經過 plugin 的 port forwarding session 要主機裡有公鑰，選了 No SSH keys 就沒有；兩種工作階段都經過 Bastion、security list 的 22 port 與主機的 sshd，所以有公鑰時，這一組擋得住 plugin 與支援範圍的問題，擋不住 sshd 改壞。不經過 sshd 的是序列主控台，它要一個設了密碼的帳號，Ubuntu 平台映像的 `ubuntu` 只用金鑰登入，要用初始化腳本在建立時建，而初始化腳本也是建立後不能改的欄位。所以這台建立的那一刻就只剩一條 SSH 路徑，而那條路徑是不支援的組合；剩下的入口是替換開機磁碟、把開機磁碟掛到另一台主機修改、序列主控台與重建，各自的條件見〈這台主機剩下的登入入口〉。

**容量稀缺時的取捨**。A1 在這一區的容量要靠重送腳本搶（〈重送建立請求：CLI 自己的重送、限流門檻與重送腳本〉），選錯建立後不能改的設定，補救就是再搶一次。照這一項，這台的設定該選補救代價低的那一種：放自己的公鑰、或改用 Oracle Linux 映像（A1 加 Oracle Linux 是 managed SSH session 支援的組合，版本要選可用 plugin 裡有 Bastion 的那一個）。「完全不放金鑰」裡跟機型無關的部分（Bastion 與 plugin 的設定、security list）可以在容易重建的機型上驗，而 A1 加 Ubuntu 這個組合支不支援只能讀 Known Issues，演練驗不到。這一區的 Change shape 視窗沒有列出 E2.1.Micro（見〈Basic information：名稱、compartment、位置、映像檔與機型〉），所以這個帳號找不到容易重建的免費機型；這時的做法是建這台時就選 A1 加 Oracle Linux 這個支援的組合來驗「完全不放金鑰」；它同樣要搶 A1 的容量，差別在組合不支援的風險已經由 Known Issues 排除，失敗的代價同樣是再搶一次。

## 進建立頁之前：compartment、VCN、閘道與 private subnet

建立頁上的網路欄位只能選已經存在的 VCN 與 subnet，或讓主控台建一個新的（新建的那個會帶一份對網際網路開放 22 port 的預設規則，見〈Networking：VCN、subnet 與公開 IP〉）。這次先用 OCI CLI 建好下面幾項，建立頁上一律選既有的。CLI 的登入方式見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)，主控台上的對應頁面是 Identity & Security → Identity → Compartments 與 Networking → Virtual cloud networks。

- **compartment `blog-verify`**：tenancy 底下分組資源的容器，實驗用的資源都放在這裡，清理時不碰 root 裡的其他設定。
- **VCN `verify-vcn`**（`10.0.0.0/16`，位址範圍的寫法見 [CIDR](/infra/knowledge-cards/cidr/) 卡）：主機所在的虛擬網路。
- **service gateway 與路由表 `private-rt`**：私有 subnet 沒有通往網際網路的路由，主機上的 Oracle Cloud Agent 要連到 Oracle 自己的服務端點，經由 service gateway 出去；路由表裡那一條規則把送往 Oracle 服務網段的流量導向 service gateway。managed SSH session 對閘道與路由的要求見 [登入](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉，這次在其中選了 service gateway。

這份網路刻意沒有 NAT 閘道，主機只用來測 Bastion 登入；沒有 NAT 時，主機連不到 Ubuntu 的套件來源，`apt` 更新與安裝都會失敗。要當一般主機用，就另外建一個 NAT 閘道，在路由表加一條通往它的路由，並在 security list 的出站規則放行網際網路。這三項在 Ubuntu 24.04 主機上實際加過一次，出站規則改放在只掛在那台主機上的 NSG，指令與錯誤原文見 [Oracle Cloud 私有子網路 Ubuntu 主機的實測紀錄：套件來源的出站（NAT gateway、路由與 NSG）、序列主控台的連線，以及被回收之後的重建](/infra/cloud-providers/oracle-cloud/hands-on/private-ubuntu-egress-console-rebuild/)〈加出站：NAT gateway、路由規則與只掛在這台主機上的 NSG〉。

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

這幾項各自沒做時的結果與替代做法：

- **不建 compartment、資源放在 root**：主機照樣建立成功（照文件推出，這次沒有在 root 建）。清理時要在 root 的資源清單裡逐項挑出這次建的，權限政策也只能寫成整個 tenancy 的範圍；〈Run Command 補公鑰的嘗試：dynamic group、IAM 政策與 ocarun 沒有 sudo 的結果〉那條政策寫成 `in compartment blog-verify`，範圍就只到這組實驗資源。
- **不用 private subnet、改用公開 subnet 加公開 IP**：主機有公開 IP，security list 只放行自己的公開 IP 連 22 port，就能用 `ssh` 直接登入，不需要 Bastion（照文件推出，這次沒有建公開 subnet）；代價是主機的位址暴露在網際網路上，家用網路的公開 IP 改變時規則要跟著改。兩種做法對管理通道各層的影響見 [網路](/infra/cloud-providers/vm-options/networking/) 的〈公開 IP：網際網路上的入口〉與 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。
- **不建 service gateway 與它的路由**：主機上的 Oracle Cloud Agent 連不到 Oracle 的服務端點。官方〈Managed SSH Session Creation Failed〉寫明這時 Bastion plugin 的狀態是 `INVALID`、managed SSH session 建不起來；Run Command 的說明頁只對腳本或輸出放在 Object Storage 的用法寫了出站條件，純文字的用法同樣要讓 plugin 連得到服務端點才領得到指令，這一點是推論，這次沒有在缺閘道的情況下實跑。替代做法是 NAT 閘道：它同樣讓代理程式連得到服務端點，另外讓主機連得到網際網路上的套件來源。
- **security list 的 22 port 放行 `0.0.0.0/0`**：這個 subnet 禁止公開 IP，網際網路上的來源本來就到不了主機，所以結果相同（從網路設定推出，這次沒有改成全開驗證）；收窄成同一個 subnet，是讓這份 security list 之後被掛到另一個允許公開 IP 的 subnet 時，那個 subnet 的 22 port 不會跟著對網際網路開放。

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

這一頁影響後面結果最大的是映像檔。這次選 Ubuntu，A1 加 Ubuntu 落在 managed SSH session 不支援的組合裡（〈建立之前的檢查：套在這台主機上的查法與結果〉）。替代做法是 Oracle Linux 的 aarch64 平台映像：A1 加 Oracle Linux 是 managed SSH session 支援的組合，條件是選的版本可用的 plugin 裡有 Bastion（2026-10-25 實測 10 確定沒有，9 與 8 用查詢工具分不出，查法與讀法見〈建立之前查映像檔版本與它可用的 plugin〉），Oracle Linux 也在 Run Command 的支援映像清單上；換到的代價是預設使用者改成 `opc`、套件管理改用 `dnf`，照 Ubuntu 寫的教學指令要換寫法。映像檔建立之後只能換成同一個發行版（〈Replacing a Boot Volume〉），所以這一欄選錯，補救就是重建。

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

這次選 No SSH keys，目的是驗證主機完全不放金鑰時，managed SSH session 這條路本身走不走得通；managed SSH session 在主機有放公鑰時照樣能用，只是那樣就驗不出這件事。選了之後主機裡不放任何長期有效的公鑰，登入改用 Bastion 的 managed SSH session，由主機上的 Bastion plugin 臨時放進一把公鑰。Oracle Cloud 對這個選項的說明是選了之後就不能再提供公鑰，所以這條路要求〈Management：Oracle Cloud Agent 與其他進階選項〉那一節的 Bastion plugin 一定打開。這次刻意不留退路，代價在〈建立之後：Bastion managed SSH session 逾時的排查〉與〈Run Command 補公鑰的嘗試：dynamic group、IAM 政策與 ocarun 沒有 sudo 的結果〉兩節出現：工作階段的建立逾時之後，主機上沒有任何 SSH 登入的入口，Run Command 又寫不了 `ubuntu` 的 `authorized_keys`。

放公鑰與不放公鑰，差在 managed SSH session 失敗之後還剩什麼：

- **放自己的公鑰**（上傳或貼上）：managed SSH session 失敗時，改建不經過 plugin 的 SSH port forwarding session，用那把公鑰登入。主機在 private subnet、沒有公開 IP，這把公鑰只對經由 Bastion 進來的連線有用；代價是這把金鑰要自己保管。這次如果這樣選，cloud-init 在 Authorization header 開著時寫入公鑰、security list 放行 Bastion 目標 subnet 的 22 port 這兩項成立的話，三次逾時之後就能登入主機查 plugin 的日誌；這是推論，cloud-init 寫公鑰這一段沒有在這台實跑；後來重建的 Oracle Linux 10.2 主機在 Authorization header 開著時寫入了公鑰（〈重建：Oracle Linux 映像加建立時放公鑰，經由 port forwarding session 登入〉），2026-10-26 在 Ubuntu 24.04 平台映像上也驗過寫得進（[Oracle Cloud 私有子網路 Ubuntu 主機的實測紀錄：套件來源的出站（NAT gateway、路由與 NSG）、序列主控台的連線，以及被回收之後的重建](/infra/cloud-providers/oracle-cloud/hands-on/private-ubuntu-egress-console-rebuild/)〈建 Ubuntu 24.04 主機與經由 port forwarding 登入〉）。
- **No SSH keys**：主機裡沒有長期有效的公鑰，登入完全依賴 Bastion plugin，而這個欄位建立後不能改（`ssh_authorized_keys` 不接受修改）。plugin 這條路不通時，剩下的入口見〈這台主機剩下的登入入口〉。

第一次建主機、還沒走通 Bastion 時先放公鑰的做法與它的前提，見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。

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

- **Authorization header：Enabled**。這是建立頁對 Ubuntu 的預設，而官方列出支援中繼資料第二版的平台映像只有 Oracle Linux 系列，Ubuntu 不在清單上。2026-10-25 建好的主機開著這個選項，代理程式照常回報各 plugin 的狀態；managed SSH session 的建立逾時時，暫時改成允許第一版也一樣逾時，所以這個選項不是那次失敗的成因，見〈建立之後：Bastion managed SSH session 逾時的排查〉。cloud-init 從中繼資料讀出公鑰寫進 `authorized_keys` 這一段，這台選了 No SSH keys 驗不到；後來重建的 Oracle Linux 10.2 主機開著這個選項時寫入了，2026-10-26 另一台放了公鑰的 Ubuntu 24.04 主機開著這個選項時也寫入了（〈SSH keys〉那一節的「放自己的公鑰」那一項）。要怎麼確認見 [代理程式、中繼資料服務、初始化腳本、維護行為與標籤](/infra/cloud-providers/vm-options/management/) 的〈中繼資料服務與 Authorization header〉。
- **Live migration：讓 Oracle 選擇**、**Restart after infrastructure maintenance：Enabled**：實驗機能接受維護時被遷移或重開。
- **不放初始化腳本、不加標籤**：這台主機只用來測登入，沒有要預先裝的軟體。沒放初始化腳本的結果，到了要用 Run Command 救援時才出現：Run Command 以 `ocarun` 執行，沒有 sudo（〈Run Command 補公鑰的嘗試：dynamic group、IAM 政策與 ocarun 沒有 sudo 的結果〉），而替 `ocarun` 設 sudo 的 sudoers 檔，官方列的做法有兩種：建立時用 cloud-init 放，或建好之後登入主機設定；登不進去時只剩前一種。所以要把 Run Command 當成救援入口，替代做法是在這一欄放一段 cloud-init，建立時把官方說明頁列的那一行 sudoers（`ocarun ALL=(ALL) NOPASSWD:ALL`，或只列救援要用的指令）寫進 `/etc/sudoers.d/` 底下的一個檔；這個欄位也是建立後不能改的那一種。這段 cloud-init 的寫法這次沒有實跑，所以這裡不附，實跑過再補（記在 Oracle Cloud 目錄頁的 Backlog）。給 `ocarun` 不限指令的 sudo，等於讓有權限送 Run Command 的人取得主機的 root，所以送指令的權限政策要跟著收窄。

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
    500) back=$(( back - 10 < 60 ? 60 : back - 10 )) ;;   # 容量不足：每次縮 10 秒，下限 60 秒
    *)   echo "回應碼 ${status}，重送也不會好，停下來看訊息：$(grep -o '"message": "[^"]*"' <<<"$out" | head -1)"; exit 4 ;;   # 400 參數錯誤這類
  esac
  echo "$(date +%H:%M:%S) ${status:-?}，約 ${back} 秒後再送"
  sleep $(( back - 15 + RANDOM % 31 ))                   # 加 ±15 秒的隨機抖動
done
```

- 四個佔位值的查法與〈等效的 CLI 指令〉那一節相同；`--display-name verify-a1` 是主機在清單上的名稱，換成自己要的名稱時，〈重複建立的風險〉那一項查同名主機的指令也跟著換；`--shape-config` 到 `--instance-options` 是那一節的同一組設定，`--no-retry` 是寫在子命令之前的全域選項。
- **間隔的調整方式**：收到 429 時間隔加倍，收到容量不足的 500 時每次縮 10 秒，所以間隔會在「剛好不被限流」的附近來回。被限流的期間就算剛好有容量空出來也送不進去，所以把頻率壓在門檻下、讓請求能長時間穩定地送，比把間隔縮到最短更有機會碰上容量釋出的那一刻。120、600、60 這三個值是起點、上限與下限，換帳號時從 120 起跑，讓腳本自己往門檻靠。
- **抖動（jitter）**：每次的等待多加 ±15 秒的隨機值，讓送出的時間點不落在固定的週期上。間隔加倍的退避做法見 [Exponential Backoff](/backend/knowledge-cards/exponential-backoff/) 卡，那張卡把 jitter 列為退避要一起搭配的一項；抖動對這次搶到容量有沒有影響，這次沒有量。
- **驗證方式**：`export OCI_CLI_AUTH=security_token` 等同每條指令都帶 `--auth security_token`。`--profile DEFAULT` 填 `oci session authenticate` 時取的 profile 名稱，沒有另外取名時就是 `DEFAULT`。
- **判斷建立成功的方式**：輸出裡找得到 `ocid1.instance.` 開頭的 OCID 就算成功。標準錯誤併進了 `$out`，CLI 在 OCID 之前印出警告時（例如設定檔權限的警告），整段輸出就不是以 OCID 開頭；只比對開頭的話，已經建成的這一次會被當成失敗、再送一次，建出第二台。
- **結束條件**：建立成功（exit 0）、session token 無法再延長或收到 401（exit 2）、輸出裡讀不出回應碼（exit 3，設定檔或網路錯誤這類，重送也不會好）、收到 500 與 429 以外的回應碼（exit 4）。只有 500（容量不足）與 429（限流）是等一段時間就可能變好的回應；400 這類回應代表請求本身有誤（例如 `<AD 的完整名稱>` 沒換掉或填錯），重送幾次都是同一個結果，所以腳本印出回應碼與 `message` 就結束，照訊息改好參數再跑。`last_refresh=0` 讓腳本開跑時先延長一次 token，開跑時 token 只剩不到 30 分鐘也不會在第一次延長之前過期。session token 一次登入最長延到 24 小時，超過就要重跑 `oci session authenticate`，見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)；要讓腳本跑超過一天，改用 API 簽章金鑰，並拿掉 `OCI_CLI_AUTH` 與延長 token 的那一段。
- **重複建立的風險**：建立成功就結束，所以收得到回應時，同一支腳本不會建出第二台。收不到回應的情形擋不住：建立請求在 Oracle 那一端已經成功、回應卻因為網路中斷沒有回到本機，這一次會落進讀不出回應碼的分支而結束（exit 3）。所以腳本以 exit 3 結束、或要再次執行之前，先用 `oci compute instance list -c <compartment 的 OCID> --display-name verify-a1` 確認沒有還在的同名主機。

2026-10-25 實際跑的版本另外在開跑前查一次有沒有同名主機、把每次的結果寫進紀錄檔，重送與間隔的邏輯跟上面相同，只是那時遇到 500 與 429 以外的回應碼也會重送；2026-10-25 那一輪回的都是 500 與 429，沒有走到這個分支。2026-10-27 補上 exit 4 那一個分支之後，上面這一份用一支假的 `oci` 指令跑過六組回應，確認每個分支的間隔與結束碼：依序回 500、429、500 與成功（間隔 110、220、210 秒，exit 0）、先在標準錯誤印警告再印 OCID（只送一次，exit 0）、回一段沒有回應碼的錯誤（exit 3）、回 401（exit 2）、回 400（只送一次，印出回應碼與 `message`，exit 4）、先回 500 再回 400（重送一次之後 exit 4）；六組都在第一次送出之前先延長了一次 token。400 那兩組的 `message` 是假的 `oci` 自己編的，Oracle 實際回的訊息這次沒有看過。

不用腳本時，替代做法是在主控台隔一段時間按一次 Create：每一次要有人在場，間隔不固定；2026-10-24 在主控台手動按 Create、加上背景以 90 秒與 5 分鐘間隔跑的 CLI 迴圈，整天的回應都是容量不足。不加 `--no-retry`、沿用 CLI 自己的重送時，外層的每一次嘗試送出好幾個請求，同樣的間隔下更早被限流（2026-10-24 以 90 秒送，前三次就收到 429）。換區域、換機型、改付費這些不在重送範圍內的退路，與各自是否計費，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈A1 容量不足時的退路〉。腳本送出的建立參數是寫腳本那一刻的設定，重新啟動腳本之前，參數要再拿〈建立之前的檢查：套在這台主機上的查法與結果〉對一次。

## 建立之後：Bastion managed SSH session 逾時的排查

這一節記錄主機建好之後建立 Bastion 與 managed SSH session、工作階段停在 `CREATING` 約 15 分鐘後轉成 `DELETED`、從 work request 讀到的兩則錯誤，以及對照官方 Known Issues 找到的成因。這一節的指令跟腳本一樣用 session token 驗證：先在 shell 裡 `export OCI_CLI_AUTH=security_token`，或每條指令加 `--auth security_token`，兩種寫法等效。

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

主機開機時的序列主控台輸出（console history：開機輸出的唯讀快照，不是 [序列主控台](/infra/knowledge-cards/serial-console/) 的互動連線）可以不登入就讀，用來確認開機與代理程式的啟動：

```bash
oci compute console-history capture --instance-id <主機的 OCID> --wait-for-state SUCCEEDED --query data.id --raw-output
oci compute console-history get-content --instance-console-history-id <上一條印出的 OCID> --length 10000000 --file <存檔的路徑>
```

- `--wait-for-state SUCCEEDED`：擷取是非同步的作業，等它完成再讀內容；不等的話，緊接著的 `get-content` 可能讀到還沒擷取完的內容。
- `--length 10000000`：要讀的位元組數。官方說明一次擷取最多 1 MB，填一個比 1 MB 大的數字就是讀全部。

這次的輸出（1576 行）裡，cloud-init 在開機 63 秒時完成，`oracle-cloud-agent`（Ubuntu 上是 snap 套件）有啟動，`ssh.socket` 在監聽；`no authorized SSH keys fingerprints found for user ubuntu` 是選了 No SSH keys 的預期結果。序列主控台輸出不含 plugin 的日誌。

### 成因：A1 加 Ubuntu 是官方列出的不支援組合

Oracle 官方〈Known Issues for Bastion〉的第一條寫明，用 Arm 架構的 Ampere A1 機型建立、而且作業系統不是 Oracle Linux（例如 Ubuntu）的主機，不支援 managed SSH session；原文的理由是這類主機上的 Bastion plugin 沒有正確啟用（「isn't properly enabled on some Arm-based instances」），所以建立工作階段會失敗。這台正是 A1 加 Ubuntu 24.04。主控台上的 plugin 狀態是 `RUNNING`，跟原文說的「沒有正確啟用」在主控台上看不出差別，所以 plugin 的狀態不能當成這條路走得通的證據。官方給的替代做法是改用 SSH port forwarding session。同一頁的另一條是 Ubuntu 上的 Oracle Cloud Agent 低於 1.11 版時 managed SSH session 也會失敗（處置是在主機上跑 `sudo snap refresh oracle-cloud-agent`）。這台主機的代理程式版本，後來用 Run Command 讀到是 1.61.0，這一條可以排除，見〈用 Run Command 讀代理程式的版本與日誌〉。

上面那張表的三次是在查到這一條之前做的。官方〈Managed SSH Session Creation Failed〉列的成因，對這台的狀況是：代理程式與 Bastion plugin 都在跑；VCN 有 service gateway 與路由，缺 gateway 時 plugin 的狀態會是 `INVALID`，這台不是；`ubuntu` 是存在的使用者；sshd 設定那一項，這台沒有 SSH 登入的入口可以查。建 managed SSH session 之前先讀 Known Issues 那一頁，確認機型與作業系統的組合有支援，三次各 15 分鐘的等待就可以省掉。

Port forwarding session 不經過 plugin，主機的登入驗證仍然是主機上的 sshd 與 `authorized_keys`；這台建立時選了 No SSH keys，主機裡沒有任何公鑰，所以 port forwarding session 建得起來也登不進去。下一節試的是先用 Run Command 把公鑰寫進主機。

## Run Command 補公鑰的嘗試：dynamic group、IAM 政策與 ocarun 沒有 sudo 的結果

Run Command 從 API 把一段腳本送進主機執行，由主機上的 Run Command plugin 定期向服務領取。要用它寫公鑰，有三件事要同時成立：主機有權限領取指令、plugin 在這個作業系統上執行得了腳本、執行腳本的使用者寫得了 `ubuntu` 家目錄裡的 `authorized_keys`。後兩件在官方文件上都不利：Run Command 說明頁的支援映像清單沒有 Ubuntu，而 plugin 以 `ocarun` 這個使用者執行，要以管理員權限執行得先在主機上加 sudoers 檔。主機頁面上這個 plugin 的狀態是 `RUNNING`，而〈成因：A1 加 Ubuntu 是官方列出的不支援組合〉已經看過 plugin 的狀態不能當成支援的證據，所以第一次只送唯讀的探測腳本，先查 `ocarun` 能不能 sudo，再決定要不要寫公鑰。

plugin 的狀態用這條指令列：

```bash
oci instance-agent plugin list --instanceagent-id <主機的 OCID> --compartment-id <compartment 的 OCID> \
  --query 'data[].{name:name,status:status}' --output table
```

這台列出 Compute Instance Run Command、Bastion、Custom Logs Monitoring、Compute Instance Monitoring、Cloud Guard Workload Protection 是 `RUNNING`，其餘是 `STOPPED` 或 `NOT_SUPPORTED`。

### 讓主機領得到指令：dynamic group 與 IAM 政策

主機向 Run Command 服務領取指令，用的是主機自己的身分，所以要先把主機放進一個 dynamic group，再寫政策允許這個群組領取與回報指令：

```bash
oci iam dynamic-group create --compartment-id <tenancy 的 OCID> --name verify-a1-runcommand \
  --description "<用途說明>" --matching-rule "ALL {instance.id = '<主機的 OCID>'}"

oci iam policy create --compartment-id <compartment 的 OCID> --name verify-a1-runcommand --description "<用途說明>" \
  --statements '["Allow dynamic-group verify-a1-runcommand to use instance-agent-command-execution-family in compartment blog-verify"]'
```

- **dynamic group**：依比對規則把資源本身當成 IAM 主體的群組。它建在 tenancy 層（`--compartment-id` 填 tenancy 的 OCID）；這個帳號只有 Default 這一個 identity domain（Oracle Cloud 存放使用者、群組與 dynamic group 的身分網域，`oci iam domain list --compartment-id <tenancy 的 OCID>` 列得出來），`oci iam dynamic-group create` 直接建在它底下；有多個 identity domain 的帳號，dynamic group 建在哪一個 domain 要另外確認，這次沒有實跑。`--matching-rule` 寫成 `instance.id = '<主機的 OCID>'`，群組裡只有這一台；改寫成 `instance.compartment.id = '<compartment 的 OCID>'` 會納入整個 compartment 的主機，之後新建的主機也自動有領取指令的身分（這時政策要加下一項說的 `where` 條件）。
- **政策**：建在 `blog-verify` 這個 compartment，`instance-agent-command-execution-family` 是領取與回報指令的權限，對象只有這個 dynamic group。官方〈Required IAM Policy for Working with Instances〉的範例在句尾多了 `where request.instance.id=target.instance.id`，限制每台主機只領取送給自己的指令；這次群組裡只有一台主機，加不加結果相同，比對規則改成整個 compartment 時要加上，否則群組裡的每一台主機都領得到送給其他主機的指令。政策裡的 `blog-verify` 與 `verify-a1-runcommand` 換成自己的 compartment 與群組名稱。
- **送指令的人**：這次用 tenancy 的管理員帳號送，沒有另外寫送指令的政策；一般使用者要送指令，另外需要送指令的權限政策，Run Command 說明頁指向官方〈Required IAM Policy for Working with Instances〉，這次沒有實跑。

沒有這組政策時，官方的疑難排解寫明 plugin 的日誌（`/var/log/oracle-cloud-agent/plugins/runcommand/runcommand.log`）會出現 `NotAuthorizedOrNotFound` 的 404，plugin 領不到指令。官方寫的等待時間依建立的先後而定：先建 dynamic group、再建主機時，主機一建好就開始領取；主機建好之後才加進 dynamic group 時，最多要 30 分鐘。這次屬於後一種，政策在 13:03:06（台北時間）建好，13:03:26 送出指令，13:10:27 執行完，從送出到執行完約 7 分鐘。

### 送出唯讀的探測腳本

探測腳本只讀狀態，不改主機上的任何東西：

```bash
#!/bin/bash
# 第一次 Run Command：只讀，確認 ocarun 的身分與能不能 sudo
id
. /etc/os-release && echo "$PRETTY_NAME"
if sudo -n true 2>/dev/null; then echo "SUDO=yes"; else echo "SUDO=no"; fi
ls -l /etc/sudoers.d/ 2>&1
```

`sudo -n` 在需要輸入密碼時直接失敗、不等待輸入，Run Command 不支援會要求輸入的腳本。腳本以文字的形式放進指令內容的 JSON，再送出：

```bash
python3 -c 'import json;print(json.dumps({"source":{"sourceType":"TEXT","text":open("runcmd-probe.sh").read()},"output":{"outputType":"TEXT"}}))' > probe-content.json

oci instance-agent command create --compartment-id <compartment 的 OCID> --display-name verify-probe \
  --timeout-in-seconds 600 --target '{"instanceId":"<主機的 OCID>"}' --content file://probe-content.json
```

- `runcmd-probe.sh` 是上面那支腳本存成的檔名。用 `json.dumps` 產生 JSON，腳本裡的換行與引號會自動跳脫；以文字送出的腳本上限 4 KB。
- `"outputType":"TEXT"`：輸出以文字保存在指令的執行紀錄裡，只保留最後 1 KB；要完整的輸出改存到 Object Storage。
- `--timeout-in-seconds 600`：腳本執行的逾時。這個選項的名稱是 `--timeout-in-seconds`，寫成 API 欄位名稱的 `--execution-time-out-in-seconds` 時，CLI 回 `No such option`。

### 讀結果：ocarun 沒有 sudo

送出之後指令先停在 `ACCEPTED`，plugin 領取並執行完才改變狀態。狀態與輸出各用一條指令讀：

```bash
oci instance-agent command-execution get --command-id <指令的 OCID> --instance-id <主機的 OCID> \
  --query 'data."lifecycle-state"' --raw-output
oci instance-agent command-execution get --command-id <指令的 OCID> --instance-id <主機的 OCID> \
  --query 'data.content.text' --raw-output
```

`<指令的 OCID>` 是 `command create` 輸出裡的 `id`。這次每 30 秒查一次，前 405 秒都是 `ACCEPTED`，之後是 `FAILED`，輸出是：

```text
uid=999(ocarun) gid=584788(snap_daemon) groups=584788(snap_daemon),4(adm)
Ubuntu 24.04.5 LTS
SUDO=no
ls: cannot open directory '/etc/sudoers.d/': Permission denied
```

- **`FAILED` 的意思**：執行紀錄的 `exit-code` 是 2，來自腳本最後一行 `ls` 讀不了 `/etc/sudoers.d/`；同一筆紀錄的 `delivery-state` 是 `ACKED`，指令有送達並執行完。所以這裡的 `FAILED` 是腳本的結束碼，不是 plugin 沒有執行。
- **plugin 在 A1 Ubuntu 上執行得了腳本**：Ubuntu 不在支援映像清單上，而腳本確實執行了。Ubuntu 上的 Oracle Cloud Agent 是 snap 套件，`ocarun` 的群組是 `snap_daemon` 與 `adm`（`adm` 讀得到 `/var/log` 底下的系統日誌）。
- **`SUDO=no`**：`ocarun` 沒有 sudo，寫不了 `/home/ubuntu/.ssh/authorized_keys`，也加不了 sudoers 檔。要讓 `ocarun` 有 sudo，得先登入主機加 sudoers 檔，而這台正是登不進去才要用 Run Command，所以 Run Command 在這台主機上寫不了公鑰。建立時用初始化腳本放 sudoers 檔的做法，見〈Management：Oracle Cloud Agent 與其他進階選項〉。

### 用 Run Command 讀代理程式的版本與日誌

`ocarun` 寫不了其他使用者的檔案，讀得到的範圍則比較寬：它屬於 `adm` 群組，`/var/log` 底下開放給這個群組或所有人讀的檔案都讀得到。所以 Run Command 雖然救不回這台主機，仍然能在不登入的情況下查 managed SSH session 失敗時代理程式的狀態。2026-10-25 下午再送了兩次唯讀的腳本，送法同〈送出唯讀的探測腳本〉，只換腳本內容；兩次的內容合起來是：

```bash
#!/bin/bash
# 只讀：代理程式的版本、日誌目錄、代理程式主日誌裡 Bastion plugin 的紀錄
snap list oracle-cloud-agent 2>&1
ls -l /var/log/oracle-cloud-agent/plugins/ 2>&1
ls /var/log/oracle-cloud-agent/plugins/bastions/ 2>&1
grep -ih bastion /var/log/oracle-cloud-agent/*.log 2>&1 | tail -n 20
```

第二次從送出到執行完約 2 分半鐘（06:19:43Z 到 06:22:10Z；主機已經在 dynamic group 裡，不再等第一次探測的 7 分鐘）。兩次讀到的是：

- **代理程式的版本**：`snap list` 印出 `oracle-cloud-agent 1.61.0-6`，Notes 欄是 `classic,held`。Known Issues 第二條的 1.11 版以下不成立，這台的逾時只剩 A1 加 Ubuntu 那一條成因。
- **Bastion plugin 的日誌讀不到**：plugin 的目錄叫 `bastions`（不是 `bastion`），裡面有 `bastions.log`，而目錄的權限是 `drwxr--r--`、擁有者與群組都是 `snap_daemon`；`ocarun` 的主要群組雖然是 `snap_daemon`，群組那一欄是 `r--`、沒有 `x`，列得出檔名、進不了目錄，讀不了裡面的檔案（其他使用者那一欄同樣是 `r--`，不在這個群組也是一樣）。`runcommand` 目錄的擁有者是 `ocarun`、群組 `adm`。
- **代理程式的主日誌讀得到**：`/var/log/oracle-cloud-agent/agent.log` 開放所有人讀。它每 10 分鐘對 Bastion plugin 做一次健康檢查，紀錄是 `health check of plugin:[bastions], desiredState:[Enable], currentState:[running], status:[running] version:[1.61.0-6] err:[<nil>]`。讀到的是 05:51 與 06:01（UTC）這兩筆，都是 running、沒有錯誤；managed SSH session 逾時的那幾個時段（台北時間 11:04 到 12:07）的紀錄不在讀到的範圍裡。所以這次能確定的是：工作階段已經逾時三次之後，代理程式的健康檢查仍然回報 running，跟主控台上的 `RUNNING` 一樣看不出這個組合不支援。

以文字保存的輸出只留最後 1 KB，`grep` 的結果被截斷；要讀完整的日誌，輸出改存到 Object Storage（`"outputType"` 改成 Object Storage 的那一種，這次沒有實跑）。

## 這台主機剩下的登入入口

Run Command 寫不了公鑰之後，這台主機剩下的入口與各自的條件：

- **替換開機磁碟**：官方〈Replacing a Boot Volume〉限定只能換成同一個 Linux 發行版，換不成 Oracle Linux。換成新的 Ubuntu 開機磁碟時，cloud-init 讀的仍是建立時的中繼資料，而 `ssh_authorized_keys` 是空的，所以新磁碟上也沒有公鑰；這是從兩份說明推出的結果，這次沒有實跑。換成自己做的 Ubuntu aarch64 自訂映像時，公鑰或設了密碼的救援帳號可以直接做進映像，不靠 cloud-init 從中繼資料讀；這條路不重建主機、不放掉 A1 的容量，代價是要自己做映像、匯入，而〈Replacing a Boot Volume〉沒有寫自訂映像在 A1 上能不能用，這次沒有實跑。
- **把開機磁碟掛到另一台主機修改**：停止這台、卸下開機磁碟、掛到同一個可用區的另一台主機，在那裡把公鑰寫進 `authorized_keys` 再掛回來。另一台主機的架構不必相同：開機磁碟當成資料磁碟掛上去，讀寫的是上面的檔案系統，跟 CPU 架構無關（推論）。這個帳號在這一區能建的免費機型只有 A1，用 A1 要再搶一次容量；改用付費的 x86 機型（例如 `VM.Standard.E5.Flex` 的 1 OCPU）開幾十分鐘、改完就刪，付費 x86 機型通常不像 A1 那樣容量不足（推論，這一區沒有實測），費用依帳號狀態而定，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉。這次兩種都沒有實跑。
- **序列主控台**：主機裡沒有設密碼的帳號，登入提示這一步登不進去；官方從開機選單進維護模式重設金鑰的範例只寫了 Oracle Linux，同樣的做法在這台 Ubuntu 上能不能用，官方沒有寫，這次也沒有實跑。
- **重建主機**：重建時放自己的公鑰（不論映像），讓 port forwarding session 登得進去；要用 managed SSH session 時，另外選可用 plugin 裡有 Bastion 的 Oracle Linux 版本（10 確定沒有；9、8、7.9 查詢工具分不出，要建起來才確認）。只換成 Oracle Linux 而不放公鑰，選到沒有 Bastion plugin 的版本時一樣登不進去。重建要重新搶 A1 的容量；2026-10-25 照這一項重建了一台，見〈重建：Oracle Linux 映像加建立時放公鑰，經由 port forwarding session 登入〉。

截至 2026-10-25，這台主機還沒有登入過。登入是在另外重建的一台上完成的，見〈重建：Oracle Linux 映像加建立時放公鑰，經由 port forwarding session 登入〉。

## 重建：Oracle Linux 映像加建立時放公鑰，經由 port forwarding session 登入

2026-10-25 晚上另外建了一台 A1 主機 `verify-a1-ol`，Ubuntu 那台 `verify-a1` 留著不動。Free Tier 與試用中的 tenancy，Always Free 的 A1 額度合計 2 OCPU、12 GB（官方〈Always Free Resources〉；付費 tenancy 的免費量比這個大，見 [Oracle Cloud 的帳號結構與 home region：tenancy、Always Free 的範圍與主控台登入欄位](/infra/cloud-providers/oracle-cloud/account-and-home-region/)〈Always Free 的額度與它綁在 home region 上的範圍〉），兩台各 1 OCPU、6 GB 剛好用滿；要再建一台 A1 而不超出額度，得先刪掉其中一台（同一天稍晚終止了 `verify-a1`，見〈刪除這組資源的順序〉）。超出時的結果依帳號狀態而定（試用中照樣建得起來，試用結束那一刻合計超額的 A1 會全部停用），見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈Always Free 的額度與它綁在 home region 上的範圍〉。`verify-a1-ol` 改了兩個建立時才能決定的設定：映像檔換成 Oracle Linux，避開〈Known Issues for Bastion〉列為不支援 managed SSH session 的 A1 加非 Oracle Linux；建立時放自己的公鑰，讓 port forwarding session 這條不經過 Bastion plugin 的路徑也登得進去。其餘的設定（compartment、private subnet、不配公開 IP、只允許中繼資料第二版、Bastion plugin 開啟）跟 `verify-a1` 相同。這一節的指令跟〈建立之後〉那一節一樣，先在 shell 裡 `export OCI_CLI_AUTH=security_token`。

### 建立之前查映像檔版本與它可用的 plugin

managed SSH session 要主機上有 Bastion plugin，而哪些 plugin 可用是依作業系統與版本決定的。官方〈Managing Plugins with Oracle Cloud Agent〉寫明可以在建立之前用 ListInstanceagentAvailablePlugins 查，對應的 CLI 是 `available-plugins get`：

```bash
# 依作業系統名稱與版本，列出代理程式在這種映像上可用的 plugin
oci instance-agent available-plugins get -c <compartment 的 OCID> \
  --os-name "Oracle Linux" --os-version <作業系統版本> --all --query 'data[].name'
```

- `--os-name`、`--os-version`：照抄 `oci compute image list` 輸出的 `operating-system` 與 `operating-system-version` 欄。這一欄是大版本：映像名稱是 `Oracle-Linux-10.2-aarch64-…` 的那一個，這一欄是 `10`；相容 A1 的 Oracle Linux 映像在這一欄只有 `10`、`9`、`8`、`7.9` 四種值。
- 先建一份對照：填一個不存在的版本（例如 `99`）查一次，記下回傳的清單。這支工具查不到對應時不報錯，回傳不分版本的全部 plugin（官方 CLI 參考寫明；實測填不存在的版本、或不存在的作業系統名稱，回傳的都是同一份 15 項的清單，裡面有 `Bastion`）。
- 讀法：查到的清單跟對照不同，才算查到這個版本的資料，這時清單裡有 `Bastion` 才建得了 managed SSH session；跟對照相同時，分不出是這個版本提供全部 plugin，還是工具沒有它的資料。
- 2026-10-25 的結果：Oracle Linux `10`（填 `10.2` 也一樣）回傳 8 項、沒有 `Bastion`，跟對照不同，確定沒有；Ubuntu `24.04` 回傳 12 項、有 `Bastion`，跟對照不同，確定有，但它在 A1 上受〈Known Issues for Bastion〉第一條限制；Oracle Linux `9`、`8`、`7.9` 與 Ubuntu `26.04` 回傳的清單跟對照完全相同，這支工具分不出它們有沒有 `Bastion`。要確認 Oracle Linux 9，剩下的做法是建一台再用 `plugin list` 看，或找官方逐版本列出 plugin 的文件（這次沒有找到）。

`verify-a1-ol` 建立時沒有做這一步，選的是建立時間最新的 Oracle Linux 10.2，結果見〈結果：這台 Oracle Linux 10.2 主機上沒有 Bastion plugin〉。

### 建主機：Oracle Linux 映像加 --ssh-authorized-keys-file

建立的指令跟〈等效的 CLI 指令〉那一條相同，改了映像檔、公鑰與名稱三處；`--no-retry` 是重送腳本裡的寫法（理由見〈重送建立請求〉），單跑一次時可以拿掉。容量不足時，把同樣的三處改進重送腳本裡的 launch 指令：

```bash
# 查相容 A1 機型、指定大版本的 Oracle Linux 映像，取這個版本最新的建置
oci compute image list -c <tenancy 的 OCID> --operating-system "Oracle Linux" --operating-system-version <大版本> \
  --shape VM.Standard.A1.Flex --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output

# 建主機：換掉 --image-id 與 --display-name，加上 --ssh-authorized-keys-file
oci --no-retry compute instance launch -c <compartment 的 OCID> --availability-domain <可用區名稱> \
  --display-name verify-a1-ol --shape VM.Standard.A1.Flex --shape-config '{"ocpus":1,"memoryInGBs":6}' \
  --image-id <上一條印出的映像 OCID> --subnet-id <private subnet 的 OCID> --assign-public-ip false \
  --ssh-authorized-keys-file <登入主機用的公鑰檔> \
  --agent-config '{"pluginsConfig":[{"name":"Bastion","desiredState":"ENABLED"}]}' \
  --is-pv-encryption-in-transit-enabled true \
  --instance-options '{"areLegacyImdsEndpointsDisabled":true}'
```

- `-c <tenancy 的 OCID>`：理由同〈等效的 CLI 指令〉的 `--image-id` 那一項；這次填實驗用的 compartment 也列得出同樣的平台映像。
- `--operating-system-version <大版本>`：決定取哪一個大版本，例如 `9`。不給時，`--sort-by TIMECREATED` 取到的是所有版本裡建立時間最新的那一個建置，這次取到 `Oracle-Linux-10.2-aarch64-2026.10.16-0`，也就是沒有 Bastion plugin 的版本。要用 managed SSH session，填〈建立之前查映像檔版本與它可用的 plugin〉確定有 `Bastion` 的版本；Oracle Linux 這次沒有一個版本查得到確定有，`9`、`8`、`7.9` 的查詢結果一樣，要建起來用 `plugin list` 才知道。這篇的 Backlog 選 `9` 去驗，理由是它在沒有被確定排除的版本裡最新，不是因為查詢結果比 `8` 好。
- `--ssh-authorized-keys-file`：公鑰檔的路徑，內容寫進主機的中繼資料 `ssh_authorized_keys`，開機時由 cloud-init 寫進預設使用者 `opc` 的 `authorized_keys`。這一項建立之後不能改（〈建立之前的檢查〉），所以要在這裡放。這次用自己另產的一組金鑰，跟 Bastion 工作階段用的那一組分開。用同一組也連得上，指令還少一把 `-i`；工作階段的私鑰外洩時，拿到的人還要一個有 IAM 權限的帳號替他建工作階段、來源 IP 也要在 Bastion 的允許清單裡，所以分開換到的主要是另一個方向：登入主機的私鑰外洩時，主機那一把要換（建立時放的這一把要另外改主機上的 `authorized_keys`），工作階段那一把不受影響（推論，這次沒有實跑）。

這次第一次送出就建成，沒有遇到容量不足：台北時間 19:06:13 送出，19:07 查詢時已經是 `RUNNING`。容量是否不足依區域與時段而變，`verify-a1` 在同一區重送到第 16 次才建成（〈重送建立請求〉），所以重送腳本仍然要準備好。

### 結果：這台 Oracle Linux 10.2 主機上沒有 Bastion plugin

主機開機約 30 分鐘後，`oci instance-agent plugin list --instanceagent-id <主機的 OCID> -c <compartment 的 OCID>` 列出的 plugin 裡沒有 Bastion：Compute Instance Run Command、Compute Instance Monitoring、Custom Logs Monitoring 是 `RUNNING`，其餘是 `STOPPED` 或 `NOT_SUPPORTED`，Bastion 這一項整個不在清單上。主機的 `agent-config` 仍然寫著 Bastion 是 `ENABLED`，同一時間查 `verify-a1` 的 Bastion plugin 是 `RUNNING`。登入之後在主機上查，代理程式是 `oracle-cloud-agent-1.64.0-16.el10.aarch64`，`/var/log/oracle-cloud-agent/plugins/` 底下沒有 `bastions`（`verify-a1` 上 plugin 目錄的名字）也沒有 `bastion`，`grep -i bastion` 代理程式的日誌也沒有任何一行。plugin 清單、plugin 目錄與日誌這三處都沒有 Bastion，跟〈建立之前查映像檔版本與它可用的 plugin〉查到的結果一致：Oracle Linux 10 可用的 plugin 清單裡沒有 Bastion，所以 managed SSH session 在這台建不起來。〈Known Issues for Bastion〉只寫 Arm 主機要跑 Oracle Linux，沒有寫版本，所以只讀 Known Issues 看不出這一點。

這台建立時放了公鑰，port forwarding session 這條路徑還在，所以不必重建。

### 建 port forwarding session 並經由本機的轉送登入

port forwarding session 只替一個私有 IP 的一個 port 開 TCP 轉送。官方〈Bastion Overview〉寫明它不需要目標主機上執行 Oracle Cloud Agent，〈Connecting to a Port Forwarding Session〉也寫明不符合 managed SSH session 條件的主機可以用它連。主機那一端的登入驗證是 sshd 與 `authorized_keys`。Bastion 另有一種 dynamic port forwarding（SOCKS5）工作階段，一個工作階段連得到 subnet 裡的任何主機，同樣不經過代理程式，代價是本機要走 SOCKS 代理、能連到的範圍也變寬（〈Bastion Overview〉，這次沒有實跑）；這次用的是只轉到一台主機的 port forwarding：

```bash
# 建一個轉到主機 22 port 的 port forwarding session
oci bastion session create-port-forwarding --bastion-id <Bastion 的 OCID> \
  --target-private-ip <主機的私有 IP> --target-port 22 \
  --ssh-public-key-file <這次工作階段用的公鑰> --session-ttl 3600 \
  --wait-for-state SUCCEEDED --wait-for-state FAILED --query 'data.resources[0].identifier' --raw-output

# 在本機開轉送：本機的 2222 port 經由 Bastion 轉到主機的 22 port（這條指令會一直佔著終端機）
ssh -i <這次工作階段用的私鑰> -N -L 2222:<主機的私有 IP>:22 -p 22 \
  <上一條印出的工作階段 OCID>@host.bastion.<區域>.oci.oraclecloud.com

# 另開一個終端機，經由本機的 2222 port 登入主機
ssh -i <登入主機用的私鑰> -p 2222 opc@localhost
```

- `--target-private-ip`、`--target-port 22`：轉送的終點。port forwarding session 不必指定主機的 OCID，也不經過主機上的代理程式。
- `--session-ttl 3600`：工作階段的時效（秒），上限是 Bastion 的 `--max-session-ttl`（`oci bastion bastion get --bastion-id <Bastion 的 OCID>` 的 `max-session-ttl-in-seconds`）；到期之後轉送中斷，要再建一個工作階段。
- `--wait-for-state SUCCEEDED --wait-for-state FAILED`：等建立的 work request 到其中一個狀態再回傳；`--query` 取出的是新工作階段的 OCID。work request 是 `FAILED` 時這一條一樣會印出 OCID，所以用 `oci bastion session get --session-id <印出的 OCID> --query 'data."lifecycle-state"'` 確認工作階段是 `ACTIVE`，不是的話照〈結果：停在 CREATING 約 15 分鐘後轉成 DELETED〉讀 work request（記錄這次非同步建立的進度與錯誤的物件）的錯誤。這次 11 秒就是 `ACTIVE`，`verify-a1` 的 managed SSH session 是等 15 分鐘之後逾時。
- 本機轉送那一條的 `<這次工作階段用的私鑰>`：對應 `--ssh-public-key-file` 的那一把，用來通過 Bastion 的驗證；`-N` 只開轉送、不執行遠端指令；`-L 2222:<主機的私有 IP>:22` 把本機的 2222 port 轉到主機的 22 port，本機 port 可以選任何沒在用的號碼（官方原文是 any available local port），選 1024 以上的不需要 root；`-p 22` 是 Bastion 端的 SSH port，也是 ssh 的預設值，照官方的範例寫出來；使用者名稱是工作階段的 OCID，`<區域>` 是 `ap-batam-1` 這種區域識別碼。
- 登入主機那一條的 `<登入主機用的私鑰>`：對應建立主機時 `--ssh-authorized-keys-file` 的那一把，用來通過主機上 sshd 的驗證。同一次登入用到兩把金鑰，各自通過一道驗證。
- 本機轉送那一條的完整寫法不必自己組：`oci bastion session get --session-id <工作階段的 OCID> --query 'data."ssh-metadata".command' --raw-output` 印出同一條指令，主機名稱、使用者名稱與私有 IP 已經填好，只留 `<privateKey>` 與 `<localPort>` 兩個位置要換（實測）。主控台的工作階段清單裡，那個工作階段的選單也有 Copy SSH command（〈Connecting to a Port Forwarding Session〉）。

**替代做法：用 `-J` 一條指令完成轉送與登入**。ssh 的 ProxyJump 經由 Bastion 直接連到主機，不必另開一個終端機、也不必挑本機 port。兩把私鑰要各自交代給 ssh，所以寫成一個設定檔，再用 `ssh -F <設定檔> <主機的別名>` 連：

```text
# Bastion 這一段：使用者名稱是工作階段的 OCID，用工作階段的私鑰
Host <Bastion 的別名>
  HostName host.bastion.<區域>.oci.oraclecloud.com
  User <工作階段的 OCID>
  IdentityFile <這次工作階段用的私鑰>
  IdentitiesOnly yes

# 主機這一段：經由上面那一段跳過去，用登入主機的私鑰
Host <主機的別名>
  HostName <主機的私有 IP>
  User opc
  IdentityFile <登入主機用的私鑰>
  IdentitiesOnly yes
  ProxyJump <Bastion 的別名>
```

- `IdentitiesOnly yes`：只用 `IdentityFile` 指定的那一把，不把 ssh-agent 裡的其他金鑰一把把試過去；試的次數太多時伺服器會先斷線。
- 2026-10-25 用同一個 port forwarding session 實跑，登入成功（`opc@verify-a1-ol`）。這條路的終點跟 `-L` 一樣是工作階段指定的私有 IP 與 port，所以不必另建工作階段；主機金鑰記在 known_hosts 的私有 IP 底下，而 `-L` 的寫法記在 `[localhost]:2222` 底下，之後用同一個本機 port 轉到另一台主機時，ssh 會報 `REMOTE HOST IDENTIFICATION HAS CHANGED`。

第一次跑本機轉送那一條時，ssh 先要求確認的是 Bastion 自己（`host.bastion.<區域>.oci.oraclecloud.com`）的主機金鑰，這一把跟要登入的主機無關，官方文件沒有列出它的指紋。接著第一次連 `localhost:2222` 時，ssh 要求確認的才是主機的金鑰（機制與 known_hosts 見 [SSH Host Key 與 known_hosts（主機金鑰）](/infra/knowledge-cards/ssh-host-key/)）。這台主機的金鑰在開機時由 cloud-init 產生，指紋印在序列主控台輸出裡：用〈結果：停在 CREATING 約 15 分鐘後轉成 DELETED〉那兩條 `console-history` 指令讀出輸出，找 `BEGIN SSH HOST KEY FINGERPRINTS` 那一段的 ED25519 指紋，跟 ssh 顯示的指紋相同才接受。這次是先接受、登入之後才讀序列主控台輸出比對，兩邊的 ED25519 指紋完全相同；照上面的順序先比對再接受，才擋得住連到別台主機的情形。這台的 Run Command plugin 是 `RUNNING`，所以另一個取得指紋的方式是用 Run Command 送 `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`，主機金鑰的公鑰檔所有人都讀得到，`ocarun` 沒有 sudo 也讀得了；要先有〈讓主機領得到指令：dynamic group 與 IAM 政策〉那一組設定（推論，這次沒有實跑）。

台北時間 19:37:55 登入成功：`whoami` 印出 `opc`，`/etc/os-release` 是 Oracle Linux Server 10.2，`uname -m` 是 `aarch64`，`sudo -n true` 成功（`opc` 有免密碼的 sudo）。從送出建立到登入約 32 分鐘，大部分時間花在等 Bastion plugin，而它最後沒有出現。序列主控台輸出裡，cloud-init 在開機約 38 秒時印出 `opc` 的 `authorized_keys` 並完成（送出建立之後約 73 秒），所以直接走 port forwarding 的話，主機 `RUNNING` 之後一兩分鐘就可以連，不必等 plugin。建立時放了公鑰的主機，port forwarding 本身就是完整的登入路徑；managed SSH session 多給的是登入的公鑰只在工作階段期間放進主機、主機上不留常駐的金鑰，這台已經放了常駐的公鑰，這一點就沒有了。

- **沒做時**（建立時沒放公鑰）：主機的 `authorized_keys` 是空的，而這台的 managed SSH session 又建不起來，結果跟 `verify-a1` 相同：兩種工作階段都登不進去，剩下的入口見〈這台主機剩下的登入入口〉。
- **替代做法**：
  - 映像檔選 Ubuntu 加建立時放公鑰：port forwarding 同樣登得進去，managed SSH session 仍然受〈Known Issues for Bastion〉第一條限制（照 Known Issues 推出，這次沒有實跑）。
  - 映像檔選 Oracle Linux 9 加建立時放公鑰：`available-plugins get` 對 9 的回應跟查不到時相同，有沒有 Bastion 要建起來才知道；有的話 managed SSH session 與 port forwarding 兩種工作階段都可用，沒有的話跟這次一樣靠 port forwarding（推論，這次沒有實跑）。有 Bastion 時換到的是 managed SSH session 這一條不依賴常駐公鑰的路徑，付出的是用比較舊的大版本。日常登入想讓主機上不留常駐金鑰、只在工作階段期間放臨時公鑰時，才值得為此選 9；只要登得進去，10.2 加公鑰加 port forwarding 已經夠用。
  - 選有 Bastion plugin 的版本、不放公鑰、只靠 managed SSH session：plugin 一旦沒有運作（像 `verify-a1` 那樣狀態是 `RUNNING` 卻建不起工作階段），就沒有任何 SSH 的入口。建立時放公鑰，換到的是一條不依賴 plugin 的路徑。兩種工作階段最後都經過主機上的 sshd，所以 sshd 本身壞掉時兩種都連不上（從兩種工作階段的機制推論）；那時剩下序列主控台與重建，序列主控台在 Oracle Linux 上有官方從開機選單進維護模式的範例（〈這台主機剩下的登入入口〉），這次沒有實跑。

## 刪除這組資源的順序

實驗結束要清掉時，順序跟建立時相反，因為每一項資源被後面建的資源依賴著：

1. 終止兩台主機（`verify-a1` 與 `verify-a1-ol`），在終止對話框勾選「Permanently delete the attached boot volume」，開機磁碟才會一起刪掉。CLI 是 `oci compute instance terminate --instance-id <主機的 OCID> --preserve-boot-volume false --force`：`--preserve-boot-volume false` 對應那個勾選，`--force` 跳過確認提示。2026-10-25 用這一條終止了 `verify-a1`，約 67 秒後主機與它的開機磁碟都是 `TERMINATED`；用 `oci bv boot-volume list -c <compartment 的 OCID> --availability-domain <可用區名稱>` 確認開機磁碟的狀態。本機的 port forwarding 轉送用 Ctrl-C 結束，工作階段到了 `--session-ttl` 自己失效。
2. 刪除 Run Command 用的政策與 dynamic group（`oci iam policy delete --policy-id <政策的 OCID>`、`oci iam dynamic-group delete --dynamic-group-id <dynamic group 的 OCID>`）。政策建在 compartment 上，compartment 刪除之前要先刪；dynamic group 在 tenancy 層，不會隨 compartment 刪除，不刪的話它的比對規則仍然指著已經終止的主機 OCID。2026-10-25 終止 `verify-a1` 之後照這個順序刪了兩者，兩條都加 `--force` 跳過確認提示；刪完之後再 `oci iam policy get` 與 `oci iam dynamic-group get`，兩者都回 `404 NotAuthorizedOrNotFound`，代表已經不存在。
3. VCN 裡另外建了 NAT gateway 與 NSG 時，先刪它們：NSG 要先從網卡拿掉才刪得掉，NAT gateway 要先從路由表拿掉那一條路由，順序與指令見 [Oracle Cloud 私有子網路 Ubuntu 主機的實測紀錄：套件來源的出站（NAT gateway、路由與 NSG）、序列主控台的連線，以及被回收之後的重建](/infra/cloud-providers/oracle-cloud/hands-on/private-ubuntu-egress-console-rebuild/)〈刪除這組資源的順序〉。
4. 刪除 Bastion（`oci bastion bastion delete --bastion-id <Bastion 的 OCID>`）。Bastion 的私有端點在目標 subnet 裡，Bastion 還在時 subnet 刪不掉；它的工作階段隨 Bastion 一起失效。
5. 刪除 subnet。subnet 裡還有主機或網卡時刪不掉。
6. 刪除 subnet 用過的路由表與 security list。
7. 刪除 service gateway。
8. 刪除 VCN。
9. 刪除 compartment。官方〈Deleting a Compartment〉寫明 compartment 要先清空所有資源（包括掛在它上面的權限政策）才能刪除，刪除是非同步的工作，狀態會先變成 Deleting。

這個順序除了終止 `verify-a1` 與刪除政策和 dynamic group 這兩步，還沒有實際跑過（截至 2026-10-25 `verify-a1-ol` 與網路都還在），各項刪不掉時，看錯誤訊息指出的那一項依賴、先刪它。

要讓這組資源可以重建、清掉也不心疼，改用 IaC 描述它們，見 [IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)；已經用主控台或 CLI 建好的資源要收進 IaC，做法見 [Unmanaged Resource 批次 Import 工作流](/infra/takeover/partial-iac-bulk-import/)。
