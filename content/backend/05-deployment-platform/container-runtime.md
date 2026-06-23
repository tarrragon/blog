---
title: "5.1 container 與 runtime"
date: 2026-04-23
description: "整理 image、resource limit 與啟動行為"
weight: 1
tags: ["backend", "deployment", "container"]
---

容器執行環境（container runtime）的核心責任是把應用執行環境做成可重現、可限制、可觀測的交付單位。它是部署可靠性的起點——後續的 probe、canary、rollback 都假設 runtime 產物行為可預測。

## image 與建置責任

image 的責任是固定依賴、執行入口與檔案結構，讓同一版本在不同環境行為一致。建置流程要回答三件事：基底映像是否可維護、建置產物是否可追溯、敏感資訊是否被隔離。

映像層數、套件來源、編譯參數都會影響啟動時間與安全邊界。部署策略在後面才有效，前提是 runtime 產物本身可預測。

### 基底映像選擇

基底映像（base image）決定 image 的安全維護基線與啟動時體積。選擇的核心取捨是體積 / 啟動速度與除錯便利性：

- **語言官方映像**（`python:3.12`、`node:20`）：套件齊全、除錯方便，但體積大（通常 800MB+）、攻擊面廣。適合開發環境與 CI。
- **slim / alpine 變體**（`python:3.12-slim`、`node:20-alpine`）：體積壓到 100-200MB、啟動快、攻擊面小。代價是缺少除錯工具（strace、curl、dig），生產事故時 exec 進容器排查會受限。Alpine 用 musl libc 而非 glibc，某些 C extension 需要額外處理。
- **distroless**（`gcr.io/distroless/base`）：只包含 runtime 必要檔案，無 shell、無套件管理器。攻擊面最小，但除錯只能靠 ephemeral debug container 或外部觀測。適合安全要求高且觀測基礎建設完備的生產環境。
- **自建基底**：組織統一維護的基底映像，可以固定安全基線、預裝觀測 agent、統一 timezone / locale。代價是基底維護本身是持續工作，版本更新節奏要有明確 owner。

選完基底後要確認兩件事：upstream 的更新節奏是否可追蹤（CVE 修補從上游到自家 image 的時間），以及團隊是否有能力在基底更新後快速重建並驗證所有服務 image。

### 建置可重現性

同一份 source code 在不同時間建置出不同 image，會讓 rollback 的假設失效——「回退到上一版」回退的是哪一版，取決於當時 build 環境的狀態。

可重現建置的關鍵實踐：

1. **鎖定依賴版本**：`go.sum`、`package-lock.json`、`poetry.lock` 要進 git。依賴解析在建置時不從 registry 重新 resolve。
2. **Multi-stage build**：把建置環境（compiler、dev dependencies）和執行環境分開。最終 image 只包含 runtime 必要檔案，體積小且攻擊面收窄。
3. **避免 image 中殘留敏感資訊**：build arg、環境變數、中間層都可能殘留 secret。secret 不進 Dockerfile，用 runtime mount 或 secret manager 注入。
4. **image 標記策略**：`latest` tag 不可重現——同一個 tag 指向的 image 會隨時間改變。用 git commit SHA 或語意版本號標記，讓每個 tag 指向唯一 image。

對應 [5.C3 Orbitera managed K8s migration](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/)：揭露「跨平台遷移本質是能力遷移」。遷移到新平台時，CI/CD pipeline 可能換了 runner 環境、換了 registry——建置可重現性的前提是依賴鎖定與 multi-stage build 本身不依賴特定 CI 環境。

## entrypoint 與啟動行為

entrypoint/command 的責任是定義容器如何啟動與退出。啟動流程應顯式處理初始化步驟、配置載入、依賴檢查與失敗退出。退出流程應處理信號中斷、在途請求收斂與資源釋放。

若啟動行為隱藏在 shell script 且無可觀測訊號，部署平台很難判斷 readiness 與失敗原因。

