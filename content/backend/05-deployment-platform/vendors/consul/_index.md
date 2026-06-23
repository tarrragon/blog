---
title: "Consul"
date: 2026-05-01
description: "Service registry / mesh / KV / DNS"
weight: 9
tags: ["backend", "deployment", "vendor"]
---

Consul 是 HashiCorp 出品的 service networking 平台、承擔三個責任：service registry + discovery + health check（跨 VM / container / bare metal）、KV store + watch（dynamic config）、service mesh（Consul Connect、mTLS sidecar）。設計取捨偏向「跨平台統一 registry + multi-datacenter 一級公民 + DNS interface」、適合非 K8s-only 環境。BSL 授權變動同 Terraform。

對「非 K8s 環境 service discovery、跨平台統一 registry、KV store + watch、跨 datacenter mesh」這條路徑、Consul 是首選。

## 本章目標

讀完本章後、你應該能：

1. 部署 Consul cluster（Server + Agent）
2. 註冊 service + 配置 health check
3. 用 KV store + watch 做 dynamic config
4. 部署 Consul Connect（mTLS service mesh）
5. 評估 BSL 授權影響跟 alternative（etcd / ZooKeeper）

## 最短路徑：5 分鐘把 Consul 跑起來

```bash
# 1. 啟動 dev mode
consul agent -dev -client=0.0.0.0

# 2. 註冊 service（用 JSON 定義）
cat > web.json <<'SVC'
{"service": {"name": "web", "port": 8080,
  "check": {"http": "http://localhost:8080/health", "interval": "10s"}}}
SVC
consul services register web.json

# 3. 查詢（DNS + HTTP API）
dig @127.0.0.1 -p 8600 web.service.consul SRV
curl -s http://localhost:8500/v1/catalog/service/web | jq .
```

## 日常操作與決策形狀

### Agent / Server 拓樸

子議題：

- Server：Raft consensus、quorum（3 / 5 node）
- Agent：每 host 一個、forward 到 server
- Client mode（不參 Raft、純 forward）
- 對應 K8s 內 sidecar mode

### Service registration

子議題：

- API / CLI / config file 註冊
- Health check：HTTP / TCP / Script / TTL
- Tags / metadata
- 對應指令：`consul services register`、`consul catalog services`

### KV store + watch

子議題：

- HTTP API：PUT / GET / DELETE
- Watch：long polling / blocking query
- 適合：dynamic config / feature flag / leader election
- 對應 consul-template 用 KV 模板生 config

## 進階主題（按需閱讀）

### Consul Connect（mTLS service mesh）

子議題：

- Sidecar proxy（Envoy-based）
- Service intentions（誰可訪誰）
- mTLS 自動憑證
- 跟 Istio / Linkerd 對比

### DNS interface

子議題：

- Consul DNS port 8600（dig 可訪）
- 跟 system resolver 整合（unbound / dnsmasq forward to Consul）
- SRV record / A record
- 對應 service discovery 替代 client-side library

### Multi-datacenter

子議題：

- Consul 一級公民跨 DC 設計
- WAN federation
- Network areas
- 跟 etcd（單 DC focused）對比

### ACL system

子議題：

- Token-based ACL
- Policy / Role
- Bootstrap token / agent token / management token
- 對應 [07 security](/backend/07-security-data-protection/) IAM

### BSL 授權影響

子議題：

- 2023 改 BSL（同 Terraform）
- 不能 host Consul-as-a-Service 對外
- 對 internal 用沒影響
- Fork：HashFork / no major fork yet（vs OpenTofu 對 Terraform）

### 跟 etcd / ZooKeeper 對比

子議題：

- etcd：K8s control plane 後端、API minimal
- ZooKeeper：老牌、Java-heavy、Kafka 跟 HBase 用
- Consul：service discovery first、DNS / health check 內建
- 選擇判讀：K8s 內 → etcd（就在那）；non-K8s 多 DC → Consul

### Consul + Nomad / Vault integration

子議題：

- 跟 HashiCorp Nomad（替代 K8s）整合
- 跟 Vault（secrets）整合
- 三件套：Consul + Nomad + Vault

## 排錯快速判讀

### Service 不出現在 catalog

操作原則：先確認 registration API 成功、再看 health check state。

```bash
consul catalog services
consul members
consul catalog nodes -service=web
```

### Health check flapping

操作原則：check interval / timeout 設定 + 應用本身不穩定。判讀：UI 看 check history。

### Split brain（Raft）

操作原則：Server 數量 < quorum（< 半數）會 split brain。修法：recover snapshot / 加 server。

### KV race condition

操作原則：多 client 同時改、要用 CAS（compare-and-swap）。判讀：API ModifyIndex。

### Consul Connect sidecar 連不上

操作原則：proxy config 錯 / intention 沒設 / cert 過期。判讀：Envoy admin endpoint（sidecar 後面）。

## 何時改走其他服務

| 需求形狀                     | 改走                                |
| ---------------------------- | ----------------------------------- |
| K8s 內 service discovery     | K8s 內建 Service / DNS              |
| K8s service mesh             | Istio / Linkerd / Cilium            |
| 純 K8s control plane backend | etcd                                |
| 純 Java 生態                 | ZooKeeper / Eureka                  |
| BSL 敏感                     | etcd（OSI）/ ZooKeeper（OSI）       |
| Cloud-native（AWS）          | Service Connect for ECS / Cloud Map |

## 不在本頁內的主題

- Consul API 完整 reference
- Vault / Nomad 細節（各自獨立工具）
- Raft protocol 內部
- BSL 法律細節

## 案例回寫

### 跨 vendor 對照

| 案例                                                                                                            | 對 Consul 的對應                                                              |
| --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| [5.C1 Tradeshift self-managed → EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) | Tradeshift 用 Linkerd 做切流、對照 Consul Connect 做跨叢集 mTLS 的取捨        |
| [5.C7 Airbnb Istio](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/)                     | 大規模 mesh 升級節奏的對照、Consul Connect 在類似治理上要設計分批與回退窗口   |
| [5.C10 規模對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)                   | 非 K8s 多 DC 場景 Consul 首選、K8s-only 場景則退到 K8s 內建 service discovery |

**待補 Consul 案例**：HashiCorp customer story、Bloomberg / Cloudflare / Stripe 等大規模 Consul 案例、Consul → K8s service mesh 遷移案例。

## 下一步路由

- 上游概念：[5 deployment platform](/backend/05-deployment-platform/)
- 平行 vendor：[Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/)（K8s 內建 service discovery）
- 下游能力：[07 security IAM](/backend/07-security-data-protection/)、[6 reliability](/backend/06-reliability/)
