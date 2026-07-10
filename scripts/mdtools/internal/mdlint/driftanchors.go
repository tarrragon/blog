package mdlint

import (
	"regexp"
	"strings"

	"blog/scripts/mdtools/internal/mdfmt"
	"blog/scripts/mdtools/internal/report"
)

// checkDriftAnchors implements two warning-level candidate scans from
// the reference-discipline cards（#155 引用用語意標題 / #156 命名不內
// 嵌數量）。Both report candidates, not verdicts — frozen external
// numbering (RFC sections, statute articles) and counts adjacent to
// their own list are legitimate, so the rules never escalate to error.
//
//	REF1-positional-anchor — prose that anchors a reference on document
//	position（「見第 3 點」「詳見第五章」「§4」）。Position numbers are
//	derivations of the current layout: after a reorder the reference
//	resolves to the wrong target without breaking, which is harder to
//	detect than a dead link. A § whose line cites an RFC / ISO / IEEE
//	document is exempt: that numbering is frozen by the spec's publisher
//	and survives any reorder of ours.
//
//	REF2-count-in-name — headings and front-matter titles that bake a
//	member count into a collection name（「六大原則」「核心七問」）。The
//	count is a derivation of current membership and goes stale on the
//	first add / remove. Scope is headings / titles only, where the
//	string acts as a canonical name; inline counts that sit right next
//	to their list stay out of scope.
//
// Matches inside a 「」 span are skipped in both rules — the repo
// convention for quoting an anti-example is to wrap it in 「」.
var (
	positionalAnchorRe = regexp.MustCompile(`(?:見|詳見|參見|如)[^。\n「」]{0,6}?第\s*[一二三四五六七八九十0-9]+\s*(?:章|節|點|步|輪|段)|§\s*[0-9]`)
	countInNameRe      = regexp.MustCompile(`[0-9一二三四五六七八九十]+\s*大\s*(?:支柱|原則|步驟|階段|面向|心法)|[0-9一二三四五六七八九十]+\s*(?:支柱|原則|步驟|階段)`)

	// frozenSpecRe marks a line as citing externally frozen numbering
	// (RFC / ISO / IEEE section numbers). Their §N is a stable
	// identifier published by the spec author, not a derivation of our
	// own layout, so REF1 does not apply to it.
	frozenSpecRe = regexp.MustCompile(`(?i)(?:RFC|STD|BCP|ECMA|IEEE)[\s-]*[0-9]+|ISO(?:/IEC)?[\s-]*[0-9]+`)
)

// quotedAt reports whether byte position idx falls inside a 「」 span
// (U+300C … U+300D) on this line — i.e. the match is being quoted as an
// example rather than used as a live reference. Only balanced spans
// count: an unclosed 「 leaves the rest of the line unquoted, so a
// stray bracket cannot silence the rest of the file's prose.
//
// Membership, not adjacency, is the test. Quoted anti-examples carry
// their own emphasis and inner quotes (「核心責任**不是** X、**而是** Y」,
// 「高階函式不是『用了比較高級』、而是…」), so the match rarely starts on
// the byte right after 「.
func quotedAt(line string, idx int) bool {
	const open, close = "「", "」"
	depth, start := 0, 0
	for i := 0; i+3 <= len(line); {
		switch line[i : i+3] {
		case open:
			if depth == 0 {
				start = i
			}
			depth++
			i += 3
		case close:
			if depth > 0 {
				depth--
				if depth == 0 && idx > start && idx < i {
					return true
				}
			}
			i += 3
		default:
			i++
		}
	}
	return false
}

// inlineCodeAt reports whether byte position idx falls inside a
// backtick-delimited inline code span (`...`). Matches inside inline
// code are technical content (grep patterns, regex, identifiers), not
// prose — they should not trigger prose-quality lint rules.
func inlineCodeAt(line string, idx int) bool {
	inside := false
	for i := 0; i < len(line); {
		if line[i] == '`' {
			if i == idx {
				return inside
			}
			inside = !inside
			i++
			continue
		}
		if i == idx {
			return inside
		}
		i++
	}
	return false
}

// precededByOrdinalPrefix reports whether the rune right before idx is
// 第 or 下, which turns a count-in-name candidate into an ordinal
// (第三階段) or a sequential reference (下一階段 = "next phase") that
// REF2 does not target.
func precededByDi(line string, idx int) bool {
	return idx >= 3 && (line[idx-3:idx] == "第" || line[idx-3:idx] == "下")
}

func checkDriftAnchors(path string, lines []string, ctx mdfmt.LineContext) []report.Violation {
	var out []report.Violation

	inFrontMatter := false
	for i, line := range lines {
		// Front-matter title lines carry canonical names, so REF2
		// applies to them even though ctx.Skip is true there.
		if i == 0 && strings.TrimSpace(line) == "---" {
			inFrontMatter = true
			continue
		}
		if inFrontMatter {
			if strings.TrimSpace(line) == "---" {
				inFrontMatter = false
				continue
			}
			if strings.HasPrefix(strings.TrimSpace(line), "title:") {
				out = append(out, scanCountInName(path, i, line)...)
			}
			continue
		}
		if ctx.Skip[i] {
			continue
		}

		trimmed := strings.TrimSpace(line)
		isHeading := strings.HasPrefix(trimmed, "#")

		for _, loc := range positionalAnchorRe.FindAllStringIndex(line, -1) {
			if quotedAt(line, loc[0]) {
				continue
			}
			// A § on a line that cites an RFC / ISO / IEEE document is
			// that spec's own frozen numbering. The 見第 N 章 form never
			// refers to an external spec, so it stays in scope here.
			if strings.HasPrefix(line[loc[0]:], "§") && frozenSpecRe.MatchString(line) {
				continue
			}
			out = append(out, report.Violation{
				Path:    path,
				Line:    i + 1,
				Rule:    "REF1-positional-anchor",
				Level:   report.LevelWarn,
				Message: "positional reference candidate; anchor on the target's semantic title when it is a living document (frozen external numbering like RFC sections is exempt)",
			})
		}

		if isHeading {
			out = append(out, scanCountInName(path, i, line)...)
		}
	}
	return out
}

func scanCountInName(path string, lineIdx int, line string) []report.Violation {
	var out []report.Violation
	for _, loc := range countInNameRe.FindAllStringIndex(line, -1) {
		if quotedAt(line, loc[0]) || precededByDi(line, loc[0]) {
			continue
		}
		out = append(out, report.Violation{
			Path:    path,
			Line:    lineIdx + 1,
			Rule:    "REF2-count-in-name",
			Level:   report.LevelWarn,
			Message: "count-bearing collection name in heading/title; name by role and let the list carry the count (externally frozen brands like SOLID are exempt)",
		})
	}
	return out
}
