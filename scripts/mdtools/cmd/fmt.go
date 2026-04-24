package cmd

import (
	"flag"
	"fmt"
	"os"

	"blog/scripts/mdtools/internal/files"
	"blog/scripts/mdtools/internal/mdfmt"
	"blog/scripts/mdtools/internal/rules"
)

// Fmt runs the fmt subcommand.
//
// Phase 1 rules (line-based): MD026 (heading trailing punct),
// MD022 (heading blank lines), MD047 (trailing newline).
//
// Phase 2 rules (AST-guided, deferred): MD031 / MD032 / MD029 / MD034 / MD060.
func Fmt(args []string) int {
	fs := flag.NewFlagSet("fmt", flag.ExitOnError)
	fix := fs.Bool("fix", false, "apply fixes in place (pre-commit mode)")
	check := fs.Bool("check", false, "report-only; non-zero exit on pending changes (CI mode)")
	quiet := fs.Bool("quiet", false, "suppress per-file output in --fix mode")
	_ = fs.Parse(args)

	if *check && *fix {
		fmt.Fprintln(os.Stderr, "mdtools fmt: --fix and --check are mutually exclusive")
		return 2
	}
	if !*check && !*fix {
		// Default to --check when neither given so accidental invocation
		// does not silently mutate files.
		*check = true
	}

	paths := fs.Args()
	if len(paths) == 0 {
		paths = []string{"content"}
	}

	mdFiles, err := files.WalkMarkdown(paths)
	if err != nil {
		fmt.Fprintf(os.Stderr, "mdtools fmt: walk error: %v\n", err)
		return 2
	}
	if len(mdFiles) == 0 {
		fmt.Fprintf(os.Stderr, "mdtools fmt: no markdown files under %v\n", paths)
		return 0
	}

	cfg := rules.Default()
	changed := 0
	errors := 0

	for _, path := range mdFiles {
		result, err := mdfmt.FormatFile(path, cfg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "mdtools fmt: %s: %v\n", path, err)
			errors++
			continue
		}
		if !result.Changed() {
			continue
		}
		changed++
		switch {
		case *fix:
			if err := os.WriteFile(path, result.Fixed, 0o644); err != nil {
				fmt.Fprintf(os.Stderr, "mdtools fmt: write %s: %v\n", path, err)
				errors++
				continue
			}
			if !*quiet {
				fmt.Printf("fixed: %s\n", path)
			}
		case *check:
			fmt.Printf("would fix: %s\n", path)
		}
	}

	switch {
	case errors > 0:
		return 2
	case *check && changed > 0:
		fmt.Fprintf(os.Stderr, "\nmdtools fmt --check: %d file(s) need formatting\n", changed)
		return 1
	case *fix && changed > 0:
		fmt.Printf("\nmdtools fmt --fix: %d file(s) updated\n", changed)
		return 0
	default:
		return 0
	}
}
