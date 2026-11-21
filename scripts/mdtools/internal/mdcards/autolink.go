package mdcards

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"unicode"

	"github.com/yuin/goldmark/ast"
)

// autolinkDictPath is the dictionary bin/autolink-dict generates from the
// card titles. The site marks every mention of these names in article prose
// as a link to the card (assets/js/autolink.js), so a card mentioned by name
// is reachable from that article even without a markdown link. mdtools runs
// from the repo root (the pre-commit hook cds there), hence the relative path.
const autolinkDictPath = "data/autolink_terms.json"

type autolinkTerm struct {
	Name   string `json:"name"`
	Card   string `json:"card"`   // content-relative path without .md
	Module string `json:"module"` // first directory under content/
}

// autolinkExcluded is a name bin/autolink-dict keeps out of the terms, with
// the reason (short-han, short-latin, config, card-off, ambiguous).
type autolinkExcluded struct {
	Name   string   `json:"name"`
	Cards  []string `json:"cards"`
	Reason string   `json:"reason"`
}

type autolinkDict struct {
	Scopes   map[string][]string `json:"scopes"`
	Terms    []autolinkTerm      `json:"terms"`
	Excluded []autolinkExcluded  `json:"excluded"`
}

var (
	autolinkOnce   sync.Once
	autolinkLoaded *autolinkDict
)

// loadAutolinkDict reads the generated dictionary once per process. A missing
// or unreadable file yields nil: the orphan check then counts markdown links
// only, which is the behaviour before auto-linking existed.
func loadAutolinkDict() *autolinkDict {
	autolinkOnce.Do(func() {
		data, err := os.ReadFile(autolinkDictPath)
		if err != nil {
			return
		}
		var d autolinkDict
		if json.Unmarshal(data, &d) == nil {
			autolinkLoaded = &d
		}
	})
	return autolinkLoaded
}

// contentModule returns the first directory under content/ for a file path,
// or "" when the path is not under content/.
func contentModule(p string) string {
	p = filepath.ToSlash(p)
	i := strings.Index(p, "content/")
	if i < 0 {
		return ""
	}
	rest := p[i+len("content/"):]
	if j := strings.Index(rest, "/"); j > 0 {
		return rest[:j]
	}
	return ""
}

// autolinkedCards returns the card files (as "content/<card>.md") among
// `wanted` that the site would auto-link from at least one non-card file.
// It mirrors the page-side rules in assets/js/autolink.js: the page's module
// picks the scope; a name owned by cards in several allowed modules resolves
// to the page's own module or is skipped; matching is case-insensitive and a
// Latin edge must sit on a word boundary; whitespace runs count as one space;
// a longer in-scope name covering the same text wins (the page regex lists
// names longest first); code, headings, links, image alt text and draft pages
// are not prose.
func autolinkedCards(g *Graph, d *autolinkDict, cardsRoot string, wanted map[string]bool) map[string]bool {
	found := map[string]bool{}
	if d == nil || len(wanted) == 0 {
		return found
	}
	wantedID := map[string]bool{}
	for p := range wanted {
		wantedID[cardID(p)] = true
	}
	all := map[string][]autolinkTerm{}
	for _, t := range d.Terms {
		k := normalizeKey(t.Name)
		all[k] = append(all[k], t)
	}
	// Only names that some wanted card owns can change the result; the other
	// terms still take part in pickCard through all[key].
	byName := map[string][]autolinkTerm{}
	for k, terms := range all {
		for _, t := range terms {
			if wantedID[t.Card] {
				byName[k] = terms
				break
			}
		}
	}
	if len(byName) == 0 {
		return found
	}

	// Longer names that contain a wanted name: an occurrence inside one of
	// them is consumed by the longer name on the page.
	longer := map[string][]string{}
	for k := range byName {
		for other := range all {
			if len(other) > len(k) && strings.Contains(other, k) {
				longer[k] = append(longer[k], other)
			}
		}
	}

	for _, fn := range g.Files {
		if isCardPath(fn.Path, cardsRoot) || isSectionIndex(fn.Path) || isDraft(fn.Src) {
			continue
		}
		module := contentModule(fn.Path)
		allowed := map[string]bool{}
		for _, m := range d.Scopes[module] {
			allowed[m] = true
		}
		if len(allowed) == 0 {
			continue
		}
		var prose string
		for key, terms := range byName {
			card := pickCard(terms, allowed, module)
			if card == "" {
				continue
			}
			path := filepath.ToSlash(filepath.Join(contentRoot(fn.Path), card+".md"))
			if !wanted[path] || found[path] {
				continue
			}
			if prose == "" {
				prose = normalizeKey(proseText(fn))
			}
			var cover []string
			for _, l := range longer[key] {
				if inScope(all[l], allowed) {
					cover = append(cover, l)
				}
			}
			if containsTerm(prose, key, cover) {
				found[path] = true
			}
		}
	}
	return found
}

