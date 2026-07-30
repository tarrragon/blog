package mdcards

import (
	"strings"
	"testing"

	"blog/scripts/mdtools/internal/astutil"
	"blog/scripts/mdtools/internal/report"
)

// docGraph parses real markdown, so the test exercises the same AST path
// production does — heading text extraction and link parsing included.
func docGraph(files map[string]string) *Graph {
	paths := make([]string, 0, len(files))
	for p := range files {
		paths = append(paths, p)
	}
	// Deterministic order: the walker hands over sorted paths.
	for i := 0; i < len(paths); i++ {
		for j := i + 1; j < len(paths); j++ {
			if paths[j] < paths[i] {
				paths[i], paths[j] = paths[j], paths[i]
			}
		}
	}

	parser := astutil.NewParser()
	g := &Graph{
		byPath:   map[string]*FileNode{},
		inbound:  map[string][]int{},
		outbound: map[string][]int{},
	}
	for _, p := range paths {
		src := []byte(files[p])
		g.Files = append(g.Files, FileNode{Path: p, AST: parser.Parse(src), Src: src})
	}
	for i := range g.Files {
		g.byPath[g.Files[i].Path] = &g.Files[i]
	}
	for _, fn := range g.Files {
		g.extractEdges(fn)
	}
	return g
}

func TestCheckL7Fragments(t *testing.T) {
	target := "## 升級路徑\n\n prose\n\n## 判讀流程\n\nprose\n"

	cases := []struct {
		name       string
		files      map[string]string
		wantCount  int
		wantSubstr string
	}{
		{
			name: "a fragment naming an existing heading is silent",
			files: map[string]string{
				"content/a/target.md": target,
				"content/a/source.md": "see [x](/a/target/#升級路徑)\n",
			},
			wantCount: 0,
		},
		{
			name: "a fragment naming no heading is reported",
			files: map[string]string{
				"content/a/target.md": target,
				"content/a/source.md": "see [x](/a/target/#升級流程)\n",
			},
			wantCount:  1,
			wantSubstr: "#升級流程",
		},
		{
			// The motivating case: the file still exists, so L1 is happy.
			name: "a link with no fragment is not this check's business",
			files: map[string]string{
				"content/a/target.md": target,
				"content/a/source.md": "see [x](/a/target/)\n",
			},
			wantCount: 0,
		},
		{
			name: "a same-page anchor is checked against this page's headings",
			files: map[string]string{
				"content/a/source.md": "## 形態\n\njump to [there](#不存在的段)\n",
			},
			wantCount: 1,
		},
		{
			name: "a valid same-page anchor is silent",
			files: map[string]string{
				"content/a/source.md": "## 形態\n\njump to [there](#形態)\n",
			},
			wantCount: 0,
		},
		{
			// Anchors inside fenced code are documentation, not references.
			name: "a fragment inside a fenced code block is exempt",
			files: map[string]string{
				"content/a/target.md": target,
				"content/a/source.md": "```markdown\n[x](/a/target/#不存在)\n```\n",
			},
			wantCount: 0,
		},
		{
			name: "section index pages are resolved as fragment owners",
			files: map[string]string{
				"content/a/_index.md": "## 從問題進入\n\nprose\n",
				"content/b/source.md": "see [x](/a/#從問題進入)\n",
			},
			wantCount: 0,
		},
		{
			name: "a fragment on a section index that has no such heading is reported",
			files: map[string]string{
				"content/a/_index.md": "## 從問題進入\n\nprose\n",
				"content/b/source.md": "see [x](/a/#從需求進入)\n",
			},
			wantCount: 1,
		},
		{
			// L1 owns whether the file should exist; L7 must not double-report.
			name: "a fragment on a target outside the graph is skipped",
			files: map[string]string{
				"content/a/source.md": "see [x](/nowhere/#anything)\n",
			},
			wantCount: 0,
		},
		{
			name: "heading text takes the display text of an inline link",
			files: map[string]string{
				"content/a/target.md": "## [Session 處理](/operations/session/)\n\nprose\n",
				"content/a/source.md": "see [x](/a/target/#session-處理)\n",
			},
			wantCount: 0,
		},
		{
			name: "heading text takes the content of inline code",
			files: map[string]string{
				"content/a/target.md": "## `md-check`\n\nprose\n",
				"content/a/source.md": "see [x](/a/target/#md-check)\n",
			},
			wantCount: 0,
		},
		{
			// Hugo suffixes repeated heading text in document order.
			name: "the second heading with the same text answers to -1",
			files: map[string]string{
				"content/a/target.md": "## 形態\n\nx\n\n## 形態\n\ny\n",
				"content/a/source.md": "see [x](/a/target/#形態-1)\n",
			},
			wantCount: 0,
		},
		{
			name: "a -2 suffix with only two such headings is reported",
			files: map[string]string{
				"content/a/target.md": "## 形態\n\nx\n\n## 形態\n\ny\n",
				"content/a/source.md": "see [x](/a/target/#形態-2)\n",
			},
			wantCount: 1,
		},
		{
			name: "relative links resolve from the source page's URL directory",
			files: map[string]string{
				"content/a/target.md": target,
				"content/a/source.md": "see [x](../target/#判讀流程)\n",
			},
			wantCount: 0,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := checkL7Fragments(docGraph(tc.files))
			if len(got) != tc.wantCount {
				t.Fatalf("got %d violation(s), want %d: %+v", len(got), tc.wantCount, got)
			}
			for _, v := range got {
				if v.Level != report.LevelError {
					t.Errorf("level = %v, want error (the stock was zero, so any hit is new breakage)", v.Level)
				}
				if v.Rule != "L7-broken-fragment" {
					t.Errorf("rule = %q", v.Rule)
				}
				if tc.wantSubstr != "" && !strings.Contains(v.Message, tc.wantSubstr) {
					t.Errorf("message %q does not quote the destination", v.Message)
				}
			}
		})
	}
}

