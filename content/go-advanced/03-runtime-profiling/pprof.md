---
title: "3.2 pprof 基礎診斷流程"
date: 2026-04-22
description: "用 pprof endpoint 診斷 heap、goroutine 與 CPU 問題"
weight: 2
---

pprof 的核心用途是用實際執行資料定位效能問題。它能協助觀察 heap、goroutine、CPU、block、mutex 與 [trace](/backend/knowledge-cards/trace/)，讓工程師從「感覺哪裡慢」改成「依 profile 判斷哪裡有壓力」。

## 本章目標

學完本章後，你將能夠：

1. 安全地條件啟用 pprof endpoint
2. 判斷 heap、goroutine、CPU、block、mutex、trace 各自回答什麼問題
3. 用 `go tool pprof` 取得 profile 並閱讀 `top`
4. 區分 `inuse_space` 與 `alloc_space`
5. 把 profile 結果連回程式設計邊界

---

## 【觀察】效能問題需要先問對問題

pprof 診斷的核心起點是先確認你要回答哪個問題。不同 profile 回答不同問題，拿錯工具會讓分析變成猜測。

| 問題                                | 優先 profile       |
| ----------------------------------- | ------------------ |
| 記憶體持續上升                      | heap `inuse_space` |
| GC 壓力高、配置很多                 | heap `alloc_space` |
| goroutine 數量持續增加              | goroutine profile  |
| CPU 使用率高                        | CPU profile        |
| goroutine 常卡在 channel 或 syscall | goroutine / trace  |
| mutex 等待嚴重                      | mutex profile      |
| channel/send/receive 阻塞多         | block profile      |

Profile 不是一次全抓就會自動給答案。先問清楚問題，再抓對應資料，分析成本會低很多。

## 【判讀】pprof endpoint 是受控診斷入口

pprof endpoint 的核心安全責任是受控地暴露診斷資訊。它可能包含 goroutine stack、函式名稱、路徑、記憶體配置模式與部分請求脈絡；正式服務應把 `/debug/pprof/` 放在明確啟用、內部網路或驗證保護之後。

條件啟用範例：

```go
import _ "net/http/pprof"

func RegisterDebugEndpoints(mux *http.ServeMux) {
    if os.Getenv("APP_PPROF") != "1" {
        return
    }

    mux.Handle("/debug/pprof/", http.DefaultServeMux)
}
```

實務上還可以只綁定 localhost、掛在內部管理 port、加上身份驗證，或只在開發與診斷環境啟用。重點是 pprof 要受控，而不是跟公開 API 一起裸露。

## 【執行】heap profile 看記憶體保留與配置壓力

Heap profile 的核心問題是「哪些物件佔用或配置了記憶體」。當服務記憶體持續上升時，heap profile 是第一個常用工具。

看目前仍被保留的記憶體：

```bash
go tool pprof http://localhost:8080/debug/pprof/heap
```

進入 pprof 後：

```text
(pprof) top
```

`inuse_space` 代表目前仍被保留的記憶體，適合分析 leak、cache、map、slice、send [buffer](/backend/knowledge-cards/buffer/)、長期持有資料。

看累積配置量：

```bash
go tool pprof -alloc_space http://localhost:8080/debug/pprof/heap
```

`alloc_space` 代表累積配置量，適合分析 JSON marshal、slice append、短命 object、熱路徑反覆配置造成的 GC 壓力。

## 【判讀】heap profile 要連回資料結構

Heap profile 的核心解讀不是只看函式名稱，而是問「誰持有資料」或「誰反覆配置」。看到某個函式在 top 裡，下一步要回到資料結構與生命週期。

常見對應：

| profile 現象                                                    | 可能設計問題                     |
| --------------------------------------------------------------- | -------------------------------- |
| map 持續佔用                                                    | cache 沒有淘汰或 key 無限制成長  |
| slice/history 佔用高                                            | history 無上限或 list 回傳太大   |
| JSON marshal alloc 高                                           | 高頻推送每個 client 重複 marshal |
| bytes.Buffer 配置高                                             | 熱路徑重複建立 buffer            |
| [websocket](/backend/knowledge-cards/websocket/) message 佔用高 | send buffer 滿載或慢 client      |

Profile 給的是線索，不是最終修正。修正要回到資料模型、copy boundary、buffer policy 或 cache policy。

## 【執行】goroutine profile 看存活與卡住路徑

Goroutine profile 的核心問題是「哪些 goroutine 還活著，以及它們卡在哪裡」。它常用來診斷 goroutine leak、channel 等待、鎖等待與 network read 阻塞。

