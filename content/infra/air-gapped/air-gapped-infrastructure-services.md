---
title: "斷網環境的基礎服務：DNS、NTP、CA 與 Secret Management"
date: 2026-06-26
description: "斷網環境裡其他所有服務的前提——內部 DNS 做名稱解析、NTP 做時間同步、內部 CA 簽發 TLS 憑證、Vault 管理機密值。這四個服務先部署、其他才能跟上。"
weight: 8
tags: ["infra", "air-gapped", "dns", "ntp", "ca", "vault"]
---

斷網環境裡的 GitLab、Harbor、Prometheus、Nexus 都有一個共同前提：它們需要名稱解析（DNS）才能互相找到、需要時間同步（NTP）才能讓 log 和憑證有效、需要 TLS 憑證（CA）才能走 HTTPS、需要機密儲存（Vault）才能安全管理密碼和 token。這四個是「服務的服務」——沒有它們，其他自建服務要麼無法啟動、要麼只能用不安全的 HTTP 明文通訊。

## Internal DNS：內部名稱解析

斷網環境沒有公開 DNS 可用。內部服務之間的互相引用（GitLab 連 PostgreSQL、Harbor 連 storage backend）如果靠 IP 位址，每次 IP 變動都要改一輪設定。內部 DNS 讓服務用 hostname（`gitlab.internal`、`harbor.internal`）互相引用，IP 變動只改 DNS zone 一處。

### CoreDNS vs BIND

| 面向     | CoreDNS                   | BIND                                   |
| -------- | ------------------------- | -------------------------------------- |
| 設定方式 | Corefile（宣告式、短）    | named.conf（傳統、長）                 |
| 部署方式 | 單一 binary / container   | 系統套件                               |
| 適合情境 | Kubernetes 原生整合、輕量 | 複雜 DNS 需求（split-horizon、DNSSEC） |
| 學習曲線 | 低                        | 中高                                   |

多數斷網環境用 CoreDNS 就夠——zone 檔案放在磁碟上、Corefile 幾行就能啟動。

### 最小設定

```text
# Corefile
internal:53 {
    file /etc/coredns/zones/internal.zone
    log
    errors
}

.:53 {
    forward . /dev/null
    log
}
```

第一個 block 處理 `internal` 域名的查詢、從 zone 檔案回應。第二個 block 攔截所有其他查詢——斷網環境不能轉發到上游 DNS，`forward . /dev/null` 讓非內部域名直接返回 NXDOMAIN 而非 timeout。

```text
; /etc/coredns/zones/internal.zone
$ORIGIN internal.
@       IN SOA  ns1.internal. admin.internal. (
        2026062601 ; serial
        3600       ; refresh
        600        ; retry
        86400      ; expire
        60         ; minimum
)
        IN NS   ns1.internal.
ns1     IN A    10.0.1.10
gitlab  IN A    10.0.1.20
harbor  IN A    10.0.1.21
vault   IN A    10.0.1.22
nexus   IN A    10.0.1.23
prom    IN A    10.0.1.24
grafana IN A    10.0.1.25
ntp     IN A    10.0.1.11
```

新增服務時加一行 A record、重載 CoreDNS（`kill -SIGUSR1 $(pidof coredns)` 或重啟 container）。serial 號遞增讓變更可追蹤。

### 客戶端設定

每台機器的 `/etc/resolv.conf` 指向 CoreDNS 的 IP：

```text
nameserver 10.0.1.10
search internal
```

如果環境有 DHCP server，在 DHCP option 裡配 DNS server 位址，新加入的機器自動取得。沒有 DHCP 就靠 provisioning 腳本或 Ansible playbook 推送。

## NTP：內部時間同步

時間不同步在斷網環境會引發三類問題：log 的時間戳錯亂讓事故排查無法跨機器對齊、TLS 憑證的有效期判斷出錯導致合法憑證被拒絕、以及 Kerberos 等時間敏感的認證協定直接失敗。正常環境從 `pool.ntp.org` 取得時間，斷網環境需要自己的時間源。

### chrony 作為 NTP server

chrony 比傳統的 ntpd 更適合網路不穩或隔離的環境——它的時鐘修正演算法在長時間無外部時間源時仍能保持較準確的漂移補償。

