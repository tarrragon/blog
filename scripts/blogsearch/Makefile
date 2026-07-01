.PHONY: build install ingest rebuild query status verify bench clean help

BINARY    := ../../bin/blogsearch
INDEX_DIR := ../../.blogsearch
CONTENT   := ../../content
EMBED_MODEL := nomic-embed-text

## Build

build: ## Build blogsearch binary
	go build -o $(BINARY) .

install: build ## Build + pull embedding model (first-time setup)
	@echo "Checking Ollama..."
	@curl -s http://localhost:11434/api/tags > /dev/null 2>&1 || \
		(echo "ERROR: Ollama not running. Start with: ollama serve &" && exit 1)
	@echo "Pulling $(EMBED_MODEL)..."
	ollama pull $(EMBED_MODEL)
	@echo "Ready. Run 'make ingest' to build index."

## Index

ingest: build ## Build full index from content/
	$(BINARY) ingest -content $(CONTENT) -out $(INDEX_DIR)

rebuild: ingest ## Alias for ingest (full rebuild)

## Query

query: ## Semantic search (usage: make query Q="your query")
	@test -n "$(Q)" || (echo "Usage: make query Q=\"your query\"" && exit 1)
	$(BINARY) query -index $(INDEX_DIR) $(Q)

status: ## Show index stats
	$(BINARY) status -index $(INDEX_DIR)

## Verify

verify: status ## Verify index works with a test query
	@echo ""
	@echo "=== Test query: RAG storage ==="
	$(BINARY) query -index $(INDEX_DIR) "RAG storage 選型"

## Benchmark

bench: ## Run four-backend benchmark (requires index)
	@test -d $(INDEX_DIR) || (echo "ERROR: No index. Run 'make ingest' first." && exit 1)
	cd ../.. && uv run --with sqlite-vec --with faiss-cpu --with numpy \
		scripts/blogsearch-bench/bench.py --index .blogsearch

## Cleanup

clean: ## Remove index files
	rm -rf $(INDEX_DIR)
	@echo "Index removed. Run 'make ingest' to rebuild."

## Help

help: ## Show this help
	@grep -E '^[a-z][a-z-]+:.*##' $(MAKEFILE_LIST) | \
		awk -F ':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'
