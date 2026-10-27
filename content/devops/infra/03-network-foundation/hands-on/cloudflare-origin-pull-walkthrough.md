---
title: "Cloudflare 回源的實測紀錄：Oracle Cloud NSG 只放行 Cloudflare 位址與規則數上限、回源的來源位址、Authenticated Origin Pulls、Worker 偽造 CF-Connecting-IP 與 Tunnel 的出站連接埠"
date: 2026-10-26
description: "源站要放在 Cloudflare 後面、想確認只放行 Cloudflare 位址的雲端防火牆放不放得下整份清單、回源實際用哪些位址、Authenticated Origin Pulls 怎麼驗證、Cloudflare Worker 能不能穿過這道防火牆並偽造 CF-Connecting-IP、或 Tunnel 要開哪些出站連接埠時，查 Oracle Cloud 與 Cloudflare 免費方案上實際跑過的指令與輸出"
weight: 4
tags: ["infra", "network", "firewall", "cloudflare", "oracle-cloud", "nginx", "hands-on"]
aliases: ["/infra/03-network-foundation/hands-on/cloudflare-origin-pull-walkthrough/"]
---

> **事件說明**：2026-10-25 到 26 日，用 Cloudflare 免費方案的帳號與一個已經加進 Cloudflare 的網域（原本只有郵件路由的紀錄），源站是 Oracle Cloud `ap-batam-1` 區域新建的一台 A1 主機（Arm、Oracle Linux 10.2、1 OCPU、6 GB），放在新建的公開子網路、有公開 IPv4，VCN 沒有開 IPv6。nginx 1.26.3（Oracle Linux 的套件），cloudflared 2026.10.3（Cloudflare 在 GitHub 發佈的 RPM），wrangler 4.152.0（以 `npx` 執行）。

這篇記錄把一台源站（實際跑網站程式的主機）接到 Cloudflare 後面、實際讓 Cloudflare 回源（[CDN](/devops/infra/knowledge-cards/cdn/) 從自己的機房連回源站取回應）時量到的結果：Oracle Cloud 的 NSG（network security group，套在網卡上的一組放行規則，跟 AWS 的 [Security Group](/devops/infra/knowledge-cards/security-group/) 是同一類）只放行 Cloudflare 的 IPv4 清單，以及 NSG 的規則數上限與每次 API 呼叫能加的規則數、GCP 與 AWS 文件寫的上限；源站的 nginx 設定與從 Cloudflare 範圍外直連的結果；網域的 DNS 紀錄經由 Cloudflare 代理之後，回源連線實際的來源位址與它們落在公布清單的哪一段；Authenticated Origin Pulls（AOP，Cloudflare 回源時出示用戶端憑證，也就是 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 的雙向驗證）在 nginx 上的驗證與拒絕沒有憑證的連線；Cloudflare Worker 從 Cloudflare 的位址連到源站、並在請求裡偽造 `CF-Connecting-IP` 時源站收到什麼（用的是自己的帳號，連一個不屬於任何 Cloudflare 網域的主機名稱）；Cloudflare Tunnel 的 quick tunnel 在源站沒有任何入站放行時的連線方式、預設的協定，以及出站擋掉 UDP 7844、TCP 7844 之後的結果；清理與 Cloudflare 設定的還原。這些限制各自擋得住什麼、要放在雲端防火牆、主機防火牆還是 Cloudflare 端，寫在概念文章 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/devops/infra/03-network-foundation/origin-host-firewall/)；主機防火牆上只放行 Cloudflare 位址的寫法在 [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/devops/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/)。

## 前置條件：Cloudflare 的網域、有公開 IP 的源站與本機的工具

- **一個加進 Cloudflare 的網域**：免費方案就夠。實測只新增一筆子網域的 A 紀錄（下文的 `verify-origin.<網域>`），網域原有的紀錄不動；SSL/TLS 模式與 AOP 是整個網域的設定，改之前先記下原值，測完照原值還原（〈清理與 Cloudflare 設定的還原〉）。網域上有正在服務的網站時，改 SSL/TLS 模式會影響它，要另外評估或用一個沒有在用的網域。
- **一台有公開 IP、能連外的主機**：Cloudflare 回源要連得到源站，Tunnel 要源站連得出去，所以主機要在有 internet gateway 的公開子網路。只有 service gateway 的私有子網路（例如 [Oracle Cloud 建立主機的實測紀錄：建立前的檢查、前置網路、主控台各分頁的 Always Free 設定值、等效的 CLI 指令、容量不足的重送、Bastion 工作階段逾時、Run Command 補公鑰的嘗試與重建後經由 port forwarding 登入](/devops/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/) 建的那一種）兩件事都做不到，下文在一個既有的 VCN 裡另建公開子網路與一台新主機。原本想用永久免費的 `VM.Standard.E2.1.Micro`：`oci limits resource-availability get` 回 `available: 2`，但 `oci compute shape list --availability-domain <AD>` 列出的 shape 裡沒有它（`<AD>` 是 availability domain 的名稱，`oci iam availability-domain list` 查得到），ap-batam-1 不提供這個 shape，改用同樣在免費額度內的 A1（`VM.Standard.A1.Flex`，1 OCPU、6 GB）。
- **本機的工具**：OCI CLI（以 session token 登入，做法見 [從本機用 OCI CLI 操作 Oracle Cloud：session token 登入、時效與 API 簽章金鑰](/devops/infra/cloud-providers/oracle-cloud/cli-session-login/)）、`npx`（Node.js 附的，執行 wrangler 用），以及 SSH 金鑰。
- **wrangler 登入與 workers.dev 子網域**：`npx wrangler login` 會開瀏覽器做 OAuth 授權，由帳號的擁有者自己按。Worker 要部署到 `*.workers.dev` 之前，帳號要先有一個 workers.dev 子網域；這次的帳號還沒有，`wrangler deploy` 回 `Could not automatically register "worker" as your workers.dev subdomain because the name is unavailable`，它給的註冊網址（`/workers/onboarding`）在主控台回 404。打開主控台的 Workers & Pages 頁面之後，頁面的 Account details 列出了一個以帳號名稱建的子網域，再 `wrangler deploy` 就成功了；子網域是打開頁面時自動建的，還是更早就有，沒有分辨。

