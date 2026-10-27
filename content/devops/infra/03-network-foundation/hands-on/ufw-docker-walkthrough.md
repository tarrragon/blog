---
title: "ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑"
date: 2026-10-26
description: "在 Ubuntu 的 ufw 主機上用 Docker 發佈連接埠、想只放行 Cloudflare 的位址、或想限制容器送出的 DNS 查詢時，查 ufw 規則對發佈連接埠的效果、DOCKER-USER 規則在 reload 與重開機之後還在不在、IPv6 那一份發佈由誰接收，以及 compose 容器的 DNS 封包從哪裡送出"
weight: 2
tags: ["infra", "network", "firewall", "ufw", "docker", "dns", "hands-on"]
aliases: ["/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/"]
---

> **事件說明**：2026-10-26，在本機 macOS 的 OrbStack 2.2.5 建的一台 Ubuntu 24.04.5 機器上實測（Arm 架構，核心是 OrbStack 自己的 `7.2.12-orbstack`，有 systemd、可以重開機）。ufw 0.36.2，iptables 1.8.10（nf_tables 後端），Docker CE 29.9.2 從 Docker 官方的 apt 套件庫安裝，測試容器是 `busybox:1.37`。機器的 DNS 解析器是 OrbStack 提供的 `0.250.250.200`。

這篇記錄在一台用 ufw 的 Ubuntu 主機上，Docker 發佈的連接埠跟 ufw 規則之間的關係：用兩個 network namespace 模擬位址在 Cloudflare 範圍內與範圍外的來源、ufw 的入站規則與 route 規則對發佈連接埠的效果、FORWARD 鏈裡 Docker 與 ufw 的跳轉順序、`DOCKER-USER` 規則在 `ufw reload`、ufw 關閉再開啟、Docker 重啟與重開機之後還在不在、寫進 `/etc/ufw/after.rules` 讓規則開機時載入的做法與這個檔案對非 ASCII 字元的限制、`-p` 發佈在 IPv6 的那一份由 docker-proxy 接收而受 ufw 入站規則管、compose 自訂網路的容器經由 Docker 內建解析器 `127.0.0.11` 查詢時封包由主機送出，以及清理。為什麼要只放行 CDN 的位址、各種限制寫法的取捨，寫在概念文章 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/devops/infra/03-network-foundation/origin-host-firewall/)；firewalld 主機上的同一組實測在 [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/devops/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/)，Podman 與 rootless Docker 在 [Podman 與 rootless Docker 發佈連接埠的實測紀錄：rootful Podman 在 ufw 與 firewalld 上的轉送路徑、rootless Docker 與 rootless Podman 由主機程式接收的連接埠與容器看到的來源位址](/devops/infra/03-network-foundation/hands-on/podman-rootless-ports-walkthrough/)。

## 前置條件：Ubuntu 主機、ufw 與 Docker

- **一台有 systemd、可以重開機的 Ubuntu 主機，有 sudo**：雲端 VM、本機 VM 或 OrbStack、Multipass 這類工具建的機器都行。Oracle Cloud 的 Ubuntu 平台映像例外：Oracle 的〈Images〉寫明不要在上面用 ufw 改規則，可能讓主機開不了機，見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/devops/infra/cloud-providers/vm-options/networking/) 的〈防火牆規則的位置與合併方式〉。這次用 OrbStack 是因為免費、建與刪都在一分鐘內，代價是核心是 OrbStack 自己編的版本、不是 Ubuntu 的映像核心；下文量到的是 iptables、ufw 與 Docker 的行為，它們在 Ubuntu 的映像核心上的差異沒有比較。建法是 `orb create ubuntu:noble verify-ufw`，之後用 `orb -m verify-ufw sudo bash` 進 root shell。
- **登入路徑跟要測的連接埠分開**：測試只動 8080、8081 與 IPv6 的 8081。用 SSH 登入雲端主機時，啟用 ufw 之前先 `ufw allow 22/tcp`（或只放行自己的位址），否則 `ufw enable` 之後連線會斷；OrbStack 經由自己的通道進機器，不受 ufw 影響。
- **ufw 與 Docker**：

  ```bash
  apt-get update
  apt-get install -y ufw iproute2 iptables conntrack dnsutils curl
  # Docker 官方的 apt 套件庫，步驟見 docs.docker.com 的〈Install Docker Engine on Ubuntu〉
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  docker pull busybox:1.37
  ```

  `docker-ce` 帶 systemd 的 unit，裝好就由 systemd 執行並設成開機啟動。Ubuntu 自己的 `docker.io` 套件版本較舊，Docker 寫防火牆規則的方式依版本而變（28.0.0 改過發佈在 127.0.0.1 的連接埠對同網段主機的可達性），沒有比較。
- **暫存目錄用 `verify-` 開頭，放在 `/var/tmp`**：這台機器的 `/tmp` 是 tmpfs（`findmnt /tmp` 的 `FSTYPE` 欄是 `tmpfs`），重開機就清空；`/var/tmp` 在磁碟上，重開機後還在。這次第一輪把網頁檔放在 `/tmp/verify-fw/www`，重開機之後容器自動重新啟動時，Docker 發現 bind mount 的來源目錄不存在，替它建了一個空目錄，httpd 找不到 `index.html` 而回 404。

## 共用的函式與兩個測試來源

下文的指令都在同一個 root shell 裡跑。`ns_setup` 建兩個 [network namespace](/devops/infra/knowledge-cards/network-namespace/)：`verify-cf` 的位址 `173.245.48.10` 落在 Cloudflare 的 `173.245.48.0/20`，`verify-other` 的 `203.0.113.10` 是文件保留位址、不在任何 Cloudflare 範圍。兩者各用一對 veth 接到主機，對主機的 IP 發連線，封包從主機的 veth 介面進來，經過的防火牆路徑跟從網卡進來的相同。`probe <連接埠>` 讓兩個來源各連一次。

