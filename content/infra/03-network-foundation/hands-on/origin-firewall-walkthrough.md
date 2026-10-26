---
title: "源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS"
date: 2026-10-25
description: "要在 Linux 主機上設定只放行 Cloudflare 位址的防火牆、確認 Docker 發佈的連接埠有沒有繞過 firewalld、在 DOCKER-USER、StrictForwardPorts 與 nftables 表之間選一種限制容器的來源、或限制出站 DNS 時，查 Oracle Linux 10 上實際跑過的指令、輸出，以及規則在重新載入、dockerd 重啟與重開機之後還在不在"
weight: 1
tags: ["infra", "network", "firewall", "firewalld", "nftables", "docker", "cloudflare", "hands-on"]
---

> **事件說明**：2026-10-25，在 Oracle Cloud `ap-batam-1` 區域的一台 A1 主機（Arm 架構，Oracle Linux 10.2，核心 `6.12.0-207.111.5.1.el10uek.aarch64`，1 OCPU、6 GB）上實測。主機在私有 subnet、沒有公開 IP，管理員經由 Oracle Cloud Bastion 的 port forwarding session 登入（建法見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/)）。firewalld 2.4.3、nftables 後端、預設 zone `public`，`public` zone 只開 `ssh` 與 `dhcpv6-client`；Docker 用官方的靜態二進位檔 29.9.2（iptables 後端），測試容器是 `busybox:1.37`。2026-10-26 另在本機 OrbStack 2.2.5 建的一台 Oracle Linux 10.2 機器上（核心是 OrbStack 的 `7.2.12-orbstack`，firewalld 2.4.3 nftables 後端、Docker CE 29.9.2 以套件安裝、由 systemd 執行）測了 zone 的 sources、IPv6、daemon 的 `ip` 設定、policy 上的 forward-port、本機 forward-port，以及 reload 清掉 `DOCKER-USER` 的條件。OrbStack 的核心是它自己編的版本，量到的是 firewalld、iptables-nft、nftables 與 Docker 這幾個使用者層程式的行為，跟 Oracle Linux 映像核心的差異沒有比較。

這篇記錄在一台 Linux 主機上驗證「源站只放行 Cloudflare 的位址」這類防火牆規則的過程：用兩個 network namespace 模擬位址在 Cloudflare 範圍內與範圍外的兩個來源、firewalld 以 ipset 與 rich rule 只放行 Cloudflare 位址到主機本身的程式、Docker 發佈的連接埠不受這條規則約束、[`DOCKER-USER`](/infra/knowledge-cards/docker-user/) 鏈的規則在 dockerd 重啟之後還在、在 `firewall-cmd --reload` 之後是否消失取決於 firewalld 的後端與主機有沒有 direct 設定（iptables 後端時一律清掉；nftables 後端時看有沒有 direct rule 或 passthrough，OCI 的 Oracle Linux 映像自帶 passthrough）、firewalld policy 擋不到發佈的連接埠與它的原因、`StrictForwardPorts=yes` 只管得到連接埠、掛在目的位址轉換之前的 nftables 表與它的開機載入、出站 DNS 只准送往 VCN 解析器的 policy 對主機與容器的不同效果、清理，以及各寫法在 reload、dockerd 重啟與重開機之後的對照表。每一種限制寫法的機制與取捨寫在概念文章 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/infra/03-network-foundation/origin-host-firewall/)，這裡不重寫。這篇沒有用到 Cloudflare 帳號，也沒有讓 Cloudflare 實際回源：防火牆比對的只有來源位址，所以用 Cloudflare 位址段裡的一個位址當來源，就能驗證規則。Cloudflare 回源時實際用的位址、Authenticated Origin Pulls、Worker 與 Tunnel，接上實際的 Cloudflare 帳號量在 [Cloudflare 回源的實測紀錄：Oracle Cloud NSG 只放行 Cloudflare 位址與規則數上限、回源的來源位址、Authenticated Origin Pulls、Worker 偽造 CF-Connecting-IP 與 Tunnel 的出站連接埠](/infra/03-network-foundation/hands-on/cloudflare-origin-pull-walkthrough/)。

## 前置條件：主機、登入方式與測試檔案

- **一台跑 firewalld 的 Linux 主機，有 sudo**：指令以 Oracle Linux 10 與 firewalld 的 nftables 後端寫成。`firewall-cmd --state` 回 `running`、`sudo grep FirewallBackend /etc/firewalld/firewalld.conf` 回 `nftables` 才跟這次相同。主機上要有 `curl`、`dig`（套件 `bind-utils`）、`python3`、`iptables`（套件 `iptables-nft`）與 `nft`，`command -v curl dig python3 iptables nft` 印得出五個路徑就齊了；這台的平台映像都已經裝好。用 `ufw` 的主機（Ubuntu）上，Docker 發佈的連接埠同樣繞過 ufw，規則在 `ufw reload` 與重開機之後的存續、寫進 `/etc/ufw/after.rules` 的做法，記在 [ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑](/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/)。
- **登入路徑跟要測的連接埠分開**：這次經由 Bastion 連 SSH 的連接埠 22，測試只改動 8080 到 8083，`public` zone 的 `ssh` 沒有動，規則寫錯也不會把自己鎖在外面。主機有公開 IP、從網際網路直接 SSH 時，同樣只動測試用的連接埠。
- **Docker 與測試映像**：這台主機在私有 subnet，只有連到 Oracle 服務的 service gateway，連不到 `download.docker.com` 與 Docker Hub。所以在本機下載靜態二進位檔、匯出映像與 Cloudflare 的位址清單，再傳上主機：

  ```bash
  curl -sSfLO https://download.docker.com/linux/static/stable/aarch64/docker-29.9.2.tgz
  docker pull --platform linux/arm64 busybox:1.37 && docker save busybox:1.37 -o busybox-1.37.tar
  curl -s https://www.cloudflare.com/ips-v4 > cf-ips-v4.txt
  ssh -F <ssh 設定檔> <主機的 Host 名稱> 'mkdir -p /tmp/verify-fw'
  scp -F <ssh 設定檔> docker-29.9.2.tgz busybox-1.37.tar cf-ips-v4.txt <主機的 Host 名稱>:/tmp/verify-fw/
  ```

  `aarch64` 對應 A1 這種 Arm 主機，x86 主機換成 `x86_64`，`--platform` 換成 `linux/amd64`；`29.9.2` 是 2026-10-25 時 `stable/aarch64/` 目錄裡最新的版本，照抄之前先打開那個目錄看一次。`<ssh 設定檔>` 是寫了 `ProxyJump` 經由 Bastion 的 ssh 設定（寫法在上面那篇 Oracle Cloud 實測紀錄的〈建 port forwarding session 並經由本機的轉送登入〉），`<主機的 Host 名稱>` 是那份設定裡主機的 `Host`。約 82 MB 的檔案經由 Bastion 傳了約 5 分鐘（本機計時，依本機的上行頻寬與 Bastion 而變）。`cf-ips-v4.txt` 在 2026-10-25 是 15 段 IPv4，最後一行沒有換行（`wc -l` 回 14）；清單會變，每次照著做時重抓。
- **主機連得到網際網路時改用套件安裝**：加 Docker 的 RHEL 套件庫再 `dnf install docker-ce`。Docker 寫防火牆規則的行為由 dockerd 決定，跟安裝方式無關；差別在套件版附 systemd 的 unit，裝好就由 systemd 執行 dockerd，下文 `start_dockerd` 與 `restart_dockerd` 裡的 `nohup dockerd` 與 `pkill -x dockerd` 要換成 `systemctl start docker` 與 `systemctl restart docker`（unit 帶 socket 啟用與自動重啟，`pkill` 之後 dockerd 會被拉起來），重開機之後 dockerd 也會自動啟動。這一段依套件的安裝方式推論，沒有實跑。
- **暫存目錄用 `verify-` 開頭**：測完一條 `find /tmp /var/tmp -maxdepth 1 -name 'verify-*'` 就查得出有沒有漏清的檔案。這台的 `/tmp` 在重開機之後還在；`/tmp` 是 tmpfs 的主機（Fedora、Debian 13 這類）重開機會清空它，那時把下文的 `D` 改成 `/var/tmp/verify-fw`，傳檔的目的地也跟著改。

## 共用的變數與函式

