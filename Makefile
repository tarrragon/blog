# Blog mdtools build and quality-gate targets.
#
# This Makefile wraps scripts/mdtools (Go + goldmark markdown toolchain)
# so contributors and CI both invoke the same commands. See
# content/posts/mdtools-design.md for architecture context.

MDTOOLS_SRC := $(shell find scripts/mdtools -type f -name '*.go' 2>/dev/null)
MDTOOLS_MOD := scripts/mdtools/go.mod scripts/mdtools/go.sum
MDTOOLS_BIN := bin/mdtools

.PHONY: build check fix lint cards install-hooks clean help site

help:
	@echo "Blog mdtools targets:"
	@echo ""
	@echo "  make build           Build bin/mdtools (rebuilds on source changes)"
	@echo "  make check           Run fmt --check + lint + cards (CI mode)"
	@echo "  make fix             Apply fmt --fix to content/**"
	@echo "  make lint            Run lint on content/**"
	@echo "  make cards           Run cards on content/**"
	@echo "  make install-hooks   Point git at .githooks/ for pre-commit"
	@echo "  make site            Build Hugo + Pagefind search index into public/"
	@echo "  make clean           Remove bin/"

build: $(MDTOOLS_BIN)

$(MDTOOLS_BIN): $(MDTOOLS_SRC) $(MDTOOLS_MOD)
	@mkdir -p bin
	@cd scripts/mdtools && go build -o ../../$(MDTOOLS_BIN) .
	@echo "built $(MDTOOLS_BIN)"

check: build
	@./$(MDTOOLS_BIN) fmt --check content/
	@./$(MDTOOLS_BIN) lint content/
	@./$(MDTOOLS_BIN) cards content/

fix: build
	@./$(MDTOOLS_BIN) fmt --fix content/

lint: build
	@./$(MDTOOLS_BIN) lint content/

cards: build
	@./$(MDTOOLS_BIN) cards content/

install-hooks:
	@git config core.hooksPath .githooks
	@echo "hooks installed: git config core.hooksPath .githooks"
	@echo "run 'make build' once to produce bin/mdtools"

clean:
	@rm -rf bin/
	@echo "removed bin/"

# Full site build: Hugo output + Pagefind search index.
# Run this locally before previewing search; CI runs the same two steps.
site:
	@rm -rf public
	@hugo --minify
	@npx -y pagefind --site public --root-selector main
