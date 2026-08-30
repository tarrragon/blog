package mdlint

import (
	"regexp"
	"unicode/utf8"

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
//	the 而是 / 「— 是」/ 「，是」/ 「、是」/ 不在…而在 / 不如 connectives,
//	but enumerating variants is inherently incomplete (#166): the real
//	judgment is whether the core concept leads, not which connective
//	appears — a missed variant just keeps a candidate silent until a
//	reader catches it (which is exactly how 「不是 X — 是 Y」,
//	「不在 X、而在 Y」 and the bare-comma 「不是 X，是 Y」 each slipped past
//	an earlier version of this rule, caught later by adversarial review).
//
//	The bare-comma form needs guards the 而是 form does not. Its middle
//	excludes ，and 、 so a match cannot span clauses, and two preceding
//	runes disqualify it (see precededBy). An earlier version also excluded
//	因 on the Y side, on the theory that 「不是 X，是因為 Z」 explains a
//	cause rather than correcting a definition — that was wrong and cost
//	ten real hits: 「不是因為 attention、是因為 residual + LayerNorm」 puts
//	two parallel causes side by side and buries the point in the second,
//	which is the canonical shape this rule exists to surface.
//	One shape stays imprecise on purpose: a 是 whose subject is the whole
//	preceding clause (「哪些不是自己說了算，是排序問題」) looks identical to
//	a corrected object and would need parsing to separate. The rule warns
//	rather than errors, so a reader settles it.
//
// Three legitimate forms stay out of scope and are handled by exemptions:
// anti-example citations wrapped in 「」 (skipped via quotedAt, e.g. the
// spec and report cards that quote the pattern), inline code spans
// (skipped via inlineCodeAt — grep patterns and regex are technical
// content, not prose), and contrast inside an explicit 反例 / 對照
// section (#94) — that judgment is left to the reader, which is why
// the rule only warns.
var negationLeadRe = regexp.MustCompile(`不是[^。\n「」]{0,30}而是|不是[^。\n「」—–]{0,25}[—–]\s*是|不是[^。\n「」，、]{1,25}[，、]\s*是|不在[^。\n「」]{0,30}而在|與其[^。\n「」]{0,25}不如`)

// precededBy reports whether the rune immediately before idx is any of
// the given runes. Two of them disqualify a 不是 from leading a negation:
//
//   - 是 — 「是不是」 is the interrogative, not a negated definition.
//   - 而 — 「A 而不是 B」 puts the negation *after* the point, which is the
//     shape this rule wants writers to reach. A bare-comma match that
//     starts inside 而不是 therefore reports the correct form as a defect
//     (「放在 </body> 前、而不是 <head> 裡，是為了…」), and the 是 it lands
//     on takes the whole preceding clause as its subject.
func precededBy(line string, idx int, runes ...rune) bool {
	if idx == 0 {
		return false
	}
	r, size := utf8.DecodeLastRuneInString(line[:idx])
	if size == 0 {
		return false
	}
	for _, want := range runes {
		if r == want {
			return true
		}
	}
	return false
}

func checkNegationLead(path string, lines []string, ctx mdfmt.LineContext) []report.Violation {
	var out []report.Violation
	for i, line := range lines {
		if ctx.Skip[i] {
			continue
		}
		for _, loc := range negationLeadRe.FindAllStringIndex(line, -1) {
			if quotedAt(line, loc[0]) || inlineCodeAt(line, loc[0]) {
				continue
			}
			if precededBy(line, loc[0], '是', '而') {
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
