---
title: "網路：subnet、私有 IP、公開 IP 與防火牆規則"
date: 2026-10-24
description: "建立虛擬機時網路區塊的選項：主機放進哪個虛擬網路與 subnet、私有 IP 與公開 IP 各自的用途與生命週期、防火牆規則掛在 subnet、網卡與作業系統哪一個位置以及各家怎麼合併，以及主控台新建的網路預設對外開放了什麼"
weight: 3
tags: ["infra", "cloud-providers", "vm", "network", "security"]
---

建立頁的網路區塊決定一台主機在虛擬網路裡的位置、網際網路上的人連不連得到它，以及哪些 port 對外開放。範圍是把一台主機放進網路的那些欄位；虛擬網路本身怎麼切 subnet、路由與 NAT 怎麼設計見 [VPC、subnet 與 security group](/infra/03-network-foundation/vpc-subnet-security-group/)，管理員要怎麼登入沒有公開 IP 的主機見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## 虛擬網路與 subnet：主機放在哪一段網路

每台主機的網卡都接在一個虛擬網路裡的某一個 [Subnet](/infra/knowledge-cards/subnet/) 上；虛擬網路在 Oracle Cloud 叫 VCN，在 Google Cloud 與 AWS 叫 VPC（見 [VPC](/infra/knowledge-cards/vpc/) 卡）。建立頁要決定的是接在哪一個 subnet。在 Oracle Cloud 與 AWS 上，subnet 已經決定了這台主機能不能從網際網路直接連到、要對外連線時走哪一條路；Google Cloud 沒有這一層區分，由主機有沒有外部 IP 與防火牆規則決定。

概念上，subnet 分成公開與私有兩種：

- **公開 subnet**：路由表有一條通往網際網路閘道（internet gateway）的路由，裡面有公開 IP 的主機可以被網際網路直接連到開放的 port，也經由這個閘道對外連線。
- **私有 subnet**：沒有那一條路由，外面連不進來。主機要對外連線（下載套件更新）時經由 [NAT](/infra/knowledge-cards/nat/) 閘道（NAT gateway）出去；要連業者自己的服務（物件儲存、監控、管理通道服務）時，經由業者提供的私有連線，Oracle Cloud 叫服務閘道（service gateway）、AWS 叫 VPC endpoint、Google Cloud 叫 Private Google Access。

三家實作這個區分的方式不同。Oracle Cloud 的 subnet 建立時有一個「禁止公開 IP」的屬性，打開的就是私有 subnet，裡面的網卡指派不了公開 IP。AWS 的公開與私有只看路由表：私有 subnet 裡的主機在技術上還是能被指派公開 IP，但這個 subnet 的路由表沒有通往網際網路閘道的路由，所以那個公開 IP 收不到網際網路來的連線。Google Cloud 沒有公開與私有 subnet 之分，任何 subnet 裡的主機都可以有外部 IP。另外，AWS 的一個 subnet 只在一個可用區裡，兩台主機要分到不同可用區時，要放進兩個不同可用區的 subnet；Oracle Cloud 與 Google Cloud 的 subnet 可以跨同一區域內的可用區，見 [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/)。

在 Oracle Cloud 上，公開 subnet 裡沒有公開 IP 的主機完全沒有出站路徑：官方〈Internet Gateway〉的說明是，要經由 internet gateway 連網際網路的資源必須在公開 subnet 裡、而且有公開 IP，只有私有 IP 的資源要改走 NAT 閘道。所以「放公開 subnet」與「給公開 IP」在 Oracle Cloud 上是一起決定的。

單一台實驗機的放法，要回答兩件事：這台主機上有沒有服務要讓網際網路的人連，以及管理員要從哪裡登入。再加上主機自己要不要對外連線（下載套件更新），就決定了 subnet 與公開 IP：

- **沒有對外的服務、管理員經由業者的管理通道登入**：放私有 subnet、不給公開 IP，外面連不進來。Oracle Cloud 的 Bastion 是業者託管的服務，不是自己架的 [跳板機（bastion host）](/infra/knowledge-cards/bastion-host/)：它在 subnet 裡有一個私有端點，連線由那裡轉進主機，主機與 Bastion 都不需要公開 IP，Bastion 本身不另外收費。主機要下載套件更新時，路由表要另外有一條經過 NAT 閘道的路由；AWS 的 NAT Gateway 與 Google Cloud 的 Cloud NAT 另外計費，費率見各家價格頁。管理通道服務需要的其他條件見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。
- **沒有對外的服務、管理員直接用 SSH 登入**：放公開 subnet、給公開 IP，設定最少，出站也經由網際網路閘道。代價是 SSH port 對網際網路可見，要把防火牆規則的來源收緊成自己的 IP，自己的 IP 會變時每次都要改規則；業者預設網路的規則已經對整個網際網路開著 22 port，見〈各家預設網路規則對 SSH 的開放〉。
- **有一個服務要讓網際網路的人直接連（例如自架 VPN）**：放公開 subnet、給公開 IP，防火牆規則只放行那一個服務的 port。管理員的 SSH 不必跟著對外：來源收緊成自己的 IP，或先連上 VPN、再經由主機的私有 IP 登入。
- **網頁這類 HTTP 服務**：主機放私有 subnet，由放在公開 subnet 的負載平衡器承接網際網路來的連線。Oracle Cloud 的 Always Free 含一個 10 Mbps 的負載平衡器；AWS 與 Google Cloud 的負載平衡器另外計費，計費項目見各家價格頁。

