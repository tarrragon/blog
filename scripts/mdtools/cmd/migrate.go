package cmd

import (
	"flag"
	"fmt"
	"os"

	"blog/scripts/mdtools/internal/mdcards"
	"blog/scripts/mdtools/internal/mdmigrate"
	"blog/scripts/mdtools/internal/rules"
)

// Migrate dispatches one-off content migration subcommands. Unlike fmt
// and lint, migrate is not part of the pre-commit loop — it's for
// operator-initiated content cleanup where a class of violations can
// be fixed mechanically once.
func Migrate(args []string) int {
	if len(args) == 0 {
		migrateUsage()
		return 2
	}
	sub := args[0]
	rest := args[1:]
	switch sub {
	case "fix-links":
		return migrateFixLinks(rest)
	case "-h", "--help", "help":
		migrateUsage()
		return 0
	default:
		fmt.Fprintf(os.Stderr, "unknown migrate subcommand: %q\n\n", sub)
		migrateUsage()
		return 2
	}
}

func migrateUsage() {
	fmt.Fprintln(os.Stderr, `mdtools migrate — one-off content migration tools

Usage:
  mdtools migrate <subcommand> [options] [paths...]

Subcommands:
  fix-links [--apply]   Auto-correct broken relative links (L1) whose
                        intended target can be inferred by slug lookup.
                        Default is dry-run; --apply writes changes.`)
}

func migrateFixLinks(args []string) int {
	fs := flag.NewFlagSet("migrate fix-links", flag.ExitOnError)
	apply := fs.Bool("apply", false, "write fixes to files (default: dry-run)")
	verbose := fs.Bool("v", false, "list every proposed fix (default: summary only)")
	_ = fs.Parse(args)

	paths := fs.Args()
	if len(paths) == 0 {
		paths = []string{"content"}
	}

	cfg := rules.Default()
	g, err := mdcards.BuildGraph(paths)
	if err != nil {
		fmt.Fprintf(os.Stderr, "mdtools migrate fix-links: build graph: %v\n", err)
		return 2
	}

	fixes, unresolvable := mdmigrate.FindFixes(g, cfg.Cards.CardsRoot)

	fmt.Printf("L1 fixes proposed: %d\n", len(fixes))
	fmt.Printf("unresolvable:      %d\n", len(unresolvable))

	if *verbose || !*apply {
		// In dry-run or verbose mode, print per-fix detail.
		for _, f := range fixes {
			fmt.Printf("  %s:%d  %s  →  %s  (%s)\n",
				f.SourcePath, f.Line, f.OldDest, f.NewDest, f.Reason)
		}
	}

	if *apply {
		n, err := mdmigrate.ApplyFixes(fixes)
		if err != nil {
			fmt.Fprintf(os.Stderr, "apply error: %v\n", err)
			return 1
		}
		fmt.Printf("\napplied: %d file(s) updated\n", n)
	} else if len(fixes) > 0 {
		fmt.Printf("\n(dry-run; re-run with --apply to write changes)\n")
	}

	if len(unresolvable) > 0 {
		fmt.Printf("\n=== unresolvable (target not found in content/**) ===\n")
		for _, u := range unresolvable {
			fmt.Printf("  %s:%d  %s  (slug=%s)\n", u.SourcePath, u.Line, u.Dest, u.Slug)
		}
	}

	return 0
}
