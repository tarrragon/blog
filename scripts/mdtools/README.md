# mdtools

Blog-internal markdown toolchain. Implements the rule contract defined in
`content/posts/markdown-writing-spec.md` using Go + goldmark AST.

## Build

```bash
(cd scripts/mdtools && go build -o ../../bin/mdtools .)
```

Binary output is `bin/mdtools` at the repo root (gitignored).

## Subcommands

```text
mdtools fmt [--fix|--check] [paths...]    Format normalization
mdtools lint [paths...]                   Structural + schema checks
mdtools cards [paths...]                  Cross-file card completeness
mdtools help                              Show usage
mdtools version                           Print version
```

When no paths are given, defaults to `content/**`.

## Package layout

```text
scripts/mdtools/
├── main.go                 subcommand dispatcher
├── cmd/                    subcommand entry points (Fmt, Lint, Cards)
├── internal/
│   ├── astutil/            goldmark wrapper + walker helpers
│   ├── rules/              toggle-able rule config mirroring spec §1-§7
│   └── report/             Violation type and stable output formatter
└── README.md
```

## Spec references

- Rule contract: `content/posts/markdown-writing-spec.md`
- Architecture rationale: `content/posts/mdtools-design.md`
- AST rationale: `content/posts/what-is-ast.md`
- Agent integration: `AGENTS.md` §8
