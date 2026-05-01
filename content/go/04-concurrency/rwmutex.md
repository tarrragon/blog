---
title: "4.4 sync.RWMutex：保護共享狀態"
date: 2026-04-22
description: "用讀寫鎖保護共享狀態"
weight: 4
---

`sync.RWMutex` 是 Go 用來保護共享狀態的讀寫鎖。它的核心用途是允許多個讀取者同時讀取，但寫入者必須獨占資料，避免 goroutine 同時讀寫 map、slice 或 struct 時產生資料競爭。

## 本章目標

學完本章後，你將能夠：

1. 理解 data race 的風險
2. 區分 `Mutex` 與 `RWMutex`
3. 用 `RLock` / `RUnlock` 保護讀取
4. 用 `Lock` / `Unlock` 保護寫入
5. 避免回傳內部 map 或 slice 破壞鎖邊界

---

## 【觀察】共享 map 不能被多個 goroutine 無保護地讀寫

共享狀態的核心規則是：只要多個 goroutine 可能同時讀寫同一份資料，就必須用同步機制保護。以下程式同時讀寫 map，存在 data race：

```go
type UserRepository struct {
    users map[string]User
}

func (r *UserRepository) Set(id string, user User) {
    r.users[id] = user
}

func (r *UserRepository) Get(id string) (User, bool) {
    user, ok := r.users[id]
    return user, ok
}
```

如果 `Set` 和 `Get` 從不同 goroutine 同時執行，map 可能被同時讀寫。Go 的 map 不保證這種情境安全。

## 【判讀】RWMutex 區分讀取與寫入

`RWMutex` 的核心規則是：讀取使用 `RLock`，寫入使用 `Lock`；多個讀取可並行，寫入會排他。

```go
type UserRepository struct {
    users map[string]User
    mu    sync.RWMutex
}

func (r *UserRepository) Set(id string, user User) {
    r.mu.Lock()
    defer r.mu.Unlock()
    r.users[id] = user
}

func (r *UserRepository) Get(id string) (User, bool) {
    r.mu.RLock()
    defer r.mu.RUnlock()
    user, ok := r.users[id]
    return user, ok
}
```

`Set` 修改 map，所以用 `Lock`。`Get` 只讀 map，所以用 `RLock`。

## 【策略】鎖保護的是資料不變式

鎖範圍的核心規則是：鎖要包住所有需要一致觀察或一致修改的資料。鎖的邊界應涵蓋完整不變式，慢速 I/O、網路呼叫與和共享資料無關的計算則應放在鎖外。

例如，這個更新同時修改兩個欄位，兩個欄位要在同一把鎖內更新：

```go
func (r *UserRepository) Add(user User) {
    r.mu.Lock()
    defer r.mu.Unlock()

    r.users[user.ID] = user
    r.count++
}
```

如果 `users` 和 `count` 分開鎖，讀者可能看到 map 已更新但 count 還沒更新的中間狀態。

## 【執行】回傳資料時要保留 copy boundary

鎖邊界的核心規則是：鎖只能保護鎖內操作；回傳內部 map 會讓呼叫者在鎖外修改資料，破壞 repository 對狀態的控制權。

不安全做法：

```go
func (r *UserRepository) Users() map[string]User {
    r.mu.RLock()
    defer r.mu.RUnlock()
    return r.users
}
```

安全做法是回傳複製：

```go
func (r *UserRepository) Users() map[string]User {
    r.mu.RLock()
    defer r.mu.RUnlock()

    result := make(map[string]User, len(r.users))
    for id, user := range r.users {
        result[id] = user
    }
    return result
}
```

呼叫者拿到的是複本，不能繞過 `UserRepository` 修改內部狀態。

## Mutex 還是 RWMutex？

選擇鎖的核心規則是：讀多寫少且讀操作可並行時用 `RWMutex`；不確定時先用 `Mutex`，設計更簡單。

| 鎖             | 適合情境                             |
| -------------- | ------------------------------------ |
| `sync.Mutex`   | 狀態小、讀寫都簡單、沒有明顯讀多寫少 |
| `sync.RWMutex` | 讀取頻繁、寫入較少、讀操作可安全並行 |

`sync.Mutex` 的核心優勢是簡單。若狀態很小、讀寫都很快，或讀寫比例尚未明確，先使用 `Mutex` 通常更容易維護。它讓每次存取都走同一條鎖路徑，讀者也比較容易確認資料何時被保護。

`sync.RWMutex` 的核心優勢是讀多寫少時可以讓多個讀取並行。它適合像 in-memory cache、狀態查詢 repository 或連線註冊表這類讀取頻繁的資料結構。使用它時，寫入仍然要用 `Lock`，因為 `RLock` 只適合保護純讀取。

鎖選擇的判斷重點是資料不變式與讀寫比例。若讀取本身會組裝複雜資料、需要複製大型 map，或很快就會呼叫外部 I/O，`RWMutex` 帶來的並行讀取收益可能被複雜度抵消。

