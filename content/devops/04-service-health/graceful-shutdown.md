---
title: "Graceful shutdown"
date: 2026-07-03
description: "設計服務收到停止信號後的收束流程時，釐清 SIGTERM 到 SIGKILL 的 grace period、退場的固定順序、以及不同 workload 的 drain 窗口要留多長"
weight: 5
tags: ["devops", "graceful-shutdown", "sigterm", "drain", "signal"]
---

服務收到停止信號時，graceful shutdown 決定它是有序收束、還是被硬砍中斷。有序收束的責任分兩層：shutdown 是服務停止接受新工作、釋放自己持有的資源；drain 是平台在真正移除這個實例之前，讓已經在處理的請求、連線、背景工作有時間收完。這兩層都做對，一次正常的部署替換或縮容才不會掉掉在途的工作；做錯，使用者會在每次部署時撞到中斷的請求。

收束的相對面是硬砍。平台給的收束時間是有上限的，超過上限服務就被 `SIGKILL` 強制結束、不走任何清理。所以 graceful shutdown 的成敗判準是清理邏輯能不能在 grace period 內跑完——跑不完，清理邏輯寫得再完整也等於沒有。

## 信號路徑與 grace period

關閉從一個信號開始，設計的第一件事是確認這個信號真的到得了服務、以及服務有足夠時間反應。在 Kubernetes 上，平台先執行 preStop hook、再送 `SIGTERM`；`terminationGracePeriodSeconds` 是平台願意等的最長時間，超過就 `SIGKILL`。這個值要覆蓋 preStop、drain、資源釋放的總時間——設太短，收束到一半被硬砍。

驗證信號到不到得了服務，靠實際觸發一次關閉看紀錄：在 staging 觸發實例刪除，看 log 有沒有出現關閉處理器的紀錄。沒看到，代表信號根本沒傳到服務，要先修傳遞路徑、再談清理邏輯——清理邏輯寫得再完整，信號收不到就一行都不會跑。

## 退場的固定順序

實例退場的四個步驟要固定順序：平台先把這個實例從流量目標摘掉、服務停止接受新請求、服務完成手上的在途請求、實例退出。順序穩定，rollback 這種「反向操作」才能在同一套機制下運作。這條順序的第一步對應 [readiness](/devops/04-service-health/liveness-vs-readiness/)——關閉的起手式是把 readiness 轉為否，讓平台停止送新流量，而不是直接關進程。先把流量停掉再收束在途工作，跟先關進程再期待流量自己不來，是完全不同的結果。

這裡有一個單機環境不會遇到、多機才有的細節：readiness 轉為否，到平台真的停止送流量之間，有一段傳播延遲。Kubernetes 把 endpoint 跟 readiness 綁定，readiness 轉否要先傳到 endpoint controller、再傳到每個節點的 kube-proxy 或 envoy，這段期間客戶端仍可能打到已經標記為 not-ready 的實例。穩定的做法是在 preStop hook 加一段短暫等待（5 到 15 秒），讓摘除的狀態傳播到所有轉發層，再開始真正的收束。這段等待是 drain 總窗口的一個子區間，不是浪費——它填的正是「服務說我不 ready」跟「流量真的不再進來」之間的空隙。

## drain 窗口按 workload 決定

Drain 要留多久，取決於服務跑的是哪種 workload，沒有通用值：

- **短請求 API**（HTTP REST、gRPC unary）：窗口通常 5 到 30 秒，收束條件是在途請求數歸零。主要風險是負載平衡的 deregistration delay 仍會送幾秒流量進來，drain 窗口要覆蓋這段。
- **長連線**（WebSocket、gRPC streaming、SSE）：窗口從 30 秒到數分鐘，收束條件是現有連線收斂、且重連的波形穩定。主要風險是 reconnect storm——一堆連線同時被斷、同時重連，把接手的實例壓垮。
- **背景 worker**：窗口取決於單一 job 的最長執行時間，收束條件是不可中斷的 job 跑完。風險是被強制結束的 job 留下不一致狀態。

服務若混合了多種 workload，drain 窗口取最嚴格（最長）的那個——短請求 5 秒就收完，但同一個服務還有一個要跑兩分鐘的 job，總窗口就得容納兩分鐘。用短請求的窗口去砍一個長 job，等於每次部署都中斷它。

## 信號收不到，收束就變硬砍

清理邏輯的前提是收得到信號，容器環境有三個常見的信號傳不到陷阱，都跟 PID 1 有關。第一個是用 shell 當 PID 1 又不轉發——`ENTRYPOINT ["sh", "-c", "java -jar app.jar"]` 這種寫法，`SIGTERM` 送到 sh，sh 預設不轉發給 java，java 一直收不到、等 grace period 到期被 `SIGKILL` 強殺；修法是用 exec form 或在腳本裡 `exec`，讓服務直接當 PID 1。第二個是多進程容器的殭屍回收——PID 1 不做 `wait()`，結束的子進程累積成殭屍，這屬於 [supervisor 選型](/devops/04-service-health/process-supervisor-selection/) 裡 init process 的職責。第三個是啟動腳本的 trap handler 卡住，把本來 graceful 的關閉拖成 ungraceful 的 hang——trap handler 本身要設逾時，不能無限等。

這三個陷阱的共同表現是一樣的：log 裡看不到關閉處理器跑過的紀錄、服務每次都撐到 grace period 上限才消失。看到這個表現，先查 PID 1 是誰、信號有沒有轉發，而不是先懷疑清理邏輯。

## 收束要保護的是已承諾未完成的工作

Graceful shutdown 真正要保護的，是那些「已經對外承諾、但還沒真正完成」的工作。本站 collector 是個具體例子：它收到事件先回 202、事件進 channel buffer、再非同步寫入儲存。從回 202 到真正寫入之間有一個窗口，這段期間若被 `SIGKILL` 硬砍，這些已承諾但未持久化的事件就遺失了。graceful shutdown 的收束序列要 flush 這些 pending write——把 buffer 裡還沒寫的先寫完，再退出。

哪些關閉保護得了、哪些保護不了，看退出走不走 graceful。走 `SIGTERM` 加 grace period 的正常關閉，收束序列有機會 flush；但 OOM kill、硬體故障這種非 graceful 的結束，不走任何清理、在途工作直接中斷——這也是 [liveness](/devops/04-service-health/liveness-vs-readiness/) 要在記憶體逼近上限時主動回報 unhealthy 的理由：主動回報讓平台在還能 graceful 的時候有序重建，好過等 OOM kill 硬砍中斷在途工作。這條「有沒有走 graceful」的分界在監控上也留得下痕跡——collector 正常關閉會送一個 `collector.shutdown` 事件，這個事件的有無，就是區分有序退場跟異常中斷的訊號。

## 下一步路由

- 收束的第一步是 readiness 轉否、停止接流量 → [Liveness 與 Readiness](/devops/04-service-health/liveness-vs-readiness/)
- 信號傳不到的 PID 1 選型問題 → [Process supervisor 選型](/devops/04-service-health/process-supervisor-selection/)
- 部署替換時 drain 與 rollback 的完整流程 → [Backend 部署替換、drain 與 rollback](/backend/05-deployment-platform/deployment-rollout-drain-rollback/)
- 端到端資料完整性：已承諾未持久化窗口的更多場景 → [端到端資料完整性](/monitoring/04-collector/data-integrity/)
