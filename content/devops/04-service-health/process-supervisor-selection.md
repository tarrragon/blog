---
title: "Process supervisor 選型"
date: 2026-07-03
description: "在 systemd、supervisord、Docker restart policy、Kubernetes 之間選服務監管方式時，用平台能不能分開表達 startup、readiness、liveness、drain 當判準"
weight: 4
tags: ["devops", "supervisor", "systemd", "docker", "kubernetes"]
---

選 process supervisor 的判準是這個平台能不能分別表達服務生命週期的四個階段：啟動（startup）、就緒（readiness）、存活（liveness）、收束（drain）。表達力越完整，越能讓平台在對的時機做對的動作；表達力有缺，缺的那部分邏輯就要在應用層自己補，複雜度從平台設定轉移到程式碼裡。選型不是比誰功能多，是比這個服務需要的生命週期粒度，跟平台能表達的粒度對不對得上。

在動手比較之前，先問服務四個問題：啟動要多久、哪些依賴是就緒條件；失敗時該自己恢復還是交平台重建；停止時有哪些在途請求、連線、背景工作要收束；以及平台能不能把 startup、readiness、liveness、drain 分開表達。這四個問題的答案決定了要往哪個方向選。

## 四種平台的生命週期表達力

各平台對這四階段的支援程度不同，這張對照是選型的骨架：

| 平台       | 啟動 gate            | 就緒與存活                     | 收束                           |
| ---------- | -------------------- | ------------------------------ | ------------------------------ |
| systemd    | 無原生 startup gate  | `sd_notify(READY=1)` 宣告就緒  | `ExecStop` + `KillSignal`      |
| Kubernetes | `startupProbe`       | readiness 與 liveness 獨立探針 | `preStop` hook + endpoint 摘除 |
| Docker     | 無                   | `HEALTHCHECK` 不分離就緒與存活 | `stop_grace_period`            |
| ECS        | startup health check | 依 health check 設定           | deregistration delay           |

Kubernetes 的表達力最完整——三種探針獨立、收束有 preStop hook 加 endpoint 摘除，能精確表達每個階段。代價是參數最多、也最容易配錯：探針門檻、間隔、grace period 任何一個設歪，行為就跟預期不符。systemd 在單機場景反而直接，`sd_notify` 讓服務主動宣告狀態，不必外部反覆探測，但它沒有原生的 startup gate 概念，啟動期的健康要自己用就緒宣告的時機表達。

Docker 跟 ECS 的關鍵限制是不分離就緒與存活——`HEALTHCHECK` 只有一個健康概念，無法同時回答「可以接流量嗎」跟「還活著嗎」。服務若真的需要把這兩者分開（例如依賴斷線時要摘流量但不要重啟），這段差距就得在應用層補：自己維護就緒狀態、自己在健康端點裡分辨這次探測該回答哪個問題。這不是做不到，是把本來平台該表達的邏輯搬進了程式碼。

## Restart policy 是恢復動作的表達

除了生命週期階段，各平台對「進程退出後怎麼辦」也有各自的表達。Docker 的 restart policy 有 `no`（不重啟）、`on-failure`（非零退出才重啟，可設次數上限）、`always`（永遠重啟，含手動停止後 daemon 重啟也拉起）、`unless-stopped`（類似 always 但尊重手動停止）。Kubernetes 的 Pod `restartPolicy` 有 `Always`、`OnFailure`、`Never`，語意對應到 Pod 層的容器重啟。

這些選項對應的決策跟 systemd 的 `Restart=on-failure` 是同一件事：這個服務退出時，是該無條件拉回、只在異常時拉回、還是不動它交給更上層處理。選 `always` 類的策略要搭配重試上限或退避，否則一個永遠起不來的服務會陷入無限重啟迴圈——這條跟 systemd 的 `StartLimitBurst` 是同一個問題，[systemd watchdog 與自動重啟](/devops/04-service-health/systemd-watchdog-restart/) 有單機上的完整設定。

## 容器裡的 PID 1 是另一層選型

跑在容器裡時，還有一個容易漏掉的選型：誰當 PID 1。容器的 PID 1 是 init process，除了跑服務，還負責接收 `SIGTERM`／`SIGINT` 並轉發給子進程、以及回收結束的子進程（zombie reaping）。這個責任交給誰，直接影響服務收不收得到關閉信號、以及會不會累積殭屍進程。

問題出在把服務直接設成 PID 1、又用 shell 包一層的情況。多進程容器若 PID 1 不做 `wait()`，結束的子進程會變殭屍累積。解法是用 tini 或 dumb-init 這類輕量 init 當 PID 1，讓它負責信號轉發跟殭屍回收，或在 Kubernetes 設 `shareProcessNamespace` 讓 kubelet 接手處理。信號傳不到服務造成的關閉失敗，是 [graceful shutdown](/devops/04-service-health/graceful-shutdown/) 章最常見的失效模式，根因常常就在 PID 1 選錯。

## 選型收斂

單機、服務自己寫得動、要零額外依賴 → systemd，用 `sd_notify` 宣告就緒與報活。多機、需要 startup、readiness、liveness、drain 全部分開表達、能吃下配置複雜度 → Kubernetes。容器化但生命週期需求簡單、不需要分離就緒與存活 → Docker restart policy 加 `HEALTHCHECK`，不足的部分在應用層補。判準始終是同一條：服務需要的生命週期粒度，跟平台能表達的粒度對不對得上——需求簡單卻上最複雜的平台，付的是配置成本；需求複雜卻用表達力不足的平台，付的是應用層補洞的成本。

## 下一步路由

- 平台要表達的 startup、readiness、liveness 各是什麼語意 → [Liveness 與 Readiness](/devops/04-service-health/liveness-vs-readiness/)
- systemd 上 restart policy 與 watchdog 的完整設定 → [systemd watchdog 與自動重啟](/devops/04-service-health/systemd-watchdog-restart/)
- 收束階段的信號傳遞與 grace period 設計 → [Graceful shutdown](/devops/04-service-health/graceful-shutdown/)
- 部署平台的完整生命週期契約 → [Backend 部署平台生命週期契約](/backend/05-deployment-platform/platform-lifecycle-contract/)
