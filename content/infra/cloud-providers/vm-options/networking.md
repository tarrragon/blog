---
title: "網路：subnet、私有 IP、公開 IP 與防火牆規則"
date: 2026-10-24
description: "建立虛擬機時網路區塊的選項：主機放進哪個虛擬網路與 subnet、私有 IP 與公開 IP 各自的用途與生命週期、防火牆規則掛在 subnet、網卡與作業系統哪一層，以及預設網路設定對外開放了什麼"
weight: 3
tags: ["infra", "cloud-providers", "vm", "network", "security"]
---

這篇說明建立頁上網路區塊的選項，範圍是一台主機在既有網路裡的位置與對外的入口。虛擬網路本身怎麼切 subnet、路由與 NAT 怎麼設計見 [VPC、subnet 與 security group](/infra/03-network-foundation/vpc-subnet-security-group/)；管理員要怎麼登入沒有公開 IP 的主機見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## 虛擬網路與 subnet：主機放在哪一段網路

每台主機的網卡都接在一個虛擬網路（Oracle Cloud 叫 VCN，其他兩家叫 VPC）裡的某一個 [Subnet](/infra/knowledge-cards/subnet/) 上。建立頁要決定的是接在哪一個 subnet，而 subnet 已經決定了大部分的網路性質：

- **公開 subnet**：路由表有一條通往網際網路閘道的路由，裡面的主機可以有公開 IP，網際網路上的人可以直接連到它開放的 port。
- **私有 subnet**：沒有通往網際網路閘道的路由，裡面的主機不能有公開 IP，外面連不進來。主機要對外連線（下載套件更新）時經由 NAT 閘道出去，要連業者自己的服務（物件儲存、監控）時經由服務閘道。

建立頁通常提供「選既有的網路」與「建一個新的網路」兩條路。選「建新的」時，主控台會順手建一個 VCN 與 subnet，VCN 會帶著一份自動產生的預設防火牆規則，內容見〈預設防火牆規則對外開放了 22 port〉。要把主機放進自己設計過的網路時，先在網路的頁面建好 VCN 與 subnet，再回到建立頁選既有的。

Oracle Cloud 的 VCN 下拉選單只列出目前選定的 compartment 裡的 VCN。VCN 建在另一個 compartment 時，要先把建立頁上「VCN 所在的 compartment」那一欄切過去，選單裡才會出現它。

## 私有 IP：主機在虛擬網路裡的位址

每張網卡一定有一個私有 IP，從 subnet 的位址範圍裡分配。建立頁的選項是自動分配（預設）或手動指定一個位址。單一台主機選自動分配；要讓其他設定寫死這台主機的位址時（例如另一台主機的設定檔、防火牆規則只放行這一個位址），才手動指定。

私有 IP 在主機停止與重開時都不會變，終止主機時才釋放。同一個虛擬網路裡的其他主機用這個位址連它。

Oracle Cloud 另有一個 DNS record 選項：勾選之後，網卡會在 VCN 的內部 DNS 裡得到一個名稱，同一個 VCN 裡的主機可以用名稱代替 IP 連它。這個選項要 VCN 與 subnet 都設了 DNS label 才能用，名稱只在 VCN 內部有效，網際網路上查不到。

## 公開 IP：網際網路上的入口

公開 IP 讓網際網路上的人能直接連到這台主機。它只能指派給公開 subnet 裡的網卡；主機放在私有 subnet 時，建立頁上的公開 IP 選項是灰的。

Oracle Cloud 的公開 IP 分兩種，性質在建立後不能互換：

- **臨時（ephemeral）**：跟著主機的生命週期。主機停止時保留，終止時自動刪除。建立頁上勾選「自動指派公開 IPv4」拿到的就是這一種。
- **保留（reserved）**：獨立的資源，主機終止之後仍然存在，可以再指派給另一台主機。要讓 DNS 記錄或外部白名單長期指向同一個位址時用這一種。

公開 IP 可以在建立之後再加、也可以拿掉：網卡沒有公開 IP 時，可以另外建一個臨時公開 IP 指派上去。所以建立時不確定要不要對外，先不要給，比較安全。

