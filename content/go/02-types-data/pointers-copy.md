---
title: "2.5 指標與資料複製邊界"
date: 2026-04-22
description: "理解指標、slice 與共享狀態的防護策略"
weight: 5
---

Go 的指標讓函式可以操作原本的資料，而不是資料複本。這很有效率，也很危險：當多個地方共享同一份資料時，你需要明確決定誰可以修改，誰只能讀取。

## 本章目標

學完本章後，你將能夠：

1. 理解值傳遞與指標傳遞的差異
2. 判斷何時使用 pointer
3. 理解 slice、map 本身已經帶有共享底層資料的特性
4. 用 copy 保護資料邊界

---

## 【觀察】Go 預設是值傳遞

值傳遞的核心規則是：函式收到的是參數值的複本，修改複本不會改到呼叫端原值。以下範例中，`Rename` 修改的是複本：

```go
type User struct {
    Name string
}

func Rename(u User) {
    u.Name = "Bob"
}

func main() {
    user := User{Name: "Alice"}
    Rename(user)
    fmt.Println(user.Name) // Alice
}
```

`Rename` 修改的是複本，不是 `main` 裡的 `user`。

指標傳遞的核心規則是：函式收到原值位址，因此可以修改呼叫端原值。如果想修改原本的值，就要傳指標：

```go
func Rename(u *User) {
    u.Name = "Bob"
}

func main() {
    user := User{Name: "Alice"}
    Rename(&user)
    fmt.Println(user.Name) // Bob
}
```

`&user` 取得位址，`*User` 表示指向 `User` 的指標。

## 【判讀】pointer 表示共享修改權

pointer 的核心語意是共享修改權，不只是效能工具。它表示被呼叫者可能看到或修改原本那份資料。

適合使用 pointer 的情境：

| 情境                     | 原因                           |
| ------------------------ | ------------------------------ |
| 方法需要修改 receiver    | 例如 `Counter.Inc()`           |
| struct 很大，複製成本高  | 避免每次呼叫都複製大量資料     |
| 需要表示 optional object | `nil` 可表示不存在             |
| 多個方法共享同一份狀態   | 例如 repository、server、cache |

不適合濫用 pointer 的情境：

- 小型不可變資料，例如 `time.Time` 常直接值傳遞
- 只是為了「看起來像物件導向」
- 不希望呼叫者能修改內部資料

## 【策略】slice 和 map 要特別小心

slice 和 map 的核心風險是：即使參數不是 pointer，也會共享底層資料。

### slice 共享底層陣列

slice 參數會複製 slice header，但 header 指向同一個底層 array；因此函式內修改元素，外面會看見。

```go
func Modify(items []string) {
    items[0] = "changed"
}

func main() {
    names := []string{"Alice", "Bob"}
    Modify(names)
    fmt.Println(names[0]) // changed
}
```

### map 本身就是 reference-like

map 傳入函式後，函式可以修改同一份 map。這是很多共享狀態 bug 的來源。

```go
func Modify(m map[string]int) {
    m["count"] = 10
}

func main() {
    values := map[string]int{"count": 1}
    Modify(values)
    fmt.Println(values["count"]) // 10
}
```

## 【執行】回傳資料時建立 copy 邊界

copy 邊界的核心規則是：不希望外部修改內部狀態時，不要直接回傳內部 map、slice 或 pointer。假設 `UserRepository` 內部保存一組使用者：

```go
type User struct {
    ID   string
    Name string
}

type UserRepository struct {
    users map[string]User
}
```

直接回傳 map 會把內部狀態暴露給呼叫者：

```go
func (r *UserRepository) Users() map[string]User {
    return r.users
}
```

呼叫者就可以繞過 `UserRepository` 修改內部資料：

```go
users := repo.Users()
users["1"] = User{ID: "1", Name: "Changed"}
```

安全做法是回傳複製：

```go
func (r *UserRepository) Users() map[string]User {
    result := make(map[string]User, len(r.users))
    for id, user := range r.users {
        result[id] = user
    }
    return result
}
```

回傳 slice 時也要複製 slice：

```go
func (r *UserRepository) ListUsers() []User {
    result := make([]User, 0, len(r.users))
    for _, user := range r.users {
        result = append(result, user)
    }
    return result
}
```

這樣呼叫者可以自由排序、append 或修改回傳資料，不會影響 repository 內部狀態。

## 深層複製與淺層複製

深層複製的核心規則是：struct 裡面若含 slice、map 或 pointer，只複製 struct 本身仍會共享內部資料。以下 `Profile` 包含 slice：

```go
type Profile struct {
    Name string
    Tags []string
}
```

淺層複製：

```go
copyProfile := profile
```

`copyProfile.Tags` 和 `profile.Tags` 仍然指向同一個底層 array。若要保護邊界，需要複製 slice：

```go
func CloneProfile(p Profile) Profile {
    p.Tags = append([]string(nil), p.Tags...)
    return p
}
```

這種 copy 邊界在共享狀態、快取、API response、測試資料中都很重要。

## 小結

Go 的值傳遞讓資料流預設比較安全，但 pointer、slice、map 都會引入共享修改的可能。設計 API 時要明確決定資料是否可以被外部修改；不希望被改，就建立 copy 邊界。