建立頁上網路的選法也因業者而不同。Oracle Cloud 的建立頁提供「選既有的 VCN」與「建一個新的 VCN」兩條路，選「建新的」時，主控台會順手建一個 VCN、一個 subnet 與一份預設的防火牆規則；Google Cloud 的專案預先就有一個 `default` 網路，建立頁預設把主機放進去；AWS 的啟動精靈把主機放進帳號的預設 VPC，並順手建一個新的 security group。要把主機放進自己設計過的網路時，先在網路的頁面建好虛擬網路與 subnet，再回到建立頁選它。Oracle Cloud 的網路下拉選單還受 compartment（tenancy 底下分組資源的容器）篩選，只列出選定的 compartment 裡的 VCN；篩選的規則見 [Oracle Cloud 主控台導覽](/infra/cloud-providers/oracle-cloud/console-navigation/) 的〈清單頁的 compartment 篩選器〉，實際卡住的情形見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/) 的 Networking 段。

## 私有 IP：主機在虛擬網路裡的位址

每張網卡一定有一個私有 IP，從 subnet 的位址範圍裡分配。建立頁的選項是自動分配（預設）或手動指定一個位址。單一台主機選自動分配；要讓其他設定寫死這台主機的位址時（例如另一台主機的設定檔、防火牆規則只放行這一個位址），才手動指定。

主機停止與重開時，私有 IP 都不會變，終止主機時業者才把它釋放。同一個虛擬網路裡的其他主機用這個位址連它。

Oracle Cloud 另有一個 DNS record 選項：勾選之後，網卡會在 VCN 的內部 DNS 裡得到一個名稱，同一個 VCN 裡的主機可以用名稱代替 IP 連它。這個選項要 VCN 與 subnet 都設了 DNS label（建立 VCN 與 subnet 時填的名稱片段）才能用，名稱只在 VCN 內部有效，網際網路上查不到。同一個 VCN 裡有其他主機要連這一台時勾選，設定檔寫名稱比寫 IP 好維護；只有一台主機時勾不勾都沒有差別。

## 公開 IP：網際網路上的入口

公開 IP 讓網際網路上的人能直接連到這台主機。在 Oracle Cloud 上，它只能指派給公開 subnet 裡的網卡；主機放在私有 subnet 時，建立頁上的公開 IP 選項是灰的。

Oracle Cloud 的公開 IP 分兩種，性質在建立後不能互換：

- **臨時（ephemeral）**：跟著主機的生命週期。主機停止時保留，終止時自動刪除。建立頁上勾選「自動指派公開 IPv4」拿到的就是這一種。
- **保留（reserved）**：獨立的資源，主機終止之後仍然存在，可以再指派給另一台主機。要讓 DNS 記錄或外部白名單長期指向同一個位址時用這一種。

在 Oracle Cloud 上，公開 IP 可以在建立之後再加、也可以拿掉：網卡沒有公開 IP 時，可以另外建一個臨時公開 IP 指派上去。AWS 上建立時沒有自動指派的主機，之後要對外得另外掛一個 Elastic IP。建立之後還能加，所以不確定要不要對外時，可以先放私有 subnet、出站走 NAT 閘道，之後真的要對外再改放法；放在公開 subnet 卻不給公開 IP 的主機，在 Oracle Cloud 上連對外下載套件都做不到（見〈虛擬網路與 subnet〉）。AWS 對每個公開 IPv4 位址按小時另外計費，見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)。

主機是否指派了公開 IP，決定它在網際網路上暴露的面積。管理用的 SSH port 經由公開 IP 對外開放之後，網際網路上的掃描程式會持續嘗試登入。

## 防火牆規則的位置與合併方式

一個封包要到得了主機上的程式，要通過兩道關：雲端業者那一側的防火牆規則，以及主機作業系統裡的防火牆，兩道都放行才到得了。

雲端業者那一側，Oracle Cloud 與 AWS 有兩個掛規則的位置，Google Cloud 只有一個：

