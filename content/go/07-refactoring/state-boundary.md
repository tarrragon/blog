---
title: "7.4 狀態管理的安全邊界"
date: 2026-04-22
description: "用 lock、copy 與 API 限制保護共享狀態"
weight: 4
---

狀態管理重構的核心目標是集中寫入、保護 map、回傳複製資料，並避免讓 handler、背景工作或即時連線直接操作內部狀態。本章用一般 repository 範例說明如何建立安全邊界。

## 本章目標

學完本章後，你將能夠：

1. 辨識共享狀態外洩的程式碼壞味道
2. 用 repository 或 state owner 集中寫入
3. 用 `sync.RWMutex` 保護 map、slice 與狀態不變式
4. 用 copy boundary 防止呼叫端修改內部資料
5. 用行為測試與 `go test -race` 驗證並發狀態

---

## 【觀察】共享狀態外洩會讓規則分散

共享狀態外洩的核心問題是多個元件可以繞過同一套規則直接修改資料。當 handler、worker、[WebSocket](../../backend/knowledge-cards/websocket) client manager 都能改同一個 map，狀態不一致與 data race 會變得很難追蹤。

重構前常見寫法：

```go
type Server struct {
    jobs map[string]JobProjection
}

func (s *Server) handleJobStarted(w http.ResponseWriter, r *http.Request) {
    id := r.URL.Query().Get("id")
    s.jobs[id] = JobProjection{
        ID:        id,
        Status:    JobStatusRunning,
        UpdatedAt: time.Now(),
    }
    w.WriteHeader(http.StatusAccepted)
}

func (s *Server) handleJobList(w http.ResponseWriter, r *http.Request) {
    _ = json.NewEncoder(w).Encode(s.jobs)
}
```

這段程式有三個問題：handler 直接改 map，map 沒有 lock，查詢直接輸出內部資料。只要另一個 goroutine 同時讀寫 `jobs`，就可能產生 data race。

## 【判讀】state owner 是唯一寫入入口

state owner 的核心責任是擁有資料與狀態轉移規則。它可以叫 repository、store、manager；名稱不是重點，重點是所有寫入都經過同一組方法。

```go
type JobRepository struct {
    mu   sync.RWMutex
    jobs map[string]JobProjection
}

func NewJobRepository() *JobRepository {
    return &JobRepository{
        jobs: make(map[string]JobProjection),
    }
}
```

handler 不再直接改 map，而是呼叫 repository 方法：

```go
func (r *JobRepository) MarkRunning(id string, now time.Time) error {
    if strings.TrimSpace(id) == "" {
        return fmt.Errorf("job id is required")
    }

    r.mu.Lock()
    defer r.mu.Unlock()

    job := r.jobs[id]
    job.ID = id
    job.Status = JobStatusRunning
    job.UpdatedAt = now
    r.jobs[id] = job
    return nil
}
```

這個方法把「running 狀態怎麼寫入」集中起來。未來如果 running 只能從 pending 轉移，規則也加在這裡。

## 【策略】鎖保護的是不變式

lock 的核心責任是保護完整狀態不變式，不只是保護某一行 map assignment。若一次狀態轉移要同時更新 current、history、updated time，就要在同一把鎖內完成。

```go
type JobRecord struct {
    Current JobProjection
    History []JobProjection
}

type JobRepository struct {
    mu      sync.RWMutex
    records map[string]JobRecord
}
```

寫入時同時更新 summary 與 history：

```go
func (r *JobRepository) Apply(event JobEvent) error {
    r.mu.Lock()
    defer r.mu.Unlock()

    record := r.records[event.JobID]
    next := record.Current
    next.ID = event.JobID
    next.UpdatedAt = event.OccurredAt

    switch event.Type {
    case "job.started":
        next.Status = JobStatusRunning
    case "job.succeeded":
        next.Status = JobStatusSucceeded
        next.Progress = 100
    case "job.failed":
        next.Status = JobStatusFailed
    default:
        return fmt.Errorf("unsupported job event type %q", event.Type)
    }

    record.Current = next
    record.History = append(record.History, next)
    r.records[event.JobID] = record
    return nil
}
```

這段程式讓 current 與 history 保持一致。若分散在不同 handler 或不同鎖裡，就可能留下「current 已更新但 history 沒有記錄」的中間狀態。

## 【執行】讀取要回傳 copy

copy boundary 的核心目標是避免呼叫端拿到內部可變資料。鎖只保護鎖內操作；一旦把內部 slice 或 pointer 回傳出去，呼叫端就可以在鎖外修改資料。

單筆查詢：

