#!/usr/bin/env python3
"""
Minimal RAG query: load index.pkl, embed query, retrieve top-K,
build augmented prompt, call Ollama chat completion.

Usage:
    python3 query.py "你的問題"
    python3 query.py --top-k 5 --model gemma3:1b "問題"
"""
import argparse
import json
import math
import pickle
import sys
import urllib.request
from pathlib import Path

EMBED_URL = "http://localhost:11434/api/embeddings"
CHAT_URL = "http://localhost:11434/v1/chat/completions"
EMBED_MODEL = "nomic-embed-text"


def embed(text: str) -> list[float]:
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        EMBED_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["embedding"]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def retrieve(records: list[dict], query_vec: list[float], top_k: int) -> list[tuple[float, dict]]:
    scored = [(cosine(query_vec, r["embedding"]), r) for r in records]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def build_prompt(question: str, retrieved: list[tuple[float, dict]]) -> list[dict]:
    context_blocks = []
    for score, r in retrieved:
        context_blocks.append(
            f"[來源：{r['source']}#chunk{r['chunk_index']} 相似度：{score:.3f}]\n{r['text']}"
        )
    system = (
        "你是一個技術文件問答助手。"
        "依下方 context 內容回答問題、不要編造 context 外的事實。"
        "若 context 不足以回答、明確說『資料不足』。"
        "回答末尾列出引用的來源 path。"
    )
    user = "## Context\n\n" + "\n\n---\n\n".join(context_blocks) + f"\n\n## Question\n\n{question}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def chat(messages: list[dict], model: str) -> str:
    payload = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = urllib.request.Request(
        CHAT_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", help="natural language question")
    ap.add_argument("--index", default="scripts/rag-demo/index.pkl", type=Path)
    ap.add_argument("--top-k", default=4, type=int)
    ap.add_argument("--model", default="gemma3:1b")
    ap.add_argument("--show-retrieved", action="store_true")
    args = ap.parse_args()

    with args.index.open("rb") as f:
        records = pickle.load(f)
    print(f"Loaded {len(records)} chunks from {args.index}", file=sys.stderr)

    q_vec = embed(args.question)
    retrieved = retrieve(records, q_vec, args.top_k)

    if args.show_retrieved:
        print("\n=== Retrieved chunks ===", file=sys.stderr)
        for score, r in retrieved:
            print(f"  {score:.3f}  {r['source']}#chunk{r['chunk_index']}", file=sys.stderr)
        print("", file=sys.stderr)

    messages = build_prompt(args.question, retrieved)
    answer = chat(messages, args.model)
    print(answer)


if __name__ == "__main__":
    main()
