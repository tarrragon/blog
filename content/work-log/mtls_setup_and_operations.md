---
title: "mTLS 實際怎麼設定與運維：CA 階層、憑證生命週期、撤銷機制"
date: 2026-05-18
draft: false
description: "拆解 mTLS（雙向 TLS）從 CA 階層設計、憑證簽發、儲存、撤銷到基礎設施整合的完整工程實務，包含 nginx / envoy / service mesh 的設定模式，以及跟 API Key / OAuth 的成本與安全取捨。"
tags: ["security", "mtls", "tls", "pki", "service-mesh", "operations"]
---

## 為什麼專門寫這篇

mTLS（mutual TLS、雙向 TLS）在介紹文章中常被輕描淡寫成「**雙向 TLS 憑證、適合金融醫療**」 — 但實際設定起來、會碰到一連串工程問題：

- 自簽 CA 還是商業 CA？
- 憑證放哪、怎麼 rotate？
- 怎麼撤銷？CRL 還是 OCSP 還是 short-lived cert？
- nginx 設定怎麼寫、service mesh 怎麼整合？
- 跟 API Key、OAuth 比、什麼時候 mTLS 才划算？

這些不是「mTLS 的高級議題」、是**第一次部署就會踩到**的基本問題。

本文拆解 mTLS 的工程實務：

1. **CA 階層**：為什麼要分層、Root CA / Intermediate CA / Leaf cert
2. **憑證生命週期**：簽發、儲存、rotation、撤銷
3. **基礎設施整合**：nginx / envoy / service mesh 設定模式
4. **跟其他 Layer 2 方案的取捨**：何時 mTLS 才是對的選擇

> **本文位置**：本文是 [API 認證的三層信任邊界](/work-log/api_auth_trust_boundaries/) Layer 2 的深入篇之一。主文聚焦「為什麼系統間要獨立 credential」、本文聚焦「用 mTLS 實作這層的具體工程細節」。

---

## mTLS 解什麼問題

### 跟一般 TLS 的差異

一般 TLS（HTTPS）是**單向認證**：

```text
client ────"我要連 example.com"────▶ server
       ◀───server 出示憑證───────── server
       驗證:"這是真的 example.com 嗎"
       ↓
       建立加密通道
```

client 驗證 server、但 server 不驗證 client。Client 是匿名的、靠後續 API Key / token 認證。

mTLS 加上**反向驗證**：

```text
client ──"我要連 example.com、這是我的憑證"──▶ server
       ◀──server 出示憑證───────────────────── server
       
       雙方驗證對方憑證：
       client: "這是真的 example.com 嗎"
       server: "這個 client 是被授權的嗎"
       ↓
       建立加密通道、且雙方都已認證
```

每個 client 有自己的憑證、server 用 CA 信任鏈驗證 client 憑證是否合法。**Client 的身分綁定在 X.509 憑證上、不需要額外的 API Key**。

### mTLS 解的具體威脅

| 威脅                                   | 一般 TLS + API Key       | mTLS                                                   |
| -------------------------------------- | ------------------------ | ------------------------------------------------------ |
| 中間人攔截                             | ✅ TLS 已解              | ✅ TLS 已解                                            |
| 攻擊者用洩漏的 API Key 假冒 client     | ❌ 漏                    | ✅ 需 client 私鑰、無法只憑網路觀察取得                |
| API Key 寫在 client code、被反編譯     | ❌ 漏                    | ✅ 私鑰可放硬體（HSM / TPM / Secure Enclave）          |
| Server 端 per-client credential 被攻陷 | ❌ 漏（API Key DB 外流） | ✅ server 無 per-client secret、僅 CA trust chain 暴露 |
| Client 端被植入、用合法身分滲透        | ⚠️ 部分（rate limit）     | ⚠️ 同樣（需依靠撤銷機制）                               |

mTLS 的核心優勢：**client 端的 private key 是 scope-bound、不跨系統共用**。私鑰理論上不離開 client、且驗證憑藉的是 CA 簽章而非可重用字串、被偷的暴露範圍小於 shared API Key（後者一張被偷可能影響所有依賴它的系統）。

