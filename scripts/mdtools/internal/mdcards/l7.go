package mdcards

import (
	"fmt"
	"path/filepath"
	"strings"
	"unicode"

	"github.com/yuin/goldmark/ast"

	"blog/scripts/mdtools/internal/report"
)

// checkL7Fragments flags links whose `#fragment` names no heading on the
// target page.
//
// L1 already guarantees the target file exists, and it deliberately stops
// there: resolveTarget drops everything after `#`. The consequence is that
// renaming a heading silently breaks every cross-file link pointing at it.
// The link still opens, the page still renders, and the reader lands at the
// top with no idea which section they were sent to — a misdirected
// reference, which is harder to notice than a dangling one because nothing
// looks wrong from either end.
//
// Heading IDs are computed the way Hugo's github-style auto-ID does it:
// keep unicode letters, digits and `_` (lowercased), turn whitespace and
// existing hyphens into `-`, drop everything else without leaving a
// separator behind. Repeated heading text on one page gets `-1`, `-2` and
// so on in document order.
//
// Anchors inside fenced code blocks never reach here — they are not Link
// nodes — so documentation examples are exempt for free.
//
// Known limit: anchors that belong to no heading (footnote back-references,
// theme-injected IDs) are unknown to this check and would be reported. None
// exist in the repo today; if one appears, the fix is to teach this check
// about that generator rather than to weaken the rule.
//
// Reported at error level. The stock was zero when the rule landed, so
// there is no debt to work down — anything this reports is new breakage,
// and letting it merge is exactly the silent rot the rule exists to stop.
func checkL7Fragments(g *Graph) []report.Violation {
	headings := map[string]map[string]bool{} // file path → heading ID set

	idsFor := func(path string) map[string]bool {
		if ids, ok := headings[path]; ok {
			return ids
		}
		fn := g.FindFile(path)
		if fn == nil {
			headings[path] = nil
			return nil
		}
		ids := headingIDs(fn.AST, fn.Src)
		headings[path] = ids
		return ids
	}

	var out []report.Violation
	for _, edge := range g.Edges {
		if edge.Fragment == "" {
			continue
		}

		// Resolve the fragment's owning file. Hugo routes a slug to either
		// form, so try the content page before the section index.
		var ids map[string]bool
		var found bool
		for _, candidate := range []string{
			edge.Target + ".md",
			filepath.Join(edge.Target, "_index.md"),
		} {
			if got := idsFor(filepath.ToSlash(candidate)); got != nil {
				ids, found = got, true
				break
			}
		}
		// A target outside the walked roots has no heading index; L1 owns
		// whether the file itself should exist.
		if !found {
			continue
		}

		if ids[strings.ToLower(edge.Fragment)] {
			continue
		}
		out = append(out, report.Violation{
			Path:  edge.SourcePath,
			Line:  edge.SourceLine,
			Rule:  "L7-broken-fragment",
			Level: report.LevelError,
			Message: fmt.Sprintf(
				"link %q points at no heading on the target page; "+
					"anchor on a heading that exists, or drop the fragment",
				edge.Destination),
		})
	}
	return out
}

// headingIDs returns the set of anchor IDs a page exposes, matching Hugo's
// github-style auto-ID including the `-N` suffix for repeated text.
func headingIDs(root ast.Node, src []byte) map[string]bool {
	ids := map[string]bool{}
	seen := map[string]int{}

	ast.Walk(root, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
		if !entering {
			return ast.WalkContinue, nil
		}
		h, ok := n.(*ast.Heading)
		if !ok {
			return ast.WalkContinue, nil
		}
		text := string(h.Text(src))

		// Hugo parses a trailing `{#custom-id}` as the heading's ID. The
		// shared parser has attribute parsing off, so the braces arrive as
		// literal text; register the explicit ID and drop it from the text
		// the auto-ID is computed from. Registering both keeps the check
		// correct whichever form a link uses.
		if id, rest, ok := explicitID(text); ok {
			ids[id] = true
			text = rest
		}

		base := anchorize(text)
		if base == "" {
			return ast.WalkContinue, nil
		}
		id := base
		if n := seen[base]; n > 0 {
			id = fmt.Sprintf("%s-%d", base, n)
		}
		seen[base]++
		ids[id] = true
		return ast.WalkContinue, nil
	})
	return ids
}

// explicitID splits a trailing `{#custom-id}` off heading text, returning
// the ID (lowercased, as Hugo emits it into the href) and the remaining
// text. ok is false when the heading carries no such attribute.
func explicitID(text string) (id, rest string, ok bool) {
	trimmed := strings.TrimRight(text, " \t")
	if !strings.HasSuffix(trimmed, "}") {
		return "", text, false
	}
	open := strings.LastIndex(trimmed, "{#")
	if open < 0 {
		return "", text, false
	}
	id = trimmed[open+2 : len(trimmed)-1]
	if id == "" || strings.ContainsAny(id, " \t{}#") {
		return "", text, false
	}
	return strings.ToLower(id), strings.TrimRight(trimmed[:open], " \t"), true
}

// anchorize converts heading text to its Hugo anchor ID.
func anchorize(s string) string {
	var b strings.Builder
	for _, r := range s {
		switch {
		case unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_':
			b.WriteRune(unicode.ToLower(r))
		case unicode.IsSpace(r) || r == '-':
			b.WriteRune('-')
		}
	}
	return b.String()
}
