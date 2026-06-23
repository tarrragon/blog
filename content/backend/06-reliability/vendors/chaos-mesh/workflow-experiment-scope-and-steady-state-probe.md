---
title: "Chaos Mesh：Workflow、Scope Control 與 Steady State Probe"
date: 2026-06-23
description: "用 Chaos Workflow 編排多步驟實驗、用 selector 與 mode 控制 blast radius、用 StatusCheck 做 steady state probe。"
weight: 1
tags: ["backend", "reliability", "vendor", "chaos"]
---

## 問題情境

單一 ChaosExperiment（PodChaos pod-kill、NetworkChaos delay）只能驗證一個故障面向。真實的可靠性驗證需要多步驟編排：先注入依賴延遲，觀察 [steady state](/backend/knowledge-cards/steady-state/) 是否維持，再注入節點失效，最後驗證恢復路徑。Chaos Workflow 提供這個編排能力，把多個 fault injection 與 health check 組成可重播的驗證流程。

experiment scope 的精準控制同樣關鍵。selector 選到 production 全部 pod 的 chaos experiment 會變成真實事故。scope control 的責任是讓 [blast radius](/backend/knowledge-cards/blast-radius/) 從最小範圍開始，逐步放大，每一步都有停止條件。

## Chaos Workflow 設計

Chaos Workflow 是多個 ChaosExperiment 與 StatusCheck 組成的 DAG（有向無環圖），用 YAML 定義步驟順序與分支條件。

### 步驟類型

| 類型        | 責任                                    | 適用場景                     |
| ----------- | --------------------------------------- | ---------------------------- |
| Serial      | 順序執行，前一步完成才進下一步          | 依賴故障 → 觀察 → 節點故障   |
| Parallel    | 平行執行多個注入                        | 同時打多個依賴驗證交叉影響   |
| Suspend     | 暫停等待人工確認後再繼續                | 高風險步驟前的 approval gate |
| StatusCheck | 對 HTTP / gRPC / custom script 做 probe | 注入前後的 steady state 驗證 |

StatusCheck 是 workflow 的核心控制面。它在故障注入前後對目標 endpoint 做 health check，pass/fail 決定 workflow 是否繼續。StatusCheck 的 success condition 對應 [6.22 steady state definition](/backend/06-reliability/steady-state-definition/) 的穩態門檻：success rate、latency、queue lag 都能作為 probe 判準。

典型 workflow 編排：NetworkChaos(delay 200ms) → StatusCheck(api-latency-ok) → PodChaos(pod-kill) → StatusCheck(recovery-within-30s)。第一個 StatusCheck 驗證延遲注入後服務仍可用；第二個 StatusCheck 驗證節點失效後恢復時間可接受。

### Suspend 的使用時機

Suspend 步驟適合放在 blast radius 擴大之前。例如先在 canary namespace 跑完 chaos + StatusCheck，通過後 Suspend 等待值班工程師確認，再擴大到 production namespace。Suspend 讓自動化 workflow 在關鍵決策點保留人工判斷。

## Experiment Scope Control

Scope control 的責任是讓每個 ChaosExperiment 的影響面可預測、可限制。Chaos Mesh 用 selector + mode 兩層控制。

### Selector

Selector 決定哪些 pod 是實驗目標。

| Selector 類型      | 作用                          | 範例                           |
| ------------------ | ----------------------------- | ------------------------------ |
| namespace          | 限制在特定 namespace          | `namespaces: [canary]`         |
| labelSelector      | 按 label 篩選                 | `app: checkout, tier: backend` |
| annotationSelector | 按 annotation 篩選            | `chaos-eligible: "true"`       |
| fieldSelector      | 按 field 篩選（如 node name） | `spec.nodeName: node-3`        |
| podPhase           | 只選特定狀態的 pod            | `Running`                      |

最安全的起點是 namespace + labelSelector + annotation 三層組合：只在 canary namespace、只選帶 `chaos-eligible` annotation 的特定服務 pod。annotation-based opt-in 讓團隊明確標記哪些 pod 可以被 chaos 觸及。

### Mode

Mode 決定在 selector 命中的 pod 中選多少個。

| Mode               | 行為             | Blast radius |
| ------------------ | ---------------- | ------------ |
| one                | 隨機選 1 個      | 最小         |
| fixed              | 固定選 N 個      | 可控         |
| fixed-percent      | 選命中 pod 的 N% | 比例控制     |
| random-max-percent | 隨機選最多 N%    | 有隨機性     |
| all                | 選全部命中的 pod | 最大         |