// cardID turns a card file path into the dictionary's card key: the path
// under content/ without the .md suffix.
func cardID(p string) string {
	p = filepath.ToSlash(p)
	if i := strings.Index(p, "content/"); i >= 0 {
		p = p[i+len("content/"):]
	}
	return strings.TrimSuffix(p, ".md")
}

// contentRoot returns the path prefix up to and including "content" so card
// paths resolve the same way the walker spelled the source file.
func contentRoot(p string) string {
	p = filepath.ToSlash(p)
	i := strings.Index(p, "content/")
	if i < 0 {
		return "content"
	}
	return p[:i+len("content")]
}

func pickCard(terms []autolinkTerm, allowed map[string]bool, module string) string {
	var inScope []autolinkTerm
	for _, t := range terms {
		if allowed[t.Module] {
			inScope = append(inScope, t)
		}
	}
	switch {
	case len(inScope) == 0:
		return ""
	case len(inScope) == 1:
		return inScope[0].Card
	}
	var own []autolinkTerm
	for _, t := range inScope {
		if t.Module == module {
			own = append(own, t)
		}
	}
	if len(own) == 1 {
		return own[0].Card
	}
	return ""
}

func isLatinOrDigit(r rune) bool {
	return r < unicode.MaxASCII && (unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_')
}

// normalizeKey is the comparison form shared with the page script's keyOf:
// lowercase, whitespace runs folded to one space, ’ folded to '.
func normalizeKey(s string) string {
	s = strings.ToLower(strings.ReplaceAll(s, "’", "'"))
	return strings.Join(strings.Fields(s), " ")
}

func inScope(terms []autolinkTerm, allowed map[string]bool) bool {
	for _, t := range terms {
		if allowed[t.Module] {
			return true
		}
	}
	return false
}

// isDraft reports whether the front matter sets draft: true; Hugo does not
// render those pages, so they link nothing.
func isDraft(src []byte) bool {
	end := frontMatterEnd(src)
	if end == 0 {
		return false
	}
	for _, line := range strings.Split(string(src[:end]), "\n") {
		if strings.TrimSpace(line) == "draft: true" {
			return true
		}
	}
	return false
}

// matchesAt reports whether name occurs at text[start:] with word boundaries
// on any Latin edge.
func matchesAt(text, name string, start int) bool {
	if start < 0 || !strings.HasPrefix(text[start:], name) {
		return false
	}
	nameRunes := []rune(name)
	end := start + len(name)
	if isLatinOrDigit(nameRunes[0]) && start > 0 && isLatinOrDigit(lastRune(text[:start])) {
		return false
	}
	if isLatinOrDigit(nameRunes[len(nameRunes)-1]) && end < len(text) && isLatinOrDigit(firstRune(text[end:])) {
		return false
	}
	return true
}

// containsTerm reports whether normalized text holds the normalized name with
// word boundaries on any Latin edge, at a position no name in `cover` (longer
// names containing it) also matches over.
func containsTerm(text, name string, cover []string) bool {
	from := 0
	for {
		i := strings.Index(text[from:], name)
		if i < 0 {
			return false
		}
		start := from + i
		if matchesAt(text, name, start) && !coveredAt(text, name, start, cover) {
			return true
		}
		from = start + 1
	}
}

func coveredAt(text, name string, start int, cover []string) bool {
	for _, l := range cover {
		for off := strings.Index(l, name); off >= 0; {
			if matchesAt(text, l, start-off) {
				return true
			}
			next := strings.Index(l[off+1:], name)
			if next < 0 {
				break
			}
			off += 1 + next
		}
	}
	return false
}

func lastRune(s string) rune {
	r := []rune(s)
	return r[len(r)-1]
}

func firstRune(s string) rune {
	for _, r := range s {
		return r
	}
	return 0
}

// proseText concatenates the text the page script would scan: text nodes
// outside code, headings, links and images (alt text is an attribute on the
// page), after the front matter. Raw HTML is skipped although the page script
// scans text inside HTML blocks, so a name used only there reads as orphan.
// Adjacent text nodes are joined, so a name split across emphasis
// ("**Rollback** Strategy") matches here but not on the page. Only longer
// names that contain a name count as covering it; two names that merely
// overlap ("A B" and "B C" over "A B C") resolve left-first on the page,
// where "B C" is not linked, while this check counts it.
func proseText(fn FileNode) string {
	fmEnd := frontMatterEnd(fn.Src)
	var b strings.Builder
	_ = ast.Walk(fn.AST, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
		if !entering {
			return ast.WalkContinue, nil
		}
		switch n.Kind() {
		case ast.KindHeading, ast.KindLink, ast.KindAutoLink, ast.KindImage, ast.KindCodeSpan,
			ast.KindCodeBlock, ast.KindFencedCodeBlock, ast.KindHTMLBlock, ast.KindRawHTML:
			return ast.WalkSkipChildren, nil
		case ast.KindText:
			t := n.(*ast.Text)
			if t.Segment.Start >= fmEnd {
				b.Write(t.Segment.Value(fn.Src))
				b.WriteByte('\n')
			}
		}
		return ast.WalkContinue, nil
	})
	return b.String()
}
