---
title: "6.3 如何擴展狀態投影欄位"
date: 2026-04-22
description: "更新狀態模型、repository 與 API 輸出"
weight: 3
---

擴展狀態投影欄位的核心流程是先確認欄位屬於 domain state、[read model](../../../backend/knowledge-cards/read-model/) 還是 response view。欄位加在哪一層，會決定寫入規則、相容性與測試方式。

## 本章目標

學完本章後，你將能夠：

1. 分辨 domain state、read model 與 response view
2. 判斷新欄位的零值是否有語意
3. 把狀態轉移集中在 repository 或 state owner
4. 用 copy boundary 保護內部 slice/map
5. 測試 state transition、repository copy 與 JSON response

---

## 【觀察】先判斷欄位屬於哪一層

狀態欄位的核心問題是「這個欄位代表哪一種資料責任」。同一個欄位放在不同層，代表不同寫入規則與相容性承諾。

| 層次                                                                  | 意義                     | 範例                                |
| --------------------------------------------------------------------- | ------------------------ | ----------------------------------- |
| domain state                                                          | 影響業務規則與狀態轉移   | job 是否 running、failed、completed |
| [projection](../../../backend/knowledge-cards/projection/)/read model | 方便查詢、列表或即時顯示 | 最近更新時間、目前進度百分比        |
| response view                                                         | 只影響對外輸出格式       | 顯示文字、前端用 badge 顏色         |

例如「job 狀態」是 domain state，因為它會影響是否能重試、取消或完成。相反地，「狀態顯示文字」通常是 response view，因為它只是把內部狀態轉成 client 更容易顯示的文字。

本章使用一個簡化的 job 狀態投影作為範例。事件進入系統後，repository 會把事件套用成目前 projection，再由 response layer 輸出給 client。

## 【判讀】domain state 要用明確型別

domain state 的核心規則是用型別表達可用狀態，而不是讓任意字串在系統裡流動。當欄位會影響規則時，應該優先考慮 typed constant。

```go
type JobStatus string

const (
    JobStatusPending   JobStatus = "pending"
    JobStatusRunning   JobStatus = "running"
    JobStatusSucceeded JobStatus = "succeeded"
    JobStatusFailed    JobStatus = "failed"
)
```

接著定義狀態投影：

```go
type JobProjection struct {
    ID         string
    Status     JobStatus
    Progress   int
    UpdatedAt  time.Time
    FinishedAt time.Time
}
```

`Status` 是 domain state。`Progress` 可以是 read model 欄位，代表目前顯示用進度。`FinishedAt` 需要進一步判斷：如果完成時間會影響重試、保留時間或排序，它就不只是 response 欄位。

零值也要有語意。`FinishedAt` 的零值可以代表「尚未完成」，但這個語意必須被程式明確處理；若零值會造成混淆，可以改用 pointer：

```go
type JobProjection struct {
    ID         string
    Status     JobStatus
    Progress   int
    UpdatedAt  time.Time
    FinishedAt *time.Time
}
```

pointer 在這裡的用途是區分「沒有值」和「有一個零值」。時間、數字與 bool 欄位最常遇到這個問題。

## 【策略】狀態轉移要集中在同一個入口

狀態轉移的核心規則是所有寫入都經過同一組方法。handler、worker 或 [WebSocket](../../../backend/knowledge-cards/websocket/) router 應把狀態變更交給 repository 或 state owner，而不是自行修改 map 或 projection 欄位。

先定義內部 event：

```go
type JobEvent struct {
    JobID      string
    Type       string
    Progress   int
    OccurredAt time.Time
}
```

repository 可以集中套用事件：

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

`Apply` 是狀態寫入入口：

```go
func (r *JobRepository) Apply(event JobEvent) error {
    r.mu.Lock()
    defer r.mu.Unlock()

    job := r.jobs[event.JobID]
    job.ID = event.JobID
    job.UpdatedAt = event.OccurredAt

    switch event.Type {
    case "job.started":
        job.Status = JobStatusRunning
        job.Progress = 0
    case "job.progressed":
        job.Progress = event.Progress
    case "job.succeeded":
        job.Status = JobStatusSucceeded
        job.Progress = 100
        finishedAt := event.OccurredAt
        job.FinishedAt = &finishedAt
    case "job.failed":
        job.Status = JobStatusFailed
        finishedAt := event.OccurredAt
        job.FinishedAt = &finishedAt
    default:
        return fmt.Errorf("unsupported job event type %q", event.Type)
    }

    r.jobs[event.JobID] = job
    return nil
}
```

這段程式讓狀態轉移規則集中在 repository。未來如果要禁止 failed job 重新變成 running，或要求 progress 不可倒退，可以在同一個入口加規則與測試。

## 【判讀】read model 可以為查詢服務