| 規則的位置 | Oracle Cloud                  | AWS                                                      | 作用範圍                   |
| ---------- | ----------------------------- | -------------------------------------------------------- | -------------------------- |
| subnet     | Security list                 | Network ACL                                              | 這個 subnet 裡的每一張網卡 |
| 網卡       | Network security group（NSG） | [Security group](/infra/knowledge-cards/security-group/) | 加入這一組規則的那幾張網卡 |

兩個位置的規則同時存在時怎麼合併，各家不同：

- **Oracle Cloud 取聯集**：官方〈Security Rules〉的說明是，套用在一張網卡上的規則是 subnet 的 security list 與這張網卡加入的所有 NSG 的聯集。Security list 與 NSG 都只能寫放行的規則，沒有拒絕規則，所以任何一邊有一條規則放行，封包就通過雲端那一道關。以 22 port 為例：

  | Security list 對 22 port | NSG 對 22 port | 封包能不能通過雲端那一道關 |
  | ------------------------ | -------------- | -------------------------- |
  | 有放行規則               | 沒有規則       | 能                         |
  | 沒有規則                 | 有放行規則     | 能                         |
  | 沒有規則                 | 沒有規則       | 不能                       |

  所以要擋掉 22 port，要把兩邊放行它的規則都拿掉；預設的 security list 開著 22 port 時，NSG 裡不寫 22 port 擋不住它。
- **AWS 兩個位置都要放行**：封包要先通過 subnet 的 Network ACL，再通過網卡的 security group。Network ACL 可以寫拒絕規則，官方建議把它當成第二道控制，用來擋掉特定的流量；security group 放行了，Network ACL 擋下來的封包仍然到不了。
- **Google Cloud 只有一個位置**：防火牆規則設在 VPC 上，再用網路標記或服務帳號選出它要套用的主機，沒有 subnet 這一層的規則。單一專案、沒有另外建過政策時只會遇到這一種；Google Cloud 另有專案層的 network firewall policy 與組織層的 hierarchical firewall policy，建了之後會跟 VPC 的防火牆規則依順序一起評估。

Oracle Cloud 建立頁上能設定的只有 NSG：「Use network security groups to control traffic」這個選項把主機的網卡加入某幾個 NSG，只有選既有的 VCN 時才出現。Security list 要到 VCN 的頁面設。官方文件說明 NSG 讓 subnet 的切法與應用程式的安全需求分開管理：同一個 subnet 裡的資料庫主機與網頁主機可以開不同的 port，不必為了開不同的 port 拆成兩個 subnet。

作業系統的防火牆（`iptables`、`nftables`、`ufw`）由主機自己管，不在雲端的主控台上。雲端那一道關放行了某個 port、連線仍然被拒絕時，要進主機查作業系統這一道。Oracle Cloud 的平台映像出廠就帶著一組作業系統防火牆規則，其中有讓主機連到開機磁碟與區塊磁碟的 iSCSI 端點的必要規則，官方〈Images〉建議不要移除；同一頁另外寫明在 Ubuntu 映像上不要用 `ufw` 改規則，用它改可能讓主機開不了機。

## 各家預設網路規則對 SSH 的開放

三家業者替使用者預先建好或順手建的網路，預設的規則都放行 22 port 的 SSH 流量，Oracle Cloud 與 Google Cloud 的來源是整個網際網路：

- **Oracle Cloud**：建立頁選「建一個新的 VCN」時，主控台一起建一份「Default Security List」，入站規則放行來源 `0.0.0.0/0` 的 TCP 22。Subnet 沒有另外指定 security list 時套用的就是這一份，所以在新建的公開 subnet 裡建一台有公開 IP 的主機，那台主機的 SSH port 一建好就對網際網路開放。這份規則的完整內容（實測值）見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/) 的 Networking 段。
- **Google Cloud**：專案建立時就有的 `default` 網路帶一條 `default-allow-ssh` 規則，放行 `0.0.0.0/0` 的 TCP 22，套用在這個網路裡的每一台主機。換掉這條規則的步驟見 [GCP VM 的 SSH 與 RDP 管理通道](/infra/cloud-providers/gcp/gcp-iap-ssh-access/)。
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
| 網卡層規則    | Network security group | 無（Firewall rule 設在 VPC 上，以網路標記或服務帳號選主機） | Security group                   |
| 兩層的合併    | 聯集                   | 只有一層                                                    | 兩層都要放行                     |
| 保留的公開 IP | Reserved public IP     | Static external IP address                                  | Elastic IP                       |

Subnet 的切法、路由表與 NAT 的設計見 [VPC、subnet 與 security group](/infra/03-network-foundation/vpc-subnet-security-group/)；網路通了之後，登入時用的金鑰與帳號見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/)。
