---
title: "網路：subnet、私有 IP、公開 IP 與防火牆規則"
date: 2026-10-24
description: "雲端主機建立頁網路區塊的選項：主機放進哪個虛擬網路與 subnet、私有 IP 與公開 IP 各自的用途與生命週期、防火牆規則掛在 subnet、網卡與作業系統哪一個位置以及各家怎麼合併，以及主控台新建的網路預設對外開放了什麼"
weight: 3
tags: ["infra", "cloud-providers", "vm", "network", "security"]
---

建立頁的網路區塊決定一台主機在虛擬網路裡的位置、網際網路上的人連不連得到它，以及哪些 port 對外開放。範圍是把一台主機放進網路的那些欄位；虛擬網路本身怎麼切 subnet、路由與 NAT 怎麼設計見 [VPC、subnet 與 security group](/infra/03-network-foundation/vpc-subnet-security-group/)，管理員要怎麼登入沒有公開 IP 的主機見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## 虛擬網路與 subnet：主機放在哪一段網路

每台主機的網卡都接在一個虛擬網路裡的某一個 [Subnet](/infra/knowledge-cards/subnet/) 上；虛擬網路在 Oracle Cloud 叫 VCN，在 Google Cloud 與 AWS 叫 VPC（見 [VPC](/infra/knowledge-cards/vpc/) 卡）。建立主機的人在建立頁要決定的是接在哪一個 subnet。在 Oracle Cloud 與 AWS 上，選定的 subnet 的路由表決定網際網路來的連線能否送到這台主機、主機對外連線時走哪一條路；網卡能否拿到公開 IP，Oracle Cloud 由 subnet 的屬性決定，AWS 是另一個獨立的設定（見下文 AWS 的說明）。Google Cloud 的 subnet 沒有公開與私有之分，主機能否從網際網路直接連到、對外連線走哪一條路，由主機是否有外部 IP 與防火牆規則決定。

概念上，subnet 分成公開與私有兩種：

- **公開 subnet**：[路由表（route table）](/infra/knowledge-cards/route-table/)有一條通往網際網路閘道（internet gateway）的路由，裡面有公開 IP 的主機可以被網際網路直接連到開放的 port，也經由這個閘道對外連線。
- **私有 subnet**：沒有那一條路由，外面連不進來。主機要對外連線（下載套件更新）時經由 [NAT](/infra/knowledge-cards/nat/) 閘道（NAT gateway）出去；要連業者自己的服務（物件儲存、監控、管理通道服務）時，經由業者提供的私有連線，Oracle Cloud 叫服務閘道（service gateway）、AWS 叫 VPC endpoint、Google Cloud 叫 Private Google Access。

公開與私有這個區分記在哪裡，Oracle Cloud 與 AWS 的做法不同。Oracle Cloud 記在 subnet 自己的屬性上：建立 subnet 時有一個「禁止公開 IP」的屬性，打開的就是私有 subnet，裡面的網卡指派不了公開 IP。AWS 上公開 IP 與路由是兩個獨立的設定，官方〈Subnets for your VPC〉分別寫了兩者：

- **網卡是否有公開 IP**：由 subnet 的「自動指派公開 IPv4」屬性決定，建立主機時可以對那一台主機覆寫這個屬性。
- **網際網路來的連線能否送到主機**：由 subnet 的路由表決定。官方的定義是，有直接通往 internet gateway 路由的是公開 subnet，沒有的是私有 subnet。

所以 AWS 私有 subnet 裡的主機可以有公開 IP，而那個公開 IP 收不到網際網路來的連線。Google Cloud 沒有公開與私有 subnet 之分，任何 subnet 裡的主機都可以有外部 IP。另外，AWS 的一個 subnet 只在一個可用區裡，兩台主機要分到不同可用區時，要放進兩個不同可用區的 subnet；Oracle Cloud 與 Google Cloud 的 subnet 可以跨同一區域內的可用區，見 [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/)。

