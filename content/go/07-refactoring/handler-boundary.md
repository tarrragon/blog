---
title: "7.1 把 handler 邏輯拆成可測單元"
date: 2026-04-22
description: "分離 HTTP 協定處理與核心邏輯"
weight: 1
---

handler 重構的核心目標是把 transport concern 和 application concern 分開。handler 應處理 request/response，usecase 應處理行為規則，domain 應保存狀態語意。

## 本章目標

學完本章後，你將能夠：

1. 辨識 handler 過重的訊號
2. 把 request DTO 與 command 分開
3. 把業務規則搬到 usecase
4. 讓 handler 只做 request/response 轉換
5. 分開撰寫 usecase test、handler test 與少量 integration test

---

## 【觀察】過重 handler 會混合三種責任

handler 過重的核心問題是 transport、application 與 state concern 混在同一個函式。當一個 handler 同時解析 JSON、驗證欄位、檢查重複、修改 map、組 response，它就很難測，也很難重用。

常見壞味道：

- handler 超過一兩個螢幕。
- 測試核心規則必須透過 HTTP。
- JSON tag 出現在 domain type 上。
- handler 直接改 repository 的 map 或 slice。
- 多個 handler 重複同樣的驗證與錯誤 mapping。
- 想新增 CLI、worker 或 WebSocket action 時，只能複製 handler 內的邏輯。

以下是一個過重的建立通知 handler：

```go
var notifications = map[string]Notification{}

func handleCreateNotification(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        return
    }

    var req struct {
        ID    string `json:"id"`
        Topic string `json:"topic"`
        Title string `json:"title"`
    }
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "invalid json", http.StatusBadRequest)
        return
    }

    if strings.TrimSpace(req.ID) == "" || strings.TrimSpace(req.Topic) == "" {
        http.Error(w, "missing required field", http.StatusBadRequest)
        return
    }

    if _, exists := notifications[req.ID]; exists {
        http.Error(w, "notification already exists", http.StatusConflict)
        return
    }

    notification := Notification{
        ID:        req.ID,
        Topic:     req.Topic,
        Title:     req.Title,
        CreatedAt: time.Now(),
    }
    notifications[notification.ID] = notification

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    _ = json.NewEncoder(w).Encode(notification)
}
```

這段程式可以跑，但它把太多責任放進 HTTP 邊界。只要要測「重複 ID 不可建立」，就必須走 HTTP；只要要改儲存方式，就必須改 handler。

## 【判讀】先拆 request DTO

request DTO 的核心責任是描述外部輸入格式。它可以有 JSON tag，但不應直接當成 domain model 或 repository model。

```go
type createNotificationRequest struct {
    ID    string `json:"id"`
    Topic string `json:"topic"`
    Title string `json:"title"`
}

func (r createNotificationRequest) validate() error {
    if strings.TrimSpace(r.ID) == "" {
        return ErrInvalidInput{Field: "id", Reason: "required"}
    }
    if strings.TrimSpace(r.Topic) == "" {
        return ErrInvalidInput{Field: "topic", Reason: "required"}
    }
    return nil
}
```

DTO 可以是 unexported，因為它只服務 HTTP handler。JSON tag 也停在 transport layer，不會污染 application command。

錯誤可以先用簡單型別表達：

```go
type ErrInvalidInput struct {
    Field  string
    Reason string
}

func (e ErrInvalidInput) Error() string {
    return e.Field + ": " + e.Reason
}
```

這個錯誤型別讓 handler 可以把輸入錯誤轉成 `400 Bad Request`，而不必靠字串比對。

## 【策略】command 表達 usecase 輸入

command 的核心責任是描述 application layer 要執行的行為。它不需要 JSON tag，也不需要知道 request body 來自 HTTP、WebSocket 或 CLI。

```go
type CreateNotificationCommand struct {
    ID        string
    Topic     string
    Title     string
    CreatedAt time.Time
}
```

handler 負責 DTO -> command 的轉換：

