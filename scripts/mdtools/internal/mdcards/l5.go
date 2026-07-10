package mdcards

import (
	"fmt"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"blog/scripts/mdtools/internal/report"
)

var weightFieldRe = regexp.MustCompile(`(?m)^weight:`)

// checkL5SectionWeightConsistency flags Hugo sections whose pages carry
// `weight` inconsistently.
//
// Hugo's default page sort is weight ascending, with weight-0 (unset)
// pages placed after every weighted page, and only then date descending.
// A section is therefore ordered coherently in exactly two states:
//
//	all pages weighted    → manual order (chapter sequence, card numbers)
//	no page weighted      → date descending (newest first)
//
// Any mix silently splits the list in two: the weighted pages sort first
// by weight, the rest sink below them by date. Nothing errors, nothing
// renders wrong, and the omission only surfaces as "why is this old post
// above the new ones" — or, in the case that motivated this check, as an
// entire batch of cards stranded at the bottom of the list.
//
// Reported at warn level, because one legitimate Hugo idiom produces the
// same shape: giving a single page a low weight pins it above an
// otherwise date-sorted section. Exempt those sections explicitly via
// cfg.Cards.WeightExemptSections — a recorded exemption is the thing that
// distinguishes a decision from an oversight.
//
// The check needs the whole section on disk, so it lives here rather than
// in mdlint: lint runs on a caller-supplied file set (pre-commit passes
// only staged files), where a section would look inconsistent merely
// because its other pages were not staged.
func checkL5SectionWeightConsistency(g *Graph, exempt []string) []report.Violation {
	type sectionStat struct {
		total   int
		weighed int
		missing []string
		present []string
		anyPath string
	}

	sections := map[string]*sectionStat{}
	indexPages := map[string]string{}

	for _, fn := range g.Files {
		dir := filepath.ToSlash(filepath.Dir(fn.Path))
		if isSectionIndex(fn.Path) {
			indexPages[dir] = fn.Path
			continue
		}
		s := sections[dir]
		if s == nil {
			s = &sectionStat{}
			sections[dir] = s
		}
		s.total++
		s.anyPath = fn.Path
		if weightFieldRe.Match(frontMatterOf(fn.Src)) {
			s.weighed++
			s.present = append(s.present, filepath.Base(fn.Path))
		} else {
			s.missing = append(s.missing, filepath.Base(fn.Path))
		}
	}

	dirs := make([]string, 0, len(sections))
	for d := range sections {
		dirs = append(dirs, d)
	}
	sort.Strings(dirs)

	var out []report.Violation
	for _, dir := range dirs {
		s := sections[dir]
		if s.weighed == 0 || s.weighed == s.total {
			continue
		}
		if isExemptSection(dir, exempt) {
			continue
		}

		// Anchor the violation on the section's landing page when it has
		// one; the fix is a property of the section, not of any one file.
		path := indexPages[dir]
		if path == "" {
			path = s.anyPath
		}

		// Name the minority — those are the files to change, whichever
		// direction the section is meant to go.
		odd, verb := s.missing, "lack"
		if len(s.present) < len(s.missing) {
			odd, verb = s.present, "carry"
		}

		out = append(out, report.Violation{
			Path:  path,
			Line:  0,
			Rule:  "L5-section-weight-consistency",
			Level: report.LevelWarn,
			Message: fmt.Sprintf(
				"section %s mixes weighted and unweighted pages (%d of %d weighted); "+
					"Hugo sorts unweighted pages below every weighted one. "+
					"Make weight all-or-nothing, or exempt the section if a page is pinned deliberately. "+
					"Minority (%s weight): %s",
				dir, s.weighed, s.total, verb, summarize(odd, 5)),
		})
	}
	return out
}

// frontMatterOf returns the bytes between the opening and closing `---`
// fences, so a `weight:` inside a code block or prose cannot be mistaken
// for a front-matter field.
func frontMatterOf(src []byte) []byte {
	s := string(src)
	if !strings.HasPrefix(s, "---\n") {
		return nil
	}
	end := strings.Index(s[4:], "\n---")
	if end < 0 {
		return nil
	}
	return []byte(s[4 : 4+end+1])
}

// isExemptSection reports whether dir was explicitly excused from the
// all-or-nothing rule.
func isExemptSection(dir string, exempt []string) bool {
	for _, e := range exempt {
		if dir == strings.TrimSuffix(filepath.ToSlash(e), "/") {
			return true
		}
	}
	return false
}

// summarize renders at most n names, noting how many were elided.
func summarize(names []string, n int) string {
	sort.Strings(names)
	if len(names) <= n {
		return strings.Join(names, ", ")
	}
	return fmt.Sprintf("%s, and %d more", strings.Join(names[:n], ", "), len(names)-n)
}
