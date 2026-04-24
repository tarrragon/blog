---
title: "6.4 版本偵測與 feature gate"
date: 2026-04-22
description: "依版本與環境能力啟用功能"
weight: 4
---

Feature gate 的核心目標是在外部能力、部署環境或版本不同時，讓服務保留可預期行為。它不是把不穩定功能藏起來而已，而是明確管理功能何時啟用、關閉時如何降級、錯誤時如何回報。

## 本章目標

學完本章後，你將能夠：

1. 用 config struct 集中載入 feature gate
2. 把外部版本偵測轉成 capability
3. 為 gate 關閉時定義降級、回錯或延後處理策略
4. 避免在程式各處直接讀環境變數
5. 同時測試 feature 開與關兩條路徑

---

## 【觀察】新功能上線需要可控行為

Feature gate 的核心需求來自生產環境差異。新功能可能只在部分部署環境可用，外部依賴可能版本不同，某些診斷入口只應在內網啟用，某些即時能力需要先灰度。

沒有 gate 時常見問題：

- 新功能只能一次性全開或全關。
- 部署環境不支援時服務直接失敗。
- 測試只能覆蓋預設路徑。
- 問題發生時無法快速降級。
- 程式各處用環境變數判斷，行為難以推理。

Feature gate 的目的不是增加開關數量，而是讓行為決策集中、可測、可回滾。

## 【判讀】feature gate 是行為合約

Feature gate 的核心語意是控制某段行為是否啟用，以及未啟用時系統要做什麼。它不只是 `if`，而是一個操作合約。

```go
type Features struct {
    RealtimePush bool
    Diagnostics  bool
    Pprof        bool
}
```

開關名稱應描述功能，而不是描述臨時任務。`RealtimePush` 比 `NewCode` 更能長期維護；`Diagnostics` 比 `DebugStuff` 更清楚。

Gate 應在應用啟動時集中載入，再傳給需要的元件。不要在程式各處反覆直接讀環境變數，否則測試與推理都會變困難。

## 【執行】集中載入 feature config

Feature config 的核心責任是把環境變數、設定檔或啟動參數轉成明確資料。

```go
func LoadFeaturesFromEnv() Features {
    return Features{
        RealtimePush: os.Getenv("FEATURE_REALTIME_PUSH") == "1",
        Diagnostics:  os.Getenv("APP_DIAGNOSTICS") == "1",
        Pprof:        os.Getenv("APP_PPROF") == "1",
    }
}
```

組裝時傳入元件：

```go
func main() {
    features := LoadFeaturesFromEnv()

    mux := http.NewServeMux()
    RegisterDiagnostics(mux, features.Diagnostics)

    publisher := NewPublisher(PublisherConfig{
        RealtimeEnabled: features.RealtimePush,
    })

    _ = publisher
}
```

這樣功能測試可以直接建構 `Features`，不必依賴全域環境變數。環境變數解析只需要在 `LoadFeaturesFromEnv` 的測試中覆蓋。

## 【判讀】版本偵測要轉成能力

版本偵測的核心原則是不要讓整個程式到處比較版本字串。應把外部版本轉成 capability，內部只判斷能力。

```go
type Capabilities struct {
    SupportsStreaming bool
    SupportsMetadata  bool
}

func DetectCapabilities(version semver.Version) Capabilities {
    return Capabilities{
        SupportsStreaming: version.GTE(semver.MustParse("2.0.0")),
        SupportsMetadata:  version.GTE(semver.MustParse("2.1.0")),
    }
}
```

內部程式應寫成：

```go
if caps.SupportsStreaming {
    return useStreaming(ctx)
}

return usePolling(ctx)
```

這比到處寫 `if version >= ...` 更清楚，也更容易測試。版本字串是外部事實，capability 是內部行為判斷。

## 【策略】gate 關閉時要有降級策略

Feature gate 的核心問題不是只決定開或關，而是關閉時要做什麼。常見策略包括降級、回錯、隱藏入口、排程稍後處理。

| 策略                                                   | 行為                         | 適用情境                     |
| ------------------------------------------------------ | ---------------------------- | ---------------------------- |
| [fallback](../../../backend/knowledge-cards/fallback/) | 使用舊流程                   | 新能力只是效率改善           |
| reject                                                 | 回明確錯誤                   | 功能沒有安全替代方案         |
| hide                                                   | 不註冊 endpoint 或不顯示入口 | 使用者不應看到該功能         |
| store for later                                        | 先保存，稍後處理             | 即時能力暫不可用但資料不能丟 |

例如即時推送關閉時，可以改成保存待處理資料：

```go
func (p Publisher) Publish(ctx context.Context, event DomainEvent) error {
    if p.realtimeEnabled {
        return p.realtime.Publish(ctx, event)
    }

    return p.repository.SaveForLater(ctx, event)
}
```

