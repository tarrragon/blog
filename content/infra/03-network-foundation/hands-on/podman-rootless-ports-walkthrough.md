---
title: "Podman 與 rootless Docker 發佈連接埠的實測紀錄：rootful Podman 在 ufw 與 firewalld 上的轉送路徑、rootless Docker 與 rootless Podman 由主機程式接收的連接埠與容器看到的來源位址"
date: 2026-10-26
description: "用 Podman 或 rootless 模式的 Docker 發佈連接埠、想知道 ufw 或 firewalld 的規則管不管得到、或想在容器裡拿到連線的真實來源位址時，查 rootful Podman 在 ufw 與 firewalld 上的不同結果、rootless 模式接收連線的路徑，以及容器看到的來源位址"
weight: 3
tags: ["infra", "network", "firewall", "podman", "docker", "rootless", "ufw", "firewalld", "hands-on"]
---

> **事件說明**：2026-10-26，在本機 macOS 的 OrbStack 2.2.5 建的兩台機器上實測（Arm 架構，核心是 OrbStack 自己的 `7.2.12-orbstack`）。一台是 Ubuntu 24.04.5：ufw 0.36.2、iptables 1.8.10（nf_tables 後端）、Podman 4.9.3 與 netavark 1.4.0、slirp4netns 1.2.1、Docker CE 29.9.2 加 `docker-ce-rootless-extras`。另一台是 Oracle Linux 10.2：firewalld 2.4.3（nftables 後端）、Podman 5.8.2（netavark）、Docker CE 29.9.2。測試容器是 `busybox:1.37`。

這篇記錄 Docker 以外的兩種容器執行方式發佈連接埠時，主機防火牆管不管得到：rootful Podman（以 root 執行、用 netavark 寫防火牆規則）在 Ubuntu 的 ufw 與 Oracle Linux 的 firewalld 上得到相反結果的原因、ufw 的 route 規則放行它的寫法；rootless Docker 與 rootless Podman（以一般使用者執行，核心的網路設定由使用者命名空間裡的程式代辦）發佈的連接埠由主機上的程式接收、受主機防火牆的入站規則管，以及代價：容器看到的來源位址不是真正的來源；最後是清理。以 root 執行的 Docker 在 ufw 主機上的行為見 [ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑](/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/)，在 firewalld 主機上見 [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/)，只放行 CDN 位址的取捨見概念文章 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/infra/03-network-foundation/origin-host-firewall/)。Kubernetes 的 NodePort 沒有測。

## 前置條件與測試來源

- **兩台主機**：一台用 ufw 的 Ubuntu、一台用 firewalld 的 RHEL 系（這次是 Oracle Linux）。OrbStack 的建法是 `orb create ubuntu:noble verify-ufw` 與 `orb create oracle:10 verify-fwd`。兩台的 Docker 都照 Docker 官方套件庫的步驟裝，Podman 用發行版自己的套件（`apt-get install podman`、`dnf install podman`），所以兩台的 Podman 版本不同（4.9.3 與 5.8.2）。下文 rootful Podman 在兩台的結果不同，成因可能是防火牆、也可能是 Podman 的版本，這次沒有拿同一個版本在兩種防火牆上比較來分開兩者。
- **兩個測試來源**：每台都照 [ufw 主機上 Docker 發佈連接埠的實測紀錄：ufw 規則的效果、DOCKER-USER 規則的存續與 after.rules、IPv6 的 docker-proxy、compose 內建 DNS 的出站路徑](/infra/03-network-foundation/hands-on/ufw-docker-walkthrough/) 的〈共用的函式與兩個測試來源〉建 `verify-cf`（`173.245.48.10`，在 Cloudflare 範圍內）與 `verify-other`（`203.0.113.10`，範圍外）兩個 namespace，用同一個 `probe <連接埠>` 函式從兩個來源各連一次。`rc=0  200` 是連上，`rc=7` 是立即回拒，`rc=28  000` 是逾時。
- **網頁檔**：`/var/tmp/verify-fw/www/index.html`，內容隨意（`mkdir -p /var/tmp/verify-fw/www; echo ok > /var/tmp/verify-fw/www/index.html`）。
- **起始狀態**：Ubuntu 那一台從 ufw 那一篇的〈DOCKER-USER 規則的效果…〉之前的狀態接著做：ufw 已經啟用（`ufw default deny incoming`、`ufw --force enable`；雲端主機先 `ufw allow 22/tcp`），Docker 的 `verify-web` 發佈著 8081（下文比較 Docker 與 Podman 時用到）。從一台新機器開始時，照那一篇的〈共用的函式與兩個測試來源〉與〈ufw 的入站規則與 route 規則對發佈連接埠的效果〉的前兩個區塊做到這個狀態。Oracle Linux 那一台只要 firewalld 執行中、`public` zone 是預設值。