```go
func (r createNotificationRequest) toCommand(now time.Time) CreateNotificationCommand {
    return CreateNotificationCommand{
        ID:        strings.TrimSpace(r.ID),
        Topic:     strings.TrimSpace(r.Topic),
        Title:     strings.TrimSpace(r.Title),
        CreatedAt: now,
    }
}
```

`CreatedAt` 由 handler 或 usecase 決定都可以，但要一致。若時間是業務規則的一部分，通常由 usecase 注入 clock 會更穩；若只是 request 接收時間，handler 傳入也合理。重點是不要在測試中散落 `time.Now()`。

## 【執行】usecase 保存行為規則

usecase 的核心責任是處理行為規則與資料能力。重複檢查、儲存、事件發布或狀態轉移應該在 usecase，而不是 handler。

先定義 usecase 需要的 repository：

```go
type NotificationRepository interface {
    Save(ctx context.Context, notification Notification) error
    FindByID(ctx context.Context, id string) (Notification, bool, error)
}
```

再定義 service：

```go
type CreateNotificationUsecase struct {
    repository NotificationRepository
}

func NewCreateNotificationUsecase(repository NotificationRepository) *CreateNotificationUsecase {
    return &CreateNotificationUsecase{repository: repository}
}
```

執行 command：

```go
func (u *CreateNotificationUsecase) Execute(ctx context.Context, cmd CreateNotificationCommand) (Notification, error) {
    if strings.TrimSpace(cmd.ID) == "" {
        return Notification{}, ErrInvalidInput{Field: "id", Reason: "required"}
    }
    if strings.TrimSpace(cmd.Topic) == "" {
        return Notification{}, ErrInvalidInput{Field: "topic", Reason: "required"}
    }

    if _, exists, err := u.repository.FindByID(ctx, cmd.ID); err != nil {
        return Notification{}, fmt.Errorf("find notification: %w", err)
    } else if exists {
        return Notification{}, ErrAlreadyExists{ID: cmd.ID}
    }

    notification := Notification{
        ID:        cmd.ID,
        Topic:     cmd.Topic,
        Title:     cmd.Title,
        CreatedAt: cmd.CreatedAt,
    }

    if err := u.repository.Save(ctx, notification); err != nil {
        return Notification{}, fmt.Errorf("save notification: %w", err)
    }

    return notification, nil
}
```

`ErrAlreadyExists` 可以是明確錯誤型別：

```go
type ErrAlreadyExists struct {
    ID string
}

func (e ErrAlreadyExists) Error() string {
    return "notification already exists: " + e.ID
}
```

這樣 handler 可以用 `errors.As` 把它對應到 `409 Conflict`。

## 【執行】handler 只做轉換與 mapping

重構後 handler 的核心責任是 request -> command、result -> response、error -> HTTP status。它不直接碰 map，也不保存業務規則。

```go
type NotificationCreator interface {
    Execute(ctx context.Context, cmd CreateNotificationCommand) (Notification, error)
}

type NotificationHandler struct {
    creator NotificationCreator
    now     func() time.Time
}

func NewNotificationHandler(creator NotificationCreator, now func() time.Time) NotificationHandler {
    return NotificationHandler{creator: creator, now: now}
}
```

handler 實作：

```go
func (h NotificationHandler) Create(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        writeError(w, http.StatusMethodNotAllowed, "method_not_allowed", "method not allowed")
        return
    }

    var req createNotificationRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeError(w, http.StatusBadRequest, "invalid_json", "request body must be valid JSON")
        return
    }

    if err := req.validate(); err != nil {
        writeError(w, http.StatusBadRequest, "invalid_input", err.Error())
        return
    }

    notification, err := h.creator.Execute(r.Context(), req.toCommand(h.now()))
    if err != nil {
        writeUsecaseError(w, err)
        return
    }

    writeJSON(w, http.StatusCreated, newNotificationResponse(notification))
}
```

這個 handler 仍然有 HTTP 協定責任，但核心行為已經搬出去。未來 WebSocket action 或 worker 也可以建立 `CreateNotificationCommand` 呼叫同一個 usecase。

## 【策略】response struct 是對外 contract

