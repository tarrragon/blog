package autolinkhtml

import (
	"reflect"
	"strings"
	"testing"
)

// testDict: cards in two folders, a name owned by two backend cards
// (ambiguous), a name owned by one backend and one devops card (resolves to
// the page's folder), a longer name containing a shorter one, a Latin name,
// a name with a space and one with an apostrophe.
func testDict() *Dict {
	return &Dict{
		Cards: map[string]Card{
			"backend/kc/transaction": {U: "/b/transaction/", T: "Transaction（交易）", D: "交易的定義"},
			"backend/kc/isolation":   {U: "/b/isolation/", T: "Isolation Level", D: ""},
			"backend/kc/log":         {U: "/b/log/", T: "Log", D: "日誌"},
			"backend/kc/cache-a":     {U: "/b/cache-a/", T: "Cache A", D: "a"},
			"backend/kc/cache-b":     {U: "/b/cache-b/", T: "Cache B", D: "b"},
			"backend/kc/queue":       {U: "/b/queue/", T: "Queue", D: "q"},
			"devops/kc/queue":        {U: "/d/queue/", T: "Queue", D: "dq"},
			"backend/kc/read-model":  {U: "/b/read-model/", T: "Read Model", D: "rm"},
			"backend/kc/owners":      {U: "/b/owners/", T: "Owner's Key", D: "ok"},
			"backend/kc/ab":          {U: "/b/ab/", T: "A&B", D: `x "y" <z>`},
		},
		Terms: []Term{
			{N: "Transaction", C: "backend/kc/transaction", M: "backend"},
			{N: "交易", C: "backend/kc/transaction", M: "backend"},
			{N: "交易隔離等級", C: "backend/kc/isolation", M: "backend"},
			{N: "Log", C: "backend/kc/log", M: "backend"},
			{N: "Cache", C: "backend/kc/cache-a", M: "backend"},
			{N: "Cache", C: "backend/kc/cache-b", M: "backend"},
			{N: "Queue", C: "devops/kc/queue", M: "devops"},
			{N: "Queue", C: "backend/kc/queue", M: "backend"},
			{N: "Read Model", C: "backend/kc/read-model", M: "backend"},
			{N: "Owner's Key", C: "backend/kc/owners", M: "backend"},
			{N: "A&B", C: "backend/kc/ab", M: "backend"},
			{N: "Missing", C: "backend/kc/missing", M: "backend"},
		},
	}
}

var backendPage = Page{Scope: []string{"backend", "devops"}, Module: "backend"}

func link(t *testing.T, p Page, text string) string {
	t.Helper()
	out, _ := NewLinker(testDict(), p).LinkText(text)
	if out == "" {
		return text
	}
	return out
}

