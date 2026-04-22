---
title: "7.5 以 domain 重新整理 package"
date: 2026-04-22
description: "讓 account、job、event、workflow 這類領域邊界在目錄中可見"
weight: 5
---

# 以 domain 重新整理 package

以 domain 重新整理 package 的核心目標是讓程式結構反映業務語意，而不是只反映技術元件。當系統開始有 account、job、event、workflow 這些不同概念時，平面檔案會讓邊界越來越難看見。

Go package 是語意邊界，不只是檔案分類。好的 package 名稱應該讓讀者知道這裡負責哪一組概念；如果只能命名成 `utils`、`common` 或 `helpers`，通常代表邊界還沒有想清楚。

這一章承接入門篇的「單檔到多檔案」路線。平面多檔案不是錯誤，而是 Go 程式自然長大的中間階段；只有當檔案切分已經無法表達業務邊界時，才需要把概念搬成更清楚的 domain package。

## 本章目標

學完本章後，你將能夠：

1. 判斷何時該從平面多檔案拆出 package
2. 用業務語意命名 package
3. 依照純型別、純規則、usecase/repository 的順序搬移
4. 避免 import cycle
5. 用 type alias 與測試降低搬移風險

---

## 【觀察】平面多檔案是成長階段，不是錯誤

平面 package 的核心價值是初期簡單。服務還小時，`main.go`、`models.go`、`handlers.go`、`repository.go` 放在同一層，常常比一開始切十幾個資料夾更容易理解。

常見中間階段：

```text
notify/
├── go.mod
├── main.go
├── models.go
├── handlers.go
├── repository.go
├── events.go
└── worker.go
```

這個結構不是問題本身。真正的問題通常出現在概念開始混在一起：HTTP request struct、domain state、event type、repository model 都放在 `models.go`；handler、worker、processor 都直接引用同一批可變資料。

## 【判讀】拆 package 的訊號是語意邊界變模糊

拆 package 的核心判斷是讀者是否能從結構看出概念邊界。若只是檔案變多，先拆檔案即可；若業務概念混在一起，才需要拆 package。

適合拆 package 的訊號：

- `models.go` 同時包含 request DTO、domain state、response view。
- 新增功能時不知道型別該放哪個檔案。
- event、job、account 規則互相 import 或互相修改。
- 測試一個 domain 規則必須初始化 handler 或 server。
- package 內 unexported helper 太多，讀者很難判斷哪些屬於哪個概念。

不一定要拆 package 的情境：

- 檔案只是稍長，但仍圍繞同一個概念。
- 只有單一 main package 的小工具。
- 邊界還不穩，拆完很可能馬上搬回來。
- 只是為了符合某個目錄模板。

## 【策略】package 名稱要表達業務概念

domain package 的核心要求是名稱要讓讀者知道這裡負責哪組概念。`job`、`event`、`account`、`workflow` 比 `common`、`types`、`utils` 更有語意。

一個可能的拆分：

```text
notify/
├── go.mod
├── main.go
├── domain/
│   ├── account/
│   ├── job/
│   ├── event/
│   └── workflow/
├── transport/
│   └── http/
└── storage/
    └── memory/
```

這不是固定模板，而是示範語意方向。小型服務也可以先只拆：

```text
notify/
├── main.go
├── notification/
└── httpapi/
```

Go package 不需要層數多才算成熟。好的 package 是讓 import 讀起來自然：

```go
import "example.com/notify/domain/job"
```

如果 package 名稱只能叫 `misc` 或 `helpers`，代表邊界還沒有清楚。

## 【執行】先搬純型別

搬移 package 的核心順序是先搬依賴最少的東西。純型別通常最安全，因為它不呼叫外部元件。

重構前：

```go
// models.go
package main

type JobStatus string

const (
    JobStatusPending   JobStatus = "pending"
    JobStatusRunning   JobStatus = "running"
    JobStatusSucceeded JobStatus = "succeeded"
    JobStatusFailed    JobStatus = "failed"
)

type JobProjection struct {
    ID        string
    Status    JobStatus
    UpdatedAt time.Time
}
```

重構後：

```go
// domain/job/job.go
package job

import "time"

type Status string

const (
    StatusPending   Status = "pending"
    StatusRunning   Status = "running"
    StatusSucceeded Status = "succeeded"
    StatusFailed    Status = "failed"
)

type Projection struct {
    ID        string
    Status    Status
    UpdatedAt time.Time
}
```

使用端改成：

```go
import "example.com/notify/domain/job"

var projection job.Projection
```

package 名稱已經提供語境，所以型別不必再叫 `JobProjection`。在 `job` package 裡叫 `Projection` 就夠清楚。

## 【策略】用 type alias 過渡

type alias 的核心用途是降低搬移風險。若一次改完所有 import 太大，可以先在舊位置保留 alias，讓既有程式逐步遷移。

```go
// models.go
package main

import "example.com/notify/domain/job"

type JobStatus = job.Status
type JobProjection = job.Projection

const (
    JobStatusPending   = job.StatusPending
    JobStatusRunning   = job.StatusRunning
    JobStatusSucceeded = job.StatusSucceeded
    JobStatusFailed    = job.StatusFailed
)
```

這不是永久設計，而是過渡工具。等呼叫端逐步改成直接 import `domain/job`，再移除 alias。

type alias 適合降低大型搬移風險，但不要讓新舊命名長期並存，否則讀者會不知道哪個才是正式 API。

## 【執行】再搬純規則

純規則的核心特徵是輸入值、回傳值，不依賴 handler、repository 或外部 I/O。這類函式也適合早期搬入 domain package。

