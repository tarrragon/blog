package mdfmt

import (
	"bytes"
	"os"
	"strings"

	"blog/scripts/mdtools/internal/rules"
)

// FixResult summarizes the outcome of formatting a single file.
type FixResult struct {
	Path     string
	Original []byte
	Fixed    []byte
}

// Changed reports whether Fixed differs from Original.
func (r FixResult) Changed() bool {
	return !bytes.Equal(r.Original, r.Fixed)
}

// FormatFile reads path, applies all enabled fmt rules, and returns the
// result. The file is never written to disk by this function — callers
// decide (see cmd.Fmt for --fix vs --check handling).
func FormatFile(path string, cfg rules.Config) (FixResult, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return FixResult{}, err
	}
	fixed := applyAll(data, cfg)
	return FixResult{Path: path, Original: data, Fixed: fixed}, nil
}

// applyAll runs all enabled line-based rules in a deterministic order.
// Context is re-analyzed before each rule that depends on line indices,
// because the previous rule may have inserted blank lines.
//
// Order matters: line-count preserving rules run first, then
// line-count changing rules in an order that avoids double-insertion
// (headings → fences → lists; each pass inserts only at boundaries
// the previous pass did not already normalize).
func applyAll(data []byte, cfg rules.Config) []byte {
	lines := splitLines(data)

	// MD026 — strip trailing punct in headings. Line-count preserving.
	if cfg.Headings.ForbidTrailingPunct {
		ctx := AnalyzeLines(lines)
		lines = FixHeadingTrailingPunct(lines, ctx, cfg.Headings.ForbiddenTrailingPunct)
	}

	// MD022 — blank lines around headings. Line-count changing.
	if cfg.Headings.RequireBlankLines {
		ctx := AnalyzeLines(lines)
		lines = FixHeadingBlankLines(lines, ctx)
	}

	// MD031 — blank lines around fenced code blocks.
	if cfg.CodeBlocks.RequireBlankLinesAround {
		ctx := AnalyzeLines(lines)
		lines = FixFencedCodeBlankLines(lines, ctx)
	}

	// MD032 — blank lines around top-level lists. Conservative; relies
	// on MD022 having already normalized heading-to-list transitions.
	ctx := AnalyzeLines(lines)
	lines = FixListBlankLines(lines, ctx)

	out := joinLines(lines)
	out = EnsureTrailingNewline(out) // MD047
	return out
}

// splitLines splits on '\n'. A single trailing newline at EOF does not
// produce a ghost empty last element. Absence of trailing newline is
// preserved until EnsureTrailingNewline re-adds one.
func splitLines(data []byte) []string {
	if len(data) == 0 {
		return nil
	}
	s := string(data)
	// Strip at most one trailing newline so Split doesn't yield an empty
	// tail element. Multiple trailing newlines collapse to one via
	// EnsureTrailingNewline later.
	if strings.HasSuffix(s, "\n") {
		s = strings.TrimRight(s, "\n")
	}
	if s == "" {
		return []string{}
	}
	return strings.Split(s, "\n")
}

// joinLines joins with '\n'. No trailing newline is added here;
// EnsureTrailingNewline owns that responsibility.
func joinLines(lines []string) []byte {
	if len(lines) == 0 {
		return nil
	}
	return []byte(strings.Join(lines, "\n"))
}
