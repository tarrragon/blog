---
title: "5.6 Platform Lifecycle Contract"
date: 2026-05-11
description: "說明 runtime、startup、readiness、liveness、shutdown 與 drain 如何組成平台生命週期合約。"
weight: 6
tags: ["backend", "deployment", "platform", "lifecycle"]
---

Platform lifecycle contract 的核心責任是讓服務和部署平台對同一組生命週期訊號有共同解讀。進入 Kubernetes、systemd、Docker、ELB 或 Envoy 前，讀者需要先理解「服務啟動」和「服務可接流量」是不同狀態。

## Lifecycle Contract

Lifecycle contract 定義平台如何啟動、檢查、接流量、停止與回收服務實例。它包含 runtime、startup、readiness、liveness、shutdown 與 drain。

| 狀態      | 服務責任                                   | 平台責任                    |
| --------- | ------------------------------------------ | --------------------------- |
| runtime   | 固定 image、entrypoint、config 與 resource | 提供可預期執行環境          |
| startup   | 初始化依賴與內部狀態                       | 避免過早重啟慢啟動服務      |
| readiness | 宣告可安全接流量                           | 只把流量導向 ready instance |
| liveness  | 宣告基本運作能力                           | 在不可恢復時重建 instance   |
| shutdown  | 停接新工作並釋放資源                       | 給予 termination window     |
| drain     | 完成在途請求或連線退場                     | 從路由集合摘除 instance     |

這些狀態分開後，部署事故才能定位是啟動、接流量、退場還是平台判讀問題。

runtime 與 startup 決定服務能否形成可運行實例。readiness 與 liveness 決定平台何時導入流量與何時重建實例。shutdown 與 drain 決定版本退場時是否能保護在途工作。這些狀態都屬於生命週期合約，卻對應不同的事故處理路徑。

## Startup 與 Readiness

startup 的責任是確認服務初始化完成。[readiness](/backend/knowledge-cards/readiness/) 的責任是確認服務可承接實際流量。啟動完成不代表依賴已就緒，也不代表背景任務、config、secret 或 connection pool 都可用。

慢啟動服務需要 startup gate，避免 liveness 在初始化期間反覆重啟。依賴敏感服務需要 readiness gate，避免尚未連上資料庫、cache 或 queue 時就接收請求。

### 啟動時間的組成與壓縮

服務啟動時間的長短決定 rollout 節奏的下限。啟動時間由四段組成，每段有不同壓縮策略：

1. **runtime 初始化**：語言 VM、GC 初始化、class loading（JVM warmup 可達 10-30 秒）。壓縮手段是 ahead-of-time compilation（GraalVM native image、Go 靜態編譯啟動速度快）或 CDS（Class Data Sharing）。
2. **依賴建立**：資料庫連線池、cache 連線、queue consumer 註冊。壓縮手段是 lazy initialization（按需建立）或 connection pool pre-warming（啟動時建好但不阻擋 readiness）。
3. **資料預載**：config 同步、feature flag 初始拉取、本地快取預熱。壓縮手段是區分必要載入與非必要載入——必要的阻擋 readiness，非必要的平行載入。
4. **就緒驗證**：自我健康檢查、依賴可達性驗證。壓縮手段是平行驗證多個依賴，避免串行等待。

啟動時間超過平台預設 startup timeout 時，先拆成這四段分析瓶頸，再決定調大 timeout 還是壓縮啟動流程。盲目調大 timeout 會掩蓋啟動退化問題，讓單次 rollout 的最短觀察窗拉長。

### Readiness 設計的核心取捨

readiness 太鬆（只檢查 HTTP port 是否可達）會讓尚未就緒的實例接到流量。readiness 太緊（檢查所有下游可達性）會讓非自身問題的下游故障觸發連鎖 not-ready，放大故障面。

取捨的判讀框架是「這個依賴不可用時，服務是否仍能提供有意義的回應」：

- **必要依賴**：資料庫、auth service——不可用時服務完全無法處理請求。這類依賴的可達性應納入 readiness 條件。
- **可降級依賴**：推薦引擎、非關鍵 cache——不可用時服務可回傳降級結果。這類依賴不應納入 readiness，改用 [circuit breaker](/backend/knowledge-cards/circuit-breaker/) 或 [fallback](/backend/knowledge-cards/fallback/) 處理。
- **觀測依賴**：metrics collector、log shipper——不可用不影響業務流量。這類依賴進 readiness 是常見誤判，會讓觀測基礎設施故障擊倒整個服務。

