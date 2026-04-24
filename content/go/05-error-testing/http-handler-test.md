---
title: "5.4 HTTP handler 測試"
date: 2026-04-22
description: "用 httptest 驗證 request 與 response"
weight: 4
---

HTTP handler 測試的核心規則是不用啟動真實 server，也能驗證 request 進入 handler 後產生的 response。`net/http/httptest` 提供 request builder 與 response recorder，讓 handler 可以像普通函式一樣被測試。

## `httptest` 把 HTTP 測試變成函式呼叫

`httptest` 的核心用途是建立測試用 request 與 response writer。handler 本來就是 `func(http.ResponseWriter, *http.Request)`，所以測試可以直接呼叫 handler。

```go
func handleHealth(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    fmt.Fprint(w, `{"status":"ok"}`)
}
```

這個 handler 可以不用啟動 port，也不用發出真實網路請求。

```go
func TestHandleHealth(t *testing.T) {
    req := httptest.NewRequest(http.MethodGet, "/health", nil)
    rec := httptest.NewRecorder()

    handleHealth(rec, req)

    res := rec.Result()
    defer res.Body.Close()

    if res.StatusCode != http.StatusOK {
        t.Fatalf("status = %d, want %d", res.StatusCode, http.StatusOK)
    }
}
```

`httptest.NewRequest` 建立 request，`httptest.NewRecorder` 記錄 response。測試直接呼叫 `handleHealth(rec, req)`，再檢查 recorder 產生的結果。

## status code 是第一個行為合約

HTTP response 的核心合約通常先看 status code。成功、輸入錯誤、方法不允許與伺服器錯誤，都應該有明確狀態碼。

```go
func TestHandleHealthMethodNotAllowed(t *testing.T) {
    req := httptest.NewRequest(http.MethodPost, "/health", nil)
    rec := httptest.NewRecorder()

    handleHealth(rec, req)

    if rec.Code != http.StatusMethodNotAllowed {
        t.Fatalf("status = %d, want %d", rec.Code, http.StatusMethodNotAllowed)
    }
}
```

`rec.Code` 可以直接取得 handler 寫出的狀態碼。若 handler 沒有呼叫 `WriteHeader`，但有寫 body，狀態碼通常會是 `200`。

測試狀態碼時，不要只檢查 body 字串。body 可能改文案，但 status code 才是呼叫端最依賴的協定訊號。

## body 檢查要符合輸出格式

response body 的核心檢查方式應該配合輸出格式。純文字可以比對字串；JSON 應該解析成 struct 或 map 後再比對欄位。

```go
func TestHandleHealthBody(t *testing.T) {
    req := httptest.NewRequest(http.MethodGet, "/health", nil)
    rec := httptest.NewRecorder()

    handleHealth(rec, req)

    var body struct {
        Status string `json:"status"`
    }

    if err := json.NewDecoder(rec.Body).Decode(&body); err != nil {
        t.Fatalf("decode response body: %v", err)
    }

    if body.Status != "ok" {
        t.Fatalf("status field = %q, want %q", body.Status, "ok")
    }
}
```

解析 JSON 後檢查欄位，比直接比對 `{"status":"ok"}` 更穩定。JSON 欄位順序、空白與換行不應該讓測試失敗。

## request body 可以用 `strings.NewReader`

測試 JSON request 的核心做法是把字串或 bytes 包成 reader。handler 看到的是 `io.Reader`，不需要知道資料來自檔案、網路或測試字串。

```go
func TestHandleCreateUser(t *testing.T) {
    body := strings.NewReader(`{"name":"Alice","email":"alice@example.com"}`)
    req := httptest.NewRequest(http.MethodPost, "/users", body)
    req.Header.Set("Content-Type", "application/json")

    rec := httptest.NewRecorder()
    handler := newCreateUserHandler(fakeUserCreator{})

    handler.ServeHTTP(rec, req)

    if rec.Code != http.StatusCreated {
        t.Fatalf("status = %d, want %d", rec.Code, http.StatusCreated)
    }
}
```

`strings.NewReader` 讓測試資料留在測試檔中，適合小型 JSON。若 request 很大或要重複使用，可以把測試資料放在 `testdata` 目錄。

## 依賴應該用 fake 隔離

handler 測試的核心邊界是 HTTP 行為，不是資料庫或外部服務。若 handler 需要呼叫內部服務，可以提供 fake 實作，讓測試專注於 request/response。

```go
type fakeUserCreator struct {
    id  string
    err error
}

func (f fakeUserCreator) CreateUser(ctx context.Context, name string, email string) (string, error) {
    if f.err != nil {
        return "", f.err
    }
    return f.id, nil
}
```

成功案例可以讓 fake 回傳 id，失敗案例可以讓 fake 回傳錯誤。這樣測試可以分別驗證 `201 Created` 與 `500 Internal Server Error`。

```go
func TestHandleCreateUserServiceError(t *testing.T) {
    req := httptest.NewRequest(http.MethodPost, "/users", strings.NewReader(`{"name":"Alice","email":"alice@example.com"}`))
    rec := httptest.NewRecorder()

    handler := newCreateUserHandler(fakeUserCreator{err: errors.New("database unavailable")})
    handler.ServeHTTP(rec, req)

    if rec.Code != http.StatusInternalServerError {
        t.Fatalf("status = %d, want %d", rec.Code, http.StatusInternalServerError)
    }
}
```

這不是完整整合測試，而是 handler 單元測試。資料庫連線、[migration](../../../backend/knowledge-cards/migration/)、真實網路等行為應該放在更高層級的整合測試處理。

## 小結

`httptest` 讓 handler 測試保持快速且可控：建立 request、用 recorder 接 response、檢查 status、header 與 body。好的 handler 測試會隔離外部依賴，專注於 HTTP 協定行為，讓 API 邊界在重構時不容易被破壞。

下一章會處理時間注入，說明如何避免測試依賴真實現在時間。
