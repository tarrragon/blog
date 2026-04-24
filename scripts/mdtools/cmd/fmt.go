package cmd

import (
	"flag"
	"fmt"
)

// Fmt runs the fmt subcommand.
// Format normalization: MD022 / MD026 / MD029 / MD031 / MD032 / MD034 / MD047 / MD060.
// --fix writes changes back to files; --check returns non-zero on any pending change.
func Fmt(args []string) int {
	fs := flag.NewFlagSet("fmt", flag.ExitOnError)
	fix := fs.Bool("fix", false, "apply fixes in place (re-stage in pre-commit context)")
	check := fs.Bool("check", false, "report-only; non-zero exit on pending changes (CI mode)")
	_ = fs.Parse(args)

	mode := "fix"
	switch {
	case *check && *fix:
		fmt.Println("mdtools fmt: --fix and --check are mutually exclusive")
		return 2
	case *check:
		mode = "check"
	case *fix:
		mode = "fix"
	default:
		// default to check mode when neither flag given
		mode = "check"
	}

	paths := fs.Args()
	if len(paths) == 0 {
		paths = []string{"content"}
	}

	fmt.Printf("mdtools fmt: not implemented yet (mode=%s paths=%v)\n", mode, paths)
	return 0
}
