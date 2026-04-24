---
title: "3.1 GC 與 memory limit"
date: 2026-04-22
description: "理解 debug.SetMemoryLimit 在長時間服務中的用途"
weight: 1
---

GC 與 memory limit 的核心關係是：Go runtime 會根據 heap 成長決定何時執行 GC，而 memory limit 讓 runtime 有一個軟性記憶體目標。Memory limit 不是硬性上限，也不是 leak 修復工具；它是讓 runtime 更早回應記憶體壓力的控制訊號。

## 本章目標

學完本章後，你將能夠：

1. 理解 heap growth、GOGC 與 GC 頻率的關係
2. 判斷 `debug.SetMemoryLimit` 能解決什麼、不能解決什麼
3. 從環境變數設定服務 memory limit
4. 用 runtime [metrics](../../backend/knowledge-cards/metrics) 觀察調整效果
5. 分辨 GC 壓力、長期保留與真正 leak

---

## 【觀察】長時間服務的記憶體問題通常是趨勢問題

記憶體診斷的核心觀察不是單一瞬間數字，而是趨勢。Heap 是否持續上升、GC 後是否下降、goroutine 是否增加、某個操作後是否留下無法回收的資料，這些都比「現在用了多少 MB」更重要。

常見現象：

- 啟動後 heap 穩定在某個區間：通常正常。
- 每次高峰後 heap 都能下降：可能是短暫配置。
- GC 後 heap 仍持續上升：可能有長期保留或 leak。
- GC 次數快速增加且 CPU 升高：可能是 allocation 壓力。
- goroutine 與 heap 同時增加：可能是 goroutine leak 或 send [buffer](../../backend/knowledge-cards/buffer) 堆積。

Memory limit 可以幫 runtime 更積極控制 heap，但不能替代趨勢判讀。

## 【判讀】GC 控制的是 heap 成長

Go GC 的核心目標是回收不再被引用的 heap 物件。Runtime 會根據 `GOGC` 控制下一次 GC 觸發點。

```bash
GOGC=100 go run ./cmd/server
```

`GOGC=100` 大致表示 heap 在上次 GC 後成長約 100% 時觸發下一次 GC。數字越小，GC 越頻繁，記憶體通常較低但 CPU 成本較高；數字越大，GC 較少，記憶體通常較高但 CPU 成本較低。

這是取捨，不是調大或調小就一定更好。CPU 緊繃的服務可能不能承受過低 `GOGC`；記憶體緊繃的服務可能不能承受過高 `GOGC`。

## 【判讀】memory limit 是 runtime 軟目標

`debug.SetMemoryLimit` 的核心用途是告訴 Go runtime 希望整體記憶體使用量靠近某個目標。當 runtime 接近目標時，會更積極回收 heap。

```go
func configureRuntime() {
    const limit = 512 << 20 // 512 MiB
    debug.SetMemoryLimit(limit)
}
```

這不是作業系統層級的硬限制。程式仍可能短暫超過這個值，特別是有大量非 Go heap 記憶體、cgo、mmap、大型 byte slice 尖峰或外部 library 配置時。

Memory limit 適合容器、桌面常駐服務、背景 worker、[WebSocket](../../backend/knowledge-cards/websocket) server 這類需要避免吃掉過多資源的服務。若部署平台已有 memory limit，Go runtime 的 limit 通常應略低於平台限制，留給非 Go heap 與系統開銷。

## 【執行】設定值應來自部署環境

Memory limit 的核心配置原則是由部署環境決定，而不是寫死在 library 裡。應用入口可以讀取環境變數，解析後設定 runtime。

```go
func ConfigureMemoryLimitFromEnv() error {
    raw := os.Getenv("APP_MEMORY_LIMIT_MB")
    if raw == "" {
        return nil
    }

    mb, err := strconv.Atoi(raw)
    if err != nil {
        return fmt.Errorf("parse APP_MEMORY_LIMIT_MB: %w", err)
    }

    if mb <= 0 {
        return fmt.Errorf("APP_MEMORY_LIMIT_MB must be positive")
    }

    debug.SetMemoryLimit(int64(mb) << 20)
    return nil
}
```

錯誤應在啟動時明確失敗。服務若用錯誤設定悄悄運行，後續記憶體行為會很難解釋。

## 【策略】runtime metrics 用來看調整是否有效

Runtime metrics 的核心用途是驗證調整效果。只改 `GOGC` 或 memory limit，不看 heap 與 GC 趨勢，容易變成憑感覺調參。

簡單方式可以用 `runtime.ReadMemStats`：

