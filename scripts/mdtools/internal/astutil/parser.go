// Package astutil wraps goldmark parsing and AST walking utilities shared
// across mdtools subcommands. The goal is to parse each markdown file at
// most once per mdtools invocation and expose helpers (parent chain lookup,
// node text extraction, code-block detection) that the rule packages can
// reuse without re-implementing walker bookkeeping.
package astutil

import (
	"github.com/yuin/goldmark"
	"github.com/yuin/goldmark/ast"
	"github.com/yuin/goldmark/extension"
	"github.com/yuin/goldmark/parser"
	"github.com/yuin/goldmark/text"
)

// Parser wraps a configured goldmark.Markdown with the extensions required
// to produce the same AST that Hugo uses during render.
type Parser struct {
	md goldmark.Markdown
}

// NewParser returns a Parser with GFM extensions enabled, matching Hugo's
// default content pipeline.
func NewParser() *Parser {
	md := goldmark.New(
		goldmark.WithExtensions(
			extension.GFM, // includes Table, Strikethrough, Linkify, TaskList
		),
	)
	return &Parser{md: md}
}

// Parse returns the root document node for src. The returned node retains
// the source byte slice; callers must keep src alive while walking.
func (p *Parser) Parse(src []byte) ast.Node {
	reader := text.NewReader(src)
	return p.md.Parser().Parse(reader, parser.WithContext(parser.NewContext()))
}
