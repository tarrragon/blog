// Package autolinkhtml marks knowledge-card names in the built site as links
// to their cards, after hugo has written public/. It is the build-time twin of
// assets/js/autolink.js: the deployed pages and the full text of each RSS item
// (content:encoded; the description summary is left alone) carry the links in
// their HTML, so readers without JavaScript, feed readers and crawlers see
// them; `hugo server` does not run `mdtools autolink-html`, and the page
// script links the names there for local preview.
//
// Both read the same dictionary, the JSON hugo writes from
// data/autolink_terms.json (layouts/partials/autolink-dict.html), and follow
// the same rules. The rules are listed once, in the header of
// assets/js/autolink.js; the comments here name the page-script function or
// JavaScript behaviour each piece mirrors. A change to a rule goes into both
// programs and into this package's tests (autolinkhtml_test.go), and into
// the markdown approximation in internal/mdcards/autolink.go that the L2
// orphan-card check and `mdtools autolink-gaps` use.
package autolinkhtml

import (
	"html"
	"sort"
	"strings"
	"unicode"
	"unicode/utf16"
)

// Card is a dictionary entry for one card page: its URL, title and
// description, as hugo resolved them.
type Card struct {
	U string `json:"u"`
	T string `json:"t"`
	D string `json:"d"`
}

// Term is one name that links to a card; M is the card's first-level folder.
type Term struct {
	N string `json:"n"`
	C string `json:"c"`
	M string `json:"m"`
}

// Dict is the browser dictionary hugo writes to public/js/autolink-terms.*.json.
type Dict struct {
	Cards map[string]Card `json:"cards"`
	Terms []Term          `json:"terms"`
}

// Page is what a page's autolink <script> says about it: the card folders it
// may link to, its own first-level folder, and the card it is (if any).
type Page struct {
	Scope  []string
	Module string
	Self   string
}

type entry struct {
	name  []rune
	card  string
	link  bool
	units int
}

// Linker links the names of one scope (one Page) in text.
type Linker struct {
	dict    *Dict
	byFirst map[rune][]*entry
	feed    bool
}

// forFeed is l for RSS content: feed readers do not load the site's CSS, so
// the tooltip attributes (data-link-title, data-link-desc) would be dead
// bytes there; a feed link carries the card title in a title attribute.
func (l *Linker) forFeed() *Linker {
	c := *l
	c.feed = true
	return &c
}

// NewLinker picks the names page p may match, mirroring pickTerms in
// assets/js/autolink.js.
func NewLinker(d *Dict, p Page) *Linker {
	allowed := map[string]bool{}
	for _, m := range p.Scope {
		allowed[m] = true
	}
	type pick struct {
		name, card, mod string
		ambiguous       bool
	}
	picked := map[string]*pick{}
	var order []string
	for _, t := range d.Terms {
		if !allowed[t.M] {
			continue
		}
		if _, ok := d.Cards[t.C]; !ok {
			continue
		}
		key := keyOf(t.N)
		cur := picked[key]
		switch {
		case cur == nil:
			picked[key] = &pick{name: t.N, card: t.C, mod: t.M}
			order = append(order, key)
		case cur.mod == p.Module && t.M != p.Module:
		case t.M == p.Module && cur.mod != p.Module:
			*cur = pick{name: t.N, card: t.C, mod: t.M}
		default:
			cur.ambiguous = true
		}
	}
	entries := make([]*entry, 0, len(order))
	for _, key := range order {
		pk := picked[key]
		entries = append(entries, &entry{
			name:  []rune(pk.name),
			card:  pk.card,
			link:  !pk.ambiguous && pk.card != p.Self,
			units: len(utf16.Encode([]rune(pk.name))),
		})
	}
	// The page script sorts by JavaScript string length (UTF-16 units) with a
	// stable sort, so ties keep dictionary order.
	sort.SliceStable(entries, func(i, j int) bool { return entries[i].units > entries[j].units })
	l := &Linker{dict: d, byFirst: map[rune][]*entry{}}
	for _, e := range entries {
		if len(e.name) == 0 {
			continue
		}
		for _, r := range firstKeys(e.name[0]) {
			l.byFirst[r] = append(l.byFirst[r], e)
		}
	}
	return l
}

func firstKeys(r rune) []rune {
	if r == '\'' {
		return []rune{'\'', '’'}
	}
	return []rune{foldKey(r)}
}