在 Oracle Cloud 上，公開 subnet 裡沒有公開 IP 的主機完全沒有出站路徑：官方〈Internet Gateway〉的說明是，要經由 internet gateway 連網際網路的資源必須在公開 subnet 裡、而且有公開 IP，只有私有 IP 的資源要改走 NAT 閘道。所以在 Oracle Cloud 上，放進公開 subnet 的主機要同時給公開 IP 才有出站路徑；不給公開 IP 的主機放私有 subnet，出站走 NAT 閘道。

替單一台實驗機選 subnet 與公開 IP 時，要先確定三項需求：主機上是否有服務要讓網際網路的人連、管理員從哪裡登入、主機自己是否要對外連線（下載套件更新）。下面各條依對外服務與登入方式的組合寫出放法，出站路徑寫在各條裡：

- **沒有對外的服務、管理員經由業者的管理通道登入**：放私有 subnet、不給公開 IP，外面連不進來。Oracle Cloud 的 Bastion 是業者託管的服務、不是自己架的 [跳板機（bastion host）](/infra/knowledge-cards/bastion-host/)，經由它登入的主機不需要公開 IP；它的網路條件、費用與配額見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。主機要下載套件更新時，路由表要另外有一條經過 NAT 閘道的路由；AWS 的 NAT Gateway 與 Google Cloud 的 Cloud NAT 另外計費，費率見各家價格頁。
- **沒有對外的服務、管理員直接用 SSH 登入**：放公開 subnet、給公開 IP，設定最少，出站也經由網際網路閘道。代價是 SSH port 對網際網路可見，要把防火牆規則的來源收緊成自己的 IP，自己的 IP 會變時每次都要改規則。三家業者預先準備的網路規則（Oracle Cloud 主控台新建 VCN 時的 Default Security List、Google Cloud `default` 網路的 `default-allow-ssh`、AWS 啟動精靈新建的 security group）預設都放行 22 port；Google Cloud 那一條的來源是整個網際網路，Oracle Cloud 那一份在 2026-10-24 實測時也是，見〈各家預設網路規則對 SSH 的開放〉。
- **有一個服務要讓網際網路的人直接連（例如自架 VPN）**：放公開 subnet、給公開 IP，防火牆規則只放行那一個服務的 port。管理員的 SSH 不必跟著對外：來源收緊成自己的 IP，或先連上 VPN、再經由主機的私有 IP 登入。
- **網頁這類 HTTP 服務**：主機放私有 subnet，由放在公開 subnet 的負載平衡器承接網際網路來的連線。Oracle Cloud 的 Always Free 含一個 10 Mbps 的負載平衡器；AWS 與 Google Cloud 的負載平衡器另外計費，計費項目見各家價格頁。

建立頁替主機準備網路的方式，各家預先準備的東西不一樣。Oracle Cloud 的建立頁提供「選既有的 VCN」與「建一個新的 VCN」兩條路，選「建新的」時，主控台會順手建一個 VCN、一個 subnet 與一份預設的防火牆規則；Google Cloud 的專案預先就有一個 `default` 網路，建立頁預設把主機放進去；AWS 的啟動精靈把主機放進帳號的預設 VPC，並順手建一個新的 security group。要把主機放進自己設計過的網路時，先在網路的頁面建好虛擬網路與 subnet，再回到建立頁選那個 subnet。Oracle Cloud 的網路下拉選單還受 compartment（tenancy 底下分組資源的容器）篩選，只列出選定的 compartment 裡的 VCN；篩選的規則見 [Oracle Cloud 主控台導覽](/infra/cloud-providers/oracle-cloud/console-navigation/) 的〈清單頁的 compartment 篩選器〉，實際卡住的情形見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/) 的 Networking 段。

## 私有 IP：主機在虛擬網路裡的位址

每張網卡一定有一個私有 IP，從 subnet 的位址範圍裡分配。建立頁的選項是自動分配（預設）或手動指定一個位址。單一台主機選自動分配；要讓其他設定寫死這台主機的位址時（例如另一台主機的設定檔、防火牆規則只放行這一個位址），才手動指定。

主機停止與重開時，私有 IP 都不會變，終止主機時業者才把它釋放。同一個虛擬網路裡的其他主機用這個位址連它。

