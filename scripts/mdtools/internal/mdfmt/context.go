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

// LineContext holds per-line skip flags produced by AnalyzeLines.
// Skip[i] is true when line i sits inside a region that line-based rules
// must leave alone (YAML front matter, fenced code block).
type LineContext struct {
	Skip []bool
}

// AnalyzeLines scans lines once and populates the context. The scan is
// O(n) and allocation-light; callers can re-run it after any pass that
// changes line count.
func AnalyzeLines(lines []string) LineContext {
	skip := make([]bool, len(lines))
	inFrontMatter := false
	frontMatterOpened := false
	var fence string // "" when not inside fenced code; otherwise holds the marker used to open

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

		// Fenced code block: any `` ``` `` or `~~~` at line start opens;
		// matching marker (same char, len >= opening) closes.
		if fence == "" {
			if open := detectOpenFence(trimmed); open != "" {
				fence = open
				skip[i] = true
				continue
			}
		} else {
			skip[i] = true
			if isClosingFence(trimmed, fence) {
				fence = ""
			}
			continue
		}
	}

	return LineContext{Skip: skip}
}

// detectOpenFence returns the fence marker ("```" or "~~~") if trimmed
// starts with one of them. Language hints after the marker are allowed
// and don't affect detection.
func detectOpenFence(trimmed string) string {
	for _, marker := range []string{"```", "~~~"} {
		if strings.HasPrefix(trimmed, marker) {
			return marker
		}
	}
	return ""
}

// isClosingFence reports whether trimmed is a closing fence matching the
// given opening marker. A closing fence consists only of the marker char,
// repeated at least len(marker) times, with optional surrounding space.
func isClosingFence(trimmed, opening string) bool {
	if len(trimmed) < len(opening) {
		return false
	}
	if trimmed == opening {
		return true
	}
	// Allow longer runs of the same fence char, e.g. "````" closes "```".
	marker := opening[0]
	for i := 0; i < len(trimmed); i++ {
		if trimmed[i] != marker {
			return false
		}
	}
	return len(trimmed) >= len(opening)
}
