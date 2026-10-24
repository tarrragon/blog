---
title: "位置：區域、可用區與故障域"
date: 2026-10-24
description: "雲端主機的區域、可用區與故障域各自代表多大的範圍、各自決定主機的哪些性質（延遲、出口 IP 的國家、可用機型與容量、硬體故障的影響範圍），以及哪一層建立後就不能改"
weight: 1
tags: ["infra", "cloud-providers", "vm", "region", "availability-zone"]
---

這篇說明建立虛擬機時決定主機實體位置的三層選項。三層由大到小是區域、可用區、故障域，越大的那一層越早定、越難改。範圍是單一台主機的放置；多台主機跨可用區做高可用的設計見 [冗餘設計模式](/operations/06-high-availability/redundancy-patterns/)。

## 區域（region）：主機在哪個城市

區域是一個地理位置上的資料中心群。Oracle Cloud 的區域識別碼帶城市（`ap-tokyo-1`），Google Cloud 與 AWS 用洲別、方位加編號（`asia-east1` 在台灣、`ap-northeast-1` 在東京），城市要查各家的區域對照表。區域決定主機的下面這幾種性質：

- **延遲**：從使用者所在地連到主機的延遲主要由距離決定，量級上同一洲之內是幾十毫秒、跨洲是一兩百毫秒；實際的值用各家提供的區域延遲測試頁量，或從自己的電腦對那一區的服務端點量往返時間。
- **出口 IP 屬於哪個國家**：主機對外連線時，對方看到的來源 IP 登記在區域所在的國家。要讓連線看起來從某個國家發出（例如自架 VPN），只有那個國家的區域符合。
- **資料受哪個國家的法律管轄**：主機與它的磁碟實體上放在區域所在的國家，裡面的資料受那個國家的法規管轄。服務有資料落地的要求（個人資料不出境、產業法規指定存放地）時，能選的區域只剩那個國家或那個法域裡的區域。
- **能選的機型與服務**：區域之間提供的機型不同，新開的區域常常缺幾種舊機型。一個區域實際提供哪些機型，要在那一區的建立頁或 API 上查，不能從另一區推。

主機建好之後不能搬到另一個區域。要換區域，做法是在新區域建一台新主機、把資料搬過去，再刪掉舊的。

免費額度常常綁在特定區域上：Oracle Cloud 的 Always Free 只能用在申請時選的 home region，Google Cloud 的 Free Tier 只適用於三個美國區域。Oracle Cloud 的 home region 在申請帳號時就定了、之後不能改，所以這一層在 Oracle Cloud 上要在申請帳號之前想清楚；Google Cloud 的區域在建立主機時才選，選在三個美國區域以外就不算免費。各家的區域限制見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)。

## 可用區（availability zone / availability domain）：區域裡的哪一棟

可用區是區域裡彼此隔離的資料中心，各自有獨立的電力、冷卻與網路，設計上不會同時故障。建立頁上的這個欄位決定主機落在哪一個可用區，知識卡見 [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/)。

單一台主機選哪個可用區，影響的是兩件事：

- **容量**：免費機型與熱門機型的容量是按可用區分配的。一個可用區回報容量不足時，同一區域的另一個可用區可能還有。換可用區是容量不足時的退路之一，其他退路（等待重試、不指定故障域、改小規格、建立前查容量、換架構、可被收回的容量、預留容量、升級付費帳戶）在 Oracle Cloud 上的完整清單，連同哪幾項會計費，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈A1 容量不足時的退路〉。只有一個可用區的區域少了換可用區這條退路——Oracle Cloud 的商用區域多數只有一個可用區，有三個可用區的只有少數幾個，名單與查證日期見 [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/) 卡；業者開新區域時這份名單會變，選區之前回到官方〈Regions and Availability Domains〉的區域表看一次。
- **磁碟與主機要在同一個可用區**：開機磁碟與區塊磁碟屬於某一個可用區，主機只能掛同一個可用區的磁碟。從保留下來的開機磁碟重建主機時，新主機要建在那顆磁碟所在的可用區。

主機建好之後也不能換可用區，換的做法跟換區域相同。

## 故障域（fault domain）：同一棟裡的哪一組硬體

故障域是可用區內部的一組硬體與基礎設施，Oracle Cloud 的每個可用區有三個。它防的是兩種事件：某一組實體主機的硬體故障，以及業者對那一組硬體做的計畫性維護。一個故障域出事時，放在其他故障域的主機不受影響。知識卡見 [Fault Domain（故障域）](/infra/knowledge-cards/fault-domain/)。

只有一台主機時，故障域沒有選擇的意義：不論放在哪一個，那台主機都只在一組硬體上。建立頁的預設「讓業者選」就是對的選擇，Oracle Cloud 會依當下的容量挑一個（[實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/)在只有一個可用區的 `ap-batam-1` 就是這樣填的）。手動指定故障域還會縮小可用的容量：指定之後只接受那一個故障域裡的硬體。Oracle Cloud 的 Compute〈Known Issues〉頁對 `Out of host capacity` 列的處置裡，就有一項是不指定 fault domain 再建一次。

故障域的作用在兩台以上。同一個服務的兩台主機，區域有多個可用區時先分到不同可用區，因為可用區隔離的是整棟資料中心的電力與網路，範圍比故障域大（見 [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/) 的〈設計責任〉）；區域只有一個可用區時，才靠故障域把兩台放在不同的硬體上，一組硬體故障時只停一台。跨可用區的代價是兩台之間的流量多一段距離：AWS 與 Google Cloud 對跨可用區的流量另外計費，兩台之間做同步複製時延遲也比同一個可用區裡高。

Oracle Cloud 允許建立之後修改故障域。AWS 與 Google Cloud 沒有故障域這個欄位，對應的功能是放置政策（AWS 的 placement group 用 spread 策略、Google Cloud 的 spread placement policy），作用同樣是讓一組主機分散到不同的實體硬體上。兩家都能套用到既有的主機：AWS 要先停止主機才能把它換進或移出 placement group，Google Cloud 的 spread placement policy 指定了多個 availability domain（官方的說明是彼此隔離、各自不同的一組硬體；它跟 Oracle Cloud 的 availability domain 同名、層級不同，Oracle Cloud 那一層對應的是可用區）時，官方說明可以不停機就套用到既有的主機；套用時 Compute Engine 可能要把主機搬到另一個 availability domain，搬的方式依主機的維護政策，是即時遷移或停止主機。

## 各家的欄位名稱：區域、可用區與故障域

| 概念   | Oracle Cloud              | Google Cloud            | AWS                            |
| ------ | ------------------------- | ----------------------- | ------------------------------ |
| 區域   | Region                    | Region                  | Region                         |
| 可用區 | Availability domain（AD） | Zone                    | Availability Zone（AZ）        |
| 故障域 | Fault domain              | Spread placement policy | Placement group（spread 策略） |

Oracle Cloud 建立頁的 Placement 區塊裡另有一個 Capacity type 欄位，它決定的是計費與可被收回的條件，跟位置無關，說明在 [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/)。

## 延伸閱讀：同一組選項的下一層

- [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/)：那一區能選哪些機型，以及容量不足時改小規格、換架構或改用可被收回容量各自的代價
- [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)：免費額度綁在區域上時，申請帳號那一刻就決定了位置；配額表列出某個機型、而那一區沒有那種硬體時，建立會失敗而錯誤碼分不出原因
