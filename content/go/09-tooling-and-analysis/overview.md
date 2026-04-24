---
title: "9.0 Go 在工具鏈生態的位置"
date: 2026-04-24
description: "後端服務以外，Go 常被用來寫 CLI、靜態分析、基礎設施客戶端。本章建立工具類 Go 程式跟服務類 Go 程式在結構、生命週期與錯誤處理上的分野"
weight: 0
---

工具類 Go 程式的核心責任是**完成一次特定工作就退出**：讀輸入、處理、寫輸出、結束。這個生命週期特徵決定了它的結構 — 以短命、I/O 為主、錯誤即時中斷為預設，跟服務類 Go 長期健康運行的假設正好相反。本章先把這個前提講清楚，後續章節對 main 結構、goroutine 用法、錯誤處理的安排才能看懂為什麼長那樣。

工具類跟服務類的差異常被隱晦地帶過，於是後端工程師轉寫工具時會帶進服務的慣性（長時 goroutine pool、defensive 錯誤降級、龐大依賴樹），讓工具變得重而難維護。把分野講清楚比給 cheatsheet 有用 — 後續每個模式落地時，讀者自己會判斷該採哪套預設。

## 業界哪些人在用 Go 寫工具

下列工具都用 Go 寫成，讀者多半每天都在使用或間接依賴它們：

- **hugo** — 靜態網站產生器，parse markdown + render template + serve dev。
- **kubectl** / **helm** — Kubernetes 的 CLI 客戶端，parse YAML + call API + render output。
- **terraform** — 基礎設施描述語言的 interpreter + state management。
- **gh** — GitHub CLI，把 REST/GraphQL API 包成命令列操作。
- **goldmark** — CommonMark parser，提供 AST 給其他 Go 程式使用。
- **stringer** / **gopls** — Go 官方工具鏈，分析 Go 原始碼並產生程式碼或語言服務。
- **golangci-lint** — 聚合多個 Go linter 的 runner。
- **caddy** / **traefik** — 雖然是服務，但以 CLI-first 配置見長。
- **protobuf / grpc** 的 code generator — 讀 IDL、吐 Go 程式碼。

這些程式都享受 Go 的幾個特定優勢：單一 binary 跨平台部署、快速啟動、stdlib 的 I/O 與檔案系統支援、goroutine 讓 pipeline fan-out 便宜、型別系統防止參數解析等瑣碎錯誤。

## 工具類 Go 跟服務類 Go 的結構差異

多數後端工程師轉去寫工具會遇到幾個慣性衝突。本節列五個最明顯的。

### 生命週期：短命而非長時

服務類 Go 跑起來就不預期結束 — goroutine pool、connection pool、graceful shutdown、health check 都繞著「長時健康運行」打轉。工具類 Go 預設是**執行、完成工作、退出**：

```go
func main() {
    if err := run(); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}
```

沒有 `for { select {} }` 的主迴圈，也不用註冊 signal handler 做 graceful 收尾（OS 會幫你回收檔案描述子）。延伸影響：

- **錯誤處理偏向中斷**：服務類在錯誤時常選擇降級、記錄、繼續；工具類多半直接退出並印訊息，交給呼叫者決定下一步。
- **goroutine 用法保守**：工具很少要 100 個並發 worker。有也多半是 pipeline 的 fan-out，而非長時 pool。
- **context 用法簡單**：很少需要 `context.WithCancel`，`context.Background()` 經常夠用。

### 輸入輸出：檔案 / stdin / 命令列，而非 HTTP / queue

服務讀 request body、寫 response JSON、從 queue 拉訊息。工具讀檔案、parse 命令列 flag、接 stdin pipe、寫 stdout。這改變了幾個預設：

- **輸入格式多元**：工具常處理 markdown、YAML、CSV、純文字；encoding/json 是基礎而非核心，其他 parser 反而更常用。
- **`os.ReadFile` / `os.WriteFile` / `filepath.WalkDir` 是主力**。Path 處理（`filepath.Rel`、`filepath.ToSlash`）會反覆出現。
- **stdout 是結果通道**。服務的 log 跟 response 是兩條 stream；工具的 log 跟 output 經常搶同一條 stream，需要嚴格 discipline：log 全部走 stderr，output 走 stdout，讓使用者能 pipe。