## 公開子網路、只放行 Cloudflare 的 NSG 與它的規則數上限

這一步在 VCN 裡建出一條對外的路：internet gateway、預設路由指向它的 route table、只放行管理者自己 SSH 的 security list、公開子網路，以及一個只放行 Cloudflare IPv4 到 80 與 443 的 NSG。`<C>`、`<V>` 是 compartment 與 VCN 的 OCID，`<管理者的公開 IP>` 是自己這台電腦連外時的公開位址（`curl -s https://ifconfig.me` 查得到）：

```bash
export OCI_CLI_AUTH=security_token
IGW=$(oci network internet-gateway create -c <C> --vcn-id <V> --is-enabled true --display-name verify-igw \
  --wait-for-state AVAILABLE --query data.id --raw-output)
RTP=$(oci network route-table create -c <C> --vcn-id <V> --display-name verify-public-rt \
  --route-rules "[{\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$IGW\"}]" \
  --wait-for-state AVAILABLE --query data.id --raw-output)
SLP=$(oci network security-list create -c <C> --vcn-id <V> --display-name verify-public-sl \
  --ingress-security-rules '[{"protocol":"6","source":"<管理者的公開 IP>/32","tcpOptions":{"destinationPortRange":{"min":22,"max":22}}}]' \
  --egress-security-rules '[{"protocol":"all","destination":"0.0.0.0/0"}]' \
  --wait-for-state AVAILABLE --query data.id --raw-output)
SNP=$(oci network subnet create -c <C> --vcn-id <V> --cidr-block 10.0.2.0/24 --display-name verify-public-subnet \
  --dns-label pub --prohibit-public-ip-on-vnic false --route-table-id "$RTP" --security-list-ids "[\"$SLP\"]" \
  --wait-for-state AVAILABLE --query data.id --raw-output)
NSG=$(oci network nsg create -c <C> --vcn-id <V> --display-name verify-origin-cf \
  --wait-for-state AVAILABLE --query data.id --raw-output)
```

五個變數存著新建資源的 OCID，後面的 NSG、主機與清理都用到它們；只存在這個 shell 裡，換了 shell（實測橫跨兩天）時用顯示名稱查回來，例如 `NSG=$(oci network nsg list -c <C> --display-name verify-origin-cf --query 'data[0].id' --raw-output)`，其餘四種資源的 `list` 子命令同樣接受 `--display-name`（這幾行查詢沒有實跑）。session token 預設一小時過期，過期之後照 [從本機用 OCI CLI 操作 Oracle Cloud：session token 登入、時效與 API 簽章金鑰](/devops/infra/cloud-providers/oracle-cloud/cli-session-login/) 的〈Session token 的時效與 refresh〉延長或重新登入。`10.0.2.0/24` 是 VCN 的 `10.0.0.0/16` 裡一段還沒用過的位址，換成自己 VCN 裡沒有被其他子網路佔用的一段。security list 套在整個子網路上，這裡只放 SSH；網站的 80 與 443 放在 NSG，NSG 只套在指定的網卡上，同一個子網路裡別的主機不會因此對 Cloudflare 開放。出站全放行，cloudflared 與套件安裝要用。

NSG 的規則每一條只放一段來源與一個連接埠範圍，Cloudflare 的 15 段 IPv4 對 80 與 443 各一條，是 30 條，每 25 條分一批送：

```bash
curl -s https://www.cloudflare.com/ips-v4 | python3 -c '
import sys, json
nets = sys.stdin.read().split()
rules = [{"direction":"INGRESS","protocol":"6","source":n,"sourceType":"CIDR_BLOCK",
  "tcpOptions":{"destinationPortRange":{"min":p,"max":p}},"description":"cloudflare"} for n in nets for p in (80,443)]
for i in range(0, len(rules), 25):
    open(f"/tmp/verify-nsg-batch{i//25}.json","w").write(json.dumps(rules[i:i+25]))'
for f in /tmp/verify-nsg-batch*.json; do
  oci network nsg rules add --nsg-id "$NSG" --security-rules "file://$f" --query 'length(data."security-rules")'
done
oci network nsg rules list --nsg-id "$NSG" --all --query 'length(data)'
```

```text
25
5
30
```

一次送出 30 條時 API 回 `InvalidParameter`：`Count of security rules to add: 30 cannot be greater than 25`。每一次 `nsg rules add` 最多 25 條，所以 Python 把規則每 25 條寫成一個檔，迴圈逐檔加。`/tmp/verify-nsg-batch*.json` 是本機的暫存檔，加完以 `rm /tmp/verify-nsg-batch*.json` 刪掉。Cloudflare 的清單會變（2026-10-25 是 15 段 IPv4、7 段 IPv6），每次重抓。

