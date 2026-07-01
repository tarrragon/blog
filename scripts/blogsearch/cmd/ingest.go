package cmd

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"blog/scripts/blogsearch/internal/chunk"
	"blog/scripts/blogsearch/internal/embed"
	"blog/scripts/blogsearch/internal/store"
)

func Ingest(args []string) int {
	fs := flag.NewFlagSet("ingest", flag.ExitOnError)
	contentRoot := fs.String("content", "content", "content directory to index")
	outDir := fs.String("out", ".blogsearch", "output directory for index")
	tokenCap := fs.Int("chunk-tokens", 400, "soft token cap per chunk")
	fs.Parse(args)

	start := time.Now()
	fmt.Printf("indexing %s ...\n", *contentRoot)

	var records []store.Record
	err := filepath.Walk(*contentRoot, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() || !strings.HasSuffix(path, ".md") {
			return nil
		}

		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		text := string(data)

		meta := extractMeta(path, *contentRoot, text)
		chunks := chunk.Markdown(text, *tokenCap)

		for _, c := range chunks {
			vec, err := embed.Text(c.Text)
			if err != nil {
				fmt.Fprintf(os.Stderr, "embed error %s chunk %d: %v\n", path, c.ChunkIdx, err)
				continue
			}
			records = append(records, store.Record{
				Meta: store.ChunkMeta{
					Source:   meta.source,
					Title:    meta.title,
					Section:  meta.section,
					Tags:     meta.tags,
					ChunkIdx: c.ChunkIdx,
				},
				Text:      c.Text,
				Embedding: vec,
			})
		}

		fmt.Printf("  %s: %d chunks\n", path, len(chunks))
		return nil
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "walk error: %v\n", err)
		return 1
	}

	if err := store.Save(*outDir, records); err != nil {
		fmt.Fprintf(os.Stderr, "save error: %v\n", err)
		return 1
	}

	elapsed := time.Since(start)
	fmt.Printf("done: %d chunks from %s in %.1fs → %s/\n",
		len(records), *contentRoot, elapsed.Seconds(), *outDir)
	return 0
}

type fileMeta struct {
	source  string
	title   string
	section string
	tags    []string
}

func extractMeta(path, contentRoot, text string) fileMeta {
	rel, _ := filepath.Rel(contentRoot, path)
	parts := strings.SplitN(rel, string(filepath.Separator), 2)
	section := ""
	if len(parts) > 1 {
		section = parts[0]
	}

	title := filepath.Base(path)
	title = strings.TrimSuffix(title, ".md")

	lines := strings.SplitN(text, "\n", 30)
	inFront := false
	var tags []string
	for _, line := range lines {
		if line == "---" {
			if inFront {
				break
			}
			inFront = true
			continue
		}
		if !inFront {
			continue
		}
		if strings.HasPrefix(line, "title:") {
			t := strings.TrimPrefix(line, "title:")
			t = strings.TrimSpace(t)
			t = strings.Trim(t, "\"")
			if t != "" {
				title = t
			}
		}
		if strings.HasPrefix(line, "tags:") {
			tagLine := strings.TrimPrefix(line, "tags:")
			tagLine = strings.TrimSpace(tagLine)
			tagLine = strings.Trim(tagLine, "[]")
			for _, tag := range strings.Split(tagLine, ",") {
				tag = strings.TrimSpace(tag)
				tag = strings.Trim(tag, "\"")
				if tag != "" {
					tags = append(tags, tag)
				}
			}
		}
	}

	return fileMeta{
		source:  rel,
		title:   title,
		section: section,
		tags:    tags,
	}
}