Oracle Cloud 另有一個 DNS record 選項：勾選之後，網卡會在 VCN 的內部 DNS 裡得到一個名稱，同一個 VCN 裡的主機可以用名稱代替 IP 連它。這個選項要 VCN 與 subnet 都設了 DNS label（建立 VCN 與 subnet 時填的名稱片段）才能用，名稱只在 VCN 內部有效，網際網路上查不到。同一個 VCN 裡有其他主機要連這一台時勾選，設定檔寫名稱比寫 IP 好維護；只有一台主機時勾不勾都沒有差別。

## 公開 IP：網際網路上的入口

公開 IP 讓網際網路上的人能直接連到這台主機。在 Oracle Cloud 上，它只能指派給公開 subnet 裡的網卡；主機放在私有 subnet 時，建立頁上的公開 IP 選項是灰的。

Oracle Cloud 的公開 IP 分兩種，性質在建立後不能互換：

- **臨時（ephemeral）**：跟著主機的生命週期。主機停止時保留，終止時自動刪除。建立頁上勾選「自動指派公開 IPv4」拿到的是臨時公開 IP。DNS 記錄指向臨時 IP 時，主機終止、重建之後拿到的是另一個位址，DNS 記錄仍然指向那個已經刪除、不再屬於這個帳號的舊位址；DNS 查詢照常回應那個舊位址而不會報錯，連線只是到不了新主機。
- **保留（reserved）**：獨立的資源，主機終止之後仍然存在，可以再指派給另一台主機。要讓 DNS 記錄或外部白名單長期指向同一個位址時用保留公開 IP。

在 Oracle Cloud 上，公開 IP 可以在建立之後再加、也可以拿掉：公開 subnet 裡的網卡沒有公開 IP 時，可以另外建一個臨時公開 IP 指派上去。AWS 上建立時沒有自動指派的主機，之後要對外得另外掛一個 Elastic IP。

主機所在的 subnet 在建立之後能否更換，三家的官方說明不同。Oracle Cloud 與 AWS 的官方網卡說明都寫明主要網卡（建立主機時自動建的那一張）不能從主機拿掉，網卡的私有 IP 從它所在的 subnet 分配，兩家的文件都沒有寫主要網卡可以換到另一個 subnet；所以在這兩家，把 subnet 當成建立時就決定的選項，主機要不要對外在建立頁選 subnet 時就決定。

在 Oracle Cloud 上，放在私有 subnet 的主機之後要對外，可走的路是加一張接在公開 subnet 的次要網卡、改由放在公開 subnet 的負載平衡器承接，或重建主機。官方說明次要網卡可以接在同一個或另一個 VCN 的其他 subnet，條件是跟主機在同一個可用區。在 Oracle Cloud 上，放在公開 subnet 卻不給公開 IP 的主機沒有出站路徑（見〈虛擬網路與 subnet：主機放在哪一段網路〉）。

Google Cloud 的〈Migrating a VM between networks〉說明頁寫明，主機的網卡可以換到同一個 VPC 網路裡的另一個 subnet：主機要先停止，換完之後主機仍在原來的區域與可用區，網卡的 MAC 位址會改變，目標 subnet 的位址範圍與原本不同時，內部 IP 也會改變。

AWS 對每個公開 IPv4 位址按小時另外計費，見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)。

主機是否指派了公開 IP，決定它在網際網路上暴露的面積。管理用的 SSH port 經由公開 IP 對外開放之後，網際網路上的掃描程式會持續嘗試登入。

## 防火牆規則的位置與合併方式

一個封包要到得了主機上的程式，要通過兩道關：雲端業者那一側的防火牆規則，以及主機作業系統裡的防火牆，兩道都放行才到得了。

雲端業者那一側，Oracle Cloud 與 AWS 有兩個掛規則的位置，Google Cloud 只有一個：

