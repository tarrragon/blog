package mdcards

import (
	"sort"
	"testing"

	"blog/scripts/mdtools/internal/astutil"
)

// parsedGraph builds a graph from file contents with real goldmark ASTs and
// no markdown-link edges, so only auto-linking can make a card reachable.
func parsedGraph(files map[string]string) *Graph {
	paths := make([]string, 0, len(files))
	for p := range files {
		paths = append(paths, p)
	}
	sort.Strings(paths)
	p := astutil.NewParser()
	g := &Graph{byPath: map[string]*FileNode{}}
	for _, path := range paths {
		src := []byte(files[path])
		g.Files = append(g.Files, FileNode{Path: path, AST: p.Parse(src), Src: src})
	}
	for i := range g.Files {
		g.byPath[g.Files[i].Path] = &g.Files[i]
	}
	return g
}

func testDict() *autolinkDict {
	return &autolinkDict{
		Scopes: map[string][]string{
			"backend":     {"backend"},
			"programming": {"programming", "backend"},
			"business":    {"business"},
		},
		Terms: []autolinkTerm{
			{Name: "Schema Drift", Card: "backend/knowledge-cards/schema-drift", Module: "backend"},
			{Name: "結構漂移", Card: "backend/knowledge-cards/schema-drift", Module: "backend"},
			{Name: "Log", Card: "backend/knowledge-cards/log", Module: "backend"},
			{Name: "Retention", Card: "backend/knowledge-cards/retention", Module: "backend"},
			{Name: "Retention", Card: "business/knowledge-cards/retention", Module: "business"},
			{Name: "Widget", Card: "programming/knowledge-cards/widget", Module: "programming"},
			{Name: "Widget", Card: "backend/knowledge-cards/widget", Module: "backend"},
		},
	}
}

const fm = "---\ntitle: \"t\"\ndescription: \"mentions Log and Schema Drift here\"\n---\n\n"

func orphanPaths(t *testing.T, files map[string]string, dict *autolinkDict) map[string]bool {
	t.Helper()
	got := map[string]bool{}
	for _, v := range checkL2OrphansWith(parsedGraph(files), "knowledge-cards", dict) {
		got[v.Path] = true
	}
	return got
}

func cardFiles() map[string]string {
	return map[string]string{
		"content/backend/knowledge-cards/schema-drift.md": fm + "card body",
		"content/backend/knowledge-cards/log.md":          fm + "card body",
		"content/backend/knowledge-cards/retention.md":    fm + "card body",
		"content/business/knowledge-cards/retention.md":   fm + "card body",
		"content/programming/knowledge-cards/widget.md":   fm + "card body",
		"content/backend/knowledge-cards/widget.md":       fm + "card body",
	}
}

func TestAutolinkMentionInProseMakesCardReachable(t *testing.T) {
	files := cardFiles()
	files["content/backend/a.md"] = fm + "偵測結構漂移的方法。\n"
	got := orphanPaths(t, files, testDict())
	if got["content/backend/knowledge-cards/schema-drift.md"] {
		t.Fatal("schema-drift is mentioned by its Chinese name in a backend article, should not be orphan")
	}
	if !got["content/backend/knowledge-cards/log.md"] {
		t.Fatal("log is only mentioned in front matter, should stay orphan")
	}
}

func TestAutolinkSkipsCodeHeadingsLinksAndWordParts(t *testing.T) {
	files := cardFiles()
	files["content/backend/a.md"] = fm + "## Log\n\n`Log` 與 [Log](/x/) 與 Logit 與 catalog\n\n```\nLog\n```\n"
	if !orphanPaths(t, files, testDict())["content/backend/knowledge-cards/log.md"] {
		t.Fatal("Log appears only in heading, code, link text and inside other words; should stay orphan")
	}
	files["content/backend/a.md"] = fm + "寫進 log 檔。\n"
	if orphanPaths(t, files, testDict())["content/backend/knowledge-cards/log.md"] {
		t.Fatal("lowercase log in prose should match case-insensitively")
	}
}

func TestAutolinkRespectsScopes(t *testing.T) {
	files := cardFiles()
	files["content/business/a.md"] = fm + "schema drift 在這裡不算。\n"
	files["content/til/a.md"] = fm + "Schema Drift outside any scope.\n"
	if !orphanPaths(t, files, testDict())["content/backend/knowledge-cards/schema-drift.md"] {
		t.Fatal("business and til pages may not link backend cards")
	}
}

func TestAutolinkSameNamePicksPageModuleOrSkips(t *testing.T) {
	files := cardFiles()
	files["content/business/a.md"] = fm + "Retention 指留存。\n"
	files["content/programming/a.md"] = fm + "Widget 與 Retention。\n"
	got := orphanPaths(t, files, testDict())
	if got["content/business/knowledge-cards/retention.md"] {
		t.Fatal("business page should reach the business Retention card")
	}
	if got["content/backend/knowledge-cards/retention.md"] {
		t.Fatal("the programming scope holds only the backend Retention card, so the programming page should reach it")
	}
	if got["content/programming/knowledge-cards/widget.md"] {
		t.Fatal("programming page should prefer the programming Widget card")
	}
	if !got["content/backend/knowledge-cards/widget.md"] {
		t.Fatal("backend Widget loses to the page's own module and stays orphan")
	}
}

func TestAutolinkLongerNameConsumesShorterAndRespectsPageRules(t *testing.T) {
	d := testDict()
	d.Terms = append(d.Terms, autolinkTerm{Name: "Log Shipping", Card: "backend/knowledge-cards/log-shipping", Module: "backend"})
	files := cardFiles()
	files["content/backend/knowledge-cards/log-shipping.md"] = fm + "card body"
	files["content/backend/a.md"] = fm + "設定 Log Shipping 的步驟。\n"
	if !orphanPaths(t, files, d)["content/backend/knowledge-cards/log.md"] {
		t.Fatal("Log inside Log Shipping is consumed by the longer name on the page")
	}
	files["content/backend/a.md"] = fm + "設定 Log\nShipping 之後看 log。\n"
	got := orphanPaths(t, files, d)
	if got["content/backend/knowledge-cards/log-shipping.md"] {
		t.Fatal("a name split by a soft line break still matches")
	}
	if got["content/backend/knowledge-cards/log.md"] {
		t.Fatal("the separate lowercase log should match")
	}
}

func TestAutolinkSkipsDraftAndImageAlt(t *testing.T) {
	files := cardFiles()
	files["content/backend/a.md"] = "---\ntitle: \"t\"\ndraft: true\n---\n\n結構漂移\n"
	files["content/backend/b.md"] = fm + "![Log](/x.png)\n"
	got := orphanPaths(t, files, testDict())
	if !got["content/backend/knowledge-cards/schema-drift.md"] {
		t.Fatal("draft pages are not rendered and link nothing")
	}
	if !got["content/backend/knowledge-cards/log.md"] {
		t.Fatal("image alt text is an attribute on the page, not prose")
	}
}

func TestAutolinkNilDictKeepsMarkdownOnlyBehaviour(t *testing.T) {
	files := cardFiles()
	files["content/backend/a.md"] = fm + "結構漂移\n"
	if !orphanPaths(t, files, nil)["content/backend/knowledge-cards/schema-drift.md"] {
		t.Fatal("without a dictionary only markdown links count")
	}
}
