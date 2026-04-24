// Package mdlint implements structural and schema checks for mdtools
// lint. Unlike mdfmt, these rules only report; they never rewrite.
// Checks requiring full AST analysis (anti-phishing R-URL, MD036 bold
// as heading) are deferred to a later phase and will land here.
package mdlint

import (
	"os"
	"strings"

	"blog/scripts/mdtools/internal/mdfmt"
	"blog/scripts/mdtools/internal/report"
	"blog/scripts/mdtools/internal/rules"
)

// Check runs all enabled lint rules against path and returns the
// accumulated violations. Callers typically aggregate across many
// files and pass the collected set to a report.Reporter.
func Check(path string, cfg rules.Config) ([]report.Violation, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	lines := splitLines(data)
	ctx := mdfmt.AnalyzeLines(lines)

	var out []report.Violation

	if !cfg.Headings.AllowH1InBody {
		out = append(out, checkH1Ban(path, lines, ctx)...)
	}
	if cfg.Headings.DuplicatePolicy == "siblings_only" {
		out = append(out, checkHeadingDuplicates(path, lines, ctx)...)
	}
	if cfg.CodeBlocks.RequireLanguage {
		out = append(out, checkCodeBlockLanguage(path, lines, ctx)...)
	}
	// MD010 prose-tab: warn on tab characters outside fenced code
	// blocks / front matter. Code block tabs are legitimate Go source
	// indentation, so the rule is scoped to plain content lines.
	out = append(out, checkProseTabs(path, lines, ctx)...)
	// Front matter schema check always runs; rules.Config.FrontMatter
	// describes which fields are required / recommended / disallowed.
	out = append(out, checkFrontMatter(path, lines, cfg.FrontMatter, cfg.Cards.CardsRoot)...)

	// AST-guided checks share one parser invocation per file; keep
	// them grouped together so we only pay the goldmark cost once.
	if cfg.Headings.ForbidBoldAsHeading {
		out = append(out, checkEmphasisAsHeading(path, data)...)
	}
	if cfg.URLs.AntiPhishingCheck {
		out = append(out, checkAntiPhishingURLs(path, data, cfg.URLs)...)
	}

	return out, nil
}

// splitLines mirrors mdfmt's splitLines to avoid a cyclic import for a
// one-liner utility. Keeping it local allows mdlint to consume bytes
// read from disk without pulling in mdfmt's Fixer API.
func splitLines(data []byte) []string {
	if len(data) == 0 {
		return nil
	}
	s := string(data)
	if strings.HasSuffix(s, "\n") {
		s = strings.TrimRight(s, "\n")
	}
	if s == "" {
		return []string{}
	}
	return strings.Split(s, "\n")
}
