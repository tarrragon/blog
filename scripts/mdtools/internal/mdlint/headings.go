package mdlint

import (
	"fmt"
	"strings"

	"blog/scripts/mdtools/internal/mdfmt"
	"blog/scripts/mdtools/internal/report"
)

// checkH1Ban flags any H1 in the body. Hugo front matter `title` already
// produces H1, so a body H1 creates dual H1 and breaks semantic order.
// This enforces a stricter version of MD025.
func checkH1Ban(path string, lines []string, ctx mdfmt.LineContext) []report.Violation {
	var out []report.Violation
	for i, line := range lines {
		if ctx.Skip[i] {
			continue
		}
		level, _ := parseHeading(line)
		if level != 1 {
			continue
		}
		out = append(out, report.Violation{
			Path:    path,
			Line:    i + 1,
			Rule:    "MD025-no-body-h1",
			Level:   report.LevelError,
			Message: "H1 forbidden in body; Hugo front matter `title` already produces H1",
		})
	}
	return out
}

// checkHeadingDuplicates implements MD024 siblings_only: a heading must
// be unique among its siblings under the same parent heading. Duplicates
// across different parent chains are allowed (supports parallel
// structures like case-by-case chapters).
func checkHeadingDuplicates(path string, lines []string, ctx mdfmt.LineContext) []report.Violation {
	var out []report.Violation

	// parent[level] holds the heading text at each depth currently in scope.
	parent := [7]string{} // indices 1..6

	// seenAt[parentKey] maps child text -> 1-based line number of first use.
	seenAt := map[string]map[string]int{}

	for i, line := range lines {
		if ctx.Skip[i] {
			continue
		}
		level, text := parseHeading(line)
		if level == 0 {
			continue
		}

		parentKey := rootParentKey
		if level > 1 {
			parentKey = parent[level-1]
			if parentKey == "" {
				parentKey = rootParentKey
			}
		}

		children, ok := seenAt[parentKey]
		if !ok {
			children = map[string]int{}
			seenAt[parentKey] = children
		}
		if prev, dup := children[text]; dup {
			out = append(out, report.Violation{
				Path:  path,
				Line:  i + 1,
				Rule:  "MD024-siblings_only",
				Level: report.LevelError,
				Message: fmt.Sprintf(
					"duplicate heading %q under the same parent (first seen at line %d)",
					text, prev,
				),
			})
		} else {
			children[text] = i + 1
		}

		parent[level] = text
		// Clear deeper levels: entering a new level-N heading invalidates
		// level N+1..6 parents from the previous sibling.
		for l := level + 1; l <= 6; l++ {
			parent[l] = ""
		}
	}
	return out
}

// rootParentKey names the synthetic parent for top-level (H2 at document
// root) headings. Any non-empty string works — it just has to be
// distinct from any real heading text.
const rootParentKey = "\x00root"

// parseHeading returns the heading level (1..6) and trimmed text. Level
// 0 means the line is not an ATX heading. Closing hashes are stripped
// from the text (CommonMark §4.2).
func parseHeading(line string) (level int, text string) {
	trimmed := strings.TrimLeft(line, " ")
	// CommonMark: up to 3 leading spaces allowed before `#`.
	if len(line)-len(trimmed) > 3 {
		return 0, ""
	}
	if !strings.HasPrefix(trimmed, "#") {
		return 0, ""
	}
	for level < len(trimmed) && trimmed[level] == '#' {
		level++
	}
	if level < 1 || level > 6 {
		return 0, ""
	}
	// Empty heading: `##` alone.
	if level == len(trimmed) {
		return level, ""
	}
	// Must be followed by a space.
	if trimmed[level] != ' ' {
		return 0, ""
	}
	text = strings.TrimSpace(trimmed[level+1:])
	text = strings.TrimRight(text, "#")
	text = strings.TrimSpace(text)
	return level, text
}
