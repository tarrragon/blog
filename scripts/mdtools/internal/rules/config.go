// Package rules defines the toggle-able rule configuration that mirrors
// content/posts/markdown-writing-spec.md. Rule implementations live in
// sibling files; this file holds the shape and defaults only.
//
// When updating defaults here, also update the spec article. The two
// must stay in sync — the spec is the human-readable contract and this
// struct is the machine-readable one.
package rules

// Config is the root configuration passed to every rule check.
type Config struct {
	Headings    HeadingRules
	URLs        URLRules
	Tables      TableRules
	CodeBlocks  CodeBlockRules
	FrontMatter FrontMatterRules
	Cards       CardRules
	LineLength  LineLengthRules
}

// HeadingRules governs §2 of the spec.
type HeadingRules struct {
	AllowH1InBody              bool   // false — front matter title already produces H1
	DuplicatePolicy            string // "siblings_only" | "strict"
	RequireBlankLines          bool   // MD022
	ForbidTrailingPunct        bool   // MD026
	ForbiddenTrailingPunct     string // character set for MD026; defaults to ".,:;。，：；"
	ForbidBoldAsHeading        bool   // MD036
	MaxLevel                   int    // 6
}

// URLRules governs §3 of the spec.
type URLRules struct {
	BareURLPolicy        string   // "shorten-with-identifier" | "shorten-domain-only" | "off"
	AntiPhishingCheck    bool     // R-URL-1 / R-URL-2
	TLDMarkers           []string // triggers anti-phishing domain check
	IdentifierPatterns   []string // regex strings for URL path identifiers (CVE etc.)
	SkipCodeBlockURLs    bool     // true: do not transform URLs inside fenced code blocks
	ApplyToBlockquoteURLs bool    // true: blockquote URLs handled like paragraph URLs
}

// TableRules governs §4 of the spec.
type TableRules struct {
	// Style is one of "aligned" (default) or "compact".
	//   "aligned": every column padded to its max display width using
	//              CJK-aware runewidth; pipes line up vertically.
	//   "compact": single space around each pipe, no padding.
	Style                string
	ForbidAlignmentColon bool // true: `| --- |` without `:` for alignment
}

// CodeBlockRules governs §5.1 (MD040), §5.2 (MD031).
type CodeBlockRules struct {
	RequireLanguage bool // MD040
	RequireBlankLinesAround bool // MD031
}

// FrontMatterRules governs §6 of the spec.
type FrontMatterRules struct {
	// Tier 1: required for every standard content file.
	GlobalRequired []string // e.g. []string{"title", "date"}
	// Tier 1-section: required for Hugo `_index.md` section pages, which
	// don't carry meaningful per-page `date` (they're list landing pages).
	IndexRequired []string // e.g. []string{"title"}
	// Tier 2: recommended — warn on absence, do not block.
	Recommended []string // e.g. []string{"description", "tags"}
	// Tier 3: card-specific required.
	CardRequired []string // e.g. []string{"title", "date", "description", "weight"}
	// Roots whose files carry the Tier 3 schema. Kept separate from
	// Cards.CardsRoot: that one marks the knowledge-card *system* (orphan
	// and K4 structure checks assume a 概念位置 section), while a folder can
	// need the card front-matter schema without being part of that system.
	// content/report/** is the case in point — `weight` orders the list, but
	// the cards carry no 概念位置 section.
	CardPaths []string // e.g. []string{"content/backend/knowledge-cards", "content/report"}
	// Fields explicitly disallowed (warn if present).
	Disallowed []string // e.g. []string{"author", "permalink"}
}

