---
title: "Bastion Host（跳板機）"
date: 2026-10-23
description: "內部主機不想各自對外開管理 port、或要評估自建跳板機與改用身分感知代理的取捨時，查跳板機的連線方式、暴露面與維運責任"
weight: 55
tags: ["infra", "knowledge-cards", "network", "ssh", "access"]
---

管理員要登入 private [Subnet](/infra/knowledge-cards/subnet/) 裡的主機時，跳板機（bastion host，也稱 jump host；其他中文資料常寫作「堡壘主機」）是常見的中繼點：一台放在公開網段、只負責轉接管理連線的主機。其他主機的防火牆只接受來自跳板機的 SSH，管理員先連上跳板機，再從那裡連到目的主機。OpenSSH 用 `ssh -J <bastion-host> <target-host>`（設定檔裡的 `ProxyJump`）一次完成兩段連線，私鑰留在管理員自己的電腦上，不必複製到跳板機。

## 概念位置

跳板機在[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的模型裡屬於網路可達性這一層：它把「每台主機都對外開 22 port」收斂成「只有一台對外開」。它同時兼任通道授權，判斷依據是跳板機上的 SSH 金鑰；跳板機與目的主機接受同一把金鑰時，一把私鑰外洩就同時通過這兩層。它放在 public [Subnet](/infra/knowledge-cards/subnet/)，目的主機留在 private subnet，兩者之間的放行由 [Security Group](/infra/knowledge-cards/security-group/) 的來源引用表達。

暴露面收斂成一台，但沒有消失：跳板機仍然對網際網路開著管理 port，它的 sshd 漏洞與金鑰管理就是整個環境的入口。不讓任何自管主機對外的做法是 [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/)，對外接收連線的那一層改由代理服務承擔。

雲端廠商也提供受管的跳板服務（例如 Azure Bastion），主機的修補由廠商負責，連線方式與身分驗證依各家服務而定，位置介於自建跳板機與身分感知代理之間。

## 可觀察訊號

- private subnet 主機的 security group 只允許來自某一個 security group（或某一台主機）的 22 port
- 管理員的 `~/.ssh/config` 裡有 `ProxyJump` 設定，或團隊文件寫著「先連 bastion」
- 跳板機的認證紀錄裡持續有來自陌生 IP 的失敗登入——這台主機承受的是整個環境的掃描流量

## 設計責任

使用跳板機時要決定：

- **跳板機的來源範圍**：管理員有固定的對外 IP 時，跳板機的 22 port 只放行那幾個 IP；遠端工作、IP 會變動時，白名單縮不下來，跳板機的 22 port 實質上對全網開放，這時它的 sshd 修補速度就是整個環境的暴露期，對外入口改用 VPN 或身分感知代理承接比較划算
- **私鑰不落地**：用 `ProxyJump` 讓認證在管理員電腦上完成；把私鑰放上跳板機、或開啟 agent forwarding，跳板機被入侵時攻擊者就拿得到通往所有主機的憑證，這種擴散見 [Lateral Movement（橫向移動）](/backend/knowledge-cards/lateral-movement/)
- **修補與監控**：跳板機要比其他主機更快套用 sshd 的安全更新，並保留連線紀錄
- **操作紀錄**：需要集中錄製管理員在目的主機上做了什麼時，跳板機是錄製的位置。多雲與地端混用的環境仍選用跳板機，理由有兩個：它與廠商無關、一套設定涵蓋所有環境，以及它是集中錄製的位置

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — 跳板機轉接的協定與金鑰認證
- [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/) — 改用代理服務承擔對外接收連線
- [Subnet](/infra/knowledge-cards/subnet/) — 跳板機放 public、目的主機放 private
- [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/) — 跳板機與其他管理通道做法的選擇條件
