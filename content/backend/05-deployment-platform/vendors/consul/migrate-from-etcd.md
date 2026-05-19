---
title: "etcd → Consul：KV + N 個 extras feature matrix"
date: 2026-05-19
description: "etcd → Consul 是 Type E paradigm shift expansion — 從 pure KV store 升到 service mesh / discovery / health check / multi-DC；本文用對照表 + paradigm expansion 路線、5 個 production 踩雷（API 對位 / lock semantics / watch event model / multi-DC topology / ACL system）"
weight: 12
tags: ["backend", "deployment-platform", "etcd", "consul", "paradigm-shift", "migration", "type-e"]
---

> 本文是跨 vendor migration playbook、cross-link [etcd](https://etcd.io/) 跟 [Consul](/backend/05-deployment-platform/vendors/consul/)。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *Paradigm = High（pure KV → service mesh paradigm）→ Type E paradigm shift*；跟 [Redis → Memcached](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/)（paradigm reduction）對偶、本文是 *paradigm expansion*（upgrade）方向。

## KV + N 個 extras：feature matrix

| 概念               | etcd                                  | Consul                                            |
| ------------------ | ------------------------------------- | ------------------------------------------------- |
| 核心 paradigm      | Pure KV with Raft consensus           | Service mesh（KV + 6 個其他）                     |
| Data store         | KV with versioned values + watch      | KV + service catalog + health checks + sessions   |
| API style          | gRPC + HTTP/REST                      | HTTP/REST + gRPC（Connect）+ DNS                  |
| Service discovery  | 無（application 自管）                | Built-in（DNS / HTTP API）                        |
| Health check       | 無                                    | Built-in（HTTP / TCP / script / TTL）             |
| Service mesh       | 無                                    | Connect（mTLS + intentions + service-to-service） |
| Multi-DC           | 不支援（per-cluster only）            | Built-in WAN federation                           |
| ACL system         | RBAC (etcd 3.5+)                      | Token-based ACL + namespaces (Enterprise)         |
| Lock primitive     | Lease + transaction                   | Session + KV check-and-set                        |
| Watch event model  | Event stream（gRPC stream）           | Long-polling blocking query (X-Consul-Index)      |
| Distributed config | KV + watch                            | KV + watch + template rendering (consul-template) |
| Use case 對映      | K8s control plane / 純 distributed KV | Service mesh + service discovery + config + KV    |

**核心差異不在「Consul 多功能」、在「Consul 是 service mesh paradigm」**：service discovery / health check / Connect mTLS 是 first-class、KV 只是其中一個 sub-feature。

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/)：

| 維度               | 評估                                           | 等級       |
| ------------------ | ---------------------------------------------- | ---------- |
| Schema / API       | KV API 對位 + 多 N 個 extra API                | Medium     |
| Operational model  | 兩者 Raft-based、ops similar                   | Low        |
| Paradigm           | Pure KV → service mesh                         | **High**   |
| Components         | 同 1 cluster                                   | Low        |
| Application change | KV API 改 + 新增 service registration / health | Medium     |
| Data topology      | 單 DC → multi-DC（如果用 federation）          | Low-Medium |

Paradigm = High（其他 Low-Medium）→ **Type E paradigm shift**；KV 是 sub-feature、不是 migration scope 全部。

## 為什麼遷：3 條 expansion driver

- **Service mesh adoption**：本來用 etcd 跑 K8s control plane、現在 application 端要 service mesh（mTLS / intentions / 流量切換）、Consul 一站式 cover
- **Multi-DC strategy**：etcd 不支援跨 DC、要 active-passive failover；Consul WAN federation 支援 active-active 多 DC
- **Configuration management**：consul-template + envconsul 比 etcd watch + 自寫 reloader 簡單

反向 driver（Consul → etcd）：

- 純 K8s control plane scenario、不需要 service discovery / health check / mesh、etcd 簡單足夠
- Resource constraint：Consul agent 比 etcd 更吃資源、low-end VM 上不夠

## Paradigm expansion 路線

跟 [Redis → Memcached paradigm reduction](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/)（移除 features）對偶、Consul 是 *補進 features*：

```text
etcd KV pattern         → Consul KV API (1:1 對位)
etcd watch              → Consul blocking query / consul-template
etcd lease + lock       → Consul session + KV CAS

(額外加進)
無                      → Consul service registration (services.json / API)
無                      → Consul health check (HTTP / TCP / TTL)
無                      → Consul service discovery (DNS / HTTP)
無                      → Consul Connect (mTLS + intentions)
無                      → Consul WAN federation (multi-DC)
無                      → Consul ACL token + policy
```

Migration 不只是 KV API 對位、是 *application 增能*。

## API 對位