func TestLinkTextRules(t *testing.T) {
	cases := []struct {
		name, in, want string
	}{
		{"case-insensitive, keeps the text's case", "a transaction here",
			`a <a class="kc-auto" href="/b/transaction/" data-link-title="Transaction（交易）" data-link-desc="交易的定義">transaction</a> here`},
		{"longest name wins", "交易隔離等級",
			`<a class="kc-auto" href="/b/isolation/" title="Isolation Level">交易隔離等級</a>`},
		{"Latin edge needs a word boundary", "Logit and Logs and _Log", "Logit and Logs and _Log"},
		{"word boundary passes next to CJK", "看Log檔",
			`看<a class="kc-auto" href="/b/log/" data-link-title="Log" data-link-desc="日誌">Log</a>檔`},
		{"ambiguous name is not linked", "the Cache", "the Cache"},
		{"own folder wins over another in-scope folder", "Queue",
			`<a class="kc-auto" href="/b/queue/" data-link-title="Queue" data-link-desc="q">Queue</a>`},
		{"whitespace in a name matches any run", "read\n  model",
			"<a class=\"kc-auto\" href=\"/b/read-model/\" data-link-title=\"Read Model\" data-link-desc=\"rm\">read\n  model</a>"},
		{"apostrophe matches the typographic one", "Owner’s Key",
			`<a class="kc-auto" href="/b/owners/" data-link-title="Owner&#39;s Key" data-link-desc="ok">Owner’s Key</a>`},
		{"text and attributes are escaped", "A&B <tag>",
			`<a class="kc-auto" href="/b/ab/" data-link-title="A&amp;B" data-link-desc="x &#34;y&#34; &lt;z&gt;">A&amp;B</a> &lt;tag&gt;`},
		{"card without a page in the dictionary is skipped", "Missing", "Missing"},
		// The page script's RegExp has the i flag but no u flag.
		{"non-ASCII letter does not match an ASCII one", "Tran\xc5\xbfaction", "Tran\xc5\xbfaction"},
		{"U+0085 is not whitespace in JavaScript", "read\xc2\x85model", "read\xc2\x85model"},
		{"U+FEFF is whitespace in JavaScript", "read\xef\xbb\xbfmodel",
			"<a class=\"kc-auto\" href=\"/b/read-model/\" data-link-title=\"Read Model\" data-link-desc=\"rm\">read\xef\xbb\xbfmodel</a>"},
	}
	// canon compares uppercase forms only, as JavaScript's i flag without u
	// does (checked with node: /θ/i matches Θ, /σ/i matches ς, /ϴ/i does not
	// match θ, /ß/i does not match ẞ).
	for _, p := range [][2]rune{{'θ', 'Θ'}, {'ς', 'σ'}} {
		if !foldEq(p[0], p[1]) {
			t.Errorf("foldEq(%q, %q) = false, JavaScript's i flag matches them", p[0], p[1])
		}
	}
	for _, p := range [][2]rune{{'ϴ', 'θ'}, {'ß', 'ẞ'}} {
		if foldEq(p[0], p[1]) {
			t.Errorf("foldEq(%q, %q) = true, JavaScript's i flag without u does not match them", p[0], p[1])
		}
	}
	for _, c := range cases {
		if got := link(t, backendPage, c.in); got != c.want {
			t.Errorf("%s:\n got  %s\n want %s", c.name, got, c.want)
		}
	}
}

func TestLinkTextScopeAndSelf(t *testing.T) {
	devops := Page{Scope: []string{"devops"}, Module: "devops"}
	if got := link(t, devops, "Transaction Queue"); got != `Transaction <a class="kc-auto" href="/d/queue/" data-link-title="Queue" data-link-desc="dq">Queue</a>` {
		t.Errorf("out-of-scope name linked or in-scope name missed: %s", got)
	}
	self := Page{Scope: []string{"backend"}, Module: "backend", Self: "backend/kc/transaction"}
	if got := link(t, self, "Transaction"); got != "Transaction" {
		t.Errorf("page linked its own card: %s", got)
	}
	// On the card's own page a longer name that contains one of the card's
	// names (交易隔離等級 contains 交易) still links to its own card.
	if got := link(t, self, "交易隔離等級"); !strings.Contains(got, `href="/b/isolation/"`) {
		t.Errorf("longer name missed on a card page: %s", got)
	}
}

func TestAmbiguousNameConsumesText(t *testing.T) {
	d := testDict()
	d.Terms = append(d.Terms, Term{N: "Cache Log", C: "backend/kc/cache-a", M: "backend"}, Term{N: "Cache Log", C: "backend/kc/cache-b", M: "backend"})
	out, n := NewLinker(d, backendPage).LinkText("Cache Log")
	if n != 0 || out != "" {
		t.Errorf("Log inside an ambiguous longer name was linked: %q", out)
	}
}

