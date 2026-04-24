package cmd

import (
	"flag"
	"fmt"
)

// Lint runs the lint subcommand.
// Structural checks: MD024 siblings_only / H1-ban / MD036 / MD040 / anti-phishing
// R-URL-1 / R-URL-2 / front matter schema.
func Lint(args []string) int {
	fs := flag.NewFlagSet("lint", flag.ExitOnError)
	_ = fs.Parse(args)

	paths := fs.Args()
	if len(paths) == 0 {
		paths = []string{"content"}
	}

	fmt.Printf("mdtools lint: not implemented yet (paths=%v)\n", paths)
	return 0
}
