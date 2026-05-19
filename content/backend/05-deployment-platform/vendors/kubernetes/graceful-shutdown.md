---
title: "Kubernetes Graceful Shutdown：termination 序列跟你以為的不一樣"
date: 2026-05-18
description: "K8s pod termination 五步序列、preStop / SIGTERM / terminationGracePeriodSeconds 的真實時序、5 個 production 踩雷（500 期間 502、connection drain race、init container 重啟、StatefulSet 串行終止、Job 不 graceful）、跟 service mesh / readiness probe 整合"
weight: 10
tags: ["backend", "deployment", "kubernetes", "graceful-shutdown", "deep-article"]
---

> 本文是 [Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/) overview 的 implementation-layer deep article。Overview 已說明 K8s 在 deployment platform 譜系的定位、本文聚焦 *pod termination* 這個 production 最常踩、被誤解最深的議題：序列、配置、五個 case、跟 service mesh 整合。

## Graceful shutdown 沒做對、500 期間每次 deploy 都吃 502

最常見的觸發場景：deploy 新 image、prometheus alert 在 5 分鐘內收到一波 502 / 503、SRE 翻 application log 看到「正在處理 request」「connection closed」交替出現。Application 本身沒 bug、但 K8s 在 pod terminate 時跟 traffic 來源 *沒對齊步調*、舊 pod 還在處理請求時就被 SIGKILL、新 request 還在打到準備關閉的 pod 上。

很多團隊修法是 *把 terminationGracePeriodSeconds 從 30 拉到 120*、暫時掩蓋問題；但症狀會在下次 rolling update / HPA scale-down / node drain 時換個形式回來。根因在 *termination 序列* — pod 不是收到 SIGTERM 就 graceful、序列裡每一步出錯都有不同 fail mode。

## Termination 序列：五步、每步都能爆

K8s 收到 delete pod 請求後、發生的事 *按時間* 是：

| 時序                                      | 事件                                       | 動作來源            |
| ----------------------------------------- | ------------------------------------------ | ------------------- |
| t=0                                       | API server 標 pod 為 Terminating           | kubelet 收到 delete |
| t=0                                       | Pod 從 Service Endpoints 移除（**async**） | endpoint controller |
| t=0                                       | kubelet 跑 preStop hook（若有定義）        | container runtime   |
| t=preStop 結束                            | container 收到 SIGTERM                     | container runtime   |
| t=SIGTERM + terminationGracePeriodSeconds | container 收到 SIGKILL                     | container runtime   |

關鍵誤解：

1. **「pod 從 Service 移除」跟「container 收到 SIGTERM」是 *平行*、不是序列**。Endpoint controller 更新 Endpoints object → kube-proxy 重新寫 iptables → 各 node 的 traffic 才真正停 — 這條鏈通常需要 *1-5 秒*；同時間 SIGTERM 已經發給 application。

2. **preStop hook 是「container 還在跑、SIGTERM 還沒發」期間執行**。pre-Stop 設 `sleep 10` 是 production 標準作法 — 用 sleep 讓 endpoint controller 有時間把 pod 從 Service 移除、避免 SIGTERM 期間還有新 request 進來。

3. **terminationGracePeriodSeconds 是 *從 preStop 開始* 計時、不是從 SIGTERM**。preStop sleep 10s + application 30s graceful = 至少要設 40s。

4. **graceful 不是 framework 自動的**。Application 必須 *主動處理 SIGTERM*：拒絕新 request、等 in-flight 完成、close DB connection、flush log。沒處理 SIGTERM、container 會在 grace period 後被強殺。

5. **readiness probe 在 Terminating 期間 *仍會被執行*、但結果不影響 traffic**（已經從 Endpoints 移除）。但若 application 沒主動讓 readiness fail、service mesh / external LB 可能仍在送 request（依不同 mesh 行為）。

## 配置全圖

### Deployment spec

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 60          # SIGTERM 後 60s 才 SIGKILL
      containers:
        - name: app
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 10"]
          readinessProbe:
            httpGet:
              path: /healthz/ready
              port: 8080
            periodSeconds: 5
            failureThreshold: 2
```

時序：t=0 preStop 開始 sleep 10s → t=10s container SIGTERM → t=70s SIGKILL（不是 t=60s、是 60s after SIGTERM）。

### Application 處理 SIGTERM（Go 範例）

```go
sigs := make(chan os.Signal, 1)
signal.Notify(sigs, syscall.SIGTERM)

server := &http.Server{Addr: ":8080"}
go server.ListenAndServe()