## rootful Podman 在 ufw 上：netavark 的轉送鏈、ufw 的預設 routed 政策、route 規則與 DOCKER-USER

ufw 已經啟用、預設拒絕入站，`default routed` 是 Ubuntu 預設的 `deny`（`ufw default deny routed`），沒有任何一條規則提到 8082：

```bash
podman run -d --name verify-pod-web -p 8082:80 -v /var/tmp/verify-fw/www:/www:ro \
  docker.io/library/busybox:1.37 httpd -f -p 80 -h /www
probe 8082
ss -ltnp | grep 8082
iptables -t nat -S | grep 'dport 8082 -j DNAT'
iptables -S NETAVARK_FORWARD
```

```text
  verify-cf     -> :8082  rc=28  000
  verify-other  -> :8082  rc=28  000
LISTEN 0  4096   0.0.0.0:8082   0.0.0.0:*   users:(("conmon",pid=2929,fd=5))
-A NETAVARK-DN-1D8721804F16F -p tcp -m tcp --dport 8082 -j DNAT --to-destination 10.88.0.2:80
-A NETAVARK_FORWARD -d 10.88.0.0/16 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A NETAVARK_FORWARD -s 10.88.0.0/16 -j ACCEPT
```

Podman 用全名 `docker.io/library/busybox:1.37`，因為它不像 Docker 預設到 Docker Hub 找短名稱的映像。netavark 跟 Docker 一樣用 [DNAT](/infra/knowledge-cards/dnat/) 把 8082 改寫成容器的 80，封包走轉送路徑。差別在轉送鏈：netavark 的 `NETAVARK_FORWARD` 只放行「送往容器網路的回程」與「容器送出的」，新的入站連線不在其中，封包往下落到 ufw 的鏈，最後被 FORWARD 的預設政策 DROP 丟掉，兩個來源都逾時。`conmon`（Podman 監看容器的程式）聽著 `0.0.0.0:8082`，它只是佔住這個連接埠，連線不經過它。

實測的順序跟上面相反：容器建好時這台的 routed 是 `allow`（FORWARD 的預設政策是 ACCEPT），第一次 `probe 8082` 兩個來源都拿到 200；改成 `deny routed` 之後才量到上面的兩個逾時。所以 routed 政策是 `allow` 時兩個來源都連得到，是 `deny` 時都連不到。

要只放行 Cloudflare，用 ufw 的 route 規則寫在轉送路徑上，目的地寫容器的位址與容器內的連接埠（位址轉換之後的值）：

```bash
ufw default deny routed
ufw route allow proto tcp from 173.245.48.0/20 to 10.88.0.2 port 80
probe 8082
```

```text
  verify-cf     -> :8082  rc=0  200
  verify-other  -> :8082  rc=28  000
```

只有範圍內的來源連得到。`10.88.0.2` 是容器的位址，取自上面那條 DNAT 規則的 `--to-destination`；容器重建之後位址可能變，規則要跟著改，這是 route 規則寫在位址轉換之後的代價。同一台主機上 Docker 的 8081 在 `deny routed` 下照樣對兩個來源開放（Docker 的 `DOCKER-FORWARD` 排在 ufw 的鏈之前、先接受了），所以同一台主機上 Docker 與 Podman 對同一條 ufw 設定的結果相反。

