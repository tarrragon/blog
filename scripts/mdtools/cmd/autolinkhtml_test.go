package cmd

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeSite(t *testing.T, files map[string]string) string {
	t.Helper()
	root := t.TempDir()
	for p, s := range files {
		full := filepath.Join(root, filepath.FromSlash(p))
		if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(full, []byte(s), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

const siteDict = `{"cards":{"backend/kc/queue":{"u":"/blog/backend/kc/queue/","t":"Queue","d":"q"}},` +
	`"terms":[{"n":"Queue","c":"backend/kc/queue","m":"backend"}]}`

const sitePage = `<html><body><div class=article-body><p>a queue</p></div>` +
	`<script src=/blog/js/autolink.min.js data-terms=/blog/js/autolink-terms.abc.json data-scope='["backend"]' data-module=backend data-self defer></script></body></html>`

func TestAutolinkHTMLLinksPagesAndFeeds(t *testing.T) {
	root := writeSite(t, map[string]string{
		"js/autolink-terms.abc.json": siteDict,
		"backend/a/index.html":       sitePage,
		"posts/b/index.html":         `<html><body><div class=article-body><p>a queue</p></div></body></html>`,
		"index.xml": `<rss><channel><item><link>https://x.org/blog/backend/a/</link><content:encoded><![CDATA[<p>queue</p>]]></content:encoded></item>` +
			`<item><link>https://x.org/blog/posts/b/</link><content:encoded><![CDATA[<p>queue</p>]]></content:encoded></item>` +
			// its path ends in backend/a/, the auto-linking page's path under root
			`<item><link>https://x.org/blog/posts/backend/a/</link><content:encoded><![CDATA[<p>queue</p>]]></content:encoded></item></channel></rss>`,
		"sitemap.xml": `<urlset><url><loc>https://x.org/blog/backend/a/</loc></url></urlset>`,
	})
	if code := AutolinkHTML([]string{root}); code != 0 {
		t.Fatalf("exit %d", code)
	}
	read := func(p string) string {
		b, err := os.ReadFile(filepath.Join(root, p))
		if err != nil {
			t.Fatal(err)
		}
		return string(b)
	}
	if got := read("backend/a/index.html"); !strings.Contains(got, `<a class="kc-auto" href="/blog/backend/kc/queue/"`) || !strings.Contains(got, "<script data-static ") {
		t.Errorf("auto-linking page not linked or not marked:\n%s", got)
	}
	if got := read("posts/b/index.html"); strings.Contains(got, "kc-auto") {
		t.Errorf("page without the autolink script was linked:\n%s", got)
	}
	feed := read("index.xml")
	if strings.Count(feed, "kc-auto") != 1 || !strings.Contains(feed, `posts/b/</link><content:encoded><![CDATA[<p>queue</p>]]>`) {
		t.Errorf("feed: want only the backend item linked:\n%s", feed)
	}
	before := read("backend/a/index.html") + feed
	if code := AutolinkHTML([]string{root}); code != 0 {
		t.Fatalf("second run exit %d", code)
	}
	if after := read("backend/a/index.html") + read("index.xml"); after != before {
		t.Error("second run changed the output")
	}
}

func TestAutolinkHTMLErrors(t *testing.T) {
	if code := AutolinkHTML(nil); code != 2 {
		t.Errorf("no argument: exit %d, want 2", code)
	}
	if code := AutolinkHTML([]string{t.TempDir()}); code != 2 {
		t.Errorf("empty directory: exit %d, want 2", code)
	}
	missingDict := writeSite(t, map[string]string{"backend/a/index.html": sitePage})
	if code := AutolinkHTML([]string{missingDict}); code != 2 {
		t.Errorf("missing dictionary: exit %d, want 2", code)
	}
}