read model 的核心用途是讓查詢與顯示更直接。它不一定等同完整 domain state，而是為某種讀取需求整理出的投影。

例如列表頁可能只需要 summary：

```go
type JobSummary struct {
    ID        string
    Status    JobStatus
    Progress  int
    UpdatedAt time.Time
}
```

repository 可以提供查詢方法：

```go
func (r *JobRepository) ListSummaries() []JobSummary {
    r.mu.RLock()
    defer r.mu.RUnlock()

    result := make([]JobSummary, 0, len(r.jobs))
    for _, job := range r.jobs {
        result = append(result, JobSummary{
            ID:        job.ID,
            Status:    job.Status,
            Progress:  job.Progress,
            UpdatedAt: job.UpdatedAt,
        })
    }
    return result
}
```

這個方法回傳新 slice，而不是暴露 repository 內部資料。若 read model 包含 slice、map 或 pointer，也要確認呼叫端不能修改內部狀態。

## 【執行】讀取方法要保護 copy boundary

copy boundary 的核心目標是避免外部呼叫者修改 repository 內部資料。Go 的 slice、map、pointer 都可能讓內部狀態外洩。

單筆查詢可以回傳值與 bool：

```go
func (r *JobRepository) Get(id string) (JobProjection, bool) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    job, ok := r.jobs[id]
    if !ok {
        return JobProjection{}, false
    }
    return cloneJobProjection(job), true
}
```

若 struct 內含 pointer，clone 函式要複製 pointer 指向的值：

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

這個 clone 看似瑣碎，但它保護了 repository 的擁有權。呼叫端拿到資料後，即使修改 `FinishedAt` 指向的時間，也不會影響 repository 內部狀態。

## 【策略】response view 負責對外格式

response view 的核心責任是把內部狀態轉成外部 contract。JSON tag、`omitempty`、顯示文字與相容性都應該在 response struct 中處理，讓 domain model 保持在業務狀態語意上。

```go
type JobResponse struct {
    ID          string     `json:"id"`
    Status      JobStatus  `json:"status"`
    Progress    int        `json:"progress"`
    UpdatedAt   time.Time  `json:"updatedAt"`
    FinishedAt  *time.Time `json:"finishedAt,omitempty"`
    DisplayText string     `json:"displayText,omitempty"`
}
```

轉換函式可以集中 response 規則：

```go
func NewJobResponse(job JobProjection) JobResponse {
    return JobResponse{
        ID:          job.ID,
        Status:      job.Status,
        Progress:    job.Progress,
        UpdatedAt:   job.UpdatedAt,
        FinishedAt:  job.FinishedAt,
        DisplayText: displayText(job.Status),
    }
}

func displayText(status JobStatus) string {
    switch status {
    case JobStatusPending:
        return "Waiting"
    case JobStatusRunning:
        return "Running"
    case JobStatusSucceeded:
        return "Completed"
    case JobStatusFailed:
        return "Failed"
    default:
        return "Unknown"
    }
}
```

`DisplayText` 是 response view，負責呈現用文字。若未來前端改文案，response 轉換函式可以調整，repository 狀態轉移規則應保持穩定。

## 【判讀】`omitempty` 是相容性語意

`omitempty` 的核心語意是欄位在某些情境中可以不存在。它在對外 contract 中表示「這個欄位可能不存在」，而不是只為了縮短 JSON。

例如 `FinishedAt` 只有 job 完成或失敗後才有值：

```go
FinishedAt *time.Time `json:"finishedAt,omitempty"`
```

舊 client 如果不知道 `finishedAt`，通常會忽略新欄位。新 client 如果需要這個欄位，也必須處理它不存在的情況。

必填欄位的 JSON contract 應保持穩定輸出。`id` 或 `status` 這類欄位消失會讓 client 無法理解資料，因此它們屬於必要欄位，應維持固定輸出。

## 【執行】state transition 測試要鎖定規則

state transition 測試的核心目標是確認事件會產生正確狀態。這類測試不需要 HTTP，也不需要 WebSocket。

```go
func TestJobRepositoryApplySucceeded(t *testing.T) {
    repo := NewJobRepository()
    finishedAt := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)

    err := repo.Apply(JobEvent{
        JobID:      "job_1",
        Type:       "job.succeeded",
        OccurredAt: finishedAt,
    })
    if err != nil {
        t.Fatalf("apply event: %v", err)
    }

    job, ok := repo.Get("job_1")
    if !ok {
        t.Fatalf("job should exist")
    }
    if job.Status != JobStatusSucceeded {
        t.Fatalf("status = %q, want %q", job.Status, JobStatusSucceeded)
    }
    if job.Progress != 100 {
        t.Fatalf("progress = %d, want 100", job.Progress)
    }
    if job.FinishedAt == nil || !job.FinishedAt.Equal(finishedAt) {
        t.Fatalf("finished at = %v, want %v", job.FinishedAt, finishedAt)
    }
}
```

