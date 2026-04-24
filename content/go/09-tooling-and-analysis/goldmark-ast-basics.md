---
title: "9.2 第三方 parser 整合：goldmark AST 入門"
date: 2026-04-24
description: "用 goldmark 把 markdown 解析成 AST，掌握 ast.Walk visitor 模式、block 與 inline 節點的判讀、byte offset 如何定位到行號"
weight: 2
---

第三方 parser 整合的核心責任是**把外部格式的語法細節封裝成可走訪的結構化樹**，讓上層業務邏輯脫離字串處理，直接在 AST 節點上判讀。對 markdown 這類格式，成熟 parser（如 goldmark）提供完整 CommonMark 解析、GFM 擴充、位置資訊；上層工具接住 AST 後再決定要做 lint、rewrite、render 或 graph 分析。

Go 的慣例是**封一層薄 wrapper** — 不讓呼叫端直接看到第三方 API 的完整型別空間，保留未來換 parser 的彈性。加上 Go 的 AST 節點通常區分 **block** 跟 **inline** 兩種型別（對應到 CommonMark spec），走訪時需要配合型別判讀，以免呼叫到只存在於 block 節點的 method（`Lines()` 就是典型例子，對 inline 節點呼叫會 panic）。

本章以 `scripts/mdtools/internal/astutil` 跟 `internal/mdcards/graph.go` 為 concrete instance 示範整合流程。更廣泛的 AST 概念背景在 [什麼是 AST](../../../posts/what-is-ast/)；本章聚焦 Go 層面的整合 pattern。

## 為什麼選 goldmark

Markdown parser 在 Go 有多個選項。選 goldmark 的理由：

- **Hugo 內建用它** — 同一個 parser 解析，lint 結果跟 render 結果一定一致。其他 parser 可能判讀差異導致「lint 過了但 Hugo render 壞」的長尾 bug。
- **完整 CommonMark 支援 + GFM 擴充**。table、strikethrough、task list 都在。
- **AST 節點設計貼近 CommonMark spec**。不用翻對照表。
- **純 Go、零 CGO、穩定**。build 不會踩奇怪的 C 依賴。

類似選擇邏輯可套用到其他格式：Go 原始碼用 `go/parser`，YAML 用 `gopkg.in/yaml.v3`，protobuf 用 `google.golang.org/protobuf/encoding/prototext`。

## 最小整合：parse 一份 markdown

```go
// scripts/mdtools/internal/astutil/parser.go
package astutil

import (
	"github.com/yuin/goldmark"
	"github.com/yuin/goldmark/ast"
	"github.com/yuin/goldmark/extension"
	"github.com/yuin/goldmark/parser"
	"github.com/yuin/goldmark/text"
)

type Parser struct {
	md goldmark.Markdown
}

func NewParser() *Parser {
	md := goldmark.New(
		goldmark.WithExtensions(
			extension.GFM, // Table, Strikethrough, Linkify, TaskList
		),
	)
	return &Parser{md: md}
}

func (p *Parser) Parse(src []byte) ast.Node {
	reader := text.NewReader(src)
	return p.md.Parser().Parse(reader, parser.WithContext(parser.NewContext()))
}
```

為什麼包一層 `Parser` 而不是直接呼叫 `goldmark.New(...).Parser().Parse(...)`：

- **第三方 API 面積大**，工具只需要其中一部分。封裝讓呼叫端看不到 `goldmark.Markdown`、`parser.NewContext` 這些細節。
- **未來換 parser 成本低**：如果有天換 mistune-for-go 或自寫 parser，呼叫端的 `astutil.NewParser().Parse(src)` 不用改。
- **測試替身容易**：unit test 可以 mock `Parser` interface。

三個 struct / package / extension 配置的預設值：

- **Extensions**：`extension.GFM` 涵蓋 blog 需要的全部；不要包太多沒用到的 extension。
- **Context**：每次 `Parse` 都建新 context — goldmark context 儲存 parse 狀態，不能跨 parse 共用。

## AST 節點階層：Block 跟 Inline 的分野

goldmark 的 AST 節點有兩大類，型別系統直接區分：

```go
// goldmark/ast/ast.go
type NodeType int
const (
	TypeDocument NodeType = iota
	TypeBlock
	TypeInline
)
```

**Block 節點**：段落、heading、list、table、blockquote、fenced code block — 在來源檔案中占據完整的行。這類節點帶有 source line segments，能用 `n.Lines()` 取得起訖位置。

**Inline 節點**：link、emphasis、text、code span、image — 存在於 block 節點內部。Inline 節點**沒有獨立的 line segments**；它們的位置由父 block 管理。

這個區分有個實戰後果。第一次寫 AST 走訪的人經常這樣寫：

```go
// WRONG: 對 inline 節點呼叫 Lines() 會 panic
ast.Walk(doc, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
	link, ok := n.(*ast.Link) // Link 是 inline
	if !ok {
		return ast.WalkContinue, nil
	}
	segs := link.Lines() // panic: "can not call with inline nodes"
	...
})
```

Link 節點沒有 Lines()。正確做法是**走上去找最近的 block 節點**：

```go
// scripts/mdtools/internal/mdcards/graph.go
func nodeLine(n ast.Node, src []byte) int {
	for p := n; p != nil; p = p.Parent() {
		if p.Type() != ast.TypeBlock {
			continue
		}
		segs := p.Lines()
		if segs != nil && segs.Len() > 0 {
			return lineNumber(src, segs.At(0).Start)
		}
	}
	return 0
}
```

這個 walk-up-to-block 模式在每個會操作 inline 節點的工具裡都會出現。**初學者的第一個 goldmark panic 幾乎必然是這個**。

## `ast.Walk` visitor 模式