const page = `<!doctype html><html><head><title>Transaction</title>` +
	`<script src=/js/autolink.min.js data-terms=/blog/js/autolink-terms.x.json data-scope='["backend","devops"]' data-module=backend data-self defer></script>` +
	`</head><body><div class=nav>Transaction nav</div><h1>Transaction</h1><div class=article-body data-pagefind-body>` +
	`<span hidden>Transaction</span><p>A Transaction &amp; a <em>Log</em>.<br>交易</p>` +
	`<pre><code>Transaction</code></pre><h2 id=x>Log</h2><p><a href=/x/>Transaction</a> <code>Log</code></p>` +
	`<div class=mermaid>graph Transaction</div><svg><text>Log</text></svg><p hidden>Log</p>` +
	`<noscript>Log &amp; <img src=x></noscript><iframe>Log</iframe><template><p>Log</p></template>` +
	`<ul><li>Queue<li>Read Model</ul></div><p>Transaction after body</p></body></html>`

func TestScriptInfo(t *testing.T) {
	terms, p, done, ok, err := ScriptInfo([]byte(page))
	if err != nil || !ok || done {
		t.Fatalf("ScriptInfo: ok=%v done=%v err=%v", ok, done, err)
	}
	if terms != "/blog/js/autolink-terms.x.json" || !reflect.DeepEqual(p, Page{Scope: []string{"backend", "devops"}, Module: "backend"}) {
		t.Fatalf("ScriptInfo: %q %+v", terms, p)
	}
	if _, _, _, ok, _ := ScriptInfo([]byte(`<html><body><div class=article-body>Transaction</div></body></html>`)); ok {
		t.Fatal("page without the autolink script reported as auto-linking")
	}
}

func TestLinkPage(t *testing.T) {
	_, p, _, _, _ := ScriptInfo([]byte(page))
	out, n, err := LinkPage([]byte(page), NewLinker(testDict(), p))
	if err != nil {
		t.Fatal(err)
	}
	got := string(out)
	// Linked: prose Transaction, Log inside <em>, 交易, Queue and Read Model
	// in list items (end tags omitted).
	if n != 5 {
		t.Errorf("links = %d, want 5\n%s", n, got)
	}
	for _, untouched := range []string{
		`<title>Transaction</title>`, `<div class=nav>Transaction nav</div>`, `<h1>Transaction</h1>`, `<span hidden>Transaction</span>`,
		`<pre><code>Transaction</code></pre>`, `<h2 id=x>Log</h2>`, `<a href=/x/>Transaction</a>`,
		`<code>Log</code>`, `<div class=mermaid>graph Transaction</div>`, `<svg><text>Log</text></svg>`,
		`<p hidden>Log</p>`, `<p>Transaction after body</p>`,
		`<noscript>Log &amp; <img src=x></noscript>`, `<iframe>Log</iframe>`, `<template><p>Log</p></template>`,
	} {
		if !strings.Contains(got, untouched) {
			t.Errorf("skipped region changed, missing %q\n%s", untouched, got)
		}
	}
	if !strings.Contains(got, `<p>A <a class="kc-auto" href="/b/transaction/"`) || !strings.Contains(got, `</a> &amp; a <em><a class="kc-auto" href="/b/log/"`) {
		t.Errorf("prose not linked or entity lost:\n%s", got)
	}
	if !strings.Contains(got, `<script data-static src=/js/autolink.min.js`) {
		t.Errorf("script not marked data-static:\n%s", got)
	}
	// A second run: the script says the page is done.
	if _, _, done, _, _ := ScriptInfo(out); !done {
		t.Error("ScriptInfo does not see data-static after LinkPage")
	}
	again, n2, _ := LinkPage(out, NewLinker(testDict(), p))
	if n2 != 0 || string(again) != got {
		t.Errorf("second LinkPage changed the page (%d links)", n2)
	}
}

func TestLinkPageKeepsBytesWithoutHits(t *testing.T) {
	src := `<!doctype html><html><body><div class=article-body><p>nothing&nbsp;here &amp; <b>there</b></p><!-- c --></div></body></html>`
	out, n, err := LinkPage([]byte(src), NewLinker(testDict(), backendPage))
	if err != nil || n != 0 || string(out) != src {
		t.Errorf("page without hits changed: n=%d err=%v\n%s", n, err, out)
	}
}