對應 [5.C3 Orbitera managed K8s migration](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/)：揭露「跨平台遷移本質是能力遷移、部署 / 觀測 / 恢復與團隊流程都需要同步重建」。遷移到新平台時，舊平台的 readiness 條件不能直接搬——新平台的依賴可達路徑、DNS 解析速度、secret 注入方式可能改變，readiness 條件要重新驗證。

## Liveness 與 Restart

liveness 的責任是偵測無法自我恢復的狀態。短暫下游故障適合交給 readiness、circuit breaker 或 fallback 處理，否則平台會用重啟放大故障。

liveness 太敏感會造成 restart loop；liveness 太寬鬆會讓壞實例長期留在線上。設計時要先定義哪些錯誤可由服務內部恢復，哪些才需要平台重建。

### Liveness 適合偵測的失敗模式

liveness 的工程價值在於捕捉服務自己無法修復的狀態。把 liveness 當成通用健康檢查是過度使用，會讓正常的瞬態故障觸發不必要的重建。

適合 liveness 偵測的狀態：

- **deadlock**：所有 worker thread 被卡住，無法處理新請求也無法回傳錯誤。liveness endpoint 設在獨立 goroutine / thread 上，如果 worker pool 卡住但 liveness goroutine 能回應，問題在業務邏輯而非 deadlock。
- **memory leak 導致的 OOM 前兆**：記憶體使用率持續上升不回落，GC 已無法回收。此時主動回報 unhealthy 讓平台在 OOM kill 前重建，比被動等 OOM 更可控——OOM kill 不走 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/)，在途請求直接中斷。
- **essential background task 永久停止**：必要的定期任務（如 license renewal、session cleanup）超過預期間隔仍未執行。這類失敗靜默發生，只有 liveness 主動偵測能發現。

不適合 liveness 偵測的狀態：下游資料庫短暫不可用、外部 API timeout、cache miss 率升高。這些由 readiness 或 circuit breaker 處理——用 liveness 重建不會修好下游，只會用重啟放大問題。

### Restart 的代價量化

每次 liveness 觸發的重啟會產生四類代價：

1. **在途請求中斷**：被重啟的實例正在處理的請求直接失敗。
2. **連線重建成本**：資料庫連線池、cache 連線、queue consumer 重新建立。
3. **啟動期間的容量缺口**：重啟到 readiness 通過之間，整體服務容量降低。
4. **thundering herd 風險**：多實例同時被 liveness 判定失敗並重啟時，同時重建連線、同時搶資源、下游壓力瞬間放大。

對應 [5.C7 Airbnb Istio 升級治理](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/)：揭露「基礎平台元件升級若缺乏分批治理、會形成全域風險放大器」。以下基於通用工程知識展開：Istio 等 service mesh 升級期間的 sidecar 重啟可觸發大量服務的 liveness 暫時失敗，若 liveness 太敏感會放大成全域 restart storm。升級期的 liveness 閾值應比穩態更寬鬆，或在升級批次中暫時加大 liveness failure threshold。

## Shutdown 與 Drain

shutdown 的責任是讓服務停止接新工作並完成資源釋放。[draining](/backend/knowledge-cards/draining/) 的責任是讓平台在移除實例前，讓 [in-flight](/backend/knowledge-cards/in-flight/) request、長連線或背景工作有時間收束。

短 request API、長連線服務與 background worker 的 drain 條件不同。短 API 主要看在途請求歸零；長連線看 reconnect 節奏；worker 看已領取工作能否完成或重新排隊。tunnel 入口的 startup / readiness / drain 對齊見 [5.10 Outbound Tunnel 入口](/backend/05-deployment-platform/outbound-tunnel-entry/)。

### 三種 Workload 的 Drain 差異

不同 workload 類型的 drain 完成條件與時間尺度完全不同，用同一套 drain 設定覆蓋所有 workload 會在至少一類服務上出事。