```go
func (r *JobRepository) Get(id string) (JobProjection, bool) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    record, ok := r.records[id]
    if !ok {
        return JobProjection{}, false
    }
    return cloneJobProjection(record.Current), true
}
```

history 查詢：

```go
func (r *JobRepository) History(id string) []JobProjection {
    r.mu.RLock()
    defer r.mu.RUnlock()

    history := r.records[id].History
    result := make([]JobProjection, len(history))
    for i, item := range history {
        result[i] = cloneJobProjection(item)
    }
    return result
}
```

clone 函式處理 pointer 欄位：

```go
func cloneJobProjection(job JobProjection) JobProjection {
    cloned := job
    if job.FinishedAt != nil {
        finishedAt := *job.FinishedAt
        cloned.FinishedAt = &finishedAt
    }
    return cloned
}
```

如果 struct 未來新增 slice、map 或 pointer 欄位，clone 函式也要跟著更新。這是資料擁有權邊界的一部分。

## 【判讀】state 和 projection 要分清楚

state/[projection](../../backend/knowledge-cards/projection) 分離的核心原因是寫入規則與讀取需求不同。domain state 保存規則，projection 服務查詢與顯示。

```go
type JobState struct {
    ID        string
    Status    JobStatus
    UpdatedAt time.Time
}

type JobProjection struct {
    ID          string
    Status      JobStatus
    Progress    int
    UpdatedAt   time.Time
    DisplayText string
}
```

`DisplayText` 不應參與狀態轉移，它是 response 或 [read model](../../backend/knowledge-cards/read-model) 的資料。若把顯示文字混進核心 state，前端文案改動就會牽動業務規則測試。

重構時不一定要一次拆出兩個 struct。可以先在程式碼中標記哪些欄位是 state，哪些欄位是 projection；等壓力變大，再正式拆型別。

## 【策略】handler 只請求狀態更新

handler 的核心責任是把 HTTP request 轉成狀態更新請求，而不是自己修改狀態。

重構後：

```go
type JobStarter interface {
    MarkRunning(id string, now time.Time) error
}

type JobHandler struct {
    jobs JobStarter
    now  func() time.Time
}

func (h JobHandler) Start(w http.ResponseWriter, r *http.Request) {
    id := r.URL.Query().Get("id")
    if err := h.jobs.MarkRunning(id, h.now()); err != nil {
        http.Error(w, "start job", http.StatusBadRequest)
        return
    }
    w.WriteHeader(http.StatusAccepted)
}
```

handler 不知道 repository 內部用 map、slice、mutex 還是資料庫。它只知道「可以把 job 標記為 running」。

## 【策略】為未來資料庫保留邊界，但不提前綁死

[database](../../backend/knowledge-cards/database)-ready 邊界的核心是 context、error 與一致性語意，不是提早引入 ORM。memory repository 可以先存在，但方法簽名可以保留未來 I/O 的可能。

```go
type JobRepositoryPort interface {
    Apply(ctx context.Context, event JobEvent) error
    Get(ctx context.Context, id string) (JobProjection, bool, error)
}
```

memory implementation 可以忽略 context：

```go
func (r *JobRepository) Get(ctx context.Context, id string) (JobProjection, bool, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    record, ok := r.records[id]
    if !ok {
        return JobProjection{}, false, nil
    }
    return cloneJobProjection(record.Current), true, nil
}
```

未來換成資料庫時，context 可以傳給 query；error 可以包上資料庫錯誤。[transaction](../../backend/knowledge-cards/transaction) 則等到一個 usecase 真的需要多筆寫入一致性時再設計。

## 【執行】state transition 測試鎖定規則

state transition 測試的核心目標是確認事件會產生正確狀態與 history。這類測試不需要 HTTP，也不需要 goroutine。

```go
func TestJobRepositoryApplyRecordsHistory(t *testing.T) {
    repo := &JobRepository{records: make(map[string]JobRecord)}
    startedAt := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)

    err := repo.Apply(JobEvent{
        JobID:      "job_1",
        Type:       "job.started",
        OccurredAt: startedAt,
    })
    if err != nil {
        t.Fatalf("apply event: %v", err)
    }

    job, ok := repo.Get("job_1")
    if !ok {
        t.Fatalf("job should exist")
    }
    if job.Status != JobStatusRunning {
        t.Fatalf("status = %q, want %q", job.Status, JobStatusRunning)
    }

    history := repo.History("job_1")
    if len(history) != 1 {
        t.Fatalf("history length = %d, want 1", len(history))
    }
}
```

這個測試鎖定的是狀態規則，而不是鎖本身。

## 【執行】copy boundary 測試要嘗試破壞資料

copy boundary 測試的核心目標是證明呼叫端拿到的資料不能修改 repository 內部狀態。

