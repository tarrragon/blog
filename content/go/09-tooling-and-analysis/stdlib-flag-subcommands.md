---
title: "9.1 用 stdlib flag 寫 subcommand CLI"
date: 2026-04-24
description: "Go 的 flag 套件足以支撐多層 subcommand 的 CLI，不用過早引入 cobra；本章示範 main → cmd/ → internal/ 的標準 layout"
weight: 1
---

Go 的 `flag` 套件聲譽不佳 — 很多後端工程師第一次接觸就跳去 cobra，錯過了 stdlib 真正能做的事。實際情況是：**三層以內的 subcommand，`flag.NewFlagSet` 搭配 `os.Args` 已經足夠**；cobra 的說服點在於 tab completion、generated help、hierarchical commands，不在 flag 解析本身。

本章以 `scripts/mdtools` 為範例，拆解一個實戰 CLI 的 layout：main dispatcher、subcommand entry、internal 實作分層。

## 基礎：為什麼不用 `flag.Parse()` 就好

`flag.Parse()` 只解析一次全域 flag set。對只有一個命令的小工具（如 `tool --input foo`）夠用；但一旦進入 `tool fmt --fix` 這種 `<tool> <subcommand> [flags]` 結構，全域 flag set 就擋路：

- `--fix` 對 `fmt` 命令有意義，對 `lint` 命令沒有。
- 各子命令可能共享 name（例如 `--verbose`）但預設值或語意不同。
- help 輸出需要分子命令各自列自己的 flags。

`flag.NewFlagSet` 讓每個子命令擁有**獨立的 flag 命名空間**：

```go
fs := flag.NewFlagSet("fmt", flag.ExitOnError)
fix := fs.Bool("fix", false, "apply fixes in place")
check := fs.Bool("check", false, "report-only")
_ = fs.Parse(args) // args = os.Args[2:]，已經跳過了子命令本身
```

`fs.Parse(args)` 只看傳進去的片段，不碰 `os.Args` 全域。這是撐起 subcommand CLI 的核心 API。

## 專案 Layout：main → cmd/ → internal/

Go 慣例的 CLI 專案結構是三層，對應三種責任：

```text
scripts/mdtools/
├── main.go             ← 層 1：dispatcher，只做「看第一個參數分派到哪裡」
├── cmd/
│   ├── fmt.go          ← 層 2：每個子命令一個檔案，負責 flag 解析與呼叫 internal
│   ├── lint.go
│   ├── cards.go
│   └── migrate.go
└── internal/
    ├── mdfmt/          ← 層 3：純邏輯，不碰 flag、os.Args、os.Exit
    ├── mdlint/
    └── mdcards/
```

分層的目的不是形式主義。每一層測試方式不同：

- **layer 1**：幾乎不測，因為只是 `switch`。
- **layer 2**：integration test（給定 argv、確認 exit code 與 stdout）。
- **layer 3**：unit test，純函式輸入輸出。

把 `os.Exit` / `os.Args` / `os.Stderr` 都擋在 layer 1-2，layer 3 就能用一般 table-driven test 測，不用起 subprocess。

## Layer 1：main.go dispatcher

```go
// scripts/mdtools/main.go
package main

import (
	"fmt"
	"os"

	"blog/scripts/mdtools/cmd"
)

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}

	sub := os.Args[1]
	args := os.Args[2:]

	var exitCode int
	switch sub {
	case "fmt":
		exitCode = cmd.Fmt(args)
	case "lint":
		exitCode = cmd.Lint(args)
	case "cards":
		exitCode = cmd.Cards(args)
	case "migrate":
		exitCode = cmd.Migrate(args)
	case "-h", "--help", "help":
		usage()
	case "version":
		fmt.Println("mdtools 0.1.0-dev")
	default:
		fmt.Fprintf(os.Stderr, "unknown subcommand: %q\n\n", sub)
		usage()
		exitCode = 2
	}

	os.Exit(exitCode)
}
```

注意幾個 pattern：

- **dispatcher 不做 flag 解析**。`args := os.Args[2:]` 把剩下交給子命令。
- **每個子命令回傳 `int`，dispatcher 統一呼叫 `os.Exit`**。這讓子命令本身容易測（不會直接 kill 測試 process）。
- **`-h` / `--help` / `help` 三種寫法都接受**。Unix 慣例。
- **unknown subcommand 進 exit code 2**，保留 exit 1 給「有違規」的語義。

## Layer 2：子命令入口

每個子命令一個檔案，結構類似：

```go
// scripts/mdtools/cmd/fmt.go
package cmd

import (
	"flag"
	"fmt"
	"os"

	"blog/scripts/mdtools/internal/files"
	"blog/scripts/mdtools/internal/mdfmt"
	"blog/scripts/mdtools/internal/rules"
)

func Fmt(args []string) int {
	fs := flag.NewFlagSet("fmt", flag.ExitOnError)
	fix := fs.Bool("fix", false, "apply fixes in place")
	check := fs.Bool("check", false, "report-only; non-zero on pending changes")
	_ = fs.Parse(args)

	if *check && *fix {
		fmt.Fprintln(os.Stderr, "mdtools fmt: --fix and --check are mutually exclusive")
		return 2
	}
	if !*check && !*fix {
		*check = true // safe default
	}

	paths := fs.Args()
	if len(paths) == 0 {
		paths = []string{"content"}
	}

	cfg := rules.Default()
	mdFiles, err := files.WalkMarkdown(paths)
	if err != nil {
		fmt.Fprintf(os.Stderr, "mdtools fmt: walk error: %v\n", err)
		return 2
	}

	changed := 0
	for _, path := range mdFiles {
		result, err := mdfmt.FormatFile(path, cfg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "mdtools fmt: %s: %v\n", path, err)
			return 2
		}
		if !result.Changed() {
			continue
		}
		changed++
		if *fix {
			if err := os.WriteFile(path, result.Fixed, 0o644); err != nil {
				fmt.Fprintf(os.Stderr, "write %s: %v\n", path, err)
				return 2
			}
			fmt.Printf("fixed: %s\n", path)
		} else {
			fmt.Printf("would fix: %s\n", path)
		}
	}

	if *check && changed > 0 {
		return 1 // CI-friendly: exit 1 means "things need fixing"
	}
	return 0
}
```

