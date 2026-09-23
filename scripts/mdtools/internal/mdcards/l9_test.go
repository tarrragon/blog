package mdcards

import (
	"sort"
	"strings"
	"testing"

	"blog/scripts/mdtools/internal/report"
)

// weightPage renders a file whose front matter carries the given weight
// line verbatim ("" means no weight field). The body also holds a
// `weight: 0` inside a fenced block, so a check that reads the whole file
// instead of the front matter would disagree with this fixture.
func weightPage(line string) []byte {
	var b strings.Builder
	b.WriteString("---\ntitle: \"t\"\ndate: 2026-09-23\n")
	if line != "" {
		b.WriteString(line + "\n")
	}
	b.WriteString("---\n\nprose\n\n```yaml\nweight: 0\n```\n")
	return []byte(b.String())
}

// weightGraphOf builds a graph in sorted path order, as the production
// walker does; ranging the map directly would hide order-dependence.
func weightGraphOf(files map[string]string) *Graph {
	paths := make([]string, 0, len(files))
	for p := range files {
		paths = append(paths, p)
	}
	sort.Strings(paths)
	g := &Graph{}
	for _, p := range paths {
		g.Files = append(g.Files, FileNode{Path: p, Src: weightPage(files[p])})
	}
	return g
}

func TestCheckL9WeightZero(t *testing.T) {
	cases := []struct {
		name      string
		files     map[string]string
		wantPaths []string
		wantScope string
	}{
		{
			name:  "positive and negative weights are silent",
			files: map[string]string{"content/a/x.md": "weight: 1", "content/a/y.md": "weight: -1", "content/a/z.md": "weight: 10"},
		},
		{
			name:  "no weight field is silent",
			files: map[string]string{"content/a/x.md": ""},
		},
		{
			name:  "weight 0 only inside the body is silent",
			files: map[string]string{"content/a/x.md": "weight: 3"},
		},
		{
			name:      "a page with weight 0 is an error",
			files:     map[string]string{"content/a/x.md": "weight: 0", "content/a/y.md": "weight: 1"},
			wantPaths: []string{"content/a/x.md"},
			wantScope: "sibling pages",
		},
		{
			name:      "a section index with weight 0 is an error",
			files:     map[string]string{"content/a/_index.md": "weight: 0"},
			wantPaths: []string{"content/a/_index.md"},
			wantScope: "sibling sections",
		},
		{
			name:      "other spellings of zero are caught",
			files:     map[string]string{"content/a/p.md": "weight: 00", "content/a/q.md": "weight: -0", "content/a/r.md": "weight:0  ", "content/a/s.md": "weight: 100"},
			wantPaths: []string{"content/a/p.md", "content/a/q.md", "content/a/r.md"},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := checkL9WeightZero(weightGraphOf(tc.files))
			if len(got) != len(tc.wantPaths) {
				t.Fatalf("got %d violations, want %d: %+v", len(got), len(tc.wantPaths), got)
			}
			for i, v := range got {
				if v.Path != tc.wantPaths[i] {
					t.Errorf("violation %d path = %s, want %s", i, v.Path, tc.wantPaths[i])
				}
				if v.Level != report.LevelError {
					t.Errorf("violation %d level = %v, want error", i, v.Level)
				}
				if tc.wantScope != "" && !strings.Contains(v.Message, tc.wantScope) {
					t.Errorf("message %q lacks %q", v.Message, tc.wantScope)
				}
			}
		})
	}
}

// A section whose pages are all weighted except one weight-0 page is mixed
// to Hugo, so L5 has to see it as mixed too.
func TestCheckL5TreatsWeightZeroAsUnset(t *testing.T) {
	g := weightGraphOf(map[string]string{
		"content/a/_index.md": "",
		"content/a/first.md":  "weight: 0",
		"content/a/second.md": "weight: 1",
		"content/a/third.md":  "weight: 2",
	})
	got := checkL5SectionWeightConsistency(g, nil)
	if len(got) != 1 {
		t.Fatalf("got %d L5 violations, want 1: %+v", len(got), got)
	}
	if !strings.Contains(got[0].Message, "first.md") {
		t.Errorf("L5 should name first.md as the unweighted minority, got %q", got[0].Message)
	}

	allZero := weightGraphOf(map[string]string{
		"content/b/x.md": "weight: 0",
		"content/b/y.md": "weight: 0",
	})
	if got := checkL5SectionWeightConsistency(allZero, nil); len(got) != 0 {
		t.Errorf("a section with every page at weight 0 is uniformly unset, got %+v", got)
	}
}
