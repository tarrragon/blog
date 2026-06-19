---
title: "CI 中的服務 fixture 管理"
date: 2026-06-19
description: "在 CI 中啟動和停止真實服務的 test harness 設計 — Process.start / Docker / testcontainers 三種方案的適用場景"
weight: 4
tags: ["testing", "integration-test", "ci", "fixture", "docker", "testcontainers"]
---

Protocol integration test 需要真實的外部服務實例。在 CI 中管理這些服務實例的啟動、初始化、健康檢查和停止，是 protocol integration test 基礎設施的核心問題。

## 三種服務管理方案

### Process.start（直接啟動程序）

在 test 的 setUp 中用 `Process.start` 啟動服務程序，tearDown 中用 `process.kill` 停止。

適合的前提：服務是單一二進位檔（不需要 Docker），啟動速度快（< 2 秒），不需要持久化狀態。

app_tunnel 的 ttyd 就是這個模式。`ttyd bash` 一行指令啟動，不需要設定檔，不需要資料庫，啟動到可接受連線約 500ms。Test harness 只需要：

```text
setUp: process = Process.start('ttyd', ['--port', '7681', 'bash'])
       await waitForPort(7681, timeout: 3s)
tearDown: process.kill()
```

### Docker Compose

用 Docker Compose 定義服務堆疊，CI 的 before_all 階段 `docker compose up`，after_all 階段 `docker compose down`。

適合的前提：服務有依賴（database + cache + app server）、需要特定 OS 環境、需要精確的版本控制。

Docker Compose 的成本是 image pull 時間（首次或 image 更新時）和容器啟動時間。CI 中可以用 image cache 減少 pull 時間，但冷啟動仍比直接啟動程序慢。

### Testcontainers

在 test 程式碼中用 testcontainers 套件管理 Docker 容器。每個 test class 或 test suite 啟動自己的容器，test 結束後自動清理。

適合的前提：和 Docker Compose 類似，但需要更細粒度的控制（不同 test 用不同的服務設定），或需要在 test 程式碼中動態決定服務的啟動參數。

Testcontainers 的優勢是 test 和 fixture 在同一個程式碼檔案中，容易理解每個 test 需要什麼環境。缺點是每個 test suite 啟動自己的容器，比共用容器慢。

## 健康檢查

服務啟動後到可以接受請求之間有延遲。直接在啟動後發送 test request 會因為服務尚未 ready 而失敗。

健康檢查的方式依服務類型而定：

**TCP port 可達**：`waitForPort(port, timeout)` 反覆嘗試 TCP 連線，成功即表示服務在監聽。最簡單，適合所有 TCP 服務。

**HTTP health endpoint**：對 `/health` 或 `/ready` 發送 GET request，收到 200 表示服務 ready。比 port check 更可靠 — port 監聽不代表應用層 ready。

**特定操作成功**：執行一個輕量的業務操作（例如 WebSocket 連線 + 簡單指令），成功表示服務完全 ready。最可靠但最慢。

## 服務狀態隔離

不同 test 之間的服務狀態需要隔離 — test A 在服務中建立的資料不應該影響 test B。

三種隔離策略：

**每 test 重啟服務**：最強隔離，最慢。適合服務啟動快（< 1 秒）的場景。

**每 test 重設狀態**：服務持續運行，test 開始前清理狀態（truncate tables, flush cache）。適合服務啟動慢但重設快的場景。

**每 test 用獨立 namespace**：服務持續運行，每個 test 使用獨立的 database schema / topic / channel。適合支援多租戶的服務。

app_tunnel 的 ttyd 是無狀態服務（每次連線是獨立的 terminal session），不需要狀態隔離。每個 test 建立新的 WebSocket 連線 = 新的 session。

## 下一步路由

- 什麼時候值得建 protocol integration test 基礎設施 → [成本判斷表](/testing/03-protocol-integration-test/cost-judgment/)
- Protocol integration test 的定義 → [Protocol integration test 定義](/testing/03-protocol-integration-test/definition-and-boundary/)
- WebSocket 的 protocol test 實作 → [WebSocket 協議測試實作](/testing/03-protocol-integration-test/websocket-protocol-test/)
