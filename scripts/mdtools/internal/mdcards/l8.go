package mdcards

import (
	"fmt"
	"path/filepath"
	"regexp"
	"strings"

	"blog/scripts/mdtools/internal/report"
)

// slugFieldRe captures the value of a front-matter `slug:` field, with or
// without surrounding quotes. Anchored to the start of a line so a `slug:`
// nested under another key cannot match.
var slugFieldRe = regexp.MustCompile(`(?m)^slug:[ \t]*["']?([^"'\r\n]*?)["']?[ \t]*$`)

// checkL8SlugFilenameAlignment flags pages whose `slug` disagrees with
// their filename.
//
// Hugo builds a page's URL from `slug` when the field is present. Every
// other consumer in this repo resolves links the other way: L1 walks the
// filesystem and matches on filename, `mdtools fmt` never looks at slug,
// and a human writing a cross-file link copies the filename they see in
// the tree. The two agree for free — until a page carries a slug that
// spells its own name differently.
//
// The failure that motivated this check (measured 2026-08-04): seven pages
// under content/macos/ used underscored filenames and hyphenated slugs.
// Hugo published them at `/macos/macos-apfs-volume-structure/` while all
// 45 inbound links spelled the underscores. L1 reported zero violations
// throughout, because on disk the targets exist and L1 only ever asked
// that question.
//
// This is the exact shape L5's sibling rules exist to prevent: a check
// whose clean output is indistinguishable from "nobody looked at this
// axis". L1's success is honest about what it verified — the file is
// there — and silent about the URL that will actually be served.
//
// Scope is the whole content tree the CLI was handed (g.Files), not
// cfg.Cards.CardsRoots: a slug governs the URL of any page, not only of a
// card. Stated here because scope is a fact independent of the rule, and
// an unstated one is indistinguishable from an inherited default.
//
// Known boundary — what this rule does NOT cover, measured 2026-08-04:
//
//   - Pages with no `slug` at all: 2758 of 3079 non-index pages. They exit
//     at the `m == nil` guard below. markdown-writing-spec requires slug on
//     every page, and no rule in lint or cards enforces that requirement,
//     so a green run here says nothing about it.
//   - The absent-slug fallback is section-dependent, and only one side is
//     harmless. Sections with no `[permalinks]` template fall back to the
//     filename, which is what every link already spells; all 2758 pages
//     above are in these. Sections that DO have a template built from
//     `:slug` — posts, work-log, record, other in this repo's hugo.toml —
//     fall back to a urlized *title* instead, which for CJK titles is a
//     percent-encoded string no link ever spells. Those four sections are
//     at full slug coverage as of 2026-08-04 (183 of 183 routes match
//     their filename), so this failure mode currently has zero stock; it
//     had 173 pages and 663 dead inbound links when the rule landed.
//
// Nothing prevents the next new page in those four sections from omitting
// slug and reintroducing it. The regression check and the numbers live in
// markdown-writing-spec ("L8 的沉默區"); this comment is a copy and will
// drift, so treat that section as the source.
//
// Reported at error level: all 148 pages that carry a slug satisfied it
// when the rule landed, so anything it reports is new breakage rather than
// debt to work down. A page that genuinely wants a URL different from its
// filename should be renamed instead; the alternative (keeping both
// spellings and remembering which one links use) is the state this rule
// removes.
//
// `_index.md` is exempt: its slug names the section it heads, not a page
// within it, so alignment with the literal string `_index` is meaningless.
// The flip side is that a wrong slug on `_index.md` silently re-routes the
// whole section and this rule will not see it.
func checkL8SlugFilenameAlignment(g *Graph) []report.Violation {
	var out []report.Violation

	for _, fn := range g.Files {
		if isSectionIndex(fn.Path) {
			continue
		}
		m := slugFieldRe.FindSubmatch(frontMatterOf(fn.Src))
		if m == nil {
			continue
		}
		slug := strings.TrimSpace(string(m[1]))
		if slug == "" {
			continue
		}
		stem := strings.TrimSuffix(filepath.Base(fn.Path), ".md")
		if slug == stem {
			continue
		}

		out = append(out, report.Violation{
			Path:  fn.Path,
			Line:  slugLine(fn.Src),
			Rule:  "L8-slug-filename-alignment",
			Level: report.LevelError,
			Message: fmt.Sprintf(
				"slug %q disagrees with filename %q; Hugo serves this page at the slug "+
					"while every link in the repo is written from the filename, so inbound "+
					"links 404 while L1 still passes. Set slug to %q, or rename the file to %q.",
				slug, stem, stem, slug+".md"),
		})
	}
	return out
}

// slugLine returns the 1-based line of the front-matter `slug:` field, so
// the report points at the field rather than at the file. Returns 0 when
// the field is not in front matter, matching the whole-file convention.
func slugLine(src []byte) int {
	fm := frontMatterOf(src)
	if len(fm) == 0 {
		return 0
	}
	for i, line := range strings.Split(string(fm), "\n") {
		if slugFieldRe.MatchString(line) {
			return i + 2 // +1 for 1-based, +1 for the opening `---`
		}
	}
	return 0
}
