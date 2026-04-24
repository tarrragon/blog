---
title: "mdtools：Go + goldmark 的 markdown 工具鏈設計"
date: 2026-04-24
description: "Blog 專案自訂 markdown 工具鏈 mdtools 的架構決策紀錄。為什麼選 Go 而非 Python、為什麼用 goldmark、單一 binary 多子命令的理由、pre-commit 與 CI 整合方式。"
tags: ["Go", "goldmark", "Markdown", "工具設計", "pre-commit"]
---

## 背景：為什麼要自訂工具

Blog 專案的 markdown 規範有三類不同性質的檢查需求：

1. **基礎格式**（MD022 / MD024 / MD034 / MD060 等）— 市面 linter 都有，但規則細節不一致，我們對 `MD024` 要特殊處理（`siblings_only` 模式允許平行結構下的同名標題）。
2. **反釣魚校驗**（R-URL-1/2）— 顯示文字含 TLD 字樣時必須與 href 的 domain 一致，避免釣魚型連結。這條規則不在 markdownlint 標準集內。
3. **卡片雙向完整性**（L1/L2/L4）— 跨文件的圖論檢查：每張卡片至少被一篇正文引用、相對連結目標存在、卡片首段含鄰卡連結。

三類檢查共享兩個技術需求：**AST 層的語法理解**、**goldmark 與 Hugo render 的一致性**。詳細原因寫在[什麼是 AST](../what-is-ast/)。

Markdownlint-cli2 涵蓋第一類、無法表達第二、三類。現成方案湊不出來，就自己寫。

## 語言選擇：Go vs Python 的 tripwire 式決策

這是實際討論過的決策，值得留下紀錄。

### 表面的直覺：Blog 用 Hugo（Go 寫的），所以用 Go 最自然

這個推論有個破口：Hugo 雖然用 Go 寫，但我們用的是 **pre-built binary**。`hugo server` 本地跑的是下載好的執行檔，CI 用 `peaceiris/actions-hugo` 這類 action，整個 blog 的 build 流程完全不碰 Go toolchain。

「專案已有 Go 依賴」這個前提不成立。真正要問的是：**我是否願意為這組工具引入 Go toolchain 這個新依賴？**

### 務實的對比

| 面向                         | Python                            | Go                                                       |
| ---------------------------- | --------------------------------- | -------------------------------------------------------- |
| Pre-commit 啟動速度          | ~50ms（interpreter 啟動）         | `go run` ~500ms/次；pre-build binary 則要 commit 進 repo |
| CI 新增依賴                  | `setup-python`（runner 通常自帶） | `setup-go` + build step                                  |
| 開發速度（regex / 字串處理） | 快                                | 慢 2-3x，boilerplate 較多                                |
| AST 解析選擇                 | mistune / markdown-it-py          | **goldmark（與 Hugo 同源）**                             |

Go 唯一的決定性優勢是 goldmark — 跟 Hugo 用同一個 parser 可以保證「lint 通過 ↔ Hugo render 成功」等價。

### 關鍵一問：現在需要 AST 嗎？

我們最初傾向的是 tripwire 策略：**現在用 Python + regex 先頂著，等 rule 複雜度超過臨界就升級 Go + goldmark**。Tripwire 條件大致是：

1. Rule 數量超過 5 條。
2. 任一規則需要「這段文字在 code block 內嗎」這類上下文判斷。
3. Hugo render 結果跟 lint 判讀開始不一致。

但事實是：

- MD024 的 siblings_only 已經需要父子關係追蹤 — 條件 2 馬上命中。
- 卡片雙向完整性是當前任務（不是未來可能）— 跨文件檢查 regex 做不到。

兩個條件當下已經滿足，delay migration 反而要兩次寫工具。所以直接選 Go + goldmark。

這個決定的邏輯層面是：**當需求已在手上而非 speculative，延遲決策的代價 > 直接上的代價**。

## 為什麼選 goldmark

三個具體理由：

### 1. 解析結果與 Hugo 一致

