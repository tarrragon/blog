---
title: "Rate Limit 實作"
date: 2026-06-20
description: "單機 middleware / Redis 分散式限速 / 配額設計 — 概念見 DevOps 流量管控，本章聚焦後端實作"
weight: 11
tags: ["backend", "performance", "rate-limit", "middleware", "redis"]
---

[Rate limit](/backend/knowledge-cards/rate-limit/) 的實作分成三個層次：單機 middleware（一個 server instance 內的限速）、分散式限速（多個 instance 共用的限速狀態）、配額設計（不同 client 和 endpoint 的差異化配額）。Rate limit 的概念基礎（token bucket / sliding window / 和背壓的區別）見 [DevOps 流量管控](/devops/03-traffic-management/rate-limiting/)，本章聚焦後端的程式碼實作。

## 單機 Middleware 實作

Rate limit middleware 在 HTTP handler 之前攔截請求。每個 request 過一次 limiter，通過就進入 handler，超限就回 429。

### Go 實作

Go 標準生態的 `golang.org/x/time/rate` 提供 token bucket 的 `rate.Limiter`。

```go
import "golang.org/x/time/rate"

// 全域 limiter：每秒 100 個 request、burst 上限 200
var globalLimiter = rate.NewLimiter(100, 200)

func rateLimitMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if !globalLimiter.Allow() {
            w.Header().Set("Retry-After", "1")
            http.Error(w, "Too Many Requests", http.StatusTooManyRequests)
            return
        }
        next.ServeHTTP(w, r)
    })
}
```

### Per-client 限速

全域 limiter 對所有 client 共用一個配額。Per-client 限速讓每個 client（by API key、IP、或 tenant ID）有各自的配額。

```go
var clients sync.Map // map[string]*rate.Limiter

func getClientLimiter(clientID string) *rate.Limiter {
    if limiter, ok := clients.Load(clientID); ok {
        return limiter.(*rate.Limiter)
    }
    limiter := rate.NewLimiter(10, 20) // 每 client 每秒 10 個
    clients.Store(clientID, limiter)
    return limiter
}
```

Per-client limiter 用 `sync.Map` 存、首次出現的 client 自動建立 limiter。長期運行的服務需要定期清理不再活躍的 client limiter（用 goroutine + ticker 掃描最後使用時間）。

### 回應格式

超限時的 HTTP response 需要帶足夠資訊讓 client 做正確的重試決策。

```text
HTTP/1.1 429 Too Many Requests
Retry-After: 1
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1719014400
```

`Retry-After` 告訴 client 等多久再試（秒數或 HTTP date）。`X-RateLimit-*` headers 不是 RFC 標準但被廣泛使用（GitHub API、Stripe API 都用），讓 client 在被限速前就知道剩餘配額。

## 分散式限速（Redis-backed）

單機 limiter 的計數存在 process 記憶體中。多個 server instance 各自有獨立的 limiter，client 的請求被 load balancer 分配到不同 instance 時，每個 instance 只看到部分請求 — 全域限速失效。

Redis 做共用的計數儲存，所有 instance 查同一個 counter。

### Sliding Window Counter

用 Redis 的 INCR + EXPIRE 實作 sliding window counter。

```lua
-- Redis Lua script（原子操作）
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end

if current > limit then
    return 0  -- 超限
end
return 1      -- 通過
```

Key 的設計：`ratelimit:{client_id}:{endpoint}:{window_start}`。Window start 用當前時間截斷到秒或分鐘（如 `1719014400`），每個窗口一個 key，EXPIRE 自動清理過期窗口。

### 現成套件

自己寫 Lua script 適合學習，production 用現成套件更可靠：

| 語言   | 套件                                      | 特點                                                         |
| ------ | ----------------------------------------- | ------------------------------------------------------------ |
| Go     | `go-redis/redis_rate`                     | Token bucket 演算法、原子操作、直接整合 go-redis             |
| Node   | `rate-limit-redis` + `express-rate-limit` | Express middleware、Redis store 外掛                         |
| Python | `limits` + Redis backend                  | 多演算法支援（fixed window / sliding window / token bucket） |

## 配額設計

### 差異化配額

不同的 endpoint 和 client 有不同的配額需求。搜尋 API 比列表 API 消耗更多計算資源，應該有更低的速率上限。

| 維度         | 配額範例                             | 理由                   |
| ------------ | ------------------------------------ | ---------------------- |
| Per-API key  | 1000 req/min                         | 每個 client 的公平上限 |
| Per-endpoint | 搜尋 100 req/min、列表 500 req/min   | 搜尋比列表貴           |
| Per-tenant   | 免費 100 req/min、付費 10000 req/min | 商業差異化             |

### 配額溢出的處理

超限時的處理策略依業務需求決定：

**Reject（429）**：直接拒絕。最簡單，適合 API 服務。Client 收到 429 後按 Retry-After 重試。

**Queue（排隊等）**：超限的請求進入等待隊列，按順序處理。適合不能丟棄的操作（付款確認、訂單建立）。代價是 client 端等待時間增加。

**Degrade（降級回應）**：超限時回傳簡化版的回應（cached 結果、摘要而非完整資料）。適合讀取操作。

## 和 Monitoring 的整合

Rate limit 的命中事件應該記入監控系統，讓團隊知道哪些 client 在撞限速、哪些 endpoint 的配額是否合理。

```go
// Rate limit hit 時送 metric 事件
monitor.Metric("ratelimit.hit", map[string]any{
    "client_id": clientID,
    "endpoint":  r.URL.Path,
    "limit":     100,
    "window":    "1m",
})
```

Dashboard 視圖：rate limit hit 的時間趨勢 + 按 client 和 endpoint 分群。Hit 數持續上升代表配額設太低（正常使用被限速）或某個 client 在濫用。

## 下一步路由

- Rate limit 的概念基礎 → [DevOps 流量管控 — Rate Limiting](/devops/03-traffic-management/rate-limiting/)
- 背壓機制（被動的流量控制）→ [DevOps 背壓機制](/devops/03-traffic-management/backpressure/)
- Rate limit 知識卡 → [Rate Limit](/backend/knowledge-cards/rate-limit/)
- 監控系統中的 ingestion 限速 → [Monitoring Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/)
