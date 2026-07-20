---
title: "CIDR（Classless Inter-Domain Routing）"
date: 2026-06-26
description: "用前綴長度表示 IP 地址範圍的表示法，決定 VPC 與 subnet 的地址空間大小"
weight: 13
tags: ["infra", "knowledge-cards", "cidr", "network"]
---

CIDR（Classless Inter-Domain Routing）用前綴長度表示一段 IP 地址範圍。`10.0.0.0/16` 表示前 16 bit 是網路位址、後 16 bit 是主機位址，提供約六萬五千個可用位址。前綴越短、範圍越大：`/16` 比 `/24`（約 256 個位址）大 256 倍。[VPC](/infra/knowledge-cards/vpc/) 和 [subnet](/infra/knowledge-cards/subnet/) 的地址空間都用 CIDR 表示。

## 概念位置

CIDR 是 [VPC](/infra/knowledge-cards/vpc/) 規劃的起點決策。建立 VPC 時指定的 CIDR 區塊決定了這個 VPC 能容納多少 subnet 和多少資源。這個決策在建立後難以修改——事後擴張意味著追加 secondary CIDR，而追加的網段在 routing 與服務相容性上有限制。

在 infra 系列中，CIDR 規劃出現在[模組三：網路地基](/infra/03-network-foundation/vpc-subnet-security-group/)的 VPC 段落。Terraform 的 `cidrsubnet` 函式可以從 VPC 的 CIDR 自動切出 subnet 的子網段，避免手動計算。

## 可觀察訊號

CIDR 規劃出問題的訊號有兩類。第一類是地址耗盡：subnet 切不出新的子網段、或 subnet 內的 IP 分配用完，新資源無法取得位址。第二類是網段衝突：需要透過 VPC peering、Transit Gateway 或 VPN 互連兩個 VPC 時，發現兩端的 CIDR 重疊，路由無法解析，peering 建立失敗。

## 設計責任

規劃 CIDR 時要決定：

- 大小：單一環境用 `/16` 通常足夠寬裕，切成 `/20` 的 subnet 可分配 16 個子網段
- 不重疊：多個環境（dev `10.0.0.0/16`、staging `10.1.0.0/16`、prod `10.2.0.0/16`）用連續但不重疊的區段，為日後互連預留空間
- 與地端的協調：如果未來可能接 VPN 回地端機房，CIDR 要避開地端已使用的私有網段

## 鄰卡

- [VPC](/infra/knowledge-cards/vpc/) — 用 CIDR 區塊定義的邏輯隔離網段
- [Subnet](/infra/knowledge-cards/subnet/) — 從 VPC CIDR 切出的子網段
