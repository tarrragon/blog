package mdcards

import (
	"blog/scripts/mdtools/internal/report"
	"blog/scripts/mdtools/internal/rules"
)

// Check runs the enabled card-level checks and returns all violations.
// Callers typically feed these into a report.Reporter for stable output.
//
// The graph is built once and reused across L1/L2/L4. Parse cost is
// dominated by goldmark + file I/O; for ~300 markdown files this takes
// well under a second on a warm disk.
func Check(roots []string, cfg rules.Config) ([]report.Violation, error) {
	g, err := BuildGraph(roots)
	if err != nil {
		return nil, err
	}

	var out []report.Violation
	if cfg.Cards.CheckLinkValidity {
		out = append(out, checkL1LinkValidity(g)...)
	}
	if cfg.Cards.CheckOrphans {
		for _, root := range cfg.Cards.CardsRoots {
			out = append(out, checkL2Orphans(g, root)...)
		}
	}
	if cfg.Cards.CheckK4StructureLinks {
		for _, root := range cfg.Cards.CardsRoots {
			out = append(out, checkL4K4Structure(g, root, cfg.Cards.K4ConceptPositionTitle)...)
		}
	}
	if cfg.Cards.CheckSectionWeightConsistency {
		out = append(out, checkL5SectionWeightConsistency(g, cfg.Cards.WeightExemptSections)...)
	}
	return out, nil
}
