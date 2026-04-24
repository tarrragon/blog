package cmd

import (
	"flag"
	"fmt"
)

// Cards runs the cards subcommand.
// Cross-file completeness checks:
//   L1 link validity     — all relative links resolve to existing files.
//   L2 orphan detection  — every knowledge card has at least one inbound edge.
//   L4 K4 compliance     — card's first paragraph and "概念位置" section each
//                          contain at least one adjacent-card link.
func Cards(args []string) int {
	fs := flag.NewFlagSet("cards", flag.ExitOnError)
	_ = fs.Parse(args)

	paths := fs.Args()
	if len(paths) == 0 {
		paths = []string{"content"}
	}

	fmt.Printf("mdtools cards: not implemented yet (paths=%v)\n", paths)
	return 0
}
