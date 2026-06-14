package mdlint

import (
	"regexp"

	"blog/scripts/mdtools/internal/mdfmt"
	"blog/scripts/mdtools/internal/report"
)

// checkNegationLead implements a warning-level candidate scan from the
// positive-statement card（#166 重點優先陳述是跨語言的資訊結構原則）.
// It reports candidates, not verdicts — whether a hit is a real
// lead-with-the-point violation (is the core concept buried after 而是?)
// requires reading the sentence, so the rule never escalates to error.
//
//	POS-negation-lead — 「不是 X、而是 Y」「與其 X、不如 Y」: prose that
//	opens on a negated wrong understanding and pushes the core concept
//	(Y) after 而是 / 不如. The information-structure cost is real: the
//	reader processes a rejected X before reaching the point. The defect
//	is cross-language (English "not X but Y", Japanese "X ではなく Y"),
//	so the signal is the sentence shape, not a Chinese-specific token —
//	detection is mechanizable but the judgment is not. The regex covers
//	the 而是 / 「— 是」/ 不如 connectives, but enumerating variants is
//	inherently incomplete (#166): the real judgment is whether the core
//	concept leads, not which connective appears — a missed variant just
//	keeps a candidate silent until a reader catches it (which is exactly
//	how 「不是 X — 是 Y」 slipped past the first version of this rule).
//
// Two legitimate forms stay out of scope and are handled by exemptions:
// anti-example citations wrapped in 「」 (skipped via quotedAt, e.g. the
// spec and report cards that quote the pattern), and contrast inside an
// explicit 反例 / 對照 section (#94) — that judgment is left to the
// reader, which is why the rule only warns.
var negationLeadRe = regexp.MustCompile(`不是[^。\n「」]{0,30}而是|不是[^。\n「」—–]{0,25}[—–]\s*是|與其[^。\n「」]{0,25}不如`)

func checkNegationLead(path string, lines []string, ctx mdfmt.LineContext) []report.Violation {
	var out []report.Violation
	for i, line := range lines {
		if ctx.Skip[i] {
			continue
		}
		for _, loc := range negationLeadRe.FindAllStringIndex(line, -1) {
			if quotedAt(line, loc[0]) {
				continue
			}
			out = append(out, report.Violation{
				Path:    path,
				Line:    i + 1,
				Rule:    "POS-negation-lead",
				Level:   report.LevelWarn,
				Message: "negation-lead candidate (不是 X 而是 Y / 與其 X 不如 Y); the core concept is pushed after 而是/不如 — lead with the point when this builds a concept (explicit anti-example contrast in a 反例 section is exempt, and 「」-quoted citations are auto-skipped)",
			})
		}
	}
	return out
}
