---
title: "5.2 testing 基礎"
date: 2026-04-22
description: "用 testing package 驗證函式行為"
weight: 2
---

# testing 基礎

Go 測試的核心規則是：測試檔以 `_test.go` 結尾，測試函式以 `Test` 開頭並接收 `*testing.T`。本章將說明如何建立第一個單元測試、檢查結果與回報失敗。

## 測試是同一個 package 的行為說明

Go 測試的核心目標是驗證可觀察行為。測試不是重寫實作細節，而是用輸入、輸出與錯誤條件說明這段程式應該如何運作。

```go
func NormalizeName(input string) string {
	input = strings.TrimSpace(input)
	return strings.ToLower(input)
}
```

這個函式的可觀察行為是：移除前後空白，並轉成小寫。測試應該檢查這個行為，而不是檢查函式內部是否真的先呼叫 `TrimSpace` 再呼叫 `ToLower`。

```go
func TestNormalizeName(t *testing.T) {
	got := NormalizeName("  Alice  ")
	want := "alice"

	if got != want {
		t.Fatalf("NormalizeName() = %q, want %q", got, want)
	}
}
```

這就是最小的 Go 單元測試：準備輸入，呼叫函式，比對結果，失敗時回報清楚訊息。

## 測試檔命名有固定規則

Go 測試檔的核心規則是檔名必須以 `_test.go` 結尾。測試函式必須以 `Test` 開頭，接收一個 `*testing.T` 參數，且沒有回傳值。

```go
// normalize_test.go
func TestNormalizeName(t *testing.T) {
	// ...
}
```

`go test` 會自動找到這些檔案與函式。測試檔可以和被測程式放在同一個 package，也可以使用 `package xxx_test` 建立外部測試 package。

同 package 測試可以存取未匯出的函式與型別，外部測試只能使用匯出的 API。入門階段可以先用同 package 測試，等到需要從使用者視角驗證 public API 時，再使用外部測試。

## 失敗訊息要說明 got 與 want

測試失敗訊息的核心責任是幫助讀者快速定位差異。Go 社群常用 `got` 與 `want` 表示實際結果與預期結果。

```go
if got != want {
	t.Fatalf("NormalizeName() = %q, want %q", got, want)
}
```

這個訊息包含函式名稱、實際結果與預期結果。當測試失敗時，讀者不需要再打開測試檔猜哪個值錯了。

`t.Fatal` 與 `t.Fatalf` 會立刻中止目前測試；`t.Error` 與 `t.Errorf` 會記錄失敗但繼續執行。若後續檢查依賴目前結果，使用 `Fatalf` 比較安全。

```go
got, err := ParsePort("8080")
if err != nil {
	t.Fatalf("ParsePort() error = %v", err)
}

if got != 8080 {
	t.Fatalf("ParsePort() = %d, want %d", got, 8080)
}
```

如果解析已經失敗，後面再檢查數值沒有意義，所以先用 `Fatalf` 結束測試。

## 測試錯誤要明確檢查錯誤存在

錯誤情境測試的核心原則是同時檢查「是否有錯」與「錯誤是否符合預期」。只檢查回傳值常常不足以描述失敗行為。

```go
func ParsePort(input string) (int, error) {
	port, err := strconv.Atoi(input)
	if err != nil {
		return 0, fmt.Errorf("parse port %q: %w", input, err)
	}

	if port <= 0 {
		return 0, fmt.Errorf("port must be positive")
	}

	return port, nil
}
```

測試成功情境時，應確認沒有錯誤；測試失敗情境時，應確認錯誤確實發生。

```go
func TestParsePortInvalid(t *testing.T) {
	_, err := ParsePort("abc")
	if err == nil {
		t.Fatalf("ParsePort() error = nil, want error")
	}
}
```

若程式使用 sentinel error 或可辨識的錯誤型別，可以再用 `errors.Is` 或 `errors.As` 檢查錯誤種類。不要只比對完整錯誤字串，除非錯誤訊息本身就是公開合約。

## helper 函式可以降低重複

測試 helper 的核心用途是隱藏準備資料的細節，而不是隱藏真正的驗證邏輯。helper 應該讓測試主體更接近「這個行為應該成立」。

```go
func mustParsePort(t *testing.T, input string) int {
	t.Helper()

	port, err := ParsePort(input)
	if err != nil {
		t.Fatalf("ParsePort(%q) error = %v", input, err)
	}

	return port
}
```

`t.Helper()` 會讓失敗行號指向呼叫 helper 的測試，而不是 helper 內部。這能讓測試失敗時更快找到真正的案例位置。

helper 不應該把測試意圖藏起來。若 helper 名稱太抽象，或讀者必須跳進 helper 才知道測試在驗證什麼，這個 helper 可能反而降低可讀性。

## 測試要避免依賴不穩定環境

可靠測試的核心規則是讓輸入可控制、輸出可觀察。時間、隨機數、檔案系統、網路與全域狀態都可能讓測試不穩定。

```go
func IsExpired(now time.Time, deadline time.Time) bool {
	return now.After(deadline)
}
```

這個函式把 `now` 當成參數，因此測試可以傳入固定時間。

```go
func TestIsExpired(t *testing.T) {
	now := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)
	deadline := time.Date(2026, 4, 22, 9, 0, 0, 0, time.UTC)

	if !IsExpired(now, deadline) {
		t.Fatalf("IsExpired() = false, want true")
	}
}
```

測試不是越接近真實環境越好，而是要在合適層級控制變因。單元測試優先控制依賴，整合測試才使用真實檔案、網路或服務。

## 小結

Go 測試的基本形狀很固定：`_test.go` 檔案、`TestXxx(t *testing.T)` 函式、清楚的 got/want 比對，以及可讀的失敗訊息。好的測試描述行為，不綁死實作細節；它讓工程師敢修改程式，因為重要行為會被測試保護。

下一章會介紹 table-driven test，說明如何用同一個測試流程整理多組案例。
