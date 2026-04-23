---
title: "5.1 錯誤回傳與早期返回"
date: 2026-04-22
description: "寫出可追蹤的失敗路徑"
weight: 1
---

Go 把錯誤當成回傳值。這讓失敗路徑直接出現在程式碼裡，也讓呼叫者必須明確決定如何處理失敗。

## 本章目標

學完本章後，你將能夠：

1. 理解 `error` 回傳值的設計目的
2. 用 early return 保持控制流程扁平
3. 為錯誤加上足夠脈絡
4. 在 HTTP handler 中對應不同錯誤情境

---

## 【觀察】Go 錯誤處理很顯式

Go 錯誤處理的核心規則是：可能失敗的函式用 `error` 回傳失敗，呼叫者在呼叫點立即處理。常見寫法如下：

```go
data, err := os.ReadFile("config.json")
if err != nil {
    return err
}
```

這段程式很直接：讀檔可能失敗，失敗就回傳錯誤。

對剛接觸 Go 的人來說，`if err != nil` 可能看起來重複。但這個重複有明確目的：失敗路徑不被隱藏，讀者可以逐步看見每個操作失敗時會發生什麼事。

## 【判讀】錯誤是控制流程的一部分

Go 的錯誤模型把失敗視為控制流程的一部分。很多語言用 exception 讓錯誤跳出目前流程；Go 則偏好讓錯誤留在函式簽名和呼叫點：

```go
func LoadConfig(path string) (Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return Config{}, fmt.Errorf("read config: %w", err)
    }

    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return Config{}, fmt.Errorf("parse config: %w", err)
    }

    if err := validateConfig(cfg); err != nil {
        return Config{}, fmt.Errorf("validate config: %w", err)
    }

    return cfg, nil
}
```

錯誤脈絡的核心規則是：越靠近失敗來源，越應補上「正在做什麼」的資訊。這裡每個錯誤都被加上脈絡：

- `read config`
- `parse config`
- `validate config`

當錯誤出現在 [log](../../backend/knowledge-cards/log) 裡時，讀者不只知道失敗了，也知道失敗在哪個階段。

## 【策略】用 early return 避免巢狀

early return 的核心規則是：失敗路徑就地返回，成功路徑保持在左側。不要把成功路徑包在很多層 `else` 裡：

```go
// 不佳：成功路徑被包在巢狀中
func Load(path string) (Config, error) {
    data, err := os.ReadFile(path)
    if err == nil {
        var cfg Config
        err = json.Unmarshal(data, &cfg)
        if err == nil {
            return cfg, nil
        } else {
            return Config{}, err
        }
    } else {
        return Config{}, err
    }
}
```

Go 更常用 early return：

```go
func Load(path string) (Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return Config{}, err
    }

    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return Config{}, err
    }

    return cfg, nil
}
```

成功路徑保持在左側，失敗路徑就地處理。這是 Go 可讀性的重要風格。

## 【執行】HTTP handler 中的錯誤路徑

邊界層錯誤處理的核心規則是：內部錯誤要轉成呼叫者能理解的回應。HTTP handler 要把 Go 的錯誤轉成 HTTP response：

```go
func handleCreateUser(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeJSONError(w, http.StatusBadRequest, "invalid JSON")
        return
    }

    if req.Name == "" {
        writeJSONError(w, http.StatusBadRequest, "name is required")
        return
    }

    user, err := createUser(req)
    if err != nil {
        writeJSONError(w, http.StatusInternalServerError, "create user failed")
        return
    }

    writeJSON(w, http.StatusCreated, user)
}
```

這段程式的層次很清楚：

1. JSON 格式錯誤 → 400
2. 欄位驗證錯誤 → 400
3. 內部建立失敗 → 500
4. 成功 → 201

每個錯誤路徑都結束於 `return`，後面的成功流程不需要被 `else` 包住。

## 錯誤訊息要包含脈絡

錯誤訊息分層的核心規則是：內部 error 保留診斷脈絡，對外 response 保持穩定且不洩漏內部細節。底層函式應該保留技術脈絡：

```go
return fmt.Errorf("insert user %q: %w", req.Name, err)
```

但對外 response 不一定要暴露內部錯誤：

```go
writeJSONError(w, http.StatusInternalServerError, "create user failed")
```

這是兩層不同需求：

| 層次          | 目標                       |
| ------------- | -------------------------- |
| 內部 error    | 幫工程師定位問題           |
| 對外 response | 給呼叫者穩定、可理解的訊息 |

## 小結

Go 的錯誤處理看似重複，但它讓失敗路徑保持可見。用 early return 保持成功路徑扁平，用 `fmt.Errorf(... %w ...)` 補上脈絡，再在邊界層把錯誤轉成合適的回應。
