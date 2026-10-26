---
title: "DNAT（目的位址轉換）"
date: 2026-10-25
description: "容器發佈的連接埠沒被主機防火牆擋下、port forwarding 的限制規則要寫在位址轉換之前還是之後、或要比對位址轉換之前的連接埠時，查 DNAT 改寫封包目的地的時間點與它對防火牆規則的影響"
weight: 67
tags: ["infra", "knowledge-cards", "nat", "network", "firewall"]
---

[NAT Gateway](/infra/knowledge-cards/nat/) 改的是出站封包的來源位址（SNAT），讓內部主機借一個公開位址出去；DNAT（destination NAT，目的位址轉換）改的是入站封包的目的地，讓外面的連線送到指定的那一台：封包原本送往「主機的 8081」，改寫之後送往「容器的 80」。回程的封包由 [conntrack（連線追蹤）](/infra/knowledge-cards/conntrack/) 記下的對應自動改回來，外面的連線方看到的始終是主機的位址與 8081。

## 概念位置

Linux 處理封包的框架叫 netfilter，它在封包流程上留了幾個固定位置（hook）讓規則掛上去。DNAT 掛在 prerouting 這個 hook：封包剛進主機、核心還沒決定路由之前就改寫（iptables 寫在 nat 表的 PREROUTING 鏈，nftables 寫在 `type nat` 的鏈；主機本機發出的連線則在 OUTPUT 那一段改寫）。改寫之後，核心依新的目的地決定路由：目的地是容器或另一台主機時，封包走轉送（forward）路徑送給另一個介面，不經過管主機本身入站連線的 input 路徑；改寫成主機本機的位址或連接埠時（iptables 的 REDIRECT、firewalld 不帶目的位址的 forward-port），封包仍走 input 路徑。

Docker 用 `-p 8081:80` 發佈連接埠時，IPv4 那一份屬於目的地改成容器的那一種：寫在 input 路徑上的主機防火牆規則（ufw、firewalld 的 zone）管不到它（容器網路沒開 IPv6 時，IPv6 那一份不經 DNAT，由主機上的 docker-proxy 程式接收、走 input 路徑，見 [ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑](/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/)），而轉送路徑上 Docker 與 firewalld 預設都放行經過位址轉換的連線（Docker 的 `DOCKER-FORWARD` 鏈、firewalld 的 `ct status dnat accept`），所以這些連接埠繞過了主機防火牆。雲端的 [Security Group](/infra/knowledge-cards/security-group/) 在封包到達主機、還沒被改寫之前就比對完，不受這個改寫影響。

## 可觀察訊號與例子

- **`iptables -t nat -S DOCKER` 看得到規則**：`-A DOCKER ! -i docker0 -p tcp -m tcp --dport 8081 -j DNAT --to-destination 172.17.0.2:80` 就是 Docker 發佈 8081 時寫的那一條。
- **防火牆清單看不到、外面卻連得到的連接埠**：`firewall-cmd --list-all` 與 `ufw status` 都沒有列 8081，從外面連照樣拿到容器的回應；查發佈的連接埠要用 `docker ps` 或 `ss -ltnp`。
- **規則比對不到改寫前的連接埠**：寫在 FORWARD 鏈的 `--dport 8081` 比對不到任何封包，因為封包到那裡時目的連接埠已經是 80。

## 判讀方式

限制規則寫在 DNAT 之前還是之後，決定它看得到哪一個連接埠：之前（prerouting、優先序比 dstnat 小）看得到原本的目的連接埠，直接用它比對；之後（FORWARD 鏈、Docker 的 `DOCKER-USER`）看到的是改寫後的容器位址，要改用連線追蹤記下的原始值比對（iptables 的 `-m conntrack --ctorigdstport 8081`、nftables 的 `ct original proto-dst 8081`）。主機防火牆沒有放行、外面卻連得到的連接埠，多半是經過 DNAT 送給了容器或另一台主機，這時原因在規則的位置，不在規則的內容。Kubernetes 的 NodePort 在 kube-proxy 的 iptables 模式下也用 DNAT 送往 Pod，IPVS 模式的掛法不同，兩者都沒有在這個站上實測。Docker 的實測與各種限制寫法的比較見 [源站防火牆只放行 Cloudflare 位址的實測紀錄](/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/)。