Hugo 的 content render pipeline 走 goldmark。用同一個 parser 寫 lint，可以杜絕「lint 通過但 Hugo render 失敗」或「Hugo 看得懂但 lint 誤判」這類長尾 bug。

### 2. AST API 直觀

Goldmark 的 AST 節點型別設計貼近 CommonMark spec：`Document` / `Heading` / `Paragraph` / `Link` / `Table` / `FencedCodeBlock`。要寫 rule 時幾乎不需要翻對照表，直接比對心中的 markdown 結構。

### 3. 活躍且嵌入在主流 Go 生態

Goldmark 是 Hugo 使用的 parser，社群活躍、bug fix 持續進來。不會變成 abandoned dependency。

## 架構設計：單一 binary + 子命令

三個檢查功能分開寫比較好懂，但如果寫成三個 binary，每次 pre-commit 都要 parse markdown 三次，對大型 repo（我們這個已經超過 300 個 markdown）會明顯拖慢。

折衷方案是**單一 binary + 子命令**：

```text
scripts/mdtools/
├── go.mod
├── main.go                    # subcommand dispatcher
├── cmd/
│   ├── fmt.go                 # mdtools fmt [--fix|--check]
│   ├── lint.go                # mdtools lint
│   └── cards.go               # mdtools cards
├── internal/
│   ├── astutil/               # goldmark 封裝（parse, walk, parent chain）
│   ├── rules/                 # 規則定義（可被三個子命令共用）
│   │   ├── config.go          # 全域開關與參數
│   │   ├── headings.go        # 標題規則
│   │   ├── urls.go            # URL + 反釣魚
│   │   ├── tables.go          # 表格正規化
│   │   ├── frontmatter.go     # front matter schema
│   │   └── identifiers.go     # 識別碼白名單（CVE、KB、...）
│   └── report/                # 統一錯誤輸出格式
└── README.md
```

三個子命令共享 `internal/astutil` 和 `internal/rules`，同一個 parse 結果可以在不同規則間重用。

## 實際走訪：MD024 siblings_only 在 goldmark 上怎麼寫

這段是示範 AST-based rule 的可讀性，不是最終實作版本。

```go
package rules

import (
    "bytes"

    "github.com/yuin/goldmark/ast"
    "github.com/yuin/goldmark/text"
)

// CheckSiblingsOnlyHeadings walks the document and flags headings
// that share the same text with a sibling under the same parent heading.
func CheckSiblingsOnlyHeadings(doc ast.Node, src []byte) []Violation {
    var violations []Violation

    // parentMap[level] 保留目前走到的各層 heading，作為後續 H(n+1) 的 parent context
    parentMap := map[int]*ast.Heading{}
    // 每個 parent context 下，收集已見過的子 heading 文字
    seenUnderParent := map[*ast.Heading]map[string]ast.Node{}

    ast.Walk(doc, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
        if !entering {
            return ast.WalkContinue, nil
        }

        h, ok := n.(*ast.Heading)
        if !ok {
            return ast.WalkContinue, nil
        }

        text := string(h.Text(src))
        parent := parentMap[h.Level-1] // 直接上層 heading
        seen, exists := seenUnderParent[parent]
        if !exists {
            seen = map[string]ast.Node{}
            seenUnderParent[parent] = seen
        }

        if prev, dup := seen[text]; dup {
            violations = append(violations, Violation{
                Rule:    "MD024-siblings_only",
                Node:    h,
                Message: "duplicate heading under the same parent: " + text,
                Prev:    prev,
            })
        } else {
            seen[text] = h
        }

        parentMap[h.Level] = h
        // 進到更深層時，清空下層的舊狀態
        for lv := h.Level + 1; lv <= 6; lv++ {
            delete(parentMap, lv)
        }

        return ast.WalkContinue, nil
    })

    return violations
}
```

對比 regex 版本要自己寫「目前 H2 是誰」狀態機 + 「切回上層時清狀態」— goldmark 的 walker pattern 把階層邏輯外部化到樹結構，rule 本身只處理「同一 parent 下有沒有重複」的核心語義。