下文每一個指令區塊都在主機上同一個 root shell 裡依序執行（`sudo -i` 之後一路跑到清理），變數與函式只存在那個 shell 裡；中途換了 shell 或重開機之後，重新貼一次這個區塊。`HOSTIP` 填主機自己的 IP：`ip -br a` 主要網卡那一行的位址，取斜線之前的部分（`10.0.1.35/24` 填 `10.0.1.35`）。`RESOLVER` 填主機用的 DNS 解析器（`/etc/resolv.conf` 的 `nameserver`），Oracle Cloud VCN 裡是 `169.254.169.254`，只在出站 DNS 那一節用到。

```bash
HOSTIP=<主機的 IP>
RESOLVER=<主機的 DNS 解析器>
D=/tmp/verify-fw
export PATH=$D/docker:$PATH
cd $D
ns_setup() {
  ip netns add verify-cf; ip netns add verify-other
  ip link add vcf-h type veth peer name vcf-n netns verify-cf
  ip link add voth-h type veth peer name voth-n netns verify-other
  ip addr add 192.0.2.1/32 dev vcf-h; ip link set vcf-h up            # 主機這一端的位址，只當 namespace 的閘道
  ip addr add 192.0.2.5/32 dev voth-h; ip link set voth-h up
  ip route add 173.245.48.10/32 dev vcf-h                              # 回給 verify-cf 的封包從 vcf-h 送出
  ip route add 203.0.113.10/32 dev voth-h
  ip -n verify-cf addr add 173.245.48.10/32 dev vcf-n; ip -n verify-cf link set vcf-n up; ip -n verify-cf link set lo up
  ip -n verify-cf route add 192.0.2.1/32 dev vcf-n; ip -n verify-cf route add default via 192.0.2.1 dev vcf-n
  ip -n verify-other addr add 203.0.113.10/32 dev voth-n; ip -n verify-other link set voth-n up; ip -n verify-other link set lo up
  ip -n verify-other route add 192.0.2.5/32 dev voth-n; ip -n verify-other route add default via 192.0.2.5 dev voth-n
}
probe() {  # probe <連接埠>：兩個來源各連一次 http://$HOSTIP:<連接埠>/，-m 5 是 5 秒逾時
  for ns in verify-cf verify-other; do
    out=$(ip netns exec $ns curl -sS -m 5 -o /dev/null -w '%{http_code}' http://$HOSTIP:$1/ 2>&1); rc=$?
    printf '  %-13s -> :%s  rc=%s  %s\n' "$ns" "$1" "$rc" "$out"
  done
}
start_dockerd() {  # 背景啟動 dockerd，等到 docker info 回得了（最多 30 秒）
  nohup dockerd >>$D/dockerd.log 2>&1 &
  for i in $(seq 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
}
restart_dockerd() {  # 停掉 dockerd、等它結束、再啟動，並把測試容器啟動回來
  pkill -x dockerd; while pgrep -x dockerd >/dev/null; do sleep 1; done
  start_dockerd
  docker start verify-web-all verify-web-lo verify-web-v >/dev/null 2>&1; sleep 2
}
```

`docker start` 的三個容器在〈Docker 發佈的連接埠與 firewalld 的規則〉那一節建立，在那之前呼叫 `restart_dockerd` 時這一行什麼都不做。

## 用 network namespace 模擬 Cloudflare 與其他來源

要測「只放行 Cloudflare 的位址」，需要兩個來源：一個的位址在 Cloudflare 的範圍裡，一個不在。`ns_setup` 在主機上建兩個 [network namespace](/infra/knowledge-cards/network-namespace/)（核心裡各自獨立的一套網路介面與路由表），各用一對 veth（成對的虛擬網路介面，從一端送進去的封包從另一端出來）接到主機：`verify-cf` 的位址是 `173.245.48.10`（落在 Cloudflare 的 `173.245.48.0/20`），`verify-other` 的位址是 `203.0.113.10`（RFC 5737 保留給文件用的 TEST-NET-3，不在任何 Cloudflare 範圍）。兩者都對主機的 IP 發連線，封包從主機的 `vcf-h`、`voth-h` 介面進來，經過的防火牆路徑跟從網卡進來的封包相同。

```bash
ns_setup
firewall-cmd --get-zone-of-interface=vcf-h; firewall-cmd --get-default-zone
```

`ns_setup` 只跑一次；namespace 已經存在時再跑會印一串 `File exists`。`--get-zone-of-interface=vcf-h` 回 `no zone`、`--get-default-zone` 回 `public`：veth 介面沒有被指派到任何 zone，firewalld 把它們的流量交給預設 zone 處理，跟主機的網卡同一個 zone。

下文輸出裡的 `10.0.1.35` 是這次那台主機的私有 IP，每段輸出前的 `==` 行是實測時腳本印的說明。`probe` 的輸出有三種讀法：`rc=0  200` 是連上並拿到回應；`rc=7`、`after 0 ms: Could not connect to server` 是主機立即回拒（firewalld 以 ICMP 回拒，或沒有程式在聽）；`rc=28`、`Connection timed out after 5002 milliseconds` 是封包被丟棄、沒有任何回應。連線失敗時 `curl` 另外印一行 `000`（`-w` 印的狀態碼），下文的輸出把那一行省略了。

這一步可以換成實體的兩個來源（另一台主機，或實際讓 Cloudflare 回源），結果相同，因為防火牆只看封包的來源位址（依規則的比對方式推論）；代價是要多一台主機或一個 Cloudflare 帳號，而且一般主機的位址不會落在 Cloudflare 的範圍裡，Cloudflare 位址被放行的情形測不到。

## firewalld 以 ipset 只放行 Cloudflare 位址到主機本身的程式

主機上聽 8080 的程式代表直接跑在主機上的網站程式。還沒加任何規則時，兩個來源都被 `public` zone 回拒：

```bash
nohup python3 -m http.server 8080 --directory $D >$D/http8080.log 2>&1 &
sleep 1; probe 8080
```

```text
== 沒有任何放行 8080 的規則
  verify-cf     -> :8080  rc=7  curl: (7) Failed to connect to 10.0.1.35 port 8080 after 0 ms: Could not connect to server
  verify-other  -> :8080  rc=7  curl: (7) Failed to connect to 10.0.1.35 port 8080 after 0 ms: Could not connect to server
```

把 Cloudflare 的位址段放進一個 ipset，再加一條 rich rule（firewalld 可以同時寫來源、連接埠與動作的規則）放行這個 ipset 到 8080：

```bash
firewall-cmd --permanent --new-ipset=cloudflare-v4 --type=hash:net     # hash:net 存的是位址段
firewall-cmd --permanent --ipset=cloudflare-v4 --add-entries-from-file=$D/cf-ips-v4.txt
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source ipset="cloudflare-v4" port port="8080" protocol="tcp" accept'
firewall-cmd --reload
firewall-cmd --ipset=cloudflare-v4 --get-entries | wc -l
probe 8080
```

```text
15
== 放行 ipset cloudflare-v4 到 8080
  verify-cf     -> :8080  rc=0  200
  verify-other  -> :8080  rc=7  curl: (7) Failed to connect to 10.0.1.35 port 8080 after 0 ms: Could not connect to server
```

ipset 裡是 15 段，跟下載的清單相同。正式設定時把 `8080` 換成 `80` 與 `443`（或 `service="http"`、`service="https"`）。這一步的選項與替代做法：

