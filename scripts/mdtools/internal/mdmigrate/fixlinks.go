// Package mdmigrate holds one-off content migration tools. These are
// not part of the pre-commit / CI pipeline — they run manually when
// the repo has accumulated a class of violations that's not practical
// to fix by hand but too content-specific for fmt --fix.
//
// Current tool:
//   - fix-links: auto-correct broken relative links (L1) whose intended
//     target can be inferred by slug lookup. See content/posts/
//     markdown-writing-spec.md §5 (L1 link validity) for the rule the
//     fixes satisfy.
package mdmigrate

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"blog/scripts/mdtools/internal/mdcards"
)

// LinkFix is one proposed rewrite of a relative link destination.
type LinkFix struct {
	SourcePath string // file containing the broken link
	Line       int    // 1-based; may point to the enclosing block
	OldDest    string // destination as written (source of truth for text search)
	NewDest    string // corrected destination
	TargetPath string // resolved target file (for debug / reports)
	Reason     string // "single-candidate" | "knowledge-cards-preference" | "same-top-level-preference"
}

// UnresolvableLink is a broken link whose target cannot be inferred —
// the slug doesn't match any file or section in content/**.
type UnresolvableLink struct {
	SourcePath string
	Line       int
	Dest       string
	Slug       string
}

// FindFixes scans the graph, identifies broken L1 edges, and returns
// the proposed fixes plus the truly unresolvable ones. cardsRoot is
// the knowledge-cards directory prefix used by the heuristic that
// prefers card targets when slug matches multiple places.
func FindFixes(g *mdcards.Graph, cardsRoot string) ([]LinkFix, []UnresolvableLink) {
	slugIndex := buildSlugIndex(g)

	var fixes []LinkFix
	var unresolved []UnresolvableLink

	for _, edge := range g.Edges {
		if mdcards.TargetExists(edge.Target) {
			continue
		}
		fix, miss := resolveEdge(edge, slugIndex, cardsRoot)
		if fix != nil {
			fixes = append(fixes, *fix)
			continue
		}
		if miss != nil {
			unresolved = append(unresolved, *miss)
		}
	}

	sort.SliceStable(fixes, func(i, j int) bool {
		if fixes[i].SourcePath != fixes[j].SourcePath {
			return fixes[i].SourcePath < fixes[j].SourcePath
		}
		return fixes[i].Line < fixes[j].Line
	})
	sort.SliceStable(unresolved, func(i, j int) bool {
		if unresolved[i].SourcePath != unresolved[j].SourcePath {
			return unresolved[i].SourcePath < unresolved[j].SourcePath
		}
		return unresolved[i].Line < unresolved[j].Line
	})

	return fixes, unresolved
}

// buildSlugIndex maps a slug to the filesystem paths that could satisfy
// it. For content pages the path is the .md file without extension; for
// Hugo section pages (`_index.md`) the path is the enclosing directory
// (which is what Hugo routes `parent/slug/` to).
func buildSlugIndex(g *mdcards.Graph) map[string][]string {
	index := make(map[string][]string)
	for _, fn := range g.Files {
		base := filepath.Base(fn.Path)
		if base == "_index.md" {
			parent := filepath.Dir(fn.Path)
			slug := filepath.Base(parent)
			if slug != "" && slug != "." {
				index[slug] = append(index[slug], parent)
			}
			continue
		}
		slug := strings.TrimSuffix(base, ".md")
		target := strings.TrimSuffix(fn.Path, ".md")
		index[slug] = append(index[slug], target)
	}
	return index
}

// resolveEdge applies the three-tier heuristic (single candidate →
// knowledge-cards preference → same-top-level preference) and, if a
// unique target emerges, computes the correct relative URL from source
// to that target.
func resolveEdge(edge mdcards.Edge, slugIndex map[string][]string, cardsRoot string) (*LinkFix, *UnresolvableLink) {
	slug := extractSlug(edge.Destination)
	candidates := slugIndex[slug]
	if len(candidates) == 0 {
		return nil, &UnresolvableLink{
			SourcePath: edge.SourcePath,
			Line:       edge.SourceLine,
			Dest:       edge.Destination,
			Slug:       slug,
		}
	}

	reason := "single-candidate"
	if len(candidates) > 1 {
		if cards := filterCardCandidates(candidates, cardsRoot); len(cards) == 1 {
			candidates = cards
			reason = "knowledge-cards-preference"
		} else if len(cards) > 1 {
			candidates = cards
		}
	}
	if len(candidates) > 1 {
		if sameTop := filterSameTopLevel(candidates, edge.SourcePath); len(sameTop) == 1 {
			candidates = sameTop
			reason = "same-top-level-preference"
		}
	}
	if len(candidates) != 1 {
		return nil, &UnresolvableLink{
			SourcePath: edge.SourcePath,
			Line:       edge.SourceLine,
			Dest:       edge.Destination,
			Slug:       slug,
		}
	}

	newDest, err := computeRelativeURL(edge.SourcePath, candidates[0])
	if err != nil {
		return nil, &UnresolvableLink{
			SourcePath: edge.SourcePath,
			Line:       edge.SourceLine,
			Dest:       edge.Destination,
			Slug:       slug,
		}
	}
	// Preserve the anchor fragment if the original link had one.
	if i := strings.Index(edge.Destination, "#"); i >= 0 {
		newDest += edge.Destination[i:]
	}
	if newDest == edge.Destination {
		return nil, nil // already correct but graph said broken — silent skip
	}
	return &LinkFix{
		SourcePath: edge.SourcePath,
		Line:       edge.SourceLine,
		OldDest:    edge.Destination,
		NewDest:    newDest,
		TargetPath: candidates[0],
		Reason:     reason,
	}, nil
}