### PID 1 與信號處理

容器內 PID 1 有特殊語意：它是 init process，負責接收平台送來的 SIGTERM / SIGINT 並轉發給子進程。PID 1 的問題出在三種情境：

**Shell 作為 PID 1**：`ENTRYPOINT ["sh", "-c", "java -jar app.jar"]` 讓 sh 成為 PID 1。SIGTERM 送到 sh、sh 預設不轉發、java 進程收不到信號、等到 terminationGracePeriodSeconds 到期後被 SIGKILL 強殺。修法是用 `exec` 或直接用 exec form：`ENTRYPOINT ["java", "-jar", "app.jar"]`。

**多進程容器**：一個容器跑多個進程時，PID 1 要負責信號轉發與子進程回收（zombie reaping）。如果 PID 1 不做 wait()，結束的子進程會變成 zombie。解法是用 tini 或 dumb-init 作為輕量 init，或在 Kubernetes 設 `shareProcessNamespace: true` 讓 kubelet 處理。

**啟動腳本的信號遮蔽**：entrypoint script 在初始化階段（下載 config、等依賴就緒）捕捉 SIGTERM 做清理，但如果清理邏輯卡住，整個 shutdown 會被阻塞。啟動腳本的 trap handler 要有 timeout，避免把 graceful shutdown 變成 ungraceful hang。

### 啟動時間對部署策略的影響

啟動時間直接影響 rollout 的最短觀察窗。一個啟動需 60 秒的服務，rollout 每批至少要等 60 秒 + 觀察窗口才能確認新版本穩定。啟動時間的組成與壓縮策略見 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)。

image 體積也影響啟動時間——image pull 在冷啟動（節點上沒有這個 image 的快取）時占啟動時間的顯著比例。1GB image 在 100Mbps 網路下需要 ~80 秒 pull。壓縮 image 體積同時改善啟動速度與節省 registry 頻寬。

## resource limit

CPU/memory [Resource Limit](/backend/knowledge-cards/resource-limit/) 隔離資源競爭並保護叢集穩態。限制過低會導致頻繁節流與重啟，過高會壓縮同節點容量並放大鄰近工作負載風險。

限制設計要依服務流量型態與 GC/執行時特性調整，並與 autoscaling、rollout 批次策略一起評估。

### CPU request 與 limit 的設定策略

CPU 限制有兩個參數：request（排程保證）與 limit（硬上限）。兩者的關係決定服務在負載變動下的行為：

- **request = limit**（guaranteed QoS）：CPU 用量穩定可預測，不會被 throttle 也不會超用。代價是無法在閒時借用節點剩餘 CPU。適合延遲敏感的 API 服務。
- **request < limit**（burstable QoS）：平時用 request 保證的份額，高峰時可用到 limit。代價是當節點 CPU 競爭激烈時，所有 burstable pod 同時被 throttle，延遲會一起劣化。適合批次處理或對延遲要求不高的服務。
- **不設 limit**（只設 request）：服務可用到節點全部剩餘 CPU。Kubernetes 社群近年傾向這個做法——CPU throttle 常比 CPU contention 更難排查。代價是需要良好的觀測來偵測 noisy neighbor。

### Memory limit 與 OOM 的判讀

memory limit 是硬邊界——超過就 OOM kill，不走 graceful shutdown。OOM kill 的判讀分兩種情境：

**真正的 memory leak**：記憶體使用量隨時間單調上升，GC 無法回收。修法在程式碼層。memory limit 只是延後問題爆發，不是解法。

**memory limit 設太低**：服務在高峰流量下的正常記憶體使用超過 limit。常見於 JVM 服務——JVM heap + metaspace + native memory + thread stack 的總和超出 container memory limit。設 limit 時要用「峰值實際使用 + headroom」而非「平均使用」。