- **`--permanent` 加 `--reload`，或不帶 `--permanent`**：帶 `--permanent` 的規則寫進設定檔；不帶時只改執行中的規則，下一次 `--reload` 就消失。這次用 `--permanent`，dockerd 啟動之後與 reload 之後 8080 的結果都跟上面相同（實測）；重開機之後依 `--permanent` 的機制會在，重開機後沒有再連 8080。
- **ipset，或每一段各寫一條 rich rule**：每段一條也行得通，15 段就是 15 條規則，清單更新時要逐條比對；ipset 更新時只換集合的內容，rich rule 不動。依 firewalld 的規則寫法推論，沒有實跑。
- **把 ipset 加到一個 zone 的 sources**：來源落在 ipset 的連線改由那個 zone 處理，放行的範圍是那個 zone 開的全部服務與連接埠。OrbStack 那一台上建了一個只開 8080 的 zone，sources 放 `ipset:cloudflare-v4`（實測時這個 zone 叫 `verify-cf`，跟 namespace 同名，這裡改名避免混淆；`firewall-cmd --permanent --new-zone=verify-cfzone`、`--zone=verify-cfzone --add-source=ipset:cloudflare-v4`、`--zone=verify-cfzone --add-port=8080/tcp`）：`verify-cf` 連 8080 拿到 200、`verify-other` 被回拒，跟 rich rule 的結果相同；差別在 `verify-cf` 連 22 時回 `No route to host`（被 `verify-cfzone` 回拒，它沒有開 ssh），`verify-other` 連 22 仍由 `public` zone 處理。zone sources 接管的是那些位址的全部入站連線，來源落在清單裡的連線只看這個 zone 開了什麼，`public` zone 的設定對它們不再生效。用 `trusted` zone 時則相反，那些位址連任何連接埠都放行。Docker 發佈的 8081 照樣兩個來源都連得到，zone 管不到轉送路徑。測完以 `firewall-cmd --permanent --delete-zone=verify-cfzone` 加 `firewall-cmd --reload` 刪掉這個 zone。
- **IPv6**：OCI 這台主機沒有全域的 IPv6 位址，在 OrbStack 那一台上用一個 ULA（unique local address，`fd00::/8` 裡只在本地使用的 IPv6 位址）`fd00:beef::1` 當主機的 IPv6 位址（兩個來源加 IPv6 位址的指令見 ufw 那一篇〈共用的函式與兩個測試來源〉的 `ns_setup6`）、兩個 namespace 各加一個 IPv6 位址（`verify-cf` 用 Cloudflare 的 `2606:4700::10`，`verify-other` 用文件保留的 `2001:db8::10`）測。`--option=family=inet6` 建的 ipset 放進 `ips-v6` 的 7 段，rich rule 寫 `family="ipv6"`：`verify-cf` 經由 IPv6 連 8080 拿到 200、`verify-other` 被回拒，跟 IPv4 相同。同一組 IPv6 位址也拿來量 Docker 發佈的 8081，結果寫在〈Docker 發佈的連接埠與 firewalld 的規則〉裡 IPv6 那一份發佈的那一段。測完以 `--remove-rich-rule` 刪掉這一段與那一段加的兩條 IPv6 rich rule（8080 與 8081）再 reload；namespace 裡的 IPv6 位址隨清理段刪 namespace 一起消失，`lo` 上的 ULA 與 `cloudflare-v6` ipset 寫在清理段。

## Docker 發佈的連接埠與 firewalld 的規則

解開靜態檔、在背景啟動 dockerd，看它對 firewalld 與 iptables 做了什麼：

```bash
sysctl net.ipv4.ip_forward
tar xzf $D/docker-29.9.2.tgz -C $D
start_dockerd
docker info --format 'firewall backend: {{.FirewallBackend}}'
sysctl net.ipv4.ip_forward
firewall-cmd --zone=docker --list-all; firewall-cmd --info-policy=docker-forwarding
iptables -S FORWARD
```

```text
net.ipv4.ip_forward = 0
firewall backend: {iptables+firewalld [...]}
net.ipv4.ip_forward = 1
docker (active)
  target: ACCEPT
  interfaces: docker0
docker-forwarding (active)
  priority: -1
  target: ACCEPT
  ingress-zones: ANY
  egress-zones: docker
-P FORWARD DROP
-A FORWARD -j DOCKER-USER
-A FORWARD -j DOCKER-FORWARD
```

（zone 與 policy 只留相關的欄位。）dockerd 把 `ip_forward` 從 0 改成 1，在 firewalld 裡建了 `docker` zone 與 `docker-forwarding` policy；iptables 的 FORWARD 鏈在 dockerd 啟動之後預設政策是 DROP（同一台主機在沒有 dockerd 時是 ACCEPT），開頭跳到 `DOCKER-USER` 與 `DOCKER-FORWARD`。接著跑三個容器：一個發佈在全部介面、一個只發佈在本機位址、一個帶存取記錄的當作後面的對照組：

```bash
docker load -i $D/busybox-1.37.tar
mkdir -p $D/www && echo hello > $D/www/index.html
# busybox 的 httpd：-f 在前景執行、-p 聽的連接埠、-h 網頁根目錄；-v 印出每一筆存取
docker run -d --name verify-web-all -v $D/www:/www:ro -p 8081:80 busybox:1.37 httpd -f -p 80 -h /www
docker run -d --name verify-web-lo  -v $D/www:/www:ro -p 127.0.0.1:8082:80 busybox:1.37 httpd -f -p 80 -h /www
docker run -d --name verify-web-v   -v $D/www:/www:ro -p 8083:80 busybox:1.37 httpd -f -v -p 80 -h /www
sleep 2
firewall-cmd --zone=public --list-ports; firewall-cmd --zone=public --list-rich-rules
probe 8081; probe 8082
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8082/
```

同一行裡 `docker run` 的 `-v $D/www:/www:ro` 是把主機的目錄唯讀掛進容器，`httpd -f -v` 的 `-v` 是 busybox httpd 自己的記錄選項，兩者不同。

```text
（--list-ports 沒有輸出）
rule family="ipv4" source ipset="cloudflare-v4" port port="8080" protocol="tcp" accept
== -p 8081:80（沒有指定位址）
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=0  200
== -p 127.0.0.1:8082:80
  verify-cf     -> :8082  rc=7  ... Could not connect to server
  verify-other  -> :8082  rc=7  ... Could not connect to server
200
```

firewalld 沒有任何一條規則提到 8081，`public` zone 對未列出的連線一律回拒，而兩個來源都拿到容器的回應。看改寫目的地的那條規則與容器記到的來源：

```bash
iptables -t nat -S DOCKER | grep 8081
probe 8083 >/dev/null; docker logs verify-web-v 2>&1 | tail -2
```

```text
-A DOCKER ! -i docker0 -p tcp -m tcp --dport 8081 -j DNAT --to-destination 172.17.0.2:80
[::ffff:173.245.48.10]:34162: response:200
[::ffff:203.0.113.10]:33384: response:200
```

`DNAT`（[目的位址轉換](/infra/knowledge-cards/dnat/)）那一條就是在主機防火牆之前改寫目的地的規則。容器的記錄裡兩個來源的位址原樣出現：容器看得到真正的來源，所以來源限制做得到，只是要寫在別的位置。只發佈在 `127.0.0.1` 的 8082 從兩個外部來源都連不到、主機本機連得到；這是 Docker 29.9.2 的結果，Docker〈Port publishing〉寫明 28.0.0 以前同一個 L2 網段的其他主機連得到發佈在 127.0.0.1 的連接埠。對外改由主機上的反向代理接時，反向代理受〈firewalld 以 ipset 只放行 Cloudflare 位址到主機本身的程式〉那種 rich rule 約束。

預設的發佈位址可以在 Docker 的設定裡改，OrbStack 那一台實跑了兩種。`/etc/docker/daemon.json` 寫 `{ "ip": "127.0.0.1" }` 並重啟 Docker 之後，預設 bridge 網路上 `-p 8085:80` 的容器發佈在 `127.0.0.1:8085`，兩個外部來源都連不到；同時間另一個接在自訂網路（`docker network create verify-custom`）上、`-p 8086:80` 的容器仍發佈在 `0.0.0.0:8086` 與 `[::]:8086`，兩個外部來源都連得到：`ip` 選項只作用在預設的 bridge 網路。自訂網路建立時帶 `-o com.docker.network.bridge.host_binding_ipv4=127.0.0.1`（這次建的網路叫 `verify-hb`），那個網路上 `-p 8087:80` 的容器就發佈在 `127.0.0.1:8087`。`docker ps` 的 PORTS 欄看得到每個容器實際發佈在哪個位址。compose 的自訂網路在 `networks:` 底下的 `driver_opts` 寫同一個選項，沒有實跑。測完要還原，否則之後各節重建的容器都會發佈在 `127.0.0.1`、結果跟文章不同：刪掉這三個容器、`docker network rm verify-custom verify-hb`、`rm /etc/docker/daemon.json`、`systemctl restart docker`。

IPv6 那一份發佈走另一條路。OrbStack 那一台用〈firewalld 以 ipset 只放行 Cloudflare 位址到主機本身的程式〉的 IPv6 那一項建的位址量：Docker 的 `-p 8081:80` 同時發佈在 IPv6，而容器的網路沒有開 IPv6 時，`[::]:8081` 由 docker-proxy 這個主機上的程式（[Userland Proxy](/infra/knowledge-cards/userland-proxy/) 的一種）接聽。沒有任何規則時兩個來源經由 IPv6 連 8081 都被 `public` zone 回拒，加一條 `rule family="ipv6" source ipset="cloudflare-v6" port port="8081" protocol="tcp" accept` 之後只有 `verify-cf` 連得到。IPv6 那一份走 input 路徑、受 zone 管，跟 IPv4 那一份相反；同一條 rich rule 加上之後，IPv4 的 8081 仍然兩個來源都連得到。容器的網路帶 `--ipv6` 時，Docker 改用 ip6tables 的位址轉換處理 IPv6，那一種沒有測。

