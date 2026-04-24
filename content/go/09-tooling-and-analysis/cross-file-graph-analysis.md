---
title: "9.4 跨檔案圖分析：從 lint 走到 static analysis"
date: 2026-04-24
description: "Single-file 規則用 AST 搞定；跨檔 orphan 偵測、broken link、backlink 完整性需要把整個 repo 建成圖再走訪。用 mdtools cards 為例"
weight: 4
---

跨檔案靜態分析的核心責任是**把整個 repo 結構化成可查詢的 [link graph](../../glossary/#跨檔案-link-graph)**，讓「這張卡片有沒有被引用」「這個連結指的目標存在嗎」「這個 section 是否被孤立」這類反向/跨檔問題能在 O(1) 或 O(log n) 的 graph lookup 內回答，而不是每次查詢都重 parse 全部檔案。圖的節點是檔案、邊是檔案間的連結 / 引用 / 依賴關係；一次 parse（用 [AST walker](../../glossary/#ast-walker) 掃過）之後，所有跨檔 query 都在 in-memory map 上做。

這類分析的典型觸發點是需求已經離開 single-file 層：**orphan 偵測**（某個檔案是否被引用）、**backlink 完整性**（連結目標是否存在）、**dependency cycle 檢測**（import graph 是否有環）、**unused export 偵測**（某個 symbol 是否被使用）。每個都是圖論問題，需要先把 repo 結構化，單檔 walker 看不見跨檔 edge。本章以 `mdtools cards`（L1 連結有效性、L2 orphan 卡片、L4 卡片 K4 合規）作為 concrete instance。

## 為什麼要預先建圖而非每次 lint 都現查

直覺會說：對每個 link，直接 `os.Stat(target)` 看存在不存在，就能驗證 L1。

這個做法在 100 個檔案、每檔 10 個 link 時 OK — 1000 次 stat、每次 < 1ms，總計 1 秒內。但一旦要做 L2 「每張卡片至少被一篇正文引用」，問題就變成：

```text
for each card file C:
  for each other file F:
    parse F
    for each link L in F:
      if L points to C: mark C as referenced
```

N² parse，每次 parse 又走 AST。1000 檔 × 1000 檔 = 100 萬次 parse，每次 50ms，總計 14 小時。

解法是 **parse 一次、存下所有 edge、在圖上查**。Parse 是 O(N) 一次；所有後續 query 都在 in-memory map 上做，microseconds。

## Graph 的資料結構

```go
// scripts/mdtools/internal/mdcards/graph.go
type Edge struct {
	SourcePath  string // 包含連結的檔案
	SourceLine  int    // 連結所在行
	Destination string // link 目的地（原文）
	Target      string // 解析後的檔案路徑（可能不存在）
	DisplayText string // 顯示文字（反釣魚用）
}

type FileNode struct {
	Path string
	AST  ast.Node
	Src  []byte
}

type Graph struct {
	Files []FileNode  // 所有 .md 檔
	Edges []Edge      // 所有相對連結

	byPath   map[string]*FileNode // path → FileNode
	inbound  map[string][]int     // target path → edge indices
	outbound map[string][]int     // source path → edge indices
}
```

設計重點：

- **FileNode 保留 AST + src**：後面 L4 檢查（卡片首段是否有鄰卡連結）需要重讀 AST，不想再 parse 一次。
- **Edge 用 slice 儲存，index 走 map**：比起直接用 `map[string][]Edge`，這個 layout allocation 少、GC 友善，也容易 sort 輸出。
- **inbound / outbound 都預先建**：L1 靠 outbound，L2 靠 inbound。一次 parse 把兩邊都填好。

## Parse pipeline：兩段式確保指標穩定

```go
// scripts/mdtools/internal/mdcards/graph.go
func BuildGraph(roots []string) (*Graph, error) {
	mdFiles, err := files.WalkMarkdown(roots)
	if err != nil {
		return nil, err
	}

	parser := astutil.NewParser()
	g := &Graph{
		byPath:   map[string]*FileNode{},
		inbound:  map[string][]int{},
		outbound: map[string][]int{},
	}

	// 第一段：parse 全部檔案，填 g.Files
	for _, path := range mdFiles {
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, err
		}
		doc := parser.Parse(data)
		node := FileNode{Path: path, AST: doc, Src: data}
		g.Files = append(g.Files, node)
		g.byPath[path] = &g.Files[len(g.Files)-1]
	}

	// 第二段：抽出 edge（此時 g.Files 大小已固定，指標穩定）
	for _, node := range g.Files {
		g.extractEdges(node)
	}

	return g, nil
}
```

**兩段式的理由**：第一段邊 parse 邊 append，slice 可能重新分配 underlying array，之前取的 `*FileNode` 指標會失效。第一段收斂後才取指標，保證穩定。這是 Go slice 常見的踩坑。

如果用 `[]*FileNode`（指標 slice）就沒這問題，但對這個情境 `[]FileNode` 空間效率較好。兩種都 OK，選一種就要注意對應的陷阱。

## L1：連結有效性（outbound 走訪）

最簡單的 graph query：對每個 edge，檢查 target 是否存在。

```go
// scripts/mdtools/internal/mdcards/l1.go
func checkL1LinkValidity(g *Graph) []report.Violation {
	var out []report.Violation
	for _, edge := range g.Edges {
		if TargetExists(edge.Target) {
			continue
		}
		out = append(out, report.Violation{
			Path:  edge.SourcePath,
			Line:  edge.SourceLine,
			Rule:  "L1-broken-link",
			Level: report.LevelError,
			Message: fmt.Sprintf(
				"broken link %q: target not found", edge.Destination,
			),
		})
	}
	return out
}
```

`TargetExists` 試兩個候選路徑 — `{target}.md` 跟 `{target}/_index.md`，因為 Hugo 的 URL routing 對 content page 跟 section page 一視同仁：

```go
func TargetExists(target string) bool {
	for _, cand := range []string{target + ".md", filepath.Join(target, "_index.md")} {
		if info, err := os.Stat(cand); err == nil && !info.IsDir() {
			return true
		}
	}
	return false
}
```

## L2：orphan 偵測（inbound 反查）

「每張卡片至少被一篇非卡片文章引用」— 這是反向查詢：對每張卡片，看它的 `inbound` 有沒有來自「非卡片檔」的 edge。

```go
// scripts/mdtools/internal/mdcards/l2.go
func checkL2Orphans(g *Graph, cardsRoot string) []report.Violation {
	inboundNonCard := map[string]int{}
	for _, edge := range g.Edges {
		targetMd := edge.Target + ".md"
		if !isCardPath(targetMd, cardsRoot) || isSectionIndex(targetMd) {
			continue
		}
		if isCardPath(edge.SourcePath, cardsRoot) {
			continue // card-to-card 不算
		}
		inboundNonCard[targetMd]++
	}

	var out []report.Violation
	for _, fn := range g.Files {
		if !isCardPath(fn.Path, cardsRoot) || isSectionIndex(fn.Path) {
			continue
		}
		if inboundNonCard[fn.Path] > 0 {
			continue
		}
		out = append(out, report.Violation{
			Path:    fn.Path,
			Rule:    "L2-orphan-card",
			Level:   report.LevelWarn,
			Message: "card has no inbound link from non-card content",
		})
	}
	return out
}
```

**設計取捨**：

- **Card-to-card 不算 inbound**：依 spec，卡片應被「教學文章」引用證明使用場景；卡片互連只證明概念網路，不證明實用。
- **Warn 而非 error**：orphan 是**內容覆蓋率訊號**，不是格式錯誤；新卡片剛建時不該被擋 commit。
- **_index.md 排除**：section page 不是 card。

## L4：AST 跟 Graph 混用

這條規則複雜：「卡片的首段跟『概念位置』section 都要各有至少一個鄰卡連結」。要用 graph 抓候選，再用 AST 精確判讀在哪個 paragraph / section 內。

```go
// scripts/mdtools/internal/mdcards/l4.go
func checkL4K4Structure(g *Graph, cardsRoot, conceptHeadingTitle string) []report.Violation {
	var out []report.Violation
	for _, fn := range g.Files {
		if !isCardPath(fn.Path, cardsRoot) || isSectionIndex(fn.Path) {
			continue
		}

		firstPara := firstBodyParagraph(fn.AST)
		if !subtreeHasCardLink(firstPara, fn.Path, cardsRoot) {
			out = append(out, report.Violation{
				Path:    fn.Path,
				Rule:    "L4-first-paragraph-no-card-link",
				Level:   report.LevelWarn,
				Message: "opening paragraph should link to an adjacent card",
			})
		}

		section := headingSection(fn.AST, conceptHeadingTitle, fn.Src)
		if len(section) == 0 {
			out = append(out, report.Violation{
				Path:    fn.Path,
				Rule:    "L4-missing-concept-position",
				Level:   report.LevelWarn,
				Message: "card missing 概念位置 section",
			})
			continue
		}
		if !sectionHasCardLink(section, fn.Path, cardsRoot) {
			out = append(out, report.Violation{...})
		}
	}
	return out
}
```

兩個 helper 展示 graph 跟 AST 的交界：

- `firstBodyParagraph(doc)` 用 AST 走第一個 Paragraph 節點（document 的第一個 top-level child）。
- `subtreeHasCardLink(node, sourcePath, cardsRoot)` 用 `ast.Walk` 在該節點下找所有 Link，再用 `resolveTarget` 判斷是不是指向卡片。

**為什麼用 AST 而不是行號範圍**：Hugo content 的卡片結構多樣，首段可能跨多行；用 `paragraph.Lines()` 也能拿到 byte range，但還要處理 list item、table row 這類邊界。直接走 AST 子樹是最穩定的做法。

## 反向索引的設計擴充：slug-based 啟發式

`mdtools migrate fix-links` 要處理「broken link 但作者其實想連到某個存在的檔案，只是路徑寫錯」。這需要**額外一個 slug 反向索引**：

```go
// scripts/mdtools/internal/mdmigrate/fixlinks.go
func buildSlugIndexes(g *mdcards.Graph) (primary, normalized map[string][]string) {
	primary = make(map[string][]string)
	normalized = make(map[string][]string)
	for _, fn := range g.Files {
		base := filepath.Base(fn.Path)
		var slug, target string
		if base == "_index.md" {
			parent := filepath.Dir(fn.Path)
			slug = filepath.Base(parent)
			target = parent
		} else {
			slug = strings.TrimSuffix(base, ".md")
			target = strings.TrimSuffix(fn.Path, ".md")
		}
		primary[slug] = append(primary[slug], target)
		if norm := sectionPrefixRe.ReplaceAllString(slug, ""); norm != slug && norm != "" {
			normalized[norm] = append(normalized[norm], target)
		}
	}
	return primary, normalized
}
```

查詢時走多層啟發式：

1. **精確 slug 命中**（`broker` → `content/backend/knowledge-cards/broker`）
2. **數字前綴 normalized 命中**（`03-cpython-internals` 找不到 → 試 `cpython-internals` → 命中 `04-cpython-internals`）
3. **卡片優先**（多個 candidate 時選 `knowledge-cards/` 下的）
4. **同頂層子目錄優先**（source 在 `content/go/...` 時選 `content/go/` 下的 candidate）

這四層啟發式把 143 個 multi-candidate 收斂到 0 個 ambiguous。**啟發式的層層疊加是 static analysis 工具常見 pattern** — 寫過 linter、LSP、refactoring tool 的人都會在類似的決策樹花時間。

## Parse 成本的實務控制

跨檔分析一次要 parse 幾百個檔案。幾個優化：

- **只 parse 一次**：Graph 建好後 L1 / L2 / L4 共用。呼叫端不該重建 Graph。
- **concurrent parse（選擇性）**：`mdtools` 目前單執行緒 parse ~400 檔案 < 1 秒，沒必要並發。若檔案過萬，用 `golang.org/x/sync/errgroup` + worker pool fan out。
- **避免記憶體持有**：Graph 的 `FileNode.Src` 跟 `AST` 都持有 reference。如果 GC 壓力敏感，做完 L1-L4 後顯式 `g = nil` 或分段釋放。blog 這個規模沒必要。

## 常見陷阱

### Slice append 失效的指標

上面提過 — 邊 append 邊取指標會炸。BuildGraph 的兩段式是標準修法。

### filepath.Rel 在 root 外的 panic

```go
rel, err := filepath.Rel("/foo", "/bar")  // 不會 panic，回傳 "../bar"
rel, err := filepath.Rel("foo", "../bar") // err != nil
```

跨 repo root 的 rel 路徑會回 error。graph 的 target resolution 要接住這個 error。

### Symlink 的走訪

`filepath.WalkDir` 預設**不跟隨 symlink**。這對 blog repo OK（沒 symlink）；但對其他 repo（例如 monorepo 有 symlink 指到 sibling package）要用 `filepath.Walk` 或自己實作。mdtools 不處理這個情境。

### Hugo 的 URL 路由細節

`../broker/` 從 `content/backend/knowledge-cards/_index.md` 出發，Hugo 解析成 `content/backend/knowledge-cards/broker`（也就是 sibling card 的 URL）。從 `content/backend/knowledge-cards/acme-automation.md` 出發，同樣的 `../broker/` 卻解析成 `content/backend/broker`（錯誤，broker 不在 backend 直屬）。這是因為 Hugo 把**內容頁 URL dir 當成「slug 的 URL 資料夾」**，不是「檔案所在的資料夾」。做 target resolution 時要注意這一點，參考 `resolveTarget()` 的實作。

## 擴充路徑

- **Ingest commit history**：把 git commit 的時序資訊加進 graph，抓「這張卡片連結了一個之前存在但被刪掉的檔案」。需要整合 `go-git`。
- **Parallel parse**：大型 monorepo 的 lint 可用 worker pool 並行 parse。用 channel 把 parse 結果丟回 main，注意 goldmark context 不跨 goroutine。
- **Graph visualization**：把 graph 輸出成 Graphviz DOT 或 Mermaid，給作者看「這張卡片的 backlinks 是什麼」。有助於規劃內容修訂。

## 下一步

[9.5 工具決策的 tripwire](../tool-decision-tripwire/) 跳出實作，看「什麼時候該從 regex 升級到 AST、什麼時候該從 Python 換到 Go」的決策方法。