```bash
HOSTIP=$(ip -4 -br a show eth0 | awk '{print $3}' | cut -d/ -f1)   # 主機主要網卡的位址；網卡名不是 eth0 時換掉
ns_setup() {
  ip netns add verify-cf; ip netns add verify-other
  ip link add vcf-h type veth peer name vcf-n netns verify-cf
  ip link add voth-h type veth peer name voth-n netns verify-other
  ip addr add 192.0.2.1/32 dev vcf-h; ip link set vcf-h up
  ip addr add 192.0.2.5/32 dev voth-h; ip link set voth-h up
  ip route add 173.245.48.10/32 dev vcf-h; ip route add 203.0.113.10/32 dev voth-h
  ip -n verify-cf addr add 173.245.48.10/32 dev vcf-n; ip -n verify-cf link set vcf-n up; ip -n verify-cf link set lo up
  ip -n verify-cf route add 192.0.2.1/32 dev vcf-n; ip -n verify-cf route add default via 192.0.2.1 dev vcf-n
  ip -n verify-other addr add 203.0.113.10/32 dev voth-n; ip -n verify-other link set voth-n up; ip -n verify-other link set lo up
  ip -n verify-other route add 192.0.2.5/32 dev voth-n; ip -n verify-other route add default via 192.0.2.5 dev voth-n
}
probe() {  # probe <連接埠>：兩個來源各連一次 http://$HOSTIP:<連接埠>/，5 秒逾時
  for ns in verify-cf verify-other; do
    out=$(ip netns exec $ns curl -sS -m 5 -o /dev/null -w '%{http_code}' http://$HOSTIP:$1/ 2>&1); rc=$?
    printf '  %-13s -> :%s  rc=%s  %s\n' "$ns" "$1" "$rc" "$(echo "$out" | tail -1)"
  done
}
ns_setup
sysctl -w net.ipv4.ip_forward=1
```

`192.0.2.1` 與 `192.0.2.5` 是主機這一端的位址，只當兩個 namespace 的閘道。namespace 連主機本身的程式（8080）屬於主機自己接收，不需要轉送；連 Docker 發佈的連接埠時，封包被改寫成容器位址之後要由主機轉送到容器網路，`ip_forward=1` 管的是這一段，Docker 啟動時也會把它設成 1。`probe` 的輸出有三種讀法：`rc=0  200` 是連上並拿到回應；`rc=7` 是主機立即回拒；`rc=28  000` 是封包被丟棄、5 秒內沒有回應。namespace 與 veth 在重開機之後消失，`HOSTIP` 與兩個函式只存在這個 shell 裡：重開機或換一個 shell 之後，重新貼一次上面整個區塊（它會重新定義函式並重建 namespace）。

量 IPv6 的那幾節另外替兩個來源各加一個 IPv6 位址，並在主機的 `lo` 上加一個測試用的 IPv6 位址（ULA，`fd00::/8` 裡只在本地使用的位址）當連線目標。`verify-cf` 用 Cloudflare `2606:4700::/32` 裡的 `2606:4700::10`，`verify-other` 用文件保留的 `2001:db8::10`：

```bash
HOST6=fd00:beef::1
ns_setup6() {
  ip -6 addr add $HOST6/128 dev lo
  ip -n verify-cf addr add 2606:4700::10/128 dev vcf-n; ip -n verify-other addr add 2001:db8::10/128 dev voth-n
  sleep 3                                                    # 等 veth 的 link-local 位址生效
  ip -6 route add 2606:4700::10/128 dev vcf-h; ip -6 route add 2001:db8::10/128 dev voth-h
  ip -n verify-cf -6 route add default via $(ip -6 -br a show vcf-h | grep -o 'fe80::[^/]*') dev vcf-n
  ip -n verify-other -6 route add default via $(ip -6 -br a show voth-h | grep -o 'fe80::[^/]*') dev voth-n
}
probe6() {  # probe6 <連接埠>：兩個來源各經由 IPv6 連一次 http://[$HOST6]:<連接埠>/
  for ns in verify-cf verify-other; do
    out=$(ip netns exec $ns curl -sS -m 5 -o /dev/null -w '%{http_code}' "http://[$HOST6]:$1/" 2>&1); rc=$?
    printf '  %-13s -> [%s]:%s  rc=%s  %s\n' "$ns" "$HOST6" "$1" "$rc" "$(echo "$out" | tail -1)"
  done
}
ns_setup6
```

兩個 namespace 的預設路由指向主機那一端 veth 的 link-local 位址（`fe80::` 開頭，介面啟用後幾秒才生效）。重開機之後 `ns_setup` 與 `ns_setup6` 都要重跑。

主機上聽 8080 的程式代表直接跑在主機上的網站，聽 8081 的容器代表 Docker 發佈的網站：

```bash
mkdir -p /var/tmp/verify-fw/www; echo ok > /var/tmp/verify-fw/www/index.html
python3 -m http.server 8080 --directory /var/tmp/verify-fw/www >/var/tmp/verify-fw/http8080.log 2>&1 &
docker run -d --name verify-web --restart unless-stopped -p 8081:80 \
  -v /var/tmp/verify-fw/www:/www:ro busybox:1.37 httpd -f -p 80 -h /www
```

`--restart unless-stopped` 讓容器在 Docker 重啟與重開機之後自己起來，重開機那幾步要靠它。

