---
title: "HashiCorp Vault Dynamic Credential：lease 治理跟 application 整合的實作層"
date: 2026-05-18
description: "Vault database secrets engine 怎麼配、application 怎麼 renew lease、production 五大踩雷（lease 過期 race、DB max_connections 撞牆、Vault sealed、token expire、scope 過寬）、容量規劃跟 vault-agent injector 整合"
weight: 10
tags: ["backend", "security", "vault", "secrets", "dynamic-credential", "deep-article"]
---

> 本文是 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) overview 的 implementation-layer deep article。Overview 已說明 Vault 在 secrets / credentials 治理譜系的定位（跟 cloud-native secrets manager / cert-manager 的取捨）、本文聚焦 *dynamic credential engine* 的實作層：怎麼配 database engine、application 怎麼 renew lease、production 踩過哪些坑、跟 cloud-native vault 跟 vault-agent injector 怎麼整合。

## 問題情境

Long-lived database credential 寫進 application config 是 production 環境最常見的 secret hygiene 失敗：credential 一旦外洩、輪替成本是 *跨團隊協調 + 多服務同步重啟*、實務上半年才換一次、credential 在 git history / log / dump file 留下軌跡。動態憑證（dynamic credential）的核心承諾是 *credential 生命週期跟 application session 對齊*、用完就 revoke、外洩窗口從幾個月縮到幾分鐘。

但 dynamic credential 不是「換個 SDK 就好」、它把 *credential 治理* 從 secret rotation 問題轉成 *lease lifecycle* 問題。lease TTL 設多久、renewal 怎麼跑、DB 端 user 創建會不會撞 max_connections、Vault sealed 時 application 怎麼降級 — 每個都是 production-grade 議題、無法靠 vendor doc 預設值直接上線。

## 核心概念：lease lifecycle 跟 secrets engine 模型

Vault dynamic credential 由三個元件協作：

| 元件               | 責任                                                                                      |
| ------------------ | ----------------------------------------------------------------------------------------- |
| **Secrets engine** | 後端執行 credential 創建跟 revoke、每個 engine 對應一個 datastore（database / aws / ssh） |
| **Role**           | 創建 credential 的範本：DB 連線 + creation SQL + default / max TTL + allowed_roles        |
| **Lease**          | 每次 credential 發放都對應一個 lease ID、由 Vault 管 TTL / renew / revoke                 |

跟 static secret（K/V store）對照、dynamic credential 的關鍵差異是 *credential 在 read 時才產生*、且 Vault 追蹤每個 outstanding lease；application 必須 *主動 renew* 或接受 credential 失效。

Lease 的兩個 TTL：

- **default_ttl**：credential 初始有效期、application 不 renew 就到期
- **max_ttl**：credential 最長有效期、不管 renew 幾次都不能超過

實務 default 配置：`default_ttl: 1h` + `max_ttl: 24h`、application 每 30-45 分鐘 renew 一次、credential 最多活 24 小時必換新的。

## Step-by-step 配置

### Vault server 啟用 database secrets engine

```bash
# 1. enable secrets engine
vault secrets enable -path=database database

# 2. 配置 PostgreSQL connection
vault write database/config/myapp-prod \
  plugin_name=postgresql-database-plugin \
  allowed_roles="myapp-reader,myapp-writer" \
  connection_url="postgresql://{{username}}:{{password}}@db.internal:5432/myapp?sslmode=require" \
  username="vault_root" \
  password="<vault_root_pw>"

# 3. 創建 role
vault write database/roles/myapp-reader \
  db_name=myapp-prod \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
                       GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"
```

關鍵：`vault_root` 是 Vault 用來創建其他 user 的 *bootstrapping account*、權限要含 `CREATEROLE`、但不需要 SUPERUSER；creation_statements 必須含 `VALID UNTIL '{{expiration}}'`、否則 DB 端 user 不會自動過期、Vault revoke 失敗時會留 zombie account。

### Application 取得 credential

```bash
# Read 動態 credential（每次 read 都產生新 user）
vault read database/creds/myapp-reader
# Key                Value
# lease_id           database/creds/myapp-reader/abc123
# lease_duration     1h
# username           v-myapp-reader-x7y8z9-1747512345
# password           A1b2C3d4E5f6...
```

Application 從 response 拿三個值：`lease_id`（用來 renew / revoke）、`username` + `password`（DB 連線）、`lease_duration`（決定何時 renew）。

### Renew lease

```bash
# 在 lease 到期前 renew（推薦在 50-70% TTL 跑）
vault lease renew database/creds/myapp-reader/abc123
# Key                Value
# lease_id           database/creds/myapp-reader/abc123
# lease_duration     1h    # renew 後重置回 default_ttl
```

