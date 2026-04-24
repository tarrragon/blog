package cmd

import (
	"flag"
	"fmt"
	"os"

	"blog/scripts/mdtools/internal/mdcards"
	"blog/scripts/mdtools/internal/report"
	"blog/scripts/mdtools/internal/rules"
)

// Cards runs the cards subcommand — cross-file completeness checks.
//
// Rules (per content/posts/markdown-writing-spec.md §5):
//   - L1 link validity: every relative link resolves to an existing file.
//   - L2 orphan detection: every card has an inbound edge from non-card content.
//   - L4 K4 structure: first paragraph + "概念位置" section each link to adjacent cards.
//
// Unlike fmt and lint, cards parses the full content/ tree each run
// because the graph checks are inherently cross-file. Parse cost scales
// linearly with file count; at current sizes (~400 md files) the run
// completes in under a second.
func Cards(args []string) int {
	fs := flag.NewFlagSet("cards", flag.ExitOnError)
	warnAsError := fs.Bool("warn-as-error", false, "treat warnings as errors (CI strict mode)")
	_ = fs.Parse(args)

	paths := fs.Args()
	if len(paths) == 0 {
		paths = []string{"content"}
	}

	cfg := rules.Default()
	violations, err := mdcards.Check(paths, cfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "mdtools cards: %v\n", err)
		return 2
	}

	reporter := &report.Reporter{}
	for _, v := range violations {
		reporter.Add(v)
	}
	reporter.Write(os.Stdout)

	errCount := reporter.ErrorCount()
	warnCount := reporter.Count() - errCount

	if reporter.Count() > 0 {
		fmt.Fprintf(os.Stderr, "\nmdtools cards: %d error(s), %d warning(s)\n", errCount, warnCount)
	}

	if errCount > 0 {
		return 1
	}
	if *warnAsError && warnCount > 0 {
		return 1
	}
	return 0
}
