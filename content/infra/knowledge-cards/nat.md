---
title: "NAT Gateway"
date: 2026-06-26
description: "讓 private subnet 的資源主動對外連線、同時不被外部入站觸及的網路地址轉換服務"
weight: 7
tags: ["infra", "knowledge-cards", "nat", "network"]
---

NAT Gateway（Network Address Translation Gateway）的核心職責是讓 [private subnet](/infra/knowledge-cards/subnet/) 的資源能主動發起對外連線（拉套件、呼叫第三方 API、下載 OS 更新），同時不開放任何外部主動發起的入站連線。它借用一個公網 IP 把出站封包送出去，再把回應導回原請求者。

## 概念位置

NAT Gateway 在網路地基裡的角色是 private subnet 的出站閘道。它解決的問題是：private subnet 的設計意圖是「外部連不進來」，但服務仍需要主動對外。沒有 NAT，private subnet 的資源完全無法對外通訊 — 連 `apt update` 或 `pip install` 都做不到。

NAT Gateway 是綁定單一可用區的資源，活在某個 public subnet 裡，實際生不生效由該 subnet 的 [route table](/infra/knowledge-cards/route-table/) 預設路由決定。這帶來一個架構取捨：共享一個 NAT（成本低、出站方向有單點）還是每個可用區各放一個（成本高、出站與 subnet 冗餘對齊）。

## 可觀察訊號

以下狀況指向 NAT 相關問題：

- Private subnet 的服務拉不到外部套件或第三方 API 全部逾時 — 先查 route table 有沒有指向健康的 NAT
- 只有某一個可用區的節點受影響 — 該區的 NAT 或其所在 subnet 可能故障
- 雲帳單裡 NAT Gateway 的流量費用異常高 — 大量走 NAT 的流量（S3 備份、跨區同步）可用 VPC Endpoint 繞過

## 設計責任

使用 NAT Gateway 時要決定：

- **數量**：每個可用區一個（可用性優先）還是全 VPC 共享一個（成本優先）。每個 NAT 固定月費約 $32 加流量費 $0.045/GB
- **高流量路徑**：對 AWS 自家服務的流量（S3、DynamoDB）改用 Gateway Endpoint 直連，繞過 NAT 省流量費
- **route table 關聯**：每個 private subnet 的 route table 要明確指向哪個 NAT

## 鄰卡

- [Subnet](/infra/knowledge-cards/subnet/) — NAT 放在 public subnet、服務放在 private subnet
- [VPC](/infra/knowledge-cards/vpc/) — NAT 屬於 VPC 內部的出站路徑設施
