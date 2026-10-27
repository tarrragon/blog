---
title: "Network Namespace（網路命名空間）"
date: 2026-10-25
description: "容器的網路為什麼跟主機分開、要在一台主機上模擬另一個來源位址做防火牆實測、或看到 ip netns 與 veth 時，查 Linux 核心的網路隔離單位與它跟 Kubernetes namespace 的差別"
weight: 69
tags: ["infra", "knowledge-cards", "network", "linux"]
aliases: ["/infra/knowledge-cards/network-namespace/"]
---

要在一台主機上讓一個程序有自己的 IP、自己的網路介面與路由表，Linux 用的是 network namespace（網路命名空間）：核心切出的一套獨立網路環境，跑在裡面的程序只看得到那一套。它是 Linux namespace 的其中一種，同一族還有隔離程序編號的 pid、隔離掛載點的 mount 等，容器同時用好幾種。預設的 bridge 網路下，每個容器各有一個 network namespace，所以容器裡有自己的 IP 與 `eth0`；發佈連接埠時，外面的連線靠主機上的 [DNAT](/devops/infra/knowledge-cards/dnat/) 把目的地改寫成容器的位址，送進容器的 namespace。Kubernetes 也有叫 namespace 的概念，指的是叢集裡資源的命名與權限分組，見 [Namespace](/backend/knowledge-cards/namespace/)；這張卡講的是核心層的網路隔離。

## 概念位置

兩個 network namespace 之間預設不通，要用 veth（成對的虛擬網路介面，從一端送進去的封包從另一端出來）一端放在 namespace 裡、一端放在主機上，再接到主機上的 bridge（Docker 的 docker0）或直接設路由。封包從 namespace 經 veth 進到主機時，跟從實體網卡進來的封包一樣經過主機的防火牆與 DNAT、由 [conntrack（連線追蹤）](/devops/infra/knowledge-cards/conntrack/) 記錄。容器不一定各有一個：`--network host` 的容器直接用主機的 namespace，`--network container:<名稱>` 與 Kubernetes 同一個 Pod 裡的容器共用一個。

## 可觀察訊號與例子

- **`ip netns list` 與 `ip netns exec <名稱> <指令>`**：手動建的 namespace 用 `ip netns add` 建立，`ip netns exec` 讓一條指令跑在那個 namespace 裡。Docker 建的 namespace 放在 `/var/run/docker/netns`，不在 `ip netns` 讀的 `/run/netns`，所以列不出來；要進容器的 namespace，用 `docker inspect -f '{{.State.Pid}}' <容器>` 取得容器程序的 PID，再用 `nsenter -t <PID> -n <指令>` 執行。
- **主機上多出 `veth` 開頭的介面**：容器每接一個 bridge 網路就有一條，另一端在容器的 namespace 裡（第一條叫 `eth0`，再接一個網路是 `eth1`）。
- **一台主機上模擬兩個來源位址**：建兩個 namespace，各給一個位址（例如一個落在 Cloudflare 的位址段、一個落在範圍外），從各自的 namespace 連主機，就能驗證「只放行某些來源」的防火牆規則，不需要第二台主機。這個做法的完整指令見 [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/devops/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/) 的〈用 network namespace 模擬 Cloudflare 與其他來源〉；ufw 主機上的版本，以及替兩個來源加 IPv6 位址的 `ns_setup6`，見 [ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑](/devops/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/) 的〈共用的函式與兩個測試來源〉。

## 判讀方式

一個程序連不到某個位址、或看到的介面跟預期不同時，原因常在它跑在哪個 network namespace：同一台主機上的 `127.0.0.1` 在每個 namespace 裡各指自己，容器裡連 `127.0.0.1` 連不到主機上的服務，容器裡的程式也綁不上主機的 LAN 位址（那個位址不在容器的 namespace 裡）。用 namespace 模擬來源做測試時，結果只驗證到防火牆依來源位址的判斷：封包從 veth 進來，firewalld 對沒有指派 zone 的 veth 套用預設 zone 的規則，主機的實體網卡在別的 zone 時，模擬的結果不代表真實流量；真實網路上的路由、雲端防火牆與上游服務（例如 CDN 實際用哪些位址回源）也不在測試範圍內。