## ufw 的入站規則與 route 規則對發佈連接埠的效果

ufw 預設拒絕入站，只放行 Cloudflare 的一段到 8080 與 8081：

```bash
ufw default deny incoming; ufw default allow outgoing
ufw allow from 173.245.48.0/20 to any port 8080 proto tcp
ufw allow from 173.245.48.0/20 to any port 8081 proto tcp
ufw --force enable
ufw status verbose
probe 8080; probe 8081
iptables -S FORWARD | grep -- '-j'
```

```text
Default: deny (incoming), allow (outgoing), deny (routed)
8080/tcp                   ALLOW IN    173.245.48.0/20
8081/tcp                   ALLOW IN    173.245.48.0/20
  verify-cf     -> :8080  rc=0  200
  verify-other  -> :8080  rc=28  000
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=0  200
-A FORWARD -j DOCKER-USER
-A FORWARD -j DOCKER-FORWARD
-A FORWARD -j ufw-before-logging-forward
-A FORWARD -j ufw-before-forward
-A FORWARD -j ufw-after-forward
-A FORWARD -j ufw-after-logging-forward
-A FORWARD -j ufw-reject-forward
-A FORWARD -j ufw-track-forward
```

主機上的 8080 只有 Cloudflare 那一段連得到，範圍外的來源被丟棄（逾時）：ufw 的入站規則管的是 input 路徑，也就是目的地是主機本身程式的封包。容器的 8081 兩個來源都連得到：Docker 在封包剛進主機時把目的地改寫成容器（[DNAT](/devops/infra/knowledge-cards/dnat/)），封包變成要由主機轉出到另一個介面的轉送路徑，不經過 ufw 的入站規則。兩條路徑的分岔與各自的限制寫法，在概念文章 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/devops/infra/03-network-foundation/origin-host-firewall/) 的〈Docker 發佈的連接埠：封包路徑與限制的寫法〉。`ufw status` 列的 8081 規則對它沒有作用。

轉送路徑上 ufw 也有規則：`ufw route` 寫的規則放在 `ufw-user-forward`，封包經過 `ufw-before-forward` 時跳轉（jump）進這條鏈比對，而預設的 `deny (routed)` 是 FORWARD 鏈的預設政策 DROP。試著用 route 規則擋 8081 與容器的 80：

```bash
ufw route deny proto tcp from any to any port 80
ufw route deny proto tcp from any to any port 8081
ufw reload
probe 8081
```

```text
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=0  200
```

兩條 route 規則都沒有效果。原因在上面那份跳轉順序：FORWARD 鏈開頭是 Docker 的 `DOCKER-USER` 與 `DOCKER-FORWARD`，`DOCKER-FORWARD` 接受送往發佈連接埠的連線，封包在跳到任何 `ufw-*` 鏈之前就被接受，ufw 的 route 規則與 FORWARD 的預設 DROP 都輪不到它。測完刪掉這兩條：

```bash
ufw route delete deny proto tcp from any to any port 80
ufw route delete deny proto tcp from any to any port 8081
```

刪除的語法是 `ufw route delete <規則>`；寫成 `ufw delete route deny …` 時 ufw 回 `ERROR: Invalid syntax`、規則沒有刪掉。

## DOCKER-USER 規則的效果，以及它在 ufw reload、Docker 重啟與重開機之後的存續

[`DOCKER-USER`](/devops/infra/knowledge-cards/docker-user/) 排在 FORWARD 鏈最前面，裡面的規則由使用者寫。封包到這裡時目的地已經改成容器的 80，所以比對 [conntrack](/devops/infra/knowledge-cards/conntrack/)（連線追蹤）記下的原始目的連接埠 8081：

```bash
iptables -I DOCKER-USER -p tcp -m conntrack --ctorigdstport 8081 --ctdir ORIGINAL ! -s 173.245.48.0/20 -j DROP
probe 8081
```

```text
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=28  000
```

範圍外的來源被擋下，`DROP` 讓它等到逾時；換成 `-j REJECT` 時它會立即收到回拒，這次沒有比較。

這條規則只比對連接埠與來源，發佈的連接埠是 8081 時沒有副作用；換成正式的 80 與 443 時，容器自己往外連 443（呼叫外部 API、ACME 取憑證）的封包，與同一台主機上容器之間連 80 的封包，也會經過 `DOCKER-USER`，原始目的連接埠同樣是 443 或 80，來源是容器位址、不在清單裡，一起被丟掉。補測時把同樣寫法的規則套在 443、80、8081 上，一個 `busybox` 容器 `wget https://www.cloudflare.com/` 與連另一個容器的 80 都以非零結束（出站那一次的訊息是 `download timed out`）；三條規則都加上 `-m conntrack --ctstate DNAT`（只比對經過位址轉換的連線，也就是送往發佈連接埠的那些）之後，兩者恢復，範圍外的來源連 8081 仍然逾時：

```bash
iptables -I DOCKER-USER -p tcp -m conntrack --ctstate DNAT --ctorigdstport 443 --ctdir ORIGINAL ! -s 173.245.48.0/20 -j DROP
```

另一種限定法是加 `-i <對外的網卡>`，只比對從外面進來的封包，補測時同樣讓容器的出站恢復；這次的測試來源從 veth 進來，`-i eth0` 時範圍外的來源是否仍被擋，沒有量到。下文的規則以 8081 實測，正式設定換成 80、443 時都加 `--ctstate DNAT`。這裡只放行 Cloudflare 的一段，正式設定時對整份清單各寫一條 `-s … -j RETURN` 的自建鏈，寫法在 [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/devops/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/) 的〈DOCKER-USER 鏈的限制效果與規則的存續〉。接著依序做四個會重建防火牆規則的動作，每做完一個就看一次規則與結果：

