---
title: "conntrack（連線追蹤）"
date: 2026-10-25
description: "防火牆規則寫了 established、related 或 ctorigdstport、有狀態防火牆為什麼不必寫回程規則、改了規則卻像沒生效、或位址轉換之後要比對原本的位址時，查 Linux 核心記錄連線狀態的表與它在規則裡的用法"
weight: 68
tags: ["infra", "knowledge-cards", "network", "firewall"]
---

雲端的 [Security Group](/infra/knowledge-cards/security-group/) 放行一條入站連線之後，回程的封包不必另寫規則，因為它是「有狀態」的防火牆；Linux 主機上讓防火牆有狀態的元件是 conntrack（connection tracking，連線追蹤）。它是核心裡記錄每一條連線的表：兩端的位址與連接埠、協定、TCP 的連線階段（SYN_SENT、ESTABLISHED、TIME_WAIT 這類），以及經過位址轉換時原本與改寫後的兩組位址。防火牆規則比對的連線狀態（NEW、ESTABLISHED、RELATED、INVALID）是核心依這張表替每個封包推出來的。

## 概念位置

iptables 的 `-m conntrack`、`-m state` 與 nftables 的 `ct` 都在讀這張表。它也是 [DNAT](/infra/knowledge-cards/dnat/) 與 SNAT（[NAT Gateway](/infra/knowledge-cards/nat/) 做的那一種）能運作的前提：核心在連線的第一個封包改寫位址時，把原本與改寫後的對應記進表裡，同一條連線之後的封包與回程封包都照這個對應改寫。規則要比對位址轉換之前的值時，讀的就是表裡記下的「原始方向」（original）。

## 可觀察訊號與例子

- **防火牆規則開頭的 `ct state { established, related } accept`**：實測時 firewalld 的轉送鏈就以這一條起手，已經放行的連線之後的封包直接通過，規則只需要描述新連線。
- **firewalld 的 `ct status dnat accept`**：在 `StrictForwardPorts=no`（預設值）下，所有經過目的位址轉換的連線在任何 policy 之前就被接受，Docker 發佈的連接埠因此不受 firewalld policy 約束。
- **`DOCKER-USER` 裡的 `-m conntrack --ctorigdstport 8081 --ctdir ORIGINAL`**：封包的目的地已經改成容器的 80，用表裡記下的原始目的連接埠 8081 比對；`--ctdir ORIGINAL` 只比對發起方向的封包，回程封包不進這條規則。
- **`conntrack -L`**（套件 conntrack-tools）或 `/proc/net/nf_conntrack`：列出表裡每一條連線，一行裡有協定、TCP 階段、`src=`/`dst=`/`sport=`/`dport=` 兩組（第一組是原始方向，第二組是回程方向；兩組對不上就是經過了位址轉換），以及 `ASSURED` 這類旗標。

## 判讀方式

一條防火牆規則比對的是封包現在的欄位，或是表裡記下的原始值，兩者在位址轉換之後不同：寫在位址轉換之後的規則，要比對原本的位址或連接埠時要用 `ctorig*` 這類條件，用 `--dport` 只比對得到改寫後的值。規則改了卻像沒生效時，原因常在已經存在的連線：ESTABLISHED 的連線多半在規則前面就被放行，新規則只擋得到之後的新連線；要讓既有的連線也受新規則約束，用 `conntrack -D`（可加 `-p tcp --dport <連接埠>` 縮小範圍）刪掉表裡那幾條，連線方重新連線時才會被新規則比對。表的容量有上限（`nf_conntrack_max`），連線數很大的主機表滿時會丟掉新連線，核心記錄裡會出現 `nf_conntrack: table full, dropping packet`。Docker 發佈的連接埠怎麼用它限制來源，見 [CDN 後面的源站主機防火牆](/infra/03-network-foundation/origin-host-firewall/)。
