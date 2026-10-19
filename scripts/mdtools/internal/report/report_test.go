package report

import (
	"bytes"
	"strings"
	"testing"
)

func sampleViolations() []Violation {
	return []Violation{
		{Path: "content/b.md", Line: 3, Rule: "POS-negation-lead", Level: LevelWarn, Message: "long explanation"},
		{Path: "content/a.md", Line: 9, Rule: "L1-broken-link", Level: LevelError, Message: "target not found"},
		{Path: "content/a.md", Line: 1, Rule: "POS-negation-lead", Level: LevelWarn, Message: "long explanation"},
		{Path: "content/c.md", Line: 2, Rule: "REF1-position", Level: LevelWarn, Message: "position reference"},
		{Path: "content/c.md", Line: 5, Rule: "REF2-count", Level: LevelWarn, Message: "count in name"},
	}
}

func summaryOf(vs []Violation) string {
	r := &Reporter{}
	for _, v := range vs {
		r.Add(v)
	}
	var buf bytes.Buffer
	r.WriteWarnSummary(&buf)
	return buf.String()
}

func TestWriteWarnSummaryListsErrorsAndCountsWarnings(t *testing.T) {
	want := strings.Join([]string{
		"content/a.md:9: [error] L1-broken-link target not found",
		"[warn] POS-negation-lead: 2 occurrence(s) (rerun without -warn-summary to list them)",
		"[warn] REF1-position: 1 occurrence(s) (rerun without -warn-summary to list them)",
		"[warn] REF2-count: 1 occurrence(s) (rerun without -warn-summary to list them)",
		"",
	}, "\n")
	if got := summaryOf(sampleViolations()); got != want {
		t.Errorf("summary mismatch\n got:\n%s\nwant:\n%s", got, want)
	}
}

// The order violations are added in must not change the summary: counts
// come from a map, and ties are broken by rule name.
func TestWriteWarnSummaryIsOrderIndependent(t *testing.T) {
	forward := sampleViolations()
	reversed := make([]Violation, len(forward))
	for i, v := range forward {
		reversed[len(forward)-1-i] = v
	}
	if a, b := summaryOf(forward), summaryOf(reversed); a != b {
		t.Errorf("summary depends on insertion order\nforward:\n%s\nreversed:\n%s", a, b)
	}
}

func TestWriteWarnSummaryWithoutWarningsPrintsOnlyErrors(t *testing.T) {
	vs := []Violation{{Path: "content/a.md", Line: 9, Rule: "L1-broken-link", Level: LevelError, Message: "target not found"}}
	want := "content/a.md:9: [error] L1-broken-link target not found\n"
	if got := summaryOf(vs); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestWriteStillListsEveryWarning(t *testing.T) {
	r := &Reporter{}
	for _, v := range sampleViolations() {
		r.Add(v)
	}
	var buf bytes.Buffer
	r.Write(&buf)
	if n := strings.Count(buf.String(), "[warn]"); n != 4 {
		t.Errorf("Write listed %d warnings, want 4:\n%s", n, buf.String())
	}
}

// Ten rules tied at one occurrence each: without the name tie-break the
// order would follow map iteration, which Go randomizes between runs.
func TestWriteWarnSummaryBreaksTiesByRuleName(t *testing.T) {
	names := []string{"R9", "R3", "R7", "R1", "R5", "R0", "R8", "R2", "R6", "R4"}
	var vs []Violation
	for _, n := range names {
		vs = append(vs, Violation{Path: "content/x.md", Line: 1, Rule: n, Level: LevelWarn})
	}
	var want strings.Builder
	for i := 0; i < 10; i++ {
		want.WriteString("[warn] R")
		want.WriteByte(byte('0' + i))
		want.WriteString(": 1 occurrence(s) (rerun without -warn-summary to list them)\n")
	}
	for run := 0; run < 20; run++ {
		if got := summaryOf(vs); got != want.String() {
			t.Fatalf("run %d: ties not ordered by rule name\n got:\n%s", run, got)
		}
	}
}
