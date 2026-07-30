package mdcards

import (
	"fmt"
	"path/filepath"
	"sort"

	"blog/scripts/mdtools/internal/report"
)

// checkL6IndexRegistration flags cards that exist on disk but are absent
// from their own directory index.
//
// This asks a different question from L2, and the difference is the whole
// reason the check exists. L2 asks "does a teaching article link to this
// card" — it deliberately discounts links whose source is itself a card,
// which includes the directory's `_index.md`. So a card can satisfy L2 in
// full (several chapters cite it) while never appearing in the list a
// reader browses. Reachable by link and reachable by browsing are two
// properties, and until now only the first had a rule.
//
// The gap accumulates because the registering action has no trigger.
// Creating a card while writing a chapter has an obvious motive — that
// chapter needs to link it — whereas going back to add a row to the index
// changes nothing about the chapter's completeness. Every batch leaves a
// few behind, and nothing surfaces them.
//
// A card counts as registered when any section index inside the same cards
// root links to it. Accepting any index rather than only the root's own
// lets a large card set organise into subdirectories without tripping the
// check; requiring the source to sit inside the root keeps a stray link
// from a parent module page out of it.
//
// Reported at warn level. The message anchors on the card, following L2 —
// the edit happens in the index, but the card is the thing a reader cannot
// find, and naming it one-per-line is what makes the backlog countable.
func checkL6IndexRegistration(g *Graph, cardsRoot string) []report.Violation {
	if cardsRoot == "" {
		return nil
	}
	cardsRoot = filepath.ToSlash(cardsRoot)

	indexPath := filepath.ToSlash(filepath.Join(cardsRoot, "_index.md"))

	// A root with no landing page has no index to register in; L5 and the
	// front-matter tier checks own that case.
	if g.FindFile(indexPath) == nil {
		return nil
	}

	registered := map[string]bool{}
	for _, edge := range g.Edges {
		if !isCardPath(edge.SourcePath, cardsRoot) || !isSectionIndex(edge.SourcePath) {
			continue
		}
		// Hugo routes a slug to either form, so credit both.
		registered[filepath.ToSlash(edge.Target+".md")] = true
		registered[filepath.ToSlash(filepath.Join(edge.Target, "_index.md"))] = true
	}

	var unlisted []string
	for _, fn := range g.Files {
		path := filepath.ToSlash(fn.Path)
		if !isCardPath(path, cardsRoot) || isSectionIndex(path) {
			continue
		}
		if registered[path] {
			continue
		}
		unlisted = append(unlisted, path)
	}
	sort.Strings(unlisted)

	out := make([]report.Violation, 0, len(unlisted))
	for _, path := range unlisted {
		out = append(out, report.Violation{
			Path:  path,
			Line:  0,
			Rule:  "L6-card-not-in-index",
			Level: report.LevelWarn,
			Message: fmt.Sprintf(
				"card is absent from %s; readers browsing the card list cannot reach it. "+
					"Add a row for it, or delete the card if it has been superseded",
				indexPath),
		})
	}
	return out
}