主機上也裝了 Docker 時，Podman 的轉送封包也經過 `DOCKER-USER`。為了只看 `DOCKER-USER` 的效果，先把 route 規則與 8082 的容器拿掉、routed 改回 `allow`（否則 FORWARD 的 DROP 會先把兩個來源都擋下），再發佈一個 8089 並看跳轉順序：

```bash
podman rm -f verify-pod-web
ufw route delete allow proto tcp from 173.245.48.0/20 to 10.88.0.2 port 80
ufw default allow routed
podman run -d --name verify-pod-web -p 8089:80 -v /var/tmp/verify-fw/www:/www:ro \
  docker.io/library/busybox:1.37 httpd -f -v -p 80 -h /www
iptables -S FORWARD | grep -- '-j' | head -3
iptables -I DOCKER-USER -p tcp -m conntrack --ctorigdstport 8089 --ctdir ORIGINAL ! -s 173.245.48.0/20 -j DROP
probe 8089
iptables -D DOCKER-USER -p tcp -m conntrack --ctorigdstport 8089 --ctdir ORIGINAL ! -s 173.245.48.0/20 -j DROP
```

```text
-A FORWARD -m comment --comment "netavark firewall plugin rules" -j NETAVARK_FORWARD
-A FORWARD -j DOCKER-USER
-A FORWARD -j DOCKER-FORWARD
  verify-cf     -> :8089  rc=0  200
  verify-other  -> :8089  rc=28  000
```

FORWARD 先跳 `NETAVARK_FORWARD`，那裡不接受新的入站連線，封包回到 FORWARD 往下走，接著跳 Docker 的 `DOCKER-USER`；這一條跳轉沒有比對條件，所有轉送的封包都會進去。所以同一條比對原始目的連接埠的規則，對 Podman 發佈的連接埠一樣有效，範圍外的來源被擋。主機上沒有裝 Docker 時沒有 `DOCKER-USER` 這條鏈，這個寫法用不了（依鏈的建立者推論，沒有在沒裝 Docker 的主機上實跑）。量完以 `ufw default deny routed` 改回 routed 政策。

## rootful Podman 在 firewalld 上：netavark 的 nftables 表、trusted zone 與 firewalld 的轉送鏈

Oracle Linux 那一台的 `public` zone 沒有任何規則提到 8089：

```bash
podman run -d --name verify-pod-web -p 8089:80 -v /var/tmp/verify-fw/www:/www:ro,Z \
  docker.io/library/busybox:1.37 httpd -f -p 80 -h /www
probe 8089
nft list tables
firewall-cmd --get-active-zones
nft list chain inet netavark FORWARD
nft list chain inet firewalld filter_FORWARD | sed -n 2,5p
iptables -S FORWARD | head -1
```

```text
  verify-cf     -> :8089  rc=0  200
  verify-other  -> :8089  rc=0  200
table ip nat
table ip filter
table ip6 nat
table ip6 filter
table ip raw
table inet firewalld
table inet netavark
docker
  interfaces: docker0
public (default)
  interfaces: eth0
trusted
  sources: 10.88.0.0/16
	chain FORWARD {
		type filter hook forward priority filter; policy accept;
		jump NETAVARK-ISOLATION-1
		ip daddr 10.88.0.0/16 ct state established,related accept
		ip saddr 10.88.0.0/16 accept
	}
		type filter hook forward priority filter + 10; policy accept;
		ct state { established, related } accept
		ct status dnat accept
		iifname "lo" accept
-P FORWARD ACCEPT
```