要注意幾個設計決策：

- **flag 定義就在入口函式裡**，不抽成 package 常數。每個子命令的 flag 獨立演化。
- **`ExitOnError`** 讓 `fs.Parse` 遇到不合法 flag 直接 exit — 對 CLI 工具 OK，因為 parse 失敗本來就無法繼續。測試時要用 `ContinueOnError` 避免殺測試。
- **positional args 從 `fs.Args()` 取，不是 `os.Args`**。`fs.Parse` 會把非 flag 的留在 fs.Args()。
- **預設值走安全側**（`*check = true` when neither given）— 防止使用者意外執行破壞性動作。
- **exit code 分層語意**：0 = 成功、1 = 有違規、2 = 工具本身失敗。CI script 能用 `[[ $? -eq 1 ]]` 區分。

## Layer 3：internal 實作

Layer 3 是純邏輯，不知道任何 `os` / `flag` 的存在。這讓它能被 layer 2 呼叫、被 test 呼叫、也能在未來被其他 binary 或 library 重用：

```go
// scripts/mdtools/internal/mdfmt/fixer.go
package mdfmt

import (
	"bytes"
	"os"

	"blog/scripts/mdtools/internal/rules"
)

type FixResult struct {
	Path     string
	Original []byte
	Fixed    []byte
}

func (r FixResult) Changed() bool {
	return !bytes.Equal(r.Original, r.Fixed)
}

func FormatFile(path string, cfg rules.Config) (FixResult, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return FixResult{}, err
	}
	fixed := applyAll(data, cfg)
	return FixResult{Path: path, Original: data, Fixed: fixed}, nil
}
```

`FormatFile` 回傳 `(FixResult, error)`，不 `os.Exit`、不印訊息、不碰全域狀態。Test 可以直接給一個記憶體 `[]byte` 跑 `applyAll` 驗結果。

## 什麼時候該上 cobra

三層以內的命令樹，stdlib flag 都撐得住。幾個訊號代表該升級：

| 訊號                                                  | 為什麼 stdlib 處理不好                                      |
| ----------------------------------------------------- | ----------------------------------------------------------- |
| 命令層級超過 3 層（`tool sub1 sub2 sub3 --flag`）     | dispatcher 變成一堆 nested switch，flag 繼承變難維護        |
| 需要自動 shell completion（bash / zsh / fish）        | 手寫 completion 腳本成本高；cobra / urfave-cli 有 generator |
| 需要 markdown / man-page 形式的 help 輸出             | 需要手寫 template；cobra 有 `doc` package                   |
| 有多個 end-user 要閱讀 help（非開發者）               | stdlib 的 `flag.Usage` 格式樸素，使用者體驗差               |
| 大量共用 flag（--verbose / --log-level 每個命令都要） | cobra 的 PersistentFlags 比手工繼承乾淨                     |

mdtools 目前是內部工具、單層 subcommand、end-user 是工程師，這五個訊號都沒命中，繼續 stdlib。若未來做 end-user 工具（例如給讀者下載的命令列套件），值得重新評估。

## 常見陷阱

### 在 layer 3 直接呼叫 `os.Exit`

會破壞 test：test runner 呼叫 `TestXxx` 時，如果 subject code 裡 `os.Exit(1)`，整個 test process 退出，其他 test 不跑。Layer 3 應回傳 error，讓 layer 2 決定怎麼退出。

### 用全域 `var fs = flag.NewFlagSet(...)` 宣告 flag

每次呼叫會累積狀態（flag 已經被定義過會 panic），並且兩個 test 同時跑會 race。定義 flag 要在函式裡。

### 忘記 `ContinueOnError` 就跑 test

`ExitOnError` 是 production 預設，但測試時會讓測試 process 整個退出。Table-driven test 要用：

```go
fs := flag.NewFlagSet(name, flag.ContinueOnError)
fs.SetOutput(io.Discard) // 測試時不要印 usage 到 stderr
```

### 太早抽出「所有子命令共用的 flag」

PersistentFlags 概念在 stdlib 沒有，手動在每個子命令重複 `fs.Bool("verbose", false, ...)` 看似重複但其實可讀。一旦抽成共用 helper，就開始維護一個小框架 — 這時候用 cobra 反而更乾淨。

## 擴充路徑

- **命令太多時分組**：`tool fmt check`、`tool fmt fix` 的兩層 subcommand 可以用「每層一個 switch」展開，main → cmd.Fmt → cmd.FmtCheck。mdtools 的 `migrate fix-links` 就是這個模式（見 `cmd/migrate.go`）。
- **共用 config loading**：`rules.Default()` 這類邏輯放在 internal 裡，每個子命令呼叫；不要每個子命令自己 parse 配置檔。
- **測試 layer 2**：用 `buffer` 捕獲 stdout/stderr，傳入自定 args。參考 Go stdlib 的 `testing/iotest` 跟 `bytes.Buffer`。

## 下一步

[9.2 goldmark AST 入門](../goldmark-ast-basics/) 會看 mdtools 怎麼把 markdown 解析成可操作的結構，layer 3 內部怎麼組織 parser 整合。