互動模式：

```bash
go tool pprof http://localhost:8080/debug/pprof/goroutine
```

文字 stack：

```bash
curl "http://localhost:8080/debug/pprof/goroutine?debug=2"
```

若大量 goroutine 卡在同一個 channel receive、send、network read、ticker loop，通常代表某個退出條件、close path、[deadline](/backend/knowledge-cards/deadline/) 或 unregister 設計有問題。

Goroutine profile 不只看數量。少量但卡在錯誤位置的 goroutine，也可能代表資源沒有被釋放。

## 【執行】CPU profile 看熱路徑

CPU profile 的核心問題是「程式把 CPU 時間花在哪裡」。它需要採樣一段時間，適合分析 CPU 使用率高或 request latency 異常。

```bash
go tool pprof "http://localhost:8080/debug/pprof/profile?seconds=30"
```

常用指令：

```text
(pprof) top
(pprof) list Encode
```

CPU profile 要搭配流量情境解讀。低流量時抓到的 profile 可能沒有代表性；高流量時則要注意診斷本身也會造成額外負擔。

若 top 顯示大量時間花在 JSON encode、sort、lock、regex 或 compression，下一步應回到對應熱路徑，判斷是否可以減少工作、快取結果、改資料結構或降低呼叫頻率。

## 【策略】block 與 mutex profile 需要先啟用取樣

Block/mutex profile 的核心用途是分析等待，而不是分析 CPU 計算。它們通常需要在程式中設定取樣比例。

```go
func ConfigureBlockingProfiles() {
    runtime.SetBlockProfileRate(1)
    runtime.SetMutexProfileFraction(5)
}
```

Block profile 看 goroutine 在同步原語上阻塞的時間，例如 channel send/receive、select、mutex。Mutex profile 看鎖競爭。

啟用取樣有成本，不一定要常駐開最高強度。診斷時可以條件啟用，或在壓測環境中使用。

## 【執行】trace 看排程與延遲

Trace 的核心用途是觀察 goroutine 排程、network block、syscall、GC pause 與延遲事件。它比單一 profile 更完整，但也更重。

```bash
curl -o trace.out "http://localhost:8080/debug/pprof/trace?seconds=5"
go tool trace trace.out
```

Trace 適合用在你已經知道有延遲問題，但 heap、CPU、goroutine profile 都不足以解釋時。它能顯示 goroutine 何時 runnable、何時 blocked、何時被排程。

Trace 檔案可能很大，不適合長時間收集。通常先抓短時間，確認問題窗口後再精準分析。

## 【策略】診斷流程要先保留現場

pprof 診斷的核心流程是先保留現場，再改程式。若你先重啟服務或調參，可能會清掉最重要的證據。

建議流程：

1. 記錄當下流量、版本、操作、時間區間。
2. 讀 runtime [metrics](/backend/knowledge-cards/metrics/)：heap、GC、goroutine、[queue](/backend/knowledge-cards/queue/) 長度。
3. 依問題抓 profile：heap、goroutine、CPU 或 trace。
4. 用 profile 找出函式與 stack pattern。
5. 回到程式碼確認資料結構、goroutine lifecycle 或 hot path。
6. 修改後用相同情境再抓一次 profile 驗證。

這個流程能避免「看到 top 第一名就改」的衝動。Profile 需要和情境一起讀，才不會誤判。

## 本章不處理

本章先處理單一服務內的 profile 讀法；商用 APM 與分散式 tracing，會在下列章節再往外延伸：

- [Go 進階：Observability pipeline、metrics 與 tracing](/go-advanced/07-distributed-operations/observability-pipeline/)
- [Backend：可觀測性平台](/backend/04-observability/)

## 和 Go 教材的關係

這一章承接的是 goroutine、allocation 與 runtime metrics；如果你要先回看語言教材，可以讀：

- [Go：goroutine：輕量並發工作](/go/04-concurrency/goroutine/)
- [Go：select：同時等待多種事件](/go/04-concurrency/select/)
- [Go：如何新增背景工作流程](/go/06-practical/new-background-worker/)
- [Go：狀態管理的安全邊界](/go/07-refactoring/state-boundary/)

## 小結

pprof 是診斷工具，不是公開 API。Heap profile 看保留與配置，goroutine profile 看存活與卡住路徑，CPU profile 看熱點，block/mutex profile 看等待，trace 看排程與延遲。好的診斷流程會先問對問題、抓對 profile，再把結果連回資料結構、goroutine lifecycle 與服務行為。