幾百行 regex 才能穩定做到的事，AST 版本大概 30 行。規則越多，這個倍率越明顯。

## Pre-commit 與 CI 整合

### 本地開發：`.githooks/pre-commit`

```bash
#!/usr/bin/env bash
set -euo pipefail

# 確保 binary 最新
if [[ ! -x bin/mdtools ]] || [[ scripts/mdtools/main.go -nt bin/mdtools ]]; then
    echo "Rebuilding mdtools..."
    (cd scripts/mdtools && go build -o ../../bin/mdtools .)
fi

# 三段式檢查
bin/mdtools fmt --fix   # 自動修格式；改動會 re-stage
git add $(git diff --name-only --cached --diff-filter=AM | grep '\.md$' || true)

bin/mdtools lint        # 結構檢查，失敗即阻擋
bin/mdtools cards       # 跨文件檢查，失敗即阻擋
```

關鍵設計：

- `mdtools fmt --fix` 會改檔，改完後要 `git add` 回 staged，否則 commit 進去的還是舊內容。
- `lint` 和 `cards` 不改檔，只讀與報告。
- Binary mtime 檢查避免每次 commit 都 rebuild。
- `bin/mdtools` 本身 gitignore，不 commit 進 repo。

### CI：`.github/workflows/md-check.yml`

```yaml
name: md-check
on: [push, pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: 'stable' }
      - name: Build mdtools
        run: (cd scripts/mdtools && go build -o ../../bin/mdtools .)
      - name: Format check
        run: bin/mdtools fmt --check
      - name: Structural lint
        run: bin/mdtools lint
      - name: Cross-file completeness
        run: bin/mdtools cards
```

CI 用 `--check` 而非 `--fix` — 任何格式偏差都 fail，不自動修（避免 CI 把修復 commit 推回去造成誤會）。

### 安裝 hook

```bash
git config core.hooksPath .githooks
# 或用 Makefile target：
make install-hooks
```

## 維運成本的長期考量

### 誤判率是規則生命週期的關鍵

每條規則都可能誤判。我們的處理策略寫在規範的 §10：

1. 新規則先在 `internal/rules/` 實作為**可開關**（預設關）。
2. 在代表性檔案上測試誤判率。
3. 誤判率 < 1% 且有明確教材品質收益時，預設開啟。
4. 預設開啟後，同步修正既有違規。

關鍵在「預設關閉」這一步 — 給規則一個試水期，不會直接擋 commit。

### 規則與 spec 文件的同步

Rule config 在 `internal/rules/config.go`，spec 文件在 `content/posts/markdown-writing-spec.md`。兩者修改時必須同步，否則會出現「spec 寫的規則跟工具實際跑的規則不同步」的沉默 bug。

這是目前靠紀律維持的部分。未來如果發現同步偏差重複發生，可以考慮從 config.go 產生 spec 的片段（或反過來）。目前手動同步的成本還可接受。

### 規則數量的預期曲線

當前覆蓋 22 條 rule-config 條目。接下來加規則的收益會遞減 — 大部分重要的基礎格式 + 結構 + 跨文件檢查都已在內。未來新增應該集中在：

- 新內容類型帶來的 schema 擴充（例如做 podcast 或者 video posts）。
- 術語字典完成後的 **L3 術語覆蓋**（正文首次出現術語自動連卡片）。
- 特定領域的品質檢查（例如紅隊教材「每個案例必須有 3 來源」）。

基礎 markdownlint 規則能加的都加完了，再追規則就是在吸邊際收益極低的條目，不值得。

## 延伸閱讀

- [什麼是 AST — 從字串到語法樹的視角轉換](../what-is-ast/) — 為什麼要升級到 AST 工具鏈
- [Blog Markdown 寫作規範與 mdtools 檢查](../markdown-writing-spec/) — mdtools 檢查的完整規則清單
- [goldmark 官方 repo](https://github.com/yuin/goldmark) — Hugo 所用的 markdown parser
- [goldmark AST package reference](https://pkg.go.dev/github.com/yuin/goldmark/ast) — `ast.Walk`、節點型別、parent traversal API
