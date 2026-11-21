package autolinkhtml

import (
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"testing"
)

// The page script has no tests of its own, and on the deployed pages (which
// carry data-static) it never runs its matching, so nothing in CI exercises it.
// This test reads assets/js/autolink.js and fails when its SKIP list and
// skipTags here drift apart: a change to one is a change to the rules, and
// the other has to follow (the rule list is in the script's header).
func TestSkipTagsMatchPageScript(t *testing.T) {
	src, err := os.ReadFile(filepath.Join("..", "..", "..", "..", "assets", "js", "autolink.js"))
	if err != nil {
		t.Fatal(err)
	}
	m := regexp.MustCompile(`var SKIP = /\^\(([A-Z0-9|]+)\)\$/;`).FindSubmatch(src)
	if m == nil {
		t.Fatal("var SKIP = /^(...)$/; not found in assets/js/autolink.js; update this test with the script")
	}
	var js []string
	for _, tag := range strings.Split(string(m[1]), "|") {
		js = append(js, strings.ToLower(tag))
	}
	// The script skips SVG by element type (instanceof SVGElement), not by
	// tag name, so svg is in skipTags only.
	var gotest []string
	for tag := range skipTags {
		if tag != "svg" {
			gotest = append(gotest, tag)
		}
	}
	sort.Strings(js)
	sort.Strings(gotest)
	if strings.Join(js, " ") != strings.Join(gotest, " ") {
		t.Errorf("skip lists differ\n page script SKIP: %v\n skipTags:         %v", js, gotest)
	}
}
