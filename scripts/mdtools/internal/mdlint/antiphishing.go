package mdlint

import (
	"fmt"
	"net/url"
	"strings"

	"github.com/yuin/goldmark/ast"

	"blog/scripts/mdtools/internal/astutil"
	"blog/scripts/mdtools/internal/report"
	"blog/scripts/mdtools/internal/rules"
)

// checkAntiPhishingURLs implements §3.2 R-URL-1 / R-URL-2:
//
//	R-URL-1: when the link display text contains a TLD marker (.com,
//	         .org, .gov, ...), the display-text domain must equal the
//	         href domain.
//	R-URL-2: when the display text has no TLD marker, it's treated as
//	         descriptive prose and not domain-checked.
//
// Guards against the classic `[nvd.nist.gov](https://malicious/fake)`
// pattern: display text looks authoritative, href is anywhere. Raw
// regex can't pull display text / href cleanly; AST gives both.
func checkAntiPhishingURLs(path string, data []byte, cfg rules.URLRules) []report.Violation {
	if !cfg.AntiPhishingCheck {
		return nil
	}
	parser := astutil.NewParser()
	doc := parser.Parse(data)

	var out []report.Violation
	ast.Walk(doc, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
		if !entering {
			return ast.WalkContinue, nil
		}
		link, ok := n.(*ast.Link)
		if !ok {
			return ast.WalkContinue, nil
		}
		dest := string(link.Destination)
		// Only care about absolute URLs; relative paths don't phish.
		if !strings.HasPrefix(dest, "http://") && !strings.HasPrefix(dest, "https://") {
			return ast.WalkContinue, nil
		}
		displayText := extractLinkText(link, data)
		displayDomain := extractDomainFromDisplay(displayText, cfg.TLDMarkers)
		if displayDomain == "" {
			// R-URL-2 — no domain-looking token ending in a TLD marker.
			// Descriptive text; phishing check doesn't apply.
			return ast.WalkContinue, nil
		}
		hrefDomain := extractDomainFromURL(dest)
		if hrefDomain == "" {
			return ast.WalkContinue, nil
		}
		if !domainsMatch(displayDomain, hrefDomain) {
			out = append(out, report.Violation{
				Path:  path,
				Line:  nodeStartLine(link, data),
				Rule:  "R-URL-1-display-href-mismatch",
				Level: report.LevelError,
				Message: fmt.Sprintf(
					"link display text %q implies domain %q but href points to %q",
					displayText, displayDomain, hrefDomain,
				),
			})
		}
		return ast.WalkContinue, nil
	})
	return out
}

// extractLinkText returns the plain-text content of a Link node.
// Nested formatting is flattened; code spans and inline HTML content
// contribute their text.
func extractLinkText(link *ast.Link, src []byte) string {
	var b strings.Builder
	for child := link.FirstChild(); child != nil; child = child.NextSibling() {
		collectText(child, src, &b)
	}
	return b.String()
}

func collectText(n ast.Node, src []byte, b *strings.Builder) {
	switch v := n.(type) {
	case *ast.Text:
		b.Write(v.Segment.Value(src))
	case *ast.CodeSpan:
		for c := v.FirstChild(); c != nil; c = c.NextSibling() {
			collectText(c, src, b)
		}
	default:
		for c := n.FirstChild(); c != nil; c = c.NextSibling() {
			collectText(c, src, b)
		}
	}
}

// extractDomainFromDisplay returns a domain-looking token from display
// text if and only if it ends with one of the configured TLD markers.
//
// The suffix requirement avoids false positives on identifiers that
// merely contain a TLD substring. `re.compile` includes `.com` as a
// substring but doesn't end in `.com`, so it's correctly treated as a
// non-domain phrase. Only real tokens like `example.com`,
// `docs.example.com/path` qualify.
func extractDomainFromDisplay(s string, tldMarkers []string) string {
	lower := strings.ToLower(s)
	var candidates []string
	var current strings.Builder
	for i := 0; i <= len(lower); i++ {
		if i < len(lower) && isDomainChar(lower[i]) {
			current.WriteByte(lower[i])
			continue
		}
		c := strings.Trim(current.String(), ".-")
		current.Reset()
		if strings.Contains(c, ".") {
			candidates = append(candidates, c)
		}
	}
	for _, c := range candidates {
		for _, m := range tldMarkers {
			if strings.HasSuffix(c, strings.ToLower(m)) {
				return c
			}
		}
	}
	return ""
}

func isDomainChar(b byte) bool {
	switch {
	case b >= 'a' && b <= 'z':
		return true
	case b >= '0' && b <= '9':
		return true
	case b == '.' || b == '-':
		return true
	}
	return false
}

// extractDomainFromURL parses rawURL and returns its host lower-cased,
// with leading `www.` removed for comparison purposes.
func extractDomainFromURL(rawURL string) string {
	u, err := url.Parse(rawURL)
	if err != nil || u.Host == "" {
		return ""
	}
	return strings.TrimPrefix(strings.ToLower(u.Host), "www.")
}

// domainsMatch reports whether display-derived domain is compatible
// with href-derived host. A subdomain match counts: displayDomain may
// be a suffix of hrefDomain or equal.
//
// Examples (match):
//
//	display "nvd.nist.gov" / href "nvd.nist.gov" ✓
//	display "example.com"  / href "docs.example.com" ✓ (display is suffix)
//	display "docs.example.com" / href "example.com" ✓ (href is suffix)
//
// Non-match: different TLDs or brand-spoofing hosts.
func domainsMatch(displayDomain, hrefDomain string) bool {
	if displayDomain == hrefDomain {
		return true
	}
	if strings.HasSuffix(hrefDomain, "."+displayDomain) {
		return true
	}
	if strings.HasSuffix(displayDomain, "."+hrefDomain) {
		return true
	}
	return false
}
