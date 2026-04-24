package mdfmt

import (
	"bytes"
	"strings"
	"unicode/utf8"
)

// EnsureTrailingNewline implements MD047 — the file must end with
// exactly one newline. Empty files are left empty.
func EnsureTrailingNewline(data []byte) []byte {
	if len(data) == 0 {
		return data
	}
	data = bytes.TrimRight(data, "\r\n")
	return append(data, '\n')
}

// FixHeadingTrailingPunct implements MD026 — strip forbidden trailing
// punctuation from heading lines. forbidden is the set of punct chars
// (e.g. ".,:;。，：；"). Allowed chars like '?' / '!' are intentionally
// not in the set to preserve interrogative / emphatic headings.
func FixHeadingTrailingPunct(lines []string, ctx LineContext, forbidden string) []string {
	out := make([]string, len(lines))
	copy(out, lines)
	for i, line := range out {
		if ctx.Skip[i] || !isHeadingLine(line) {
			continue
		}
		out[i] = stripTrailingPunctFromHeading(line, forbidden)
	}
	return out
}

// FixHeadingBlankLines implements MD022 — ensure every heading has a
// blank line before and after (unless at file boundary). Insertions are
// idempotent: running the rule twice is a no-op.
func FixHeadingBlankLines(lines []string, ctx LineContext) []string {
	if len(lines) == 0 {
		return lines
	}
	out := make([]string, 0, len(lines)+8)
	for i, line := range lines {
		isHdr := !ctx.Skip[i] && isHeadingLine(line)

		if isHdr && len(out) > 0 && !isBlank(out[len(out)-1]) {
			out = append(out, "")
		}
		out = append(out, line)
		if isHdr && i+1 < len(lines) && !isBlank(lines[i+1]) {
			out = append(out, "")
		}
	}
	return out
}

// isHeadingLine reports whether a line is an ATX-style H1–H6. Up to 3
// leading spaces are allowed per CommonMark §4.2.
func isHeadingLine(line string) bool {
	trimmed := strings.TrimLeft(line, " ")
	// CommonMark: no more than 3 spaces of indent before `#`.
	if len(line)-len(trimmed) > 3 {
		return false
	}
	if !strings.HasPrefix(trimmed, "#") {
		return false
	}
	level := 0
	for level < len(trimmed) && trimmed[level] == '#' {
		level++
	}
	if level < 1 || level > 6 {
		return false
	}
	// Must be followed by space or end-of-line (empty heading).
	if level == len(trimmed) {
		return true
	}
	return trimmed[level] == ' '
}

// stripTrailingPunctFromHeading removes forbidden trailing punct runes.
// Whitespace surrounding the punct is also normalized.
func stripTrailingPunctFromHeading(line, forbidden string) string {
	line = strings.TrimRight(line, " \t")
	for len(line) > 0 {
		r, size := utf8.DecodeLastRuneInString(line)
		if !strings.ContainsRune(forbidden, r) {
			break
		}
		line = line[:len(line)-size]
		line = strings.TrimRight(line, " \t")
	}
	return line
}

// isBlank reports whether line contains only whitespace.
func isBlank(line string) bool {
	return strings.TrimSpace(line) == ""
}
