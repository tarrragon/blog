package main

import (
	"fmt"
	"os"

	"blog/scripts/blogsearch/cmd"
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
	case "ingest":
		exitCode = cmd.Ingest(args)
	case "query":
		exitCode = cmd.Query(args)
	case "status":
		exitCode = cmd.Status(args)
	case "-h", "--help", "help":
		usage()
	default:
		fmt.Fprintf(os.Stderr, "unknown subcommand: %q\n\n", sub)
		usage()
		exitCode = 2
	}

	os.Exit(exitCode)
}

func usage() {
	fmt.Fprintln(os.Stderr, `blogsearch — semantic search for blog content

Usage:
  blogsearch ingest [-content DIR] [-out DIR]   Build/rebuild index
  blogsearch query [-top-k N] [-section S] TEXT  Semantic search
  blogsearch status [-index DIR]                 Show index stats

Requires Ollama running locally with nomic-embed-text model.`)
}