`lease_duration` 在 renew 後 *重置回 default_ttl*、但 *不會超過 max_ttl*。例：default 1h / max 24h、application 連 renew 23 小時後、第 24 次 renew Vault 拒絕、application 必須拿新 credential。

### Revoke lease（application shutdown 時）

```bash
# Graceful shutdown 時主動 revoke
vault lease revoke database/creds/myapp-reader/abc123
```

Application 結束時 revoke 是 *credential hygiene 的最後一道閘門* — 即使 lease 還有時間、主動 revoke 讓 DB 端 user 立刻消失、避免 credential 在 application crash dump / log 內被翻出時還能用。

## 故障演練 / 邊界 case

### Case 1：Lease renewal race，credential 中途失效

**徵兆**：application log 突然出現 `FATAL: role "v-myapp-reader-x7y8z9-..." does not exist`、且時間點接近某個整點 / 半點。

**根因**：application 用 lease_duration 推算 renew 時機、但用了 *系統時間* 而非 *lease 簽發時間*；application 啟動晚於 lease 簽發 30 秒、renew 跑在 lease 過期後 5 秒、Vault 已 revoke credential、DB 端 user 已刪除。

**修法**：用 *server 回傳的 lease_duration* 反推 renew 時機、留 *20-30% buffer*。例：lease_duration 3600 秒、application 在 2400-2520 秒（66-70%）開始 renew、不要拖到 3500 秒。Vault SDK 多數有 LifetimeWatcher（Go SDK）或 Renewer（Python hvac）這類 helper、優先用 SDK 不要自管 ticker。

### Case 2：DB max_connections 撞牆

**徵兆**：application 在流量高峰開始大量 `FATAL: too many connections for role`、Vault audit log 顯示新 credential 還在發、PostgreSQL `pg_stat_activity` 看到上百個 `v-myapp-...` user 同時連著。

**根因**：每個 application instance / pod 在啟動時 read 一次 credential、credential lease 1h、但 *application 跑 30 分鐘就重啟*（K8s rolling update / OOM）；舊 user 還在 PostgreSQL 端連著（connection pool 沒釋放）、新 user 又被創建、累積到 max_connections。

**修法**：兩層

1. Application graceful shutdown 時 `vault lease revoke` + connection pool drain
2. PostgreSQL connection pool 加 `pool_lifetime_max` 跟 application instance lifetime 對齊、避免 connection leak 到 lease 失效後仍 holding

### Case 3：Vault sealed 中、existing lease 仍可用但新 lease 拿不到

**徵兆**：deploy 新 version 時、新 pod 起不來、`vault read database/creds/...` 卡住或回 `Vault is sealed`；但 *舊 pod 持續運作正常*（因為已持有 lease）。

**根因**：Vault sealed（master key 被 wrap、需要 unseal key 解封）時、existing lease 因為 *credential 已在 DB 端創建*、application 連線不需要 Vault 介入；但 *新 lease 創建需要 Vault* / *renew 也需要 Vault*。Sealed 期間 application 還能用、但無法擴容、無法 renew。

**修法**：

1. Vault HA cluster + auto-unseal（KMS / HSM auto-unseal）避免人工 unseal 鏈
2. Application 加 retry-with-backoff、Vault 短暫 unavailable 時不要立刻 crash
3. Lease 設長一點（default 4h、max 48h）給 unseal 流程留時間

### Case 4：Application Vault token expire、lease orphan

**徵兆**：application 在連續跑 1-2 週後突然開始 `Permission denied` on `vault lease renew`、credential 在 max_ttl 後失效但 application 不知道。

**根因**：application 的 Vault token（不是 DB credential 的 lease）也有 TTL；token 過期後 application 無法 renew lease、但 application 可能還沒到 *自己拿新 token* 的循環。Lease 變 orphan（沒人能 renew）、TTL 到就被 revoke。

**修法**：

1. Application 用 vault-agent injector / sidecar pattern、由 sidecar 維護 token + lease；application 只讀 file
2. 不用 sidecar 時、application token 用 *renewable token* + 跟 lease 同 lifecycle 管
3. AppRole auth method 的 secret_id 跟 token TTL 都要納入 application reload 流程

### Case 5：[CircleCI 2023 incident](/backend/07-security-data-protection/cases/) 對照 — secret_id scope 過寬

**徵兆**：CircleCI 2023 1 月事件、攻擊者拿到開發者 endpoint session token、進而拿到 Vault AppRole 的 secret_id；secret_id 對應的 policy 含 *跨環境跨資料庫 read*、攻擊者用 secret_id 拿到大量動態 credential。