response struct 的核心責任是描述 HTTP 回應格式。不要直接把 domain model 全部輸出，否則內部欄位會變成外部 API 承諾。

```go
type notificationResponse struct {
    ID        string    `json:"id"`
    Topic     string    `json:"topic"`
    Title     string    `json:"title"`
    CreatedAt time.Time `json:"createdAt"`
}

func newNotificationResponse(notification Notification) notificationResponse {
    return notificationResponse{
        ID:        notification.ID,
        Topic:     notification.Topic,
        Title:     notification.Title,
        CreatedAt: notification.CreatedAt,
    }
}
```

error response 也應該穩定：

```go
type errorResponse struct {
    Code    string `json:"code"`
    Message string `json:"message"`
}

func writeError(w http.ResponseWriter, status int, code string, message string) {
    writeJSON(w, status, errorResponse{
        Code:    code,
        Message: message,
    })
}
```

`writeJSON` 集中 JSON response 寫法：

```go
func writeJSON(w http.ResponseWriter, status int, value any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    _ = json.NewEncoder(w).Encode(value)
}
```

這個 helper 可以忽略 encode error，因為 response 已經開始寫出；正式服務通常會記錄 log。

## 【判讀】error mapping 是 handler 邊界

error mapping 的核心責任是把 application error 轉成 HTTP status 與對外 code。usecase 不應知道 HTTP status；handler 不應靠錯誤字串猜狀態。

```go
func writeUsecaseError(w http.ResponseWriter, err error) {
    var invalid ErrInvalidInput
    if errors.As(err, &invalid) {
        writeError(w, http.StatusBadRequest, "invalid_input", invalid.Error())
        return
    }

    var alreadyExists ErrAlreadyExists
    if errors.As(err, &alreadyExists) {
        writeError(w, http.StatusConflict, "already_exists", "notification already exists")
        return
    }

    writeError(w, http.StatusInternalServerError, "internal_error", "internal server error")
}
```

內部錯誤不要直接回給 client。對外 message 應該穩定且安全；詳細錯誤留給 log 與 error chain。

## 【執行】usecase 測試不需要 HTTP

usecase 測試的核心目標是驗證行為規則。它應該直接建立 command，使用 fake repository，不需要 `httptest`。

```go
type fakeNotificationRepository struct {
    existing map[string]Notification
    saved    []Notification
}

func (f *fakeNotificationRepository) Save(ctx context.Context, notification Notification) error {
    f.saved = append(f.saved, notification)
    return nil
}

func (f *fakeNotificationRepository) FindByID(ctx context.Context, id string) (Notification, bool, error) {
    notification, ok := f.existing[id]
    return notification, ok, nil
}
```

測試建立成功：

```go
func TestCreateNotificationUsecaseExecute(t *testing.T) {
    repo := &fakeNotificationRepository{existing: map[string]Notification{}}
    usecase := NewCreateNotificationUsecase(repo)

    _, err := usecase.Execute(context.Background(), CreateNotificationCommand{
        ID:        "ntf_1",
        Topic:     "deployments",
        Title:     "Deploy finished",
        CreatedAt: time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC),
    })
    if err != nil {
        t.Fatalf("execute usecase: %v", err)
    }

    if len(repo.saved) != 1 {
        t.Fatalf("saved notifications = %d, want 1", len(repo.saved))
    }
}
```

這個測試速度快、錯誤定位明確。若失敗，問題在 usecase，不在 HTTP parsing。

## 【執行】handler test 專注 request/response

handler test 的核心目標是驗證 HTTP 協定行為。它應該使用 fake usecase，而不是真 repository。

```go
type fakeNotificationCreator struct {
    got CreateNotificationCommand
    out Notification
    err error
}

func (f *fakeNotificationCreator) Execute(ctx context.Context, cmd CreateNotificationCommand) (Notification, error) {
    f.got = cmd
    if f.err != nil {
        return Notification{}, f.err
    }
    return f.out, nil
}
```

測試成功 response：

