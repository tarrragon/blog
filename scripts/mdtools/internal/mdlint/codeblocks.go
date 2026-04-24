package mdlint

import (
	"strings"

	"blog/scripts/mdtools/internal/mdfmt"
	"blog/scripts/mdtools/internal/report"
)

// checkCodeBlockLanguage implements MD040: every fenced code block must
// declare a language after the opening fence. Missing language hints
// break syntax highlighting and screen-reader metadata.
//
// Plain text output (terminal logs, diff snippets) uses `text` or
// `plain`; shell examples use `bash` even for zsh-isms; config files
// use their actual format (`toml`, `yaml`, `json`, `ini`).
func checkCodeBlockLanguage(path string, lines []string, ctx mdfmt.LineContext) []report.Violation {
	var out []report.Violation
	for i, line := range lines {
		if !ctx.FenceOpen[i] {
			continue
		}
		trimmed := strings.TrimLeft(line, " \t")
		// Skip the fence marker run.
		cursor := 0
		for cursor < len(trimmed) && (trimmed[cursor] == '`' || trimmed[cursor] == '~') {
			cursor++
		}
		rest := strings.TrimSpace(trimmed[cursor:])
		if rest != "" {
			continue
		}
		out = append(out, report.Violation{
			Path:    path,
			Line:    i + 1,
			Rule:    "MD040-no-language",
			Level:   report.LevelWarn,
			Message: "fenced code block missing language hint; use `text` for plain output",
		})
	}
	return out
}
