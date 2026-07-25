---
title: "成本判斷表"
date: 2026-06-19
description: "什麼時候值得寫 protocol integration test、什麼時候用 contract test 或實機測試替代 — 根據服務啟動成本和協議複雜度判斷"
weight: 5
tags: ["testing", "integration-test", "protocol", "cost", "decision"]
---

[Protocol integration test](/testing/knowledge-cards/protocol-integration-test/) 的價值在於用自動化方式驗證 [mock 遮蔽](/testing/knowledge-cards/mock-masking/)的協議層盲區。但它有建置成本（服務 fixture 管理）和維護成本（服務更新時 test 要跟著改）。判斷是否值得投資，依據的是兩個維度：服務啟動成本和協議複雜度。

## 服務啟動成本

服務啟動成本決定了 protocol integration test 的執行成本 — test 跑一次要多久、CI 中佔多少時間。

### 極低成本（同機單程序）

Server 是一個本機程序，`Process.start` 一行啟動，不需要 Docker、不需要網路、不需要設定檔。啟動到 ready 不到 2 秒。

一個遠端終端機 app 的 ttyd 就是這個場景。`ttyd bash` 在本機啟動，WebSocket 服務立即可用。整個 protocol integration test suite 的額外成本約 10-15 秒（包含啟動、健康檢查、5 個 test 各 2 秒）（本章合成，TF-8 Derive）。

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

在這個成本等級下，[consumer-driven contract test](/testing/knowledge-cards/consumer-driven-contract-test/) 可能比 protocol integration test 更實用 — 用 contract 定義期望的 request/response，在本地驗證 client 端行為，不需要每次都打到外部服務。

「無法本機啟動」有兩種形態、出路不同。對象是外部 SaaS——不可寫入、帳號與資料都不可控——contract test 是主要出路。對象是自家的共用測試環境——可寫入、有測試帳號——則可以把行為驗證寫成常駐測試、直接對真實後端斷言，見[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)。

## 協議複雜度

協議複雜度決定了 mock 遮蔽的風險大小 — 風險越大，protocol integration test 的價值越高。分級依據的判準是一個問句：**API 簽名有沒有隱藏協議層的行為分支？** 這個問句為什麼有效、各協議的語意斷裂長什麼樣，見[判斷原則的維度一](/testing/01-test-strategy-layers/when-protocol-integration-test/)——那裡同時給了另外兩個判斷維度（mock 寬鬆度、失敗靜默度）。本節只把答案收斂成矩陣需要的三級標籤：

| 級別 | 代表協議                   | 落在這一級的理由                                         |
| ---- | -------------------------- | -------------------------------------------------------- |
| 高   | WebSocket、gRPC、MQTT      | 單一 API 呼叫背後有多條協議層分支，mock 結構性覆蓋不到   |
| 中   | HTTP REST                  | 核心語意差距小，但 error body 格式與 header 要求會被遮蔽 |
| 低   | 本地 IPC、標準格式檔案讀寫 | 協議行為單一，mock 與真實的差距小到撐不起服務 fixture    |

三級的刻度跟判斷原則那篇的兩方對比不同：那裡把 REST 拿來跟 WebSocket 對照、結論是 REST 相對低；這裡的「低」保留給協議行為單一的本地 IPC，REST 因此落在中間。跨篇引用時以本節的三級為準——矩陣的軸需要一致刻度。

## 判斷矩陣

| 服務啟動成本 | 協議複雜度高         | 協議複雜度中       | 協議複雜度低  |
| ------------ | -------------------- | ------------------ | ------------- |
| 極低         | protocol test        | protocol test      | protocol test |
| 低           | protocol test        | protocol test      | 可選          |
| 中           | protocol test        | 視 mock 寬鬆度決定 | 實機測試替代  |
| 高           | contract test + 實機 | contract test      | 實機測試替代  |

「可選」代表 protocol integration test 有價值但不是必要 — 實機測試階段的手動驗證可能足夠。「實機測試替代」代表成本太高或收益太低，依賴實機測試階段的人工驗證。

成本和複雜度的評估結果決定了要建什麼等級的 test 基礎設施。[Protocol integration test 定義](/testing/03-protocol-integration-test/definition-and-boundary/)提供這一層 test 的精確邊界，[testing 模組一的判斷原則](/testing/01-test-strategy-layers/when-protocol-integration-test/)從 mock 遮蔽角度補充另一個判斷維度。決定要建之後，[CI 中的服務 fixture 管理](/testing/03-protocol-integration-test/service-fixture-management/)處理啟動和停止真實服務的工程問題。
