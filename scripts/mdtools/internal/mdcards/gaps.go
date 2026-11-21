package mdcards

import (
	"fmt"
	"path/filepath"
	"sort"
	"strings"
)

// Gap is a card name that appears in a page's prose but that the site will
// not auto-link there, and that the page does not link to by hand either.
// These are the names the tool can list as candidates for a hand-written
// link (prose that names a card in other words is beyond string matching);
// docs/rules/sentences.md decides which of them to link.
type Gap struct {
	Path   string   // the page
	Name   string   // the card name as written in the dictionary
	Reason string   // why the site does not link it (see gapReasons)
	Cards  []string // content-relative card paths without .md
}

// gapReasons explains each Reason value; the subcommand prints it in its
// help text so the output is readable without opening this file.
var gapReasons = map[string]string{
	"folder-unscoped":   "the page's first-level folder is not a key under [scopes] in data/autolink.toml (listed under [unlisted], or the home page): nothing on it is auto-linked",
	"out-of-scope":      "the card's folder is not in the page folder's scope",
	"ambiguous-modules": "cards in two allowed folders share the name and neither is the page's own folder",
	"short-han":         "excluded by bin/autolink-dict: too few Han characters",
	"short-latin":       "excluded by bin/autolink-dict: too few Latin characters (listed only when the case matches: dB, not DB)",
	"derived-word":      "a plain English word split off a card title (Ack in Ack / Nack); bin/autolink-dict does not link it",
	"config":            "excluded by bin/autolink-dict: listed in names.exclude",
	"card-off":          "excluded by bin/autolink-dict: the card sets autolink: false",
	"ambiguous":         "excluded by bin/autolink-dict: two cards in one folder share the name",
}

// GapReasons returns the reason table for help output, sorted by key.
func GapReasons() []string {
	var out []string
	for k, v := range gapReasons {
		out = append(out, fmt.Sprintf("  %-18s %s", k, v))
	}
	sort.Strings(out)
	return out
}

// AutolinkGaps lists, for each given page, the card names in its prose that
// the page script will not link and that the page does not already link to
// by hand. Matching follows autolinkedCards: case-insensitive, Latin edges on
// word boundaries, whitespace folded, and an occurrence inside a longer name
// the page links belongs to the longer name (on a page without auto-linking,
// any longer card name). A name is not listed when its card is already linked
// on the page, by hand or by the site through another of its names (one link
// to a card per page is enough), nor on the card's own page (the page script
// never links a card to itself). Section index pages other than the home page
// are skipped: readers never see their body. One line per page and name.
func AutolinkGaps(paths []string) ([]Gap, int, error) {
	d := loadAutolinkDict()
	if d == nil {
		return nil, 0, fmt.Errorf("cannot read %s (run from the repo root; regenerate with bin/autolink-dict)", autolinkDictPath)
	}
	g, err := BuildGraph(paths)
	if err != nil {
		return nil, 0, err
	}
	return autolinkGapsWith(g, d), len(g.Files), nil
}

func autolinkGapsWith(g *Graph, d *autolinkDict) []Gap {
	type entry struct {
		name   string
		terms  []autolinkTerm // linkable names
		reason string         // set for excluded names
		cards  []string
	}
	byKey := map[string]*entry{}
	get := func(name string) *entry {
		k := normalizeKey(name)
		if byKey[k] == nil {
			byKey[k] = &entry{name: name}
		}
		return byKey[k]
	}
	for _, t := range d.Terms {
		e := get(t.Name)
		e.terms = append(e.terms, t)
	}
	for _, x := range d.Excluded {
		e := get(x.Name)
		if e.reason == "" {
			e.reason = x.Reason
		}
		e.cards = append(e.cards, x.Cards...)
	}
	keys := make([]string, 0, len(byKey))
	for k := range byKey {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	longer := map[string][]string{}
	for _, k := range keys {
		for _, o := range keys {
			if len(o) > len(k) && strings.Contains(o, k) {
				longer[k] = append(longer[k], o)
			}
		}
	}

	var out []Gap
	for _, fn := range g.Files {
		if isDraft(fn.Src) || (isSectionIndex(fn.Path) && contentModule(fn.Path) != "") {
			continue
		}
		self := cardID(fn.Path)
		linked := map[string]bool{}
		for _, i := range g.outbound[fn.Path] {
			linked[cardID(g.Edges[i].Target)] = true
		}
		module := contentModule(fn.Path)
		allowed := map[string]bool{}
		for _, m := range d.Scopes[module] {
			allowed[m] = true
		}
		raw := proseText(fn)
		prose := normalizeKey(raw)
		var proseCased string // built on demand for short-latin names
		// first pass: the names present in prose, and the cards the site
		// links on this page through any of their names
		var present []string
		for _, k := range keys {
			cover := longer[k]
			if len(allowed) > 0 {
				// the page regex holds only the names linkable on this page
				cover = nil
				for _, l := range longer[k] {
					if inScope(byKey[l].terms, allowed) {
						cover = append(cover, l)
					}
				}
			}
			if !containsTerm(prose, k, cover) {
				continue
			}
			present = append(present, k)
			if len(allowed) > 0 {
				if c := pickCard(byKey[k].terms, allowed, module); c != "" {
					linked[c] = true // one link to a card per page is enough
				}
			}
		}
		for _, k := range present {
			e := byKey[k]
			if e.reason == "short-latin" && len(e.terms) == 0 {
				// two-letter names (dB) match common words case-insensitively (DB);
				// list them only when the case matches the card's spelling
				if proseCased == "" {
					proseCased = strings.Join(strings.Fields(strings.ReplaceAll(raw, "’", "'")), " ")
				}
				if !containsTerm(proseCased, strings.Join(strings.Fields(e.name), " "), nil) {
					continue
				}
			}
			var cards []string
			for _, t := range e.terms {
				cards = append(cards, t.Card)
			}
			cards = append(cards, e.cards...)
			var reason string
			switch {
			case len(allowed) > 0 && pickCard(e.terms, allowed, module) != "":
				continue // the site links it, even if the name is excluded in another folder
			case e.reason != "":
				reason = e.reason
			case len(allowed) == 0:
				reason = "folder-unscoped"
			case inScope(e.terms, allowed):
				reason = "ambiguous-modules"
			default:
				reason = "out-of-scope"
			}
			skip := false
			for _, c := range cards {
				if c == self || linked[c] {
					skip = true
				}
			}
			if skip {
				continue
			}
			sort.Strings(cards)
			out = append(out, Gap{Path: filepath.ToSlash(fn.Path), Name: e.name, Reason: reason, Cards: cards})
		}
	}
	return out
}
