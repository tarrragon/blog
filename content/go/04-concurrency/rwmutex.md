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

## 小結

`sync.RWMutex` 用來保護多 goroutine 共享狀態。讀取用 `RLock`，寫入用 `Lock`；鎖要保護完整資料不變式，回傳 map 或 slice 時要複製，避免呼叫者在鎖外修改內部資料。
