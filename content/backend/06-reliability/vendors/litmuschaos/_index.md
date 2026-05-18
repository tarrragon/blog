---
title: "LitmusChaos"
date: 2026-05-01
description: "Kubernetes chaos engineering 平台（CNCF graduated）"
weight: 8
tags: ["backend", "reliability", "vendor"]
---

LitmusChaos 是 CNCF graduated 的 Kubernetes chaos engineering 平台、承擔三個責任：ChaosHub experiment marketplace（現成 experiment 直接用）、ChaosWorkflow 編排多步驟實驗、Probe-based steady state validation。設計取捨偏向「現成 experiment 庫 + workflow-centric + CNCF graduated 治理」、是 Chaos Mesh 的近競品、Harness 提供商業版（ChaosNative）。

## 本章目標

讀完本章後、你應該能：

1. 部署 Litmus 到 K8s
2. 從 ChaosHub 引用現成 experiment
3. 寫 ChaosWorkflow（多步驟 + probe）
4. 設計 Probe（HTTP / Cmd / K8s / Prometheus）做 steady state
5. 評估 Litmus vs Chaos Mesh vs Gremlin 的選用

## 最短路徑：5 分鐘把 Litmus 跑起來

```bash
# 1. 安裝
# TODO: helm install litmus litmus/litmus -n litmus --create-namespace

# 2. 從 ChaosHub 引用 experiment
# TODO: kubectl apply -f https://hub.litmuschaos.io/...

# 3. 跑 experiment + 看 ChaosResult
# TODO: kubectl apply -f chaosengine.yaml
# TODO: kubectl describe chaosresult <name>
```

## 日常操作與決策形狀

### CRD 設計

子議題：

- ChaosExperiment：experiment 定義
- ChaosEngine：bind experiment 到 target
- ChaosResult：執行結果

### ChaosHub experiment

子議題：

- 現成 experiment marketplace
- Generic / Kafka / Cassandra / GCP / AWS / VMware experiments
- 自訂 experiment 上傳 Hub

### ChaosWorkflow

子議題：

- Argo Workflow-based
- 多步驟 chaos 編排
- Schedule trigger

## 進階主題（按需閱讀）

### Probe-based steady state

子議題：

- HTTP probe / Cmd probe / K8s probe / Prometheus probe
- 跟 chaos 同步 / 序列執行
- Success threshold 設計

### ChaosCenter（control plane）

子議題：

- 跨 cluster chaos 管理
- ChaosResult dashboard
- RBAC 控制

### Harness ChaosNative（商業）

子議題：

- 商業支援版本
- 跟 Harness CD 整合
- Enterprise governance

### 跟 Chaos Mesh 對照

子議題：

- Litmus：workflow-centric、ChaosHub
- Chaos Mesh：CRD-driven、Dashboard 友善
- 選擇判讀：現成 experiment 庫 → Litmus；fault types 多樣 → Chaos Mesh

### Chaos as Code

子議題：

- ChaosWorkflow YAML version control
- GitOps integration
- PR-based chaos review

## 排錯快速判讀

### Experiment fail to start

操作原則：ServiceAccount + RBAC 不對、experiment image pull 失敗。判讀：`kubectl describe chaosengine`。

### Probe 失敗

操作原則：probe 條件設錯 / target 沒準備好。判讀：ChaosResult 看 probe verdict。

### Hub experiment 引用版本不對

操作原則：experiment.yaml 跟 Litmus version 不對齊。判讀：Litmus version + experiment compatibility。

### Workflow 卡住

操作原則：Argo Workflow 卡 → 看 Argo pod log。

## 何時改走其他服務

| 需求形狀                   | 改走                                                      |
| -------------------------- | --------------------------------------------------------- |
| 多 fault types / Dashboard | [Chaos Mesh](/backend/06-reliability/vendors/chaos-mesh/) |
| 非 K8s / 商業              | [Gremlin](/backend/06-reliability/vendors/gremlin/)       |
| Integration test           | [Toxiproxy](/backend/06-reliability/vendors/toxiproxy/)   |
| AWS-native                 | AWS Fault Injection Service                               |

## 不在本頁內的主題

- ChaosHub 各 experiment 詳細 parameter
- Argo Workflow 內部
- Litmus 商業版本 detail

## 案例回寫

| 案例方向                                                                                                               | 對應主題                                            |
| ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [Netflix：Steady State、Chaos 與 FIT](/backend/06-reliability/cases/netflix/steady-state-chaos-and-fit/)               | hypothesis-driven experiment 對應 ChaosHub workflow |
| [Spotify：平台工程與可靠性契約](/backend/06-reliability/cases/spotify/platform-engineering-and-reliability-contracts/) | squad-based 採用 chaos 的平台化路徑                 |

**Case 庫稀薄**：本 cases/ 目錄目前沒有以 LitmusChaos 為主軸的案例。

- **待補 LitmusChaos customer case**：CNCF graduated 後客戶採用案例、Harness ChaosNative 客戶
- **候選 case**：Meta（K8s-native region failover chaos）、Microsoft（Chaos Studio 對照組）— 若未來收錄需先在 cases/ 補正文

## 下一步路由

- 上游概念：[6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)
- 平行 vendor：[Chaos Mesh](/backend/06-reliability/vendors/chaos-mesh/)、[Gremlin](/backend/06-reliability/vendors/gremlin/)
- 下游能力：[8 incident response](/backend/08-incident-response/)