代價是：**PKI 基礎建設複雜**、憑證生命週期管理重、運維成本高。

---

## CA 階層設計

### 為什麼要分層

直覺做法是「**用一張 Root CA 直接簽 client 憑證**」：

```text
Root CA ──signs──▶ client-A.crt
        ──signs──▶ client-B.crt
        ──signs──▶ client-C.crt
        ...
```

問題：**Root CA 的私鑰必須極度小心保管**（離線、HSM、多人簽核）— 因為它一旦洩漏、所有信任這個 Root 的系統都被攻陷、且 Root CA 通常活 10-20 年、撤換成本極高。

如果 Root CA 私鑰要常常拿出來簽 client cert、暴露風險就大幅提高。

解法：**分層**。Root CA 只簽 Intermediate CA、Intermediate CA 負責日常簽發 client cert：

```text
Root CA (offline, 20 年)
    ↓ signs (一次性 / 5-10 年)
Intermediate CA (online, 1-5 年)
    ↓ signs (日常、每張 90 天-1 年)
Leaf certificates (client / server)
```

Root CA 通常**完全離線**（air-gapped 機器、硬體 HSM）、私鑰一年只拿出來簽幾次（簽 Intermediate）。Intermediate CA 才是 online、處理日常簽發。

### 階層帶來的好處

| 好處                         | 機制                                                             |
| ---------------------------- | ---------------------------------------------------------------- |
| Root CA 私鑰暴露次數降到最低 | 只在簽 Intermediate 時用、其他時間離線                           |
| Intermediate 被攻陷可撤換    | Root CA 撤掉該 Intermediate、用新 Intermediate 簽                |
| 可按用途分 Intermediate      | 一個給 server cert、一個給 client cert、一個給 internal services |
| 短 chain 仍可驗證            | client 只信任 Root CA、Intermediate 在 chain 中傳遞              |

### 三種典型部署模式

#### 模式 A：自管 CA

完全自己跑 CA infra：

- Root CA：離線 HSM、年度作業簽 Intermediate
- Intermediate CA：online、用工具如 `step-ca`、`cfssl`、`Vault PKI`、`Smallstep`
- Leaf cert：自動化簽發、短 TTL

適合：純內部系統、不需 public trust、要完全控制 CA infrastructure。

#### 模式 B：商業 CA（DigiCert / Sectigo / Entrust）

買商業 CA 服務、商業 CA 已預埋進所有 OS / browser trust store：

- 適合：需要 public trust（HTTPS server cert、SSL/TLS for end users）
- mTLS client cert 不太用商業 CA — 因為 client cert 通常只在你自己的封閉系統內驗證、不需要 public trust

#### 模式 C：Cloud-managed PKI

雲廠商提供 managed PKI：

- AWS Private CA（ACM PCA）— managed Root + Intermediate
- GCP Certificate Authority Service
- Azure Key Vault Certificates

適合：已在某朵雲、不想自管 CA infra、可接受 vendor lock。

### 自管 CA 的最小工具鏈

如果走模式 A、推薦工具：

| 工具                    | 用途                             | 特性                           |
| ----------------------- | -------------------------------- | ------------------------------ |
| **step-ca**             | Lightweight CA server、支援 ACME | Smallstep 開源、設定簡單       |
| **HashiCorp Vault PKI** | Vault 內建 PKI engine            | 整合 Vault 既有 secret 管理    |
| **cfssl**               | Cloudflare 的 CA toolkit         | CLI-based、適合 build pipeline |
| **OpenSSL**             | 純手工建 CA                      | 維運成本高、適合學習與小規模   |

`step-ca` 是最低門檻的起手選擇 — 一行 `step ca init` 建好整套 CA、自動發 ACME 給 client。

---

## 憑證生命週期

### 簽發

**Server cert 簽發流程**：