```bash
ufw reload;                    iptables -S DOCKER-USER; probe 8081
ufw disable; ufw --force enable; iptables -S DOCKER-USER; probe 8081
systemctl restart docker;      iptables -S DOCKER-USER; probe 8081
reboot                         # OrbStack 在本機跑 orb restart verify-ufw；開機後重新貼〈共用的函式與兩個測試來源〉的區塊
iptables -S DOCKER-USER; probe 8081
```

| 動作                       | `DOCKER-USER` 裡的規則 | 範圍外的來源連 8081 |
| -------------------------- | ---------------------- | ------------------- |
| `ufw reload`               | 還在                   | 逾時                |
| `ufw disable` 再 enable    | 還在                   | 逾時                |
| `systemctl restart docker` | 還在                   | 逾時                |
| 重開機                     | 不在（只剩空的鏈）     | 200                 |

ufw 重新載入時只重建自己的 `ufw-*` 鏈，不碰 Docker 的鏈；Docker 重啟時保留 `DOCKER-USER` 的內容。iptables 指令加的規則只存在執行中的核心裡，重開機之後就不在，範圍外的來源又連得到。重開機那一列實測用的是 `orb restart verify-ufw`。

## 讓規則開機時載入：寫進 /etc/ufw/after.rules

ufw 啟動時會依序套用 `/etc/ufw/before.rules`、使用者規則與 `/etc/ufw/after.rules`，三個檔案是 `iptables-restore` 的格式。在 `after.rules` 結尾加一段 `*filter` 區塊，宣告 `DOCKER-USER` 鏈並寫規則，ufw 每次啟動與重新載入時都會寫入這條規則：

```bash
cp /etc/ufw/after.rules /var/tmp/verify-fw/after.rules.orig
cat >> /etc/ufw/after.rules <<'EOF'

# verify-ufw: published 8081 only from one Cloudflare range
*filter
:DOCKER-USER - [0:0]
-A DOCKER-USER -p tcp -m conntrack --ctorigdstport 8081 --ctdir ORIGINAL ! -s 173.245.48.0/20 -j DROP
COMMIT
EOF
iptables -F DOCKER-USER     # 沒有做〈DOCKER-USER 規則的效果…〉那一節的重開機時，清掉手動加的那一條；宣告這條鏈本身也會清空它，這一行可以省略
ufw reload
iptables -S DOCKER-USER; probe 8081
```

`ufw reload` 之後規則在、範圍外的來源逾時；`systemctl restart docker` 之後也一樣。

`:DOCKER-USER - [0:0]` 這一行宣告這條鏈：鏈不存在時建出來（ufw 開機時比 Docker 先啟動，這時鏈還不存在），鏈已經存在時（Docker 建好的）清空它的內容，再寫入檔案裡的規則。所以上面的 `iptables -F` 可以省略。宣告會清空這條鏈，帶來一個副作用，另外量過一次：先用 `iptables -I` 在 `DOCKER-USER` 加一條別的規則，再寫進這段、`ufw reload`，那一條就不在了，鏈裡只剩 after.rules 寫的。所以同一台主機上用 after.rules 時，`DOCKER-USER` 的其他規則（包括下文 DNS 那一節用 `iptables -I` 加的）也要寫進同一段，否則下一次 `ufw reload` 就被清掉。

反方向也量過：從 after.rules 刪掉這一段再 `ufw reload`，鏈裡的規則還在（ufw 不再宣告這條鏈，就不動它），要再 `iptables -D` 或重開機才消失（依 iptables 規則只存在執行中的核心推論，`iptables -D` 與重開機這兩項沒有量）。

重開機之後（OrbStack 用 `orb restart verify-ufw`，雲端主機用 `reboot`），重新貼〈共用的函式與兩個測試來源〉的區塊，再看：

```bash
iptables -S DOCKER-USER; iptables -S FORWARD | grep -- '-j' | head -2
probe 8081
systemctl show -p ActiveEnterTimestampMonotonic ufw docker
```

```text
-N DOCKER-USER
-A DOCKER-USER ! -s 173.245.48.0/20 -p tcp -m conntrack --ctorigdstport 8081 --ctdir ORIGINAL -j DROP
-A FORWARD -j DOCKER-USER
-A FORWARD -j DOCKER-FORWARD
  verify-cf     -> :8081  rc=0  404
  verify-other  -> :8081  rc=28  000
ActiveEnterTimestampMonotonic=86988488358
ActiveEnterTimestampMonotonic=86990212381
```

規則在，範圍外的來源被擋。兩個時間戳是 ufw 與 docker 兩個 unit 進入 active 的時間（開機後的微秒數），ufw 先、Docker 後：開機時 ufw 先建出 `DOCKER-USER` 並寫入規則，Docker 啟動時沿用這條已經存在的鏈、不清它的內容，再把兩條跳轉插到 FORWARD 最前面。範圍內的來源回 404 是實測時網頁目錄放在 `/tmp`、重開機後變成空的（〈前置條件〉的暫存目錄那一項），連線本身送到了容器；下面整份清單那一次放在 `/var/tmp`，重開機之後是 200。

### 整份 Cloudflare 清單：IPv4 寫進 after.rules、IPv6 用 ufw 的入站規則

