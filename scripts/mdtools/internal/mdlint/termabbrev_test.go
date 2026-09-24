package mdlint

import (
	"testing"

	"blog/scripts/mdtools/internal/mdfmt"
)

func abbrevHits(lines []string) int {
	ctx := mdfmt.AnalyzeLines(lines)
	return len(checkAbbreviatedTerms("f.md", lines, ctx))
}

func TestAbbreviatedTermsFiresOnBareProse(t *testing.T) {
	cases := []struct {
		name string
		line string
		want int
	}{
		{"bare noun fires", "這條判準只問一句話。", 1},
		{"compound fires", "停止判準寫在最後。", 1},
		{"two hits on one line both fire", "判準一與判準二並列。", 2},
		{"expanded form is clean", "這條判斷標準只問一句話。", 0},
		{"quoted discussion is exempt", "「判準」是真實存在的中文詞。", 0},
		{"inline code is exempt", "掃描用 `rg 判準` 找出殘留。", 0},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			lines := []string{"---", "title: \"t\"", "---", "", tc.line}
			if got := abbrevHits(lines); got != tc.want {
				t.Errorf("hits = %d, want %d for %q", got, tc.want, tc.line)
			}
		})
	}
}

func TestAbbreviatedTermsSkipsFencedCode(t *testing.T) {
	lines := []string{"---", "title: \"t\"", "---", "", "```text", "判準", "```"}
	if got := abbrevHits(lines); got != 0 {
		t.Errorf("fenced code produced %d hits, want 0", got)
	}
}
