---
title: "模組九：Go 做工具鏈與靜態分析"
date: 2026-04-24
description: "把 Go 的型別、interface 與標準庫用在寫 CLI、靜態分析與內部工具鏈上，補上後端服務之外的另一條常見落地路徑"
weight: 9
---

前八個模組都把 Go 放在後端服務的脈絡下談。這個模組往另一個方向走 — **Go 寫 CLI、lint / migrate 工具、靜態分析、程式碼生成**。這些程式沒有 HTTP handler、沒有 goroutine pool、沒有 PostgreSQL connection；但同樣享受 Go 的型別安全、標準庫深度與跨平台編譯。

業界大量這類 Go 程式：hugo（靜態網站產生器）、kubectl / helm（k8s 客戶端）、terraform（基礎設施描述）、gh（GitHub CLI）、goldmark（markdown parser）、stringer / gopls（官方工具鏈）、golangci-lint（linter 集合）。後端工程師轉過去寫工具時會遇到不同的設計約束：沒有長時執行、資料來自檔案而非 request、錯誤處理偏向中斷而非降級、效能瓶頸是 I/O 而非併發。

本模組以 `scripts/mdtools`（blog 本身用來守住 markdown 品質的內部工具鏈）作為 worked example 串連概念。每一章提煉可複用的 Go 技術；mdtools 只是其中一種 concrete instance，讀者能把同樣 pattern 套到自己的工具上。

## 章節列表

| 章節                                                          | 主題                                             | 關鍵收穫                                                                        |
| ------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------- |
| [9.0](/go/09-tooling-and-analysis/overview/)                  | Go 在工具鏈生態的位置                            | 從後端服務切換到工具開發的心態調整；CLI vs service 的結構差異                   |
| [9.1](/go/09-tooling-and-analysis/stdlib-flag-subcommands/)   | stdlib `flag` 做 subcommand CLI                  | `main` + `cmd/` + `internal/` 佈局；`flag.NewFlagSet` 分派；什麼時候該上 cobra  |
| [9.2](/go/09-tooling-and-analysis/goldmark-ast-basics/)       | 第三方 parser 整合：goldmark AST 入門            | `ast.Walk` visitor 模式；block vs inline 節點；byte offset 定位                 |
| [9.3](/go/09-tooling-and-analysis/ast-idempotent-rewriting/)  | AST 驅動的 idempotent 文字改寫                   | 多 rule 的執行順序；line-based vs AST-guided 的取捨；`--check` / `--fix` 雙模式 |
| [9.4](/go/09-tooling-and-analysis/cross-file-graph-analysis/) | 跨檔案圖分析：從 lint 走到 static analysis       | 建 link graph；反向索引；slug 啟發式多層匹配                                    |
| [9.5](/go/09-tooling-and-analysis/tool-decision-tripwire/)    | 工具決策：regex 到 AST、Python 到 Go 的 tripwire | 用 WRAP 框架做技術決策；哪些訊號代表該升級；延遲決策的代價                      |
| [9.6](/go/09-tooling-and-analysis/pre-commit-and-ci/)         | Pre-commit hook 與 CI 整合                       | 工具從 CLI 走到開發流程；re-staging；CI strict mode；不能繞過的邊界             |

## 本模組的教學主軸

- **stdlib 優先**：Go 的工具鏈文化偏好最小依賴。cobra / viper / 各種框架都有存在的理由，但 Go 的 `flag` + `os` + `filepath` 已經能撐起 80% 的 CLI 需求。
- **AST 是原始 regex 的升級路徑，不是預設起點**：line-based 處理便宜、直觀；AST 在需要「段落歸屬」「父子關係」「跨檔連結」時才付出整合成本才有回報。
- **工具要 idempotent**：`fmt --fix` 跑兩次結果要相同；pre-commit 觸發的修改要保持 git state 完整；`--check` 跟 `--fix` 要共用同一套規則判讀。
- **跨檔案檢查需要圖**：single-file linter 好寫；跨檔 orphan 偵測、連結完整性、reverse-dependency 這類問題需要先把整個 repo 建成結構化圖，再走訪。
- **工具的價值在落地**：寫出能跑的 binary 只是起點；接到 pre-commit hook 跟 CI 才讓工具真正守住品質。

## 章節粒度說明

本模組每章都針對 **一個可複用的工具開發技術**，篇幅會比語法章長一些。每章的結構大致是：

1. 問題描述（為何需要這個技術）
2. 概念與 Go 層面的設計取捨
3. 實作與範例（引用 mdtools 對應程式碼）
4. 常見陷阱
5. 擴充路徑

## 先備知識

讀這個模組前建議已經熟悉：

- 模組一到模組三：Go 語法、型別、標準庫基礎
- 模組五：error 處理與 testing 的基本 pattern
- （加分）模組四：concurrency — 雖然 CLI 工具很少需要 goroutine，但 pipeline fan-out 偶爾用得到

本模組與後端服務模組（6、7、8）是**並行關係**，讀者可以直接跳入，無需先讀完後端系列。

## 本模組使用的範例

- `scripts/mdtools/` — blog 自己的 markdown 品質工具鏈
  - `main.go` 的 subcommand dispatcher
  - `internal/astutil/` 的 goldmark wrapper
  - `internal/mdfmt/` 的格式正規化
  - `internal/mdcards/` 的 link graph
  - `internal/mdmigrate/` 的 L1 auto-fix
- `.githooks/pre-commit` — 把工具接進 git workflow
- `.github/workflows/md-check.yml` — CI 整合

完整工具的設計紀錄可參考 [mdtools：Go + goldmark 的 markdown 工具鏈設計](/posts/mdtools-design/)；AST 概念的入門說明見 [什麼是 AST](/posts/what-is-ast/)。

## 學習時間

預計 2.5-3.5 小時（含動手把 `scripts/mdtools` clone 下來編譯、修改、重跑）
