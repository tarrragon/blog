package cmd

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
)

func Status(args []string) int {
	fs := flag.NewFlagSet("status", flag.ExitOnError)
	indexDir := fs.String("index", ".blogsearch", "index directory")
	fs.Parse(args)

	metaPath := filepath.Join(*indexDir, "meta.json")
	f, err := os.Open(metaPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "no index found at %s\n", *indexDir)
		return 1
	}
	defer f.Close()

	var idx struct {
		Dim   int `json:"dim"`
		Count int `json:"count"`
	}
	if err := json.NewDecoder(f).Decode(&idx); err != nil {
		fmt.Fprintf(os.Stderr, "parse index: %v\n", err)
		return 1
	}

	info, _ := os.Stat(metaPath)
	vecInfo, _ := os.Stat(filepath.Join(*indexDir, "vectors.bin"))
	textInfo, _ := os.Stat(filepath.Join(*indexDir, "texts.bin"))

	fmt.Printf("index: %s/\n", *indexDir)
	fmt.Printf("  chunks:     %d\n", idx.Count)
	fmt.Printf("  dimensions: %d\n", idx.Dim)
	if vecInfo != nil {
		fmt.Printf("  vectors:    %.1f MB\n", float64(vecInfo.Size())/(1024*1024))
	}
	if textInfo != nil {
		fmt.Printf("  texts:      %.1f MB\n", float64(textInfo.Size())/(1024*1024))
	}
	if info != nil {
		fmt.Printf("  metadata:   %.1f MB\n", float64(info.Size())/(1024*1024))
		fmt.Printf("  updated:    %s\n", info.ModTime().Format("2006-01-02 15:04:05"))
	}
	return 0
}
