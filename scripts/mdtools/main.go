package main

import (
	"fmt"
	"os"

	"blog/scripts/mdtools/cmd"
)

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}

	sub := os.Args[1]
	args := os.Args[2:]

	var exitCode int
	switch sub {
	case "fmt":
		exitCode = cmd.Fmt(args)
	case "lint":
		exitCode = cmd.Lint(args)
	case "cards":
		exitCode = cmd.Cards(args)
	case "-h", "--help", "help":
		usage()
	case "version":
		fmt.Println("mdtools 0.1.0-dev")
	default:
		fmt.Fprintf(os.Stderr, "unknown subcommand: %q\n\n", sub)
		usage()
		exitCode = 2
	}

	os.Exit(exitCode)
}

func usage() {
	fmt.Fprintln(os.Stderr, `mdtools — markdown toolchain for blog content quality

Usage:
  mdtools <subcommand> [options] [paths...]

Subcommands:
  fmt [--fix|--check]  Format normalization (auto-fixable rules)
  lint                 Structural and schema checks
  cards                Cross-file card completeness checks
  version              Print version
  help                 Show this help

When no paths given, defaults to content/**.

See content/posts/markdown-writing-spec.md for the rule contract.`)
}