上面那段只放行一個位址段。正式設定時，IPv4 那一份（走轉送路徑）把整份清單寫成一條自建鏈放進 after.rules；IPv6 那一份由 docker-proxy 接收、走 input 路徑（見〈IPv6 那一份發佈：docker-proxy 的接收路徑與 ufw 入站規則的效果〉），用 ufw 的入站規則對每一段放行。先把上面那段從 after.rules 拿掉（`cp /var/tmp/verify-fw/after.rules.orig /etc/ufw/after.rules`），再：

```bash
D=/var/tmp/verify-fw
curl -sSf https://www.cloudflare.com/ips-v4 -o $D/ips-v4
curl -sSf https://www.cloudflare.com/ips-v6 -o $D/ips-v6
{
  echo
  echo '# verify-ufw: Docker published port 8081, Cloudflare IPv4 ranges only'
  echo '*filter'
  echo ':DOCKER-USER - [0:0]'
  echo ':CF-ONLY - [0:0]'
  while read -r n || [ -n "$n" ]; do [ -n "$n" ] && echo "-A CF-ONLY -s $n -j RETURN"; done < $D/ips-v4
  echo '-A CF-ONLY -j DROP'
  echo '-A DOCKER-USER -p tcp -m conntrack --ctstate DNAT --ctorigdstport 8081 --ctdir ORIGINAL -j CF-ONLY'
  echo 'COMMIT'
} >> /etc/ufw/after.rules
ufw reload
while read -r n || [ -n "$n" ]; do [ -n "$n" ] && ufw allow proto tcp from "$n" to any port 8081 >/dev/null; done < $D/ips-v6
grep -c . $D/ips-v4; iptables -S CF-ONLY | grep -c RETURN
grep -c . $D/ips-v6; ufw status | grep '8081.*ALLOW' | grep -c '::'
probe 8081
```

```text
15
15
7
7
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=28  000
```

封包進到 `DOCKER-USER`、連線經過位址轉換而原始目的連接埠是 8081 時跳到 `CF-ONLY`（實測那一次的跳轉沒有 `--ctstate DNAT`，加上它的效果是〈DOCKER-USER 規則的效果…〉量的那一組）：來源落在清單的任一段就 `RETURN` 回 `DOCKER-USER`，接著由 Docker 的 `DOCKER-FORWARD` 放行；全部不符時落到最後的 `DROP`。`8081` 換成自己發佈的連接埠，每個連接埠在 `DOCKER-USER` 寫一行跳轉、在 ufw 寫一組放行。

兩組計數要對得上：`grep -c .` 數清單的段數，另一個數實際寫進去的規則數。實測那一次是在一台新開的 ufw 上量，ufw 裡只有 IPv6 的那 7 條放行，計數用的是 `ufw status | grep -c '8081.*ALLOW'`；照本文從前面幾節做下來時，ufw 裡還有一條 IPv4 的 `173.245.48.0/20` 放行，上面的區塊因此只數來源帶 `::` 的那幾條，這個寫法沒有照這個形式跑過。`CF-ONLY` 那一行只數 `RETURN`，鏈裡另外還有最後一條 `DROP`。Cloudflare 這兩份清單的最後一行沒有換行字元，`while read -r n` 單獨寫時讀不到最後一行、也不報錯，第一次實測時 IPv4 少了 `131.0.72.0/22`、IPv6 少了 `2c0f:f248::/32`，被漏掉的位址段回源時會被擋下；`|| [ -n "$n" ]` 讓迴圈也處理沒有換行結尾的最後一行。

用〈共用的函式與兩個測試來源〉的 `ns_setup6` 加好 IPv6 位址之後，`probe6 8081` 也只有 `verify-cf` 拿到 200。重開機之後重新貼函式的區塊再量一次，IPv4 的 15 條 `RETURN` 還在，`probe 8081` 與 `probe6 8081` 的結果都跟上面相同（IPv6 那一份量的是連線結果，沒有再數規則）。Cloudflare 的清單更新時，重抓兩份清單、把 after.rules 裡這一段換成新產生的內容再 `ufw reload`，IPv6 那一份另外用 `ufw delete` 刪掉不在新清單裡的段；這個更新流程沒有實跑。

after.rules 裡的非 ASCII 字元，會讓 ufw 在重寫規則檔時中止。第一次寫進去的註解是「`# verify-ufw：Docker 發佈的 8081 …`」，`ufw reload` 照常，而改預設政策時失敗。下面的指令是那一次的紀錄；照本文用 ASCII 註解時，這條指令會成功、把 routed 政策改成 ACCEPT，所以不必照跑，跑了的話以 `ufw default deny routed` 改回：

```bash
ufw default allow routed; echo "exit=$?"
grep DEFAULT_FORWARD_POLICY /etc/default/ufw; iptables -S FORWARD | head -1
```

```text
UnicodeEncodeError: 'ascii' codec can't encode character '\uff1a' in position 12: ordinal not in range(128)
exit=1
DEFAULT_FORWARD_POLICY="ACCEPT"
-P FORWARD DROP
```

`\uff1a` 是全形冒號 `：`，position 12 是從 0 起算，也就是註解的第 13 個字元。ufw 改預設政策時會重寫規則檔，遇到這個字元時 Python 以 ASCII 編碼失敗、以 exit 1 結束。失敗之前 `/etc/default/ufw` 已經改成 `ACCEPT`，執行中的 FORWARD 鏈還是 `DROP`：設定檔與執行中的規則不一致。下一次 `ufw reload` 或重開機時 ufw 會讀設定檔，依這個讀法推論 FORWARD 會變成 `ACCEPT`，沒有實跑。反方向的 `ufw default deny routed` 也以同一個錯誤失敗過（Podman 那一篇實測時遇到）。`after.rules` 本身沒有被截斷（行數與修改時間都沒變）。註解改成 ASCII 之後同一條指令正常完成。檔案裡有沒有非 ASCII 字元，用 `grep -nP '[^\x00-\x7F]' /etc/ufw/*.rules` 查，沒有輸出就是全部 ASCII。

