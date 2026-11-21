package mdcards

import (
	"testing"
)

// linkedGraph is parsedGraph plus markdown-link edges, so a hand-written
// link can suppress a gap.
func linkedGraph(files map[string]string) *Graph {
	g := parsedGraph(files)
	g.inbound = map[string][]int{}
	g.outbound = map[string][]int{}
	for _, fn := range g.Files {
		g.extractEdges(fn)
	}
	return g
}

func gapDict() *autolinkDict {
	d := testDict()
	d.Terms = append(d.Terms,
		autolinkTerm{Name: "Helm", Card: "devops/knowledge-cards/helm", Module: "devops"},
		autolinkTerm{Name: "Transaction Log", Card: "backend/knowledge-cards/transaction-log", Module: "backend"},
	)
	d.Excluded = []autolinkExcluded{
		{Name: "交易", Cards: []string{"backend/knowledge-cards/transaction"}, Reason: "short-han"},
		{Name: "Index", Cards: []string{"backend/knowledge-cards/index"}, Reason: "config"},
	}
	return d
}

func gapsOf(t *testing.T, files map[string]string) map[string]string {
	t.Helper()
	got := map[string]string{}
	for _, gp := range autolinkGapsWith(linkedGraph(files), gapDict()) {
		got[gp.Path+"|"+gp.Name] = gp.Reason
	}
	return got
}

func TestGapsListOnlyNamesTheSiteWillNotLink(t *testing.T) {
	got := gapsOf(t, map[string]string{
		"content/backend/a.md": fm + "用 Helm 部署；這筆交易寫進 Log，Index 另外建；結構漂移；Retention。\n",
	})
	want := map[string]string{
		"content/backend/a.md|Helm":  "out-of-scope",
		"content/backend/a.md|交易":    "short-han",
		"content/backend/a.md|Index": "config",
	}
	for k, v := range want {
		if got[k] != v {
			t.Errorf("%s: got %q, want %q (all: %v)", k, got[k], v, got)
		}
	}
	for _, k := range []string{"content/backend/a.md|Log", "content/backend/a.md|結構漂移", "content/backend/a.md|Retention"} {
		if _, ok := got[k]; ok {
			t.Errorf("%s is auto-linked on a backend page, should not be a gap", k)
		}
	}
	if len(got) != len(want) {
		t.Errorf("got %d gaps, want %d: %v", len(got), len(want), got)
	}
}

func TestGapsUnscopedFolderAndAmbiguousModules(t *testing.T) {
	got := gapsOf(t, map[string]string{
		"content/report/r.md":      fm + "Schema Drift 的成因。\n",
		"content/programming/p.md": fm + "Widget 與 Retention。\n",
	})
	if got["content/report/r.md|Schema Drift"] != "folder-unscoped" {
		t.Errorf("report page: %v", got)
	}
	// programming may link programming and backend: Widget resolves to the
	// page's own folder; Retention exists in backend only within scope.
	if _, ok := got["content/programming/p.md|Widget"]; ok {
		t.Errorf("Widget resolves to programming's own card: %v", got)
	}

	// A scope holding two other folders that both own the name: the page
	// script cannot choose, so the name is a gap.
	d := gapDict()
	d.Scopes["books"] = []string{"backend", "business"}
	g := linkedGraph(map[string]string{"content/books/b.md": fm + "Retention 的定義。\n"})
	var reasons []string
	for _, gp := range autolinkGapsWith(g, d) {
		if gp.Name == "Retention" {
			reasons = append(reasons, gp.Reason)
		}
	}
	if len(reasons) != 1 || reasons[0] != "ambiguous-modules" {
		t.Errorf("books page Retention: got %v, want [ambiguous-modules]", reasons)
	}
}

func TestGapsSkipSectionIndexButNotHome(t *testing.T) {
	got := gapsOf(t, map[string]string{
		"content/backend/_index.md": fm + "Helm 的章節表。\n",
		"content/_index.md":         fm + "Helm 首頁。\n",
	})
	if _, ok := got["content/backend/_index.md|Helm"]; ok {
		t.Errorf("section index body is not shown to readers: %v", got)
	}
	if got["content/_index.md|Helm"] != "folder-unscoped" {
		t.Errorf("home page renders its body: %v", got)
	}
	// an absolute path to the home page is still the home page
	abs := gapsOf(t, map[string]string{"/repo/content/_index.md": fm + "Helm 首頁。\n"})
	if abs["/repo/content/_index.md|Helm"] != "folder-unscoped" {
		t.Errorf("absolute home page path: %v", abs)
	}
}

