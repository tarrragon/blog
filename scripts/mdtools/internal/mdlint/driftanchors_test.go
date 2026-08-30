package mdlint

import (
	"testing"

	"blog/scripts/mdtools/internal/mdfmt"
)

// ruleNames runs checkDriftAnchors / checkNegationLead over a single
// prose line and returns the rule identifiers that fired.
func ruleNames(line string, check string) []string {
	lines := []string{"---", "title: \"t\"", "---", "", line}
	ctx := mdfmt.AnalyzeLines(lines)
	var out []string
	switch check {
	case "drift":
		for _, v := range checkDriftAnchors("f.md", lines, ctx) {
			out = append(out, v.Rule)
		}
	case "negation":
		for _, v := range checkNegationLead("f.md", lines, ctx) {
			out = append(out, v.Rule)
		}
	}
	return out
}

func TestQuotedAtSpanMembership(t *testing.T) {
	cases := []struct {
		name string
		line string
		idx  int
		want bool
	}{
		{"outside any quote", "核心責任不是 X、而是 Y", 12, false},
		{"immediately after open bracket", "「不是 X、而是 Y」是反例", 3, true},
		{"deep inside span past emphasis", "反例：「核心責任**不是** X、**而是** Y」", 21, true},
		{"unclosed bracket leaves rest unquoted", "他說「不是 X、而是 Y", 9, false},
		{"after span closes", "「引用」之後核心責任不是 X、而是 Y", 27, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := quotedAt(tc.line, tc.idx); got != tc.want {
				t.Errorf("quotedAt(%q, %d) = %v, want %v", tc.line, tc.idx, got, tc.want)
			}
		})
	}
}

func TestNegationLeadSkipsQuotedAntiExample(t *testing.T) {
	cases := []struct {
		name string
		line string
		want int
	}{
		{"bare prose fires", "核心責任不是 X、而是 Y。", 1},
		{"quoted anti-example with emphasis is exempt", "違規：「核心責任**不是** X、**而是** Y」。", 0},
		{"quoted anti-example with inner brackets is exempt", "「高階函式不是『用了比較高級』、而是自然解」。", 0},
		{"quoted pattern in a table cell is exempt", "| 中文 | 「不是 X、而是 Y」 | 高 |", 0},
		{"inline code is exempt", "regex 用 `不是.{0,30}而是` 掃描。", 0},
		{"quote elsewhere on the line does not exempt prose", "「引用」之後核心責任不是 X、而是 Y。", 1},
		{"與其 不如 fires", "與其重寫整段、不如先補一句定義。", 1},
		{"bare full-width comma fires", "核心責任不是行數，是概念數。", 1},
		{"bare enumeration comma fires", "核心責任不是行數、是概念數。", 1},
		{"bare comma inside quotes is exempt", "違規：「核心責任不是行數，是概念數」。", 0},
		// Parallel causes are the canonical shape, not an exemption: the
		// point (讀者會漏看) sits behind 是因為. An earlier version excluded
		// 因 on the Y side and silently dropped ten of these.
		{"parallel causes fire", "這樣寫不是為了美觀，是因為讀者會漏看。", 1},
		{"parallel 因為 clauses fire", "不是因為 attention、是因為 residual 讓深層仍收斂。", 1},
		{"trailing negation with 而不是 is the correct form", "放在結尾、而不是開頭，是為了讓它最後才送。", 0},
		{"而不是 without a purpose clause is still correct form", "分桶而不是比大小，是這個限制下唯一穩健的用法。", 0},
		{"是不是 interrogative does not fire", "插的是不是它，是組裝層的問題。", 0},
		// Known imprecision: 是 whose subject is the whole preceding clause
		// (not a corrected object) has the same surface shape. The rule warns
		// rather than errors precisely because this needs a reader.
		{"clause-subject 是 is a known false-positive shape", "哪些承擔得起、哪些不是自己說了算，是排序問題。", 1},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := len(ruleNames(tc.line, "negation")); got != tc.want {
				t.Errorf("checkNegationLead(%q) fired %d, want %d", tc.line, got, tc.want)
			}
		})
	}
}

func TestPositionalAnchorFrozenSpecExemption(t *testing.T) {
	cases := []struct {
		name string
		line string
		want int
	}{
		{"internal section symbol fires", "判讀依 §5.10 的說明。", 1},
		{"RFC section is frozen numbering", "RFC 9110 §15.3.3 原文如此。", 0},
		{"section symbol before the RFC token", "[HTTP Semantics §15.6.3（RFC 9110）](https://example.com) 是一手 spec。", 0},
		{"two sections on one RFC line", "RFC 4918 §11.1 定義、§13 明文。", 0},
		{"ISO is frozen numbering", "ISO 8601 §4.3 定義日期格式。", 0},
		{"positional prose reference still fires on an RFC line", "RFC 9110 的說明見第三章。", 1},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := len(ruleNames(tc.line, "drift")); got != tc.want {
				t.Errorf("checkDriftAnchors(%q) fired %d, want %d", tc.line, got, tc.want)
			}
		})
	}
}
