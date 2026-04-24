package mdcards

import (
	"fmt"

	"blog/scripts/mdtools/internal/report"
)

// checkL1LinkValidity walks every edge in the graph and flags those
// whose target does not resolve to a real file on disk.
//
// Hugo renders from content/** at build time, so a broken link shows
// up as 404 for readers. Catching these at commit time turns a class
// of silent content rot into a fast fail.
func checkL1LinkValidity(g *Graph) []report.Violation {
	var out []report.Violation
	for _, edge := range g.Edges {
		if TargetExists(edge.Target) {
			continue
		}
		out = append(out, report.Violation{
			Path:  edge.SourcePath,
			Line:  edge.SourceLine,
			Rule:  "L1-broken-link",
			Level: report.LevelError,
			Message: fmt.Sprintf(
				"broken link %q: target not found (tried %s.md and %s/_index.md)",
				edge.Destination, edge.Target, edge.Target,
			),
		})
	}
	return out
}