**短 request API**（HTTP REST、gRPC unary）：drain 窗口通常在 5-30 秒。核心條件是在途請求數歸零。風險點是 load balancer 的 deregistration delay——LB 可能在服務已標記 not-ready 後仍送幾秒流量（取決於 health check interval 與 deregistration delay），所以服務端 drain 窗口要覆蓋這段延遲。endpoint 摘除的傳播窗口與 preStop 等待策略見 [5.4 摘除節奏與 Drain 的配合](/backend/05-deployment-platform/service-discovery/)。

**長連線服務**（WebSocket、gRPC streaming、SSE）：drain 窗口通常在 30 秒到數分鐘。核心條件是現有連線收斂且 reconnect 波形穩定。風險點是客戶端 reconnect 策略——服務端 drain 完成不代表客戶端已連上新實例。若客戶端沒有 backoff 或 reconnect 目標選擇邏輯，會形成 reconnect storm。drain 設計要跟客戶端 reconnect 策略一起規劃。

**Background worker**（queue consumer、定時任務、batch job）：drain 窗口取決於單一工作的最長執行時間。核心條件是已領取的工作完成處理或安全重新排隊。風險點是不可中斷工作——某些 job 做到一半無法重試（例如外部 API 呼叫已發出但回應尚未確認），drain 時序要覆蓋這類 job 的最長完成時間，否則 job 被中斷後產生不一致狀態。

對應 [5.C9 反例：平台切流未先 Draining](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)：揭露「切流失敗常在 connection lifecycle 管理」「drain / idle timeout / health check / client retry 沒有同一節奏」。反例中的事故擴大機制正是不同 workload 類型的 drain 條件被忽略——短 API 的 drain 完成了，長連線的 reconnect 仍在震盪，worker 的 job 被中斷重試造成重複處理。

### Shutdown 信號的傳遞路徑

platform 到 application 的 shutdown 信號傳遞有多個可能斷點。信號從平台送到容器 PID 1、PID 1 轉發到應用進程——PID 1 的信號處理語意與常見陷阱見 [5.1 PID 1 與信號處理](/backend/05-deployment-platform/container-runtime/)。本段聚焦 lifecycle 層的時序問題：

- **preStop hook 與 SIGTERM 時序**：Kubernetes 先執行 preStop hook、再送 SIGTERM。preStop hook 可用來等 LB 摘流量（sleep 幾秒讓 [endpoint 從可用集合移除](/backend/05-deployment-platform/service-discovery/)），讓 SIGTERM 到達時在途流量已經減少。
- **terminationGracePeriodSeconds**：平台等待的最長時間。超過後 SIGKILL 強制結束，不走 graceful shutdown。這個值要覆蓋 preStop + drain + 資源釋放的總時間。

shutdown 信號傳遞的驗證方式是在 staging 環境觸發 pod delete，觀察應用 log 中是否出現 shutdown handler 的紀錄。沒看到 shutdown log 代表信號沒傳到、要先修傳遞路徑再談 drain 設計。

## 不同 Workload 的 Lifecycle 特性對照

生命週期合約的參數設定要依 workload 類型調整。以下是三類常見 workload 的特性差異。

| 維度             | 短 request API          | 長連線服務                   | Background worker                |
| ---------------- | ----------------------- | ---------------------------- | -------------------------------- |
| startup 關注點   | 依賴連線池建立          | 依賴連線池 + 監聽埠就緒      | queue consumer 註冊完成          |
| readiness 條件   | 必要依賴可達 + 連線池滿 | 必要依賴可達 + 可接受新連線  | consumer 已註冊 + 可拉取新工作   |
| liveness 偵測    | deadlock、OOM 前兆      | 連線管理 thread 存活         | worker loop 存活、queue 輪詢正常 |
| drain 完成條件   | 在途請求數歸零          | 現有連線收斂、reconnect 穩   | 已領取工作完成或重新排隊         |
| drain 窗口       | 5-30 秒                 | 30 秒 - 數分鐘               | 取決於最長 job 執行時間          |
| shutdown 風險    | LB 延遲仍送流量         | reconnect storm              | 不可中斷 job 被強制結束          |
| rollout 節奏建議 | 可激進（秒級觀察窗）    | 保守（分鐘級、等 reconnect） | 依 job 粒度（完成當前批次再切）  |

