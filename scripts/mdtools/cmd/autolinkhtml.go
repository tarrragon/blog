package cmd

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"

	"blog/scripts/mdtools/internal/autolinkhtml"
)

// AutolinkHTML runs the autolink-html subcommand on a built site: it links
// the knowledge-card names in every page that loads the autolink script
// (layouts/partials/autolink.html), then in the RSS items of those pages, and
// rewrites the files in place. Run it after `hugo` and before pagefind:
//
//	mdtools autolink-html public
//
// It prints on stderr
//
//	mdtools autolink-html: P page(s) scanned, A page(s) linked, L link(s), S already linked; F feed(s), I item(s), K link(s)
//
// P is every .html file under the directory; A counts pages with at least
// one new link; S counts pages whose script already carries data-static (a
// second run changes nothing). A page that loads the autolink script but has
// no <div class=article-body> is neither linked nor marked, so the page script
// still links it; a second line on stderr counts such pages. Exit 0 when the run finished, 2 when the
// directory, a page or the dictionary cannot be read or written, or when the
// directory holds no .html file.
func AutolinkHTML(args []string) int {
	if len(args) != 1 {
		fmt.Fprintln(os.Stderr, "Usage: mdtools autolink-html <public-dir>")
		return 2
	}
	root := args[0]
	if err := runAutolinkHTML(root); err != nil {
		fmt.Fprintf(os.Stderr, "mdtools autolink-html: %v\n", err)
		return 2
	}
	return 0
}

func runAutolinkHTML(root string) error {
	var htmlFiles, xmlFiles []string
	err := filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		switch filepath.Ext(p) {
		case ".html":
			htmlFiles = append(htmlFiles, p)
		case ".xml":
			xmlFiles = append(xmlFiles, p)
		}
		return nil
	})
	if err != nil {
		return err
	}
	if len(htmlFiles) == 0 {
		return fmt.Errorf("no .html file under %s", root)
	}
	sort.Strings(htmlFiles)
	sort.Strings(xmlFiles)

	dicts := map[string]*autolinkhtml.Dict{}
	loadDict := func(termsURL string) (*autolinkhtml.Dict, error) {
		if d, ok := dicts[termsURL]; ok {
			return d, nil
		}
		// hugo writes the resource as js/<name> under the publish directory;
		// the URL carries the site's base path in front of it.
		_, file, ok := autolinkhtml.BasePath(termsURL)
		if !ok {
			return nil, fmt.Errorf("dictionary URL %q is not under /js/", termsURL)
		}
		data, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(file)))
		if err != nil {
			return nil, err
		}
		var d autolinkhtml.Dict
		if err := json.Unmarshal(data, &d); err != nil {
			return nil, fmt.Errorf("%s: %v", termsURL, err)
		}
		dicts[termsURL] = &d
		return &d, nil
	}

	type pageLinker struct {
		dict *autolinkhtml.Dict
		page autolinkhtml.Page
	}
	pages := map[string]pageLinker{}
	var linkedPages, links, already int
	var noBody []string
	for _, f := range htmlFiles {
		src, err := os.ReadFile(f)
		if err != nil {
			return err
		}
		termsURL, page, done, ok, err := autolinkhtml.ScriptInfo(src)
		if err != nil {
			return fmt.Errorf("%s: %v", f, err)
		}
		if !ok {
			continue
		}
		d, err := loadDict(termsURL)
		if err != nil {
			return err
		}
		// The page index is keyed by URL path (base path + path under root),
		// the form PagePath gives for a feed item's <link>, so an item maps
		// only to the page at exactly its URL.
		rel, _ := filepath.Rel(root, f)
		rel = filepath.ToSlash(rel)
		if path.Base(rel) == "index.html" {
			rel = strings.TrimSuffix(rel, "index.html")
		}
		base, _, _ := autolinkhtml.BasePath(termsURL)
		pages[base+rel] = pageLinker{dict: d, page: page}
		if done {
			already++
			continue
		}
		out, n, err := autolinkhtml.LinkPage(src, autolinkhtml.NewLinker(d, page))
		if err != nil {
			return fmt.Errorf("%s: %v", f, err)
		}
		if _, _, marked, _, _ := autolinkhtml.ScriptInfo(out); !marked {
			noBody = append(noBody, f)
		}
		if err := writeSamePerm(f, out); err != nil {
			return err
		}
		if n > 0 {
			linkedPages++
			links += n
		}
	}

	linkers := map[string]*autolinkhtml.Linker{}
	linkerFor := func(link string) *autolinkhtml.Linker {
		k := autolinkhtml.PagePath(link)
		pl, ok := pages[k]
		if !ok {
			return nil
		}
		if l, ok := linkers[k]; ok {
			return l
		}
		l := autolinkhtml.NewLinker(pl.dict, pl.page)
		linkers[k] = l
		return l
	}
	var feeds, items, feedLinks int
	for _, f := range xmlFiles {
		src, err := os.ReadFile(f)
		if err != nil {
			return err
		}
		if !strings.Contains(string(src), "<item>") {
			continue
		}
		feeds++
		out, i, n, err := autolinkhtml.LinkFeed(src, linkerFor)
		if err != nil {
			return fmt.Errorf("%s: %v", f, err)
		}
		if n > 0 {
			if err := writeSamePerm(f, out); err != nil {
				return err
			}
		}
		items += i
		feedLinks += n
	}
	fmt.Fprintf(os.Stderr, "mdtools autolink-html: %d page(s) scanned, %d page(s) linked, %d link(s), %d already linked; %d feed(s), %d item(s), %d link(s)\n",
		len(htmlFiles), linkedPages, links, already, feeds, items, feedLinks)
	if len(noBody) > 0 {
		fmt.Fprintf(os.Stderr, "mdtools autolink-html: warning: %d page(s) load the autolink script but have no <div class=article-body>; left for the page script (did layouts/_default/single.html change?), e.g. %s\n",
			len(noBody), noBody[0])
	}
	return nil
}

func writeSamePerm(p string, data []byte) error {
	info, err := os.Stat(p)
	if err != nil {
		return err
	}
	return os.WriteFile(p, data, info.Mode().Perm())
}
