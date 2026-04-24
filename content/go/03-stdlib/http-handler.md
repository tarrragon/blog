---
title: "3.5 net/http 與 handler 設計"
date: 2026-04-22
description: "用 net/http 建立健康檢查、API endpoint 與清楚的 handler 邊界"
weight: 5
---

Go 的 `net/http` 把 HTTP endpoint 簡化成一個核心模型：handler 接收 request，然後寫出 response。後端服務可以有複雜的資料庫、[queue](../../../backend/knowledge-cards/queue/)、背景工作或即時連線，但 HTTP 入口本身應該先保持清楚。

## handler 是 HTTP 邊界

HTTP handler 的核心責任是處理協定邊界。它應該讀取 request、驗證輸入、呼叫內部邏輯，最後寫出 status code、header 與 body。

```go
func handleHealth(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusOK)
    fmt.Fprint(w, `{"status":"ok"}`)
}
```

這個 handler 只處理健康檢查：確認 HTTP method，設定回應格式，寫出 JSON。它沒有讀取資料庫，也沒有啟動背景工作，因為健康檢查的責任就是讓呼叫者知道服務是否能回應。

handler 可以呼叫內部服務，但不應該把所有業務規則都塞在 HTTP 層。HTTP 層越薄，測試越容易，未來改成 CLI、queue [consumer](../../../backend/knowledge-cards/consumer/) 或其他入口時也比較不會重寫核心邏輯。

## `http.HandlerFunc` 是函式轉接器

`http.HandlerFunc` 的核心意義是讓普通函式符合 `http.Handler` 介面。只要函式形狀是 `func(http.ResponseWriter, *http.Request)`，就能成為 HTTP handler。

```go
func hello(w http.ResponseWriter, r *http.Request) {
    fmt.Fprint(w, "hello")
}

func main() {
    http.HandleFunc("/hello", hello)
    http.ListenAndServe(":8080", nil)
}
```

`http.HandleFunc` 會把 `hello` 轉成 handler 並註冊到預設 mux。小範例可以這樣寫，但實際應用通常會建立自己的 `ServeMux`，避免全域註冊讓測試與組裝變得不清楚。

```go
func newRouter() http.Handler {
    mux := http.NewServeMux()
    mux.HandleFunc("/health", handleHealth)
    mux.HandleFunc("/users", handleUsers)
    return mux
}
```

回傳 `http.Handler` 可以隱藏路由實作，呼叫端只需要知道這是一個可被 server 使用的 handler。

## `ServeMux` 負責路由分派

`ServeMux` 的核心責任是把 request path 對應到 handler。標準庫的 `http.NewServeMux` 足以建立許多小型服務與教學範例。

```go
func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("GET /health", handleHealth)
    mux.HandleFunc("POST /users", handleCreateUser)

    server := &http.Server{
        Addr:    ":8080",
        Handler: mux,
    }

    if err := server.ListenAndServe(); err != nil {
        log.Fatal(err)
    }
}
```

新版 Go 的 `ServeMux` 支援在 pattern 裡寫 HTTP method，例如 `GET /health`。這能讓 method 與 path 在註冊處一起呈現。

若你的專案需要 middleware group、path parameter 或更完整的路由功能，可以使用第三方 router。入門階段先理解標準庫模型，會更容易看懂任何 router 的抽象。

## request 讀取要有明確限制

讀取 request 的核心原則是只接受你預期的內容。handler 應該檢查 method、content type、body 大小與 JSON 格式，避免把任意輸入直接交給內部邏輯。

```go
type createUserRequest struct {
    Name  string `json:"name"`
    Email string `json:"email"`
}

func handleCreateUser(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        return
    }

    defer r.Body.Close()
    r.Body = http.MaxBytesReader(w, r.Body, 1<<20)

    var req createUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "invalid json", http.StatusBadRequest)
        return
    }

    if req.Email == "" {
        http.Error(w, "email is required", http.StatusBadRequest)
        return
    }

    w.WriteHeader(http.StatusCreated)
}
```

`http.MaxBytesReader` 限制 body 大小，避免大型輸入消耗過多記憶體。`json.Decoder` 解析 body，失敗時回傳 `400 Bad Request`。欄位驗證通過後，handler 才進入真正的建立流程。

這段範例省略了資料儲存，因為本章重點是 HTTP 邊界。實務上通常會把建立使用者的規則放到 service 函式，handler 只負責轉換 request 與 response。

## response 要先決定狀態碼

寫 response 的核心規則是先決定 status code，再寫 header 與 body。只要 body 開始寫出，Go 就會送出預設或目前設定的 status code。

```go
func writeJSON(w http.ResponseWriter, status int, value any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)

    if err := json.NewEncoder(w).Encode(value); err != nil {
        // response 已經開始寫出，這裡通常只能記錄錯誤。
        log.Printf("write json response: %v", err)
    }
}
```

`WriteHeader` 應該在 `Encode` 之前呼叫。若先寫 body，再呼叫 `WriteHeader`，狀態碼可能已經固定為 `200 OK`。

```go
writeJSON(w, http.StatusCreated, map[string]string{
    "id": "user_123",
})
```

小型範例可以直接在 handler 裡寫 response；當多個 handler 都要輸出 JSON 時，抽出 `writeJSON` 這類 helper 可以減少重複。

## handler 可以依賴介面

handler 依賴介面的核心好處是測試與替換更容易。HTTP 層不需要知道資料來自資料庫、記憶體或遠端 API，只需要知道它可以呼叫某個能力。

```go
type UserCreator interface {
    CreateUser(ctx context.Context, name string, email string) (string, error)
}

type UserHandler struct {
    creator UserCreator
}

func (h UserHandler) Create(w http.ResponseWriter, r *http.Request) {
    // 解析與驗證 request 後：
    id, err := h.creator.CreateUser(r.Context(), "alice", "alice@example.com")
    if err != nil {
        http.Error(w, "create user", http.StatusInternalServerError)
        return
    }

    writeJSON(w, http.StatusCreated, map[string]string{"id": id})
}
```

這裡的 `UserHandler` 不知道使用者如何被建立，只知道有一個 `UserCreator`。測試時可以提供假的 creator，正式環境再接上真正實作。

介面不需要一開始就為所有東西建立。當 handler 真的需要隔離外部依賴，或測試需要替換依賴時，再抽出小介面會更自然。

## 小結

`net/http` 的核心模型很小：request 進來，handler 寫出 response，`ServeMux` 負責把路由分派到 handler。好的 handler 會清楚處理 HTTP method、輸入驗證、錯誤狀態與輸出格式，並把真正的業務規則留給內部函式或服務。

下一章會回到 logging，說明如何用 `slog` 讓服務輸出可搜尋、可關聯的結構化資訊。
