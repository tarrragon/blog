---
title: "0.3 錯誤處理：把失敗路徑寫出來"
date: 2026-04-22
description: "理解 Go 顯式錯誤處理在服務維護中的價值"
weight: 3
---

Go 錯誤處理的核心原則是把失敗路徑明確寫在程式流程中。`if err != nil` 看起來重複，但它讓每一步可能失敗的地方都可見，也讓讀者能直接知道失敗時程式會怎麼結束。對需要長時間運行、並發處理、背景工作或即時請求回應的服務來說，這種顯式失敗路徑比隱式例外更容易維護。

## 為什麼這章在第零章

如果你的場景已經把 Go 推向服務型系統，那錯誤處理就不是語法細節，而是能不能把服務維持穩定的核心能力。這一章要先建立的是：Go 會要求你把失敗說清楚，因為在高併發或長時間運行的情境下，模糊的失敗行為會比清楚的錯誤訊息更難排查。

## error 是普通回傳值

Go 的 `error` 是一個普通介面值。函式若可能失敗，通常會把錯誤放在最後一個回傳值。

```go
func LoadConfig(path string) (Config, error) {
 data, err := os.ReadFile(path)
 if err != nil {
     return Config{}, fmt.Errorf("read config %q: %w", path, err)
 }

 var config Config
 if err := json.Unmarshal(data, &config); err != nil {
     return Config{}, fmt.Errorf("parse config %q: %w", path, err)
 }

 return config, nil
}
```

這段程式有兩個失敗點：讀檔失敗與 JSON 解析失敗。每個失敗點都立刻處理並回傳，正常流程則留在函式底部。

## 早期返回讓正常流程清楚

早期返回的核心目標是先排除不能繼續的情況。錯誤越早被處理，後續程式越能專注在成功路徑。

```go
func CreateUser(email string) (User, error) {
 email = strings.TrimSpace(email)
 if email == "" {
  return User{}, fmt.Errorf("email is required")
 }

 if !strings.Contains(email, "@") {
  return User{}, fmt.Errorf("invalid email")
 }

 return User{Email: email}, nil
}
```

這個函式先處理空字串與格式錯誤，最後才建立使用者。讀者不需要進入深層巢狀條件，就能知道哪些資料不能通過。

## 包裝錯誤要補上操作脈絡

錯誤包裝的核心責任是保留原始錯誤，同時補上當前操作脈絡。`fmt.Errorf` 搭配 `%w` 可以建立錯誤鏈。

```go
if err := repository.Save(ctx, user); err != nil {
 return fmt.Errorf("save user %q: %w", user.Email, err)
}
```

`save user "alice@example.com"` 是當前操作脈絡，原始錯誤則被 `%w` 保留下來。呼叫端可以印出完整錯誤，也可以用 `errors.Is` 或 `errors.As` 檢查特定錯誤。

不要在每一層都加沒有資訊量的包裝，例如 `fmt.Errorf("failed: %w", err)`。好的錯誤訊息應該回答「做什麼失敗」與「關鍵資料是什麼」。

## HTTP handler 要把錯誤轉成協定語意

HTTP handler 的錯誤處理核心是把內部錯誤轉成明確 status code。輸入格式錯誤通常是 `400`，找不到資料是 `404`，不支援的方法是 `405`，未預期內部錯誤才是 `500`。

```go
func handleCreateUser(w http.ResponseWriter, r *http.Request) {
 var req createUserRequest
 if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
  http.Error(w, "invalid json", http.StatusBadRequest)
  return
 }

 user, err := CreateUser(req.Email)
 if err != nil {
  http.Error(w, err.Error(), http.StatusBadRequest)
  return
 }

 writeJSON(w, http.StatusCreated, user)
}
```

handler 不應該把所有錯誤都回成 `500`。錯誤來自呼叫端輸入時，回 `400` 才能讓 client 知道應該修正 request。

## log 應該放在有處理責任的位置

錯誤記錄的核心規則是誰負責處理錯誤，誰才記錄錯誤。底層函式通常回傳錯誤，上層邊界再決定要 log、重試、轉成 HTTP response 或讓程式結束。

```go
func run() error {
 config, err := LoadConfig("config.json")
 if err != nil {
  return err
 }

 return StartServer(config)
}

func main() {
 if err := run(); err != nil {
  log.Fatal(err)
 }
}
```

`LoadConfig` 不需要自己 `log.Fatal`，因為它不知道呼叫端是否想重試、使用預設值或結束程式。`main` 是 process 邊界，才適合決定失敗時結束。

## 小結

Go 錯誤處理的價值不是少寫幾行，而是讓失敗路徑可讀、可測、可追蹤。每個 `if err != nil` 都是一個明確的決策點：是否補脈絡、是否轉成協定狀態、是否記錄、是否終止流程。這種顯式設計是 Go 長期維護性的核心之一。
