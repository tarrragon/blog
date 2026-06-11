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
//	detect than a dead link.
//
//	REF2-count-in-name — headings and front-matter titles that bake a
//	member count into a collection name（「六大原則」「核心七問」）。The
//	count is a derivation of current membership and goes stale on the
//	first add / remove. Scope is headings / titles only, where the
//	string acts as a canonical name; inline counts that sit right next
//	to their list stay out of scope.
//
// Matches immediately preceded by 「 are skipped in both rules — the
// repo convention for quoting an anti-example is to wrap it in 「」.
var (
	positionalAnchorRe = regexp.MustCompile(`(?:見|詳見|參見|如)[^。\n「」]{0,6}?第\s*[一二三四五六七八九十0-9]+\s*(?:章|節|點|步|輪|段)|§\s*[0-9]`)
	countInNameRe      = regexp.MustCompile(`[0-9一二三四五六七八九十]+\s*大\s*(?:支柱|原則|步驟|階段|面向|心法)|[0-9一二三四五六七八九十]+\s*(?:支柱|原則|步驟|階段)`)
)

// quotedAt reports whether the byte right before idx is the opening
// corner bracket 「 (U+300C, bytes E3 80 8C) — i.e. the match is being
// quoted as an example rather than used as a live reference.
func quotedAt(line string, idx int) bool {
	return idx >= 3 && line[idx-3:idx] == "「"
}

// precededByDi reports whether the rune right before idx is 第, which
// turns a count-in-name candidate（三階段）into an ordinal（第三階段）
// that REF2 does not target.
func precededByDi(line string, idx int) bool {
	return idx >= 3 && line[idx-3:idx] == "第"
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
