// Package mdfmt implements format normalization for mdtools fmt.
//
// Strategy is hybrid (per content/posts/mdtools-design.md): line-based
// processing for whitespace / newline rules (MD022 / MD031 / MD032 /
// MD047), line-based-with-context for MD026, and AST-guided for rules
// that need semantic understanding (MD034 URL shortening, MD036 bold
// heading detection — deferred to a later phase).
//
// Every line-based rule consumes a LineContext to avoid false positives
// inside front matter or fenced code blocks.
package mdfmt

import (
	"strings"
)

// LineContext holds per-line classification flags produced by AnalyzeLines.
//
//   - Skip[i]       — true when line i is in front matter or fenced code
//                     interior; standard line rules (heading detection,
//                     list detection) should leave it alone.
//   - FenceOpen[i]  — true when line i opens a fenced code block; used by
//                     MD031 to insert a blank line before the fence.
//   - FenceClose[i] — true when line i closes a fenced code block; used
//                     by MD031 to insert a blank line after the fence.
//
// Note: Skip is also true on FenceOpen/FenceClose lines. The two flag
// families are orthogonal — fence lines are both "skip for heading/list
// detection" and "the target of MD031".
type LineContext struct {
	Skip       []bool
	FenceOpen  []bool
	FenceClose []bool
}

// AnalyzeLines scans lines once and populates the context. The scan is
// O(n) and allocation-light; callers re-run it after any pass that
// changes line count.
func AnalyzeLines(lines []string) LineContext {
	skip := make([]bool, len(lines))
	fenceOpen := make([]bool, len(lines))
	fenceClose := make([]bool, len(lines))

	inFrontMatter := false
	frontMatterOpened := false
	var fence string // "" when outside; otherwise opening marker

	for i, line := range lines {
		trimmed := strings.TrimSpace(line)

		// Front matter: `---` as the very first line opens; next `---` closes.
		if !frontMatterOpened && i == 0 && trimmed == "---" {
			inFrontMatter = true
			frontMatterOpened = true
			skip[i] = true
			continue
		}
		if inFrontMatter {
			skip[i] = true
			if trimmed == "---" {
				inFrontMatter = false
			}
			continue
		}

		// Fenced code block.
		if fence == "" {
			if open := detectOpenFence(trimmed); open != "" {
				fence = open
				skip[i] = true
				fenceOpen[i] = true
				continue
			}
		} else {
			skip[i] = true
			if isClosingFence(trimmed, fence) {
				fenceClose[i] = true
				fence = ""
			}
			continue
		}
	}

	return LineContext{
		Skip:       skip,
		FenceOpen:  fenceOpen,
		FenceClose: fenceClose,
	}
}

// detectOpenFence returns the exact fence marker run at line start, or
// "" if trimmed does not open a fenced code block. The return value
// preserves the full run length so that isClosingFence can enforce
// CommonMark §4.5: a closing fence must be a run of the same char at
// least as long as the opening run. This is critical for nested fence
// content (e.g. a `` ``` `` block demonstrating `` ``` `` syntax inside
// a ```` ```` ```` wrapper).
func detectOpenFence(trimmed string) string {
	if len(trimmed) == 0 {
		return ""
	}
	ch := trimmed[0]
	if ch != '`' && ch != '~' {
		return ""
	}
	count := 0
	for count < len(trimmed) && trimmed[count] == ch {
		count++
	}
	if count < 3 {
		return ""
	}
	return trimmed[:count]
}

// isClosingFence reports whether trimmed is a valid closing fence for
// the given opening run. The closing fence must use the same char as
// opening and have a run length >= len(opening). Trailing language
// hints or any other non-fence chars invalidate a closing line.
func isClosingFence(trimmed, opening string) bool {
	if len(opening) == 0 || len(trimmed) < len(opening) {
		return false
	}
	ch := opening[0]
	for i := 0; i < len(trimmed); i++ {
		if trimmed[i] != ch {
			return false
		}
	}
	return true
}
