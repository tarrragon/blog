---
title: "Availability Zone（可用區）"
date: 2026-10-24
description: "建立雲端主機或磁碟時要選可用區、遇到某個可用區容量不足、規劃兩台主機要不要放在不同可用區，或對照各家把這一層叫 zone、AZ 還是 availability domain 時，查可用區的範圍、它跟區域與故障域的關係與它限制了哪些資源的搭配"
weight: 63
tags: ["infra", "knowledge-cards", "cloud", "availability"]
---

可用區（availability zone）是雲端區域（region）裡一個或一組彼此隔離的資料中心，各自有獨立的電力、冷卻與網路連線，設計上不會同時故障。同一個區域內的可用區之間以低延遲的專線相連。Google Cloud 叫 zone，AWS 叫 Availability Zone（AZ），Oracle Cloud 叫 availability domain（AD）。可用區之下還有一層更小的隔離單位，見 [Fault Domain（故障域）](/infra/knowledge-cards/fault-domain/)。

## 概念位置

雲端資源的位置由大到小是區域、可用區、故障域。區域決定的是地理位置（延遲、出口 IP 的國家、法規轄區），可用區決定的是「同一個城市裡哪一棟」，作用在兩件事上：

- **高可用**：同一個服務的多台主機分散在不同可用區，一棟資料中心停電或斷線時其他棟的主機繼續服務。只放在一個可用區的服務，那個可用區故障時整個服務停擺。
- **資源的搭配限制**：主機、開機磁碟、區塊磁碟這類資源屬於某一個可用區，主機只能掛同一個可用區的磁碟；[Subnet](/infra/knowledge-cards/subnet/) 在 AWS 上也綁在一個可用區，在 Google Cloud 與 Oracle Cloud 上可以跨可用區（Oracle Cloud 的 regional subnet）。

一個區域有幾個可用區依業者與區域而定。Oracle Cloud 的商用區域多數只有一個 AD，官方〈Regions and Availability Domains〉的區域表在 2026-10-24 列出有三個的是法蘭克福、倫敦、阿什本、芝加哥、鳳凰城，這份名單隨業者開新區域而變，選區時回到那張表看；只有一個可用區的區域做不到跨可用區的高可用，替代做法是分散到同一個可用區內的不同故障域，或跨區域。

## 可觀察訊號

- 建立主機時錯誤訊息寫「in availability domain AD-1」「in zone asia-east1-b」這類位置：容量是按可用區分配的，換一個可用區可能就建得起來
- 從保留下來的開機磁碟重建主機時，可選的可用區只剩那顆磁碟所在的那一個
- Oracle Cloud 的 AD 完整名稱帶有 tenancy 專屬的前綴（例如 `XXXX:AP-BATAM-1-AD-1`），不同帳號看到的前綴不同，指令裡要用 `oci iam availability-domain list` 查到的完整名稱

## 設計責任

- **單一台主機**：可用區只影響能否拿到容量，選建得起來的那一個即可
- **要做高可用的服務**：至少兩個可用區各放一份，負載平衡器與資料庫的副本也要跨可用區；跨可用區的流量在 AWS 與 Google Cloud 另外計費，費率見各家價格頁的資料傳輸那一項
- **選區域時**：服務需要跨可用區的高可用時，選有多個可用區的區域；只有一個可用區的區域，故障時的退路是故障域或另一個區域

## 鄰卡

- [Fault Domain（故障域）](/infra/knowledge-cards/fault-domain/) — 可用區內部更小一層的硬體隔離
- [VPC](/infra/knowledge-cards/vpc/) — 虛擬網路跨可用區還是綁在單一可用區，依業者而定
- [Subnet](/infra/knowledge-cards/subnet/) — AWS 的 subnet 綁在一個可用區，決定主機落在哪一棟
- [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/) — 建立主機時這三層選項的取捨
