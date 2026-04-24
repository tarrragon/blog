package mdcards

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/yuin/goldmark/ast"

	"blog/scripts/mdtools/internal/report"
)

// checkL4K4Structure verifies that each knowledge card satisfies the
// K4 requirement from .codex/briefs/knowledge-cards.md:
//
//	"卡片首段與「概念位置」段各至少 1 個相鄰卡片連結"
//
// Implementation uses the goldmark AST rather than regex because the
// rule depends on paragraph membership and heading-section scope —
// both of which are awkward to express on raw lines (see
// content/posts/what-is-ast.md for the rationale).
func checkL4K4Structure(g *Graph, cardsRoot, conceptHeadingTitle string) []report.Violation {
	if cardsRoot == "" {
		return nil
	}
	var out []report.Violation

	for _, fn := range g.Files {
		if !isCardPath(fn.Path, cardsRoot) || isSectionIndex(fn.Path) {
			continue
		}

		// First paragraph of the body.
		firstPara := firstBodyParagraph(fn.AST)
		if firstPara == nil {
			out = append(out, report.Violation{
				Path:    fn.Path,
				Line:    0,
				Rule:    "L4-missing-first-paragraph",
				Level:   report.LevelWarn,
				Message: "card has no opening paragraph before the first heading",
			})
		} else if !subtreeHasCardLink(firstPara, fn.Path, cardsRoot) {
			out = append(out, report.Violation{
				Path:    fn.Path,
				Line:    nodeLine(firstPara, fn.Src),
				Rule:    "L4-first-paragraph-no-card-link",
				Level:   report.LevelWarn,
				Message: "opening paragraph should link to at least one adjacent card",
			})
		}

		// "概念位置" section body.
		section := headingSection(fn.AST, conceptHeadingTitle, fn.Src)
		if len(section) == 0 {
			out = append(out, report.Violation{
				Path:    fn.Path,
				Line:    0,
				Rule:    "L4-missing-concept-position",
				Level:   report.LevelWarn,
				Message: fmt.Sprintf("card is missing the %q section", conceptHeadingTitle),
			})
			continue
		}
		if !sectionHasCardLink(section, fn.Path, cardsRoot) {
			out = append(out, report.Violation{
				Path:  fn.Path,
				Line:  nodeLine(section[0], fn.Src),
				Rule:  "L4-concept-position-no-card-link",
				Level: report.LevelWarn,
				Message: fmt.Sprintf(
					"%q section should link to at least one adjacent card",
					conceptHeadingTitle,
				),
			})
		}
	}

	return out
}

// firstBodyParagraph returns the first Paragraph child of the document
// root, or nil. Heading-first layouts skip the lookup.
func firstBodyParagraph(doc ast.Node) ast.Node {
	for child := doc.FirstChild(); child != nil; child = child.NextSibling() {
		if _, ok := child.(*ast.Paragraph); ok {
			return child
		}
	}
	return nil
}

// headingSection returns the list of top-level nodes under a heading
// whose text matches the given title (case-sensitive substring). The
// section runs from the heading's next sibling until the next heading
// of level <= heading.Level.
func headingSection(doc ast.Node, title string, src []byte) []ast.Node {
	var out []ast.Node
	for child := doc.FirstChild(); child != nil; child = child.NextSibling() {
		h, ok := child.(*ast.Heading)
		if !ok {
			continue
		}
		text := strings.TrimSpace(string(h.Text(src)))
		if !strings.Contains(text, title) {
			continue
		}
		// Collect subsequent siblings until an equal-or-shallower heading.
		for sibling := h.NextSibling(); sibling != nil; sibling = sibling.NextSibling() {
			if next, ok := sibling.(*ast.Heading); ok && next.Level <= h.Level {
				break
			}
			out = append(out, sibling)
		}
		return out
	}
	return nil
}

// subtreeHasCardLink reports whether any descendant Link under node
// points to a different card file.
func subtreeHasCardLink(node ast.Node, sourcePath, cardsRoot string) bool {
	found := false
	ast.Walk(node, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
		if !entering || found {
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
		target := resolveTarget(sourcePath, dest)
		if target == "" {
			return ast.WalkContinue, nil
		}
		for _, candidate := range []string{target + ".md", filepath.Join(target, "_index.md")} {
			if isCardPath(candidate, cardsRoot) && !isSectionIndex(candidate) && candidate != sourcePath {
				found = true
				return ast.WalkStop, nil
			}
		}
		return ast.WalkContinue, nil
	})
	return found
}

// sectionHasCardLink is subtreeHasCardLink applied across a slice of
// nodes (used for heading-bounded sections).
func sectionHasCardLink(nodes []ast.Node, sourcePath, cardsRoot string) bool {
	for _, n := range nodes {
		if subtreeHasCardLink(n, sourcePath, cardsRoot) {
			return true
		}
	}
	return false
}