**根因**：AppRole secret_id 的 policy scope 設成 *single AppRole 服務所有環境*、而不是 *per-environment AppRole*；secret_id 外洩等於拿到全公司 dynamic credential 發放權。

**修法**：

1. Per-environment AppRole：dev / staging / prod 各有獨立 AppRole + secret_id、policy 只允許該環境的 database engine path
2. Secret_id TTL 短化（< 24h）、用 *response wrapping* 傳遞、拿到後立刻 unwrap、減少 secret_id 在 build pipeline log 留軌跡
3. Vault audit log 接 SIEM、`approle/login` 異常 location / IP 即刻 alert

## 容量規劃

Dynamic credential 的容量設計圍繞 *lease churn rate* — 每秒多少新 lease 創建、多少 renew、多少 revoke。

| 維度                 | 估算方式                                                 | 警戒值                                       |
| -------------------- | -------------------------------------------------------- | -------------------------------------------- |
| 新 lease / s         | `應用 instance 數 × (1 / lease_duration)`                | 單 Vault node ~50/s、HA cluster ~200/s       |
| Renew / s            | `outstanding lease × renew_freq`                         | renew 跟 read 同 cost                        |
| DB 端 user 數        | `peak outstanding lease`                                 | 不能超過 DB max_roles 限制                   |
| DB connection 數     | `peak outstanding lease × avg connection per credential` | 不能超過 DB max_connections                  |
| Vault audit log size | 每 lease 操作 ~500 byte、`(新+renew+revoke) × 500B`      | 100 lease/s → 50MB/s audit、SIEM 端要 sizing |

實務 sizing 範例：100 個 application pod、lease_duration 1h、renew at 50% TTL：

- 新 lease：100 / 3600 ≈ 0.03/s（pod 重啟才有）
- Renew：100 / 1800 ≈ 0.06/s
- Outstanding lease：~100 個（每 pod 一個）
- DB user 數：~100 個（peak ~150 含 grace period）
- DB connection：100 × 5（pool size）= 500、需要 PostgreSQL `max_connections >= 600`

超出單 Vault node 容量（~50 ops/s）時、走 Vault HA cluster + auto-unseal、或拆 namespace。

## 整合 / 下一步

### vault-agent injector（K8s 環境推薦）

```yaml
# pod annotation
metadata:
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/role: "myapp-reader"
    vault.hashicorp.com/agent-inject-secret-db-creds: "database/creds/myapp-reader"
    vault.hashicorp.com/agent-inject-template-db-creds: |
      {{- with secret "database/creds/myapp-reader" -}}
      DB_USER={{ .Data.username }}
      DB_PASSWORD={{ .Data.password }}
      {{- end }}
```

Sidecar 自動 renew lease、credential 寫進 pod shared volume、application 讀 file。Application code 不需要 Vault SDK、降低 dependency。

### SDK pattern（非 K8s 環境）

Go：`hashicorp/vault/api` + `LifetimeWatcher`、Java：spring-cloud-vault、Python：hvac + Renewer。SDK 已處理 renew timing / retry / token rotation、不要自寫 ticker。

### 跟 cloud-native secret manager 的混搭

[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) / [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) 也有 dynamic credential rotation（每 30 天輪替）、但 *cadence 是按時間*、不是 *按 application session*。混搭 pattern：

- Cloud-native：infrastructure-level credential（RDS master / k8s service account）、long TTL（30-90 天）
- Vault dynamic：application-level credential、short TTL（1-24 小時）
- Vault root credential 存 cloud-native secret manager、Vault auto-unseal 也用 cloud KMS

### 下一步議題

- **Database snapshot 跟 dynamic credential 衝突**：PostgreSQL `pg_dump` 用 long-lived credential、不適用 dynamic；snapshot user 用 static + scoped policy、跟 application user 分離
- **Connection pool 端的 dynamic credential 支援**：[PgBouncer](/backend/01-database/vendors/postgresql/pgbouncer-config/) 不支援 per-connection credential rotation、需要 connection 整個 lifecycle 跟 lease 對齊
- **多 region Vault replication**：performance replication 跟 disaster recovery replication 對 lease 的處理不同、跨 region application 要 sticky 同一 region 的 Vault primary

## 相關連結

- 上游 vendor 頁：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)
- 對照案例：[Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)
- 對照案例：[CircleCI 2023 AppRole 事件](/backend/07-security-data-protection/cases/) — Cross-vendor mapping
- 上游 chapter：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)
- 平行 deep article：[pgBouncer 配置](/backend/01-database/vendors/postgresql/pgbouncer-config/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