`-v` 的 `:Z` 讓 Podman 替掛進去的目錄改 SELinux 標籤（Oracle Linux 預設啟用 SELinux）；Ubuntu 沒有 SELinux，不需要。兩個來源都連得到。Podman 5.8.2 的 netavark 在這台用 nftables 寫自己的表 `inet netavark`，並把容器網路 `10.88.0.0/16` 加進 firewalld 的 `trusted` zone 的來源。一個轉送的封包要通過每一張表接在 forward hook 上的鏈，三張都放它過去：netavark 的 FORWARD 鏈預設政策是 accept、iptables 的 FORWARD 鏈（這台裝了 Docker，表是 Docker 經由 iptables-nft 建的）預設政策是 ACCEPT、firewalld 的轉送鏈有 `ct status dnat accept`。

Ubuntu 那一台被擋，是因為 ufw 把 iptables 的 FORWARD 預設政策設成 DROP；這一台的 firewalld 對經過位址轉換的連線一律接受。兩台的 Podman 版本也不同（見〈前置條件與測試來源〉），版本與防火牆的影響沒有分開。限制的寫法依同樣的路徑推論跟 Docker 在 firewalld 上的相同（自己的 nftables 表掛在位址轉換之前、雲端防火牆），沒有對 Podman 實跑。這台也裝了 Docker，iptables 的 FORWARD 鏈有跳到 `DOCKER-USER` 的那一條，依 Ubuntu 那一台的結果推論 `DOCKER-USER` 的規則同樣管得到 Podman 的轉送封包，在這一台沒有實跑。firewalld 的 `StrictForwardPorts=yes` 對 Podman 的效果沒有測。

從兩個帶 IPv6 位址的來源對主機的 IPv6 位址連 8089（namespace 加 IPv6 位址的做法同 ufw 那一篇的〈IPv6 那一份發佈：docker-proxy 的接收路徑與 ufw 入站規則的效果〉），兩個都立即被回拒：`ss -ltnp` 裡 `conmon` 只聽 `0.0.0.0:8089`，Podman 沒有替 IPv6 發佈這個連接埠，連線落到 `public` zone 的回拒。

## rootless Docker：rootlesskit 的接收路徑、ufw 入站規則與容器看到的來源位址

rootless 模式的 dockerd 以一般使用者執行，它不能改主機的 iptables，發佈連接埠改由 RootlessKit（rootless 模式替 dockerd 代辦網路的程式）在主機上聽那個連接埠、收下連線再轉進容器。安裝與啟動（以 root 建使用者、以那個使用者執行設定工具）：

```bash
apt-get install -y docker-ce-rootless-extras uidmap
useradd -m -s /bin/bash verifyrl
loginctl enable-linger verifyrl             # 讓這個使用者的 systemd user 服務在沒有登入時也執行
U=verifyrl; X=/run/user/$(id -u $U)
cd /tmp                                     # 一般使用者讀不了 /root，原因寫在指令之後
sudo -u $U XDG_RUNTIME_DIR=$X DBUS_SESSION_BUS_ADDRESS=unix:path=$X/bus dockerd-rootless-setuptool.sh install
sudo -u $U XDG_RUNTIME_DIR=$X DOCKER_HOST=unix://$X/docker.sock bash -lc 'cd ~; mkdir -p www; echo ok > www/index.html;
  docker run -d --name verify-rl-web -p 8083:80 -v ~/www:/www:ro busybox:1.37 httpd -f -v -p 80 -h /www'
probe 8083
ss -ltnp | grep 8083; iptables -t nat -S | grep -c 8083
```

`verifyrl` 是這次建的測試使用者，換成實際要跑 rootless Docker 的帳號。`XDG_RUNTIME_DIR` 與 `DBUS_SESSION_BUS_ADDRESS` 指向那個使用者的 systemd user 執行環境，設定工具要用它們建立 user 服務；`DOCKER_HOST` 指到 rootless dockerd 的 socket，否則 `docker` 指令會去連 root 的那一個。httpd 的 `-v` 讓它逐筆印存取紀錄，下面用它看容器收到的來源位址。這台 OrbStack 的核心沒有 AppArmor（`aa-status` 回 `apparmor not present`），所以碰不到 Ubuntu 24.04 對非特權 user namespace 的限制；Docker 的〈Rootless mode troubleshooting〉寫明，在 Ubuntu 24.04 以後的發行版核心上，以 deb 套件裝 `docker-ce-rootless-extras` 時 rootlesskit 的 AppArmor profile 已經隨 `apparmor` 套件附上（這台的 `/etc/apparmor.d/` 也有 `rootlesskit` 這個檔），改用安裝腳本裝時要照那一頁手動加 profile，在發行版核心上沒有實跑。

