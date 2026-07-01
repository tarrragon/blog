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

	metas, vectors, dim, err := store.LoadForSearch(*indexDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "load index: %v\n", err)
		return 1
	}

	if *section != "" {
		var filteredMetas []store.ChunkMeta
		var filteredVecs []float32
		for i, m := range metas {
			if m.Section == *section {
				filteredMetas = append(filteredMetas, m)
				start := i * dim
				filteredVecs = append(filteredVecs, vectors[start:start+dim]...)
			}
		}
		metas = filteredMetas
		vectors = filteredVecs
	}

	qvec, err := embed.Text(queryText)
	if err != nil {
		fmt.Fprintf(os.Stderr, "embed query: %v\n", err)
		return 1
	}

	results := search.TopK(metas, vectors, dim, qvec, *topK)

	// Load text only for top-K results
	indices := make([]int, len(results))
	for i, r := range results {
		indices[i] = r.Index
	}
	texts, err := store.LoadTexts(*indexDir, indices)
	if err != nil {
		fmt.Fprintf(os.Stderr, "load texts: %v\n", err)
		return 1
	}

	for i, r := range results {
		fmt.Printf("\n─── %d. [%.3f] %s ───\n", i+1, r.Score, r.Meta.Source)
		fmt.Printf("    title: %s\n", r.Meta.Title)
		fmt.Printf("    section: %s | chunk: %d\n", r.Meta.Section, r.Meta.ChunkIdx)
		preview := texts[r.Index]
		if len(preview) > 200 {
			preview = preview[:200] + "..."
		}
		fmt.Printf("    %s\n", strings.ReplaceAll(preview, "\n", "\n    "))
	}
	fmt.Println()
	return 0
}