## 替代方案：什麼時候不用 RWMutex

`RWMutex` 不是共享狀態保護的唯一選擇。三類替代方案各有適用條件：

| 方案                       | 適用情境                                                            | 跟 RWMutex 對比                                                                            |
| -------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `sync.Map`                 | key 集合大、entries 異步增減、讀寫分散在不同 key                    | 內建讀寫並行、無全域鎖；但語意不同（無 size、無 range 一致性）                             |
| `sync/atomic`              | 單一純量（counter、flag、pointer）                                  | 無鎖、最快；但只能保護單一值、不能保護結構不變式                                           |
| Channel-based coordination | 狀態由單一 owner goroutine 持有、其他 goroutine 透過 channel 傳訊息 | 用 ownership 取代 sharing；適合 producer / consumer pattern、見 [4.2 channel](../channel/) |

判別準則：

- 保護**多欄位不變式**（如 `users` + `count` 同步）→ `RWMutex` 或 `Mutex`
- 保護**單一純量**且操作可表達為 atomic op（CAS、increment）→ `sync/atomic`
- 保護**大量獨立 key** 且無跨 key 不變式 → `sync.Map`
- 狀態可由**單一 owner** 持有、外部用訊息驅動 → channel-based、見 [4.2](../channel/) / [4.5 backpressure](../backpressure/)

選錯方案的代價：用 `sync/atomic` 保護需要不變式的多欄位 → silent atomicity violation；用 `sync.Map` 期待 range 一致性 → 拿到 inconsistent snapshot；用 channel 處理需要嚴格 ordering 的 fan-in → 順序錯亂。

## RWMutex 不解的問題

`RWMutex` 解的是 **data race**（多 goroutine 同時讀寫同一份資料的 visible race）。下列問題**不在 `RWMutex` 防護範圍**、必須由其他機制處理：

| 不防的問題              | 為什麼不解                                                                      | 該用什麼                                                 |
| ----------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Deadlock                | 多把鎖的鎖順序不一致、`RWMutex` 沒有偵測能力                                    | 鎖排序協議、`go test -race` 並非 deadlock detector       |
| Starvation              | RWMutex 設計上 reader 多時 writer 可能長期等不到（Go 實作有部分 fairness 保護） | 量測 lock 等待時間、讀多時切 channel-based 或 sharded 鎖 |
| Lock contention scaling | goroutine 增多時、單把鎖的競爭成本可能 dominate；`RWMutex` 多核 scalability 弱  | sharded lock、sync.Map、無鎖結構                         |
| Context cancellation    | reader 已經 hold RLock 時、context 取消不會強制釋放；reader 必須主動 check ctx  | lock 內快進快出、長操作放鎖外、check ctx                 |
| Atomicity violation     | 把多步操作拆到多次 Lock/Unlock 中間、其他 goroutine 可能看到中間狀態            | 拉大鎖範圍、或改 transaction-like API                    |
| Memory ordering（跨鎖） | RWMutex 只保證鎖內 happens-before、跨鎖讀寫的 ordering 沒保證                   | 用 channel 傳遞 ordering、或 atomic load/store           |

判讀訊號：

- `go test -race` pass、production 仍偶發資料異常 → 可能 atomicity violation 或 ordering bug、不是 data race
- 多核 CPU 加倍但 throughput 不增 → lock contention dominate、考慮 shard
- p99 latency 在高 concurrency 下爆炸 → reader 排隊或 starvation、查 lock 等待 metric
- shutdown 時 goroutine 不退 → reader hold RLock + 未 check ctx、補 context 檢查

## Context dependence：scale 改變策略

`RWMutex` 的有效性會隨 deployment 條件變化：

- **Map 大小**：copy 成本隨 entries 線性增長、1k entries 廉價、1M entries 每次 copy 都是 GC pressure 來源；大 map 改 `sync.Map` 或 sharded
- **讀寫比例**：90% 讀以下、`RWMutex` 收益不顯著、`Mutex` 簡單；讀寫接近時 RWMutex 的內部 atomic 操作成本可能反而比 Mutex 慢
- **Goroutine 數量**：少（< 10）時 contention 微、多（> 1000）時 RWMutex 不適合、要 shard 或換 lock-free 結構
- **持鎖時間**：鎖內 microsecond 級 OK、毫秒級會堆隊；鎖內絕不做 I/O / 網路呼叫

## 小結

`sync.RWMutex` 用來保護多 goroutine 共享 **可變狀態的 data race**。讀取用 `RLock`，寫入用 `Lock`；鎖要保護完整資料不變式，回傳 map 或 slice 時要複製。

但 `RWMutex` 只解 data race subset——不解 deadlock / starvation / atomicity violation / context cancellation / 多核 contention scaling。狀態可表達為 atomic op、單 owner channel、或大量獨立 key 時、`sync/atomic` / channel-based / `sync.Map` 通常更合適。選擇前先問：「不變式跨幾個欄位？讀寫比例？goroutine 數量？持鎖時間？」
