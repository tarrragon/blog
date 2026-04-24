package mdlint

import (
	"path/filepath"
	"strings"

	"blog/scripts/mdtools/internal/report"
	"blog/scripts/mdtools/internal/rules"
)

// checkFrontMatter validates the YAML front matter block against the
// schema in rules.Config.FrontMatter. It does not use a full YAML
// parser — top-level keys are extracted with a simple line scan, which
// covers all patterns observed in blog content as of 2026-04-24.
//
// Tiered schema:
//   - Global required fields: error if missing (every .md).
//   - Recommended fields: warn if missing (non-card paths only).
//   - Card required fields: error if missing (content/backend/knowledge-cards/**).
//   - Disallowed fields: warn if present (anywhere).
func checkFrontMatter(path string, lines []string, cfg rules.FrontMatterRules, cardsRoot string) []report.Violation {
	// No lines: treat as missing front matter.
	if len(lines) == 0 {
		return []report.Violation{{
			Path:    path,
			Line:    1,
			Rule:    "front-matter-missing",
			Level:   report.LevelError,
			Message: "missing YAML front matter (expected `---` block at file start)",
		}}
	}

	// Front matter must open at line 1.
	if strings.TrimSpace(lines[0]) != "---" {
		return []report.Violation{{
			Path:    path,
			Line:    1,
			Rule:    "front-matter-missing",
			Level:   report.LevelError,
			Message: "missing YAML front matter (expected `---` block at file start)",
		}}
	}

	// Find closing `---`.
	closeIdx := -1
	for i := 1; i < len(lines); i++ {
		if strings.TrimSpace(lines[i]) == "---" {
			closeIdx = i
			break
		}
	}
	if closeIdx < 0 {
		return []report.Violation{{
			Path:    path,
			Line:    1,
			Rule:    "front-matter-unclosed",
			Level:   report.LevelError,
			Message: "YAML front matter block is not closed with `---`",
		}}
	}

	// Extract top-level keys.
	present := map[string]bool{}
	for i := 1; i < closeIdx; i++ {
		if key := topLevelYAMLKey(lines[i]); key != "" {
			present[key] = true
		}
	}

	var out []report.Violation
	isCard := isStrictCardPath(path, cardsRoot)
	isIndex := filepath.Base(path) == "_index.md"

	// Required fields. Precedence: card > index > global.
	// Cards have the strictest requirement set; section index pages
	// relax `date` because they're Hugo list landing pages, not content.
	required := cfg.GlobalRequired
	switch {
	case isCard:
		required = cfg.CardRequired
	case isIndex:
		required = cfg.IndexRequired
	}
	for _, k := range required {
		if !present[k] {
			out = append(out, report.Violation{
				Path:    path,
				Line:    1,
				Rule:    "front-matter-required",
				Level:   report.LevelError,
				Message: "missing required field: " + k,
			})
		}
	}

	// Recommended fields — warn only. Skipped on card paths because
	// card-tier requirements already subsume the recommended set.
	if !isCard {
		for _, k := range cfg.Recommended {
			if !present[k] {
				out = append(out, report.Violation{
					Path:    path,
					Line:    1,
					Rule:    "front-matter-recommended",
					Level:   report.LevelWarn,
					Message: "recommended field not set: " + k,
				})
			}
		}
	}

	// Disallowed fields.
	for _, k := range cfg.Disallowed {
		if present[k] {
			out = append(out, report.Violation{
				Path:    path,
				Line:    1,
				Rule:    "front-matter-disallowed",
				Level:   report.LevelWarn,
				Message: "field explicitly disallowed: " + k,
			})
		}
	}

	return out
}

// topLevelYAMLKey extracts the key from a top-level YAML mapping line.
// Returns "" for indented lines (nested values), comments, list items,
// or malformed lines. Good enough for presence checks on the shallow
// front matter we use in blog content.
func topLevelYAMLKey(line string) string {
	if strings.HasPrefix(line, "#") {
		return ""
	}
	// Must not be indented — indentation means nested value or list item.
	if len(line) > 0 && (line[0] == ' ' || line[0] == '\t') {
		return ""
	}
	colon := strings.Index(line, ":")
	if colon <= 0 {
		return ""
	}
	key := line[:colon]
	for _, r := range key {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z',
			r >= '0' && r <= '9', r == '_', r == '-':
		default:
			return ""
		}
	}
	return key
}

// isStrictCardPath reports whether path falls under cardsRoot and is
// not an `_index.md` section page (section pages don't carry the same
// card-tier schema requirements).
func isStrictCardPath(path, cardsRoot string) bool {
	if cardsRoot == "" {
		return false
	}
	slash := filepath.ToSlash(path)
	root := strings.TrimSuffix(filepath.ToSlash(cardsRoot), "/") + "/"
	if !strings.Contains(slash, root) {
		return false
	}
	if filepath.Base(path) == "_index.md" {
		return false
	}
	return true
}