| 規則的位置 | Oracle Cloud                  | AWS                                                      | 作用範圍                   |
| ---------- | ----------------------------- | -------------------------------------------------------- | -------------------------- |
| subnet     | Security list                 | Network ACL                                              | 這個 subnet 裡的每一張網卡 |
| 網卡       | Network security group（NSG） | [Security group](/infra/knowledge-cards/security-group/) | 加入這一組規則的那幾張網卡 |

兩個位置的規則同時存在時，Oracle Cloud 取兩邊的聯集，AWS 要兩邊都放行，Google Cloud 的 VPC 防火牆規則只有一個位置而不必合併：

- **Oracle Cloud 取聯集**：官方〈Security Rules〉的說明是，套用在一張網卡上的規則是 subnet 的 security list 與這張網卡加入的所有 NSG 的聯集。Security list 與 NSG 都只能寫放行的規則，沒有拒絕規則，所以任何一邊有一條規則放行，封包就通過雲端那一道關。以 22 port 為例：

  | Security list 對 22 port | NSG 對 22 port | 封包能不能通過雲端那一道關 |
  | ------------------------ | -------------- | -------------------------- |
  | 有放行規則               | 沒有規則       | 能                         |
  | 沒有規則                 | 有放行規則     | 能                         |
  | 沒有規則                 | 沒有規則       | 不能                       |

  任一邊有一條放行規則，封包就通過雲端那一道關，所以兩邊都沒有放行 22 port 的規則時，22 port 的連線才會被擋下。預設的 security list 放行 22 port 時，NSG 裡即使沒有 22 port 的規則，22 port 的連線照樣由 security list 放行通過。
- **AWS 兩個位置都要放行**：封包要先通過 subnet 的 Network ACL，再通過網卡的 security group。Network ACL 可以寫拒絕規則，官方建議把它當成第二道控制，用來擋掉特定的流量；security group 放行了，Network ACL 擋下來的封包仍然到不了。
- **Google Cloud 的 VPC 防火牆規則只有一個位置**：防火牆規則設在 VPC 上，再用 [網路標籤（network tag）](/infra/knowledge-cards/network-tag/) 或 [服務帳號（service account）](/infra/knowledge-cards/service-account/) 選出規則要套用的主機，沒有 subnet 這一層的規則。單一專案、沒有另外建過防火牆政策時只會遇到 VPC 防火牆規則；Google Cloud 另有掛在 VPC 網路上的 network firewall policy 與組織層的 hierarchical firewall policy，建了之後會跟 VPC 的防火牆規則依官方說明的評估順序一起評估，那時套用到一台主機的規則就不只 VPC 防火牆規則這一個來源。

Oracle Cloud 建立頁上能設定的只有 NSG：「Use network security groups to control traffic」這個選項把主機的網卡加入某幾個 NSG，只有選既有的 VCN 時才出現。Security list 要到 VCN 的頁面設。官方文件說明 NSG 讓 subnet 的切法與應用程式的安全需求分開管理：同一個 subnet 裡的資料庫主機與網頁主機可以開不同的 port，不必為了開不同的 port 拆成兩個 subnet。

作業系統的防火牆（`iptables`、`nftables`、`ufw`）由主機自己管，不在雲端的主控台上。雲端那一道關放行了某個 port、連線仍然被拒絕時，要進主機查作業系統這一道。Oracle Cloud 的平台映像出廠就帶著一組作業系統防火牆規則，其中有讓主機連到開機磁碟與區塊磁碟的 iSCSI 端點的必要規則，官方〈Images〉建議不要移除；官方〈Images〉那一頁另外寫明在 Ubuntu 映像上不要用 `ufw` 改規則，用它改可能讓主機開不了機。SSH 連不上時，先看症狀是連線逾時還是連線被拒：逾時代表封包沒有送到主機（雲端規則、路由或作業系統防火牆丟棄了封包），被拒代表封包到了主機而 22 port 沒有程式接受連線或防火牆明確回拒，分辨方法見 [Connection Refused vs. Timeout（連線被拒與逾時）](/linux/dotfile/knowledge-cards/connection-refused-vs-timeout/)。主機上跑 Docker 時，容器發佈的連接埠由 Docker 在作業系統防火牆之前轉給容器，`ufw` 與 `firewalld` 的一般規則管不到它；封包路徑與限制的寫法見 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/infra/03-network-foundation/origin-host-firewall/) 的〈Docker 發佈的連接埠：封包路徑與限制的寫法〉。

