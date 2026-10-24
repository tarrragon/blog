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

`lint` and `cards` share two flags:

- `-warn-as-error` treats warnings as errors (CI strict mode).
- `-warn-summary` lists errors in full but collapses warnings into one
  count per rule. The pre-push hook runs `make check CHECK_FLAGS=-warn-summary`
  so the standing warning backlog does not bury the error count; run
  `make check` without it to see every warning. The flag is ignored under
  `-warn-as-error`, where the warnings decide the exit code.

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

## Development

- 測試在這個目錄跑：`(cd scripts/mdtools && go test ./...)`。`go.mod` 在 `scripts/mdtools/`，在 repo 根目錄跑 `go test ./...` 會失敗。CI 的 md-check 也會跑（Test step 在 lint 與 cards 之前）。新增檢查邏輯要附測試，並用突變驗證測試有作用：改壞實作，確認對應的 case 失敗。
- **跨檔規則放 `mdcards`，不放 `mdlint`**：pre-commit 只餵 staged 的檔案給 lint，跨檔規則在那裡會把「其他檔案沒被 staged」誤判成違規。`cards` 掃整個 content。
- **fmt 規則必須冪等**（`fmt(fmt(x)) == fmt(x)`）：CI 的 `fmt --fix` 會自動 commit，不冪等的規則會讓 bot 每次 push 都產生新的 diff。新的 fmt 規則加 fixture 進 `internal/mdfmt/fixer_test.go` 的 `TestApplyAllIdempotent`；規則不冪等時這個測試會失敗。
- 測試 fixture 不用 map 迭代建圖：Go 的 map 每次迭代的順序不同，同一個測試會在某些順序下通過、某些順序下失敗，通過的那一次證明不了行為正確。依賴走訪順序的行為，要有正序與逆序各餵一次的測試。

## Spec references

- Rule contract: `content/posts/markdown-writing-spec.md`
- Architecture rationale: `content/posts/mdtools-design.md`
- AST rationale: `content/posts/what-is-ast.md`
- Agent integration: `docs/rules/markdown.md`
