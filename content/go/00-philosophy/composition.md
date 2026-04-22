---
title: "0.2 組合優先：小介面與明確依賴"
date: 2026-04-22
description: "用小介面與 struct 組合取代大型繼承結構"
weight: 2
---

Go 組合的核心原則是用小型型別與小介面拼出行為，而不是建立龐大的繼承階層。程式需要什麼能力，就依賴那個能力；型別擁有哪些資料，就把資料明確放在 struct 裡。

## 組合先描述擁有什麼

struct 的核心責任是把一組資料與依賴放在同一個明確邊界內。Go 不用 class inheritance 表達「某個型別繼承另一個型別」，而是用欄位組合出需要的結構。

```go
type Logger interface {
 Info(message string)
}

type Server struct {
 addr   string
 logger Logger
}
```

`Server` 擁有一個地址，也依賴一個 logger。這些資訊都在欄位上直接呈現，讀者不需要追蹤隱式容器或父類別初始化順序。

當依賴變多時，struct 仍然應該只保留這個型別真正需要的依賴。把整個 application container 塞進 struct，通常會讓依賴邊界變模糊。

## 小介面先描述需要什麼

interface 的核心責任是描述呼叫端需要的行為。Go 的介面通常很小，常見的好介面只有一到三個方法。

```go
type UserFinder interface {
 FindUser(ctx context.Context, id string) (User, error)
}

type UserHandler struct {
 finder UserFinder
}
```

`UserHandler` 不需要知道資料來自資料庫、快取或遠端 API。它只需要「可以用 id 找使用者」這個能力，因此介面只放 `FindUser`。

介面不應該為了抽象而抽象。如果只有一個具體型別，而且沒有測試替身或替換需求，先直接依賴具體型別通常更簡單。

## 依賴由外層組裝

Go 應用組裝依賴的核心策略是讓外層建立具體型別，內層只接收自己需要的依賴。常見位置是 `main()` 或專門的 constructor。

```go
func NewUserHandler(finder UserFinder) UserHandler {
 return UserHandler{finder: finder}
}

func main() {
 db := NewDatabase("postgres://localhost/app")
 repository := NewUserRepository(db)
 handler := NewUserHandler(repository)

 http.HandleFunc("/users/", handler.ServeHTTP)
}
```

這段程式讓資料流與依賴關係保持可見：repository 依賴 db，handler 依賴 repository 的查詢能力。Go 的組合方式偏好把這些關係寫出來，而不是藏在 framework magic 裡。

## 行為可以用 embedding 重用

embedding 的核心用途是把一個型別的欄位或方法提升到外層型別。它是組合工具，不是繼承替代品。

```go
type AuditFields struct {
 CreatedAt time.Time
 UpdatedAt time.Time
}

type User struct {
 ID    string
 Email string
 AuditFields
}
```

`User` 透過 embedding 擁有 `CreatedAt` 與 `UpdatedAt`。這適合重用資料欄位，但不代表 `User` 在概念上「繼承」了 `AuditFields` 的完整行為。

embedding 應該用在語意自然的地方。若提升方法會讓外層型別出現不該公開的能力，明確寫欄位名稱通常更安全。

## 組合讓測試替換更自然

組合的測試價值是可以替換依賴，而不需要啟動整個系統。只要 production code 依賴小介面，測試就能提供 fake。

```go
type fakeUserFinder struct {
 user User
 err  error
}

func (f fakeUserFinder) FindUser(ctx context.Context, id string) (User, error) {
 if f.err != nil {
  return User{}, f.err
 }
 return f.user, nil
}
```

測試 handler 時，可以把 `fakeUserFinder` 傳進去，專注檢查 HTTP response。這不是為了追求 mock 技巧，而是讓測試只覆蓋當前邊界的行為。

## 小結

Go 的組合精神是把依賴與行為放在可讀的位置：struct 寫出擁有什麼，interface 寫出需要什麼，外層負責組裝具體實作。好的組合會讓程式更容易替換、測試與閱讀；壞的抽象則會把簡單依賴藏成難追蹤的間接關係。