```bash
# /etc/chrony.conf（NTP server 端）
# 斷網環境：沒有上游 NTP、用本機時鐘作為最後手段
local stratum 10
allow 10.0.0.0/8
driftfile /var/lib/chrony/drift
```

`local stratum 10` 宣告「我自己是時間源、但 stratum 很低（精度不高）」。其他機器的 chrony 設定指向這台 server：

```bash
# /etc/chrony.conf（客戶端）
server ntp.internal iburst
makestep 1.0 3
```

`iburst` 讓開機時快速同步、`makestep 1.0 3` 允許前三次校正時跳大步（修正啟動時的大偏差）。

### 高精度需求

如果環境對時間精度有要求（金融交易、工控系統），NTP server 需要硬體時間源——GPS 接收器或原子鐘模組。GPS 天線不需要網路連線、只需要看得到衛星的位置（屋頂或窗邊）。chrony 支援 PPS（Pulse Per Second）輸入、可以達到微秒級精度。

多數斷網環境不需要這個精度——毫秒級一致（chrony 預設行為）對 log 對齊和 TLS 驗證已經足夠。

## Internal CA：內部憑證簽發

斷網環境的每個內部 HTTPS 服務都需要 TLS 憑證。Let's Encrypt 的 ACME challenge 需要連網驗證，在斷網環境無法使用。替代方案是建立內部 CA（Certificate Authority），自己簽發憑證。

### step-ca（Smallstep）

step-ca 是一個輕量的 CA server，支援 ACME 協定——內部服務可以用跟 Let's Encrypt 相同的流程自動申請和續期憑證，只是 ACME server 是內網的 step-ca 而非 Let's Encrypt。

```bash
# 初始化 CA
step ca init --name="Internal CA" --dns="ca.internal" \
  --address=":443" --provisioner="admin"

# 啟動 CA server
step-ca $(step path)/config/ca.json
```

初始化會產生 root CA 和 intermediate CA 的 key pair。root CA 的私鑰是整個信任鏈的根——它的保護等級要最高（離線儲存、存取紀錄）。

### 憑證簽發流程

服務用 ACME client 向 step-ca 申請憑證：

```bash
# 用 step CLI 申請憑證（手動方式）
step ca certificate "gitlab.internal" gitlab.crt gitlab.key

# 用 ACME 自動續期（搭配 certbot 或 step 的 renewal daemon）
step ca renew --daemon gitlab.crt gitlab.key
```

certbot 也能配合 step-ca 使用——把 ACME server URL 從 Let's Encrypt 改成 `https://ca.internal/acme/acme/directory`。已有 certbot 自動續期腳本的服務只要改一行設定。

### Root CA 分發

每台機器和每個服務都要信任內部 CA 的 root certificate：

```bash
# Debian/Ubuntu
cp root_ca.crt /usr/local/share/ca-certificates/internal-ca.crt
update-ca-certificates

# RHEL/CentOS
cp root_ca.crt /etc/pki/ca-trust/source/anchors/internal-ca.crt
update-ca-trust
```

Docker daemon 也需要信任內部 CA（否則 `docker pull harbor.internal/image` 會報 TLS 錯誤）：

```bash
mkdir -p /etc/docker/certs.d/harbor.internal
cp root_ca.crt /etc/docker/certs.d/harbor.internal/ca.crt
systemctl restart docker
```

Ansible playbook 批量推送 root CA 到所有機器，是初始部署的標準做法。

### cfssl 作為替代

cfssl（Cloudflare 的 PKI 工具組）比 step-ca 更簡單但沒有 ACME 自動化——每張憑證要手動簽發。適合只有 5-10 個服務、不需要自動續期的小規模環境。

## Secret Management：HashiCorp Vault

資料庫密碼、API token、TLS 私鑰這些機密值需要一個集中的安全儲存。斷網環境不能用 AWS Secrets Manager 或 GCP Secret Manager，HashiCorp Vault 是最常見的自建選項。

### 斷網環境的 Vault 初始化

Vault 的初始化（unsealing）在雲端環境通常用 AWS KMS 或 GCP Cloud KMS 自動 unseal。斷網環境沒有雲端 KMS，退回 Shamir's Secret Sharing——初始化時產生 N 個 unseal key、啟動時需要 M 個 key 才能解鎖（典型設定：5 個 key、3 個即可 unseal）。

