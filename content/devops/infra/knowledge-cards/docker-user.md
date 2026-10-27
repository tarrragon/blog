---
title: "DOCKER-USER（Docker 留給使用者的轉送規則鏈）"
date: 2026-10-26
description: "要在 Docker 發佈的連接埠上加來源限制、寫進 DOCKER-USER 的規則在防火牆重新載入或重開機之後不見、或規則擋到了容器自己往外的連線時，查這條鏈在轉送路徑上的位置、比對原始連接埠的寫法與規則的存續條件"
weight: 70
tags: ["infra", "knowledge-cards", "docker", "iptables", "firewall"]
aliases: ["/infra/knowledge-cards/docker-user/"]
---

DOCKER-USER 是 Docker 在 iptables 的 filter 表裡建的一條自訂鏈：FORWARD 鏈的第一條規則無條件跳到它，Docker 自己不在裡面寫任何規則，啟動與重啟時也不清它的內容，讓使用者在 Docker 放行容器流量之前插入自己的限制。它管的是轉送路徑：Docker 發佈的連接埠經過 [DNAT（目的位址轉換）](/devops/infra/knowledge-cards/dnat/) 改寫成容器位址之後，封包由主機轉送給容器，寫在主機入站規則（ufw 的入站規則、firewalld 的 zone）上的限制碰不到它，DOCKER-USER 是這條路上第一個可以寫規則的位置。

## 概念位置

FORWARD 鏈的跳轉順序是 DOCKER-USER、Docker 自己的 `DOCKER-FORWARD`、然後才是 ufw 的 `ufw-*` 鏈；`DOCKER-FORWARD` 接受送往發佈連接埠的連線，所以寫在 ufw route 規則裡的限制輪不到這些封包，寫在 DOCKER-USER 的輪得到。封包到這條鏈時目的地已經是容器的位址與連接埠，限制發佈的連接埠要用 [conntrack（連線追蹤）](/devops/infra/knowledge-cards/conntrack/) 記下的原始目的連接埠比對：

```bash
iptables -I DOCKER-USER -p tcp -m conntrack --ctstate DNAT --ctorigdstport 443 --ctdir ORIGINAL ! -s 173.245.48.0/20 -j DROP
```

三個 conntrack 條件各管一件事：`--ctorigdstport 443` 比對位址轉換之前的連接埠；`--ctdir ORIGINAL` 只比對發起方向的封包，容器回覆的封包不拿來比對來源；`--ctstate DNAT` 只比對經過位址轉換的連線，也就是送往發佈連接埠的那些。少了最後一個時，容器自己往外連 443、同一台主機上容器之間連 80 的封包也進這條鏈、原始目的連接埠一樣是 443 或 80，一起被丟掉（2026-10-26 在 Ubuntu 24.04 與 Docker 29.9.2 上實測）。

這條鏈只存在 iptables 後端：Docker 改用 nftables 後端時沒有它（Docker 的〈firewall-nftables〉文件）。它也只管 IPv4 那一份發佈：容器網路沒開 IPv6 時，IPv6 那一份由主機上的 [Userland Proxy（使用者空間的連接埠轉送程式）](/devops/infra/knowledge-cards/userland-proxy/) 接收，不經過轉送路徑。主機上同時裝了 Docker 與以 root 執行的 Podman 時，Podman 的轉送封包也經過 DOCKER-USER（實測）。

## 可觀察訊號與例子

- **`iptables -S FORWARD` 的前兩行**：`-A FORWARD -j DOCKER-USER`、`-A FORWARD -j DOCKER-FORWARD`。主機也裝了 Podman 時，最前面還有一條 `-j NETAVARK_FORWARD`。
- **規則加了、從外面量過擋得住，過一陣子又失效**：防火牆重新載入或重開機清掉了它，`iptables -S DOCKER-USER` 只剩 `-N DOCKER-USER` 這一行。
- **加了限制之後容器呼叫外部 API 逾時**：規則只比對原始目的連接埠，沒有 `--ctstate DNAT`，容器的出站連線也被丟掉。

## 判讀方式

DOCKER-USER 的弱點在規則的存續，用 iptables 指令加的規則只存在執行中的核心裡，各種情形下的結果不同（2026-10-25 到 26 日在 Ubuntu 24.04 的 ufw 0.36.2、Oracle Linux 10.2 的 firewalld 2.4.3 上實測）：

| 情形                                                              | 規則                                                                 |
| ----------------------------------------------------------------- | -------------------------------------------------------------------- |
| 任何主機重開機                                                    | 不在                                                                 |
| `systemctl restart docker`                                        | 還在                                                                 |
| ufw 的 `ufw reload`，after.rules 沒有宣告這條鏈                   | 還在                                                                 |
| ufw 的 after.rules 宣告這條鏈                                     | 每次 reload 先清空、再寫入檔案裡的規則；用 iptables 指令另外加的不在 |
| firewalld 的 reload，nftables 後端、沒有 direct 設定              | 還在                                                                 |
| firewalld 的 reload，nftables 後端、有 direct rule 或 passthrough | 不在（Oracle Cloud 的 Oracle Linux 平台映像自帶 passthrough）        |
| firewalld 的 reload，iptables 後端                                | 不在                                                                 |

要讓規則留過重開機，ufw 主機把它寫進 `/etc/ufw/after.rules`，同一台主機上的 DOCKER-USER 規則都要寫在那裡；firewalld 主機上改用掛在位址轉換之前的自建 nftables 表，或把限制放在雲端防火牆。direct 設定是主機當下的狀態，之後裝的軟體可能再加進來，用[組態管理](/devops/infra/knowledge-cards/configuration-management/)工具定期 reload 的主機上，規則被清掉之後直連就重新開著而沒有告警。實測的指令、輸出與 after.rules 的整份清單寫法見 [ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑](/devops/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/) 與 [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/devops/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/)；各種限制寫法的取捨見 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/devops/infra/03-network-foundation/origin-host-firewall/) 的〈Docker 發佈的連接埠：封包路徑與限制的寫法〉。