```go
// domain/job/transition.go
package job

import "fmt"

func CanTransition(from Status, to Status) bool {
    switch from {
    case StatusPending:
        return to == StatusRunning || to == StatusFailed
    case StatusRunning:
        return to == StatusSucceeded || to == StatusFailed
    default:
        return false
    }
}

func Transition(current Projection, next Status) (Projection, error) {
    if !CanTransition(current.Status, next) {
        return Projection{}, fmt.Errorf("invalid job status transition: %s -> %s", current.Status, next)
    }
    current.Status = next
    return current, nil
}
```

這些規則不應 import HTTP package，也不應知道 repository。它們是 domain 的穩定核心。

## 【判讀】domain 不依賴 adapter

避免 import cycle 的核心規則是低層 domain 不依賴高層 adapter。domain 可以被 HTTP、worker、repository 使用；但 domain 不應 import 這些外部層。

不良方向：

```text
domain/job -> transport/http -> domain/job
```

良好方向：

```text
transport/http -> application -> domain/job
storage/memory -> domain/job
```

如果 `domain/job` 需要知道 HTTP request struct，代表 request DTO 沒有停在 transport layer。應把 HTTP request 轉成 command 或 domain value，再交給下層。

## 【執行】最後搬 repository/usecase

repository 和 usecase 的核心特徵是它們開始協調多個概念，所以搬移時要更謹慎。通常先搬 domain 型別與規則，再處理 application layer。

可能的結構：

```text
notify/
├── domain/
│   ├── job/
│   └── event/
├── application/
│   ├── command.go
│   └── processor.go
├── transport/
│   └── http/
└── storage/
    └── memory/
```

application 可以協調 domain：

```go
package application

import (
    "context"

    "example.com/notify/domain/event"
    "example.com/notify/domain/job"
)

type JobRepository interface {
    Apply(ctx context.Context, projection job.Projection) error
}

type Processor struct {
    jobs JobRepository
}

func (p *Processor) Process(ctx context.Context, e event.Event) error {
    projection := job.Projection{
        ID:     e.SubjectID,
        Status: job.StatusRunning,
    }
    return p.jobs.Apply(ctx, projection)
}
```

application 可以依賴多個 domain package，因為它負責協調 usecase。domain package 之間若互相依賴太多，通常代表邊界切得不對。

## 【策略】每次只搬一個邊界

package 重構的核心風險是 import 修改範圍太大。每次只搬一個語意邊界，測試通過後再搬下一個。

建議順序：

1. 搬 `domain/job` 純型別。
2. 搬 `domain/job` 純規則。
3. 修正使用端 import。
4. 搬 `domain/event` 純型別。
5. 搬 event validation/normalize helper。
6. 搬 application processor。
7. 搬 adapter implementation。

不要同時搬 job、event、repository、handler。一次搬太多會讓失敗原因難以定位。

## 【執行】測試保護搬移

package 搬移的核心驗證是行為不變。搬檔案本身不是功能變更，所以測試應該確認原本行為仍然存在。

domain 規則測試：

```go
func TestJobCanTransition(t *testing.T) {
    if !job.CanTransition(job.StatusPending, job.StatusRunning) {
        t.Fatalf("pending should transition to running")
    }
    if job.CanTransition(job.StatusSucceeded, job.StatusRunning) {
        t.Fatalf("succeeded should not transition to running")
    }
}
```

application 測試：

```go
func TestProcessorAppliesJobProjection(t *testing.T) {
    repo := &fakeJobRepository{}
    processor := application.NewProcessor(repo)

    err := processor.Process(context.Background(), event.Event{
        SubjectID: "job_1",
        Type:      event.JobStarted,
    })
    if err != nil {
        t.Fatalf("process event: %v", err)
    }

    if repo.got.ID != "job_1" {
        t.Fatalf("job ID = %q, want job_1", repo.got.ID)
    }
}
```

測試不需要關心檔案搬到哪裡，它只確認 package API 與行為仍然正確。

## 重構步驟

從平面 package 重構成 domain package，可以按這個順序：

1. 列出現有檔案中的概念：request、response、domain state、event、repository、worker。
2. 找出最穩定的 domain 名稱，例如 `job`、`event`、`account`。
3. 先建立一個 domain package，不要一次建立整棵架構。
4. 搬純型別與 typed constant。
5. 用 type alias 過渡大型呼叫端。
6. 搬純規則與測試。
7. 修正 import，避免 domain 依賴 adapter。
8. 測試通過後，再搬下一個 domain。

## 常見錯誤

### 錯誤一：照目錄模板一次切太多層

服務還小時，一次建立 `domain/application/infrastructure/interfaces` 可能只會增加跳轉成本。先拆最痛的語意邊界。

### 錯誤二：package 名稱只描述技術類型

`models`、`types`、`helpers` 通常不夠好。它們說明了程式碼形狀，沒有說明業務語意。

### 錯誤三：domain package import HTTP 或 WebSocket

domain 應保存業務語意，不應知道傳輸協定。若 domain import adapter，依賴方向已經反了。

### 錯誤四：搬移時順手改行為

package 重構應先保持行為不變。若同時改規則與搬檔案，測試失敗時很難判斷是搬移錯誤還是行為改動。

## 本章不處理

- 不要求所有專案都使用 `domain/` 目錄。
- 不一次完成完整分層架構。
- 不討論 monorepo 或多 module 拆分。
- 不把 package 拆分當成替代測試的手段。

## 小結

以 domain 重新整理 package 的重點是讓程式結構反映業務語意。平面多檔案是 Go 程式自然成長階段，只有當語意邊界變模糊時才需要拆 package。搬移時先搬純型別，再搬純規則，最後處理 usecase 與 adapter；domain 不依賴 adapter，測試保護行為不變。
