// Package report provides a unified violation type and reporter used by
// all mdtools subcommands. Keeping the format stable matters because
// pre-commit hooks and CI log scrapers parse this output.
package report

import (
	"fmt"
	"io"
	"sort"
)

// Violation describes a single rule violation located at a specific
// position in a markdown source file.
type Violation struct {
	Path    string // relative path from repo root
	Line    int    // 1-based line number; 0 if whole-file
	Column  int    // 1-based column; 0 if line-level
	Rule    string // rule identifier, e.g. "MD024-siblings_only"
	Level   Level  // severity
	Message string
}

// Level is the severity of a violation.
type Level int

const (
	LevelWarn Level = iota
	LevelError
)

func (l Level) String() string {
	switch l {
	case LevelError:
		return "error"
	case LevelWarn:
		return "warn"
	}
	return "unknown"
}

// Reporter collects violations during a run and emits them in a stable
// order suitable for pre-commit output and CI log diffing.
type Reporter struct {
	violations []Violation
}

// Add appends a violation to the reporter.
func (r *Reporter) Add(v Violation) {
	r.violations = append(r.violations, v)
}

// Count returns the total number of violations added.
func (r *Reporter) Count() int {
	return len(r.violations)
}

// ErrorCount returns the number of error-level violations.
// Pre-commit / CI exit codes key off this.
func (r *Reporter) ErrorCount() int {
	n := 0
	for _, v := range r.violations {
		if v.Level == LevelError {
			n++
		}
	}
	return n
}

// Write emits violations to w in path/line/column order.
func (r *Reporter) Write(w io.Writer) {
	sorted := make([]Violation, len(r.violations))
	copy(sorted, r.violations)
	sort.SliceStable(sorted, func(i, j int) bool {
		a, b := sorted[i], sorted[j]
		if a.Path != b.Path {
			return a.Path < b.Path
		}
		if a.Line != b.Line {
			return a.Line < b.Line
		}
		if a.Column != b.Column {
			return a.Column < b.Column
		}
		return a.Rule < b.Rule
	})
	for _, v := range sorted {
		line := v.Line
		col := v.Column
		switch {
		case line == 0:
			fmt.Fprintf(w, "%s: [%s] %s %s\n", v.Path, v.Level, v.Rule, v.Message)
		case col == 0:
			fmt.Fprintf(w, "%s:%d: [%s] %s %s\n", v.Path, line, v.Level, v.Rule, v.Message)
		default:
			fmt.Fprintf(w, "%s:%d:%d: [%s] %s %s\n", v.Path, line, col, v.Level, v.Rule, v.Message)
		}
	}
}
