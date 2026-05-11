#!/usr/bin/env python3
"""
Minimal RAG ingest: walk content/, slice markdown into chunks,
call Ollama embedding API, persist (chunk, source, embedding) tuples to pickle.

Usage:
    python3 ingest.py [--content-root PATH] [--out PATH] [--chunk-tokens N]

Design notes:
- Embedding model: nomic-embed-text (768 dim) via local Ollama
- Chunk strategy: paragraph-aware split with a soft token cap.
  Real production should use markdown AST + heading-aware chunking;
  this is the minimal viable version to validate the pipeline.
- Storage: pickle. Replace with vector DB for real workloads.
"""
import argparse
import json
import pickle
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"


def slice_markdown(text: str, soft_token_cap: int = 400) -> list[str]:
    """Paragraph-aware splitter with soft cap.

    1. Split on blank lines to get paragraphs.
    2. Greedy-pack paragraphs into chunks until soft_token_cap (approx).
    3. Token estimate: 1 token ≈ 4 chars for English, ≈ 1.5 chars for CJK.
       Use char-count / 2 as a rough universal heuristic.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for p in paragraphs:
        plen = len(p) / 2  # rough token estimate
        if buf and buf_len + plen > soft_token_cap:
            chunks.append("\n\n".join(buf))
            buf, buf_len = [], 0
        buf.append(p)
        buf_len += plen
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def embed(text: str) -> list[float]:
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["embedding"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--content-root", default="content/llm", type=Path)
    ap.add_argument("--out", default="scripts/rag-demo/index.pkl", type=Path)
    ap.add_argument("--chunk-tokens", default=400, type=int)
    args = ap.parse_args()

    md_files = sorted(args.content_root.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files under {args.content_root}", file=sys.stderr)

    records: list[dict] = []
    total_chunks = 0
    start = time.time()
    for i, md in enumerate(md_files):
        text = md.read_text(encoding="utf-8")
        # Strip front-matter for cleaner embedding
        text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
        chunks = slice_markdown(text, args.chunk_tokens)
        for j, chunk in enumerate(chunks):
            try:
                vec = embed(chunk)
            except urllib.error.URLError as e:
                print(f"  embed failed for {md}#{j}: {e}", file=sys.stderr)
                continue
            records.append(
                {
                    "source": str(md.relative_to(args.content_root.parent)),
                    "chunk_index": j,
                    "text": chunk,
                    "embedding": vec,
                }
            )
            total_chunks += 1
        if (i + 1) % 10 == 0:
            print(
                f"  [{i + 1}/{len(md_files)}] {total_chunks} chunks "
                f"in {time.time() - start:.1f}s",
                file=sys.stderr,
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("wb") as f:
        pickle.dump(records, f)
    print(
        f"Wrote {len(records)} records to {args.out} "
        f"({time.time() - start:.1f}s)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