GC-based runtime（JVM、.NET、Go）要注意 container-aware memory 設定。早期 JVM 不認 cgroup memory limit，會按宿主機記憶體計算 heap 大小，導致 heap 配置超過 container limit。現代 JVM（Java 10+）預設啟用 container awareness（`-XX:+UseContainerSupport`），Go runtime 1.19+ 支援 `GOMEMLIMIT`。

### 資源設定與 autoscaling 的協同

resource request 同時決定 HPA（Horizontal Pod Autoscaler）的觸發基線。request 設太高時，CPU utilization % 會偏低，HPA 不會觸發擴容，導致服務在真正需要擴容前已經出現延遲。request 設太低時，utilization % 容易衝高，HPA 頻繁擴容，造成 pod 數量抖動。

穩定做法是先在 staging 環境跑負載測試確認服務的實際資源消耗曲線，再以 p90 負載的 CPU / memory 使用作為 request 基線。

## runtime config

環境差異要顯式化才能追蹤——[Runtime Config](/backend/knowledge-cards/runtime-config/) 承擔這個責任。配置來源、版本、更新節奏都應可追蹤。高風險設定需配合 [Config Rollout](/backend/knowledge-cards/config-rollout/) 策略，避免同批大規模變更。

runtime 配置與映像版本要保留相容窗口，讓部署與回退可分步進行。

### 配置注入方式與取捨

配置注入容器有三條路徑，各自有不同的版本追蹤與更新語意：

| 注入方式          | 版本追蹤                    | 更新行為                           | 適用場景                         |
| ----------------- | --------------------------- | ---------------------------------- | -------------------------------- |
| 環境變數          | 跟 deployment spec 一起版控 | 需要 pod restart 才生效            | 啟動時固定的設定（DB URL、port） |
| ConfigMap mount   | ConfigMap 版本              | 自動更新（kubelet sync period 內） | 需要動態更新的非敏感設定         |
| Secret mount      | Secret 版本                 | 自動更新（同 ConfigMap）           | credential、cert、API key        |
| 外部 config store | config store 內版本         | 應用主動拉取或 sidecar push        | feature flag、複雜設定邏輯       |

環境變數最簡單但更新需要 restart。ConfigMap mount 可以動態更新但應用要能偵測檔案變化並 reload。外部 config store（Consul KV、AWS AppConfig、Feature Flag service）最靈活但引入了額外依賴。

設定變更跟 image 變更走不同路徑時，要確保兩者的版本可以交叉相容。版本 v2 的 image 搭版本 A 的 config 能跑、版本 v1 的 image 搭版本 B 的 config 也能跑——rollback image 但 config 沒回退、或 rollback config 但 image 沒回退的情境下、服務不應崩潰。這個相容窗口的設計責任見 [5.7 Config Boundary](/backend/05-deployment-platform/traffic-config-control-plane-boundary/)。

## 遷移期的 Runtime 穩定性

對應 [5.C5 Miro managed EKS 遷移](/backend/05-deployment-platform/cases/miro-managed-eks-migration/)：揭露「平台託管化的價值在讓團隊把心力從底層維護轉到交付效率與可靠性策略」。遷移到 managed 平台後，runtime 層面的變化包含 container runtime 版本（containerd vs Docker shim）、node OS、storage driver、network plugin。這些變化可能改變 image pull 速度、filesystem 行為、DNS 解析路徑。

遷移前後的 runtime 驗證應包含：

1. **image pull 時間比較**：新 registry / 新 node 的 pull 速度是否在 startup timeout 內。
2. **filesystem 行為**：log 寫入路徑、tmp 目錄、volume mount 行為在新 runtime 下是否一致。
3. **DNS 解析**：新叢集的 CoreDNS / node-local DNS 設定是否影響服務的依賴連線建立速度。
4. **resource 行為**：新 node type 的 CPU 架構（x86 vs ARM）、memory page size 是否影響服務性能特性。

## 判讀訊號