NSG 的總規則數另有上限。另建一個空的 NSG（建法同上面的 `nsg create`，顯示名稱用 `verify-limit`），每次加 25 條、目的連接埠 443、來源是 `198.18.x.y/32` 的假位址（`198.18.0.0/15` 是保留給網路設備效能測試的位址段，不會出現在網際網路上），直到被拒：

| 動作                         | 回應                                                        | 加完的總數 |
| ---------------------------- | ----------------------------------------------------------- | ---------- |
| 第 1 到 4 批，每批 25 條入站 | 成功                                                        | 100        |
| 第 5 批 25 條                | `Total security rules count 125 cannot be greater than 120` | 100        |
| 1 條出站                     | 成功                                                        | 101        |
| 19 條入站                    | 成功                                                        | 120        |
| 再 1 條入站                  | `Total security rules count 121 cannot be greater than 120` | 120        |

一個 NSG 最多 120 條，入站與出站合計，跟 Oracle〈Security Rules〉的限制表相同；超過時整批被拒，不是加到滿為止。只放行 Cloudflare 的 IPv4 到 80 與 443 要 30 條，再加 IPv6 的 7 段是 44 條，一個 NSG 放得下；要放行更多連接埠時，條數是「段數 × 連接埠數」，一張網卡最多套 5 個 NSG。security list 的上限是入站 200 條、出站 200 條（同一份文件，不能申請調高），沒有實測。測試用的 NSG 測完以 `oci network nsg delete --nsg-id <verify-limit 的 OCID> --force` 刪掉。

GCP 與 AWS 只查了文件，沒有實測：

| 業者               | 規則的形狀                   | 上限（文件）                                                                                                      | 放 Cloudflare 清單的條數               |
| ------------------ | ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| Oracle Cloud NSG   | 一條一段來源、一個連接埠範圍 | 120 條（入站加出站），實測相同                                                                                    | IPv4 30 條，加 IPv6 共 44 條           |
| AWS security group | 一條一段來源、一個連接埠範圍 | 入站 60 條（IPv4 與 IPv6 分開計算，可申請調高；乘上每張網卡的 security group 數不超過 1000）〔Amazon VPC quotas〕 | IPv4 30 條、IPv6 14 條，各自在 60 之內 |
| GCP VPC 防火牆規則 | 一條可放多段來源與多個連接埠 | 每條最多 5000 段來源，不能調高；一條規則只能是 IPv4 或只能是 IPv6〔Cloud NGFW quotas〕                            | IPv4、IPv6 各 1 條                     |

AWS 的 managed prefix list 被 security group 引用時，以 prefix list 的「最大項數」計入規則數，不是實際的項數（同一份 quotas 文件）。清單的更新三家都要有人或程式去改：Oracle 一條規則只放一段，每次更新是逐條增刪；AWS 規則直接寫位址段時也是逐條增刪，改用自建的 customer-managed prefix list 時更新的是 list 的項目，security group 的規則不動（依文件，沒有實跑）；GCP 改的是那一條規則的來源清單。

## 源站主機：建立、nginx 與從範圍外直連的結果

主機建在公開子網路，帶公開 IP，網卡套上那個 NSG：

```bash
INST=$(oci compute instance launch -c <C> --availability-domain <AD> --display-name verify-origin \
  --shape VM.Standard.A1.Flex --shape-config '{"ocpus":1,"memoryInGBs":6}' \
  --image-id <Oracle Linux 10 aarch64 映像的 OCID> --subnet-id "$SNP" --assign-public-ip true --nsg-ids "[\"$NSG\"]" \
  --ssh-authorized-keys-file <公鑰檔> --wait-for-state RUNNING --max-wait-seconds 900 --query data.id --raw-output)
```

A1 回容量不足（`Out of host capacity`）時要重送，做法見 [Oracle Cloud 建立主機的實測紀錄：建立前的檢查、前置網路、主控台各分頁的 Always Free 設定值、等效的 CLI 指令、容量不足的重送、Bastion 工作階段逾時、Run Command 補公鑰的嘗試與重建後經由 port forwarding 登入](/devops/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/) 的〈重送建立請求：CLI 自己的重送、限流門檻與重送腳本〉；這次第一次送出就建成了。映像的 OCID 用 `oci compute image list -c <C> --operating-system "Oracle Linux" --shape VM.Standard.A1.Flex --sort-by TIMECREATED` 查，第一筆是最新的；這次是 `Oracle-Linux-10.2-aarch64-2026.10.16-0`。主機進入 RUNNING 之後，`oci compute instance list-vnics --instance-id "$INST"` 列出公開 IP，SSH 以 `opc` 登入，再 `sudo -i` 進 root shell：下面在源站上跑的區塊都在這個 root shell 裡（`cat > /etc/…` 的重導向要 root 權限）。

nginx 開兩個服務：80 給一般回源；443 用自簽憑證，之後測 AOP。存取紀錄記下 TCP 連線的來源位址（`$remote_addr`）、Cloudflare 帶來的 `CF-Connecting-IP` 標頭與用戶端憑證的驗證結果：