這張表是選型前判準的操作化：先確認服務屬於哪類 workload，再套用對應的 lifecycle 參數基線。混合 workload（例如同時提供 HTTP API 和 WebSocket）要取各層的嚴格值——drain 窗口取最長的、readiness 取最嚴格的。

## 平台如何表達 Lifecycle 差異

不同部署平台表達生命週期合約的能力不同。選型時要問的是「這個平台能不能分別設定 startup、readiness、liveness 與 drain」。

| 平台       | startup gate          | readiness 與 liveness 分離          | drain 能力                   | termination 窗口              |
| ---------- | --------------------- | ----------------------------------- | ---------------------------- | ----------------------------- |
| Kubernetes | startupProbe          | readinessProbe / livenessProbe 獨立 | preStop hook + endpoint 摘除 | terminationGracePeriodSeconds |
| systemd    | 無原生 startup probe  | 靠 sd_notify(READY=1)               | ExecStop + KillSignal        | TimeoutStopSec                |
| Docker     | HEALTHCHECK（不分離） | 單一 HEALTHCHECK                    | stop_grace_period            | stop_grace_period             |
| ECS        | startupHealthCheck    | health check（不分離）              | deregistration delay         | stopTimeout                   |

Kubernetes 在 lifecycle 表達力上最完整，但參數最多也最容易配錯。systemd 靠 sd_notify 協議明確宣告 readiness，在單機部署場景下反而比 K8s 的 probe 直接。Docker 和 ECS 不分離 readiness 與 liveness，需要在應用層自行實作降級邏輯。

選平台不只看功能清單，要看它表達 lifecycle 差異的粒度是否覆蓋服務需求。若服務需要分離 startup 和 readiness 但平台只有一個 health check，這個差距要在應用層補——代價是複雜度從平台設定轉移到程式碼。

## 遷移期的 Lifecycle 重新驗證

對應 [5.C6 Airbnb Kubernetes 叢集擴縮演進](/backend/05-deployment-platform/cases/airbnb-kubernetes-cluster-scaling-evolution/)：揭露「擴縮策略版本化與可回放」「不同 workload 區分擴縮政策」。以下基於通用工程知識展開：叢集演進過程中，lifecycle 參數的假設會改變——workload 從穩態變成高波動、從單一類型變成混合類型、從小規模變成大規模。lifecycle contract 的參數不是設一次就好，要隨叢集演進重新驗證。

對應 [5.C10 對照：規模差異下的平台遷移](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)：揭露「小型組織最容易漏掉回退腳本化」「中型組織依賴錯位、服務切過去但資料面 / 認證面 / 觀測面沒同步」。lifecycle contract 在遷移後的完整性驗證不只看 probe 設定——secret 注入時序、資料庫連線池的 endpoint 是否切到新叢集、observability pipeline 的 readiness 是否對齊，都是 lifecycle 合約的一部分。

遷移後的 lifecycle 驗證清單：

1. **startup 時序重測**：新平台的 image pull 時間、secret mount 時間、DNS 解析路徑可能不同，原本的 startup timeout 可能不夠。
2. **readiness 依賴路徑檢查**：readiness 檢查的依賴是否仍可達（新叢集到舊資料庫的 latency 是否增加、跨叢集 [service discovery](/backend/05-deployment-platform/service-discovery/) 是否對齊、DNS TTL 與快取行為是否改變）。
3. **drain 行為驗證**：在新平台觸發 pod delete、觀察 drain 完成時間與在途請求處理是否符合預期。
4. **信號傳遞驗證**：在新平台觸發 shutdown、確認 SIGTERM 到達應用進程並觸發 graceful shutdown handler。

## 選型前判準

部署平台選型前要先回答：

1. 服務啟動需要多久，哪些依賴是 readiness 條件。
2. 服務失敗時應由自己恢復，還是由平台重建。
3. 服務停止時有哪些 in-flight request、connection 或 job。
4. 平台是否能表達 startup、readiness、liveness 與 drain 的差異。

這些問題決定後續要比較 Kubernetes probe、systemd restart policy、load balancer health check 或 service mesh drain 能力。

## 判讀訊號

