package mdlint

import (
	"github.com/yuin/goldmark/ast"

	"blog/scripts/mdtools/internal/astutil"
	"blog/scripts/mdtools/internal/report"
)

// checkEmphasisAsHeading implements MD036 via AST — flag any paragraph
// whose sole inline child is a Strong (`**text**`) or Emph (`*text*`)
// node. Those "decorative heading" paragraphs break TOC, screen
// readers, and anchor links because Hugo doesn't treat them as
// structural headings. Authors should use `###` / `####` instead.
//
// AST is necessary here — regex can approximate the pattern on a
// single line but cannot reliably distinguish a standalone decorative
// paragraph from a paragraph that begins with an emphasis phrase.
func checkEmphasisAsHeading(path string, data []byte) []report.Violation {
	parser := astutil.NewParser()
	doc := parser.Parse(data)

	var out []report.Violation
	ast.Walk(doc, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
		if !entering {
			return ast.WalkContinue, nil
		}
		para, ok := n.(*ast.Paragraph)
		if !ok {
			return ast.WalkContinue, nil
		}
		if !paragraphIsSoleEmphasis(para) {
			return ast.WalkContinue, nil
		}
		out = append(out, report.Violation{
			Path:    path,
			Line:    nodeStartLine(para, data),
			Rule:    "MD036-emphasis-as-heading",
			Level:   report.LevelWarn,
			Message: "paragraph contains only bold/italic text; use a proper `###` heading instead (breaks TOC and anchors)",
		})
		return ast.WalkSkipChildren, nil
	})
	return out
}

// paragraphIsSoleEmphasis reports whether para's only inline child is a
// Strong or Emph node. A single trailing whitespace text child (rare in
// practice but possible) doesn't disqualify.
func paragraphIsSoleEmphasis(para *ast.Paragraph) bool {
	first := para.FirstChild()
	if first == nil {
		return false
	}
	// Must be Strong or Emph.
	switch first.(type) {
	case *ast.Emphasis:
	default:
		return false
	}
	// No following meaningful content.
	for sib := first.NextSibling(); sib != nil; sib = sib.NextSibling() {
		if txt, ok := sib.(*ast.Text); ok {
			seg := txt.Segment
			if seg.Stop-seg.Start == 0 {
				continue
			}
			return false
		}
		return false
	}
	return true
}