```bash
dnf -y install nginx openssl
mkdir -p /etc/nginx/verify
openssl req -x509 -newkey rsa:2048 -nodes -days 7 -subj "/CN=verify-origin" \
  -keyout /etc/nginx/verify/self.key -out /etc/nginx/verify/self.crt
curl -sSf https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem -o /etc/nginx/verify/cf-origin-pull-ca.pem
cat > /etc/nginx/conf.d/verify.conf <<'EOF'
log_format verify '$remote_addr cfip=$http_cf_connecting_ip host=$host ssl_client_verify=$ssl_client_verify "$request" $status';
server {
    listen 80 default_server;
    server_name _;
    access_log /var/log/nginx/verify.log verify;
    location / { default_type text/plain; return 200 "verify-origin http from $remote_addr\n"; }
}
server {
    listen 443 ssl default_server;
    server_name _;
    ssl_certificate     /etc/nginx/verify/self.crt;
    ssl_certificate_key /etc/nginx/verify/self.key;
    ssl_client_certificate /etc/nginx/verify/cf-origin-pull-ca.pem;
    ssl_verify_client optional;
    access_log /var/log/nginx/verify.log verify;
    location / { default_type text/plain; return 200 "verify-origin https from $remote_addr client_verify=$ssl_client_verify\n"; }
}
EOF
sed -i 's/listen       80 default_server;/listen       80;/; s/listen       \[::\]:80 default_server;/listen       [::]:80;/' /etc/nginx/nginx.conf
nginx -t && systemctl enable --now nginx
firewall-cmd --permanent --zone=public --add-service=http --add-service=https; firewall-cmd --reload
```

`authenticated_origin_pull_ca.pem` 是 Cloudflare 用來簽 AOP 共用用戶端憑證的 CA，`ssl_client_certificate` 指向它，nginx 才驗得出那張憑證。`ssl_verify_client optional` 先只記錄驗證結果、不拒絕，後面改成 `on`。Oracle Linux 套件附的 `nginx.conf` 自帶一個 `listen 80 default_server` 的 server 區塊，跟 `verify.conf` 的 `default_server` 重複時 `nginx -t` 會失敗，所以 `sed` 拿掉原檔的 `default_server`；拿掉之後 `nginx -t` 仍印 `conflicting server name "_" on 0.0.0.0:80, ignored` 的警告，兩個區塊都用 `_` 當 server_name，不影響結果。主機防火牆開 http 與 https 是因為這次的來源限制放在 NSG；主機防火牆再疊一層只放行 Cloudflare 的寫法見 [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/devops/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/)。

從本機（位址不在 Cloudflare 範圍）直接連源站的公開 IP：

```bash
curl -sS -m 8 -o /dev/null -w '%{http_code}\n' http://<源站的公開 IP>/
curl -sSk -m 8 -o /dev/null -w '%{http_code}\n' https://<源站的公開 IP>/
```

兩條都在 8 秒後逾時，印 `000`：NSG 沒有放行本機的位址，封包在 Oracle 的網路上就被丟掉，主機收不到。管理者的 SSH 走 security list 放行的 22，不受影響。

## DNS 紀錄經由 Cloudflare 代理之後，回源的來源位址

在 Cloudflare 主控台的 DNS → Records 新增一筆紀錄：類型 `A`、名稱 `verify-origin`、IPv4 位址填源站的公開 IP、Proxy status 是 Proxied（橘色雲朵）、TTL 自動（用預設值，沒有比較其他值；依 Cloudflare 的 DNS 文件，Proxied 的紀錄 TTL 由 Cloudflare 決定）。Proxy status 改成 DNS only（灰色雲朵）時，網域直接解析到源站的公開 IP，訪客直連源站，被 NSG 擋下，這次沒有實跑。存好之後從本機連：

```bash
dig +short verify-origin.<網域> A; dig +short verify-origin.<網域> AAAA
for i in $(seq 10); do
  curl -s -m 10 -o /dev/null -w "http %{http_code}\n" http://verify-origin.<網域>/
  curl -s -m 10 -o /dev/null -w "https %{http_code}\n" https://verify-origin.<網域>/
done | sort | uniq -c
curl -s https://verify-origin.<網域>/
```

```text
<Cloudflare 的 IPv4 位址，兩個>
<Cloudflare 的 IPv6 位址，兩個>
  10 http 200
  10 https 200
verify-origin http from 172.69.134.32
```

網域解析到 Cloudflare 的位址（`104.21.0.0/16`、`172.67.0.0/16` 與 `2606:4700::/32` 裡各兩個，每個網域分到的位址不同），Proxied 的紀錄另外有 AAAA，即使源站只填了 IPv4。https 的回應內容寫著 `http from`：這個網域的 SSL/TLS 是自動模式，當時實際套用的是 Flexible（彈性），訪客到 Cloudflare 用 https，Cloudflare 回源用 http 的 80。

連了幾輪之後，把源站的存取紀錄拿回本機，逐筆比對來源位址在不在 Cloudflare 公布的清單裡：

```bash
python3 - verify.log ips-v4.txt <<'EOF'
import sys, ipaddress, collections
nets = [ipaddress.ip_network(n) for n in open(sys.argv[2]).read().split()]
c = collections.Counter(l.split()[0] for l in open(sys.argv[1]) if not l.startswith('127.'))
for ip, n in sorted(c.items()):
    hit = [str(x) for x in nets if ipaddress.ip_address(ip) in x]
    print(f"{ip:16} {n:3}  {hit[0] if hit else '範圍外'}")
EOF
```