一台主機有沒有公開 IP，決定的是它暴露在網際網路上的面積。管理用的 SSH port 經由公開 IP 對外開放之後，網際網路上的掃描程式會持續嘗試登入；服務本身要對外時，通常由負載平衡器承接，主機留在私有 subnet。

## 防火牆規則掛在哪一層

一個封包到得了主機上的程式，要依序通過幾層規則，任何一層不放行就到不了。建立頁上能設定的只有其中一層，其餘要到別的頁面設：

| 層       | Oracle Cloud                  | 作用範圍                   |
| -------- | ----------------------------- | -------------------------- |
| subnet   | Security list                 | 這個 subnet 裡的每一張網卡 |
| 網卡     | Network security group（NSG） | 加入這個 NSG 的那幾張網卡  |
| 作業系統 | `ufw`、`iptables`、`nftables` | 這一台主機                 |

Oracle Cloud 的 security list 設在 subnet 上，subnet 裡的每一張網卡都套用同一份；NSG 設在網卡上，同一個 subnet 裡的不同主機可以加入不同的 NSG。建立頁上「Use network security groups to control traffic」這個選項就是把主機的網卡加入某幾個 NSG，只有選既有的 VCN 時才出現。官方文件說明 NSG 讓 subnet 的切法與應用程式的安全需求分開管理：同一個 subnet 裡的資料庫主機與網頁主機可以開不同的 port，不必為了開不同的 port 拆成兩個 subnet。

作業系統這一層由主機自己管，不在雲端的主控台上。雲端的規則放行了某個 port、連線仍然被拒絕時，要進主機查這一層。

## 預設防火牆規則對外開放了 22 port

Oracle Cloud 建立 VCN 時會自動建一份「Default Security List for <VCN 名稱>」。實測一個新建的 VCN，這份預設規則的入站部分是：

- TCP 22（SSH），來源 `0.0.0.0/0`，也就是網際網路上的任何位址
- ICMP type 3 code 4（Path MTU Discovery 需要的封包），來源 `0.0.0.0/0`
- ICMP type 3，來源是 VCN 自己的位址範圍

出站是全部放行。Subnet 沒有另外指定 security list 時，套用的就是這一份，所以在公開 subnet 裡建一台有公開 IP 的主機，它的 SSH port 一建好就對整個網際網路開放。官方文件對這一條的描述是「from authorized source IP addresses」，並建議收緊；收緊的做法是把來源改成管理員的 IP，或改用不需要對外開放 SSH 的管理通道（見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)）。

## 其他網路欄位

- **網卡名稱（VNIC name）**：顯示用的名稱，不必唯一、之後可以改，不影響連線。留空時業者自動產生。
- **IPv6**：只有 VCN 與 subnet 都設了 IPv6 位址段時才能勾。單一台實驗機不需要。
- **Launch options（Oracle Cloud）**：網卡的虛擬化方式，只對虛擬機有效，維持預設即可。

## 各家的欄位名稱

| 概念          | Oracle Cloud           | Google Cloud                                | AWS                              |
| ------------- | ---------------------- | ------------------------------------------- | -------------------------------- |
| 虛擬網路      | VCN                    | VPC network                                 | VPC                              |
| 網卡          | VNIC                   | Network interface                           | ENI（Elastic Network Interface） |
| subnet 層規則 | Security list          | 無（規則設在 VPC 上）                       | Network ACL                      |
| 主機層規則    | Network security group | Firewall rule（以網路標記或服務帳號選主機） | Security group                   |
| 保留的公開 IP | Reserved public IP     | Static external IP address                  | Elastic IP                       |

## 延伸閱讀：網路設計與管理通道

- [VPC、subnet 與 security group](/infra/03-network-foundation/vpc-subnet-security-group/)：subnet 的切法、路由表與 NAT、最小開放的規則設計
- [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)：主機不給公開 IP 時，管理員怎麼登入
- [登入：SSH 金鑰與預設使用者](/infra/cloud-providers/vm-options/login/)：網路通了之後，登入時用的金鑰與帳號