```bash
# etcd basic KV
etcdctl put /myapp/config/db_url 'postgres://...'
etcdctl get /myapp/config/db_url

# Consul KV (對位)
consul kv put myapp/config/db_url 'postgres://...'
consul kv get myapp/config/db_url
```

```bash
# etcd watch
etcdctl watch --prefix /myapp/config/

# Consul blocking query (long polling)
curl 'http://consul:8500/v1/kv/myapp/config?recurse&index=5&wait=10s'
# X-Consul-Index header 為 watch cursor
```

```bash
# etcd transaction (multi-key atomic)
etcdctl txn <<EOF
compares:
mod("/myapp/lock") = "0"
success requests:
put /myapp/lock "owner1"
EOF

# Consul session + KV CAS (對位)
SESSION_ID=$(curl -X PUT 'http://consul:8500/v1/session/create' | jq -r .ID)
curl -X PUT 'http://consul:8500/v1/kv/myapp/lock?acquire='$SESSION_ID -d 'owner1'
# 若失敗 lock 已被別人持有
```

## Application 重設計

```python
# Before: etcd
import etcd3
etcd = etcd3.client(host='etcd', port=2379)
etcd.put('/myapp/config/db_url', 'postgres://...')
db_url = etcd.get('/myapp/config/db_url')[0]

# After: Consul (KV-only)
import consul
c = consul.Consul(host='consul', port=8500)
c.kv.put('myapp/config/db_url', 'postgres://...')
_, kv = c.kv.get('myapp/config/db_url')
db_url = kv['Value']

# (額外加進) After: Consul service discovery
c.agent.service.register(
    name='myapp',
    service_id='myapp-1',
    address='10.0.0.10',
    port=8080,
    check=consul.Check.http('http://10.0.0.10:8080/health', '10s', '5s', '30s')
)

# DNS-based discovery (其他 service 找 myapp)
# dig +short myapp.service.consul SRV
```

## Migration 流程

```text
1. Pre-migration audit
   - 列 etcd 使用的所有 application
   - 評估每個 application 是否 *需要* Consul extras（service discovery / health / mesh）
   - 純 KV use case 標 *low-effort migration*、用得到 extras 標 *value-add migration*

2. Consul cluster build
   - 跨 DC 設計（WAN federation 規劃）
   - ACL system 配置（不要 default open）
   - 性能 sizing（Consul agent 比 etcd 重）

3. Application migration（per-app）
   - 純 KV: SDK 換、API 對位、cutover
   - Service discovery: 加 registration + health check + DNS lookup
   - Service mesh: 加 Connect proxy + intentions

4. Dual-run period
   - etcd 仍跑、application 漸進切到 Consul
   - 每 application cutover 後驗證

5. etcd decommission
   - 確認所有 application 已切
   - K8s control plane（如果是 etcd 唯一 user）保留不切
```

整體 2-4 個月、依 application 數量跟 extras 採用程度。

## Production 故障演練

### Case 1：KV API 對位看似 1:1、watch event model 不同

**徵兆**：application 端從 etcd watch 切 Consul blocking query 後、event 處理 latency 從 50ms 漲到 1-5s；應用以為 event push 即時、實際變 polling。

**根因**：etcd watch 是 gRPC stream、event 即時 push；Consul blocking query 是 long-polling、有 `wait` timeout、event 在 timeout 內到才即時收到。

**修法**：

1. **降 `wait` timeout** 跟業務需求對齊（default 5min、可設 10s）
2. **多 instance 並發 polling**：N 個 application instance 各自 polling、降單點 event 延遲
3. **架構**：critical event 用 Consul event API（`PUT /v1/event/fire/<name>`）+ blocking query event endpoint、跟 KV change 分開
4. **保留 etcd for critical watch**：mission-critical watch 用 etcd 不切

### Case 2：Session-based lock 跟 etcd lease 差

**徵兆**：原本 etcd lease 5s TTL、lease holder application 失聯時 5s 內 lock 自動釋放；切 Consul session 後、session TTL 仍生效、但 health check 整合複雜、偶發 lock not released。

**根因**：Consul session 有兩種模式 — `delete`（session expire 時 release lock）vs `release`（release lock 但 KV 保留）；TTL 配 health check 時行為複雜。

**修法**：

```python
# 明示 session behavior
session_id = c.session.create(
    name='myapp-lock',
    ttl=15,           # 15s TTL
    behavior='delete' # session 過期時 lock 自動 release
)
c.kv.put('myapp/lock', 'owner1', acquire=session_id)
```

session TTL 範圍 10s-86400s、不能 < 10s（etcd 可以 1s）；critical low-latency lock 不適用 Consul。

### Case 3：Multi-DC failover、KV 寫到 wrong DC

**徵兆**：跨 DC 部署後、某 application 寫 KV、但 read 不到；發現 application 端 hardcode 一個 DC 端點、write 到 us-east 但 read 來自 us-west。