`verify.log` 是源站的 `/var/log/nginx/verify.log`，`ips-v4.txt` 是 `https://www.cloudflare.com/ips-v4` 的內容。這次全部測試結束時的結果：

```text
104.22.17.208      3  104.16.0.0/13
104.22.17.80       2  104.16.0.0/13
104.22.20.232      6  104.16.0.0/13
104.22.20.233      3  104.16.0.0/13
108.162.246.209    2  108.162.192.0/18
162.158.167.47     1  162.158.0.0/15
162.158.167.48     4  162.158.0.0/15
172.69.134.32      5  172.64.0.0/13
172.69.23.187      3  172.64.0.0/13
172.71.154.190     1  172.64.0.0/13
172.71.158.118     5  172.64.0.0/13
172.71.158.119     2  172.64.0.0/13
```

37 筆來自 12 個位址，全部落在公布的四段裡，沒有一筆在範圍外；回源用哪些位址依訪客連到的 Cloudflare 機房與時間而變，自己量時清單會不同。`cfip=` 的分布：33 筆是本機的公開 IP（下文的輸出以 `<管理者的公開 IP>` 代替），2 筆是下文 Worker 的請求（`-` 與偽造的 `198.51.100.77` 各 1 筆），另外 2 筆來自 `108.162.246.209`、連的是經由代理的 `verify-origin.<網域>`、AOP 驗證 `SUCCESS`，`cfip` 是 `2a06:98c0:3600::103`，跟下文 Worker 出站時的位址相同。這 2 筆出現在 Tunnel 那一節之後，這次部署的 Worker 程式沒有連這個主機名稱，送出它們的是什麼沒有查明。VCN 沒有開 IPv6、源站只有 A 紀錄，所以回源全部經由 IPv4；源站有 IPv6 時 Cloudflare 是否改用 IPv6 回源，沒有測。

## SSL/TLS 模式「完整」與 Authenticated Origin Pulls

AOP 是 TLS 的用戶端憑證驗證，要求 Cloudflare 用 https 回源，所以先在主控台的 SSL/TLS → Configure 把加密模式從 Automatic 改成 Full（完整：回源用 https，不驗證源站憑證，接受自簽的）。Full (strict) 會驗證源站憑證，自簽的會失敗，要換成 Cloudflare 的 Origin CA 憑證或公開 CA 簽的憑證（依 Cloudflare 文件，沒有實跑）。改完之後回源改到 443，nginx 記到的驗證結果是 `NONE`（沒有出示用戶端憑證）：

```text
172.71.158.118 cfip=<管理者的公開 IP> host=verify-origin.<網域> ssl_client_verify=NONE "GET /?aop=before HTTP/1.1" 200
```

查詢字串 `?aop=before` 只是用來在紀錄裡分辨這一批請求；在 zsh 裡網址要加引號，否則 `?` 被當成萬用字元，zsh 回 `no matches found`、curl 沒有執行。接著在 SSL/TLS → Origin Server → Authenticated Origin Pulls 打開 Global（全域：使用 Cloudflare 共用的用戶端憑證）的開關，再連：

```text
verify-origin https from 172.69.23.187 client_verify=SUCCESS
verify-origin https from 104.22.20.233 client_verify=SUCCESS
```

打開開關之後再連的那一批請求都出示了憑證，驗證成功（開關生效要多久沒有量）。再把 nginx 的 `ssl_verify_client optional;` 改成 `on;`（沒有有效用戶端憑證的連線一律拒絕），`systemctl reload nginx`，各連一次：

```bash
curl -sk https://127.0.0.1/ | grep -o '<title>[^<]*'                            # 在源站上直連，沒有用戶端憑證
curl -s -w ' [%{http_code}]\n' 'https://verify-origin.<網域>/?aop=global-on'       # 在本機，經由 Cloudflare
```

```text
<title>400 No required SSL certificate was sent
verify-origin https from 172.69.23.187 client_verify=SUCCESS
 [200]
```

沒有用戶端憑證的直連被 nginx 回 400，經由 Cloudflare 的照常。從源站自己直連是因為 NSG 擋住了所有非 Cloudflare 的外部來源，外面的直連在 nginx 之前就到不了；這一步量的是 NSG 被拿掉或設錯時，nginx 這一層還擋不擋得住。

Global 用的是所有 Cloudflare 客戶共用的同一張憑證。Cloudflare 的〈Protect your origin server〉寫明，共用憑證只證明請求來自 Cloudflare 的網路：別人用自己的 Cloudflare 帳號把一個網域指向這台源站、也打開 Global 時，那些請求出示的是同一張憑證，nginx 同樣驗證成功。要分辨請求是否由自己的網域送來，就在 Zone-level（區域層級）或 Per-hostname（每個主機名稱）上傳自己的用戶端憑證，nginx 的 `ssl_client_certificate` 改成簽那張憑證的 CA。這兩種沒有實跑，「別人的帳號開 Global 也會通過」是依文件的說法，沒有用第二個帳號實測。

## Cloudflare Worker 送出的請求：出站位址、只放行 Cloudflare 的 NSG 與自己寫的 CF-Connecting-IP

