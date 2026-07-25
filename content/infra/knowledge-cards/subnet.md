---
title: "Subnet（子網路）"
date: 2026-06-26
description: "VPC 內按可用區與暴露程度切出的子網段，決定資源有沒有一條通往網際網路的路徑"
weight: 5
tags: ["infra", "knowledge-cards", "subnet", "network"]
---

Subnet 是 [VPC](/infra/knowledge-cards/vpc/) 內部按可用區（Availability Zone）與暴露程度切出來的子網段。一塊資源對外暴露到什麼程度，取決於它被放進哪個 subnet——技術上的差別在於該 subnet 關聯的 route table 裡有沒有一條指向 Internet Gateway 的預設路由。

Subnet 分兩類：

- **Public subnet**：route table 有 `0.0.0.0/0 → Internet Gateway`，讓資源能被外部 IP 直接觸及。典型住戶是對外負載平衡器、[NAT](/infra/knowledge-cards/nat/) Gateway。
- **Private subnet**：route table 把 `0.0.0.0/0` 指向 NAT Gateway，外部無法主動連入。典型住戶是應用伺服器、資料庫、快取。

Public subnet 的真實樣貌是「薄薄一層」——它通常只住入口設施，業務邏輯跟資料儲存都在 private subnet。

## 概念位置

Subnet 是[模組三：網路地基](/infra/03-network-foundation/vpc-subnet-security-group/)的中層邊界。[VPC](/infra/knowledge-cards/vpc/) 定好地址空間後，subnet 決定「哪些資源能被外網碰到、哪些只能在內網存取」。每個 subnet 綁定單一可用區，高可用設計通常是每種角色跨至少兩個可用區各開一個 subnet。

## 可觀察訊號

Subnet 配置有問題的訊號：應用伺服器被放在 public subnet 並配了公網 IP（管理埠暴露在掃描流量下）、private subnet 的服務拉不到外部套件（route table 沒指向健康的 NAT）、新服務上線時找不到適合的 subnet（CIDR 切得太小、空間不夠）。

## 設計責任

規劃 subnet 時要決定：

- CIDR 切法：VPC 是 `/16` 時，每個 subnet 用 `/20`（約四千位址）可以在三個可用區各開 public + private 共六個 subnet
- 跨可用區對稱：每種角色至少跨兩個 AZ，讓單一 AZ 故障時另一區能承接
- public 的住戶限制：只放入口設施，業務邏輯一律放 private

## 鄰卡

- [VPC](/infra/knowledge-cards/vpc/) — subnet 的容器
- [NAT](/infra/knowledge-cards/nat/) — 讓 private subnet 出站的機制
- [Security Group](/infra/knowledge-cards/security-group/) — 掛在資源上的埠級存取控制