從 `mode: one` 開始驗證基礎假設，確認 StatusCheck 通過後，逐步升級到 `fixed-percent: 25` → `fixed-percent: 50`。每一步放大前檢查 steady state 是否仍維持，這個節奏對應 [6.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/) 的漸進放大原則。

### Duration 與 Schedule

duration 控制單次故障注入持續多久，schedule 控制實驗重複頻率。duration 太短可能看不到系統完整的退化與恢復循環；太長則增加實際風險。初始建議：duration 設為 recovery SLA 的 2-3 倍（例如 RTO 30s 則 duration 設 60-90s），讓觀測窗涵蓋完整恢復。

## 實作範例

一個完整的 Chaos Workflow：先對 checkout 服務注入網路延遲，驗證 API 仍可用，再 kill pod 驗證恢復。

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: Workflow
metadata:
  name: checkout-resilience-验证
  namespace: chaos-testing
spec:
  entry: main
  templates:
    - name: main
      templateType: Serial
      children:
        - network-delay
        - check-api-health
        - pod-kill
        - check-recovery
    - name: network-delay
      templateType: NetworkChaos
      networkChaos:
        action: delay
        delay:
          latency: "200ms"
        selector:
          namespaces: [canary]
          labelSelectors:
            app: checkout
        mode: one
        duration: "60s"
    - name: check-api-health
      templateType: StatusCheck
      statusCheck:
        type: HTTP
        http:
          url: "http://checkout.canary/health"
          criteria:
            statusCode: "200"
        timeoutSeconds: 30
        failureThreshold: 3
    - name: pod-kill
      templateType: PodChaos
      podChaos:
        action: pod-kill
        selector:
          namespaces: [canary]
          labelSelectors:
            app: checkout
        mode: one
    - name: check-recovery
      templateType: StatusCheck
      statusCheck:
        type: HTTP
        http:
          url: "http://checkout.canary/health"
          criteria:
            statusCode: "200"
        timeoutSeconds: 60
        failureThreshold: 5
```

### GitOps 整合

Workflow 定義存在 git repo，用 ArgoCD 或 Flux sync 到 cluster。變更 chaos experiment 走 PR review，跟 code 變更同樣的 approval 流程。這讓 experiment 的修改歷史可追蹤、可審計。

### RBAC 約束

Chaos Mesh 的 ServiceAccount 權限需要最小化。production namespace 的 chaos experiment 應使用獨立 ServiceAccount，只授予目標 namespace 的 ChaosExperiment create/get/list 權限。避免使用 cluster-admin 角色跑 chaos — 權限過大會讓 selector 誤配時的影響面不可控。

## 邊界與陷阱

**StatusCheck timeout 太短**：服務在 pod-kill 後需要 readiness probe 通過、load balancer 更新、cache 預熱。若 StatusCheck 的 timeoutSeconds 設太短，服務還在恢復中就被判失敗，產生 false negative。初始 timeout 建議設為預期恢復時間的 2 倍。

**Selector 太寬**：namespace-level selector 不加 labelSelector 會命中該 namespace 所有 pod，包含 sidecar、monitoring agent 等非目標 pod。永遠用 labelSelector 或 annotationSelector 收窄範圍。

**Privilege 需求**：Chaos Mesh 的 IOChaos 和 StressChaos 需要 container 的 SYS_ADMIN / SYS_PTRACE capability。安全團隊可能限制這些 capability 的使用。若無法取得 privilege，可以先用 PodChaos + NetworkChaos（不需額外 capability）建立 chaos 習慣，再逐步推進。

**K8s-only 限制**：Chaos Mesh 只能注入 Kubernetes 上的故障。非 K8s 環境的依賴（外部 SaaS、bare-metal DB、第三方 API）需要用 [Toxiproxy](/backend/06-reliability/vendors/toxiproxy/)（TCP-level fault）或 [Gremlin](/backend/06-reliability/vendors/gremlin/)（跨平台 SaaS）補充。

## 整合路由

- 上游概念：[6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/) — selector + mode 對應 blast radius 設計
- 上游概念：[6.22 Steady State Definition](/backend/06-reliability/steady-state-definition/) — StatusCheck 對應穩態門檻
- 下游交接：[6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/) — Workflow 結果作為 release gate 證據
- 平行 vendor：[LitmusChaos](/backend/06-reliability/vendors/litmuschaos/)、[Gremlin](/backend/06-reliability/vendors/gremlin/)、[Toxiproxy](/backend/06-reliability/vendors/toxiproxy/)
- 案例回寫：[Netflix N1](/backend/06-reliability/cases/netflix/steady-state-chaos-and-fit/)（steady state hypothesis）、[Netflix N2](/backend/06-reliability/cases/netflix/chaos-monkey-business-hours-guardrails/)（business-hours guardrails 對應 scope control）