## DOCKER-USER 鏈的限制效果與規則的存續

在 `DOCKER-USER` 寫一條跳到自建鏈 `CF-ONLY` 的規則，`CF-ONLY` 對 Cloudflare 的每一段回到原本的流程（RETURN），其餘丟棄。這一組指令在這一節會跑兩次，所以寫成函式：

```bash
add_cf_only() {
  iptables -N CF-ONLY
  while read -r net; do [ -n "$net" ] && iptables -A CF-ONLY -s "$net" -j RETURN; done < <(cat $D/cf-ips-v4.txt; echo)
  iptables -A CF-ONLY -j DROP
  iptables -I DOCKER-USER -p tcp -m conntrack --ctorigdstport 8081 --ctdir ORIGINAL -j CF-ONLY
}
add_cf_only
probe 8081; probe 8083
```

正式設定把 8081 換成 80 與 443 時，跳轉那一條要加 `-m conntrack --ctstate DNAT`，只比對送往發佈連接埠、經過位址轉換的連線；少了它，容器自己往外連 443、容器之間連 80 的封包也會進 `CF-ONLY` 被丟掉（ufw 那一篇在 Ubuntu 上補測過：[ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑](/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/) 的〈DOCKER-USER 規則的效果，以及它在 ufw reload、Docker 重啟與重開機之後的存續〉）。

`< <(cat …; echo)` 補一個換行，因為 Cloudflare 的清單最後一行沒有換行，`read` 會漏讀最後一段。每一段各寫一條 `-s` 而不用 iptables 的 `-m set --match-set cloudflare-v4`：firewalld 的 nftables 後端把 ipset 建成 nftables 的集合，不是 iptables 的 `set` 模組讀的那種核心 ipset，推論 `-m set` 引用不到它，沒有實跑。`--ctorigdstport 8081` 比對[連線追蹤](/infra/knowledge-cards/conntrack/)記下的原始目的連接埠：封包到 `DOCKER-USER` 時目的地已經改成容器的 80，寫 `--dport 8081` 比對不到。`--ctdir ORIGINAL` 讓規則只看發起方向的封包，容器回覆的封包不進 `CF-ONLY`。`-I` 把規則插在 `DOCKER-USER` 最前面；最後那一條用 `DROP`，範圍外的來源等到逾時，換成 `REJECT` 會變成立即失敗，沒有比較。

```text
== DOCKER-USER 只放行 Cloudflare 到原始目的連接埠 8081
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=28  curl: (28) Connection timed out after 5002 milliseconds
== 對照：沒有套規則的 8083
  verify-cf     -> :8083  rc=0  200
  verify-other  -> :8083  rc=0  200
```

規則擋得住。接著分開看 firewalld 重新載入與 dockerd 重啟。先重新載入 firewalld：

```bash
firewall-cmd --reload; sleep 2
iptables -S DOCKER-USER; iptables -S CF-ONLY; probe 8081
```

```text
== firewall-cmd --reload 之後
-N DOCKER-USER
iptables: No chain/target/match by that name.
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=0  200
```

`firewall-cmd --reload` 之後，`DOCKER-USER` 只剩空的鏈，`CF-ONLY` 整條不見了，範圍外的來源又連得到。分出是誰清掉的：先停掉 dockerd，建一條測試鏈再 reload，再在 dockerd 執行中做一次：

```bash
pkill -x dockerd; while pgrep -x dockerd >/dev/null; do sleep 1; done
iptables -N VERIFY-T; iptables -A VERIFY-T -j RETURN; iptables -I DOCKER-USER -j VERIFY-T
iptables -S | grep -c VERIFY-T
firewall-cmd --reload; sleep 2; iptables -S | grep -c VERIFY-T
restart_dockerd
iptables -N VERIFY-T; iptables -A VERIFY-T -j RETURN; iptables -I DOCKER-USER -j VERIFY-T
iptables -S | grep -c VERIFY-T
firewall-cmd --reload; sleep 3; iptables -S | grep -c VERIFY-T
grep -i firewalld $D/dockerd.log | tail -3
```

兩次都是 reload 之前 3、reload 之後 0：清掉 iptables 裡自建規則的是 firewalld 的重新載入，跟 dockerd 有沒有在跑無關；dockerd 的記錄裡只有它在 reload 之後重建自己 zone 與 policy 的訊息（`Firewalld: docker zone already exists, returning` 這類）。這台主機的 `/etc/firewalld/firewalld.conf` 是 `FlushAllOnReload=yes`；〈firewalld.conf〉寫明這是預設值，作用是 reload 時清掉全部執行中的規則。

OrbStack 那一台的 firewalld 沒有任何 direct 設定（`firewall-cmd --direct --get-all-rules` 與 `--get-all-passthroughs` 都沒有輸出），`DOCKER-USER` 裡的同一條規則在 `FlushAllOnReload=yes` 與 `no` 下 reload 之後都還在、照樣擋得住。在那一台加一條 direct rule 之後：

```bash
firewall-cmd --permanent --direct --add-rule ipv4 filter OUTPUT 0 -d 169.254.0.0/16 -p tcp -j ACCEPT
firewall-cmd --reload
iptables -N VERIFY-T; iptables -I DOCKER-USER -j VERIFY-T
iptables -I DOCKER-USER -p tcp -m conntrack --ctorigdstport 8081 --ctdir ORIGINAL ! -s 173.245.48.0/20 -j DROP
firewall-cmd --reload; sleep 3
iptables -S DOCKER-USER; iptables -S VERIFY-T
```

```text
-N DOCKER-USER
iptables: No chain/target/match by that name.
```

reload 之後 `DOCKER-USER` 只剩空鏈、自建鏈 `VERIFY-T` 整條不見，範圍外的來源又連得到；`FlushAllOnReload` 改成 `no` 再做一次，結果相同。那條 direct rule 只是用來觸發 firewalld 管理 iptables，內容不重要。測完 `firewall-cmd --permanent --direct --remove-rule …` 移除它，`/etc/firewalld/direct.xml` 會留下一個只有 `<direct>` 空元素的檔，刪掉再 reload。

direct 設定的另一種是 passthrough（直接交給 iptables 的一行規則）。同一台改加一條 passthrough、不加 direct rule：

```bash
firewall-cmd --permanent --direct --add-passthrough ipv4 -A OUTPUT -d 169.254.0.2/32 -p tcp --dport 3260 -j ACCEPT
firewall-cmd --reload; sleep 3
iptables -I DOCKER-USER -p tcp -m conntrack --ctorigdstport 8081 --ctdir ORIGINAL ! -s 173.245.48.0/20 -j DROP
firewall-cmd --reload; sleep 3
iptables -S DOCKER-USER
```

```text
-N DOCKER-USER
```

只有一條 passthrough 時 reload 也清掉了 `DOCKER-USER` 的規則；加 passthrough 之前（沒有任何 direct 設定時），同一條規則留過了 reload。量完移除 passthrough、刪掉 `direct.xml` 再 reload，`--get-all-passthroughs` 回 0。所以在 nftables 後端（這兩台都是）上，清掉 iptables 自建規則的條件是 firewalld 有沒有 direct 設定（direct rule 或 passthrough 任一種），跟 `FlushAllOnReload` 的值無關。查的時候兩個指令都要跑：`--get-all-rules` 只列 direct rule，不列 passthrough。

firewalld 改用 iptables 後端時沒有這個條件。OrbStack 那一台把 `/etc/firewalld/firewalld.conf` 的 `FirewallBackend` 改成 `iptables`、重啟 firewalld 與 Docker，`--get-all-rules` 與 `--get-all-passthroughs` 都是 0，`DOCKER-USER` 裡的同一條規則在 `firewall-cmd --reload` 之後一樣不見了：原因依後端的設計推論是 iptables 後端的 firewalld 自己管理 iptables 的表，reload 時整張重建。量完改回 `nftables`、重啟兩個服務，`nft list tables | grep -c 'inet firewalld'` 回 1、`iptables -t nat -S DOCKER | grep -c 8081` 回 1，firewalld 的表與 Docker 的位址轉換規則都回來了。direct 設定也不是主機固定的屬性：之後裝的軟體可能再加進來，例如 fail2ban 的 `firewallcmd-*` 動作在 jail 啟動時寫 direct rule（依 fail2ban 的動作設定推論，沒有實跑），查的時候沒有、之後 reload 才清掉。只寫在執行中設定、沒有 `--permanent` 的 direct rule 是否同樣觸發，沒有量。