Cloudflare Workers 是跑在 Cloudflare 邊緣的程式，它對外送出的請求從 Cloudflare 的位址出去。任何人都能用免費帳號部署一個 Worker，對任意主機名稱送請求，所以它可以代表「經由別的 Cloudflare 帳號送來的請求」；這次部署在自己的帳號，換成別的帳號時的結果寫在本節最後。Worker 要連一個主機名稱，這次沒有試直接 fetch IP 位址，用的是 `nip.io` 這個公開的 DNS 服務：`<源站 IP 以連字號分隔>.nip.io` 解析到那個 IP。Worker 做三件事：問 `api.ipify.org` 自己出站的位址、連源站、帶著偽造的 `CF-Connecting-IP` 與 `X-Forwarded-For` 再連一次：

```javascript
// index.js
export default {
  async fetch(request) {
    const out = {};
    const t = async (label, url, init) => {
      try { const r = await fetch(url, init); out[label] = { status: r.status, body: (await r.text()).slice(0, 200) }; }
      catch (e) { out[label] = { error: String(e) }; }
    };
    await t("egress_ipify", "https://api.ipify.org?format=json");
    await t("origin_http", "http://<源站 IP 以連字號分隔>.nip.io/");
    await t("origin_http_spoof", "http://<源站 IP 以連字號分隔>.nip.io/spoof",
      { headers: { "CF-Connecting-IP": "198.51.100.77", "X-Forwarded-For": "198.51.100.77" } });
    return new Response(JSON.stringify(out, null, 2), { headers: { "content-type": "application/json" } });
  },
};
```

```toml
# wrangler.toml
name = "verify-origin-probe"
main = "index.js"
compatibility_date = "2026-10-01"
workers_dev = true
```

`compatibility_date` 決定 Worker 執行環境的行為版本，填部署當天或之前的日期；`workers_dev = true` 讓 Worker 部署到 `*.workers.dev` 網址，不用綁自己的網域。`198.51.100.77` 是文件保留位址，代表攻擊者想讓源站相信的訪客位址。部署並呼叫：

```bash
npx wrangler deploy
curl -s https://verify-origin-probe.<帳號的 workers.dev 子網域>.workers.dev/
```

剛註冊 workers.dev 子網域之後的第一次呼叫，curl 回 `sslv3 alert handshake failure`：新子網域的憑證還沒發好；幾分鐘後再呼叫就正常了。

```text
"egress_ipify": { "status": 200, "body": "{\"ip\":\"2a06:98c0:3600::103\"}" },
"origin_http":  { "status": 200, "body": "verify-origin http from 104.22.17.80\n" },
"origin_http_spoof": { "status": 200, "body": "verify-origin http from 104.22.17.80\n" }
```

源站的存取紀錄：

```text
104.22.17.80 cfip=- host=<源站 IP 以連字號分隔>.nip.io ssl_client_verify=- "GET / HTTP/1.1" 200
104.22.17.80 cfip=198.51.100.77 host=<源站 IP 以連字號分隔>.nip.io ssl_client_verify=- "GET /spoof HTTP/1.1" 200
```

Worker 連 `api.ipify.org` 走的是 IPv6，出站位址 `2a06:98c0:3600::103` 落在 Cloudflare 公布的 `2a06:98c0::/29`；連只有 IPv4 的源站時用的是 `104.22.17.80`，落在 `104.16.0.0/13`。連源站的兩次請求都通過了只放行 Cloudflare IPv4 的 NSG。第二筆的 `cfip=198.51.100.77`：Worker 自己寫的 `CF-Connecting-IP` 原封不動送到源站，而連線的來源是 Cloudflare 的位址。

所以「只放行 Cloudflare 的位址之後，就能信任 `CF-Connecting-IP`」這個前提不成立：nginx 以 `set_real_ip_from <Cloudflare 的位址段>` 加 `real_ip_header CF-Connecting-IP` 取訪客位址時，這一筆會被記成 `198.51.100.77`，依訪客位址做的存取紀錄、速率限制與封鎖都被騙過。擋下這一類要靠回源驗證：Zone-level 或 Per-hostname 的 AOP（Worker 對 http 的源站連線不帶用戶端憑證，對 https 的是否帶共用憑證沒有測），或改用 Tunnel、源站不收任何外部的入站連線。這次的 Worker 連的是 http 的 80；源站的 443 用自簽憑證，依推論 Worker 的 fetch 會驗證憑證而失敗，所以沒有測 Worker 對 443 的結果。

這次的 Worker 在自己的帳號裡，但它連的 `nip.io` 不屬於任何 Cloudflare 的網域，請求不經過自己網域的任何設定，依這條路徑推論，換成任何一個免費帳號結果都一樣；沒有用第二個帳號實測。測完刪掉 Worker：`npx wrangler delete --name verify-origin-probe --force`。

## Cloudflare Tunnel：源站不開入站，以及出站要放行的連接埠

Tunnel 由源站上的 cloudflared 主動往外連到 Cloudflare，請求經由這條連線送進來。quick tunnel 不需要帳號：cloudflared 向 Cloudflare 要一個隨機的 `*.trycloudflare.com` 網址，把它接到本機的一個服務。後端只聽本機位址：

```bash
dnf -y install https://github.com/cloudflare/cloudflared/releases/download/2026.10.3/cloudflared-linux-aarch64.rpm
cat > /etc/nginx/conf.d/verify2-tunnel.conf <<'EOF'
server {
    listen 127.0.0.1:8080;
    access_log /var/log/nginx/verify.log verify;
    location / { default_type text/plain; return 200 "verify-origin tunnel backend, remote_addr=$remote_addr cfip=$http_cf_connecting_ip\n"; }
}
EOF
nginx -t && systemctl reload nginx
nohup cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8080 >/var/tmp/verify-tunnel.log 2>&1 &
sleep 10                                    # 等 cloudflared 拿到網址、寫進 log
grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /var/tmp/verify-tunnel.log
grep -E 'Initial protocol|Registered tunnel connection' /var/tmp/verify-tunnel.log
```

