package cmd

import (
	"flag"
	"fmt"
	"os"
	"sort"
	"strings"

	"blog/scripts/mdtools/internal/mdcards"
)

// AutolinkGaps runs the autolink-gaps subcommand: for each given page, list
// the card names in its prose that the site will not auto-link, for cards the
// page has no link to yet. Output is one tab-separated line per page and name:
//
//	<page>\t<name>\t<reason>\t<card> [<card>...]
//
// followed on stderr by `mdtools autolink-gaps: N file(s), M candidate(s)`.
// -summary prints counts per page folder, reason and card folder instead of
// the per-name lines, for deciding a folder's scope. Which candidates get a
// hand-written link is decided by docs/rules/sentences.md, not by this tool.
// Exit 0 when the scan ran (with or without candidates), 2 when the
// dictionary or a page cannot be read. Run from the repo root: the
// dictionary path is relative.
func AutolinkGaps(args []string) int {
	fs := flag.NewFlagSet("autolink-gaps", flag.ExitOnError)
	summary := fs.Bool("summary", false, "print counts per page folder, reason and card folder")
	fs.Usage = func() {
		fmt.Fprintln(os.Stderr, "Usage: mdtools autolink-gaps [-summary] <page.md|dir>...\n\nReasons:")
		fmt.Fprintln(os.Stderr, strings.Join(mdcards.GapReasons(), "\n"))
	}
	_ = fs.Parse(args)
	if fs.NArg() == 0 {
		fs.Usage()
		return 2
	}
	gaps, n, err := mdcards.AutolinkGaps(fs.Args())
	if err != nil {
		fmt.Fprintf(os.Stderr, "mdtools autolink-gaps: %v\n", err)
		return 2
	}
	if *summary {
		counts := summarizeGaps(gaps)
		keys := make([]string, 0, len(counts))
		for k := range counts {
			keys = append(keys, k)
		}
		sort.Slice(keys, func(i, j int) bool {
			return counts[keys[i]] > counts[keys[j]] || counts[keys[i]] == counts[keys[j]] && keys[i] < keys[j]
		})
		for _, k := range keys {
			fmt.Printf("%d\t%s\n", counts[k], k)
		}
	} else {
		for _, g := range gaps {
			fmt.Printf("%s\t%s\t%s\t%s\n", g.Path, g.Name, g.Reason, strings.Join(g.Cards, " "))
		}
	}
	fmt.Fprintf(os.Stderr, "mdtools autolink-gaps: %d file(s), %d candidate(s)\n", n, len(gaps))
	return 0
}

// summarizeGaps counts gaps per "page folder\treason\tcard folder".
func summarizeGaps(gaps []mdcards.Gap) map[string]int {
	counts := map[string]int{}
	for _, g := range gaps {
		cardFolder := "-"
		if len(g.Cards) > 0 {
			cardFolder = strings.SplitN(g.Cards[0], "/", 2)[0]
		}
		counts[fmt.Sprintf("%s\t%s\t%s", pageFolder(g.Path), g.Reason, cardFolder)]++
	}
	return counts
}

// pageFolder is the first directory under content/ ("-" for the home page).
func pageFolder(p string) string {
	rest := p
	if i := strings.Index(p, "content/"); i >= 0 {
		rest = p[i+len("content/"):]
	}
	if j := strings.Index(rest, "/"); j > 0 {
		return rest[:j]
	}
	return "-"
}