func TestGapsShortLatinNeedsMatchingCaseAndDerivedWordsListed(t *testing.T) {
	d := gapDict()
	d.Excluded = append(d.Excluded,
		autolinkExcluded{Name: "dB", Cards: []string{"til/audio/knowledge-cards/decibel"}, Reason: "short-latin"},
		autolinkExcluded{Name: "Ack", Cards: []string{"backend/knowledge-cards/ack-nack"}, Reason: "derived-word"},
	)
	got := map[string]string{}
	files := map[string]string{"content/backend/a.md": fm + "寫進 DB 之後回 ack。\n"}
	for _, gp := range autolinkGapsWith(linkedGraph(files), d) {
		got[gp.Name] = gp.Reason
	}
	if _, ok := got["dB"]; ok {
		t.Errorf("DB is not dB: %v", got)
	}
	if got["Ack"] != "derived-word" {
		t.Errorf("ack is a derived word the site does not link: %v", got)
	}
	files["content/backend/a.md"] = fm + "音量差 6 dB。\n"
	got = map[string]string{}
	for _, gp := range autolinkGapsWith(linkedGraph(files), d) {
		got[gp.Name] = gp.Reason
	}
	if got["dB"] != "short-latin" {
		t.Errorf("dB with matching case is listed: %v", got)
	}
}

func TestGapsSkipCardAutolinkedThroughAnotherName(t *testing.T) {
	d := gapDict()
	d.Terms = append(d.Terms, autolinkTerm{Name: "Transaction", Card: "backend/knowledge-cards/transaction", Module: "backend"})
	files := map[string]string{"content/backend/a.md": fm + "這筆交易寫進 Log。\n"}
	got := map[string]bool{}
	for _, gp := range autolinkGapsWith(linkedGraph(files), d) {
		got[gp.Name] = true
	}
	if !got["交易"] {
		t.Fatalf("交易 alone on the page is a gap: %v", got)
	}
	files["content/backend/a.md"] = fm + "Transaction 是什麼；這筆交易寫進 Log。\n"
	got = map[string]bool{}
	for _, gp := range autolinkGapsWith(linkedGraph(files), d) {
		got[gp.Name] = true
	}
	if got["交易"] {
		t.Errorf("Transaction already links the card on this page; 交易 is not a gap: %v", got)
	}
}

func TestGapsNameExcludedElsewhereButLinkedHere(t *testing.T) {
	d := gapDict()
	d.Terms = append(d.Terms, autolinkTerm{Name: "Shared", Card: "backend/knowledge-cards/shared", Module: "backend"})
	d.Excluded = append(d.Excluded, autolinkExcluded{Name: "Shared", Cards: []string{"business/knowledge-cards/a", "business/knowledge-cards/b"}, Reason: "ambiguous"})
	for _, gp := range autolinkGapsWith(linkedGraph(map[string]string{"content/backend/a.md": fm + "Shared 的說明。\n"}), d) {
		if gp.Name == "Shared" {
			t.Errorf("Shared is linked on a backend page: got gap %+v", gp)
		}
	}
}

func TestGapsSkipHandLinkedCardsOwnCardAndLongerNames(t *testing.T) {
	got := gapsOf(t, map[string]string{
		"content/backend/a.md":                     fm + "[Helm](/devops/knowledge-cards/helm/) 與 Transaction Log。\n",
		"content/backend/knowledge-cards/index.md": fm + "Index 的定義。\n",
	})
	if _, ok := got["content/backend/a.md|Helm"]; ok {
		t.Errorf("Helm is linked by hand, should not be a gap: %v", got)
	}
	if _, ok := got["content/backend/a.md|Log"]; ok {
		t.Errorf("Log inside Transaction Log belongs to the longer name: %v", got)
	}
	if _, ok := got["content/backend/knowledge-cards/index.md|Index"]; ok {
		t.Errorf("a card's own name on its own page is not a gap: %v", got)
	}
}