`2026.10.3` 是 2026-10-21 發佈的版本，x86 主機換成 `cloudflared-linux-x86_64.rpm`，照抄之前到 GitHub 的 releases 頁看最新版。設定檔叫 `verify2-tunnel.conf` 而不是 `verify-tunnel.conf`：`conf.d` 依檔名排序載入，`-`（0x2D）排在 `.`（0x2E）前面，`verify-tunnel.conf` 會先於 `verify.conf` 載入，它用到的 `log_format verify` 還沒定義，`nginx -t` 失敗。

```text
INF Initial protocol quic
INF Registered tunnel connection connIndex=0 ... ip=198.41.200.13 location=sin22 protocol=quic
```

從本機連印出來的網址，三次都回 200，後端記到的 `remote_addr` 是 `127.0.0.1`（cloudflared 從本機連進來），`cfip` 是本機的公開 IP。後端只聽 `127.0.0.1:8080`，NSG 與主機防火牆都沒有放行 8080：Tunnel 的請求不經過任何入站規則。cloudflared 預設用 QUIC（UDP）連 Cloudflare 的邊緣，連到 `198.41.200.13`，位置是新加坡（`sin22`）。

接著在源站上建一張自己的 nftables 表擋出站，分三步收緊，每一步都要重新啟動 cloudflared、等它試完再量。`--no-autoupdate` 讓 cloudflared 不在測試中途自己更新並重啟。先擋 UDP 7844、協定照預設：

```bash
nft add table inet verify_tunnel
nft add chain inet verify_tunnel output '{ type filter hook output priority filter; policy accept; }'
nft add rule inet verify_tunnel output udp dport 7844 drop
pkill -x cloudflared; sleep 1; nohup cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8080 >/var/tmp/verify-tunnel.log 2>&1 &
sleep 10; grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /var/tmp/verify-tunnel.log
grep -c 'Failed to dial a quic connection' /var/tmp/verify-tunnel.log   # 隔幾分鐘再看一次，數字一直增加
```

從本機連新的網址。實測等了 7 分鐘，失敗計數到 28 次，網址一直回 530。實測用的是一支包著這些指令的腳本；這三個區塊裡的 `grep` 依那次 log 的訊息原文寫成，沒有照這個形式逐條跑過。接著改成 http2、UDP 仍擋著：

```bash
pkill -x cloudflared; sleep 1; nohup cloudflared tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:8080 >/var/tmp/verify-tunnel.log 2>&1 &
sleep 10; grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /var/tmp/verify-tunnel.log
grep -E 'Registered tunnel connection' /var/tmp/verify-tunnel.log
```

最後把 TCP 7844 也擋掉，協定仍是 http2：

```bash
nft add rule inet verify_tunnel output tcp dport 7844 drop
pkill -x cloudflared; sleep 1; nohup cloudflared tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:8080 >/var/tmp/verify-tunnel.log 2>&1 &
sleep 30; grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /var/tmp/verify-tunnel.log; grep -E 'i/o timeout' /var/tmp/verify-tunnel.log | tail -1
```

quick tunnel 每次啟動都拿到不同的網址，每一步都從本機連那一步印出的網址。

| 出站限制           | cloudflared 的啟動參數 | 結果                                                                                                                             |
| ------------------ | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 沒有限制           | 預設                   | QUIC 連上，網址回 200                                                                                                            |
| 擋 UDP 7844        | 預設                   | QUIC 一直失敗（`sendmsg: operation not permitted`），等了 7 分鐘、失敗 28 次，沒有改用 http2；網址回 530（Cloudflare 錯誤 1033） |
| 擋 UDP 7844        | `--protocol http2`     | 經由 TCP 連到 `198.41.192.37:7844`，網址回 200                                                                                   |
| 擋 UDP 與 TCP 7844 | `--protocol http2`     | `dial tcp …:7844: i/o timeout`，沒有連線；網址回 530                                                                             |

擋掉 UDP 時，cloudflared 的預先檢查印出 `suggested_protocol=http2`，但 quick tunnel 的設定是 `protocol:quic`，它照樣只重試 QUIC。所以出站只放行清單的主機上，cloudflared 要的是 7844：UDP 給 QUIC，TCP 給 http2；只開 TCP 時要明確指定 `--protocol http2`（或在設定檔寫 `protocol: http2`）。具名的 tunnel（綁在帳號上、由主控台或設定檔管理）的預設協定是否同樣不自動改用 http2，沒有測。兩個 7844 都擋時，quick tunnel 照樣拿到網址；只擋 UDP 的那兩次，`ss -tanp | grep cloudflared` 列得出取網址那一步的連線是 `104.16.230.132:443`，所以取網址走 443，後續的連線註冊才走 7844。

這一節的限制寫在自建的 nftables 表上，不經過 firewalld，測完 `nft delete table inet verify_tunnel` 拿掉。

## 清理與 Cloudflare 設定的還原

Cloudflare 那一側照建立的反方向還原，每一步看主控台的頁面或查詢結果確認：

