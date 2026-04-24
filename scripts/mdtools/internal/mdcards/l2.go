package mdcards

import (
	"path/filepath"
	"strings"

	"blog/scripts/mdtools/internal/report"
)

// checkL2Orphans flags knowledge cards with no inbound edge from
// non-card content. The goal is to catch cards that exist in isolation
// — they may be structurally fine but nobody finds them via teaching
// articles, so they drift out of use.
//
// Card-to-card links do not count toward preventing orphan status,
// per spec §5: the inbound edge must come from non-card content
// (articles in content/backend/, content/go/, etc.).
//
// Reported at warn level — orphans are a content-coverage signal,
// not a formatting failure, and Task 2 (knowledge-web-expansion) is
// explicitly still filling these in.
func checkL2Orphans(g *Graph, cardsRoot string) []report.Violation {
	if cardsRoot == "" {
		return nil
	}
	cardsRoot = filepath.ToSlash(cardsRoot)

	// Compute inbound-from-non-card count per card file.
	inboundNonCard := map[string]int{}
	for _, edge := range g.Edges {
		targetCandidates := []string{edge.Target + ".md", filepath.Join(edge.Target, "_index.md")}
		for _, tc := range targetCandidates {
			if !isCardPath(tc, cardsRoot) || isSectionIndex(tc) {
				continue
			}
			if isCardPath(edge.SourcePath, cardsRoot) {
				continue
			}
			inboundNonCard[tc]++
		}
	}

	var out []report.Violation
	for _, fn := range g.Files {
		if !isCardPath(fn.Path, cardsRoot) || isSectionIndex(fn.Path) {
			continue
		}
		if inboundNonCard[fn.Path] > 0 {
			continue
		}
		out = append(out, report.Violation{
			Path:    fn.Path,
			Line:    0,
			Rule:    "L2-orphan-card",
			Level:   report.LevelWarn,
			Message: "card has no inbound link from non-card content; add at least one reference from a teaching article",
		})
	}
	return out
}

// isCardPath reports whether p falls under the cards root.
func isCardPath(p, cardsRoot string) bool {
	p = filepath.ToSlash(p)
	root := strings.TrimSuffix(cardsRoot, "/") + "/"
	return strings.Contains(p, root)
}

// isSectionIndex reports whether p is a Hugo `_index.md` section page.
// Section index pages are not subject to card-tier requirements.
func isSectionIndex(p string) bool {
	return filepath.Base(p) == "_index.md"
}