OCI 的 Oracle Linux 映像本來就有 passthrough。2026-10-26 用同一個映像（`Oracle-Linux-10.2-aarch64-2026.10.16-0`）建的另一台主機上：

```bash
ls -l /etc/firewalld/direct.xml
grep -c '<passthrough' /etc/firewalld/direct.xml
firewall-cmd --direct --get-all-rules | wc -l; firewall-cmd --direct --get-all-passthroughs | wc -l
```

```text
-rw-r--r--. 1 root root 8495 Aug  8 00:48 /etc/firewalld/direct.xml
32
0
32
```

`direct.xml` 有 32 條 passthrough，內容是 `BareMetalInstanceServices` 鏈：主機送往 `169.254.0.0/16`（Oracle Cloud 的執行個體中繼資料、iSCSI、DNS 與 NTP 這類服務）的連線，只放行列出的幾個服務連接埠，其中 iSCSI 的 3260 與部分 80 只限 root 的程式，其餘 TCP 與 UDP 一律回拒；每一條的註解寫著修改或移除之前先讀 Oracle 文件的〈Oracle-Provided Images〉。`--get-all-rules` 只列 direct rule、不列 passthrough，所以回 0；要用 `--get-all-passthroughs` 才看得到。依 OrbStack 那一台的 passthrough 結果，這 32 條就是第一輪 reload 清掉 `DOCKER-USER` 的原因；在這台主機上沒有移除它們再 reload 確認。這幾條規則保護主機與中繼資料服務之間的連線，刪掉它們換取 `DOCKER-USER` 的存續不划算；在 OCI 的 Oracle Linux 上，要長期使用的限制改寫進下文的自建 nftables 表。

再把同一組規則加回去，只重啟 dockerd、不動 firewalld：

```bash
add_cf_only
restart_dockerd
iptables -S DOCKER-USER; iptables -S CF-ONLY | wc -l; probe 8081
```

```text
== 只重啟 dockerd（不 reload firewalld）
-N DOCKER-USER
-A DOCKER-USER -p tcp -m conntrack --ctorigdstport 8081 --ctdir ORIGINAL -j CF-ONLY
17
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=28  curl: (28) Connection timed out after 5002 milliseconds
```

dockerd 重啟不清 `DOCKER-USER`，`CF-ONLY` 的 17 行（建鏈一行、15 段 RETURN、一條 DROP）都在，照樣擋得住。iptables 指令加的規則只存在執行中的核心裡，重開機之後不在；實測那一輪重開機之前 `DOCKER-USER` 已經被 reload 清空，所以重開機這一項依機制寫成，沒有單獨實測。這一節做完時 `CF-ONLY` 還在，〈firewalld policy 對發佈連接埠的效果與轉送鏈的順序〉開頭的 reload 會清掉它。

## firewalld policy 對發佈連接埠的效果與轉送鏈的順序

Docker 用 `docker-forwarding` policy 放行轉送到 `docker` zone 的流量，所以試著加一條優先序更高的 policy，從 `public` 轉送到 `docker` 只放行 Cloudflare。`firewall-cmd --reload` 會一併清掉〈DOCKER-USER 鏈的限制效果與規則的存續〉留下的 `CF-ONLY`：

```bash
firewall-cmd --permanent --new-policy=cf-to-docker
firewall-cmd --permanent --policy=cf-to-docker --add-ingress-zone=public
firewall-cmd --permanent --policy=cf-to-docker --add-egress-zone=docker
firewall-cmd --permanent --policy=cf-to-docker --set-priority=-10      # 比 docker-forwarding 的 -1 先比對
firewall-cmd --permanent --policy=cf-to-docker --set-target=DROP
firewall-cmd --permanent --policy=cf-to-docker --add-rich-rule='rule family="ipv4" source ipset="cloudflare-v4" accept'
firewall-cmd --reload
probe 8081
restart_dockerd; probe 8081
```

reload 剛完成就連，兩個來源連 8081 都立即被回拒；`restart_dockerd` 之後再連，兩個來源都拿到 8081 的回應，policy 沒有擋下範圍外的來源。reload 剛完成時的回拒，推論是 Docker 的目的位址轉換規則還沒重建、封包沒有被改寫而落到 `public` zone 的回拒：〈DOCKER-USER 鏈的限制效果與規則的存續〉裡 reload 之後等 2 秒、下面移除這條 policy 之後等 3 秒再連，8081 都通了；回拒持續多久沒有量。policy 擋不住的原因在 firewalld 自己的轉送鏈：

```bash
nft list chain inet firewalld filter_FORWARD
```

```text
chain filter_FORWARD {
	type filter hook forward priority filter + 10; policy accept;
	ct state { established, related } accept
	ct status dnat accept
	iifname "lo" accept
	ct state invalid drop
	...
	jump filter_FORWARD_POLICIES
	reject with icmpx admin-prohibited
}
```

`ct status dnat accept` 排在 `jump filter_FORWARD_POLICIES` 之前，經過目的位址轉換的連線在任何 policy 之前就被接受，policy 寫什麼都輪不到它。移除這條 policy，讓 `StrictForwardPorts` 那一節從沒有 policy 的狀態開始：

```bash
firewall-cmd --permanent --delete-policy=cf-to-docker
firewall-cmd --reload; sleep 3
probe 8081
```

移除之後兩個來源都連得到 8081。

## StrictForwardPorts=yes：轉送鏈的變化與 forward-port 規則的比對條件

firewalld 轉送鏈 `filter_FORWARD` 開頭的 `ct status dnat accept` 由設定檔的 `StrictForwardPorts` 控制，預設 `no`。這一節開始時，ipset `cloudflare-v4`、8080 的 rich rule 與三個容器都在，`cf-to-docker` 已經移除。（實測時這一節在另一輪、以重新建好的 namespace、ipset 與 `verify-web-all` 跑，結果不受影響。）改成 `yes` 再看轉送鏈與連線結果：

```bash
cp /etc/firewalld/firewalld.conf /etc/firewalld/firewalld.conf.verify-bak
sed -i 's/^StrictForwardPorts=no/StrictForwardPorts=yes/' /etc/firewalld/firewalld.conf
grep '^StrictForwardPorts=' /etc/firewalld/firewalld.conf
firewall-cmd --reload; sleep 3
nft list chain inet firewalld filter_FORWARD; nft list chain inet firewalld filter_FORWARD_dnat
probe 8081
```

`grep` 要回 `StrictForwardPorts=yes`；設定檔裡沒有這一行（較舊的 firewalld 沒有這個選項）時 `sed` 什麼都不改、也不報錯，後面的結果會跟下面不同。

```text
StrictForwardPorts=yes
	ct state { established, related } accept
	ct status dnat jump filter_FORWARD_dnat
	...
	chain filter_FORWARD_dnat {
		reject with icmpx admin-prohibited
	}
== StrictForwardPorts=yes，還沒有任何放行
  verify-cf     -> :8081  rc=7  ... Could not connect to server
  verify-other  -> :8081  rc=7  ... Could not connect to server
```

經過目的位址轉換的連線改跳到 `filter_FORWARD_dnat`，那條鏈只有回拒，兩個來源都連不到發佈的 8081。先試 policy：從 `public` 轉送到 `docker`、只放行 Cloudflare，target 用預設的 CONTINUE：

```bash
firewall-cmd --permanent --new-policy=cf-to-docker
firewall-cmd --permanent --policy=cf-to-docker --add-ingress-zone=public
firewall-cmd --permanent --policy=cf-to-docker --add-egress-zone=docker
firewall-cmd --permanent --policy=cf-to-docker --set-priority=-10
firewall-cmd --permanent --policy=cf-to-docker --add-rich-rule='rule family="ipv4" source ipset="cloudflare-v4" accept'
firewall-cmd --reload; sleep 3; probe 8081
restart_dockerd; probe 8081
firewall-cmd --permanent --delete-policy=cf-to-docker; firewall-cmd --reload; sleep 3
```