這一步的替代做法：

- **iptables-persistent（netfilter-persistent）**：開機時載入 `iptables-save` 存下的整份規則。Docker 與 ufw 的規則也會一起被存進去，開機時跟 Docker、ufw 自己寫的規則重複載入，順序也可能排在它們之前或之後；這一種沒有實跑。
- **自己的 nftables 表**：寫法與開機載入在 [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/devops/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/) 的〈自己的 nftables 表：掛在目的位址轉換之前〉，那裡量過它在 firewalld 主機上的存續；在 ufw 主機上沒有實跑。ufw 用的是 iptables-nft，自建的 nftables 表跟它並存，ufw reload 時不會被清（依 ufw 只重建自己的鏈推論）。
- **不發佈或只發佈在 `127.0.0.1`**（這一項替代的是整個 `DOCKER-USER` 做法，不只是開機載入）：發佈在 `127.0.0.1` 的連接埠外部來源連不到（firewalld 那一篇在 Docker 29.9.2 上量過），前面的反向代理以主機上的程式執行時，ufw 的入站規則就管得到它；在 ufw 主機上沒有實跑。

## IPv6 那一份發佈：docker-proxy 的接收路徑與 ufw 入站規則的效果

`-p 8081:80` 同時發佈在 IPv4 與 IPv6。容器所在的網路沒有開 IPv6（Docker 預設的 bridge 網路就是）時，IPv6 那一份改由主機上的程式接收：

```bash
ss -ltnp | grep 8081
```

```text
LISTEN 0  4096     0.0.0.0:8081   0.0.0.0:*   users:(("docker-proxy",pid=616,fd=8))
LISTEN 0  4096        [::]:8081      [::]:*   users:(("docker-proxy",pid=622,fd=8))
```

`[::]:8081` 由 docker-proxy 這個主機上的程式（[Userland Proxy](/devops/infra/knowledge-cards/userland-proxy/) 的一種）接聽，它收下連線、再自己連到容器的 IPv4 位址。IPv6 的連線因此送到主機上的程式，走的是 input 路徑。IPv4 的 `0.0.0.0:8081` 也由 docker-proxy 聽著，而外部來的 IPv4 封包在 prerouting 就被 DNAT 改寫成容器位址，到不了它；它接的是不經過 prerouting 的連線，例如主機本機連 `127.0.0.1:8081`（依 Docker 的規則推論，沒有實跑）。用〈共用的函式與兩個測試來源〉的 `ns_setup6` 與 `probe6` 驗證，ufw 預設拒絕入站、沒有任何 IPv6 的放行規則時：

```bash
probe6 8081
```

```text
  verify-cf     -> [fd00:beef::1]:8081  rc=28  000
  verify-other  -> [fd00:beef::1]:8081  rc=28  000
```

兩個來源經由 IPv6 都逾時，同一時間經由 IPv4 兩個都拿到 200：IPv6 那一份受 ufw 的入站規則管，跟 IPv4 那一份相反。加上 Cloudflare `ips-v6` 每一段的放行之後只有 `verify-cf` 拿到 200（指令與計數的對帳在〈整份 Cloudflare 清單：IPv4 寫進 after.rules、IPv6 用 ufw 的入站規則〉）。第一輪另用一個只有一個來源的 namespace 量過加上與刪掉一條 IPv6 放行規則的前後，三次是逾時、連上（回 404，網頁目錄放在 `/tmp` 被清掉，連線送到了容器）、逾時。`ip6tables -S DOCKER-USER` 這時是空的，IPv6 這一路沒有經過它。

這個 IPv4 與 IPv6 分兩套機制的寫法，依賴容器網路沒有開 IPv6：之後有一個網路帶 `--ipv6`（或 daemon 設定的 `default-network-opts` 替新網路開了 IPv6），那個網路上發佈的 IPv6 連接埠就改走 ip6tables 的位址轉換與轉送路徑，ufw 的 IPv6 入站放行對它失效，而 ip6tables 的 `DOCKER-USER` 是空的，沒有任何訊號（依 Docker〈Port publishing〉推論，沒有實跑）。`docker network inspect -f '{{.EnableIPv6}}' <網路名>` 查得到每個網路有沒有開。

這一路的代價在容器看到的來源。補測時 `docker logs verify-web` 記到的兩筆是 `[::ffff:173.245.48.10]`（經由 IPv4、DNAT 轉進來的那一筆）與 `[::ffff:172.17.0.1]`（經由 IPv6、docker-proxy 轉進來的那一筆）：docker-proxy 自己連到容器，容器看到的來源是預設網路的閘道位址，不是 IPv6 的真實來源。容器裡的反向代理依來源位址判斷（例如只信任 Cloudflare 位址段送來的 `CF-Connecting-IP`）時，經由 IPv6 回源的請求不符合條件。

這個結果有兩個條件。一是 docker-proxy 有在執行：`/etc/docker/daemon.json` 寫 `{ "userland-proxy": false }`、重啟 Docker 並重建容器之後，`ss` 只剩 `0.0.0.0:8081`（由 dockerd 聽著），`docker ps` 的 PORTS 欄只有 `0.0.0.0:8081->80/tcp`，`ip6tables -t nat -S DOCKER` 沒有任何轉換規則。在 ufw 停用時跑 `probe6 8081`，兩個來源的 `curl` 都以 exit 7 結束（連線立即被拒）：IPv6 那一份沒有發佈，不是改走別的路徑。二是容器的網路沒有開 IPv6：網路建立時帶 `--ipv6`、容器有 IPv6 位址時，Docker 用 ip6tables 把 IPv6 的連線位址轉換送進容器，那時它跟 IPv4 一樣走轉送路徑、不受 ufw 入站規則管，規則要寫在 ip6tables 的 `DOCKER-USER`；這一種也沒有實跑。

