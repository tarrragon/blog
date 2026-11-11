package mdcards

import (
	"testing"

	"blog/scripts/mdtools/internal/astutil"
)

// l4Graph parses each card body with the production parser so the check
// sees the same AST shape (front matter stripped, headings as nodes).
func l4Graph(cards map[string]string) *Graph {
	parser := astutil.NewParser()
	g := &Graph{byPath: map[string]*FileNode{}}
	for _, path := range []string{cardsRoot + "/a.md", cardsRoot + "/b.md"} {
		body, ok := cards[path]
		if !ok {
			continue
		}
		src := []byte(body)
		g.Files = append(g.Files, FileNode{Path: path, AST: parser.Parse(src), Src: src})
	}
	for i := range g.Files {
		g.byPath[g.Files[i].Path] = &g.Files[i]
	}
	return g
}

const l4FrontMatter = "---\ntitle: \"A\"\ndescription: \"d\"\nweight: 1\n---\n\n"

func l4Rules(t *testing.T, body string) []string {
	t.Helper()
	g := l4Graph(map[string]string{cardsRoot + "/a.md": l4FrontMatter + body})
	var rules []string
	for _, v := range checkL4K4Structure(g, cardsRoot, "跟其他概念的關係") {
		rules = append(rules, v.Rule)
	}
	return rules
}

func TestCheckL4FirstParagraph(t *testing.T) {
	cases := []struct {
		name string
		body string
		want []string
	}{
		{
			name: "opening paragraph with a card link is silent",
			body: "A 是一種東西，見 [B](../b/)。\n\n## 跟其他概念的關係\n\n跟 [B](../b/) 的關係。\n",
			want: nil,
		},
		{
			// session-lock 那一型：front matter 之後直接接段標。舊版往下找到
			// 「跟其他概念的關係」段的段落，那一段有鄰卡連結，於是放行。
			name: "heading-first card reports the missing opening paragraph",
			body: "## 跟其他概念的關係\n\n跟 [B](../b/) 的關係。\n",
			want: []string{"L4-missing-first-paragraph"},
		},
		{
			name: "opening paragraph without a card link is reported",
			body: "A 是一種東西。\n\n## 跟其他概念的關係\n\n跟 [B](../b/) 的關係。\n",
			want: []string{"L4-first-paragraph-no-card-link"},
		},
		{
			name: "missing concept section is still reported after an opening paragraph",
			body: "A 是一種東西，見 [B](../b/)。\n\n## 判斷條件與後果\n\n內容。\n",
			want: []string{"L4-missing-concept-position"},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := l4Rules(t, tc.body)
			if len(got) != len(tc.want) {
				t.Fatalf("rules = %v, want %v", got, tc.want)
			}
			for i := range got {
				if got[i] != tc.want[i] {
					t.Fatalf("rules = %v, want %v", got, tc.want)
				}
			}
		})
	}
}
