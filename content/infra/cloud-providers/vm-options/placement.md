---
title: "位置：區域、可用區與故障域"
date: 2026-10-24
description: "建立虛擬機時的區域、可用區與故障域各自代表多大的範圍、各自決定主機的哪些性質（延遲、出口 IP 的國家、可用機型與容量、硬體故障的影響範圍），以及哪一層建立後就不能改"
weight: 1
tags: ["infra", "cloud-providers", "vm", "region", "availability-zone"]
---

這篇說明建立虛擬機時決定主機實體位置的三層選項。三層由大到小是區域、可用區、故障域，越大的那一層越早定、越難改。範圍是單一台主機的放置；多台主機跨可用區做高可用的設計見 [運行期維運的高可用模組](/operations/06-high-availability/)。

## 區域（region）：主機在哪個城市

區域是一個地理位置上的資料中心群，名稱通常帶城市（`ap-tokyo-1`、`asia-east1`、`ap-northeast-1`）。區域決定主機的三種性質：

- **延遲**：從使用者所在地連到主機的延遲主要由距離決定。同一洲之內通常是幾十毫秒，跨洲是一兩百毫秒。
- **出口 IP 屬於哪個國家**：主機對外連線時，對方看到的來源 IP 登記在區域所在的國家。要讓連線看起來從某個國家發出（例如自架 VPN），只有那個國家的區域符合。
- **能選的機型與服務**：區域之間提供的機型不同，新開的區域常常缺幾種舊機型。一個區域實際提供哪些機型，要在那一區的建立頁或 API 上查，不能從另一區推。

主機建好之後不能搬到另一個區域。要換區域，做法是在新區域建一台新主機、把資料搬過去，再刪掉舊的。

免費額度常常綁在特定區域上：Oracle Cloud 的 Always Free 只能用在申請時選的 home region，Google Cloud 的 Free Tier 只適用於三個美國區域。這一層的限制比機型與網路都早生效，所以在申請帳號、還沒進建立頁之前就要想清楚，見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)。

## 可用區（availability zone / availability domain）：區域裡的哪一棟

可用區是區域裡彼此隔離的資料中心，各自有獨立的電力、冷卻與網路，設計上不會同時故障。建立頁上的這個欄位決定主機落在哪一個可用區，知識卡見 [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/)。

單一台主機選哪個可用區，影響的是兩件事：

- **容量**：免費機型與熱門機型的容量是按可用區分配的。一個可用區回報容量不足時，同一區域的另一個可用區可能還有。只有一個可用區的區域少了這條退路——Oracle Cloud 的區域多數只有一個可用區，官方列出的商用區域裡只有法蘭克福、倫敦、阿什本、芝加哥、鳳凰城有三個。
- **磁碟與主機要在同一個可用區**：開機磁碟與區塊磁碟屬於某一個可用區，主機只能掛同一個可用區的磁碟。從保留下來的開機磁碟重建主機時，新主機要建在那顆磁碟所在的可用區。

主機建好之後也不能換可用區，換的做法跟換區域相同。

## 故障域（fault domain）：同一棟裡的哪一組硬體

故障域是可用區內部的一組硬體與基礎設施，Oracle Cloud 的每個可用區有三個。它防的是兩種事件：某一組實體主機的硬體故障，以及業者對那一組硬體做的計畫性維護。一個故障域出事時，放在其他故障域的主機不受影響。知識卡見 [Fault Domain（故障域）](/infra/knowledge-cards/fault-domain/)。

只有一台主機時，故障域沒有選擇的意義：不論放在哪一個，那台主機都只在一組硬體上。建立頁的預設「讓業者選」就是對的選擇，Oracle Cloud 會依當下的容量挑一個。手動指定故障域還會縮小可用的容量——容量不足的錯誤訊息會建議「不要指定 fault domain 再試一次」，理由在此。

故障域的作用在兩台以上：同一個服務的兩台主機放在不同故障域，一組硬體故障時只倒一台。Oracle Cloud 允許建立之後修改故障域；在 AWS 與 Google Cloud 上，對應的功能是放置政策（placement group 的 spread 策略、spread placement policy），在建立時指定。

## 各家的欄位名稱

| 概念   | Oracle Cloud              | Google Cloud            | AWS                            |
| ------ | ------------------------- | ----------------------- | ------------------------------ |
| 區域   | Region                    | Region                  | Region                         |
| 可用區 | Availability domain（AD） | Zone                    | Availability Zone（AZ）        |
| 故障域 | Fault domain              | Spread placement policy | Placement group（spread 策略） |

Oracle Cloud 建立頁的 Placement 區塊裡另有一個 Capacity type 欄位，它決定的是計費與可被收回的條件，跟位置無關，說明在 [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/)。

## 延伸閱讀：同一組選項的下一層

- [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/)：選定位置之後，那一區能選哪些機型、容量不足時換機型的取捨
- [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)：免費額度綁在區域上時，申請帳號那一刻就決定了位置