// foldKey maps the letters foldEq treats as equal to one rune (σ and ς both
// to Σ), so the first-rune index finds every name that may match.
func foldKey(r rune) rune { return canon(r) }

// keyOf is the comparison form shared with the page script's keyOf:
// lowercase, whitespace runs folded to one space, ’ folded to '.
func keyOf(s string) string {
	s = strings.ToLower(strings.ReplaceAll(s, "’", "'"))
	return strings.Join(strings.FieldsFunc(s, isSpace), " ")
}

func isLatinEdge(r rune) bool {
	return r < 128 && (r >= 'A' && r <= 'Z' || r >= 'a' && r <= 'z' || r >= '0' && r <= '9')
}

func isWordChar(r rune) bool { return isLatinEdge(r) || r == '_' }

// canon is the page script's case folding (Canonicalize for a RegExp with the
// i flag and no u flag): a letter's uppercase form, except that a non-ASCII
// letter whose uppercase is ASCII stays itself, so the Kelvin sign K does not
// match k and long s ſ does not match s. Go's single-rune ToUpper stands in
// for JavaScript's toUpperCase, which differs only where the uppercase is
// more than one character (JavaScript then keeps the letter, as ToUpper does).
func canon(r rune) rune {
	u := unicode.ToUpper(r)
	if r >= 128 && u < 128 {
		return r
	}
	return u
}

func foldEq(a, b rune) bool { return a == b || canon(a) == canon(b) }

// isSpace is JavaScript's \s: unicode.IsSpace without U+0085, plus U+FEFF.
func isSpace(r rune) bool {
	if r == 0x85 {
		return false
	}
	return r == 0xFEFF || unicode.IsSpace(r)
}

// matchAt returns the end of e's name matched at text[i:], or -1.
func (e *entry) matchAt(text []rune, i int) int {
	k := i
	for j := 0; j < len(e.name); {
		r := e.name[j]
		switch {
		case isSpace(r):
			for j < len(e.name) && isSpace(e.name[j]) {
				j++
			}
			if k >= len(text) || !isSpace(text[k]) {
				return -1
			}
			for k < len(text) && isSpace(text[k]) {
				k++
			}
			continue
		case k >= len(text):
			return -1
		case r == '\'':
			if text[k] != '\'' && text[k] != '’' {
				return -1
			}
		case !foldEq(r, text[k]):
			return -1
		}
		j++
		k++
	}
	if isLatinEdge(e.name[0]) && i > 0 && isWordChar(text[i-1]) {
		return -1
	}
	if isLatinEdge(e.name[len(e.name)-1]) && k < len(text) && isWordChar(text[k]) {
		return -1
	}
	return k
}

// LinkText returns text as HTML with the linkable names wrapped in <a>, and
// the number of links made. With no link made it returns "", 0 and the caller
// keeps its original bytes.
func (l *Linker) LinkText(text string) (string, int) {
	rs := []rune(text)
	var b strings.Builder
	links, last := 0, 0
	for i := 0; i < len(rs); {
		var hit *entry
		end := -1
		for _, e := range l.byFirst[foldKey(rs[i])] {
			if end = e.matchAt(rs, i); end >= 0 {
				hit = e
				break
			}
		}
		if hit == nil {
			i++
			continue
		}
		if hit.link {
			b.WriteString(html.EscapeString(string(rs[last:i])))
			b.WriteString(l.anchor(hit.card, string(rs[i:end])))
			last = end
			links++
		}
		i = end
	}
	if links == 0 {
		return "", 0
	}
	b.WriteString(html.EscapeString(string(rs[last:])))
	return b.String(), links
}

// anchor builds the link the page script builds: class kc-auto, the card
// title and description in data-link-title / data-link-desc for the CSS
// tooltip, or a title attribute when the card has no description.
func (l *Linker) anchor(card, text string) string {
	c := l.dict.Cards[card]
	var b strings.Builder
	b.WriteString(`<a class="kc-auto" href="`)
	b.WriteString(html.EscapeString(c.U))
	b.WriteString(`"`)
	if c.D != "" && !l.feed {
		b.WriteString(` data-link-title="` + html.EscapeString(c.T) + `" data-link-desc="` + html.EscapeString(c.D) + `"`)
	} else {
		b.WriteString(` title="` + html.EscapeString(c.T) + `"`)
	}
	b.WriteString(">")
	b.WriteString(html.EscapeString(text))
	b.WriteString("</a>")
	return b.String()
}