```text
  verify-cf     -> :8083  rc=28  000
  verify-other  -> :8083  rc=28  000
LISTEN 0  4096   0.0.0.0:8083   0.0.0.0:*   users:(("rootlesskit",pid=4085,fd=13))
LISTEN 0  4096      [::]:8083      [::]:*   users:(("rootlesskit",pid=4085,fd=15))
0
```

nat 表裡沒有 8083 的位址轉換（`0`），聽 8083 的是主機上的 `rootlesskit`。連線送到主機上的程式，走的是 input 路徑，ufw 的預設拒絕入站擋下兩個來源。加一條入站規則：

```bash
ufw allow from 173.245.48.0/20 to any port 8083 proto tcp
probe 8083
sudo -u verifyrl XDG_RUNTIME_DIR=/run/user/$(id -u verifyrl) DOCKER_HOST=unix:///run/user/$(id -u verifyrl)/docker.sock \
  bash -lc 'docker logs verify-rl-web 2>&1 | tail -1'
```

```text
  verify-cf     -> :8083  rc=0  200
  verify-other  -> :8083  rc=28  000
[::ffff:172.17.0.1]:54596: response:200
```

ufw 的入站規則對 rootless Docker 發佈的連接埠有效。IPv6 那一份也由 rootlesskit 聽著（`[::]:8083`），依同一條路徑推論受 ufw 的 IPv6 入站規則管，沒有實跑。代價在最後一行：busybox httpd 記下的連線來源是 `172.17.0.1`（rootless dockerd 自己網路裡的閘道），不是 `173.245.48.10`。預設設定下來源位址沒有保留，容器裡的網站程式依來源位址做的事（存取紀錄、速率限制、只信任來自 CDN 的 `CF-Connecting-IP`）都拿不到真正的來源。Docker 的〈Rootless mode troubleshooting〉列了保留來源位址的做法，這次都沒有實跑：RootlessKit v3.0 以後，預設的 `builtin` 連接埠轉送在 `~/.config/docker/daemon.json` 寫 `{"userland-proxy": false}` 並重啟之後保留來源位址（文件寫明可能還要載入 `br_netfilter` 模組）；更早的版本改用 `slirp4netns` 轉送方式（環境變數 `DOCKERD_ROOTLESS_ROOTLESSKIT_PORT_DRIVER=slirp4netns`），或 `pasta` 網路加 `implicit` 轉送方式（`DOCKERD_ROOTLESS_ROOTLESSKIT_NET=pasta`、`DOCKERD_ROOTLESS_ROOTLESSKIT_PORT_DRIVER=implicit`，文件標為實驗性、吞吐量比 slirp4netns 好）。環境變數寫在 `~/.config/systemd/user/docker.service.d/override.conf` 的 `[Service]` 底下。

## rootless Podman：rootlessport 的接收路徑、ufw 入站規則與容器看到的來源位址

網頁檔沿用〈rootless Docker：rootlesskit 的接收路徑、ufw 入站規則與容器看到的來源位址〉在 `verifyrl` 家目錄建的 `~/www`；跳過那一節時，在 `cd ~;` 之後先 `mkdir -p www; echo ok > www/index.html`。

