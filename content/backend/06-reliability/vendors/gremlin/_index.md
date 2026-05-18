---
title: "Gremlin"
date: 2026-05-01
description: "商業 chaos engineering 平台、跨平台與 GameDay"
weight: 9
tags: ["backend", "reliability", "vendor"]
---

Gremlin 是商業 chaos engineering SaaS、承擔三個責任：跨平台 chaos（VM / container / K8s / cloud 都有 agent）、GameDay 設計 + 報告功能、enterprise-grade audit + blast radius guardrail。設計取捨偏向「商業支援 + 跨平台 + 企業安全 + Halt button 緊急中止」、適合非純 K8s 環境 + 需要商業 SLA 的團隊。Founder 來自 Netflix Chaos team。

## 本章目標

讀完本章後、你應該能：

1. 部署 Gremlin agent 到 VM / container / K8s
2. 設計 attack（resource / state / network）+ blast radius
3. 跑 Scenario / GameDay + 報告交付
4. 用 Halt button 緊急中止
5. 評估 Gremlin vs Chaos Mesh / LitmusChaos 的選用

## 最短路徑：5 分鐘把 Gremlin 跑起來

```bash
# 1. 註冊 + 取得 team API key
# TODO: gremlin install or container agent

# 2. 第一個 attack
# TODO: gremlin attack-container --target ... --type cpu

# 3. Dashboard 看 attack timeline
# TODO: app.gremlin.com
```

## 日常操作與決策形狀

### Attack types

子議題：

- Resource：CPU / memory / disk / IO
- State：shutdown / process kill / time travel
- Network：blackhole / DNS / latency / packet loss
- Application：custom error inject

### Blast radius + magnitude

子議題：

- Target selection（host / container / K8s pod）
- Magnitude（影響度、CPU %、latency ms）
- Duration（短到分鐘 / 長到小時）
- Halt button：emergency stop

### Scenario / GameDay 設計

子議題：

- Multi-step attack scenario
- GameDay 跨 team 演練設計
- Report 自動產生

## 進階主題（按需閱讀）

### Cross-platform agent

子議題：

- VM agent（Linux / Windows）
- Container agent（Docker / Kubernetes DaemonSet）
- Cloud agent（AWS / GCP / Azure）
- Agent-less mode（限制較多）

### Enterprise audit + RBAC

子議題：

- Team / Project / Role 設計
- Attack approval workflow
- Audit log
- SSO / SAML

### 跟 OSS chaos 對比

子議題：

- Gremlin：商業 / 跨平台 / GameDay / 報告
- OSS（Chaos Mesh / Litmus）：成本低 / K8s-only / 自管
- 選型判讀：企業合規 + 跨平台 → Gremlin；K8s-only + 預算敏感 → OSS

### Halt button

子議題：

- 緊急 stop 所有 active attack
- 對應 [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)
- 跟 incident response 連動

### Application-level fault

子議題：

- Gremlin ALFI（Application-Level Fault Injection）
- SDK integration
- Custom exception inject

## 排錯快速判讀

### Agent 連不上 Gremlin

操作原則：API key / network 不通、proxy 配置錯。

### Attack 沒生效

操作原則：target selection 沒匹配 / agent 沒安裝。

### Halt 不及時

操作原則：halt button 全 active attack 立即停、但已造成影響不會回滾。

### Blast radius 過大

操作原則：magnitude / duration 設過大、影響超預期。修法：staging 先測 / 分階段放大。

## 何時改走其他服務

| 需求形狀              | 改走                                                                                                                    |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| K8s OSS               | [Chaos Mesh](/backend/06-reliability/vendors/chaos-mesh/) / [LitmusChaos](/backend/06-reliability/vendors/litmuschaos/) |
| Integration test 模擬 | [Toxiproxy](/backend/06-reliability/vendors/toxiproxy/)                                                                 |
| AWS-only              | AWS Fault Injection Service                                                                                             |
| Azure-only            | Azure Chaos Studio                                                                                                      |
| 預算極敏感            | OSS chaos 工具                                                                                                          |

## 不在本頁內的主題

- Gremlin pricing
- 各 attack parameter detail
- Agent internal

## 案例回寫

| 案例方向                                                                                                               | 對應主題                                             |
| ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| [Netflix：Steady State、Chaos 與 FIT](/backend/06-reliability/cases/netflix/steady-state-chaos-and-fit/)               | chaos 文化的對照組、商業 vs 自建工具的選擇           |
| [Netflix：Business-Hours Guardrails](/backend/06-reliability/cases/netflix/chaos-monkey-business-hours-guardrails/)    | attack scope / halt 條件對應時段與 blast radius 控制 |
| [Stripe：Idempotency 與零停機遷移](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)      | Game Day 設計 + 商業 chaos SaaS 的演練節奏           |
| [Shopify：BFCM 容量治理與 Game Day](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)                 | 峰值前 Game Day 演練的攻擊類型清單                   |
| [Spotify：平台工程與可靠性契約](/backend/06-reliability/cases/spotify/platform-engineering-and-reliability-contracts/) | squad-based 採用 chaos 的商業工具落地                |

**待補 Gremlin customer case**：Stripe / Shopify / Slack 直接公開的 Gremlin GameDay engineering blog（目前以 cases/ 內的可靠性脈絡引用為主）。

## 下一步路由

- 上游概念：[6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)
- 平行 vendor：[Chaos Mesh](/backend/06-reliability/vendors/chaos-mesh/)、[Toxiproxy](/backend/06-reliability/vendors/toxiproxy/)
- 下游能力：[8 incident response](/backend/08-incident-response/)