這個測試保護的是狀態規則，而不是輸出 JSON 格式。

## 【執行】copy boundary 測試要嘗試修改回傳值

copy boundary 測試的核心目標是證明呼叫端不能透過回傳資料改到 repository 內部狀態。

```go
func TestJobRepositoryGetReturnsCopy(t *testing.T) {
    repo := NewJobRepository()
    finishedAt := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)

    _ = repo.Apply(JobEvent{
        JobID:      "job_1",
        Type:       "job.succeeded",
        OccurredAt: finishedAt,
    })

    job, ok := repo.Get("job_1")
    if !ok {
        t.Fatalf("job should exist")
    }

    changed := finishedAt.Add(time.Hour)
    job.FinishedAt = &changed

    again, _ := repo.Get("job_1")
    if again.FinishedAt == nil || !again.FinishedAt.Equal(finishedAt) {
        t.Fatalf("repository state was modified through returned value")
    }
}
```

這種測試對 map、slice、pointer 特別重要。值型別欄位通常不需要額外 clone，但一旦 struct 包含可變參照，就要測邊界。

## 【執行】response JSON 測試要檢查 contract

response 測試的核心目標是確認對外 JSON 欄位符合 contract。測試應該解析 JSON 或檢查欄位存在性，而不是只比對整段字串。

```go
func TestJobResponseOmitsFinishedAtWhenNil(t *testing.T) {
    response := NewJobResponse(JobProjection{
        ID:        "job_1",
        Status:    JobStatusRunning,
        Progress:  40,
        UpdatedAt: time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC),
    })

    data, err := json.Marshal(response)
    if err != nil {
        t.Fatalf("marshal response: %v", err)
    }

    var body map[string]any
    if err := json.Unmarshal(data, &body); err != nil {
        t.Fatalf("unmarshal response: %v", err)
    }

    if _, ok := body["finishedAt"]; ok {
        t.Fatalf("finishedAt should be omitted when nil")
    }
}
```

這個測試不是測 `encoding/json` 本身，而是測你對外承諾的欄位語意。

## 實作檢查清單

擴展狀態投影欄位時，可以依序檢查：

1. 欄位屬於 domain state、read model 還是 response view
2. 零值是否有明確語意
3. 是否需要 typed constant
4. 寫入是否集中在 repository 或 state owner
5. handler、router、worker 是否沒有直接修改內部 map/slice
6. 查詢是否回傳 copy
7. response 是否使用正確 JSON tag
8. `omitempty` 是否真的代表可選欄位
9. 測試是否分成 state transition、copy boundary、response JSON

## 設計檢查

### 檢查一：顯示欄位放在 response view

顯示文字、顏色或前端 badge 通常是 response view。只有影響業務規則的欄位，才需要進入 domain state。

### 檢查二：handler 透過狀態入口修改 projection

handler 透過 repository 或 state owner 修改 projection，可以讓狀態規則集中。handler 直接改 projection 時，新增第二個入口容易漏掉同一套規則。

### 檢查三：回傳資料保護 copy boundary

只要呼叫端能修改 repository 內部資料，狀態邊界就失效。回傳值時要檢查是否需要 clone。

### 檢查四：`omitempty` 對應可選欄位

必填欄位加上 `omitempty` 會讓 response contract 變模糊。欄位是否可省略，應由資料語意決定，而不是由欄位零值方便性決定。

## 本章不處理

本章先處理狀態欄位如何影響 response contract；資料庫 [migration](../../../backend/knowledge-cards/migration/) 與前端相容性策略，會在下列章節再往外延伸：

- [Go 進階：Source of Truth：狀態邊界](../../../backend/knowledge-cards/source-of-truth/)
- [Go 進階：資料庫 transaction 與 schema migration](../../../go-advanced/07-distributed-operations/database-transactions/)
- [Backend：資料庫與持久化](../../../backend/01-database/)

## 和 Go 教材的關係

這一章承接的是 repository、event 與 response view 的邊界；如果你要先回看語言教材，可以讀：

- [Go：如何新增 repository port](../repository-port/)
- [Go：如何新增一種 domain event](../new-event-type/)
- [Go：狀態管理的安全邊界](../../07-refactoring/state-boundary/)
- [Go 進階：Source of Truth](../../../backend/knowledge-cards/source-of-truth/)

## 小結

擴展狀態投影欄位時，先判斷資料責任，再決定它應該放在 domain state、read model 還是 response view。狀態轉移要集中，查詢要保護 copy boundary，response 要表達穩定 JSON contract。欄位新增看似只是改 struct，但真正需要保護的是寫入規則、相容性與測試邊界。