```bash
# 初始化 Vault（5 key shares、3 threshold）
vault operator init -key-shares=5 -key-threshold=3

# Unseal（需要 3 次、每次用不同的 key）
vault operator unseal <key-1>
vault operator unseal <key-2>
vault operator unseal <key-3>
```

5 個 unseal key 分別交給不同的人保管。任何單一個人都無法獨自解鎖 Vault——這是刻意的安全設計。Vault 重啟後需要重新 unseal，所以 unseal key 的保管和取用流程要事先演練。

### 機器身分認證

服務從 Vault 讀取 secret 時需要認證自己的身分。雲端環境用 IAM role，斷網環境用 AppRole——每個服務拿到一組 role_id + secret_id、用它們換取短期 token。

```bash
# 建立 AppRole
vault auth enable approle
vault write auth/approle/role/gitlab \
  token_ttl=1h \
  token_max_ttl=4h \
  policies=gitlab-secrets

# 服務端取得 token
vault write auth/approle/login \
  role_id="$ROLE_ID" \
  secret_id="$SECRET_ID"
```

secret_id 本身也是 secret——初次部署時由 Vault admin 手動提供給服務、或透過 Ansible 的 encrypted variable 推送。

### 儲存後端

Vault 需要一個持久化的儲存後端。雲端用 DynamoDB 或 Consul，斷網環境用：

| 後端       | 適用情境               | 特性                                |
| ---------- | ---------------------- | ----------------------------------- |
| 檔案系統   | 單節點、小規模         | 最簡單、但沒有 HA                   |
| PostgreSQL | 已有 PostgreSQL 的環境 | 利用現有基礎設施                    |
| Consul     | 需要 HA 的環境         | Vault + Consul 是官方推薦的 HA 組合 |

## 部署順序的相互依賴

四個服務之間有依賴鏈：

```text
DNS → NTP → CA → Vault
 ↑_________________↓（Vault 的 FQDN 要 DNS 解析）
```

DNS 先啟動（其他服務靠它解析 hostname）→ NTP 跟著（CA 簽發憑證時需要準確的時間、否則 notBefore/notAfter 判斷會出問題）→ CA 啟動（Vault 的 HTTPS 需要 TLS 憑證）→ Vault 最後（依賴 DNS 和 TLS）。

DNS 跟 CA 之間有一個循環依賴：CA 簽發憑證時需要 DNS 解析（ACME challenge 或 CSR 裡的 SAN），但 DNS server 本身要不要 TLS？解法是 DNS 第一次啟動時用明文（不走 HTTPS），CA 啟動後回頭替 DNS 簽一張憑證、再切到 DNS-over-TLS。多數內網環境 DNS 維持明文即可——DNS 查詢在內網不加密是常見做法，風險可控。

## 時程與維護

| 服務    | 初始部署 | 持續維護                                 |
| ------- | -------- | ---------------------------------------- |
| CoreDNS | 2-4 小時 | 新增服務時加 zone record（分鐘級）       |
| chrony  | 1-2 小時 | 幾乎不需要（漂移補償自動運作）           |
| step-ca | 3-4 小時 | 憑證到期前的監控和續期（自動化後接近零） |
| Vault   | 4-8 小時 | unseal key 管理、policy 更新、備份       |

四個服務合計約 1.5-2 個工作天完成初始部署。部署完成後的日常維護負擔集中在 Vault（unseal key 管理和 policy 維護）和 DNS zone 更新。CA 的憑證續期如果用 ACME 自動化就接近零維護。

向管理層溝通時的框架：「這四個服務是所有其他服務的地基——沒有它們，其他服務要麼找不到彼此（DNS）、時間對不上（NTP）、通訊不加密（CA）、密碼寫在設定檔裡（Vault）。部署一次、之後幾乎自動運作。」

## 跨分類引用

- → [斷網環境的通用原則](/infra/air-gapped/air-gapped-principles/)：content ferry 和離線套件管理的通用操作模式
- → [斷網環境的 IaC](/infra/air-gapped/air-gapped-iac/)：Vault 作為 Terraform 的 secret backend
- → [斷網環境的容器與映像管理](/infra/air-gapped/air-gapped-container/)：Harbor 依賴 DNS 和 TLS、映像拉取需要信任內部 CA
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：Vault 的角色跟雲端的 Secrets Manager 對應
- → [模組八：治理好習慣](/infra/08-governance-habits/)：Secret 不進 code 的原則在斷網環境用 Vault 落地