// extractSlug returns the final path segment of dest, after stripping
// anchor, trailing slash, and .md extension. Matches the form used in
// buildSlugIndex.
func extractSlug(dest string) string {
	if i := strings.Index(dest, "#"); i >= 0 {
		dest = dest[:i]
	}
	dest = strings.TrimSuffix(dest, "/")
	dest = strings.TrimSuffix(dest, ".md")
	dest = strings.TrimSuffix(dest, ".markdown")
	if i := strings.LastIndex(dest, "/"); i >= 0 {
		return dest[i+1:]
	}
	return dest
}

// filterCardCandidates returns the subset of candidates that live under
// cardsRoot (e.g. content/backend/knowledge-cards).
func filterCardCandidates(candidates []string, cardsRoot string) []string {
	root := strings.TrimSuffix(filepath.ToSlash(cardsRoot), "/") + "/"
	var out []string
	for _, c := range candidates {
		if strings.Contains(filepath.ToSlash(c), root) {
			out = append(out, c)
		}
	}
	return out
}

// filterSameTopLevel returns candidates whose top-level content subdir
// matches the source's. For sourcePath=content/go/xxx.md, the top-level
// is "go" and candidates under content/go/** are preferred.
func filterSameTopLevel(candidates []string, sourcePath string) []string {
	srcTop := topLevelUnderContent(sourcePath)
	if srcTop == "" {
		return candidates
	}
	var out []string
	for _, c := range candidates {
		if topLevelUnderContent(c) == srcTop {
			out = append(out, c)
		}
	}
	return out
}

func topLevelUnderContent(path string) string {
	parts := strings.Split(filepath.ToSlash(path), "/")
	for i, p := range parts {
		if p == "content" && i+1 < len(parts) {
			return parts[i+1]
		}
	}
	return ""
}

// computeRelativeURL yields the Hugo-URL-relative form of target as
// written from sourcePath. Produces e.g. "../../knowledge-cards/broker/".
//
// Source treatment:
//   - Content page `foo.md`   → URL dir is `<dir>/foo/`.
//   - Section page `_index.md`→ URL dir is `<dir>/`.
//
// Target treatment:
//   - Plain file path (without .md) → treated as the URL-dir form
//     directly (that's what buildSlugIndex stored).
//   - Section dir path → treated as the URL dir directly.
func computeRelativeURL(sourcePath, target string) (string, error) {
	srcURLDir := urlDirOfSource(sourcePath)

	rel, err := filepath.Rel(srcURLDir, target)
	if err != nil {
		return "", err
	}
	rel = filepath.ToSlash(rel)
	if !strings.HasSuffix(rel, "/") {
		rel += "/"
	}
	return rel, nil
}

func urlDirOfSource(sourcePath string) string {
	base := filepath.Base(sourcePath)
	if base == "_index.md" {
		return filepath.Dir(sourcePath)
	}
	return filepath.Join(filepath.Dir(sourcePath), strings.TrimSuffix(base, ".md"))
}

// ApplyFixes groups fixes by source file and rewrites each file with a
// single read/write cycle. Within a file, fixes with identical OldDest
// are deduplicated — a single ReplaceAll handles every occurrence.
// Returns the number of files modified.
func ApplyFixes(fixes []LinkFix) (int, error) {
	bySource := map[string][]LinkFix{}
	for _, f := range fixes {
		bySource[f.SourcePath] = append(bySource[f.SourcePath], f)
	}
	modified := 0
	for path, set := range bySource {
		data, err := os.ReadFile(path)
		if err != nil {
			return modified, fmt.Errorf("%s: %w", path, err)
		}
		seen := map[string]string{}
		for _, f := range set {
			seen[f.OldDest] = f.NewDest
		}
		content := string(data)
		changed := false
		for old, nu := range seen {
			needle := "](" + old + ")"
			replace := "](" + nu + ")"
			next := strings.ReplaceAll(content, needle, replace)
			if next != content {
				content = next
				changed = true
			}
		}
		if !changed {
			continue
		}
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			return modified, fmt.Errorf("%s: %w", path, err)
		}
		modified++
	}
	return modified, nil
}