**根因**：Consul WAN federation 跨 DC 不自動同步 KV；KV 是 *per-DC*、跨 DC sync 需要 *Consul Enterprise license* 或自管 *consul-replicate*。

**修法**：

1. **每 application instance 連 local DC Consul**：write/read 同 DC
2. **KV replication 跨 DC**：用 consul-replicate 自管、或升 Enterprise
3. **Architecture**：跨 DC 共享 config 改用 *DB-backed config*（持久 + 跨 DC）+ Consul KV 只存 DC-local config

### Case 4：ACL system 預設 open、cutover 後曝險

**徵兆**：Consul cluster 上線 1 個月後 SOC 跑 audit、發現任何 application 都能 read 任何 KV；ACL 沒設、所有 token 都全權限。

**根因**：Consul ACL 預設 disabled、需要 *bootstrap*；很多 setup tutorial 簡化跳過 ACL、cutover 後沒補。

**修法**：

```bash
# Bootstrap ACL system
consul acl bootstrap
# 生成 management token、保留為 root credential

# 建 policy
consul acl policy create -name 'myapp-readonly' \
  -rules 'key_prefix "myapp/" { policy = "read" }'

# 建 token 給 application
consul acl token create -policy-name 'myapp-readonly'
```

Production setup 第一步就 bootstrap ACL、不可以延後。

### Case 5：Health check failure 連鎖、service discovery 失效

**徵兆**：某 application instance 因 GC pause 5 秒未 respond health check、被 Consul 標 failed；DNS query 不返回該 instance；流量切走；GC 結束後 instance 仍 healthy 但 Consul 端 still failed、需要 minutes recover。

**根因**：Consul health check 失敗後進入 critical state、需要 *連續 N 次成功* 才回 passing；default 1-2 次成功即可、但實際時間視 check interval 而定。

**修法**：

1. **`success_before_passing` 設低**（1）讓快速恢復
2. **`failures_before_critical` 設高**（3-5）容忍 transient failure
3. **Multi-check strategy**：HTTP + TCP + script check 三軸、不靠單 check
4. **Application-side hint**：JVM application 配 `MaxGCPauseMillis` 限制 GC pause < health check interval

## Capacity / cost

| 維度             | etcd                  | Consul                                        |
| ---------------- | --------------------- | --------------------------------------------- |
| Cluster baseline | 3-5 node Raft cluster | 3-5 server + N agent (per host)               |
| Memory per node  | 2-8GB                 | 4-16GB（含 agent）                            |
| Operational FTE  | 0.2-0.5               | 0.5-1.0（多 features 多運維）                 |
| Feature surface  | Pure KV               | KV + service mesh + multi-DC + ACL            |
| Setup complexity | Low                   | Medium-High                                   |
| Multi-DC support | 不支援                | Built-in WAN federation                       |
| License          | Apache 2.0 (open)     | MPL 2.0 (community) / commercial (enterprise) |
| Migration cost   | -                     | 1-3 FTE × 2-4 個月                            |

**判讀**：純 KV use case 走 etcd；service mesh / multi-DC / discovery 需求大走 Consul；混合 deployment 是 long-term default（K8s control plane 仍跑 etcd、service mesh 跑 Consul）。

## 整合 / 下一步

### 跟 Kubernetes 對位

K8s control plane *永遠* 用 etcd、不切 Consul；Consul 是 K8s *外* 的 service mesh + 跨 cluster discovery。兩者並存、不互斥。

### 跟 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 整合

Consul + Vault 是 HashiCorp 同生態、Consul 跑 service discovery / mesh、Vault 跑 secrets；Consul ACL token 可從 Vault dynamic engine 取得。

### 跟 [Istio / Linkerd](https://istio.io/) 對位

Consul Connect 是 service mesh paradigm、跟 Istio / Linkerd 並列；多數 K8s-native organization 用 Istio / Linkerd、Consul 強項在 *跨 K8s + VM + multi-DC* mesh。

### 反向 migration（Consul → etcd）

少數 organization 簡化 stack 時做、流程鏡像對稱、但 *退掉 service mesh / multi-DC 是有意識降級*、不能假裝功能等價。

### 下一步議題

- **Consul Connect production rollout**：mesh adoption 是 incremental、per-service intentions 漸進
- **Multi-DC topology 設計**：active-active vs active-passive、依 RPO/RTO 跟 cost trade-off
- **跟 Kubernetes Gateway API 整合**：service mesh paradigm 在 K8s 內 vs 外整合策略

## 相關連結

- Target vendor：[Consul](/backend/05-deployment-platform/vendors/consul/)
- 平行 migration playbook (Type E)：[Redis → Memcached](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/)（paradigm reduction 對偶）/ [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)
- 平行整合：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
