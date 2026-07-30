package mdcards

import (
	"sort"
	"strings"
	"testing"

	"blog/scripts/mdtools/internal/report"
)

// linkGraph builds a graph from an explicit file list plus explicit edges,
// so a test states exactly which index links which card. Paths arrive
// sorted, matching the production walker.
func linkGraph(paths []string, edges map[string][]string) *Graph {
	ordered := append([]string(nil), paths...)
	sort.Strings(ordered)

	g := &Graph{byPath: map[string]*FileNode{}}
	for _, p := range ordered {
		g.Files = append(g.Files, FileNode{Path: p, Src: page(true)})
	}
	for i := range g.Files {
		g.byPath[g.Files[i].Path] = &g.Files[i]
	}

	// Sort the sources too: ranging a map directly would randomise edge
	// order and hide any ordering dependency in the check.
	sources := make([]string, 0, len(edges))
	for src := range edges {
		sources = append(sources, src)
	}
	sort.Strings(sources)
	for _, src := range sources {
		for _, target := range edges[src] {
			g.Edges = append(g.Edges, Edge{SourcePath: src, Target: target})
		}
	}
	return g
}

const cardsRoot = "content/backend/knowledge-cards"

func TestCheckL6IndexRegistration(t *testing.T) {
	cases := []struct {
		name       string
		paths      []string
		edges      map[string][]string
		wantPaths  []string
		wantSubstr string
	}{
		{
			name: "a listed card is silent",
			paths: []string{
				cardsRoot + "/_index.md",
				cardsRoot + "/broker.md",
			},
			edges: map[string][]string{
				cardsRoot + "/_index.md": {cardsRoot + "/broker"},
			},
			wantPaths: nil,
		},
		{
			name: "an unlisted card is reported",
			paths: []string{
				cardsRoot + "/_index.md",
				cardsRoot + "/broker.md",
				cardsRoot + "/replay.md",
			},
			edges: map[string][]string{
				cardsRoot + "/_index.md": {cardsRoot + "/broker"},
			},
			wantPaths:  []string{cardsRoot + "/replay.md"},
			wantSubstr: cardsRoot + "/_index.md",
		},
		{
			// The case that motivated the rule: chapters cite the card, so
			// L2 is satisfied, yet the directory index never lists it.
			name: "links from articles do not register a card",
			paths: []string{
				"content/backend/07-security/chapter.md",
				cardsRoot + "/_index.md",
				cardsRoot + "/workload-identity.md",
			},
			edges: map[string][]string{
				"content/backend/07-security/chapter.md": {cardsRoot + "/workload-identity"},
			},
			wantPaths: []string{cardsRoot + "/workload-identity.md"},
		},
		{
			// Card-to-card links are how the web is woven; they say nothing
			// about whether the list a reader browses includes the card.
			name: "a link from a sibling card does not register it",
			paths: []string{
				cardsRoot + "/_index.md",
				cardsRoot + "/broker.md",
				cardsRoot + "/replay.md",
			},
			edges: map[string][]string{
				cardsRoot + "/_index.md": {cardsRoot + "/broker"},
				cardsRoot + "/broker.md": {cardsRoot + "/replay"},
			},
			wantPaths: []string{cardsRoot + "/replay.md"},
		},
		{
			// A parent module page listing a card is not the card index.
			name: "a link from a parent module index does not register it",
			paths: []string{
				"content/backend/_index.md",
				cardsRoot + "/_index.md",
				cardsRoot + "/replay.md",
			},
			edges: map[string][]string{
				"content/backend/_index.md": {cardsRoot + "/replay"},
			},
			wantPaths: []string{cardsRoot + "/replay.md"},
		},
		{
			// Large card sets may group into subdirectories; the nearest
			// index inside the root counts, so grouping is not a violation.
			name: "an index inside a subdirectory registers its cards",
			paths: []string{
				cardsRoot + "/_index.md",
				cardsRoot + "/transport/_index.md",
				cardsRoot + "/transport/broker.md",
			},
			edges: map[string][]string{
				cardsRoot + "/transport/_index.md": {cardsRoot + "/transport/broker"},
			},
			wantPaths: nil,
		},
		{
			// Without a landing page there is nothing to register in; the
			// front-matter and L5 checks own that situation.
			name: "a root with no index page stays silent",
			paths: []string{
				cardsRoot + "/broker.md",
				cardsRoot + "/replay.md",
			},
			wantPaths: nil,
		},
		{
			name: "cards outside the root are none of this root's business",
			paths: []string{
				cardsRoot + "/_index.md",
				cardsRoot + "/broker.md",
				"content/ddd/knowledge-cards/aggregate.md",
			},
			edges: map[string][]string{
				cardsRoot + "/_index.md": {cardsRoot + "/broker"},
			},
			wantPaths: nil,
		},
		{
			name: "every unlisted card gets its own violation, sorted",
			paths: []string{
				cardsRoot + "/_index.md",
				cardsRoot + "/replay.md",
				cardsRoot + "/broker.md",
				cardsRoot + "/dlq.md",
			},
			edges: map[string][]string{
				cardsRoot + "/_index.md": {cardsRoot + "/dlq"},
			},
			wantPaths: []string{cardsRoot + "/broker.md", cardsRoot + "/replay.md"},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := checkL6IndexRegistration(linkGraph(tc.paths, tc.edges), cardsRoot)
			gotPaths := make([]string, 0, len(got))
			for _, v := range got {
				gotPaths = append(gotPaths, v.Path)
			}
			if strings.Join(gotPaths, "|") != strings.Join(tc.wantPaths, "|") {
				t.Fatalf("violations on %v, want %v", gotPaths, tc.wantPaths)
			}
			for _, v := range got {
				if v.Level != report.LevelWarn {
					t.Errorf("level = %v, want warn (registration is a coverage signal)", v.Level)
				}
				if v.Rule != "L6-card-not-in-index" {
					t.Errorf("rule = %q", v.Rule)
				}
				if tc.wantSubstr != "" && !strings.Contains(v.Message, tc.wantSubstr) {
					t.Errorf("message %q does not name the index to edit", v.Message)
				}
			}
		})
	}
}

