package mdcards

import (
	"fmt"
	"regexp"

	"blog/scripts/mdtools/internal/report"
)

// weightZeroRe matches a front-matter `weight` whose integer value is zero,
// in any of the spellings YAML accepts for it (0, 00, +0, -0).
var weightZeroRe = regexp.MustCompile(`(?m)^weight:[ \t]*[+-]?0+[ \t]*$`)

// hasEffectiveWeight reports whether a front matter carries a weight that
// Hugo will actually sort by. Hugo treats `weight: 0` exactly like an absent
// field, so a zero is "unset" here too.
func hasEffectiveWeight(fm []byte) bool {
	return weightFieldRe.Match(fm) && !weightZeroRe.Match(fm)
}

// checkL9WeightZero flags every page and section index whose front matter
// sets `weight: 0`.
//
// Hugo reads weight 0 as "no weight", so the page sorts after every weighted
// sibling instead of first. The value is what a chapter numbered 00 or 1.0
// naturally gets, which is how it keeps coming back: in one sweep 38 pages
// and 8 section indexes carried it, each one sitting at the bottom of its
// list while reading as the opening chapter in the source.
//
// Reported at error level. Unlike the mixed sections L5 warns about, a zero
// weight has no legitimate reading — pinning a page first takes a low
// positive or a negative weight, and a section meant to sort by date
// carries no weight at all.
//
// Section indexes are included because their weight orders the section
// among its sibling sections, and L5 only compares pages inside one
// section, so nothing else sees them.
func checkL9WeightZero(g *Graph) []report.Violation {
	var out []report.Violation
	for _, fn := range g.Files {
		if !weightZeroRe.Match(frontMatterOf(fn.Src)) {
			continue
		}
		scope := "its sibling pages"
		if isSectionIndex(fn.Path) {
			scope = "its sibling sections"
		}
		out = append(out, report.Violation{
			Path:  fn.Path,
			Line:  0,
			Rule:  "L9-weight-zero-is-unset",
			Level: report.LevelError,
			Message: fmt.Sprintf(
				"`weight: 0` is unset to Hugo (checked against v0.148), so this sorts after every weighted one among %s. "+
					"Add 1 to every weight >= 0 in the same list, or give this one a negative weight.",
				scope),
		})
	}
	return out
}
