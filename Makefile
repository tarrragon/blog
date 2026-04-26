# Blog mdtools build and quality-gate targets.
#
# This Makefile wraps scripts/mdtools (Go + goldmark markdown toolchain)
# so contributors and CI both invoke the same commands. See
# content/posts/mdtools-design.md for architecture context.

MDTOOLS_SRC := $(shell find scripts/mdtools -type f -name '*.go' 2>/dev/null)
MDTOOLS_MOD := scripts/mdtools/go.mod scripts/mdtools/go.sum
MDTOOLS_BIN := bin/mdtools

.PHONY: build check fix lint cards install-hooks clean help site test verify-red-green

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
	@echo "  make test            Run Playwright tests (requires make site first)"
	@echo "  make verify-red-green Verify a test catches the bug it claims to (#69)"
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

# Full site build: Hugo output + Pagefind search indexes.
# Three indexes for the search page's scope filter (#55-#66 strategy C):
#   pagefind/         — full content (main); default index, scope=all
#   pagefind-title/   — title-only (article > h1); scope=title
#   pagefind-content/ — body-only (.article-body); scope=content
# Each scope is the full set under that mode — no view-layer post-filter.
site:
	@rm -rf public
	@hugo --minify
	@npx -y pagefind --site public --root-selector main
	@npx -y pagefind --site public --root-selector "article.article-content > h1" --output-subdir pagefind-title
	@npx -y pagefind --site public --root-selector ".article-body" --output-subdir pagefind-content

# Run Playwright tests against the static build in public/.
# Pre-requisite: `make site` (the test runner expects public/ to exist).
test:
	@rm -rf .test-www
	@mkdir -p .test-www
	@ln -sfn ../public .test-www/blog
	@npx playwright test

# Retrospective RED-GREEN verify (#69 Test-First protocol).
# Usage: make verify-red-green PRE_FIX=<commit-sha>
#
# Checks out the pre-fix commit's source files, rebuilds the site, and runs
# the current HEAD's test suite against it. The tests should FAIL (RED) on the
# buggy code — proving they catch the regression. Then restores HEAD + rebuilds
# + re-runs to confirm GREEN.
#
# Why: A test that's only ever seen GREEN is unverified. Seeing RED then GREEN
# proves both the test catches the bug AND the fix solves it. Detail in
# content/report/test-first-red-before-green/.
verify-red-green:
	@if [ -z "$(PRE_FIX)" ]; then \
		echo "Usage: make verify-red-green PRE_FIX=<commit-sha>"; \
		echo ""; \
		echo "<commit-sha> should be the commit BEFORE the fix you want to verify."; \
		echo "Example: make verify-red-green PRE_FIX=43b9ced"; \
		exit 1; \
	fi
	@echo "=== Step 1: Stash current state, checkout pre-fix source ==="
	@git stash push -m "verify-red-green stash" >/dev/null 2>&1 || true
	@git checkout $(PRE_FIX) -- layouts/ Makefile 2>/dev/null || \
		(echo "Cannot checkout $(PRE_FIX)"; exit 1)
	@echo ""
	@echo "=== Step 2: Build site with pre-fix source ==="
	@$(MAKE) site
	@echo ""
	@echo "=== Step 3: Run tests — expect RED (some failures prove tests catch the bug) ==="
	@$(MAKE) test || echo "(RED phase complete — failures are expected and good)"
	@echo ""
	@echo "=== Step 4: Restore HEAD source ==="
	@git checkout HEAD -- layouts/ Makefile
	@git stash pop >/dev/null 2>&1 || true
	@echo ""
	@echo "=== Step 5: Rebuild + run tests on fixed code — expect GREEN ==="
	@$(MAKE) site
	@$(MAKE) test
	@echo ""
	@echo "=== Verify complete ==="
	@echo "If you saw failures in Step 3 + all-pass in Step 5, the tests are verified."
	@echo "If Step 3 was all-pass too, the tests are weak — they don't catch the bug."