// An empty root must not make every file in the tree a violation.
func TestCheckL6EmptyRootIsSilent(t *testing.T) {
	g := linkGraph([]string{cardsRoot + "/_index.md", cardsRoot + "/broker.md"}, nil)
	if got := checkL6IndexRegistration(g, ""); len(got) != 0 {
		t.Errorf("empty cards root produced %d violation(s)", len(got))
	}
}

// The result must not depend on the order the walker hands over files or
// the order edges were extracted.
func TestCheckL6IsOrderIndependent(t *testing.T) {
	paths := []string{
		cardsRoot + "/_index.md",
		cardsRoot + "/broker.md",
		cardsRoot + "/dlq.md",
		cardsRoot + "/replay.md",
	}
	edges := map[string][]string{
		cardsRoot + "/_index.md": {cardsRoot + "/dlq"},
	}

	build := func(order []string) *Graph {
		g := &Graph{byPath: map[string]*FileNode{}}
		for _, p := range order {
			g.Files = append(g.Files, FileNode{Path: p, Src: page(true)})
		}
		for i := range g.Files {
			g.byPath[g.Files[i].Path] = &g.Files[i]
		}
		for src, targets := range edges {
			for _, target := range targets {
				g.Edges = append(g.Edges, Edge{SourcePath: src, Target: target})
			}
		}
		return g
	}

	forward := checkL6IndexRegistration(build(paths), cardsRoot)
	reversed := append([]string(nil), paths...)
	sort.Sort(sort.Reverse(sort.StringSlice(reversed)))
	backward := checkL6IndexRegistration(build(reversed), cardsRoot)

	if len(forward) != 2 || len(backward) != 2 {
		t.Fatalf("expected two violations each, got %d and %d", len(forward), len(backward))
	}
	for i := range forward {
		if forward[i].Path != backward[i].Path {
			t.Errorf("order %d differs: %q vs %q", i, forward[i].Path, backward[i].Path)
		}
	}
}
