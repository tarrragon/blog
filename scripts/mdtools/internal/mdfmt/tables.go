package mdfmt

import (
	"strings"
)

// FixTableCompactStyle implements MD060 (§4 of the spec) — enforce the
// compact table style: one space after the opening pipe and one space
// before the closing pipe, with each delimiter surrounded by single
// spaces. Separator rows use `| --- |` (no alignment colons unless the
// author explicitly kept them, in which case we leave them alone).
//
// Scope: only lines that are part of a GFM pipe table. A line is
// considered part of a table when it starts with `|` (optionally after
// up to 3 spaces of indent) OR is a separator line following a header.
// Content inside fenced code blocks / front matter is skipped via
// LineContext.
func FixTableCompactStyle(lines []string, ctx LineContext) []string {
	out := make([]string, len(lines))
	for i, line := range lines {
		if ctx.Skip[i] || !isTableRowLine(line) {
			out[i] = line
			continue
		}
		out[i] = normalizeTableRow(line)
	}
	return out
}

// isTableRowLine reports whether line looks like a GFM pipe table row.
// Requires a `|` at start (up to 3 leading spaces allowed) and at least
// one additional `|` elsewhere on the line.
func isTableRowLine(line string) bool {
	trimmed := strings.TrimLeft(line, " ")
	if len(line)-len(trimmed) > 3 {
		return false
	}
	if !strings.HasPrefix(trimmed, "|") {
		return false
	}
	// Must have at least a second `|` (cell delimiter).
	if strings.Count(trimmed, "|") < 2 {
		return false
	}
	return true
}

// normalizeTableRow rewrites a table row to the compact style.
// Preserves:
//   - Indent level (leading spaces before the first `|`).
//   - Cell contents (inner whitespace and escaped pipes `\|`).
//   - Alignment colons on separator rows (`:---`, `---:`, `:---:`).
//
// Escapes `\|` are respected: a literal pipe inside a cell does not
// split the cell.
func normalizeTableRow(line string) string {
	// Preserve leading indent.
	trimmed := strings.TrimLeft(line, " ")
	indent := line[:len(line)-len(trimmed)]
	trimmed = strings.TrimRight(trimmed, " \t")

	cells := splitTableCells(trimmed)
	// splitTableCells produces leading and trailing empty strings for
	// the outer `|` bounds; the actual cells sit in between.
	if len(cells) < 3 {
		return line
	}
	for i := range cells {
		cells[i] = strings.TrimSpace(cells[i])
	}
	// Reassemble with " | " delimiters and flanking " | " boundaries.
	// cells = ["", a, b, ..., z, ""] → "| a | b | ... | z |"
	return indent + "| " + strings.Join(cells[1:len(cells)-1], " | ") + " |"
}

// splitTableCells splits a row on unescaped `|`. Returns slice where
// the first and last entries are the empty strings flanking the outer
// boundary pipes.
func splitTableCells(row string) []string {
	var cells []string
	var current strings.Builder
	for i := 0; i < len(row); i++ {
		c := row[i]
		if c == '\\' && i+1 < len(row) && row[i+1] == '|' {
			current.WriteByte('\\')
			current.WriteByte('|')
			i++
			continue
		}
		if c == '|' {
			cells = append(cells, current.String())
			current.Reset()
			continue
		}
		current.WriteByte(c)
	}
	cells = append(cells, current.String())
	return cells
}
