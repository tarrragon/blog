# mdtools

Blog-internal markdown toolchain. Implements the rule contract defined in
`content/posts/markdown-writing-spec.md` using Go + goldmark AST, plus one
post-build pass (`autolink-html`) over the HTML and RSS hugo generates.

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
mdtools autolink-gaps <paths...>          Card names a page mentions that the site will not auto-link
mdtools autolink-html <public-dir>        Write the card auto-links into a built site (after hugo)
mdtools help                              Show usage
mdtools version                           Print version
```

When no paths are given, defaults to `content/**` (`autolink-gaps` requires paths and runs from the repo root, since it reads `data/autolink_terms.json`; `autolink-html` takes exactly one built-site directory).

`lint` and `cards` share two flags:

- `-warn-as-error` treats warnings as errors (CI strict mode).
- `-warn-summary` lists errors in full but collapses warnings into one
  count per rule. The pre-push hook runs `make check CHECK_FLAGS=-warn-summary`
  so the standing warning backlog does not bury the error count; run
  `make check` without it to see every warning. The flag is ignored under
  `-warn-as-error`, where the warnings decide the exit code.

`autolink-html` rewrites the HTML and RSS files hugo wrote, in place: it
links the knowledge-card names in every page that loads the autolink script
and marks that script `data-static`, so the page script
(`assets/js/autolink.js`) skips its own linking. The Makefile's `postbuild`
target runs it between `hugo --minify` and pagefind, and both `make site` and
the deploy workflow (`.github/workflows/deploy.yml`) run that target; `hugo
server` does not, and the page script links in local preview.
The matching rules are listed once, in the header of `assets/js/autolink.js`,
and implemented twice, there and in `internal/autolinkhtml`; a rule change goes
into both programs, into the Go tests, and into `internal/mdcards/autolink.go`,
the markdown approximation that the L2 orphan-card check and `autolink-gaps` use.
`internal/autolinkhtml/jsparity_test.go` fails when the script's SKIP list and
`skipTags` differ; no tool catches a drift in the other rules.
Only `.article-body` of pages whose section is in the `scopes` of
`data/autolink.toml` is linked, and in each RSS item only `content:encoded`, by
the scope of the page at the item's link; feed links carry the card title in
`title` and leave out the tooltip attributes, which only the site's CSS uses.
The dictionary is read from the built
site (the JSON the page script loads), so the argument must be a site hugo has
already written. It prints one line to stderr (pages scanned and linked, links,
pages already linked; feeds, items, links) and exits 2 when the directory, a
page or the dictionary cannot be read or written, or when the directory holds
no .html file.
A second run changes nothing: pages already marked `data-static` are skipped,
and in the feeds the names already inside a link are left alone. To check a
build, `make site && make test` runs `tests/autolink-static.spec.ts`, which
reads a page and a feed with JavaScript off.

## Package layout

```text
scripts/mdtools/
├── main.go                 subcommand dispatcher
├── cmd/                    subcommand entry points (one file per subcommand)
├── internal/
│   ├── astutil/            goldmark wrapper + walker helpers
│   ├── autolinkhtml/       card auto-links written into the built HTML and RSS
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