// A page whose body container is not <div class=article-body> (a template
// change) is left for the page script: no links and no data-static.
func TestLinkPageWithoutBodyLeavesScriptUnmarked(t *testing.T) {
	src := strings.Replace(page, `<div class=article-body data-pagefind-body>`, `<section class=article-body>`, 1)
	if src == page {
		t.Fatal("test page has no article-body div to replace")
	}
	out, n, err := LinkPage([]byte(src), NewLinker(testDict(), backendPage))
	if err != nil || n != 0 || string(out) != src {
		t.Errorf("page without the body div changed: n=%d err=%v\n%s", n, err, out)
	}
	if _, _, done, ok, _ := ScriptInfo(out); !ok || done {
		t.Errorf("ScriptInfo: ok=%v done=%v, want an unmarked autolink script", ok, done)
	}
}

func TestLinkFeed(t *testing.T) {
	feed := `<rss><channel><item><title>T</title><link>https://example.org/blog/backend/x/</link>` +
		`<content:encoded><![CDATA[<p>Transaction</p><pre>Log</pre>]]></content:encoded></item>` +
		`<item><link>https://example.org/blog/other/y/</link><content:encoded><![CDATA[<p>Transaction</p>]]></content:encoded></item>` +
		`<item><link>https://example.org/blog/backend/z/</link><content:encoded>&lt;p&gt;Log &amp;amp; x&lt;/p&gt;</content:encoded></item>` +
		`</channel></rss>`
	pages := map[string]bool{"/blog/backend/x/": true, "/blog/backend/z/": true}
	l := NewLinker(testDict(), backendPage)
	out, items, n, err := LinkFeed([]byte(feed), func(link string) *Linker {
		if pages[PagePath(link)] {
			return l
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	got := string(out)
	if items != 2 || n != 2 {
		t.Errorf("items=%d links=%d, want 2 and 2\n%s", items, n, got)
	}
	// Feed readers do not load the site's CSS: a feed link has the card title
	// in title, without the tooltip attributes the pages carry.
	if !strings.Contains(got, `<![CDATA[<p><a class="kc-auto" href="/b/transaction/" title="Transaction（交易）">Transaction</a>`) || strings.Contains(got, "data-link-") {
		t.Errorf("feed link not in its feed form:\n%s", got)
	}
	if !strings.Contains(got, `<![CDATA[<p><a class="kc-auto" href="/b/transaction/"`) || !strings.Contains(got, `<pre>Log</pre>]]>`) {
		t.Errorf("CDATA item not linked or code changed:\n%s", got)
	}
	if !strings.Contains(got, `<link>https://example.org/blog/other/y/</link><content:encoded><![CDATA[<p>Transaction</p>]]>`) {
		t.Errorf("item of a page that does not auto-link changed:\n%s", got)
	}
	if !strings.Contains(got, `&lt;p&gt;&lt;a class=&#34;kc-auto&#34;`) && !strings.Contains(got, `&lt;p&gt;&lt;a class="kc-auto"`) {
		t.Errorf("escaped item not linked:\n%s", got)
	}
	if !strings.Contains(got, `&amp;amp; x&lt;/p&gt;`) {
		t.Errorf("escaped item lost its entity:\n%s", got)
	}
}

func TestPagePathAndBasePath(t *testing.T) {
	if got := PagePath("https://example.org/blog/backend/x/"); got != "/blog/backend/x/" {
		t.Errorf("PagePath = %q", got)
	}
	for _, in := range []string{"/blog/js/autolink-terms.abc.json", "https://example.org/blog/js/autolink-terms.abc.json"} {
		base, file, ok := BasePath(in)
		if !ok || base != "/blog/" || file != "js/autolink-terms.abc.json" {
			t.Errorf("BasePath(%q) = %q, %q, %v", in, base, file, ok)
		}
	}
	if _, _, ok := BasePath("/blog/autolink-terms.json"); ok {
		t.Error("BasePath accepted a URL without /js/")
	}
}