```go
func ReadHeapAlloc() uint64 {
    var stats runtime.MemStats
    runtime.ReadMemStats(&stats)
    return stats.HeapAlloc
}
```

較完整的服務可以使用 `runtime/metrics`：

```go
func ReadRuntimeSamples() []metrics.Sample {
    samples := []metrics.Sample{
        {Name: "/memory/classes/heap/objects:bytes"},
        {Name: "/gc/cycles/total:gc-cycles"},
        {Name: "/sched/goroutines:goroutines"},
    }
    metrics.Read(samples)
    return samples
}
```

觀察時要看趨勢：調整後 heap 峰值是否下降、GC 次數是否合理、CPU 是否上升、goroutine 是否仍持續增加。

## 【判讀】memory limit 不能修正仍被引用的資料

Memory limit 的核心邊界是它只能影響 GC 行為，不能讓仍被引用的物件消失。若程式把資料一直留在 map、slice、cache、goroutine 或 send buffer 裡，GC 不能回收。

```go
var cache = map[string][]byte{}

func SavePayload(id string, payload []byte) {
    cache[id] = payload
}
```

如果 `cache` 沒有大小限制、[TTL](../../backend/knowledge-cards/ttl) 或刪除策略，memory limit 只會讓 GC 更常跑，但資料仍被 `cache` 引用。真正修正是設計 cache 淘汰、分頁、快照大小限制或資料釋放路徑。

因此遇到 heap 持續上升時，下一步不是先把 memory limit 調得更低，而是用 pprof 確認誰保留了記憶體。

## 【策略】判斷是 GC 壓力還是長期保留

記憶體問題的核心分流是：物件被大量配置但很快回收，還是物件被長期保留。

| 現象                                 | 可能問題                                                            | 下一步                    |
| ------------------------------------ | ------------------------------------------------------------------- | ------------------------- |
| `alloc_space` 高，`inuse_space` 不高 | 短命配置多，GC 壓力大                                               | 找熱路徑 allocation       |
| `inuse_space` 持續上升               | 長期保留或 leak                                                     | 看 heap profile retainers |
| goroutine 數量同步上升               | goroutine leak 或 [queue](../../backend/knowledge-cards/queue) 堆積 | 看 goroutine profile      |
| GC 次數暴增但 heap 仍高              | memory limit 壓力或資料保留                                         | 檢查 cache/map/buffer     |

這個分流會決定後續工具。GC 參數能緩解壓力，但保留資料要回到資料結構與 lifecycle 修。

## 【測試】runtime 設定函式可以獨立測解析

Runtime 本身不需要在單元測試中反覆調參。應把環境解析邏輯獨立出來，測試輸入與錯誤即可。

```go
func ParseMemoryLimitMB(raw string) (int64, error) {
    if raw == "" {
        return 0, nil
    }
    mb, err := strconv.Atoi(raw)
    if err != nil {
        return 0, fmt.Errorf("parse memory limit: %w", err)
    }
    if mb <= 0 {
        return 0, fmt.Errorf("memory limit must be positive")
    }
    return int64(mb) << 20, nil
}
```

測試：

```go
func TestParseMemoryLimitMB(t *testing.T) {
    got, err := ParseMemoryLimitMB("512")
    if err != nil {
        t.Fatalf("parse memory limit: %v", err)
    }
    if got != 512<<20 {
        t.Fatalf("limit = %d, want %d", got, int64(512<<20))
    }
}
```

這讓設定邏輯可測，而不需要在每個測試中真的改 runtime 狀態。

## 本章不處理

本章先處理單一 Go process 如何判讀 heap、GC 與 memory limit；平台 OOM 與部署合約，會在下列章節再往外延伸：

- [Go 進階：Kubernetes、systemd 與 load balancer 合約](../07-distributed-operations/deployment-contracts/)
- [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)

## 和 Go 教材的關係

這一章承接的是 runtime 壓力、allocation 與 pprof 診斷；如果你要先回看語言教材，可以讀：

- [Go：資料結構與 allocation 壓力](allocation/)
- [Go：goroutine leak 偵測](goroutine-leak/)
- [Go：狀態管理的安全邊界](../../go/07-refactoring/state-boundary/)
- [Go：如何新增背景工作流程](../../go/06-practical/new-background-worker/)

## 小結

GC 控制 heap 回收節奏，memory limit 給 runtime 一個記憶體軟目標。合理設定能降低長時間服務的資源風險，但不能修正 cache、map、slice、goroutine 或 buffer 長期持有資料。診斷時先看趨勢，再用 pprof 區分 GC 壓力與長期保留。