1. **Worker**：`npx wrangler delete --name verify-origin-probe --force`，回 `Successfully deleted verify-origin-probe`。帳號的 workers.dev 子網域留著，它沒有費用，是否刪除由帳號擁有者決定。
2. **AOP**：Authenticated Origin Pulls 的 Global 開關關掉。
3. **SSL/TLS 模式**：改回 Automatic SSL/TLS。改回之後頁面顯示「Current encryption mode: Full」：自動模式沿用最後一次的模式，要等下一次自動掃描（頁面寫著下次掃描的日期）才重新判斷，原本實際套用的 Flexible 沒有立刻回來。改回之前網域上沒有其他經過代理的網站紀錄時，這個差別不影響任何流量。
4. **DNS 紀錄**：刪掉 `verify-origin` 那一筆。`dig @<網域的權威 nameserver> verify-origin.<網域> A` 回 `NXDOMAIN`，網域原有的紀錄還在。

Oracle Cloud 那一側，主機要先終止，NSG、子網路、security list、route table、internet gateway 才刪得掉，順序跟建立相反：

```bash
oci compute instance terminate --instance-id "$INST" --preserve-boot-volume false --force
oci compute instance get --instance-id "$INST" --query 'data."lifecycle-state"' --raw-output   # 重複查，直到回 TERMINATED
oci network nsg delete --nsg-id "$NSG" --force --wait-for-state TERMINATED
oci network subnet delete --subnet-id "$SNP" --force --wait-for-state TERMINATED
oci network security-list delete --security-list-id "$SLP" --force --wait-for-state TERMINATED
oci network route-table delete --rt-id "$RTP" --force --wait-for-state TERMINATED
oci network internet-gateway delete --ig-id "$IGW" --force --wait-for-state TERMINATED
```

主機還在時刪其他資源，各自回的錯誤指出是誰還在引用它：NSG 回 `PreconditionFailed`（`cannot be deleted since it still has vnics attached to it`），子網路回 `Conflict`（`references the VNIC`），security list 與 route table 回 `IncorrectState`（`associated with … that is in use`），internet gateway 回 `Conflict`（`The Route Table … references the Internet Gateway`）。這次第一次的終止指令寫在腳本裡、帶 `--wait-for-state TERMINATED` 且輸出被導到 `/dev/null`，執行之後主機還是 RUNNING，後面每一步都回上面的錯誤。原因推定是 `terminate` 的 `--wait-for-state` 只收 work request 的狀態（`ACCEPTED`、`IN_PROGRESS`、`FAILED`、`SUCCEEDED`），不收主機的 `TERMINATED`：2026-10-27 用同一個 CLI 版本（3.95.1）同樣寫成 `TERMINATED` 時，CLI 印 `Invalid value for '--wait-for-state': invalid choice: TERMINATED.`、以 2 結束，請求沒有送出（實跑）；第一次清理時的 stderr 沒有留下，所以那一次的原因是從這次重現推回去的。那支腳本沒有檢查這一條的結束碼，照樣往下跑。要等它刪完，寫成 `--wait-for-state SUCCEEDED --wait-for-state FAILED`（同一天實跑，66 秒 `SUCCEEDED`，見 [Oracle Cloud 主機的暫停與恢復上線實測紀錄：暫停前的基準、收窄入口、停止主機、停止期間的計費與 Cloudflare 的回應、恢復上線的每一步與耗時，以及收尾時 DNS 紀錄與主機的刪除順序](/devops/infra/cloud-providers/oracle-cloud/hands-on/suspend-resume-drill/)〈收尾：DNS 紀錄、主機與網路資源的刪除順序〉）。單獨再下一次不帶等待的終止指令，回應裡帶 `opc-work-request-id`，主機進入 TERMINATING。`--preserve-boot-volume false` 讓開機磁碟一起刪掉，免費額度的區塊儲存才會釋放。刪完之後每一個 `get` 都回 `NotAuthorizedOrNotFound`，主機、子網路與 Cloudflare 上的測試設定都已刪除或還原。

## NSG、回源位址、AOP、Worker 與 quick tunnel 的量測結果

| 項目                                                     | 結果                                                                                                                                        |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| NSG 的規則數                                             | 每次 API 呼叫最多 25 條；一個 NSG 最多 120 條（入站加出站），超過時整批被拒                                                                 |
| 從 Cloudflare 範圍外直連源站                             | NSG 只放行 Cloudflare 的 IPv4 時逾時                                                                                                        |
| 回源的來源位址                                           | 37 筆、12 個位址，全部在公布的 IPv4 清單裡；Flexible 模式回源走 http 的 80                                                                  |
| AOP 的 Global                                            | 開啟後回源出示憑證、驗證 `SUCCESS`；nginx `ssl_verify_client on` 時沒有憑證的直連回 400；共用憑證只證明請求來自 Cloudflare 的網路（依文件） |
| Worker（自己的帳號，連不屬於 Cloudflare 網域的主機名稱） | 出站位址在公布的清單裡，穿過只放行 Cloudflare 的 NSG；它寫的 `CF-Connecting-IP` 原樣送到源站；換成別的帳號依路徑推論相同                    |
| quick tunnel                                             | 後端只聽 127.0.0.1、沒有入站放行也連得到；預設 QUIC（UDP 7844），擋掉 UDP 時不自動改用 http2；`--protocol http2` 用 TCP 7844                |
