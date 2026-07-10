package mdfmt

import (
	"bytes"
	"strings"
	"testing"

	"blog/scripts/mdtools/internal/rules"
)

// fixtures are deliberately hostile inputs, one per formatting rule plus
// the regions fmt must never touch. Each is exercised for idempotence:
// fmt output is committed automatically (CI runs `fmt --fix` and
// auto-commits; pre-commit fixes staged files), so a second pass that
// still changes bytes means the bot ping-pongs commits forever.
var fixtures = map[string]string{
	"heading crammed against prose": "intro\n## 標題\nbody\n",
	"heading with trailing colon":   "## 判讀訊號：\n\ncontent\n",
	"fenced code without blanks":    "prose\n```go\nx := 1\n```\nmore\n",
	"list without blanks":           "prose\n- a\n- b\nafter\n",
	"misaligned CJK table": "| 欄位 | 說明 |\n| --- | --- |\n| 短 | 中英 mixed 內容較長 |\n| 這格是雙寬中文 | x |\n",
	"no trailing newline":        "line one",
	"many trailing newlines":     "line one\n\n\n\n",
	"front matter with colons":   "---\ntitle: \"標題：帶冒號\"\ndate: 2026-07-10\n---\n\nbody\n",
	"heading-like text in fence": "```text\n## 不是標題：\n| 不是 | 表格 |\n```\n",
	"empty file":                 "",
	"only front matter":          "---\ntitle: t\n---\n",
}

func TestApplyAllIdempotent(t *testing.T) {
	cfg := rules.Default()
	for name, src := range fixtures {
		t.Run(name, func(t *testing.T) {
			once := applyAll([]byte(src), cfg)
			twice := applyAll(once, cfg)
			if !bytes.Equal(once, twice) {
				t.Errorf("second pass still changes bytes:\n first: %q\nsecond: %q", once, twice)
			}
		})
	}
}

// The regions fmt must leave alone: front matter and fenced-code
// interiors. A heading or table inside a fence looks exactly like the
// real thing to a line-based rule; only LineContext.Skip stands between
// them and a silent content rewrite.
func TestApplyAllLeavesProtectedRegionsAlone(t *testing.T) {
	cfg := rules.Default()

	t.Run("front matter", func(t *testing.T) {
		src := "---\ntitle: \"標題：帶冒號\"\ndate: 2026-07-10\n---\n\nbody\n"
		got := string(applyAll([]byte(src), cfg))
		if !strings.Contains(got, "title: \"標題：帶冒號\"") {
			t.Errorf("front matter was rewritten:\n%s", got)
		}
	})

	t.Run("fenced code interior", func(t *testing.T) {
		src := "```text\n## 不是標題：\n| 不是 | 表格 |\n```\n"
		got := string(applyAll([]byte(src), cfg))
		if !strings.Contains(got, "## 不是標題：") {
			t.Errorf("heading-punct rule reached inside a fence:\n%s", got)
		}
		if !strings.Contains(got, "| 不是 | 表格 |") {
			t.Errorf("table alignment reached inside a fence:\n%s", got)
		}
	})
}

func TestApplyAllBehaviors(t *testing.T) {
	cfg := rules.Default()

	t.Run("MD026 strips trailing colon from heading", func(t *testing.T) {
		got := string(applyAll([]byte("## 判讀訊號：\n\nbody\n"), cfg))
		if strings.Contains(got, "訊號：") {
			t.Errorf("trailing colon survived: %q", got)
		}
		if !strings.Contains(got, "## 判讀訊號") {
			t.Errorf("heading text damaged: %q", got)
		}
	})

	t.Run("MD022 inserts blanks around heading", func(t *testing.T) {
		got := string(applyAll([]byte("intro\n## 標題\nbody\n"), cfg))
		if !strings.Contains(got, "intro\n\n## 標題\n\nbody") {
			t.Errorf("blank lines missing around heading: %q", got)
		}
	})

	t.Run("MD047 exactly one trailing newline", func(t *testing.T) {
		for _, src := range []string{"x", "x\n", "x\n\n\n"} {
			got := applyAll([]byte(src), cfg)
			if !bytes.HasSuffix(got, []byte("x\n")) {
				t.Errorf("applyAll(%q) = %q, want single trailing newline", src, got)
			}
		}
	})

	t.Run("empty input stays empty", func(t *testing.T) {
		if got := applyAll(nil, cfg); len(got) != 0 {
			t.Errorf("empty file grew content: %q", got)
		}
	})

	t.Run("CJK table cells get aligned padding", func(t *testing.T) {
		src := "| 欄位 | 說明 |\n| --- | --- |\n| 短 | 中英 mixed 內容較長 |\n| 這格是雙寬中文 | x |\n"
		got := string(applyAll([]byte(src), cfg))
		lines := strings.Split(strings.TrimRight(got, "\n"), "\n")
		if len(lines) != 4 {
			t.Fatalf("table row count changed: %q", got)
		}
		// Aligned style: every row of one table renders at the same
		// display width. Byte length differs (CJK is 3 bytes but 2 cells
		// wide), so compare display width, the unit the rule pads in.
		w := displayWidth(lines[0])
		for i, l := range lines[1:] {
			if displayWidth(l) != w {
				t.Errorf("row %d width %d != header width %d:\n%s", i+1, displayWidth(l), w, got)
			}
		}
	})
}

// displayWidth mirrors the CJK double-width convention the table rule
// pads with: runes >= 0x1100 that are Wide or Fullwidth count as 2.
// Kept deliberately simple — the fixture uses only ASCII and common CJK.
func displayWidth(s string) int {
	w := 0
	for _, r := range s {
		if r >= 0x2E80 { // CJK blocks and beyond, fine for the fixture
			w += 2
		} else {
			w++
		}
	}
	return w
}

// EnsureTrailingNewline is exported and callable outside applyAll, where
// its input may still carry trailing newlines — inside applyAll that
// case never occurs (joinLines emits none), so only a direct test pins it.
func TestEnsureTrailingNewline(t *testing.T) {
	cases := map[string]string{"x": "x\n", "x\n": "x\n", "x\n\n\n": "x\n", "x\r\n": "x\n", "": ""}
	for in, want := range cases {
		if got := string(EnsureTrailingNewline([]byte(in))); got != want {
			t.Errorf("EnsureTrailingNewline(%q) = %q, want %q", in, got, want)
		}
	}
}