```go
func TestJobRepositoryHistoryReturnsCopy(t *testing.T) {
    repo := &JobRepository{records: make(map[string]JobRecord)}
    occurredAt := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)

    _ = repo.Apply(JobEvent{
        JobID:      "job_1",
        Type:       "job.started",
        OccurredAt: occurredAt,
    })

    history := repo.History("job_1")
    history[0].Status = JobStatusFailed

    again := repo.History("job_1")
    if again[0].Status != JobStatusRunning {
        t.Fatalf("repository history was modified through returned slice")
    }
}
```

這種測試比只看程式碼更可靠。它直接模擬呼叫端拿到資料後做了危險操作。

## 【執行】並發測試配合 race detector

並發測試的核心目標是讓 race detector 執行到共享狀態路徑。測試本身可以只檢查不 panic 或基本結果，真正的 data race 由 `go test -race` 回報。

```go
func TestJobRepositoryConcurrentAccess(t *testing.T) {
    repo := &JobRepository{records: make(map[string]JobRecord)}
    var wg sync.WaitGroup

    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func(i int) {
            defer wg.Done()

            id := fmt.Sprintf("job_%d", i%10)
            _ = repo.Apply(JobEvent{
                JobID:      id,
                Type:       "job.started",
                OccurredAt: time.Date(2026, 4, 22, 10, 0, i, 0, time.UTC),
            })
            _, _ = repo.Get(id)
            _ = repo.History(id)
        }(i)
    }

    wg.Wait()
}
```

執行：

```bash
go test -race ./...
```

race detector 只能檢查測試實際跑到的路徑。若並發讀寫沒有被測試覆蓋，它也不會發現問題。

## 重構步驟

從共享狀態外洩重構到安全邊界，可以按這個順序：

1. 找出所有直接讀寫 map、slice 或 projection 的地方。
2. 建立 state owner 或 repository。
3. 把最常用的寫入流程搬成方法。
4. 在方法內加入 lock，保護完整不變式。
5. 把讀取方法改成回傳 copy。
6. 讓 handler、worker、publisher 改呼叫方法，不直接碰資料。
7. 補 state transition 與 copy boundary 測試。
8. 補並發測試並執行 `go test -race ./...`。

不要一開始就重寫所有狀態模型。先把寫入集中，再逐步整理 state/projection 與資料庫邊界。

## 設計檢查

### 檢查一：加鎖後仍要保護回傳資料

鎖只保護鎖內操作。回傳內部 map 或 slice 後，呼叫端可以在鎖外修改資料，狀態邊界仍然失效。

### 檢查二：讀取鎖只保護讀取

`RLock` 只適合讀取。只要會修改 map、slice、pointer 指向的值或 struct 欄位，就必須使用 `Lock`。

### 檢查三：狀態副本需要明確 owner

多份狀態副本會造成 [source of truth](../../backend/knowledge-cards/source-of-truth) 混亂。handler 應該請求同一個 state owner 更新或查詢。

### 檢查四：持久化替換跟著需求前進

狀態邊界是程式碼架構的責任；資料庫只負責持久化。把 memory repository 換成 ORM 只解決「資料存在哪裡」，沒有解決「誰有權利寫、怎麼寫才一致」。

引入資料庫後，清楚的寫入方法、交易語意、copy/DTO 邊界與測試仍要留在程式碼設計中。這些規則決定狀態如何被修改，不能交給資料庫連線本身代勞。

## 本章不處理

本章先處理 state owner、lock boundary 與 copy boundary；資料庫 transaction 與分散式一致性，會在下列章節再往外延伸：

- [Go 進階：資料庫 transaction 與 schema migration](../../go-advanced/07-distributed-operations/database-transactions/)
- [Go 進階：Source of Truth：狀態邊界](../../go-advanced/04-architecture-boundaries/source-of-truth/)
- [Backend：資料庫與持久化](../../backend/01-database/)

## 和 Go 教材的關係

這一章承接的是 repository、read model 與 shared state 的邊界；如果你要先回看語言教材，可以讀：

- [Go：如何新增 repository port](../../go/06-practical/repository-port/)
- [Go：如何擴展狀態投影欄位](../../go/06-practical/state-fields/)
- [Go：用 interface 隔離外部依賴](interface-boundary/)
- [Go：以 domain 重新整理 package](domain-packages/)

## 小結

狀態管理重構的重點是建立資料擁有者。寫入集中在 repository 或 state owner，lock 保護完整不變式，讀取回傳 copy，handler 和 worker 只請求狀態更新。當狀態邊界清楚時，race detector 才有意義，未來換成資料庫也只是 adapter 變化，不會改變核心狀態規則。