```text
1. Server 產生 private key (RSA 2048+ 或 ECDSA P-256)
2. Server 用 private key 產生 CSR (Certificate Signing Request)
3. CSR 送給 CA
4. CA 驗證 CSR 內容（DN、SAN、用途）
5. CA 用 Intermediate CA 私鑰簽 cert
6. 把簽好的 cert 回給 server
7. Server 部署 cert + 自己的 private key
```

**Client cert 簽發流程**：跟 server 一樣、但 SAN 通常是 client identifier（service name、device ID）、不是 hostname。

### 私鑰絕對不離開產生端

關鍵安全原則：**private key 在哪產生、就只在那裡存活**。CA 永遠拿不到 client 的 private key — 只收 CSR（裡面只有 public key）、簽完回去。

實務上常見的錯誤：

- ❌ CA 幫 client 產生 keypair、把 private key 跟 cert 一起寄給 client（密鑰在 CA 經手了）
- ❌ 把 private key 跟 cert 打包成 PKCS12 用 email 寄
- ❌ 把 keypair 放進公共 git repo
- ✅ Client 端產生 keypair、只送 CSR 給 CA、簽完 cert 回來、private key 全程不離開 client

### 儲存

Private key 的儲存等級：

| 方式                                         | 安全等級 | 適合                                         |
| -------------------------------------------- | -------- | -------------------------------------------- |
| Plain file（chmod 600）                      | 低       | dev / staging、無 HSM 的低風險環境           |
| OS keystore（Keychain / Windows Cert Store） | 中       | desktop client、laptop                       |
| HSM（hardware security module）              | 高       | 金融、政府、私鑰永不離開硬體                 |
| Cloud KMS（AWS KMS / GCP KMS）               | 中-高    | cloud-native、private key 進 KMS、簽章用 API |
| TPM / Secure Enclave                         | 高       | mobile / IoT、跟硬體綁定                     |

Production server cert 私鑰至少應該 OS 層保護（檔案權限 + 加密磁碟）、高敏感場景上 HSM。

### Rotation

mTLS 憑證的 rotation 跟 [shared secret rotation](/work-log/shared_secret_rotation/) 概念類似、但有具體差異：

| 維度          | Shared Secret       | mTLS Cert                                                            |
| ------------- | ------------------- | -------------------------------------------------------------------- |
| 過期機制      | 沒有、要手動 rotate | 內建 `notBefore` / `notAfter`、自動過期                              |
| 雙密期        | 兩把同時 valid      | 過渡期 server 同時持有舊 cert（未過期）+ 新 cert（已簽發）、自動有效 |
| Rotation 觸發 | 排程                | 排程 + 過期前自動                                                    |

實務上的 rotation 模式：

**短 TTL + 自動續發（推薦）**：

- Leaf cert TTL 設短（24 小時 ~ 7 天）
- 用 ACME protocol（如 Let's Encrypt 的協定）讓 client 自動續發
- 不需要主動「rotate」— 過期前自動換新

工具：`cert-manager`（K8s）、`step-ca` + `step`、`certbot`。

**中 TTL + 半自動（傳統）**：

- TTL 1 年、年度手動 rotation
- 用工具列管所有 cert 的 `notAfter`、過期前 30 天自動告警
- 適合舊架構、無法跑短 TTL 的場景

**長 TTL（不建議）**：

- TTL 多年、近乎不 rotate
- 私鑰暴露窗極長、被洩漏到察覺的時間差大
- 唯一情境：IoT 設備、無法 OTA 更新

### 撤銷

當 cert 在 `notAfter` 前需要失效（私鑰洩漏、員工離職、合約終止）、需要撤銷機制。有三種主流方案：

#### CRL（Certificate Revocation List）

CA 維護一份「**已撤銷憑證 list**」、定期發佈（小時級到天級）。Client 端要：

1. 下載最新 CRL
2. 連線時檢查對方 cert 是否在 CRL 內

優缺：

- ✅ 簡單、infrastructure 輕
- ❌ CRL 大、下載成本高
- ❌ Cache 期內撤銷不生效（最差幾小時）
- ❌ Client 沒下載 CRL、撤銷完全沒效