| 訊號                                    | 判讀重點                                  | 對應動作                                      |
| --------------------------------------- | ----------------------------------------- | --------------------------------------------- |
| rollout 期間新版本反覆重啟              | startup timeout 小於實際啟動時間          | 拆分啟動四段分析瓶頸、調整 startup gate       |
| 新版本 readiness 通過但首批請求錯誤率高 | readiness 條件太鬆、依賴未就緒就接流量    | 加入必要依賴檢查、分離可降級依賴              |
| 下游故障時大量實例被 liveness 重啟      | liveness 檢查了不該檢查的下游依賴         | 把下游可達性移到 readiness、liveness 只看自身 |
| shutdown 後仍有請求中斷                 | SIGTERM 未正確傳達或 drain 窗口不足       | 驗證信號傳遞路徑、調整 terminationGracePeriod |
| 長連線服務切版後 reconnect storm        | drain 設計未考慮客戶端 reconnect 策略     | 拉長 drain、分批切流、搭配 reconnect backoff  |
| worker 切版後出現重複處理               | job 被中斷後重試、但前次已產生副作用      | drain 窗口覆蓋最長 job、或 job 支援冪等       |
| 遷移新平台後啟動時間變長                | 新平台 image pull / secret mount 路徑不同 | 重測啟動四段、調整新平台的 startup timeout    |

## 常見誤區

把所有 probe 設成同一個 `/health` endpoint，會讓 startup、readiness 與 liveness 的語意混在一起。三種 probe 回答不同問題：startup 問「初始化完了嗎」、readiness 問「可以接流量嗎」、liveness 問「還活著嗎」。同一個 endpoint 無法同時回答三個問題，因為初始化完成不代表依賴就緒，依賴暫時不可達不代表服務本身壞了。

把 drain 窗口設成固定值不分 workload 類型，會在某一類服務上出事。5 秒對短 API 足夠、對長連線不夠、對 batch job 遠遠不夠。drain 窗口要依服務實際 workload 設定，不是用平台預設值。

把 liveness 失敗當成「服務壞了」而不問代價，會忽略重啟本身的連鎖效應。每次重啟都有在途請求中斷、連線重建、容量缺口的代價——特別是多實例同時被判定 liveness 失敗時，代價會被放大。

## 案例回寫

lifecycle contract 的完整性可用多個案例交叉驗證。[5.C3 Orbitera managed K8s migration](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/) 揭露遷移後 readiness 依賴路徑改變的風險。[5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) 揭露不同 workload 的 drain 條件被忽略造成的事故擴大。[5.C7 Airbnb Istio 升級治理](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/) 揭露基礎平台元件升級缺乏分批治理會形成全域風險放大器。[5.C10 對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/) 揭露不同規模下 lifecycle 驗證的缺口模式。

這些案例共同支撐的判讀是「lifecycle contract 的每個狀態都有不同的失敗模式，混在一起處理會在事故時無法定位」。流量切換或連線生命週期問題路由到 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。runtime 產物穩定性問題路由到 [5.1 container 與 runtime](/backend/05-deployment-platform/container-runtime/)。

## 跨模組路由

lifecycle contract 是部署模組的概念基底，後續章節都會引用本篇的狀態分類。

1. 與 5.1 的交接：runtime 與 entrypoint 定義 startup 行為回到 [container 與 runtime](/backend/05-deployment-platform/container-runtime/)。
2. 與 5.2 的交接：probe 設定與 rollout 節奏回到 [Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。
3. 與 5.3 的交接：drain 與流量退場回到 [load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。
4. 與 5.10 的交接：tunnel 入口的 readiness 與 drain 對齊回到 [Outbound Tunnel 入口](/backend/05-deployment-platform/outbound-tunnel-entry/)。
5. 與 4.20 的交接：lifecycle 事件的證據收集回到 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
6. 與 6.8 的交接：lifecycle 狀態作為 release gate 判定條件回到 [Release Gate](/backend/06-reliability/release-gate/)。
7. 與 devops 的交接：startup / readiness / liveness / drain 的概念層探活、probe 語意與自動恢復進入 [devops 模組四：服務探活](/devops/04-service-health/)。

## 下一步路由

要看 Kubernetes 如何承接這組生命週期，接著讀 [5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。要看流量退場如何和 LB 對齊，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。要看不同平台的 lifecycle 表達力比較，接著讀 [vendors/](/backend/05-deployment-platform/vendors/)。
