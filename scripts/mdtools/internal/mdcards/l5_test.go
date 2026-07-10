package mdcards

import (
	"strings"
	"testing"

	"blog/scripts/mdtools/internal/report"
)

// page renders a minimal markdown file: front matter, then a body that
// deliberately also mentions `weight:` inside a fenced block.
func page(weighted bool) []byte {
	var b strings.Builder
	b.WriteString("---\ntitle: \"t\"\ndate: 2026-07-10\n")
	if weighted {
		b.WriteString("weight: 3\n")
	}
	b.WriteString("---\n\nprose\n\n```yaml\nweight: 999\n```\n")
	return []byte(b.String())
}

func graphOf(files map[string]bool) *Graph {
	g := &Graph{}
	for path, weighted := range files {
		g.Files = append(g.Files, FileNode{Path: path, Src: page(weighted)})
	}
	return g
}

func TestCheckL5SectionWeightConsistency(t *testing.T) {
	cases := []struct {
		name       string
		files      map[string]bool // path → carries weight
		exempt     []string
		wantCount  int
		wantPath   string
		wantSubstr string
	}{
		{
			name:      "every page weighted is coherent",
			files:     map[string]bool{"content/go/a.md": true, "content/go/b.md": true},
			wantCount: 0,
		},
		{
			name:      "no page weighted is coherent",
			files:     map[string]bool{"content/posts/a.md": false, "content/posts/b.md": false},
			wantCount: 0,
		},
		{
			name: "a mix splits the list and is reported once per section",
			files: map[string]bool{
				"content/report/_index.md": false,
				"content/report/a.md":      true,
				"content/report/b.md":      true,
				"content/report/c.md":      false,
			},
			wantCount: 1,
			// Anchored on the landing page: the fix belongs to the section,
			// not to any single file.
			wantPath:   "content/report/_index.md",
			wantSubstr: "c.md",
		},
		{
			name: "the minority is named even when it is the weighted side",
			files: map[string]bool{
				"content/record/_index.md": false,
				"content/record/pinned.md": true,
				"content/record/x.md":      false,
				"content/record/y.md":      false,
			},
			wantCount:  1,
			wantPath:   "content/record/_index.md",
			wantSubstr: "carry weight): pinned.md",
		},
		{
			name: "an exempt section stays silent",
			files: map[string]bool{
				"content/linux/tools/cli/pinned.md": true,
				"content/linux/tools/cli/x.md":      false,
			},
			exempt:    []string{"content/linux/tools/cli"},
			wantCount: 0,
		},
		{
			name: "exemption tolerates a trailing slash",
			files: map[string]bool{
				"content/linux/tools/cli/pinned.md": true,
				"content/linux/tools/cli/x.md":      false,
			},
			exempt:    []string{"content/linux/tools/cli/"},
			wantCount: 0,
		},
		{
			name: "sections are independent of one another",
			files: map[string]bool{
				"content/go/a.md":     true,
				"content/go/b.md":     true,
				"content/posts/a.md":  false,
				"content/report/a.md": true,
				"content/report/b.md": false,
			},
			wantCount: 1,
			wantPath:  "content/report/a.md", // no _index.md here
		},
		{
			// A section index carrying its own weight orders the section
			// among its siblings; it must not count as a page of the
			// section it heads.
			name: "weighted _index.md does not make the section mixed",
			files: map[string]bool{
				"content/posts/_index.md": true,
				"content/posts/a.md":      false,
				"content/posts/b.md":      false,
			},
			wantCount: 0,
		},
		{
			// The whole point of running on the full tree: a partial file
			// set must never look inconsistent.
			name:      "a single-file view never false-positives",
			files:     map[string]bool{"content/report/a.md": true},
			wantCount: 0,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := checkL5SectionWeightConsistency(graphOf(tc.files), tc.exempt)
			if len(got) != tc.wantCount {
				t.Fatalf("got %d violation(s), want %d: %+v", len(got), tc.wantCount, got)
			}
			if tc.wantCount == 0 {
				return
			}
			v := got[0]
			if v.Path != tc.wantPath {
				t.Errorf("anchored on %q, want %q", v.Path, tc.wantPath)
			}
			if v.Level != report.LevelWarn {
				t.Errorf("level = %v, want warn (a pinned page is a legitimate idiom)", v.Level)
			}
			if v.Rule != "L5-section-weight-consistency" {
				t.Errorf("rule = %q", v.Rule)
			}
			if tc.wantSubstr != "" && !strings.Contains(v.Message, tc.wantSubstr) {
				t.Errorf("message %q does not name the minority %q", v.Message, tc.wantSubstr)
			}
		})
	}
}

// frontMatterOf must not see a `weight:` that lives in the body, or a
// prose example would silently satisfy the check.
func TestFrontMatterOf(t *testing.T) {
	cases := []struct {
		name string
		src  string
		want string
	}{
		{"fields between the fences", "---\ntitle: t\nweight: 1\n---\nbody\n", "title: t\nweight: 1\n"},
		{"body is excluded", "---\ntitle: t\n---\n\n```yaml\nweight: 9\n```\n", "title: t\n"},
		{"no front matter at all", "# heading\n\nweight: 9\n", ""},
		{"unterminated front matter", "---\ntitle: t\n", ""},
		{"empty input", "", ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := string(frontMatterOf([]byte(tc.src))); got != tc.want {
				t.Errorf("frontMatterOf(%q) = %q, want %q", tc.src, got, tc.want)
			}
		})
	}
}

func TestFrontMatterOfIgnoresBodyWeight(t *testing.T) {
	src := page(false) // no weight field, but the body mentions weight: 999
	if weightFieldRe.Match(frontMatterOf(src)) {
		t.Error("a `weight:` inside a fenced code block was mistaken for a front-matter field")
	}
	if !weightFieldRe.Match(frontMatterOf(page(true))) {
		t.Error("a real `weight:` field was not detected")
	}
}

func TestSummarize(t *testing.T) {
	names := []string{"e.md", "a.md", "d.md", "b.md", "c.md"}
	if got, want := summarize(names, 5), "a.md, b.md, c.md, d.md, e.md"; got != want {
		t.Errorf("summarize sorted-under-limit = %q, want %q", got, want)
	}
	if got, want := summarize(names, 2), "a.md, b.md, and 3 more"; got != want {
		t.Errorf("summarize over-limit = %q, want %q", got, want)
	}
}
