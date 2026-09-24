package mdlint

import (
	"strings"

	"blog/scripts/mdtools/internal/mdfmt"
	"blog/scripts/mdtools/internal/report"
)

// abbreviatedTerms lists compressed terms that engineering readers cannot
// decode, each with the expansion to write instead.
//
//	判準 — short for 判斷標準. The word does exist in philosophy of science
//	(分界判準) and educational assessment (評分判準, a rubric), but five
//	independent low-tier model probes all reported it as unrecognisable in
//	an engineering register (#289). A site-wide replacement once removed
//	3007 occurrences, and 654 had grown back within a month because nothing
//	stopped the word at write time — this rule is that stop.
//
// The rule errors rather than warns: no engineering sentence needs the
// abbreviation, so a hit is a verdict, not a candidate. Discussing the word
// itself stays possible by quoting it (「判準」) or putting it in inline code.
var abbreviatedTerms = []struct {
	term      string
	expansion string
}{
	{"判準", "判斷標準（狀態義寫「X 條件」，例如停止判準 → 停止條件）"},
}

func checkAbbreviatedTerms(path string, lines []string, ctx mdfmt.LineContext) []report.Violation {
	var out []report.Violation
	for i, line := range lines {
		if ctx.Skip[i] {
			continue
		}
		for _, t := range abbreviatedTerms {
			for off := 0; ; {
				j := strings.Index(line[off:], t.term)
				if j < 0 {
					break
				}
				idx := off + j
				off = idx + len(t.term)
				if quotedAt(line, idx) || inlineCodeAt(line, idx) {
					continue
				}
				out = append(out, report.Violation{
					Path:    path,
					Line:    i + 1,
					Rule:    "TERM-abbreviation",
					Level:   report.LevelError,
					Message: "「" + t.term + "」is an abbreviation engineering readers cannot decode; write " + t.expansion + ". To discuss the word itself, quote it with 「」 or inline code.",
				})
			}
		}
	}
	return out
}
