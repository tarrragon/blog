---
title: "Userland Proxy（使用者空間的連接埠轉送程式）"
date: 2026-10-26
description: "ss 列出 docker-proxy、rootlesskit 或 rootlessport 聽著容器發佈的連接埠、主機防火牆的入站規則對容器的連接埠有效、或容器的存取紀錄只看得到閘道位址而沒有真實來源時，查這類轉送程式接收連線的路徑與它換掉來源位址的代價"
weight: 71
tags: ["infra", "knowledge-cards", "docker", "podman", "network", "firewall"]
aliases: ["/infra/knowledge-cards/userland-proxy/"]
---

把連線送進容器有兩種做法。[DNAT（目的位址轉換）](/devops/infra/knowledge-cards/dnat/) 是核心在封包剛進主機時改寫目的地，封包本身被轉送給容器；userland proxy 是一個在主機上執行的使用者空間程式聽著那個連接埠，收下連線之後自己再開一條連線到容器，把兩條連線之間的資料來回搬。常見的三個是 Docker 的 docker-proxy、rootless Docker 的 rootlesskit，以及 rootless Podman 的 rootlessport。

## 概念位置

連線的終點是主機上的一個程式，所以封包走的是 input 路徑（目的地是主機本身程式的那一條），主機防火牆的入站規則（ufw 的入站規則、firewalld 的 zone）管得到它，跟 DNAT 那一類正好相反。代價在容器看到的來源：容器收到的連線是轉送程式開的，來源位址是轉送程式那一端的位址，不是外面的真實來源。這跟 [Reverse Proxy（反向代理）](/devops/infra/knowledge-cards/reverse-proxy/) 換掉來源位址的道理相同，差別在反向代理常用 HTTP 標頭（`X-Forwarded-For`）把原本的來源帶過去，這幾個轉送程式在 TCP 這一層搬資料，什麼都不帶。

三個程式各在什麼時候出現：

- **docker-proxy**：以 root 執行的 Docker 用 `-p` 發佈時，主機上 IPv4 與 IPv6 各有一份；IPv4 那一份從外面來的封包在 prerouting 就被 DNAT 改寫、到不了它，IPv6 那一份在容器網路沒開 IPv6 時由它接收。Docker 的 `userland-proxy` 設成 `false` 時它不啟動，IPv6 那一份也就沒有發佈（2026-10-26 在 Docker 29.9.2 上實測）。
- **rootlesskit**：rootless Docker 的 dockerd 以一般使用者執行、不能改主機的 iptables，發佈的連接埠全部由它接聽。
- **rootlessport**：rootless Podman 的對應程式，網路由 slirp4netns（Podman 4）或 pasta（Podman 5 的預設）提供。

## 可觀察訊號與例子

- **`ss -ltnp` 列出這幾個程式聽著發佈的連接埠，nat 表裡沒有對應的 DNAT**：`users:(("rootlesskit",pid=4085,fd=13))` 聽著 `0.0.0.0:8083`，`iptables -t nat -S | grep -c 8083` 回 0。
- **容器的存取紀錄只有閘道位址**：2026-10-26 的實測裡，經由 docker-proxy 的 IPv6 連線與 rootless Docker 的連線，容器記到的來源都是 `172.17.0.1`；rootless Podman 4.9 記到的是 slirp4netns 那張 tap 介面的 `10.0.2.100`。
- **主機防火牆的入站規則對容器的連接埠有效**：ufw 預設拒絕入站時兩個測試來源都連不到 rootless 容器的連接埠，加一條入站放行之後只有被放行的那個連得到。

## 判讀方式

判斷一個發佈的連接埠屬於哪一類，先查有沒有規則把它的目的地改寫掉，再看誰在聽：`nft list ruleset | grep 'dport <連接埠>'` 同時列得出經由 iptables-nft 寫的與原生 nftables 寫的改寫規則。查到改寫規則時是 DNAT 那一類，聽著連接埠的程式只是佔住它（Podman 的 `conmon`、docker-proxy 的 IPv4 那一份），不算數；查不到時，聽著的轉送程式才是接收者。查表是預測，最終以從範圍外的來源實際連一次為準。屬於這一類時，限制寫在主機防火牆的入站規則上就有效，而容器裡依來源位址做的判斷（存取紀錄、速率限制、只信任來自 CDN 位址段的 `CF-Connecting-IP`）都拿不到真正的來源；Docker 文件列的保留來源位址做法（RootlessKit v3 的 `builtin` 加 `userland-proxy: false`、slirp4netns 轉送方式、pasta 加 `implicit`）這個站上沒有實跑。實測見 [Podman 與 rootless Docker 發佈連接埠的實測紀錄：rootful Podman 在 ufw 與 firewalld 上的轉送路徑、rootless Docker 與 rootless Podman 由主機程式接收的連接埠與容器看到的來源位址](/devops/infra/03-network-foundation/hands-on/podman-rootless-ports-walkthrough/) 與 [ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑](/devops/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/) 的〈IPv6 那一份發佈：docker-proxy 的接收路徑與 ufw 入站規則的效果〉。