加上 policy、reload 與 dockerd 重啟之後，兩個來源都還是立即被回拒：經過目的位址轉換的連線進的是 `filter_FORWARD_dnat`，policy 輪不到它們。〈firewalld.conf〉與 firewalld 官方部落格〈Strict Forward Ports〉的說法是，發佈的連接埠要用 firewalld 的 forward-port 明確放行。試的是 `public` zone 的 forward-port rich rule，限定來源是 Cloudflare 的 ipset：

```bash
CIP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' verify-web-all)
echo $CIP
firewall-cmd --permanent --zone=public --add-rich-rule="rule family=\"ipv4\" source ipset=\"cloudflare-v4\" forward-port port=\"8081\" protocol=\"tcp\" to-port=\"80\" to-addr=\"$CIP\""
firewall-cmd --reload; sleep 3
nft list chain inet firewalld filter_FORWARD_dnat
probe 8081
restart_dockerd; probe 8081
```

`CIP` 是容器在 docker0 網路上的位址（這次是 `172.17.0.2`）。Docker 29 的 `docker inspect` 已經沒有 `.NetworkSettings.IPAddress` 這個欄位，用舊的寫法會回 `map has no entry for key "IPAddress"`，`CIP` 是空的，接著 `firewall-cmd` 回 `INVALID_RULE: internal error in _lexer(): to-addr=`；所以從 `.NetworkSettings.Networks` 取。

```text
	chain filter_FORWARD_dnat {
		ct original proto-dst 8081 accept
		reject with icmpx admin-prohibited
	}
== 加上限定來源的 forward-port rich rule
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=0  200
```

firewalld 依這條 rich rule 在 `filter_FORWARD_dnat` 寫的放行是 `ct original proto-dst 8081 accept`，只比對原始目的連接埠，rich rule 的來源條件沒有寫進這一條，所以範圍外的來源也連得到；dockerd 重啟之後結果相同。rich rule 的來源條件只出現在 firewalld 依同一條規則另外寫的那條目的位址轉換裡，而 Docker 自己的位址轉換已經先改寫了封包。

OrbStack 那一台另外在 `StrictForwardPorts=yes` 下試了兩種 forward-port。一是寫在 policy 上：新建 policy `verify-fp`（`--new-policy=verify-fp`、`--add-ingress-zone=public`、`--add-egress-zone=docker`），從 `public` 到 `docker`，rich rule 一樣帶來源 ipset 與 `to-addr`。`firewall-cmd` 接受這條規則（回 `success`），reload 之後 `filter_FORWARD_dnat` 裡仍然只有 `reject with icmpx admin-prohibited`，沒有任何放行，兩個來源連 8081 都被回拒：policy 上的 forward-port 沒有在 `StrictForwardPorts` 的那條鏈裡留下放行。二是不帶 `to-addr`、轉到本機另一個連接埠：

```bash
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source ipset="cloudflare-v4" forward-port port="8088" protocol="tcp" to-port="8080"'
firewall-cmd --reload; sleep 3; probe 8088
```

`public` zone 沒有開 8080，而 `verify-cf` 連 8088 拿到 8080 那個主機程式的回應、`verify-other` 被回拒：轉到本機的 forward-port 帶著來源條件，結果是只有 Cloudflare 連得到。它轉到的是主機上的程式（封包改寫成本機位址之後走 input 路徑，見 [DNAT](/infra/knowledge-cards/dnat/) 卡），不是容器，所以只適用於網站由主機上的程式（或聽在主機位址上的反向代理）提供的情形。還原這一節改的設定：

```bash
firewall-cmd --permanent --zone=public --remove-rich-rule="rule family=\"ipv4\" source ipset=\"cloudflare-v4\" forward-port port=\"8081\" protocol=\"tcp\" to-port=\"80\" to-addr=\"$CIP\""
firewall-cmd --permanent --delete-policy=verify-fp             # OrbStack 那一台試的 policy
firewall-cmd --permanent --zone=public --remove-rich-rule='rule family="ipv4" source ipset="cloudflare-v4" forward-port port="8088" protocol="tcp" to-port="8080"'
mv /etc/firewalld/firewalld.conf.verify-bak /etc/firewalld/firewalld.conf
firewall-cmd --reload; sleep 3
grep '^StrictForwardPorts=' /etc/firewalld/firewalld.conf; firewall-cmd --zone=public --list-rich-rules
```

`grep` 回 `StrictForwardPorts=no`，rich rule 只剩 8080 那一條。OrbStack 那一台改 `StrictForwardPorts` 時用的是 `sed` 直接改值，沒有備份檔，還原也用 `sed` 改回 `no`；`mv` 那一行是 OCI 那一台的做法。

## 自己的 nftables 表：掛在目的位址轉換之前

這一節開始時 `StrictForwardPorts` 是 `no`，三個容器都在跑。在 nftables 建一張自己的表 `verify_cf_only`，鏈接在 prerouting 這個 hook 上、優先序 `dstnat - 10`（排在 Docker 與 firewalld 的目的位址轉換之前），封包的目的連接埠還是 8081 時就比對來源：

```bash
CF=$(paste -sd, $D/cf-ips-v4.txt)
cat > $D/verify-cf-only.nft <<EOF
table inet verify_cf_only {
  set cloudflare_v4 { type ipv4_addr; flags interval; elements = { $CF } }
  chain prerouting {
    type filter hook prerouting priority dstnat - 10; policy accept;
    iifname != "lo" tcp dport { 8081 } ip saddr != @cloudflare_v4 drop
  }
}
EOF
nft -f $D/verify-cf-only.nft
probe 8081; probe 8083
curl -sS -o /dev/null -w '%{http_code}\n' http://$HOSTIP:8081/
```

`iifname != "lo"` 讓主機自己連自己的位址不受限制；`flags interval` 讓位址集合 `cloudflare_v4` 存得下位址段。優先序排在 `dstnat` 或之後時，封包的目的連接埠已經被改寫成 80，`tcp dport { 8081 }` 比對不到，範圍外的來源會連得到（依 nftables 的 hook 順序推論，沒有實跑）。`ip saddr` 只比對 IPv4；主機有 IPv6 時，IPv6 的連線不受這條規則限制，要另寫一條 `ip6 saddr` 與 IPv6 的集合，後果見概念文章的〈只放行 CDN 位址的套用時機、範圍與清單的維護〉。

```text
== 自己的 nft 表，只放行 Cloudflare 到 8081
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=28  curl: (28) Connection timed out after 5002 milliseconds
== 對照 8083
  verify-cf     -> :8083  rc=0  200
  verify-other  -> :8083  rc=0  200
200
```

接著重新載入 firewalld 與重啟 dockerd，各看一次：

```bash
firewall-cmd --reload; sleep 3; nft list tables | grep verify; probe 8081
restart_dockerd; nft list tables | grep verify; probe 8081
```

兩次都列得出 `table inet verify_cf_only`，結果跟上面相同。firewalld 重新載入只重建它自己的 `inet firewalld` 這張表，自建的表留著。

`nft -f` 只改執行中的規則，開機時要由 `nftables.service` 載入。先看這台主機上這個服務與它的設定檔原本的狀態：

```bash
systemctl is-enabled nftables
grep -v '^#' /etc/sysconfig/nftables.conf | grep -c .
systemctl cat nftables | grep -E '^Exec'; systemctl cat firewalld | grep '^Conflicts'
```

這台回 `disabled`、`0`（設定檔有 6 行、全部是註解）。`ExecStop` 是 `/sbin/nft flush ruleset`，`ExecReload` 是 `nft 'flush ruleset; include "/etc/sysconfig/nftables.conf";'`；firewalld 的 `Conflicts=` 列的是 `iptables.service ip6tables.service ebtables.service ipset.service`，沒有 `nftables.service`，所以兩者可以同時啟用。設定檔原本就有內容、尤其有 `flush ruleset` 時，開機載入它會清掉 firewalld 已經建好的表，那時不要在這個檔加 `include`，改用下面替代做法裡的 oneshot unit。設定檔原本是空的時：

```bash
cp /etc/sysconfig/nftables.conf /etc/sysconfig/nftables.conf.verify-bak
cp $D/verify-cf-only.nft /etc/nftables/verify-cf-only.nft
echo 'include "/etc/nftables/verify-cf-only.nft"' >> /etc/sysconfig/nftables.conf
nft -c -f /etc/sysconfig/nftables.conf && echo "syntax ok"     # -c 只檢查語法，不套用
systemctl enable nftables
systemctl reboot
```

重開機之後：

```bash
nft list tables
systemctl is-active firewalld nftables
journalctl -b -u nftables -u firewalld --no-pager | tail -3
```