```go
func TestNotificationHandlerCreate(t *testing.T) {
    creator := &fakeNotificationCreator{
        out: Notification{
            ID:        "ntf_1",
            Topic:     "deployments",
            Title:     "Deploy finished",
            CreatedAt: time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC),
        },
    }
    handler := NewNotificationHandler(creator, func() time.Time {
        return time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)
    })

    req := httptest.NewRequest(http.MethodPost, "/notifications", strings.NewReader(`{
        "id": "ntf_1",
        "topic": "deployments",
        "title": "Deploy finished"
    }`))
    rec := httptest.NewRecorder()

    handler.Create(rec, req)

    if rec.Code != http.StatusCreated {
        t.Fatalf("status = %d, want %d", rec.Code, http.StatusCreated)
    }
    if creator.got.Topic != "deployments" {
        t.Fatalf("topic = %q, want deployments", creator.got.Topic)
    }
}
```

這個測試確認 handler 能解析 JSON、建立 command、呼叫 usecase、寫出狀態碼。它不測重複 ID 的儲存規則，那已經是 usecase 測試的責任。

## 【策略】integration test 只保留少數端到端路徑

integration test 的核心用途是確認組裝正確，不是覆蓋所有規則。當 usecase 與 handler 都已有單元測試，端到端測試只需要保留代表性成功與失敗路徑。

例如：

- `POST /notifications` 成功建立。
- invalid JSON 回 `400`。
- 重複 ID 回 `409`。

不要把所有欄位驗證都只放在 integration test。那會讓測試慢、失敗定位模糊，也讓重構成本升高。

## 重構步驟

從過重 handler 重構時，可以按這個順序：

1. 先補 handler 現有行為測試，鎖住 status code 與 response body。
2. 抽出 request DTO，但暫時不改行為。
3. 抽出 command 與 usecase，讓 handler 呼叫 usecase。
4. 把 repository 或 map 寫入移到 usecase 後方。
5. 抽出 response struct 與 error mapping helper。
6. 補 usecase 單元測試。
7. 縮減 handler 測試範圍，保留 request/response 行為。

每一步都應該讓程式可編譯、測試可跑。不要一次把 handler、repository、package 結構全部搬完。

## 常見錯誤

### 錯誤一：只把程式碼搬到另一個函式

如果新函式仍然接收 `http.ResponseWriter` 和 `*http.Request`，那只是移動程式碼，還沒有分離 transport concern。

### 錯誤二：domain model 直接加 JSON tag

JSON tag 是 transport contract。domain model 若直接承擔對外格式，未來內部欄位調整就會牽動 API 相容性。

### 錯誤三：handler 捕捉所有錯誤都回 500

輸入錯誤、重複資料、權限問題與內部錯誤應該對應不同 status code。錯誤型別與 error mapping helper 可以避免字串判斷。

### 錯誤四：只保留端到端測試

端到端測試重要，但不應是唯一測試。usecase 規則越多，越需要直接測 command 與 fake repository。

## 本章不處理

本章先處理 HTTP handler 的轉換邊界；router、middleware 與 transaction，會在下列章節再往外延伸：

- [Go 進階：逐步遷移到 ports/adapters 架構](hexagonal-migration/)
- [Go 進階：資料庫 transaction 與 schema migration](../../go-advanced/07-distributed-operations/database-transactions/)

## 和 Go 教材的關係

這一章承接的是 request DTO、command 與 usecase 分層；如果你要先回看語言教材，可以讀：

- [Go：用 interface 隔離外部依賴](../../go/07-refactoring/interface-boundary/)
- [Go：如何新增一個即時訊息 action](../../go/06-practical/new-websocket-action/)
- [Go：如何新增 repository port](../../go/06-practical/repository-port/)
- [Go：如何擴展狀態投影欄位](../../go/06-practical/state-fields/)

## 小結

handler 重構的重點是讓 HTTP 邊界變薄。request DTO 描述外部輸入，command 描述 application 行為，usecase 保存規則，response struct 描述對外 contract，error mapping 負責 HTTP 狀態碼。當 handler 只做轉換，核心邏輯就能被普通單元測試覆蓋，也能被 WebSocket、worker 或 CLI 重用。
