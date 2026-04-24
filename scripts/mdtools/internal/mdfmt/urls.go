package mdfmt

import (
	"fmt"
	"net/url"
	"regexp"
	"strings"

	"blog/scripts/mdtools/internal/rules"
)

// bareURLRe matches an HTTP(S) URL candidate. RE2 has no lookbehind, so
// context checks (already inside a markdown link, inline code, angle
// brackets) are handled after the match by maskedRanges.
//
// URL end is aggressive here — we include punctuation that's often at
// the end, then trim trailing "." / "," / ";" / ":" / "!" / "?" in
// findURLEnd below. This matches CommonMark autolink-ish behavior.
var bareURLRe = regexp.MustCompile(`https?://[^\s<>\]]+`)

// linkSpanRe matches `[...](...)` markdown links so we can mask out the
// URL inside. Not recursive; good enough for our content.
var linkSpanRe = regexp.MustCompile(`\[[^\]\n]*\]\([^)\n]*\)`)

// angleSpanRe matches `<...>` autolinks/HTML so URLs inside are skipped.
var angleSpanRe = regexp.MustCompile(`<[^<>\n]*>`)

// inlineCodeRe matches single- and double-backtick inline code spans.
// URLs inside code are preserved as typed.
var inlineCodeRe = regexp.MustCompile("`[^`\n]*`")

// FixBareURLs implements MD034 (§3.1 of the spec) — replace bare URLs
// with shortened markdown links. Line-based with inline-code and
// markdown-link masking; LineContext.Skip handles front matter and
// fenced code blocks.
func FixBareURLs(lines []string, ctx LineContext, cfg rules.URLRules) []string {
	if cfg.BareURLPolicy == "off" {
		return lines
	}
	idPatterns := compileIdentifierPatterns(cfg.IdentifierPatterns)
	out := make([]string, len(lines))
	copy(out, lines)
	for i := range out {
		if ctx.Skip[i] {
			continue
		}
		out[i] = rewriteBareURLsInLine(out[i], cfg, idPatterns)
	}
	return out
}

func compileIdentifierPatterns(patterns []string) []*regexp.Regexp {
	out := make([]*regexp.Regexp, 0, len(patterns))
	for _, p := range patterns {
		if re, err := regexp.Compile(p); err == nil {
			out = append(out, re)
		}
	}
	return out
}

// rewriteBareURLsInLine finds bare URLs in line, skipping ones already
// inside `[..](..)`, `<..>`, or `` `..` ``, and rewrites them to
// shortened markdown links.
func rewriteBareURLsInLine(line string, cfg rules.URLRules, idPatterns []*regexp.Regexp) string {
	masked := collectMaskedRanges(line)
	matches := bareURLRe.FindAllStringIndex(line, -1)
	if len(matches) == 0 {
		return line
	}

	var b strings.Builder
	cursor := 0
	for _, m := range matches {
		start, end := m[0], m[1]
		// Trim trailing sentence punctuation that commonly abuts a URL.
		end = trimURLTrailPunct(line, start, end)

		b.WriteString(line[cursor:start])
		if inMasked(masked, start) {
			// URL is inside an existing link/code/angle span; leave as-is.
			b.WriteString(line[start:end])
		} else {
			rawURL := line[start:end]
			display := shortenURL(rawURL, cfg, idPatterns)
			fmt.Fprintf(&b, "[%s](%s)", display, rawURL)
		}
		cursor = end
	}
	b.WriteString(line[cursor:])
	return b.String()
}

// maskedRange marks a byte range that URL rewriting must skip.
type maskedRange struct{ start, end int }

func collectMaskedRanges(line string) []maskedRange {
	var out []maskedRange
	for _, m := range linkSpanRe.FindAllStringIndex(line, -1) {
		out = append(out, maskedRange{m[0], m[1]})
	}
	for _, m := range angleSpanRe.FindAllStringIndex(line, -1) {
		out = append(out, maskedRange{m[0], m[1]})
	}
	for _, m := range inlineCodeRe.FindAllStringIndex(line, -1) {
		out = append(out, maskedRange{m[0], m[1]})
	}
	return out
}

func inMasked(ranges []maskedRange, pos int) bool {
	for _, r := range ranges {
		if pos >= r.start && pos < r.end {
			return true
		}
	}
	return false
}

// trimURLTrailPunct trims sentence-ending punctuation from the URL end.
// CommonMark's autolink boundary logic does similar to avoid eating a
// period or comma that belongs to the surrounding sentence.
func trimURLTrailPunct(line string, start, end int) int {
	for end > start {
		c := line[end-1]
		switch c {
		case '.', ',', ';', ':', '!', '?', ')':
			end--
			continue
		}
		break
	}
	return end
}

// shortenURL reduces rawURL to a concise display text per §3.1:
//   - Identifier match in path  →  domain.com/identifier
//   - No identifier match       →  domain.com
//
// Policy "shorten-domain-only" forces the domain-only form regardless
// of identifier match. Invalid URLs fall back to the raw string.
func shortenURL(rawURL string, cfg rules.URLRules, idPatterns []*regexp.Regexp) string {
	u, err := url.Parse(rawURL)
	if err != nil || u.Host == "" {
		return rawURL
	}
	domain := strings.TrimPrefix(u.Host, "www.")

	if cfg.BareURLPolicy == "shorten-domain-only" {
		return domain
	}
	// Default: shorten-with-identifier.
	if id := matchIdentifier(u.Path, idPatterns); id != "" {
		return domain + "/" + id
	}
	return domain
}

func matchIdentifier(path string, idPatterns []*regexp.Regexp) string {
	for _, re := range idPatterns {
		if m := re.FindString(path); m != "" {
			return m
		}
	}
	return ""
}