// CardRules governs §7 of the spec.
type CardRules struct {
	CardsRoots             []string // e.g. []string{"content/backend/knowledge-cards", "content/ddd/knowledge-cards"}
	CheckLinkValidity      bool   // L1
	CheckOrphans           bool   // L2
	CheckK4StructureLinks  bool   // L4
	// L5: every Hugo section must be weight all-or-nothing, because a mix
	// silently sinks the unweighted pages below the weighted ones.
	CheckSectionWeightConsistency bool
	// Sections excused from L5 — use when a page is pinned on purpose.
	// An exemption is a decision on record; an omission is not.
	WeightExemptSections []string
	K4ConceptPositionTitle string // heading text that marks the "concept position" section
	ContentScope           string // "content/**"
}

// LineLengthRules governs §5.7 (MD013). Disabled by default.
type LineLengthRules struct {
	Enabled       bool // default false
	SoftLimit     int  // 400 — warn when hit if enabled
	IncludeMarkup bool // true: count markdown syntax chars; false: skip fences/links
}

// Default returns the Config matching the spec defaults as of 2026-04-24.
func Default() Config {
	return Config{
		Headings: HeadingRules{
			AllowH1InBody:          false,
			DuplicatePolicy:        "siblings_only",
			RequireBlankLines:      true,
			ForbidTrailingPunct:    true,
			ForbiddenTrailingPunct: ".,:;。，：；",
			ForbidBoldAsHeading:    true,
			MaxLevel:               6,
		},
		URLs: URLRules{
			BareURLPolicy:         "shorten-with-identifier",
			AntiPhishingCheck:     true,
			TLDMarkers:            []string{".com", ".org", ".gov", ".net", ".io", ".dev", ".tw"},
			IdentifierPatterns:    []string{`CVE-\d{4}-\d+`},
			SkipCodeBlockURLs:     true,
			ApplyToBlockquoteURLs: true,
		},
		Tables: TableRules{
			Style:                "aligned",
			ForbidAlignmentColon: true,
		},
		CodeBlocks: CodeBlockRules{
			RequireLanguage:         true,
			RequireBlankLinesAround: true,
		},
		FrontMatter: FrontMatterRules{
			GlobalRequired: []string{"title", "date"},
			IndexRequired:  []string{"title"},
			Recommended:    []string{"description", "tags"},
			CardRequired:   []string{"title", "date", "description", "weight"},
			CardPaths: []string{
				"content/automation/knowledge-cards",
				"content/backend/knowledge-cards",
				"content/linux/dotfile/knowledge-cards",
				"content/business/knowledge-cards",
				"content/ci/knowledge-cards",
				"content/monitoring/knowledge-cards",
				"content/ddd/knowledge-cards",
				"content/flutter/knowledge-cards",
				"content/infra/knowledge-cards",
				"content/llm/knowledge-cards",
				"content/report",
				"content/testing/knowledge-cards",
				"content/ux-design/knowledge-cards",
			},
			Disallowed:     []string{"author", "permalink"},
		},
		Cards: CardRules{
			CardsRoots: []string{
				"content/automation/knowledge-cards",
				"content/backend/knowledge-cards",
				"content/linux/dotfile/knowledge-cards",
				"content/business/knowledge-cards",
				"content/ci/knowledge-cards",
				"content/monitoring/knowledge-cards",
				"content/ddd/knowledge-cards",
				"content/flutter/knowledge-cards",
				"content/infra/knowledge-cards",
				"content/llm/knowledge-cards",
				"content/testing/knowledge-cards",
				"content/ux-design/knowledge-cards",
			},
			CheckLinkValidity:             true,
			CheckOrphans:                  true,
			CheckK4StructureLinks:         true,
			CheckSectionWeightConsistency: true,
			WeightExemptSections: []string{
				// modern-cli-replacements is the section's overview article
				// and is pinned above the otherwise date-sorted tool posts.
				"content/linux/tools/cli",
			},
			K4ConceptPositionTitle: "概念位置",
			ContentScope:           "content",
		},
		LineLength: LineLengthRules{
			Enabled:       false,
			SoftLimit:     400,
			IncludeMarkup: true,
		},
	}
}