#### OCSP（Online Certificate Status Protocol）

Real-time 查詢、client 每次連線時即時 query OCSP responder：「**這張 cert 還有效嗎？**」

優缺：

- ✅ Real-time、撤銷即時生效
- ❌ 每次連線增加一次 OCSP query、延遲
- ❌ OCSP responder 是 single point of failure
- ❌ Privacy 顧慮（每次連線都告訴 CA 你在連誰）

進階：**OCSP Stapling** — server 預先 query OCSP、把結果 staple 在自己的 cert chain 裡、client 不需自己 query。解決延遲跟 privacy、但 server 端要實作。

#### Short-lived cert（不撤銷、讓它過期）

最現代的做法：**cert TTL 極短（小時、甚至分鐘）、不實作撤銷機制、靠過期自然失效**。

優缺：

- ✅ 不需要 CRL / OCSP infrastructure
- ✅ 撤銷窗 = TTL（小時級）、可預期
- ✅ Privacy 友善
- ❌ 需要可靠的自動續發機制
- ❌ Client 無法續發時直接斷線

工具：`SPIFFE`/`SPIRE` 主推這個模式、cert TTL 設小時級。

### 三種撤銷方案的選擇

| 場景                            | 推薦撤銷方案                  |
| ------------------------------- | ----------------------------- |
| 傳統 enterprise、不能變動架構   | CRL（最低門檻）               |
| 公開 HTTPS、需要 real-time 撤銷 | OCSP Stapling                 |
| Cloud-native、有自動續發 infra  | Short-lived cert              |
| 內部 service mesh               | Short-lived cert（mesh 自動） |

---

## 基礎設施整合

### nginx 設定 mTLS server

最常見的場景：nginx 當 reverse proxy、要求 client 出示憑證。

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;

    # Server cert (出示給 client)
    ssl_certificate     /etc/ssl/certs/api.crt;
    ssl_certificate_key /etc/ssl/private/api.key;

    # 要求 client 出示憑證、用這個 CA 驗證
    ssl_client_certificate /etc/ssl/ca/client-ca-chain.pem;
    ssl_verify_client on;            # 強制 client 出示憑證、否則拒絕
    ssl_verify_depth 2;              # 驗證 chain 深度、視 PKI 階層調 (Root → Intermediate → Leaf)

    location / {
        # 把 client cert 資訊傳給後端 application
        proxy_set_header X-Client-DN  $ssl_client_s_dn;
        proxy_set_header X-Client-Verify $ssl_client_verify;
        proxy_pass http://backend;
    }
}
```

關鍵 directive：

| Directive                | 作用                                        |
| ------------------------ | ------------------------------------------- |
| `ssl_client_certificate` | 信任的 CA chain                             |
| `ssl_verify_client on`   | 強制 client 出示憑證、`optional` 則彈性接受 |
| `ssl_verify_depth`       | chain 驗證深度、根據 PKI 階層調             |
| `$ssl_client_s_dn`       | 傳 client cert 的 subject DN 給 backend     |

### nginx 設定 mTLS client（呼叫上游）

當 nginx 是 client、要呼叫上游 mTLS server：

```nginx
location /upstream {
    proxy_pass https://upstream.example.com;
    proxy_ssl_certificate     /etc/ssl/certs/client.crt;
    proxy_ssl_certificate_key /etc/ssl/private/client.key;
    proxy_ssl_trusted_certificate /etc/ssl/ca/upstream-ca.pem;
    proxy_ssl_verify on;
}
```

### Envoy / API Gateway 整合

Envoy 是 service mesh 的常見 data plane、mTLS 設定模式：

```yaml
listeners:
- name: api_listener
  address: { socket_address: { port_value: 443 } }
  filter_chains:
  - transport_socket:
      name: envoy.transport_sockets.tls
      typed_config:
        "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
        common_tls_context:
          tls_certificates:
          - certificate_chain: { filename: /etc/ssl/api.crt }
            private_key:      { filename: /etc/ssl/api.key }
          validation_context:
            trusted_ca: { filename: /etc/ssl/client-ca.pem }
        require_client_certificate: true
