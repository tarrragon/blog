// Package mdcards implements cross-file completeness checks for mdtools
// cards. Unlike fmt and lint which operate on one file at a time, cards
// builds a link graph over all content/**/*.md and runs graph-level
// assertions.
//
// Checks (per content/posts/markdown-writing-spec.md §5):
//   - L1 link validity: every relative link resolves to an existing file.
//   - L2 orphan detection: every card has ≥ 1 inbound edge from non-card content.
//   - L4 K4 structure: a card's first paragraph and "概念位置" section
//                      each contain ≥ 1 adjacent-card link.
package mdcards

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/yuin/goldmark/ast"

	"blog/scripts/mdtools/internal/astutil"
	"blog/scripts/mdtools/internal/files"
)

// Edge is a single relative link from source file to target file,
// resolved Hugo-style (URL directory relative to the source's slug).
type Edge struct {
	SourcePath  string // path of the file containing the link
	SourceLine  int    // 1-based line number of the link (0 if unknown)
	Destination string // raw link destination as written in markdown
	Target      string // resolved target path (no .md suffix; may or may not exist)
	DisplayText string // link display text (for anti-phishing and debug)
}

// FileNode is one markdown file with its parsed AST cached for reuse
// across L1/L2/L4 checks.
type FileNode struct {
	Path string
	AST  ast.Node
	Src  []byte
}

// Graph is the link graph over a content tree.
type Graph struct {
	Files []FileNode
	Edges []Edge

	byPath   map[string]*FileNode // path → FileNode, for quick lookup
	inbound  map[string][]int     // target path → edge indices
	outbound map[string][]int     // source path → edge indices
}

// BuildGraph walks the given roots (typically just "content"), parses
// every .md with goldmark, extracts relative-Link nodes, and resolves
// each destination to a candidate filesystem target.
func BuildGraph(roots []string) (*Graph, error) {
	mdFiles, err := files.WalkMarkdown(roots)
	if err != nil {
		return nil, err
	}

	parser := astutil.NewParser()
	g := &Graph{
		byPath:   map[string]*FileNode{},
		inbound:  map[string][]int{},
		outbound: map[string][]int{},
	}

	for _, path := range mdFiles {
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, err
		}
		doc := parser.Parse(data)
		node := FileNode{Path: path, AST: doc, Src: data}
		g.Files = append(g.Files, node)
		g.byPath[path] = &g.Files[len(g.Files)-1]
	}

	// Extract edges in a second pass so g.Files is stable before we
	// take pointers into it.
	for _, node := range g.Files {
		g.extractEdges(node)
	}

	return g, nil
}

// extractEdges walks node's AST, finds every Link node pointing to a
// relative (non-external) destination, resolves it, and adds an Edge.
func (g *Graph) extractEdges(fn FileNode) {
	ast.Walk(fn.AST, func(n ast.Node, entering bool) (ast.WalkStatus, error) {
		if !entering {
			return ast.WalkContinue, nil
		}
		link, ok := n.(*ast.Link)
		if !ok {
			return ast.WalkContinue, nil
		}
		dest := string(link.Destination)
		if isExternalOrAnchor(dest) {
			return ast.WalkContinue, nil
		}
		target := resolveTarget(fn.Path, dest)
		if target == "" {
			return ast.WalkContinue, nil
		}
		edge := Edge{
			SourcePath:  fn.Path,
			SourceLine:  nodeLine(n, fn.Src),
			Destination: dest,
			Target:      target,
			DisplayText: string(link.Text(fn.Src)),
		}
		g.Edges = append(g.Edges, edge)
		idx := len(g.Edges) - 1
		g.outbound[fn.Path] = append(g.outbound[fn.Path], idx)
		g.inbound[target] = append(g.inbound[target], idx)
		return ast.WalkContinue, nil
	})
}

// isExternalOrAnchor returns true when the link destination points
// outside the filesystem (http, https, mailto) or is a pure anchor.
func isExternalOrAnchor(dest string) bool {
	if dest == "" {
		return true
	}
	if strings.HasPrefix(dest, "#") {
		return true
	}
	for _, scheme := range []string{"http://", "https://", "mailto:", "tel:", "ftp://"} {
		if strings.HasPrefix(dest, scheme) {
			return true
		}
	}
	// Absolute path like "/about/" — treat as Hugo-rendered URL, skip.
	if strings.HasPrefix(dest, "/") {
		return true
	}
	return false
}

// resolveTarget mimics Hugo URL resolution to convert a relative link
// into a canonical filesystem-adjacent path (without the .md extension).
// The caller checks both "{target}.md" and "{target}/_index.md" because
// Hugo treats section index pages and content pages interchangeably in
// URL routing.
//
// Accepts both conventions observed in the repo:
//   - Hugo URL style: `../broker/` (slug with trailing slash).
//   - Filesystem style: `broker.md` (direct file reference).
//
// Both are normalized to the same canonical form. Anchor suffixes
// (`#section`) are stripped.
//
// Source file treatment:
//   - Content page `foo.md` sits at URL `<dir>/foo/`; relative links
//     are resolved from that URL directory.
//   - Section page `_index.md` sits at URL `<dir>/`; relatives are
//     resolved from `<dir>` directly.
func resolveTarget(sourcePath, dest string) string {
	if idx := strings.Index(dest, "#"); idx >= 0 {
		dest = dest[:idx]
	}
	dest = strings.TrimSuffix(dest, "/")
	dest = strings.TrimSuffix(dest, ".md")
	dest = strings.TrimSuffix(dest, ".markdown")
	if dest == "" {
		return ""
	}

	sourceDir := filepath.Dir(sourcePath)
	sourceBase := filepath.Base(sourcePath)
	if sourceBase != "_index.md" {
		// Content page: URL dir is <sourceDir>/<name>/
		sourceDir = filepath.Join(sourceDir, strings.TrimSuffix(sourceBase, ".md"))
	}
	return filepath.Clean(filepath.Join(sourceDir, dest))
}

// nodeLine extracts the 1-based line number where node begins in src.
// Goldmark only stores source segments on block-level nodes; calling
// Lines() on an inline node panics, so we walk up to the enclosing
// block. Returns 0 when unknown.
func nodeLine(n ast.Node, src []byte) int {
	for p := n; p != nil; p = p.Parent() {
		if p.Type() != ast.TypeBlock {
			continue
		}
		segs := p.Lines()
		if segs != nil && segs.Len() > 0 {
			return lineNumber(src, segs.At(0).Start)
		}
	}
	return 0
}

func lineNumber(src []byte, offset int) int {
	if offset < 0 || offset > len(src) {
		return 0
	}
	line := 1
	for i := 0; i < offset && i < len(src); i++ {
		if src[i] == '\n' {
			line++
		}
	}
	return line
}

// TargetExists reports whether target's canonical path resolves to an
// actual file on disk. Tries `{target}.md` then `{target}/_index.md`.
func TargetExists(target string) bool {
	for _, candidate := range []string{target + ".md", filepath.Join(target, "_index.md")} {
		if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
			return true
		}
	}
	return false
}

// Inbound returns the edge indices targeting the given path.
func (g *Graph) Inbound(target string) []int {
	return g.inbound[target]
}

// FindFile returns the cached FileNode for path, or nil.
func (g *Graph) FindFile(path string) *FileNode {
	return g.byPath[path]
}
