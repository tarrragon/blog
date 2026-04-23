---
title: "模組六：生產操作"
date: 2026-04-22
description: "graceful shutdown、健康檢查、結構化日誌與 feature gate"
weight: 6
---

生產操作的核心目標是讓 Go 服務可停止、可觀測、可診斷、可漸進啟用功能。服務能在本機跑起來只是第一步；長時間運行後，真正重要的是 shutdown 是否可預期、監控訊號是否清楚、[log](../../backend/knowledge-cards/log/) 是否可查詢、功能開關是否有降級策略。

本模組承接前面的並發、[WebSocket](../../backend/knowledge-cards/websocket/)、runtime 與測試：[graceful shutdown](../../backend/knowledge-cards/graceful-shutdown/) 需要 context 和 goroutine lifecycle，health endpoint 需要區分可用性與診斷，structured [log](../../backend/knowledge-cards/log) 需要能追 event flow，feature gate 需要能安全控制新能力。

## 章節列表

| 章節                       | 主題                                 | 關鍵收穫                                                |
| -------------------------- | ------------------------------------ | ------------------------------------------------------- |
| [6.1](graceful-shutdown/)  | [graceful shutdown](../../backend/knowledge-cards/graceful-shutdown) 與 signal handling | 用 signal、context、[timeout](../../backend/knowledge-cards/timeout/) 與 owner cleanup 停止服務   |
| [6.2](health-diagnostics/) | 健康檢查與診斷 endpoint              | 區分 health、[readiness](../../backend/knowledge-cards/readiness/)、diagnostics 與 status code 合約 |
| [6.3](log-fields/)         | 結構化日誌欄位設計                   | 用穩定欄位讓 log 可 grep、可聚合、可追蹤                |
| [6.4](feature-gate/)       | 版本偵測與 feature gate              | 用功能開關、能力偵測與降級策略控制行為                  |

## 本模組使用的範例主題

本模組使用虛構的即時通知服務作為範例。範例包含 HTTP server、[WebSocket](../../backend/knowledge-cards/websocket) hub、background worker、runtime diagnostics、structured log 與 feature gate。

範例只用來展示 Go 生產操作設計，不假設讀者正在維護任何特定專案。

## 本模組的 Go 核心概念

- 用 `signal.NotifyContext` 或 signal channel 建立 root context。
- 用 `http.Server.Shutdown` 停止接受新 request。
- 用 context 傳遞停止訊號給 worker、hub、WebSocket pump。
- 用 `/health`、`/ready`、`/debug/...` 分開不同操作訊號。
- 用 `log/slog` 建立穩定 structured fields。
- 用 config struct 載入 feature gate，而不是到處讀環境變數。

## 學習重點

學完本模組後，你應該能判斷：

1. 服務收到停止訊號後，哪些元件要先停止接流量
2. health、[readiness](../../backend/knowledge-cards/readiness)、diagnostics 各自回答什麼問題
3. structured log 欄位如何支援查詢與聚合
4. 哪些資料不應進入 log
5. feature gate 關閉時應降級、回錯、隱藏還是排程稍後處理

## 本模組不處理

本模組不討論 Kubernetes、systemd、雲端平台或完整 SRE 流程的所有細節。這些環境會影響操作策略，但本模組先建立 Go 服務本身應具備的操作邊界；後續可接 [Kubernetes、systemd 與 load balancer 合約](../07-distributed-operations/deployment-contracts/) 以及 [Observability pipeline、metrics 與 tracing](../07-distributed-operations/observability-pipeline/)。

## 學習時間

預計 3-4 小時