goldmark 用標準 visitor pattern 走 AST：

```go
ast.Walk(doc, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
	// entering == true：進入節點（DFS 下行）
	// entering == false：離開節點（DFS 回溯）
	return ast.WalkContinue, nil
})
```

Walk status 三個常見值：

- `ast.WalkContinue` — 繼續深度優先走訪。
- `ast.WalkSkipChildren` — 跳過子樹，繼續走同層。適合當「處理完整個 Paragraph 就不用再進去找子 Link」。
- `ast.WalkStop` — 整個走訪中止。適合「找到第一個就結束」。

實戰中幾乎只處理 `entering == true` 的情境 — DFS 下行足以覆蓋多數規則。`entering == false` 的 post-order 位置保留給需要聚合子樹資訊的場景（例如計算子樹裡的 link 數量）。

## 實戰：抽出所有 Link 節點並計算位置

`mdtools cards` 要找所有相對連結。這是一個完整的 `ast.Walk` 應用：

```go
// scripts/mdtools/internal/mdcards/graph.go
func (g *Graph) extractEdges(fn FileNode) {
	ast.Walk(fn.AST, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
		if !entering {
			return ast.WalkContinue, nil
		}
		link, ok := n.(*ast.Link)
		if !ok {
			return ast.WalkContinue, nil
		}
		dest := string(link.Destination)
		if isExternalOrAnchor(dest) {
			return ast.WalkContinue, nil
		}
		target := resolveTarget(fn.Path, dest)
		if target == "" {
			return ast.WalkContinue, nil
		}
		g.Edges = append(g.Edges, Edge{
			SourcePath:  fn.Path,
			SourceLine:  nodeLine(n, fn.Src),
			Destination: dest,
			Target:      target,
			DisplayText: string(link.Text(fn.Src)),
		})
		return ast.WalkContinue, nil
	})
}
```

關鍵操作：

- **Type assertion 提前 filter**：`link, ok := n.(*ast.Link)`。不是 Link 就直接 continue，不做無用工。
- **判讀早退**：`isExternalOrAnchor(dest)` 先過濾 `http://` 與 `#anchor` 這類不屬於 graph 的邊。
- **對 inline 節點取行號走 walk-up**（上節講的 `nodeLine`）。
- **text 要透過 `link.Text(fn.Src)` 取** — inline 節點的文字儲存為 source 的 byte segment，不是 string。`link.Text()` 需要帶 src 才能反推。

## Byte offset 定位到行號

goldmark 的 source segment 用 byte offset 標註起訖。要轉成 1-based line number：

```go
// scripts/mdtools/internal/mdcards/graph.go
func lineNumber(src []byte, offset int) int {
	if offset < 0 || offset > len(src) {
		return 0
	}
	line := 1
	for i := 0; i < offset && i < len(src); i++ {
		if src[i] == '\n' {
			line++
		}
	}
	return line
}
```

O(offset) scan。對 300-檔 / 每檔 500 行的 blog repo 夠快；若是幾千萬行的 codebase 才需要預建 line-offset table。

## text.Segment 跟 byte slice 的對應

每個 block 節點的 `Lines()` 回傳 `*text.Segments`，裡面是多個 `text.Segment{Start, Stop int}`：

```go
// 取段落第一行的原始 byte 內容
segs := paragraph.Lines()
firstSeg := segs.At(0)
lineBytes := src[firstSeg.Start:firstSeg.Stop]
```

這個 API 讓你能回頭看原始 source，而不是透過 AST 重新渲染。對 lint 工具（要報告精確位置、甚至 rewrite）很重要。

## 常見陷阱

### 對 inline 節點呼叫 `Lines()`

已經講過，補一句：不只 Link，還有 Text、CodeSpan、Emphasis、Image — 凡是 `n.Type() == ast.TypeInline` 都不能 `Lines()`。寫 rule 時永遠用 `nodeLine` helper。

### 忘記 GFM extension，Table 節點會少

預設 `goldmark.New()` 沒開 GFM。content 裡的表格會被當成普通段落 parse，`ast.Walk` 根本找不到 `*extension.ast.Table` 節點。永遠在 `goldmark.WithExtensions(extension.GFM)`。

### 用 `string(src)` 當作可變字串操作

goldmark 預期 src 在 Parse 過程中 **不變**。若要改動，先讀 `src`、parse、收集位置、**產生新 byte slice**，不要 in-place mutation。

### `ast.Walk` 忘記回傳 continue

```go
ast.Walk(doc, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
	if someCondition {
		processNode(n)
		// 忘記 return，編譯失敗；但加 return 0 會提前終止
	}
	return ast.WalkContinue, nil
})
```

預設要回 `ast.WalkContinue, nil`。早退用 `ast.WalkSkipChildren` 或 `ast.WalkStop`，別用 bare `return`。

## 擴充路徑

- **解析自己的 Go 原始碼**：改用 `go/parser` + `go/ast`。語法樹更複雜（型別、scope、import），但 visitor pattern 本質一樣。參考 gopls 或 stringer 的原始碼。
- **寫自訂 extension**：goldmark 允許註冊 parse-time 與 render-time 的 extension（自己的 block / inline 語法、或接管某個節點的 render 行為）。但除非你的 markdown 有特殊語法（Hugo shortcode 之類），大多數工具不用走這層。
- **AST 快照比對測試**：用 `go-cmp` 比對 `ast.Walk` 抓出的節點序列；新版 goldmark 升級時能快速發現相容性問題。

## 下一步

[9.3 AST 驅動的 idempotent 文字改寫](../ast-idempotent-rewriting/) 會接著看怎麼從「讀 AST」走到「改原檔案」— 這是 `mdtools fmt --fix` 的核心。