```

> 上方只展 inbound listener 的 `DownstreamTlsContext`。Envoy 作為 client 呼叫上游 mTLS server 時、要在對應的 cluster 配 `transport_socket` + `UpstreamTlsContext`（含 client cert + private key + trusted CA）、不在這份 listener 設定裡。

跟 nginx 比、Envoy 的優勢：

- 動態設定（xDS API、不需 reload）
- 支援 SDS（Secret Discovery Service）動態取憑證
- 跟 Istio / Linkerd 等 mesh 整合

### Service Mesh（Istio / Linkerd）

Service mesh 內建 mTLS：

```yaml
# Istio: 強制 mesh 內所有 service 走 mTLS
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
```

機制：

- Mesh control plane（Istio: Istiod / Linkerd: identity）內建 CA、自動發每個 pod 一張 cert
- Sidecar proxy（Envoy / Linkerd proxy）handle TLS termination、application code 完全不感
- Cert TTL 短（Istio 預設 24 小時、視版本而定）、自動續發
- mTLS identity 綁定 K8s ServiceAccount

優點：**application 完全不用改 code、不用管 cert、不用管 rotation** — mesh 全包。

缺點：**綁定整套 mesh 架構**、運維 mesh 本身是大事、學習曲線陡。

### 為 application 直接做 mTLS

某些場景（沒 mesh、需要 application 級控制）需要 application 直接做 mTLS：

```python
# Python requests 範例 - mTLS client
import requests

response = requests.get(
    'https://api.example.com/data',
    cert=('/path/to/client.crt', '/path/to/client.key'),
    verify='/path/to/server-ca.pem',
)
```

```go
// Go net/http 範例 - mTLS client
cert, err := tls.LoadX509KeyPair("client.crt", "client.key")
if err != nil { return err }

caCert, err := os.ReadFile("server-ca.pem")
if err != nil { return err }
caCertPool := x509.NewCertPool()
caCertPool.AppendCertsFromPEM(caCert)