```bash
cd /tmp
sudo -u verifyrl XDG_RUNTIME_DIR=/run/user/$(id -u verifyrl) bash -lc 'cd ~;
  podman run -d --name verify-rlp-web -p 8084:80 -v ~/www:/www:ro docker.io/library/busybox:1.37 httpd -f -v -p 80 -h /www'
probe 8084; ss -ltnp | grep 8084
ufw allow from 173.245.48.0/20 to any port 8084 proto tcp; probe 8084
sudo -u verifyrl XDG_RUNTIME_DIR=/run/user/$(id -u verifyrl) bash -lc 'cd ~; podman logs verify-rlp-web 2>&1 | tail -1'
```

```text
  verify-cf     -> :8084  rc=28  000
  verify-other  -> :8084  rc=28  000
LISTEN 0  4096   *:8084   *:*   users:(("rootlessport",pid=4921,fd=11))
  verify-cf     -> :8084  rc=0  200
  verify-other  -> :8084  rc=28  000
[::ffff:10.0.2.100]:59274: response:200
```

`podman logs` 印出的存取紀錄裡，來源是 `10.0.2.100`（`::ffff:` 是 IPv4 位址寫成 IPv6 格式時的前綴，httpd 聽的是 IPv6 的 socket）。那是 slirp4netns（Podman 4.9 文件寫的 rootless 預設網路）在 rootless 網路命名空間裡那張 tap 介面的位址，rootlessport 從這個位址把連線轉進容器。這台的 `podman info` 取不出 rootless 網路的種類，預設是 slirp4netns 是依文件，不是從輸出確認的。跟 rootless Docker 一樣，ufw 的入站規則管得到，容器看不到真正的來源。Podman 5 的 rootless 預設網路改成 pasta，pasta 預設保留來源位址（Podman 5.0 的發行說明），沒有實跑。

兩個 rootless 的指令都先 `cd /tmp`、在使用者的 shell 裡再 `cd ~`：在 `/root` 底下以 `sudo -u` 執行時，第一次跑 rootless Podman 得到 `cannot chdir to /root: Permission denied` 與 `Error: setting up the process`，容器沒有啟動。原因是一般使用者讀不了 `/root`，而 Podman 在這個使用者的身分下要用目前的工作目錄。

## 清理：兩台主機上的容器、測試使用者、ufw 規則、namespace 與暫存目錄

Ubuntu 那一台：

```bash
podman rm -f verify-pod-web
cd /tmp
sudo -u verifyrl XDG_RUNTIME_DIR=/run/user/$(id -u verifyrl) bash -lc 'cd ~; podman rm -f verify-rlp-web;
  DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock docker rm -f verify-rl-web;
  dockerd-rootless-setuptool.sh uninstall'
loginctl disable-linger verifyrl
while pgrep -u verifyrl >/dev/null; do sleep 1; done      # 等 systemd 停掉這個使用者的程序
userdel -r verifyrl
ufw delete allow from 173.245.48.0/20 to any port 8083 proto tcp
ufw delete allow from 173.245.48.0/20 to any port 8084 proto tcp
```

8082 的 route 規則已經在 8089 那一步刪掉。namespace、`verify-web`、`/var/tmp/verify-fw` 與其他 ufw 設定，照 ufw 那一篇的〈清理：容器、ufw 規則、after.rules、namespace 與暫存目錄〉清。Oracle Linux 那一台這一篇只建了 `verify-pod-web` 與兩個 namespace：

```bash
podman rm -f verify-pod-web
firewall-cmd --zone=trusted --list-sources                 # 還列得出 10.88.0.0/16 時接下一行
firewall-cmd --zone=trusted --remove-source=10.88.0.0/16   # 只移除執行中的設定；沒有實跑
ip link del vcf-h; ip link del voth-h; ip netns del verify-cf; ip netns del verify-other
rm -rf /var/tmp/verify-fw
```

firewalld 那一篇的清理段刪的是那一篇自己建的資源（靜態的 dockerd、ipset、nftables 表、`/var/lib/docker`），不要照它整段跑。這兩段清理指令跟實測時的順序不同：實測時兩台的清理分在幾次跑，沒有照這兩段一次跑完。