### 錯誤處理：accumulate or fail-fast

服務處理單一 request 時 fail-fast 容易（回 500、log 原因）。工具常一次處理多個輸入（批次 lint 300 個檔案），需要決定：

- **Fail-fast**：第一個錯誤就退出 — 適合 `make check` 這類 gate。
- **Accumulate**：蒐集全部錯誤一起報告 — 適合 `lint` 這類讓使用者看全貌的模式。

`mdtools lint` 就選 accumulate：一次 parse 全部 content，收齊所有 violations，sort 後輸出，退出碼反映是否有 error。作者可以一次看到所有問題，不用反覆跑。

### 依賴管理：盡可能 stdlib

服務的 go.mod 動輒幾十個 require — ORM、HTTP router、metrics、tracing、queue client 全要。工具圈文化明顯保守：

- 很多優秀 Go CLI 工具只有 **1-3 個** direct dependency。
- 標準選型是先看 `flag` + `os` + `filepath` + `encoding/*` 能否滿足。
- 確實需要外部 parser、terminal UI、或結構化資料函式庫時才引入，而非預設。

這個 convention 出於實用考量：工具經常作為單一 binary 發佈，依賴越少、build 越快、跨平台問題越少。

### 部署：binary 而非 container

服務類部署到 k8s，工具類部署成 `go install example.com/tool@latest` 的 binary。連帶的預設：

- **配置用 CLI flag + 環境變數覆蓋**：真正需要結構化配置時才引入 config schema。
- **版本管理用 build tag**：`go build -ldflags "-X main.Version=..."` 把版本刻進 binary。
- **升級由 `go install` 承接**：使用者重跑 `go install` 拉最新版，end-user 工具（hugo / kubectl）才額外設計自更新。

## 工具選型的判讀表

工具語言選型的核心判準是**工作負載特徵**：要不要跨平台分發、要不要處理大量 I/O、要不要整合既有生態。下表給八個判讀情境，各自有展開說明。

| 情境                                      | 偏好 Go | 偏好其他                             |
| ----------------------------------------- | ------- | ------------------------------------ |
| 單一 binary 跨平台分發                    | ✓       | shell / Python 要求受眾處理執行環境  |
| 大量檔案 I/O + 併發加速                   | ✓       | shell 慢、Python GIL 是 CPU 瓶頸     |
| Parse 複雜格式（markdown、AST、protobuf） | ✓       | shell 寫起來會變成 awk/sed 煉金術    |
| 整合 Go 生態（goldmark、go/ast、x/tools） | ✓       | 跨語言整合成本（FFI、serialization） |
| 一次性 one-liner（grep、sed 可解）        |         | shell                                |
| 要用 ML / 資料科學套件                    |         | Python（PyTorch、pandas）            |
| 快速 prototype、throw-away 腳本           |         | Python（動筆 3 倍快）                |
| 需要 REPL 互動探索                        |         | Python / Node / Clojure              |

**單一 binary 跨平台分發**：工具的使用者可能分散在 macOS / Linux / Windows，每個人的 runtime 版本不同。Python 工具要求受眾先裝 Python、確定 3.x vs 2.7、管好 venv；shell 工具在不同 shell（bash / zsh / dash）行為分歧。Go 的靜態編譯讓一個 binary 直接丟出去能跑，這是推廣一個工具時最大的摩擦減法。適用信號：使用者超過 3 人、或使用者非工程師。反例：只在 CI 環境跑的 hook，runtime 已經固定，shell / Python 成本低。

**大量檔案 I/O + 併發加速**：linter 跑 1000 個檔案、migration 處理 10000 個 record，都是 I/O 密集任務。Go 的 goroutine + channel 讓 pipeline fan-out 極便宜，shell 靠 `xargs -P` 也能做但錯誤處理很脆弱；Python 的 GIL 限制真併發，得靠 multiprocessing 增加複雜度。信號：處理量超過「等半秒等得住」、或錯誤需要結構化蒐集。反例：處理一次、規模小於 100 檔，shell 反而快。