client := &http.Client{
    Transport: &http.Transport{
        TLSClientConfig: &tls.Config{
            Certificates: []tls.Certificate{cert},
            RootCAs:      caCertPool,
        },
    },
}
resp, err := client.Get("https://api.example.com/data")
```

每個語言的 stdlib 都有對應 API、寫法大同小異。但 application 要自己處理 cert reload、過期、rotation — 比 service mesh 麻煩很多。

---

## 跟其他 Layer 2 方案的成本比較

mTLS 在三層信任邊界的 Layer 2 是「**最安全但最重**」的選項。是否該用、看具體場景：

| 方案                         | 安全等級 | 運維成本 | 適合                         |
| ---------------------------- | -------- | -------- | ---------------------------- |
| **Shared Secret**            | 低-中    | 低       | 純內部、低風險               |
| **API Key + HTTPS**          | 中       | 低       | 一般 SaaS、對外 API          |
| **HMAC 簽章**                | 中-高    | 中       | 需防 replay / tampering      |
| **OAuth Client Credentials** | 中-高    | 中       | 跨組織、需 short-lived token |
| **mTLS**                     | 高       | 高       | 合規、零信任、私鑰可硬體保護 |

### mTLS 才划算的場景

| 場景                                           | 為什麼 mTLS 才划算               |
| ---------------------------------------------- | -------------------------------- |
| 金融、醫療、政府合規要求                       | 合規條款直接要求 mTLS            |
| 零信任網路（zero-trust）                       | 網路不可信、每個 hop 都要驗身分  |
| 內部 service mesh（K8s + Istio）               | Mesh 自動處理、邊際成本低        |
| 私鑰能放硬體（HSM / TPM / Secure Enclave）     | 比 API Key 強得多                |
| 高頻 service-to-service、API Key rotation 痛苦 | 短 TTL cert 自動續發、不用人介入 |

### mTLS 不划算的場景

| 場景                            | 為什麼不划算                                  |
| ------------------------------- | --------------------------------------------- |
| 對外開放給第三方 SDK            | 第三方搞 cert 太困難、用 API Key + HTTPS 對等 |
| 小規模、運維資源少              | PKI infra 維護成本超過安全增益                |
| 純內部、不需強身分隔離          | Shared secret 已經夠用                        |
| 大量短連線 client（mobile app） | Cert 散佈跟 rotation 複雜度高                 |

---

## 常見失敗模式

### 失敗 1：忘記 Intermediate CA、chain 不完整

**症狀**：server 設定看似正確、但 client 連線時報 `certificate verify failed`。

**根因**：server 端只放了 leaf cert、沒附 Intermediate CA。Client 端只信任 Root、無法 chain 到 Root。

**緩解**：server 端 `ssl_certificate` 要放**完整 chain**（leaf + intermediate、不含 root）：

```bash
cat leaf.crt intermediate.crt > chain.crt
# nginx 用 chain.crt 而非單獨 leaf.crt
```

### 失敗 2：Cert 過期、半夜被叫起來

**症狀**：cert `notAfter` 過了、所有 client 突然連不上。

**緩解**：

- 監控 cert 過期時間、提前 30 天告警、提前 7 天緊急告警
- 用自動續發機制（cert-manager / step-ca / ACME）
- 過期不該是「人記得 rotate」、該是系統自動防護

### 失敗 3：私鑰權限不對、被同機其他 user 讀走

**症狀**：security audit 發現 `/etc/ssl/private/server.key` 是 644、所有 user 可讀。

**緩解**：

- Private key 一律 `chmod 600`、owner `root` 或 application user
- 用 systemd 跑的 service、private key 放 `LoadCredential=` 而非 file path
- 定期 audit `/etc/ssl/` 權限

### 失敗 4：撤銷後 cert 仍能用

**症狀**：cert 撤銷了、但 client 還能連上。

**根因**：

- CRL 設定但 server 沒 enable CRL check
- OCSP 設定但 client 沒 query
- 用 short-lived cert 但 TTL 太長、撤銷窗不可接受

**緩解**：撤銷機制要**端到端測試**、不只「設定上有」、要驗證「實際生效」。

### 失敗 5：Service mesh upgrade 後 mTLS 中斷

**症狀**：Istio 升級後、cluster 內部分 service 互相連不上。

**根因**：mesh control plane 的 CA 換了、舊 cert chain 不通。

**緩解**：

- Mesh upgrade 走 staged rollout、不要一次全升
- Mesh 提供的 CA migration 流程要照走、不能跳步驟
- Staging 環境先跑升級流程

---

## 收尾

mTLS 是「**用 PKI 換掉 secret 管理**」的設計 — 私鑰不離 client、身分綁在 X.509 cert 上、不依賴可重用的字串。安全等級高、但代價是要建立 CA infrastructure、處理 cert 生命週期、整合到各種基礎設施。

幾個核心判斷：

1. **CA 分層是基本盤** — Root + Intermediate + Leaf、不要用 Root 直接簽 leaf
2. **私鑰絕不離開產生端** — CA 只簽 CSR、不碰 private key
3. **撤銷方案要實證可用** — CRL / OCSP / Short-lived 三選一、但要驗證真的生效
4. **Service mesh 是 cloud-native 的低成本入口** — Istio / Linkerd 把 mTLS 變成基礎設施、application 不用改
5. **mTLS 不是萬靈丹** — 對外開放 API、小規模、無 mesh 場景、用 OAuth / API Key 更實際

延伸閱讀：

- [API 認證的三層信任邊界](/work-log/api_auth_trust_boundaries/) — 本文的主篇、mTLS 在「Layer 2 系統層」的位置
- [Shared Secret 安全輪替設計](/work-log/shared_secret_rotation/) — 不用 mTLS 走 secret-based 認證的對應 lifecycle 問題
- [Laravel Sanctum 的 Bearer Token 設計剖析](/work-log/laravel_sanctum_pat_design/) — Layer 1 使用者層的 token 機制、跟 mTLS 解的問題不同