// The fragment check is only as good as the ID it computes, so the rules
// verified against a real Hugo build are pinned here directly.
func TestAnchorize(t *testing.T) {
	cases := []struct{ in, want string }{
		{"升級路徑", "升級路徑"},
		{"L2 與 L6 問的是兩個不同問題", "l2-與-l6-問的是兩個不同問題"},
		{"Hello World", "hello-world"},
		{"already-hyphenated", "already-hyphenated"},
		{"snake_case_kept", "snake_case_kept"},
		// Punctuation is dropped without leaving a separator behind — the
		// most common source of a hand-computed anchor being wrong.
		{"配發免不掉時要定什麼？", "配發免不掉時要定什麼"},
		{"從本章到實作（路由）", "從本章到實作路由"},
		{"A, B", "a-b"},
		// The slash is dropped without a separator, so the two spaces around
		// it produce exactly two hyphens — not three.
		{"A / B", "a--b"},
		{"CI secrets 集中化跟 blast radius", "ci-secrets-集中化跟-blast-radius"},
		{"7.28 密碼學原語選型", "728-密碼學原語選型"},
		{"", ""},
		{"！？。", ""},
	}
	for _, tc := range cases {
		if got := anchorize(tc.in); got != tc.want {
			t.Errorf("anchorize(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}

func TestHeadingIDsSuffixesInDocumentOrder(t *testing.T) {
	src := []byte("## 形態\n\na\n\n### 形態\n\nb\n\n## 其他\n\nc\n\n## 形態\n\nd\n")
	ids := headingIDs(astutil.NewParser().Parse(src), src)

	for _, want := range []string{"形態", "形態-1", "形態-2", "其他"} {
		if !ids[want] {
			t.Errorf("missing heading ID %q; got %v", want, keysOf(ids))
		}
	}
	if ids["形態-3"] {
		t.Error("invented a fourth 形態 suffix")
	}
	if len(ids) != 4 {
		t.Errorf("got %d IDs, want 4: %v", len(ids), keysOf(ids))
	}
}

func keysOf(m map[string]bool) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}

// fragmentOf and ownTarget carry the same-page case; a mistake in either
// makes every `#anchor` link silently unchecked.
func TestExplicitID(t *testing.T) {
	cases := []struct {
		in       string
		wantID   string
		wantRest string
		wantOK   bool
	}{
		{"Title {#custom}", "custom", "Title", true},
		{"Title {#Custom-ID}", "custom-id", "Title", true},
		{"標題 {#zh-anchor}", "zh-anchor", "標題", true},
		{"Title {#custom}  ", "custom", "Title", true},
		{"Title", "", "Title", false},
		{"Title {#}", "", "Title {#}", false},
		{"Title {# spaced}", "", "Title {# spaced}", false},
		{"a} b", "", "a} b", false},
	}
	for _, tc := range cases {
		id, rest, ok := explicitID(tc.in)
		if ok != tc.wantOK || id != tc.wantID || rest != tc.wantRest {
			t.Errorf("explicitID(%q) = (%q, %q, %v), want (%q, %q, %v)",
				tc.in, id, rest, ok, tc.wantID, tc.wantRest, tc.wantOK)
		}
	}
}

// A heading with an explicit ID answers to that ID, and not to the auto-ID
// computed from text that still contains the braces.
func TestHeadingIDsHonoursExplicitID(t *testing.T) {
	src := []byte("## 升級路徑 {#upgrade}\n\nprose\n")
	ids := headingIDs(astutil.NewParser().Parse(src), src)

	if !ids["upgrade"] {
		t.Errorf("explicit ID not registered; got %v", keysOf(ids))
	}
	if ids["升級路徑-upgrade"] {
		t.Error("the literal braces leaked into the auto-ID")
	}
	if !ids["升級路徑"] {
		t.Errorf("auto-ID from the remaining text missing; got %v", keysOf(ids))
	}
}

func TestFragmentOfAndOwnTarget(t *testing.T) {
	frag := []struct{ in, want string }{
		{"/a/b/#sec", "sec"},
		{"#sec", "sec"},
		{"../b/#sec", "sec"},
		{"/a/b/", ""},
		{"#", ""},
		{"/a/b/#sec#more", "sec#more"},
	}
	for _, tc := range frag {
		if got := fragmentOf(tc.in); got != tc.want {
			t.Errorf("fragmentOf(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}

	own := []struct{ in, want string }{
		{"content/a/b.md", "content/a/b"},
		{"content/a/_index.md", "content/a"},
		{"content/a/b/c.md", "content/a/b/c"},
	}
	for _, tc := range own {
		if got := ownTarget(tc.in); got != tc.want {
			t.Errorf("ownTarget(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}

// Same-page anchors must not start reporting as broken links: the edge they
// create points at the source's own page, which exists by construction.
func TestSamePageAnchorDoesNotTripL1(t *testing.T) {
	g := docGraph(map[string]string{
		"content/a/source.md": "## 形態\n\njump [there](#形態)\n",
	})
	var withFragment int
	for _, e := range g.Edges {
		if e.Fragment != "" {
			withFragment++
		}
		if e.Target != "content/a/source" {
			t.Errorf("same-page anchor resolved to %q, want the source's own path", e.Target)
		}
	}
	if withFragment != 1 {
		t.Fatalf("got %d edge(s) carrying a fragment, want 1", withFragment)
	}
}