```text
table inet verify_cf_only
table inet firewalld
table ip filter
table ip6 filter
active
active
... Started firewalld.service - firewalld - dynamic firewall daemon.
... Starting nftables.service - Netfilter Tables...
... Finished nftables.service - Netfilter Tables.
```

這一次 firewalld 先啟動、`nftables.service` 接著完成，兩張表都在。接著 `sudo -i`、重新貼〈共用的變數與函式〉的區塊，再跑：

```bash
ns_setup
start_dockerd
docker start verify-web-all verify-web-lo verify-web-v; sleep 2
probe 8081; probe 8083
```

```text
== 重開機後 8081（開機載入的 nft 表）
  verify-cf     -> :8081  rc=0  200
  verify-other  -> :8081  rc=28  curl: (28) Connection timed out after 5002 milliseconds
== 重開機後 8083（沒有限制）
  verify-cf     -> :8083  rc=0  200
  verify-other  -> :8083  rc=0  200
```

`nftables.service` 的 `stop`、`restart` 與 `reload` 都會先 `flush ruleset`，清掉的是整個 nftables 規則集，firewalld 的 `inet firewalld` 表也在裡面。所以這個服務只用來開機載入；改了 `verify-cf-only.nft` 之後，先 `nft delete table inet verify_cf_only` 再 `nft -f` 那一個檔。這一段依 unit 檔的內容寫成，沒有實跑 `restart`。

這一步的替代做法：

- **自己寫一個開機時執行 `nft -f /etc/nftables/verify-cf-only.nft` 的 systemd oneshot unit**：不經過 `nftables.service`，避開它的 `flush ruleset`，誤下 `systemctl restart nftables` 也不會清掉 firewalld 的表；代價是多一個要維護的 unit，沒有實跑。
- **把同樣的規則寫成 firewalld 的 direct rule 或 passthrough**：firewalld 會在每次重新載入時重寫，但〈firewalld.direct〉寫明 direct 介面已經棄用、由 policy 取代；而且主機一有 direct 設定，reload 就會清掉 iptables 裡其他自建的規則（〈DOCKER-USER 鏈的限制效果與規則的存續〉量到的），沒有實跑這個寫法本身。
- **把 `{ 8081 }` 換成 `{ 80, 443 }`**：這是正式設定的寫法，但要多一個條件 `fib daddr type local`（目的地是這台主機自己的位址）。少了它時，容器自己往外連 443、容器之間連 80 的封包也從 docker0 進 prerouting、目的連接埠一樣是 443 或 80、來源不在清單，一起被丟掉。OrbStack 那一台補測：規則寫成 `iifname != "lo" tcp dport { 80, 443, 8081 } ip saddr != @cloudflare_v4 drop` 時，一個 `busybox` 容器 `wget https://www.cloudflare.com/` 與連另一個容器的 80 都失敗；改成 `iifname != "lo" fib daddr type local tcp dport { 80, 443, 8081 } ip saddr != @cloudflare_v4 drop` 之後兩者恢復，範圍外的來源連 8081 仍然逾時。拿掉 `tcp dport` 這個條件時，規則變成對整台主機所有連接埠的 Cloudflare 限制，那時要另外排除管理通道進來的介面或來源，否則 SSH 一起被擋。

這張表的規則不出現在 `firewall-cmd --list-all` 裡，查的指令是 `nft list table inet verify_cf_only`。

## 出站的 DNS 只准送往 VCN 解析器：主機與容器的差別

在 `verify-other`（`203.0.113.10`）放一個收 UDP 53 與 TCP 443 的小程式，把收到的封包記進 log，用 log 的筆數判斷封包有沒有送到。`RESOLVER` 是〈共用的變數與函式〉裡填的主機解析器：

```bash
cat > $D/listen.py <<'EOF'
import socket, threading, sys
log = open(sys.argv[1], "a", buffering=1)
def udp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("203.0.113.10", 53))
    while True:
        data, peer = s.recvfrom(4096); log.write(f"udp53 from {peer[0]}\n")
def tcp():
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("203.0.113.10", 443)); s.listen()
    while True:
        c, peer = s.accept(); log.write(f"tcp443 from {peer[0]}\n"); c.close()
threading.Thread(target=udp, daemon=True).start(); tcp()
EOF
ip netns exec verify-other python3 $D/listen.py $D/listen.log &
sleep 1
check() {  # 清空 log，送四種流量，數對方收到的封包
  : > $D/listen.log
  dig +tries=1 +time=2 @$RESOLVER oracle.com A +short >/dev/null 2>&1 && r1=ok || r1=fail
  dig +tries=1 +time=2 @203.0.113.10 oracle.com A >/dev/null 2>&1
  curl -s -m 3 -o /dev/null http://203.0.113.10:443/
  docker run --rm busybox:1.37 nslookup -timeout=2 oracle.com 203.0.113.10 >/dev/null 2>&1
  sleep 1
  echo "  host -> $RESOLVER:53  $r1"
  echo "  203.0.113.10 收到的封包：$(sort $D/listen.log | uniq -c | tr '\n' ';')"
}
check
```

`dig +tries=1` 只送一次查詢；容器裡 busybox 的 `nslookup` 用 `docker run --rm` 起一個只跑這一條指令的容器。`curl` 連 443 用的是 HTTP，監聽程式收到連線就關掉，對方記到一筆 `tcp443` 就代表封包送到了，回應內容不重要；這是一般的 TCP 連線，不是 DNS over HTTPS 的查詢。加限制之前：

```text
== 沒有出站限制
  host -> 169.254.169.254:53  ok
  203.0.113.10 收到的封包：1 tcp443 from 192.0.2.5; 5 udp53 from 192.0.2.5;
```

容器的封包經過 Docker 的位址偽裝（masquerade），在對方看來來源也是主機的 `192.0.2.5`，所以收到的 5 個 UDP 53 混著主機與容器的。加一條從 `HOST`（主機本身送出的流量）到 `ANY`（任何 zone）的 policy：

```bash
firewall-cmd --permanent --new-policy=egress-dns
firewall-cmd --permanent --policy=egress-dns --add-ingress-zone=HOST
firewall-cmd --permanent --policy=egress-dns --add-egress-zone=ANY
firewall-cmd --permanent --policy=egress-dns --add-rich-rule="rule priority=\"-2\" family=\"ipv4\" destination address=\"$RESOLVER\" service name=\"dns\" accept"
firewall-cmd --permanent --policy=egress-dns --add-rich-rule='rule priority="-1" service name="dns" reject'
firewall-cmd --reload; sleep 3
check
```

`priority` 小的 rich rule 先比對，放行指定解析器的那一條要排在拒絕之前。

```text
== firewalld policy egress-dns（HOST -> ANY）
  host -> 169.254.169.254:53  ok
  203.0.113.10 收到的封包：1 tcp443 from 192.0.2.5; 4 udp53 from 192.0.2.5;
```

分開送，確認那 4 個是誰的：

```bash
: > $D/listen.log; dig +tries=1 +time=2 @203.0.113.10 oracle.com A | grep -E 'refused|timed out'; sleep 1; wc -l < $D/listen.log
: > $D/listen.log; docker run --rm busybox:1.37 nslookup -timeout=2 oracle.com 203.0.113.10 >/dev/null 2>&1; sleep 1; wc -l < $D/listen.log
```

只有主機 `dig @203.0.113.10` 時對方收到 0 個，`dig` 印 `communications error to 203.0.113.10#53: connection refused`；只有容器 `nslookup` 時對方收到 4 個。這條 policy 擋下主機本身的查詢，容器的查詢走轉送路徑、不經過 `HOST`，照樣送出去；送往 443 的連線在加限制之前與之後都送到。這裡的容器跑在預設的 bridge 網路（介面 docker0），查詢直接從容器送出。compose 的自訂網路上，容器先問 Docker 內建的解析器 `127.0.0.11`，內建解析器往外查的封包由主機送出，結果反過來：OrbStack 那一台上把這條 policy 改成拒絕主機送出的全部 `dns`，compose 容器經由 `127.0.0.11` 的查詢失敗、bridge 容器照常；量法與 conntrack 的輸出在 [ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑](/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/) 的〈compose 自訂網路的容器經由 127.0.0.11 查詢時，DNS 封包從哪裡送出〉。容器自己送出的查詢另外寫在 `DOCKER-USER`（自訂網路的介面是 `br-` 開頭，`-i docker0` 改成 `-i br-+` 或兩條都寫）：

