---
title: "Rate Limiting"
date: 2026-06-20
description: "主動限制每個來源的請求速率 — per-client vs global、token bucket vs sliding window、優先級豁免"
weight: 2
tags: ["devops", "traffic-management", "rate-limit", "token-bucket", "sliding-window"]
---

Rate limiting 是主動的流量控制 — 在系統還沒過載之前，就限制每個來源的請求速率。和背壓不同，rate limit 的觸發依據是預設的速率上限，而非實際的系統負載。

## 兩個粒度

### Per-client（每來源限速）

限制每個 client（by API key / IP / SDK instance）的請求速率。防止單一來源打爆系統。

自用場景下 per-client 限速的價值不高（只有自己的 SDK），但開源工具被多人部署後，per-client 限速防止某個失控的 SDK 影響其他來源。

### Global（全局限速）

限制系統的總吞吐量。不管多少個 client，collector 每秒最多處理 N 個事件。

Global 限速是系統保護的最後一道線 — 即使每個 client 都在限速內，所有 client 加起來可能超過系統承載。Global 限速確保總量不超過系統能力。

## 演算法

### Token Bucket

桶裡有固定數量的 token，每個請求消耗一個 token，token 按固定速率補充。桶空了就拒絕。

特點：允許短暫 burst（桶滿時一次消耗多個 token），但長期平均不超過補充速率。適合「允許偶爾的高峰但長期平均要在限制內」的場景。

### Sliding Window

在固定的時間窗口（如 1 分鐘）內計數請求。超過上限就拒絕。窗口結束時計數重設。

特點：嚴格的速率限制（窗口內不會超過 N 個），但窗口邊界有突增風險（上一個窗口末尾 + 下一個窗口開頭各 N 個 = 瞬間 2N）。滑動窗口（sliding window log / counter）解決邊界問題但記憶體較高。

### 選擇

自架監控系統推薦 token bucket — 允許 SDK 的 flush burst（一次送 100 個事件是正常行為），但限制長期平均速率。

## HTTP 429 + Retry-After

限速觸發時回 HTTP 429 Too Many Requests，帶 `Retry-After` header 和 rate limit 相關 header：

```text
HTTP/1.1 429 Too Many Requests
Retry-After: 5
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1719302400
```

SDK 收到 429 後觸發離線 buffer 暫存事件，`Retry-After` 秒後重試。

## 優先級豁免

某些請求不應被限速：

| 請求類型     | 限速？     | 理由                               |
| ------------ | ---------- | ---------------------------------- |
| Health check | 不限       | 探活請求被限速等於 LB 誤判服務掛了 |
| Error 事件   | 不限或較寬 | Debug 價值最高、丟了就查不到       |
| Event 事件   | 限速       | 量大、行為分析可以接受取樣         |
| Metric 事件  | 限速       | 高頻取樣可以降頻                   |

優先級的判斷依據是「這個事件丟了的代價」。Error 事件丟了影響 debug 能力，event 事件丟了影響行為分析精度 — 前者的代價更高。

## 下一步路由

- 被動的流量控制 → [背壓機制](/devops/03-traffic-management/backpressure/)
- 依賴失敗時的快速失敗 → [熔斷器](/devops/03-traffic-management/circuit-breaker/)
- 不同工作負載的資源隔離 → [Bulkhead 隔離](/devops/03-traffic-management/bulkhead/)
