package mdlint

import (
	"github.com/yuin/goldmark/ast"
)

// nodeStartLine returns the 1-based line number where node begins in
// src. Only block-level nodes carry source segments in goldmark; for
// inline nodes we walk up to the enclosing block. Returns 0 if unknown.
func nodeStartLine(n ast.Node, src []byte) int {
	for p := n; p != nil; p = p.Parent() {
		if p.Type() != ast.TypeBlock {
			continue
		}
		segs := p.Lines()
		if segs == nil || segs.Len() == 0 {
			continue
		}
		return offsetToLine(src, segs.At(0).Start)
	}
	return 0
}

func offsetToLine(src []byte, offset int) int {
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