```bash
iptables -I DOCKER-USER -i docker0 -p udp --dport 53 ! -d $RESOLVER -j REJECT
iptables -I DOCKER-USER -i docker0 -p tcp --dport 53 ! -d $RESOLVER -j REJECT
check
```

```text
== 再加 DOCKER-USER：容器的 53 只准到 169.254.169.254
  host -> 169.254.169.254:53  ok
  203.0.113.10 收到的封包：1 tcp443 from 192.0.2.5;
```

這兩條寫在 `DOCKER-USER`，有〈DOCKER-USER 鏈的限制效果與規則的存續〉量到的問題：這台主機上 `firewall-cmd --reload` 之後規則消失，重開機之後也不在。要長期使用就改寫進自建的 nftables 表，鏈接在 forward hook 上。OrbStack 那一台實跑了這個寫法（`RESOLVER` 是〈共用的變數與函式〉填的主機解析器）：

```bash
cat > $D/verify-egress.nft <<EOF
table inet verify_egress {
  chain forward {
    type filter hook forward priority filter - 10; policy accept;
    iifname { "docker0", "br-*" } meta l4proto { tcp, udp } th dport 53 ip daddr != $RESOLVER drop
  }
}
EOF
nft -f $D/verify-egress.nft
```

`"br-*"` 比對 compose 自訂網路的介面；`th dport 53` 同時比對 TCP 與 UDP 的目的連接埠；優先序 `filter - 10` 排在 firewalld 的轉送鏈（`filter + 10`）之前。bridge 容器與 compose 容器直接問 `1.1.1.1` 的查詢都失敗，經由各自預設解析器的照常；`firewall-cmd --reload` 之後 `nft list tables` 仍列得出 `table inet verify_egress`，結果相同。compose 容器經由 `127.0.0.11` 的那一路不經過 forward hook，要靠上面主機的 policy。開機載入的做法同〈自己的 nftables 表：掛在目的位址轉換之前〉。

## 清理：容器、dockerd、防火牆設定與暫存檔

照上面的順序做完時，要清的有：三個容器與映像、dockerd、兩個 namespace、8080 的 rich rule、ipset、`egress-dns` policy、Docker 建的 zone 與 policy、自建的 nftables 表與它的開機載入，以及暫存目錄。中途停下來的讀者，只跑做過的那幾節對應的行；`--remove-rich-rule` 與 `--delete-*` 對不存在的項目只回錯誤，不改別的設定。

```bash
docker rm -f verify-web-all verify-web-lo verify-web-v; docker rmi busybox:1.37
pkill -x dockerd; while pgrep -x dockerd >/dev/null; do sleep 1; done; pkill -x containerd
pkill -f 'http.server 8080'; pkill -f "$D/listen.py"
ip link del vcf-h; ip link del voth-h; ip netns del verify-cf; ip netns del verify-other
firewall-cmd --permanent --zone=public --remove-rich-rule='rule family="ipv4" source ipset="cloudflare-v4" port port="8080" protocol="tcp" accept'
firewall-cmd --permanent --delete-policy=egress-dns
firewall-cmd --permanent --delete-ipset=cloudflare-v4
firewall-cmd --permanent --delete-policy=docker-forwarding     # 這台主機原本沒有 Docker 時才刪
firewall-cmd --permanent --delete-zone=docker                  # 同上
firewall-cmd --reload
nft delete table inet verify_cf_only
mv /etc/sysconfig/nftables.conf.verify-bak /etc/sysconfig/nftables.conf; rm -f /etc/nftables/verify-cf-only.nft
systemctl disable nftables                                     # 實測前是 disabled 時才關
rm -rf /var/lib/docker /var/lib/containerd /run/docker /var/run/docker.sock   # 這台主機原本沒有 Docker 時才刪
cd /; rm -rf /tmp/verify-fw
systemctl reboot
```

OrbStack 那一台另外多了幾項，各節測完已經還原的（zone `verify-cfzone`、IPv6 的 rich rule、`daemon.json`、policy `verify-fp`、8088 的 forward-port、`table inet verify_egress`）不必再清，剩下的是 `lo` 上的 ULA 與 IPv6 的 ipset；這兩行沒有實跑：

```bash
ip -6 addr del fd00:beef::1/128 dev lo
firewall-cmd --permanent --delete-ipset=cloudflare-v6; firewall-cmd --reload
```

ipset 排在引用它的 rich rule 之後刪。Docker 建的 `docker` zone 與 `docker-forwarding` policy 寫進了 firewalld 的永久設定，dockerd 停掉之後還在。`/var/lib/docker` 與 `/var/lib/containerd` 存著 Docker 的映像、容器與 volume；這次的主機原本沒有 Docker，所以整個刪掉。主機原本就有 Docker、這次只是借用時，只刪這次建的三個容器（`busybox:1.37` 原本就有的話也留著），zone、policy 與這兩個目錄都留著，dockerd 與 containerd 用 `systemctl` 管，不用 `pkill`。重開機是為了清掉 dockerd 留在 iptables 的 nat 與 filter 規則，以及被它改成 1 的 `ip_forward`。重開之後：

```bash
nft list tables; sysctl net.ipv4.ip_forward
firewall-cmd --list-all | grep -E 'services|rich|forward-ports'; firewall-cmd --get-ipsets
grep '^StrictForwardPorts=' /etc/firewalld/firewalld.conf
find /tmp /var/tmp -maxdepth 1 -name 'verify-*'
```

`nft list tables` 只剩 `inet firewalld`、`ip filter`、`ip6 filter`（跟實測前登入後第一次查的結果相同），`net.ipv4.ip_forward = 0`，`public` zone 只有 `dhcpv6-client ssh`、沒有 rich rule 與 forward-port，`--get-ipsets` 沒有輸出，`StrictForwardPorts=no`，`find` 沒有輸出。

## 各種寫法在重新載入、dockerd 重啟與重開機之後的結果

這張表的「範圍外的來源」欄量的是規則剛套上時；其餘三欄量的是規則套上之後各做一次那個動作，範圍外的來源還連不連得到、規則還在不在。「沒有單獨測」是那個動作做過、但這條規則不是當時要量的對象，沒有記錄它的狀態；「沒有測」是沒有做那個動作。`DOCKER-USER` 那一列只比對連接埠，正式改成 80、443 時要加 `--ctstate DNAT`，自建 nftables 表那一列要加 `fib daddr type local`（各節的說明）。

| 寫法                                                 | 範圍外的來源連發佈的連接埠        | `firewall-cmd --reload` 之後                                                                                    | dockerd 重啟之後 | 重開機之後                             |
| ---------------------------------------------------- | --------------------------------- | --------------------------------------------------------------------------------------------------------------- | ---------------- | -------------------------------------- |
| firewalld rich rule（只放行 ipset，寫在 zone 上）    | 連得到（規則管不到轉送路徑）      | 規則還在                                                                                                        | 規則還在         | 沒有單獨測（`--permanent` 依機制會在） |
| 只發佈在 `127.0.0.1`                                 | 連不到                            | 沒有單獨測                                                                                                      | 沒有測           | 沒有測（發佈位址屬於容器設定）         |
| `DOCKER-USER` 跳到自建鏈                             | 被擋（逾時）                      | nftables 後端有 direct rule 或 passthrough 時、或 iptables 後端時規則消失（OCI 的映像有 passthrough），其餘還在 | 規則還在         | 沒有單獨測（依機制不在）               |
| firewalld policy（`public` 到 `docker`）             | 連得到（`ct status dnat accept`） | 以 reload 套用，見正文                                                                                          | 連得到           | 沒有測                                 |
| `StrictForwardPorts=yes` 加限定來源的 forward-port   | 連得到（放行規則只比對連接埠）    | 連得到（規則以 reload 套用）                                                                                    | 連得到           | 沒有測                                 |
| `StrictForwardPorts=yes` 加 policy 上的 forward-port | 連不到（範圍內的也被回拒）        | 以 reload 套用                                                                                                  | 沒有測           | 沒有測                                 |
| 自建 nftables 表（prerouting，位址轉換之前）         | 被擋（逾時）                      | 規則還在                                                                                                        | 規則還在         | 規則還在（`nftables.service`）         |

OrbStack 那一台補測的幾列（`DOCKER-USER` 在沒有 direct 設定時的存續、policy 上的 forward-port）環境與 OCI 那一台不同，見事件說明；轉到本機程式的 forward-port 與自建表的出站 DNS 限制不是限制發佈的連接埠，不列在這張表，結果在各自的段落。