## compose 自訂網路的容器經由 127.0.0.11 查詢時，DNS 封包從哪裡送出

容器送出的 DNS 查詢有兩條路，依容器接在哪一種網路而定：

```bash
mkdir -p /var/tmp/verify-fw/compose
cat > /var/tmp/verify-fw/compose/compose.yaml <<'EOF'
name: verify
services:
  dns:
    image: busybox:1.37
    container_name: verify-dns-compose
    command: sleep infinity
EOF
docker compose -f /var/tmp/verify-fw/compose/compose.yaml up -d
docker run -d --name verify-dns-bridge busybox:1.37 sleep infinity
docker exec verify-dns-bridge grep nameserver /etc/resolv.conf
docker exec verify-dns-compose grep nameserver /etc/resolv.conf
```

```text
nameserver 0.250.250.200
nameserver 127.0.0.11
```

預設 bridge 網路的容器拿到主機 `/etc/resolv.conf` 的副本，直接問主機的解析器；compose 建的自訂網路（`verify_default`）上的容器問的是 `127.0.0.11`，那是 Docker 內建的解析器，它先解析同一個網路裡的服務名稱，其他名稱再往外查。

用 [conntrack](/devops/infra/knowledge-cards/conntrack/) 看往外查的那一筆封包的來源：

```bash
conntrack -F
docker exec verify-dns-compose nslookup -timeout=3 example.org >/dev/null 2>&1
conntrack -L -p udp --dport 53
conntrack -F
docker exec verify-dns-bridge nslookup -timeout=3 example.net >/dev/null 2>&1
conntrack -L -p udp --dport 53
```

```text
udp 17 29 src=192.168.139.162 dst=0.250.250.200 sport=50462 dport=53 src=0.250.250.200 dst=192.168.139.162 ...
udp 17 29 src=172.17.0.3 dst=0.250.250.200 sport=42585 dport=53 src=0.250.250.200 dst=192.168.139.162 ...
```

第一筆是 compose 容器（位址 `172.18.0.2`）的查詢：原始方向的來源是主機自己的 IP（`192.168.139.162` 是這台測試機的位址），代表往外查的封包由主機送出，不是從容器轉送出去的。第二筆是 bridge 容器的：原始來源是容器的 `172.17.0.3`，回程方向的目的地是主機 IP，那是 Docker 的位址偽裝。`conntrack -F` 清空連線追蹤表，讓 `-L` 只列出這一次查詢的那幾筆。

兩條路經過的防火牆位置因此不同。在 `DOCKER-USER` 擋掉容器網路送往解析器以外的 53，再在主機的 OUTPUT 擋掉全部的 53，量各種查詢。`RES` 是容器預設會問的上游解析器：這台機器的 `/etc/resolv.conf` 直接寫著 `0.250.250.200`。Ubuntu 預設的 systemd-resolved 讓 `/etc/resolv.conf` 指向 `127.0.0.53`，容器連不到主機的迴環位址，Docker 那時改把 `/run/systemd/resolve/resolv.conf` 裡的上游清單給容器；照抄下面那一行會取到 `127.0.0.53`，`! -d $RES` 就連 bridge 容器的預設查詢也擋掉。那種主機上改從 `/run/systemd/resolve/resolv.conf` 取，上游有好幾個時每一個各寫一組規則（依 Docker 的行為推論，沒有實跑）：

```bash
RES=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)   # systemd-resolved 主機改讀 /run/systemd/resolve/resolv.conf
q() { docker exec "$1" nslookup -timeout=3 example.com $2 >/dev/null 2>&1; echo "  $1 ${2:-（預設）} rc=$?"; }
qa() { q verify-dns-bridge; q verify-dns-bridge 1.1.1.1; q verify-dns-compose; q verify-dns-compose 1.1.1.1; }
for i in docker0 br-+; do for p in udp tcp; do
  iptables -I DOCKER-USER -i $i -p $p --dport 53 ! -d $RES -j DROP
done; done
qa
iptables -I OUTPUT -p udp --dport 53 -j DROP; iptables -I OUTPUT -p tcp --dport 53 -j DROP
q verify-dns-bridge; q verify-dns-compose
iptables -D OUTPUT -p udp --dport 53 -j DROP; iptables -D OUTPUT -p tcp --dport 53 -j DROP
```

`br-+` 比對所有 `br-` 開頭的介面，compose 建的自訂網路都是這種介面名；`docker0` 是預設網路。`nslookup` 的第二個引數是要問的 DNS 伺服器，沒給時用容器的 `/etc/resolv.conf`。

| 查詢                           | 只有 `DOCKER-USER` 的規則 | 再加主機 OUTPUT 擋 53 |
| ------------------------------ | ------------------------- | --------------------- |
| bridge 容器，用預設的解析器    | 成功                      | 成功                  |
| bridge 容器，直接問 `1.1.1.1`  | 失敗（逾時）              | 沒有量                |
| compose 容器，用 `127.0.0.11`  | 成功                      | 失敗                  |
| compose 容器，直接問 `1.1.1.1` | 失敗（逾時）              | 沒有量                |