## 各家預設網路規則對 SSH 的開放

三家業者替使用者預先建好或順手建的網路，預設的規則都放行 22 port 的 SSH 流量。Google Cloud 那一條規則的來源是整個網際網路，Oracle Cloud 那一份的來源在 2026-10-24 實測時也是整個網際網路：

- **Oracle Cloud**：建立頁選「建一個新的 VCN」時，主控台一起建一份「Default Security List」。官方〈Security Lists〉描述的是這條規則的用途：放行來自「authorized source IP addresses」的 TCP 22，讓使用者建好新的 VCN 與公開 subnet 之後，不必自己寫規則就能用 SSH 連上新建的 Linux 主機；這段描述沒有寫來源欄位的預設值。2026-10-24 實測時，主控台建出來的這條規則來源是 `0.0.0.0/0`。兩者不衝突：官方寫的是規則的用途，實測讀到的是那一次建出來的預設值。官方沒有寫預設值，所以建好之後到 subnet 的 security list 看一次實際的來源。Subnet 沒有另外指定 security list 時套用的就是這一份，所以這條規則的來源是 `0.0.0.0/0` 時，在新建的公開 subnet 裡建一台有公開 IP 的主機，那台主機的 SSH port 一建好就對網際網路開放。這份規則的完整內容（實測值）見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/) 的 Networking 段。
- **Google Cloud**：專案建立時就有的 `default` 網路帶一條 `default-allow-ssh` 規則，放行 `0.0.0.0/0` 的 TCP 22，套用在這個網路裡的每一台主機。換掉這條規則的順序見 [GCP VM 的 SSH 與 RDP 管理通道](/infra/cloud-providers/gcp/gcp-iap-ssh-access/) 的〈切換到 IAP 的順序〉，逐步的指令見 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/)。
- **AWS**：EC2 啟動精靈順手建的 security group 預設放行進來的 SSH 流量（官方〈Prerequisites for EC2 Instance Connect〉的說明），放行的來源要在精靈的網路設定那一步確認並收緊。

收緊的做法是把來源改成管理員的 IP，或改用不需要對外開放 SSH 的管理通道（見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)）。

## 其他網路欄位：VNIC 名稱、IPv6 與 Launch options

- **網卡名稱（VNIC name）**：顯示用的名稱，不必唯一、之後可以改，不影響連線。留空時業者自動產生。
- **IPv6**：只有 VCN 與 subnet 都設了 IPv6 位址段時才能勾。只用 IPv4 連線的實驗機不需要。
- **Launch options（Oracle Cloud）**：網卡的虛擬化方式，只對虛擬機有效。預設值由映像檔決定，是那個映像檔支援的方式；改成映像檔不支援的方式時，主機可能開機後沒有網路，所以維持預設。

## 各家的欄位名稱：虛擬網路、網卡、防火牆規則與保留的公開 IP

| 概念          | Oracle Cloud           | Google Cloud                                                | AWS                              |
| ------------- | ---------------------- | ----------------------------------------------------------- | -------------------------------- |
| 虛擬網路      | VCN                    | VPC network                                                 | VPC                              |
| 網卡          | VNIC                   | Network interface                                           | ENI（Elastic Network Interface） |
| subnet 層規則 | Security list          | 無（規則設在 VPC 上）                                       | Network ACL                      |
| 網卡層規則    | Network security group | 無（Firewall rule 設在 VPC 上，以網路標籤或服務帳號選主機） | Security group                   |
| 兩層的合併    | 聯集                   | 只有一層                                                    | 兩層都要放行                     |
| 保留的公開 IP | Reserved public IP     | Static external IP address                                  | Elastic IP                       |

Subnet 的切法、路由表與 NAT 的設計見 [VPC、subnet 與 security group](/infra/03-network-foundation/vpc-subnet-security-group/)；網路通了之後，登入時用的金鑰與帳號見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/)。