`disable-linger` 之後，systemd 要過一會兒才停掉那個使用者的 user 服務；實測緊接著跑 `userdel` 時回 `userdel: user verifyrl is currently used by process 2749`、使用者沒有刪掉，所以中間等到 `pgrep -u verifyrl` 沒有輸出。`dockerd-rootless-setuptool.sh uninstall` 只移除 user 服務，印出的提示寫明不刪 Docker 的資料；`userdel -r` 刪掉家目錄時，那些資料（`~/.local/share/docker`）一起刪掉。

firewalld 那一台的 `trusted` zone 裡 `10.88.0.0/16` 的來源由 netavark 在容器網路存在時加入，最後一個用到預設網路的容器刪掉之後是否移除沒有確認。留著的影響是之後任何從 `10.88.0.0/16` 來的連線都由 `trusted` zone 處理、一律放行；這段位址只在主機內部的 Podman 網路上，外部來源用不到它。OrbStack 的機器整台刪掉時兩台一起刪：`orb delete verify-ufw verify-fwd`。

## rootful 與 rootless 的 Docker、Podman：接收路徑、入站規則與容器看到的來源位址

| 執行方式                                           | 接收連線的路徑                                                                                 | 主機防火牆的入站規則是否管得到                                            | 容器看到的來源位址                                                      |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| rootful Docker（參考，見 ufw 與 firewalld 那兩篇） | IPv4 位址轉換後轉送；IPv6 由 docker-proxy 接收（容器網路沒開 IPv6、userland-proxy 預設開著時） | IPv4 管不到；IPv6 管得到（ufw 與 firewalld 都量過）                       | IPv4 是真正的來源；IPv6 是預設網路的閘道 `172.17.0.1`（ufw 那一篇量的） |
| rootful Podman 4.9.3，ufw                          | 位址轉換後轉送；routed 是 deny 時被 FORWARD 的 DROP 擋下，是 allow 時放行                      | 管不到；ufw route 規則管得到，主機也裝了 Docker 時 `DOCKER-USER` 也管得到 | 沒有記錄                                                                |
| rootful Podman 5.8.2，firewalld                    | 位址轉換後轉送，firewalld 接受                                                                 | 管不到                                                                    | 沒有記錄                                                                |
| rootless Docker 29.9.2                             | 主機上的 `rootlesskit`                                                                         | 管得到                                                                    | `172.17.0.1`                                                            |
| rootless Podman 4.9.3                              | 主機上的 `rootlessport`                                                                        | 管得到                                                                    | `10.0.2.100`                                                            |

判斷一種執行方式落在哪一列，先查有沒有規則把那個連接埠的目的地改寫掉，再看誰在聽。改寫規則用 `nft list ruleset | grep 'dport <連接埠>'` 查：它同時列出經由 iptables-nft 寫的表（Docker、Podman 4.9 的 netavark）與原生 nftables 的表（Podman 5.8.2 的 `inet netavark`）。只看 `iptables -t nat -S` 會漏掉後一種：在 Oracle Linux 那一台另發佈一個 8090，`iptables -t nat -S | grep -c 8090` 回 0，`nft list ruleset` 列得出 `tcp dport 8090 dnat ip to 10.88.0.3:80`，同時 `ss -ltnp` 顯示 `conmon` 聽著 8090。查到改寫規則時，就是轉送路徑，結果取決於轉送鏈上每一張表的預設政策，聽著那個連接埠的程式（`conmon`、docker-proxy 的 IPv4 那一份）只是佔住連接埠，不算數；IPv6 的改寫規則（`ip6 nat` 或 `inet` 表裡帶 `ip6` 的那幾條）另外判一次。查不到改寫規則、由一個轉送程式聽著時（rootlesskit、rootlessport、rootful Docker 的 IPv6 那一份聽著的 docker-proxy），才是 input 路徑，入站規則管得到。查表的結果是預測，最終以範圍外的來源實際連一次為準（`probe <連接埠>`）；Kubernetes 的 NodePort 這類多跳改寫沒有測。
