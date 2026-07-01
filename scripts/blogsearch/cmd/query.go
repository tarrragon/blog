package cmd

import (
	"flag"
	"fmt"
	"os"
	"strings"

	"blog/scripts/blogsearch/internal/embed"
	"blog/scripts/blogsearch/internal/search"
	"blog/scripts/blogsearch/internal/store"
)

func Query(args []string) int {
	fs := flag.NewFlagSet("query", flag.ExitOnError)
	indexDir := fs.String("index", ".blogsearch", "index directory")
	topK := fs.Int("top-k", 5, "number of results")
	section := fs.String("section", "", "filter by section (e.g. llm, backend, report)")
	fs.Parse(args)

	if fs.NArg() == 0 {
		fmt.Fprintln(os.Stderr, "usage: blogsearch query [flags] <query text>")
		return 2
	}
	queryText := strings.Join(fs.Args(), " ")

	records, err := store.Load(*indexDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "load index: %v\n", err)
		return 1
	}

	if *section != "" {
		var filtered []store.Record
		for _, r := range records {
			if r.Meta.Section == *section {
				filtered = append(filtered, r)
			}
		}
		records = filtered
	}

	qvec, err := embed.Text(queryText)
	if err != nil {
		fmt.Fprintf(os.Stderr, "embed query: %v\n", err)
		return 1
	}

	results := search.TopK(records, qvec, *topK)

	for i, r := range results {
		fmt.Printf("\n─── %d. [%.3f] %s ───\n", i+1, r.Score, r.Record.Meta.Source)
		fmt.Printf("    title: %s\n", r.Record.Meta.Title)
		fmt.Printf("    section: %s | chunk: %d\n", r.Record.Meta.Section, r.Record.Meta.ChunkIdx)
		preview := r.Record.Text
		if len(preview) > 200 {
			preview = preview[:200] + "..."
		}
		fmt.Printf("    %s\n", strings.ReplaceAll(preview, "\n", "\n    "))
	}
	fmt.Println()
	return 0
}