| 訊號                              | 判讀重點                             | 對應動作                                |
| --------------------------------- | ------------------------------------ | --------------------------------------- |
| 新版本容器啟動時間顯著增加        | image 體積或初始化步驟膨脹           | 優化映像層、拆分初始化流程              |
| rollout 初期出現 OOM/CPU throttle | resource limit 與實際負載不匹配      | 重設 request/limit、調整併發與批次      |
| 配置變更後特定環境異常            | runtime config 管理不一致            | 統一配置來源、補版本追蹤與差異檢查      |
| 容器停止時請求中斷率上升          | signal/drain 協調不足                | 補 shutdown hook、對齊 termination 流程 |
| 同版本在不同節點行為差異大        | runtime 依賴未固定或環境漂移         | 收斂基底映像、鎖定依賴與建置流程        |
| JVM 服務 OOM 但 heap 未用滿       | native memory / metaspace 超出 limit | 調整 MaxMetaspaceSize、限制 thread 數   |
| 冷啟動節點上服務啟動超慢          | image pull 時間在啟動時間中占比高    | 壓縮 image 體積、啟用 image cache       |
| rollback 後行為跟上次部署不同     | 建置不可重現、tag 覆蓋               | 改用 commit SHA 標記、鎖定依賴版本      |

## 常見誤區

Container 常被簡化成「打包完就好」的步驟，結果是部署風險被後移到 rollout 階段。runtime 產物穩定性不足時，後續 probe、canary、rollback 都只能被動補救。

把資源限制設成平台預設值，也常造成高峰期不穩。限制應反映服務真實耗用模式，不應只追求表面資源利用率。

把 `latest` tag 當成版本標記，會讓 rollback 指向無法預測的 image。image tag 在 registry 上是 mutable——同一個 tag 可以被覆蓋指向新 image。用 immutable tag（commit SHA、content digest）才能保證 rollback 的確定性。

把所有配置都用環境變數注入，會讓設定變更跟 image 部署綁在一起。需要動態更新的設定（feature flag、rate limit 閾值）應該用 ConfigMap mount 或外部 config store，讓設定變更不需要 pod restart。

## 案例回寫

runtime 穩定性可用 [5.C1 Tradeshift：self-managed K8s -> EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) 回寫。先看遷移期內啟動行為與資源限制如何影響切流，再對照本章檢查 image、entrypoint、limit 與 config 相容窗口。這個案例主要支撐的是「執行環境可重現性」判讀——遷移到新叢集時，image 不變但 runtime 環境變了（node OS、container runtime 版本、network plugin），runtime 穩定性的前提是 image 本身不依賴特定宿主環境的行為。

[5.C5 Miro managed EKS 遷移](/backend/05-deployment-platform/cases/miro-managed-eks-migration/) 從另一個角度支撐：managed 平台接管 runtime 基礎設施後，container runtime 版本升級由平台控制，團隊要能驗證自家 image 在新 runtime 版本下行為一致。

若同版容器在不同節點出現分歧行為，先追建置來源與 runtime config 版本鏈，確認是依賴漂移還是環境漂移，再把關鍵證據收斂到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。不直接支撐 service discovery TTL 或 queue replay 邏輯；若根因在定位鏈路或重播流程，應轉到 5.4 或 3.4。

## 跨模組路由

1. 與 5.2 的交接：部署批次與探針策略回到 [Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。
2. 與 5.3 的交接：流量進出與連線收斂回到 [load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。
3. 與 5.6 的交接：startup / readiness / drain 的生命週期定義回到 [Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)。
4. 與 4.20 的交接：啟動與資源證據回到 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
5. 與 6.8 的交接：放行與回退條件回到 [Release Gate](/backend/06-reliability/release-gate/)。
6. 與 7.3 的交接：image 安全基線與攻擊面回到 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)。

## 下一步路由

要把 runtime 行為接到部署收斂，接著讀 [5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。要看切流與退場條件，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。要看 runtime 層的生命週期如何被平台表達，接著讀 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)。
