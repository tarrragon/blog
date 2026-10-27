---
title: "Network Tag（GCP 網路標籤）"
date: 2026-10-23
description: "GCP 防火牆規則套不到某台 VM、新建的 VM 連不上，或要決定防火牆規則用 tag 還是服務帳號選 VM 時，查 network tag 怎麼讓防火牆規則選出要套用的 VM"
weight: 60
tags: ["infra", "knowledge-cards", "gcp", "network", "firewall"]
aliases: ["/infra/knowledge-cards/network-tag/"]
---

Network tag 是貼在 GCP VM 上的字串標籤，防火牆規則用它選出要套用的 VM：規則的 `--target-tags` 列出 tag，只有帶著其中一個 tag 的 VM 受這條規則影響（沒有 target 的規則套用到整個網路的 VM）。它是 VM 的屬性，`gcloud compute instances add-tags` 逐台加，或寫進 instance template 讓建出來的 VM 都帶著。AWS 沒有對應的標籤機制，對應的做法是把 instance 掛進 security group。可先對照 [Security Group](/devops/infra/knowledge-cards/security-group/)。

## 概念位置

tag 把「哪些 VM 要開這個 port」從防火牆規則裡拆出來，放到 VM 上：規則只寫一次，VM 加上 tag 就套用。代價是 tag 由誰都能改的 VM 屬性決定——有權限改 VM 的帳號加上一個 tag，那台 VM 就套用了那條規則；而一台 VM 被重建時，只有寫在 template 裡的 tag 會留下。這與 AWS 的 [Security Group](/devops/infra/knowledge-cards/security-group/) 方向相反：Security Group 是把 instance 掛進規則集合。要讓授權更嚴格時，防火牆規則改用 `--target-service-accounts` 依 VM 的服務帳號選，換服務帳號需要的權限比改 tag 高。

## 可觀察訊號

- `gcloud compute instances describe <vm> --format="value(tags.items)"` 列出這台 VM 的 tag
- 只放行 IAP 來源的規則存在、而某台 VM 經 IAP 連不上：先查這台 VM 有沒有那條規則的 target tag
- 由 [Managed Instance Group（MIG）](/devops/infra/knowledge-cards/managed-instance-group/) 自動重建或新建的 VM 少了手動加的 tag

## 設計責任

管理通道用的 tag（例如放行 IAP 來源連 22 port 的那一個）寫進 instance template 或 GKE node pool 的設定，不靠逐台 `add-tags`。改 template 或 node pool 的 tag 時，`--tags` 是整組指定，既有的 tag 要一起列進去。能改 VM tag 的權限等於能改那台 VM 套用哪些防火牆規則，授權時與防火牆規則的管理權一起考慮。

## 鄰卡

- [Security Group](/devops/infra/knowledge-cards/security-group/) — AWS 上用掛載而不是標籤決定規則套用範圍
- [Managed Instance Group（MIG）](/devops/infra/knowledge-cards/managed-instance-group/) — tag 寫在 template 裡才會留到重建後
- [Identity-Aware Proxy（身分感知代理）](/devops/infra/knowledge-cards/identity-aware-proxy/) — GCP 上放行 IAP 來源的防火牆規則用 tag 選 VM