<-sigs                                              // 等 SIGTERM
log.Println("SIGTERM received, draining...")

// 1. readiness fail（讓 mesh-aware 流量停）
ready.Store(false)

// 2. wait 5s 讓 readiness probe failureThreshold 觸發
time.Sleep(5 * time.Second)

// 3. graceful shutdown server（拒新請求、等 in-flight）
ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
defer cancel()
server.Shutdown(ctx)

// 4. close DB / cache / message consumer
db.Close()
consumer.Stop()

// 5. flush log + exit
logger.Sync()
```

關鍵：`server.Shutdown(ctx)` 是 *拒新請求、等 in-flight*、ctx timeout 設 *grace period 減去 preStop sleep 跟 readiness fail 等待時間*（60s - 10s - 5s = 45s）。

## Production 故障演練

### Case 1：Rolling update 期間 502 / 503

**徵兆**：每次 deploy 後 5 分鐘內 LB / ingress log 一波 502 / 503、application log 顯示「context canceled」「connection closed by peer」、新 pod 已 ready 但舊 pod 在 grace period 內仍收 request。

**根因**：沒設 preStop sleep、container 收到 SIGTERM 後立刻 `server.Shutdown()`、但 kube-proxy 還沒把舊 pod 從 iptables 移除、新 request 持續送到舊 pod、舊 pod 已拒收。

**修法**：preStop `sleep 10`、讓 endpoint propagation 完成再進入 SIGTERM 流程。

### Case 2：Connection drain race，long-running request 被中斷

**徵兆**：deploy 後 application log 有大量 `context canceled` 對應到 long-running endpoint（例：報表生成、檔案上傳）、user 端看到 transaction 失敗、但短 request 沒事。

**根因**：long-running endpoint 處理時間 > terminationGracePeriodSeconds、`server.Shutdown(ctx)` ctx timeout 設太短、in-flight 強制中斷。

**修法**：

1. 把 long-running endpoint 改 async（背景 job + status endpoint）、HTTP request 立刻 return job ID
2. 短期：terminationGracePeriodSeconds 拉到 long-running 99 percentile + buffer
3. application 側 ctx timeout = grace period - preStop - readiness fail wait

### Case 3：Init container 在 grace period 期間重啟、SIGTERM 沒到 main

**徵兆**：pod 顯示 Terminating 但 phase 一直在 Running、main container restart count + 1、application log 沒看到「SIGTERM received」。

**根因**：init container 用 `restartPolicy: Always`（K8s 1.28+ sidecar 模式）、或 main container 在 SIGTERM 前先 crash 觸發 restart、kubelet 在 restart 後 *不重發 SIGTERM*、main container 跑到 grace period 結束直接 SIGKILL。

**修法**：

1. Sidecar container（restartPolicy: Always）的 preStop 也要設 `sleep`、跟 main 同 lifecycle
2. main container readinessProbe 失敗時 *別自動 restart*（restartPolicy: OnFailure + crashLoopBackOff 觀察）
3. 觀察 `kubectl describe pod` 的 events、SIGTERM 沒發出來會有 `Killing container` event 缺失

### Case 4：StatefulSet 串行終止、總時間 = pod 數 × grace period

**徵兆**：StatefulSet rolling update / scale-down 比 Deployment 慢 N 倍（N = replica 數）、deploy 一個 5 replica 的 statefulset 要 5 分鐘以上。

**根因**：StatefulSet 預設 `podManagementPolicy: OrderedReady` — pod 串行終止 + 串行創建、每個 pod 至少要 grace period 完成才動下一個。Deployment 用 `RollingUpdate` 預設 maxUnavailable=25% 平行終止。

**修法**：

1. StatefulSet 改 `podManagementPolicy: Parallel`（若 application 不要求嚴格順序）
2. 嚴格順序情境（Cassandra / Kafka / etcd）保留 OrderedReady、但 grace period 設 *單 pod 必要時間*、不要設 *總時間能承受*
3. 接受序列化代價、把 deploy 排在低流量時段

### Case 5：Job / CronJob 不 graceful、SIGTERM 直接 SIGKILL

**徵兆**：CronJob 在 Job timeout / pod eviction 時不 graceful、寫一半的 file 留在 PVC、下次跑時 corrupt；application log 沒「SIGTERM received」、直接斷。

**根因**：Job 的 `activeDeadlineSeconds` 到期 / node eviction 觸發時、K8s 對 Job pod *仍會發 SIGTERM*、但 *很多 batch framework（Spring Batch / Argo Workflow worker）沒處理 SIGTERM*、application 沒主動 checkpoint。

**修法**：

1. Batch application 處理 SIGTERM、checkpoint 進度寫 storage、下次跑時 resume
2. 不適合 checkpoint 的 batch、保證 *idempotent re-run*、SIGKILL 後重跑不會 corrupt
3. Job spec 加 `terminationGracePeriodSeconds`（預設 30、batch 通常要 60-300）

## 規模影響

Graceful shutdown 的成本主要在 *deploy 時間* 跟 *capacity buffer*：

| 規模因素                              | 影響                                                                                      |
| ------------------------------------- | ----------------------------------------------------------------------------------------- |
| terminationGracePeriod 60s            | 單 pod deploy ~70-80s（含 preStop + grace + new pod startup）                             |
| Deployment 100 replica + maxSurge 25% | 全 deploy ~5-10 分鐘、需要 *25% extra capacity*（25 replica buffer）                      |
| StatefulSet 串行 + 60s grace          | 10 replica 約 10-12 分鐘、deploy window 要在低流量時段                                    |
| HPA scale-down 跟 graceful 一起跑     | scale-down 觸發 → preStop + grace + new metric → 下次 scale 判斷、avg 反應週期 ≈ 3-5 分鐘 |

實務 default：

- Web service：`terminationGracePeriodSeconds: 60`、preStop sleep 10、application graceful 45s
- Backend worker（消費 queue）：`terminationGracePeriodSeconds: 120`、preStop 不 sleep（用 readiness 控）、application 處理當前 message + commit offset
- Batch job：`terminationGracePeriodSeconds: 300`、checkpoint pattern
- StatefulSet（DB / queue）：grace period 對齊 vendor 建議（Kafka 90s、PostgreSQL 60s）

## 跟其他元件整合

### Service mesh（Istio / Linkerd）

Service mesh sidecar（envoy / linkerd-proxy）也有自己的 termination — 通常比 main container 晚一點關。配置原則：

1. mesh sidecar 設 `terminationGracePeriodSeconds` 比 main 多 5-10s、main 處理完才換 sidecar
2. Istio 1.12+ 的 `proxy.istio.io/config.holdApplicationUntilProxyStarts` 控啟動順序、shutdown 也要對應
3. mTLS 環境 graceful 多一道：在 SIGTERM 後等 mesh 主動 close cert rotation、不要硬斷

### Readiness probe 跟 mesh-aware traffic

純 K8s Service（kube-proxy iptables）：endpoint 移除後 *已建立 connection 仍會跑完*、新 connection 不來。Mesh-aware traffic（service mesh / external LB with health check）：要 readiness fail 才會停送。

修法：application graceful 第一步是 `ready.Store(false)` + 等 readiness probe 至少 fail 一次（5-10s）、才開始 server.Shutdown。

### 跟 Pod Disruption Budget（PDB）的衝突

Node drain 時 PDB 限制可同時 unavailable 的 pod 數、graceful shutdown 拖長會讓 drain 卡住。對策：

1. 緊急 drain（node 硬體故障）：`kubectl drain --grace-period=30 --force`、接受短時間 502
2. 正常 drain（升級 / 維運）：PDB 設 `minAvailable: <replicas-1>`、容許單 pod 慢慢 graceful
3. 不要設 `maxUnavailable: 0`、會讓 drain 卡死

## 下一步

- **Application graceful 寫法**：[12-factor app](https://12factor.net/disposability) disposability 章節給 framework-agnostic 模板、各語言 SDK 寫法見對應 framework
- **Queue consumer 的 graceful**：訊息 ack / offset commit 必須在 SIGTERM 內完成、否則 duplicate message — 對應 [03 message queue](/backend/03-message-queue/) 模組的 consumer-design 段
- **跨 region / 多 cluster 的 graceful**：multi-cluster service mesh（Istio multicluster / Linkerd multicluster）的 traffic shift 期間 graceful 行為跟單 cluster 不同、需要對齊 mesh 配置

## 相關連結

- 上游 vendor 頁：[Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/)
- 上游 chapter：[5.X deployment-rollout-drain-rollback](/backend/05-deployment-platform/deployment-rollout-drain-rollback/)
- 對照案例：rolling update 期間 502 多見於 stage-3 mesh adoption case 庫
- 平行 deep article：[pgBouncer 配置](/backend/01-database/vendors/postgresql/pgbouncer-config/) / [Vault Dynamic Credential](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
