---
title: "成本判斷表"
date: 2026-06-19
description: "什麼時候值得寫 protocol integration test、什麼時候用 contract test 或實機測試替代 — 根據服務啟動成本和協議複雜度判斷"
weight: 5
tags: ["testing", "integration-test", "protocol", "cost", "decision"]
---

Protocol integration test 的價值在於用自動化方式驗證 mock 遮蔽的協議層盲區。但它有建置成本（服務 fixture 管理）和維護成本（服務更新時 test 要跟著改）。判斷是否值得投資，依據的是兩個維度：服務啟動成本和協議複雜度。

## 服務啟動成本

服務啟動成本決定了 protocol integration test 的執行成本 — test 跑一次要多久、CI 中佔多少時間。

### 極低成本（同機單程序）

Server 是一個本機程序，`Process.start` 一行啟動，不需要 Docker、不需要網路、不需要設定檔。啟動到 ready 不到 2 秒。

app_tunnel 的 ttyd 就是這個場景。`ttyd bash` 在本機啟動，WebSocket 服務立即可用。整個 protocol integration test suite 的額外成本約 10-15 秒（包含啟動、健康檢查、5 個 test 各 2 秒）（本章合成，TF-8 Derive）。

在這個成本等級下，protocol integration test 幾乎沒有理由不寫。

### 低成本（Docker 單容器）

Server 用 Docker 容器啟動，需要 pull image（首次或更新時），啟動到 ready 約 5-30 秒。Redis、PostgreSQL、Elasticsearch 等 open source 服務屬於這個等級。

CI 中用 image cache 可以把 pull 時間降到接近零。但容器啟動時間仍比原生程序長。整個 protocol integration test suite 的額外成本約 30-60 秒。

在這個成本等級下，如果協議有任何複雜度（見下方），protocol integration test 值得寫。

### 中等成本（多容器堆疊）

Server 依賴多個服務（app server + database + cache + message queue），需要 Docker Compose 管理。啟動到所有服務 ready 約 30-120 秒。

Protocol integration test 的執行成本顯著上升。適合在 CI 的獨立 stage 跑（和 unit test 分開），避免拖慢 fast feedback loop。

### 高成本（外部服務 / SaaS）

Server 是外部 SaaS（Stripe API、AWS S3、第三方 OAuth provider），無法本地啟動。Test 需要打到 sandbox environment，有速率限制和網路延遲。

在這個成本等級下，consumer-driven contract test 可能比 protocol integration test 更實用 — 用 contract 定義期望的 request/response，在本地驗證 client 端行為，不需要每次都打到外部服務。

## 協議複雜度

協議複雜度決定了 mock 遮蔽的風險大小 — 風險越大，protocol integration test 的價值越高。

**高複雜度**：WebSocket（frame type、handshake、子協議）、gRPC（streaming、deadline、metadata）、MQTT（QoS level、retain、will message）。API 簽名隱藏了協議層的行為分支，mock 結構性地無法覆蓋。

**中複雜度**：HTTP REST API（多種 status code、error body 格式、認證流程、分頁）。核心語意（JSON request/response）差距小，但 edge case（error response 格式、header 要求）仍可能被 mock 遮蔽。

**低複雜度**：本地 IPC（Unix socket、named pipe）、標準格式的檔案讀寫。協議行為簡單，mock 和真實行為差距小。

## 判斷矩陣

| 服務啟動成本 | 協議複雜度高         | 協議複雜度中       | 協議複雜度低  |
| ------------ | -------------------- | ------------------ | ------------- |
| 極低         | protocol test        | protocol test      | protocol test |
| 低           | protocol test        | protocol test      | 可選          |
| 中           | protocol test        | 視 mock 寬鬆度決定 | 實機測試替代  |
| 高           | contract test + 實機 | contract test      | 實機測試替代  |

「可選」代表 protocol integration test 有價值但不是必要 — 實機測試階段的手動驗證可能足夠。「實機測試替代」代表成本太高或收益太低，依賴實機測試階段的人工驗證。

成本和複雜度的評估結果決定了要建什麼等級的 test 基礎設施。[Protocol integration test 定義](/testing/03-protocol-integration-test/definition-and-boundary/)提供這一層 test 的精確邊界，[testing 模組一的判斷原則](/testing/01-test-strategy-layers/when-protocol-integration-test/)從 mock 遮蔽角度補充另一個判斷維度。決定要建之後，[CI 中的服務 fixture 管理](/testing/03-protocol-integration-test/service-fixture-management/)處理啟動和停止真實服務的工程問題。
