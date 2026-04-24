// Package files provides file discovery shared across mdtools subcommands.
package files

import (
	"io/fs"
	"path/filepath"
	"strings"
)

// skippedDirs names directories that mdtools never descends into — build
// output, third-party theme content, dependency caches.
var skippedDirs = map[string]bool{
	"public":       true, // Hugo build output
	"resources":    true, // Hugo cache
	"themes":       true, // third-party
	"node_modules": true,
	".git":         true,
	"bin":          true,
}

// WalkMarkdown returns the set of `.md` files reachable under paths.
// Directories are walked recursively. Files passed directly are included
// even when outside typical content roots. Hidden directories (dotfiles)
// are skipped unless the path itself starts with "." (for explicit opt-in).
func WalkMarkdown(paths []string) ([]string, error) {
	var out []string
	for _, root := range paths {
		err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if d.IsDir() {
				name := d.Name()
				if skippedDirs[name] {
					return fs.SkipDir
				}
				if name != root && strings.HasPrefix(name, ".") && name != "." {
					return fs.SkipDir
				}
				return nil
			}
			if strings.EqualFold(filepath.Ext(path), ".md") {
				out = append(out, path)
			}
			return nil
		})
		if err != nil {
			return nil, err
		}
	}
	return out, nil
}