**Parse 複雜格式**：markdown、YAML、protobuf、Go 原始碼這類格式需要完整 parser，自己寫 AST walker 成本高。Go 有大量成熟 parser（goldmark、x/net/html、go/parser）可直接 import；shell 靠 grep / awk 拼不出正確解析；Python 的對應 parser（mistune、lxml）也成熟但跟 Go 生態隔離。信號：錯誤率 regex 已經解不乾淨。反例：純粹的文字搜尋 / 取代，regex 穩定勝出。

**整合 Go 生態**：要讀 Go 原始碼（gopls、stringer）、要跟 Hugo / Kubernetes 控制平面互動、要產生 Go 程式碼。這些場景跨語言整合成本高（要 FFI 或 serialization 橋接），Go 原生最直接。信號：上游依賴是 Go 專案、或產出物是 Go 程式碼。反例：跟 Python / JavaScript 生態為主時，用該語言更順。

**一次性 one-liner**：要做的事 grep / sed / awk 十行內能解決，沒有可觀的重複執行需求。用 Go 寫等於建立一個新 binary、build pipeline、版本管理 — 投資回不來。信號：命令能在 shell 下一口氣打完。反例：同樣 logic 要在三個地方重複貼，就該升級成腳本。

**要用 ML / 資料科學套件**：PyTorch、pandas、scikit-learn 沒有 Go 生態等價物。Go 有 gonum、但離 Python ML stack 的工具豐富度差一個數量級。信號：要調 model、做 EDA、畫圖表。反例：只是簡單統計彙總，Go 夠用。

**快速 prototype、throw-away 腳本**：動筆成本比 runtime 效能重要。Python 寫一個 50 行 script 的心智負擔比 Go 低（不用宣告型別、不用 import 大堆 package、REPL 可探索）。信號：要先弄清楚問題形狀。反例：prototype 很快會變成正式工具，Go 直接上反而省重寫。

**需要 REPL 互動探索**：Python / Node / Clojure 有成熟 REPL 文化，能邊試邊寫；Go 的 REPL 工具（yaegi 等）存在但非主流。信號：要實驗資料結構、API 行為、或設計決策。反例：解法已確定，不需要試 — Go 的 test-driven 小程式效果也不差。

## mdtools 作為本模組的 worked example

本模組每一章講一個可複用的工具開發技術，同時用 `scripts/mdtools`（blog 自己用的 markdown 品質工具鏈，實體檔案在本 repo）作為 **concrete instance**。讀者不需要預先熟悉 mdtools — 每章會先講通用 pattern，再用 mdtools 的對應 code 示範一種可行實作。以下是 mdtools 的全貌，方便後面章節引用時有背景：

- **目的**：保證 blog 的 `content/**/*.md` 在 commit 前符合規範文件（`content/posts/markdown-writing-spec.md`）的所有約束。
- **結構**：單一 binary `bin/mdtools`，三個子命令 — `fmt`（格式修正）、`lint`（結構檢查）、`cards`（跨檔完整性）、加一個 `migrate`（一次性批量修正）。
- **實作層**：
  - `internal/mdfmt` — 行為層 format rule，idempotent。
  - `internal/mdlint` — AST 層結構 rule，只報告。
  - `internal/mdcards` — 跨檔 link graph，報告 L1 / L2 / L4 違規。
  - `internal/mdmigrate` — 讀 graph、計算可自動化的修復、改檔。
- **依賴**：stdlib + `github.com/yuin/goldmark` + `github.com/mattn/go-runewidth`（僅此三個 direct）。
- **整合**：`.githooks/pre-commit` 跟 `.github/workflows/md-check.yml` 讓工具在每次 commit / push 都跑。

本模組的章節會逐層展開這些實作背後的 Go 技術。

## 下一步

進入 [9.1 stdlib flag 做 subcommand CLI](../stdlib-flag-subcommands/) 開始看具體實作。
