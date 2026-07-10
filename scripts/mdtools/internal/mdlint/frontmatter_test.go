package mdlint

import "testing"

// isStrictCardPath decides which files get the strictest front-matter
// schema. A wrong answer here changes nothing observable — the file just
// stops being checked — so the behaviour is pinned rather than trusted.
func TestIsStrictCardPath(t *testing.T) {
	cardPaths := []string{"content/backend/knowledge-cards", "content/report"}

	cases := []struct {
		name  string
		path  string
		roots []string
		want  bool
	}{
		{"card under a listed root", "content/report/some-card.md", cardPaths, true},
		{"card under the other listed root", "content/backend/knowledge-cards/idempotency.md", cardPaths, true},
		{"nested below a listed root", "content/report/sub/deep.md", cardPaths, true},

		// Section landing pages are Hugo list pages, not cards: they carry
		// no date and must not be forced into the card schema.
		{"section index is never a card", "content/report/_index.md", cardPaths, false},
		{"nested section index is never a card", "content/backend/knowledge-cards/_index.md", cardPaths, false},

		{"unlisted directory", "content/posts/writing-spec.md", cardPaths, false},

		// The root is matched with a trailing slash, so a directory that
		// merely shares a prefix must not be swept in.
		{"prefix-sharing sibling directory", "content/reportage/note.md", cardPaths, false},

		{"no roots configured", "content/report/some-card.md", nil, false},
		{"empty root entry is skipped", "content/report/some-card.md", []string{""}, false},
		{"trailing slash in root still matches", "content/report/some-card.md", []string{"content/report/"}, true},

		// Paths are normalised before comparison, so a caller passing OS
		// separators gets the same verdict.
		{"leading ./ in path", "./content/report/some-card.md", cardPaths, true},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := isStrictCardPath(tc.path, tc.roots); got != tc.want {
				t.Errorf("isStrictCardPath(%q, %v) = %v, want %v", tc.path, tc.roots, got, tc.want)
			}
		})
	}
}
