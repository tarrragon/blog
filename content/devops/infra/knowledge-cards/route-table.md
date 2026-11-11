---
title: "Route Table"
date: 2026-06-26
description: "掛在 subnet 上的流量轉送規則，決定封包離開 subnet 後往哪走"
weight: 15
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/route-table/"]
---

Route table 是一組轉送規則，掛在 [subnet](/devops/infra/knowledge-cards/subnet/) 上，定義「目的地是某個網段的封包該往哪送」。每個 subnet 關聯一張 route table，封包離開 subnet 時逐條比對規則、走最長前綴匹配的那一條。

## 跟其他概念的關係

Route table 決定了一個 subnet 是 public 還是 private。技術上的差別只有一行：route table 裡有沒有一條 `0.0.0.0/0 → Internet Gateway` 的預設路由。有這條路由的 subnet 是 public（封包可以直接出網、外部也可以連入）；把預設路由指向 [NAT Gateway](/devops/infra/knowledge-cards/nat/) 的 subnet 是 private（只能主動出站、外部無法入站）。subnet 本身的屬性不含 public/private 標記，性質完全由關聯的 route table 賦予。

## 可觀察訊號

private subnet 的服務突然拉不到外部套件或第三方 API 全部逾時時，排查路徑的第一步是檢查該 subnet 關聯的 route table：預設路由是否指向健康的 NAT Gateway。如果只有某一個可用區的節點受影響，通常是那一區的 NAT Gateway 或其所在 subnet 出狀況。

另一個常見訊號是新建的 subnet 沒有手動關聯 route table，被 VPC 的 main route table 自動關聯——main route table 的預設設定可能跟預期不符。

## 判斷條件與後果

一個 subnet 的預設路由指向哪裡，決定它的封包能不能出網、外部能不能連進來：指向 Internet Gateway 時它是 public subnet，裡面配了公網 IP 的資源會被外部直接觸及；指向 NAT Gateway 時它只能主動出站；沒有預設路由時它連外部套件來源都連不到。main route table 帶著對外路由時，新建而沒有手動關聯 route table 的 subnet 會自動套用它，在沒有人決定的情況下變成 public，原因是沒有明確關聯的 subnet 一律落回 main route table。VPC 之間的 peering 與服務 endpoint 只有在 route table 裡有對應的目的地網段時才收得到流量，少了那一條時連線逾時而沒有錯誤訊息。路由是在主控台手動加的時，review 的人讀不到某一條路由為什麼存在，所以每一條路由的目的地網段與目標寫進 IaC。

## 鄰卡

- [Subnet](/devops/infra/knowledge-cards/subnet/) — route table 掛在 subnet 上
- [NAT](/devops/infra/knowledge-cards/nat/) — private subnet 的預設路由目標
- [VPC](/devops/infra/knowledge-cards/vpc/) — route table 存在於 VPC 內