右欄的兩格「沒有量」：加了 OUTPUT 規則之後只送了兩種用預設解析器的查詢（上面區塊的 `q` 那一行），直接問 `1.1.1.1` 的兩種在左欄已經被 `DOCKER-USER` 擋下。「失敗」是 `nslookup` 在 3 秒內拿不到回應、以非零結束。

bridge 容器的查詢與 compose 容器直接指定伺服器的查詢，都從容器的介面轉送出去，`DOCKER-USER` 管得到、主機的 OUTPUT 管不到。compose 容器經由 `127.0.0.11` 的查詢由主機送出，只有主機的 OUTPUT 管得到；`DOCKER-USER` 的規則對它沒有作用。所以要讓容器的 DNS 只送往指定的解析器，兩個位置都要寫：`DOCKER-USER`（或自建 nftables 表的 forward 鏈）擋容器直接送出的，主機的出站規則擋內建解析器替它送出的。用 ufw 寫主機的出站規則時，寫法是先 `ufw allow out to <解析器的位址> port 53`、再 `ufw deny out 53`（ufw 依加入順序比對），這兩條沒有實跑，實測用的是上面的 iptables OUTPUT 規則。

這個結果是在主機解析器不是迴環位址（`0.250.250.200`）時量的；systemd-resolved 的主機上內建解析器往外查的封包從哪裡送出，沒有量。

## 清理：容器、ufw 規則、after.rules、namespace 與暫存目錄

```bash
docker rm -f verify-web verify-dns-bridge; docker compose -f /var/tmp/verify-fw/compose/compose.yaml down
pkill -f 'http.server 8080'
cp /var/tmp/verify-fw/after.rules.orig /etc/ufw/after.rules
ufw --force reset            # 回到 ufw 未設定、停用的狀態；主機原本就在用 ufw 時改成逐條 ufw delete
iptables -F DOCKER-USER; iptables -X CF-ONLY   # after.rules 不再宣告之後，鏈裡的規則要手動清（或重開機）
ip link del vcf-h; ip link del voth-h
ip netns del verify-cf; ip netns del verify-other
ip -6 addr del fd00:beef::1/128 dev lo
rm -f /etc/docker/daemon.json; systemctl restart docker   # 做過 userland-proxy 那一項時才需要
rm -rf /var/tmp/verify-fw
find /tmp /var/tmp -maxdepth 1 -name 'verify-*'      # 沒有輸出就清乾淨了
```

實測時 `after.rules` 的備份第一輪放在 `/tmp`、重開機時被清掉，所以還原那一行沒有實跑，改用 `sed -i '/^# verify-ufw/,$d' /etc/ufw/after.rules` 刪掉加上去的那一段（從註解那一行刪到檔尾，前提是那一段加在檔案最後），`grep -c verify /etc/ufw/after.rules` 回 0。`ufw --force reset` 會停用 ufw 並把規則檔備份成帶時間戳的副本，用在專門為實測建的機器上；主機原本有自己的 ufw 規則時，只刪這次加的那幾條（8080、8081 的兩條入站、IPv6 測試段與 `ips-v6` 各段的放行），改過 routed 政策的話以 `ufw default deny routed` 改回。整份清單那一次的清理照這個區塊實跑過，`ip netns list` 沒有輸出、`ufw status` 回 `inactive`、`DOCKER-USER` 只剩空鏈。veth 要在 namespace 之前刪：先刪 namespace 時，接在裡面的那一端消失，整對 veth 跟著不在，之後的 `ip link del` 回 `Cannot find device`（結果一樣乾淨，只是多一行錯誤訊息）。實測的清理在一個 `bash -c '…'` 裡跑時，`pkill -f 'http.server 8080'` 比對到了那個 bash 自己的命令列、把它殺掉，後面的指令都沒有執行；在互動式 shell 裡一行一行貼不會遇到，要寫成腳本時改用 `pkill -f '[h]ttp.server 8080'`，讓比對字串不出現在自己的命令列裡。機器是專為實測建的時，整台刪掉最乾淨：`orb delete verify-ufw`。

## 各寫法在 ufw 主機上的結果

| 寫法                                                | 範圍外的來源連發佈的連接埠（IPv4） | `ufw reload` 之後                        | Docker 重啟之後 | 重開機之後           |
| --------------------------------------------------- | ---------------------------------- | ---------------------------------------- | --------------- | -------------------- |
| ufw 入站規則（`ufw allow from … to any port 8081`） | 連得到（管不到轉送路徑）           | 沒有單獨測                               | 沒有單獨測      | 沒有測               |
| ufw route 規則（`ufw route deny`）                  | 連得到（排在 Docker 的鏈之後）     | 連得到                                   | 沒有測          | 沒有測               |
| iptables 指令加進 `DOCKER-USER`                     | 被擋（逾時）                       | 規則還在（after.rules 沒有宣告這條鏈時） | 規則還在        | 規則不在             |
| 寫進 `/etc/ufw/after.rules`                         | 被擋（逾時）                       | 規則還在                                 | 規則還在        | 規則還在             |
| IPv6 那一份：ufw 入站規則只放行 `ips-v6`            | 被擋（逾時，經由 IPv6 連）         | 沒有單獨測                               | 沒有測          | 被擋（沒有再數規則） |

第二欄是規則剛套上時，範圍外的來源經由 IPv4（最後一列經由 IPv6）連發佈的連接埠的結果；後三欄是做完那個動作之後規則還在不在。「沒有單獨測」是那個動作做過、但這條規則不是當時要量的對象（例如量 `DOCKER-USER` 時順帶 reload 過），沒有記錄它的狀態；「沒有測」是沒有做那個動作。
