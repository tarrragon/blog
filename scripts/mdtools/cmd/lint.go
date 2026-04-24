package cmd

import (
	"flag"
	"fmt"
	"os"

	"blog/scripts/mdtools/internal/files"
	"blog/scripts/mdtools/internal/mdlint"
	"blog/scripts/mdtools/internal/report"
	"blog/scripts/mdtools/internal/rules"
)

// Lint runs the lint subcommand.
//
// Phase 1 rules (line-based):
//   - H1 ban (stricter than MD025): Hugo front matter `title` already
//     produces H1; body H1 forbidden.
//   - MD024 siblings_only: duplicate heading under the same parent.
//   - MD040: fenced code block missing language hint.
//   - Front matter schema: tiered required/recommended/disallowed fields.
//
// Deferred (need AST): MD036 bold-as-heading detection; anti-phishing
// R-URL-1 / R-URL-2 domain consistency checks.
func Lint(args []string) int {
	fs := flag.NewFlagSet("lint", flag.ExitOnError)
	warnAsError := fs.Bool("warn-as-error", false, "treat warnings as errors (CI strict mode)")
	_ = fs.Parse(args)

	paths := fs.Args()
	if len(paths) == 0 {
		paths = []string{"content"}
	}

	mdFiles, err := files.WalkMarkdown(paths)
	if err != nil {
		fmt.Fprintf(os.Stderr, "mdtools lint: walk error: %v\n", err)
		return 2
	}
	if len(mdFiles) == 0 {
		fmt.Fprintf(os.Stderr, "mdtools lint: no markdown files under %v\n", paths)
		return 0
	}

	cfg := rules.Default()
	reporter := &report.Reporter{}
	fatal := 0

	for _, path := range mdFiles {
		vs, err := mdlint.Check(path, cfg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "mdtools lint: %s: %v\n", path, err)
			fatal++
			continue
		}
		for _, v := range vs {
			reporter.Add(v)
		}
	}

	reporter.Write(os.Stdout)

	if fatal > 0 {
		return 2
	}

	errCount := reporter.ErrorCount()
	warnCount := reporter.Count() - errCount

	if reporter.Count() > 0 {
		fmt.Fprintf(os.Stderr, "\nmdtools lint: %d error(s), %d warning(s)\n", errCount, warnCount)
	}

	if errCount > 0 {
		return 1
	}
	if *warnAsError && warnCount > 0 {
		return 1
	}
	return 0
}
