package mdlint

import (
	"strings"

	"blog/scripts/mdtools/internal/mdfmt"
	"blog/scripts/mdtools/internal/report"
)

// checkProseTabs implements MD010 with code-blocks exempt: tab
// characters in prose lines are flagged; tabs inside fenced code
// blocks and YAML front matter are allowed (Go source code uses
// tabs by gofmt convention and it must remain copy-pastable).
//
// LineContext.Skip is true for front-matter interiors and fenced
// code block interiors. Fence marker lines themselves (opening /
// closing ```) have Skip=true too, so this rule naturally avoids
// them as well.
func checkProseTabs(path string, lines []string, ctx mdfmt.LineContext) []report.Violation {
	var out []report.Violation
	for i, line := range lines {
		if ctx.Skip[i] {
			continue
		}
		if strings.ContainsRune(line, '\t') {
			out = append(out, report.Violation{
				Path:    path,
				Line:    i + 1,
				Rule:    "MD010-prose-tab",
				Level:   report.LevelWarn,
				Message: "tab character in prose; use spaces (fenced code blocks are exempt)",
			})
		}
	}
	return out
}
