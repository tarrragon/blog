package mdcards

import (
	"sort"
	"strings"
	"testing"

	"blog/scripts/mdtools/internal/report"
)

// slugPage renders a file whose front matter carries the given slug (empty
// string means the field is absent). The body deliberately also contains a
// `slug:` line inside a fenced block, so a check that greps the whole file
// instead of the front matter would disagree with this fixture.
func slugPage(slug string) []byte {
	var b strings.Builder
	b.WriteString("---\ntitle: \"t\"\ndate: 2026-08-03\n")
	if slug != "" {
		b.WriteString("slug: \"" + slug + "\"\n")
	}
	b.WriteString("---\n\nprose\n\n```yaml\nslug: \"from-the-body\"\n```\n")
	return []byte(b.String())
}

// slugGraphOf builds a graph in sorted path order; the production walker
// hands over sorted paths, and ranging a map here would hide any
// order-dependence in the check.
func slugGraphOf(files map[string]string) *Graph {
	paths := make([]string, 0, len(files))
	for p := range files {
		paths = append(paths, p)
	}
	sort.Strings(paths)

	g := &Graph{}
	for _, p := range paths {
		g.Files = append(g.Files, FileNode{Path: p, Src: slugPage(files[p])})
	}
	return g
}

func TestCheckL8SlugFilenameAlignment(t *testing.T) {
	cases := []struct {
		name       string
		files      map[string]string // path → slug ("" means no slug field)
		wantCount  int
		wantPath   string
		wantSubstr string
	}{
		{
			name:      "slug spelling its own filename is silent",
			files:     map[string]string{"content/macos/macos_apfs.md": "macos_apfs"},
			wantCount: 0,
		},
		{
			name:      "no slug field at all is silent",
			files:     map[string]string{"content/macos/macos_apfs.md": ""},
			wantCount: 0,
		},
		{
			// The case that motivated the rule: underscored filename,
			// hyphenated slug. Hugo serves the hyphens, links use the
			// underscores, L1 sees a file that exists and says nothing.
			name:       "hyphenated slug against an underscored filename is reported",
			files:      map[string]string{"content/macos/macos_apfs.md": "macos-apfs"},
			wantCount:  1,
			wantPath:   "content/macos/macos_apfs.md",
			wantSubstr: `slug "macos-apfs" disagrees with filename "macos_apfs"`,
		},
		{
			name:       "the message names both repair routes",
			files:      map[string]string{"content/x/a.md": "b"},
			wantCount:  1,
			wantPath:   "content/x/a.md",
			wantSubstr: `Set slug to "a", or rename the file to "b.md"`,
		},
		{
			// _index.md's slug names the section it heads, so comparing it
			// against the literal string `_index` would report every
			// section landing page in the repo.
			name:      "_index.md is exempt",
			files:     map[string]string{"content/macos/_index.md": "macos"},
			wantCount: 0,
		},
		{
			name: "each offending page is reported independently",
			files: map[string]string{
				"content/a/one.md":   "one-x",
				"content/a/two.md":   "two",
				"content/b/three.md": "three-y",
			},
			wantCount: 2,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := checkL8SlugFilenameAlignment(slugGraphOf(tc.files))
			if len(got) != tc.wantCount {
				t.Fatalf("got %d violation(s), want %d: %+v", len(got), tc.wantCount, got)
			}
			if tc.wantCount == 0 {
				return
			}
			v := got[0]
			if tc.wantPath != "" && v.Path != tc.wantPath {
				t.Errorf("anchored on %q, want %q", v.Path, tc.wantPath)
			}
			if v.Level != report.LevelError {
				t.Errorf("level = %v, want error (an inbound link 404s, and no other check sees it)", v.Level)
			}
			if v.Rule != "L8-slug-filename-alignment" {
				t.Errorf("rule = %q", v.Rule)
			}
			if tc.wantSubstr != "" && !strings.Contains(v.Message, tc.wantSubstr) {
				t.Errorf("message %q lacks %q", v.Message, tc.wantSubstr)
			}
		})
	}
}

// A `slug:` in the body must never satisfy or trigger the check — every
// fixture above carries one inside a fenced block for exactly this reason.
func TestL8IgnoresBodySlug(t *testing.T) {
	g := &Graph{Files: []FileNode{
		{Path: "content/x/from-the-body.md", Src: slugPage("")},
	}}
	if got := checkL8SlugFilenameAlignment(g); len(got) != 0 {
		t.Errorf("a `slug:` inside a fenced block was read as front matter: %+v", got)
	}

	// And the mirror: a body slug must not mask a real disagreement.
	g2 := &Graph{Files: []FileNode{
		{Path: "content/x/a.md", Src: slugPage("b")},
	}}
	if got := checkL8SlugFilenameAlignment(g2); len(got) != 1 {
		t.Errorf("front-matter slug was not read, got %d violations", len(got))
	}
}

// The report points at the slug field, not at the top of the file.
func TestL8ReportsTheSlugLine(t *testing.T) {
	// ---(1) title(2) date(3) slug(4)
	g := &Graph{Files: []FileNode{{Path: "content/x/a.md", Src: slugPage("b")}}}
	got := checkL8SlugFilenameAlignment(g)
	if len(got) != 1 {
		t.Fatalf("got %d violations, want 1", len(got))
	}
	if got[0].Line != 4 {
		t.Errorf("Line = %d, want 4 (the slug field)", got[0].Line)
	}
}

// Unquoted and single-quoted slugs are the same fact as a double-quoted
// one; a regex that only understood double quotes would let the other two
// spellings through unchecked.
func TestL8AcceptsEveryQuotingStyle(t *testing.T) {
	for _, fm := range []string{
		"---\nslug: b\n---\n",
		"---\nslug: 'b'\n---\n",
		"---\nslug: \"b\"\n---\n",
		"---\nslug:   b   \n---\n",
	} {
		g := &Graph{Files: []FileNode{{Path: "content/x/a.md", Src: []byte(fm)}}}
		got := checkL8SlugFilenameAlignment(g)
		if len(got) != 1 {
			t.Errorf("front matter %q produced %d violations, want 1", fm, len(got))
			continue
		}
		if !strings.Contains(got[0].Message, `slug "b"`) {
			t.Errorf("front matter %q parsed the value wrong: %s", fm, got[0].Message)
		}
	}
}

// Walk order must not change what is reported.
func TestL8IsOrderIndependent(t *testing.T) {
	files := map[string]string{
		"content/x/a.md": "a-x",
		"content/x/b.md": "b",
		"content/x/c.md": "c-y",
	}
	forward := checkL8SlugFilenameAlignment(slugGraphOf(files))

	paths := []string{"content/x/c.md", "content/x/b.md", "content/x/a.md"}
	g := &Graph{}
	for _, p := range paths {
		g.Files = append(g.Files, FileNode{Path: p, Src: slugPage(files[p])})
	}
	backward := checkL8SlugFilenameAlignment(g)

	if len(forward) != 2 || len(backward) != 2 {
		t.Fatalf("expected two violations each, got %d and %d", len(forward), len(backward))
	}
	seen := func(vs []report.Violation) []string {
		var ps []string
		for _, v := range vs {
			ps = append(ps, v.Path)
		}
		sort.Strings(ps)
		return ps
	}
	f, b := seen(forward), seen(backward)
	for i := range f {
		if f[i] != b[i] {
			t.Errorf("reported set depends on walk order: %v vs %v", f, b)
		}
	}
}
