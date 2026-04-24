---
title: "9.3 AST 驅動的 idempotent 文字改寫"
date: 2026-04-24
description: "用 AST 定位位置、用 line-based 或 byte-level 改寫；設計多條 rule 的執行順序；--check 跟 --fix 如何共用邏輯"
weight: 3
---

AST 驅動文字改寫的核心契約是 **[idempotent](/go/glossary/#idempotent-文字改寫)**：對同一輸入跑一次或十次結果相同。這個契約讓工具能安全地接到 [pre-commit hook](/go/glossary/#pre-commit-hook-定位)（每次 commit 都跑不會累積漂移）、能分段除錯（改一條 rule 不會破壞其他 rule 的輸出）、能用 `--check` 跟 `--fix` 共用同一套邏輯（差別只在要不要寫檔）。`gofmt`、`prettier`、`ruff fix` 這類工具在工程界立信譽的基礎就是冪等。

設計一個冪等的改寫流水線有三個配合層：**策略選擇**（AST round-trip / byte surgical / 混合）、**rule 鏈順序**（每條 rule 的輸出要是下一條的合法輸入）、**context 重算紀律**（行數變動後索引要重建）。本章依序展開這三層，並以 `mdtools fmt --fix` 的 `applyAll` 為 concrete instance。

## 改檔的三種策略

把 AST 資訊轉成檔案修改有三條路：

| 策略                          | 做法                                                                                        | 優點                              | 缺點                                                         |
| ----------------------------- | ------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------ |
| AST 重新 serialize            | parse → 在 AST 上改 → 用 renderer 寫回 markdown                                             | 概念乾淨；不會遺漏結構            | goldmark 的 renderer **不保證 round-trip 精確**；diff 會爆炸 |
| 位置導向 byte 改寫            | 用 AST 找違規節點的 offset，外科手術式字串編輯                                              | diff 只影響違規處，保留原格式細節 | byte offset 要嚴謹管理；規則越多越囉嗦                       |
| 混合：line-based + AST-guided | 行內能解決的（空行、trailing newline）用逐行處理；複雜的（URL 縮短、結構重構）用 AST 找位置 | 取兩者之長；簡單規則簡單寫        | 要明確劃分哪條 rule 用哪種策略                               |

mdtools 選第三條。純 AST round-trip 在長尾場景（nested fence、特殊 escape）會產出跟 source 不等價的 markdown；純 byte-offset 讓 MD047（trailing newline）這類微瑣事變得囉嗦。混合讓每條 rule 在它最自然的層級解決。

設計原則：**能用 line-based 就用，AST 只在真的需要語意判讀時才上**。

## Rule 鏈的結構

`mdtools fmt` 的 `applyAll` 是條流水線：

```go
// scripts/mdtools/internal/mdfmt/fixer.go
func applyAll(data []byte, cfg rules.Config) []byte {
	lines := splitLines(data)

	// MD026 — 標題結尾標點，line-preserving
	if cfg.Headings.ForbidTrailingPunct {
		ctx := AnalyzeLines(lines)
		lines = FixHeadingTrailingPunct(lines, ctx, cfg.Headings.ForbiddenTrailingPunct)
	}

	// MD022 — 標題前後空行，line-count changing
	if cfg.Headings.RequireBlankLines {
		ctx := AnalyzeLines(lines)
		lines = FixHeadingBlankLines(lines, ctx)
	}

	// MD031 — fenced code block 前後空行
	if cfg.CodeBlocks.RequireBlankLinesAround {
		ctx := AnalyzeLines(lines)
		lines = FixFencedCodeBlankLines(lines, ctx)
	}

	// MD032 — 列表前後空行
	ctx := AnalyzeLines(lines)
	lines = FixListBlankLines(lines, ctx)

	// MD060 — 表格對齊
	ctx = AnalyzeLines(lines)
	lines = FixTables(lines, ctx, cfg.Tables)

	// MD034 — 裸 URL 縮短
	ctx = AnalyzeLines(lines)
	lines = FixBareURLs(lines, ctx, cfg.URLs)

	out := joinLines(lines)
	out = EnsureTrailingNewline(out) // MD047
	return out
}
```

幾個**設計決策**值得拆開看。

### 順序決定結果

Rule 順序有明確的依賴判準：**每條 rule 的輸出應該是下一條 rule 的合法輸入**。

- MD026 先跑：它改標題內容、不改行數，後面 rule 的行號不會位移。
- MD022 / MD031 / MD032 緊接著：這些都 insert blank lines，會改行數；但它們彼此之間不衝突（heading ≠ fence ≠ list）。
- MD060 表格對齊在 URL 縮短之前：讓表格先成為可解析結構，URL rule 才能正確判斷「這個 URL 在表格 cell 內」。
- MD034 URL 縮短最後：URL 變短會讓表格欄寬變化；但因為 MD060 已經做過對齊，後續工具會再跑一次 fmt --fix 重新對齊。這個「跑兩次才穩定」的特性是可接受的，因為 fmt --fix 本來就冪等。
- MD047 trailing newline 在 byte 層做，最後一步。

### 每條 rule 重新 analyze context

`AnalyzeLines(lines)` 在每個會變行數的 rule 之前重跑。為什麼：

- 上一條 rule 可能把 fence 或 front matter 位置推後。
- Context 裡的 `Skip[]`、`FenceOpen[]`、`FenceClose[]` 都是按行索引儲存。
- 行數改變 → 索引失效 → 必須重算。

成本是 O(N)，對 500-行檔案微秒級。在整體 pipeline 中可忽略。

### Line-based rule 本體範例

以 MD022（標題前後空行）為例：

```go
// scripts/mdtools/internal/mdfmt/rules.go
func FixHeadingBlankLines(lines []string, ctx LineContext) []string {
	if len(lines) == 0 {
		return lines
	}
	out := make([]string, 0, len(lines)+8)
	for i, line := range lines {
		isHdr := !ctx.Skip[i] && isHeadingLine(line)

		if isHdr && len(out) > 0 && !isBlank(out[len(out)-1]) {
			out = append(out, "")
		}
		out = append(out, line)
		if isHdr && i+1 < len(lines) && !isBlank(lines[i+1]) {
			out = append(out, "")
		}
	}
	return out
}
```

關鍵 idempotent 技巧：

- **判斷「上一行不是 blank 就插」而非「永遠插」**。已經插過 blank 的情況下，第二次跑會看到 blank，跳過，結果相同。
- **out 是新 slice**，不改動原 lines。函式純粹。
- **look-ahead 看原 lines**，避免剛插的 blank 讓邏輯誤判下一輪。

## AST-guided rule 範例：MD034 URL 縮短

這條 rule 用 AST 找「哪些 text 是 link 之外的」，行內用 regex + mask 處理：

```go
// scripts/mdtools/internal/mdfmt/urls.go
func rewriteBareURLsInLine(line string, cfg rules.URLRules, idPatterns []*regexp.Regexp) string {
	masked := collectMaskedRanges(line) // [...](/go/09-tooling-and-analysis/ast-idempotent-rewriting/...) / <...> / `...` 的位置
	matches := bareURLRe.FindAllStringIndex(line, -1)
	if len(matches) == 0 {
		return line
	}
	var b strings.Builder
	cursor := 0
	for _, m := range matches {
		start, end := m[0], m[1]
		end = trimURLTrailPunct(line, start, end)
		b.WriteString(line[cursor:start])
		if inMasked(masked, start) {
			b.WriteString(line[start:end]) // 已在 link / code span / 角括號內
		} else {
			rawURL := line[start:end]
			display := shortenURL(rawURL, cfg, idPatterns)
			fmt.Fprintf(&b, "[%s](/go/09-tooling-and-analysis/ast-idempotent-rewriting/%s)", display, rawURL)
		}
		cursor = end
	}
	b.WriteString(line[cursor:])
	return b.String()
}
```

這裡的 **混合精神**：

- AST 不直接改檔，只提供「這行的哪些 byte 範圍是 existing link / code span」的判讀（實際上這段用了 regex 模擬；真正嚴謹時會改用 AST 定位）。
- 真的改寫走字串層級，保留原格式。
- 已在 link 內的 URL 不再包第二層 — `inMasked` 檢查防止 double-wrap，這也是 **idempotent 關鍵**：第二次跑，所有 URL 都已經在 masked range 裡，跳過。

## `--check` 跟 `--fix` 共用邏輯

一個常見反 pattern 是：`check` 模式重寫一次邏輯「看會不會改」，`fix` 模式真的改。兩套邏輯一旦漂移，誤報或漏報就出現。

正確做法是**共用同一個 FormatFile，然後比對結果**：

```go
// scripts/mdtools/internal/mdfmt/fixer.go
func FormatFile(path string, cfg rules.Config) (FixResult, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return FixResult{}, err
	}
	fixed := applyAll(data, cfg)
	return FixResult{Path: path, Original: data, Fixed: fixed}, nil
}

// check / fix 都呼叫 FormatFile，只差在怎麼處理結果
func (r FixResult) Changed() bool {
	return !bytes.Equal(r.Original, r.Fixed)
}
```

子命令層處理差異：

```go
// cmd/fmt.go 簡化版
result, _ := mdfmt.FormatFile(path, cfg)
if !result.Changed() {
	return // 沒改動，跳過
}
if *fix {
	os.WriteFile(path, result.Fixed, 0o644)
} else {
	fmt.Printf("would fix: %s\n", path)
}
```

**check 跟 fix 跑一模一樣的 rule chain，只是其中一個寫檔、另一個回報**。這個結構讓兩個模式的行為**保證一致**。

## Idempotent 的驗證方式

工具宣稱冪等，測試要驗證：

```go
func TestFormatIdempotent(t *testing.T) {
	inputs, _ := filepath.Glob("testdata/*.md")
	cfg := rules.Default()
	for _, in := range inputs {
		data, _ := os.ReadFile(in)
		once := applyAll(data, cfg)
		twice := applyAll(once, cfg)
		if !bytes.Equal(once, twice) {
			t.Errorf("%s: not idempotent (applied twice != once)", in)
		}
	}
}
```

生產環境的 pre-commit hook 本質上每次 commit 都在驗證冪等：

1. 作者寫 commit → `fmt --fix` 跑過 → re-stage
2. 如果邏輯不冪等，下次作者改同檔案，可能又會被改回/改去
3. 使用者很快會發現「為什麼這個工具一直來回改我的檔案」

冪等是 pre-commit 的信譽基礎。

## 常見陷阱

### Rule 之間互相抵消

```text
Rule A: 移除行尾空白
Rule B: 把每個 heading 後面補空格到 60 欄
```

A 跟 B 串起來會永遠改來改去。寫 rule 時要想「其他 rule 會對我的輸出做什麼」。

### 讀 src 跟改 src 用不同的 byte slice

在迴圈中一邊掃 `data`、一邊 append 到 `out`，中間忘了切換視角。建議永遠遵循 `(原 lines, 新 out)` 兩個名字，迴圈體只 look-back 到 `out[len(out)-1]` 或 look-ahead 到 `lines[i+1]`，絕不在同一時段既讀又寫同一 slice。

### Trailing newline 的邊界

```go
bytes.TrimRight(data, "\r\n")      // 去掉全部
return append(data, '\n')           // 加一個
```

空檔案要特別處理 — 加了 `\n` 就變非空。mdtools 的作法是：

```go
if len(data) == 0 {
	return data
}
```

空檔保持空。

### Regex-based URL 偵測的邊界

Go 的 RE2 沒有 lookbehind，無法用 regex 直接寫「URL 不在 `](` 後面」。解法是先掃 mask（link span、angle bracket、code span），再跑 URL regex，match 結果對照 mask 決定是否替換。`collectMaskedRanges` 就是這個模式。

## 擴充路徑

- **Rule dry-run diff**：把每條 rule 單獨跑一遍，輸出每條 rule 改了哪幾個檔案。debug 為什麼某檔案被改時用得到。
- **Configurable rule disabling**：把 rule 開關改成 front matter 級別（`mdtools-disable: MD026`），讓個別檔案能 opt-out。
- **Rule 可程式化插入**：把 `applyAll` 改成「讀 config → 產生 rule list → iterate」，讓新 rule 不用改 fixer.go 而是註冊進來。

## 下一步

[9.4 跨檔案圖分析](/go/09-tooling-and-analysis/cross-file-graph-analysis/) 離開 single-file 世界，看 `mdtools cards` 怎麼建整個 repo 的 link graph 跑反向查詢。