降級策略要符合資料語意。不能即時送出不代表可以直接丟掉重要事件。

## 【執行】HTTP endpoint 可用 gate 控制註冊或行為

HTTP feature gate 的核心選擇是「不註冊 endpoint」或「註冊但回明確錯誤」。兩者語意不同。

不註冊 endpoint：

```go
if features.Diagnostics {
    RegisterDiagnostics(mux, true)
}
```

適合診斷入口、內部工具或不希望使用者看見的功能。

註冊但回錯：

```go
func HandleRealtimeExport(features Features) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        if !features.RealtimePush {
            http.Error(w, "realtime export is disabled", http.StatusNotImplemented)
            return
        }

        startRealtimeExport(w, r)
    }
}
```

適合公開 API，讓呼叫端知道功能存在但目前不可用。

## 【策略】gate 不應散落成巢狀 if

Feature gate 的核心維護風險是判斷散落在多層呼叫中，最後沒人知道功能到底何時啟用。

反模式：

```go
if os.Getenv("FEATURE_REALTIME_PUSH") == "1" {
    if version >= "2.0.0" {
        if user.Enabled {
            // ...
        }
    }
}
```

較清楚的做法是先組出 decision：

```go
type RealtimeDecision struct {
    Enabled bool
    Reason  string
}

func DecideRealtime(features Features, caps Capabilities) RealtimeDecision {
    if !features.RealtimePush {
        return RealtimeDecision{Enabled: false, Reason: "feature_disabled"}
    }
    if !caps.SupportsStreaming {
        return RealtimeDecision{Enabled: false, Reason: "streaming_not_supported"}
    }
    return RealtimeDecision{Enabled: true}
}
```

Decision 物件讓 [log](../../../backend/knowledge-cards/log/)、測試與錯誤回應都能使用相同 reason。

## 【執行】log 要記錄 gate decision

Feature gate 的核心操作需求是知道功能為何啟用或關閉。當 gate 影響行為時，應記錄穩定 reason。

```go
decision := DecideRealtime(features, caps)
logger.Info("realtime decision",
    "feature", "realtime_push",
    "enabled", decision.Enabled,
    "reason", decision.Reason,
)
```

這能回答「功能為什麼沒有走即時推送」這類問題。Reason 應是小集合，不要塞完整錯誤字串。

## 【測試】開與關兩條路徑都要測

Feature gate 測試的核心規則是同時測啟用與停用路徑。只測預設值很容易讓另一條路徑壞掉。

停用路徑：

```go
func TestHandleRealtimeExportFeatureDisabled(t *testing.T) {
    req := httptest.NewRequest(http.MethodPost, "/export", nil)
    rec := httptest.NewRecorder()

    handler := HandleRealtimeExport(Features{RealtimePush: false})
    handler.ServeHTTP(rec, req)

    if rec.Code != http.StatusNotImplemented {
        t.Fatalf("status = %d, want %d", rec.Code, http.StatusNotImplemented)
    }
}
```

啟用路徑：

```go
func TestDecideRealtimeEnabled(t *testing.T) {
    decision := DecideRealtime(
        Features{RealtimePush: true},
        Capabilities{SupportsStreaming: true},
    )

    if !decision.Enabled {
        t.Fatalf("realtime should be enabled, reason %q", decision.Reason)
    }
}
```

環境變數解析應單獨測 `LoadFeaturesFromEnv`。功能測試應直接傳入 `Features`，不要依賴全域環境狀態。

## 本章不處理

本章先處理服務內部的 gate 行為邊界；遠端 [feature flag](../../../backend/knowledge-cards/feature-flag/) 平台與灰度流程，會在下列章節再往外延伸：

- [Backend：部署平台與網路入口](../../../backend/05-deployment-platform/)

## 和 Go 教材的關係

這一章承接的是 composition root、handler boundary 與 runtime gate；如果你要先回看語言教材，可以讀：

- [Go：composition root 與依賴組裝](../../../go/07-refactoring/composition-root/)
- [Go：把 handler 邏輯拆成可測單元](../../../go/07-refactoring/handler-boundary/)
- [Go：用 interface 隔離外部依賴](../../../go/07-refactoring/interface-boundary/)
- [Go：testing 基礎](../../../go/05-error-testing/testing-basics/)
- [Go 進階：Kubernetes、systemd 與 load balancer 合約](../../07-distributed-operations/deployment-contracts/)

## 小結

Feature gate 是生產操作工具，也是程式設計邊界。好的 gate 會集中載入、轉成 capability、定義降級策略、輸出穩定 reason，並同時測試開與關兩條路徑。它控制的是行為合約，不只是把新程式碼藏在 `if` 後面。
