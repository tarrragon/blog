---
title: "VNIC（虛擬網路卡）"
date: 2026-10-27
description: "雲端主機的私有 IP、公開 IP 或網卡層的防火牆規則要查、要改，或主機重建之後私有 IP 與防火牆規則跟著不見時，查 VNIC 掛著哪些設定、它跟主機一起建立與刪除的關係，以及各家的名稱"
weight: 76
tags: ["infra", "knowledge-cards", "network", "vnic"]
---

VNIC（virtual network interface card，虛擬網路卡）是雲端主機接上虛擬網路的那一張網卡。主機在網路上的身分都掛在它上面：所在的 [Subnet（子網路）](/infra/knowledge-cards/subnet/)、私有 IP、公開 IP（有配發時），以及網卡層的防火牆規則（Oracle Cloud 的 NSG、AWS 的 [Security Group](/infra/knowledge-cards/security-group/)）。各家的名稱不同：Oracle Cloud 叫 VNIC，AWS 叫 ENI（Elastic Network Interface），Google Cloud 叫 network interface。

## 概念位置

主機與網路設定之間隔著 VNIC 這一層，所以「這台主機的私有 IP 是多少」「這台主機套用了哪些網卡層的防火牆規則（[Security Group](/infra/knowledge-cards/security-group/) 這一類）」查的都是它的 VNIC，不是主機本身。Oracle Cloud 的 CLI 也是這樣分工：`oci compute instance list-vnics` 列出主機的 VNIC 與私有 IP，掛上或拿掉 NSG 用的是 `oci network vnic update --nsg-ids`，而不是主機的指令。

建立主機時，業者同時替它建一張主要的 VNIC；主機被刪除時，這張 VNIC 也跟著刪除，上面的私有 IP 與防火牆規則的掛載關係一起消失。所以主機被刪除再重建時，新主機拿到的是一張新的 VNIC：私有 IP 多半換了一個，原本掛在舊 VNIC 上的 NSG 要重新掛上去；而 NSG 本身與它的規則屬於虛擬網路，不跟著主機消失。主機只是停止時，VNIC 與私有 IP 都留著。在 Oracle Cloud 上實際重建過一次的資源去留與重新掛 NSG 的指令，見 [Oracle Cloud 私有子網路 Ubuntu 主機的實測紀錄：套件來源的出站（NAT gateway、路由與 NSG）、序列主控台的連線，以及被回收之後的重建](/infra/cloud-providers/oracle-cloud/hands-on/private-ubuntu-egress-console-rebuild/)〈被回收之後的重建：怎麼發現、留下與消失的資源、重建腳本〉。

一台主機可以另外掛第二張以上的 VNIC，接到另一個 subnet；那些額外的網卡依各家的規則可以單獨拿掉，主要的那一張跟主機一起建立、一起刪除。

## 可觀察訊號

- 主機重建之後，原本連得到網際網路的套件更新又逾時、而沒有任何錯誤訊息：新的 VNIC 沒有掛上原本的出站規則
- 剛建好的主機，列出 VNIC 的查詢一時回空值：主機還在建立，VNIC 的掛載紀錄還沒出現
- 同一個 subnet 裡兩台主機的防火牆行為不同：subnet 層的規則相同，差在各自 VNIC 上掛的 NSG 或 security group

## 設計責任

網卡層的規則只影響掛上它的那幾張 VNIC，subnet 層的規則影響整個 subnet，所以放規則的位置決定了影響範圍；而 VNIC 會隨主機重建而換新，所以：

- **規則放在哪一層**：只給一台主機的放行（例如只有它需要的出站）放在網卡層，掛在它的 VNIC 上；整個 subnet 都需要的放在 subnet 層。兩層怎麼合併見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/)〈防火牆規則的位置與合併方式〉
- **重建時的重新掛載**：用腳本或 IaC 重建主機時，把「掛上網卡層規則」寫成重建流程的一步，或在建立主機時就指定（Oracle Cloud 的 `instance launch --nsg-ids`），不靠人記得
- **整份替換**：Oracle Cloud 的 `vnic update --nsg-ids` 用給的清單取代整份 NSG 清單，加一個 NSG 時要把原本掛著的那幾個一起寫進去

## 鄰卡

- [Subnet（子網路）](/infra/knowledge-cards/subnet/) — VNIC 接在哪一個 subnet，決定它的私有 IP 範圍與 subnet 層的規則
- [Security Group](/infra/knowledge-cards/security-group/) — 掛在網卡層的有狀態防火牆，Oracle Cloud 的對應是 NSG
- [NAT Gateway](/infra/knowledge-cards/nat/) — 沒有公開 IP 的 VNIC 往外連時經過的出口
- [VPC（Virtual Private Cloud）](/infra/knowledge-cards/vpc/) — VNIC 所在的虛擬網路
