package mdfmt

import (
	"strings"

	"github.com/mattn/go-runewidth"

	"blog/scripts/mdtools/internal/rules"
)

func init() {
	// Blog content mixes CJK and ASCII; ambiguous-width chars (like
	// fullwidth punctuation) should count as 2 columns to match the
	// visual layout in a CJK-aware monospace font.
	runewidth.EastAsianWidth = true
}

// FixTables normalizes pipe tables per rules.Tables.Style. Supports:
//
//   - "aligned" (default, per §4 of the spec): every column is padded
//     with trailing spaces to the max display width observed in that
//     column across all rows in the table. Pipes line up vertically.
//     CJK width is computed via go-runewidth.
//   - "compact": single space around each pipe, no padding.
//
// Skip lines (front matter, fenced code interior) are preserved
// verbatim via LineContext.
func FixTables(lines []string, ctx LineContext, cfg rules.TableRules) []string {
	out := make([]string, 0, len(lines))
	for i := 0; i < len(lines); {
		if ctx.Skip[i] || !isTableRowLine(lines[i]) {
			out = append(out, lines[i])
			i++
			continue
		}
		start := i
		for i < len(lines) && !ctx.Skip[i] && isTableRowLine(lines[i]) {
			i++
		}
		block := lines[start:i]
		switch cfg.Style {
		case "compact":
			for _, row := range block {
				out = append(out, normalizeCompactRow(row))
			}
		default:
			out = append(out, normalizeAlignedTable(block)...)
		}
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
	if strings.Count(trimmed, "|") < 2 {
		return false
	}
	return true
}

// normalizeCompactRow rewrites a table row to compact style: single
// space after the opening pipe, single space before the closing pipe,
// and single-space delimiters between cells. Preserves escaped `\|`.
func normalizeCompactRow(line string) string {
	indent, trimmed := stripLeadingIndent(line)
	trimmed = strings.TrimRight(trimmed, " \t")
	cells := splitTableCells(trimmed)
	if len(cells) < 3 {
		return line
	}
	inner := cells[1 : len(cells)-1]
	for i := range inner {
		inner[i] = strings.TrimSpace(inner[i])
	}
	return indent + "| " + strings.Join(inner, " | ") + " |"
}

// normalizeAlignedTable computes column widths for the entire table
// (all contiguous rows) and emits each row padded to those widths.
// The separator row's dashes are regenerated to match column width;
// alignment colons are dropped per §4 of the spec.
func normalizeAlignedTable(rows []string) []string {
	if len(rows) == 0 {
		return rows
	}

	indent, _ := stripLeadingIndent(rows[0])

	parsed := make([][]string, len(rows))
	isSep := make([]bool, len(rows))
	for i, row := range rows {
		_, trimmed := stripLeadingIndent(row)
		trimmed = strings.TrimRight(trimmed, " \t")
		cells := splitTableCells(trimmed)
		if len(cells) < 3 {
			return rows // malformed; leave verbatim
		}
		inner := cells[1 : len(cells)-1]
		for j := range inner {
			inner[j] = strings.TrimSpace(inner[j])
		}
		parsed[i] = inner
		isSep[i] = isSeparatorCells(inner)
	}

	numCols := 0
	for _, row := range parsed {
		if len(row) > numCols {
			numCols = len(row)
		}
	}
	if numCols == 0 {
		return rows
	}

	widths := make([]int, numCols)
	for i, row := range parsed {
		if isSep[i] {
			continue // don't let separator dashes drive width
		}
		for c, cell := range row {
			w := runewidth.StringWidth(cell)
			if w > widths[c] {
				widths[c] = w
			}
		}
	}
	// Separator cells need at least 3 dashes; also enforce 3 as column floor.
	for c := range widths {
		if widths[c] < 3 {
			widths[c] = 3
		}
	}

	out := make([]string, len(rows))
	for i, row := range parsed {
		var b strings.Builder
		b.WriteString(indent)
		b.WriteString("|")
		for c := 0; c < numCols; c++ {
			var content string
			if c < len(row) {
				content = row[c]
			}
			b.WriteString(" ")
			if isSep[i] {
				b.WriteString(strings.Repeat("-", widths[c]))
			} else {
				b.WriteString(content)
				pad := widths[c] - runewidth.StringWidth(content)
				if pad < 0 {
					pad = 0
				}
				b.WriteString(strings.Repeat(" ", pad))
			}
			b.WriteString(" |")
		}
		out[i] = b.String()
	}
	return out
}

// isSeparatorCells reports whether every cell looks like a table
// separator entry: only dashes (and optional leading/trailing `:` for
// alignment, which we strip during emission). Empty cells count.
func isSeparatorCells(cells []string) bool {
	if len(cells) == 0 {
		return false
	}
	for _, c := range cells {
		t := strings.Trim(c, ":")
		if t == "" {
			continue // all colons → still accept as separator ambiguity
		}
		for _, r := range t {
			if r != '-' {
				return false
			}
		}
	}
	// Must have at least one dash somewhere, else it's an empty header row.
	for _, c := range cells {
		if strings.ContainsRune(c, '-') {
			return true
		}
	}
	return false
}

// stripLeadingIndent returns the leading whitespace run and the rest.
func stripLeadingIndent(line string) (indent, rest string) {
	i := 0
	for i < len(line) && (line[i] == ' ' || line[i] == '\t') {
		i++
	}
	return line[:i], line[i:]
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
