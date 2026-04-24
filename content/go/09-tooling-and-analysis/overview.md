---
title: "9.0 Go 在工具鏈生態的位置"
date: 2026-04-24
description: "後端服務以外，Go 常被用來寫 CLI、靜態分析、基礎設施客戶端。本章建立工具類 Go 程式跟服務類 Go 程式在結構、生命週期與錯誤處理上的分野"
weight: 0
---

寫 Go 的工程師第一批落地場景常是後端服務，但業界大量 Go 程式其實是**沒有 HTTP 伺服器、沒有長時 runtime、沒有外部資料庫**的工具。這一章先把「工具類 Go」跟「服務類 Go」的差異講清楚，後續 9.1–9.6 才能聚焦在工具特有的技術。

## 誰在用 Go 寫工具

列幾個業界常見的 Go 寫成的工具，看使用者是否每天在用：

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

- **JSON 不是主角**。工具常處理 markdown、YAML、CSV、純文字；encoding/json 是基礎而非核心。
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

這不是教條，是因為工具經常作為單一 binary 發佈，依賴越少、build 越快、跨平台問題越少。

### 部署：binary 而非 container

服務類部署到 k8s，工具類部署成 `go install example.com/tool@latest` 的 binary。連帶的：

- **不用設計配置檔格式**除非真的需要（CLI flag + 環境變數經常夠）。
- **版本管理用 build tag**（`go build -ldflags "-X main.Version=..."`），不用寫 config schema。
- **升級用戶體驗用 `go install` 就解決**，不用設計自更新機制（除非是 hugo / kubectl 這種 end-user tool）。

## 什麼時候該選 Go 寫工具（跟什麼時候不該）

跟語言選型一樣，決策由工作負載決定：

| 情境                                              | 通常 Go | 通常不是 Go                   |
| ------------------------------------------------- | ------- | ----------------------------- |
| 單一 binary 跨平台分發                            | ✓       | shell / Python 要處理執行環境 |
| 處理大量檔案 I/O、需要併發加速                    | ✓       | shell 太慢、Python GIL 是瓶頸 |
| 需要 parse 複雜格式（markdown、AST、protobuf）    | ✓       | shell 寫起來像噩夢            |
| 要跟 Go 生態系統整合（goldmark、go/ast、x/tools） | ✓       | 跨語言整合成本                |
| 一次性 shell one-liner（grep、sed 能做的）        |         | shell                         |
| 真的需要 ML 或資料科學套件                        |         | Python                        |
| 快速 prototype、throw-away 腳本                   |         | Python                        |
| 需要 REPL 互動探索                                |         | Python / Node                 |

## mdtools 作為本模組的 worked example

從 9.1 開始，每一章都會引用 `scripts/mdtools` 對應程式碼。先簡要介紹這個工具的全貌：

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
