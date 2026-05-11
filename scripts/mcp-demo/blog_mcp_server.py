#!/usr/bin/env python3
"""
Minimal MCP server exposing blog content as tools.

Speaks JSON-RPC 2.0 over stdio (the MCP transport). Implements just enough
of the MCP protocol to demonstrate the server side:

  - initialize          → declare server capabilities
  - tools/list          → describe available tools
  - tools/call          → execute a tool, return content

Tools exposed:
  - search_blog(query)  → cosine search over pre-built RAG index
  - read_chunk(source, chunk_index)  → return one chunk verbatim

This is intentionally dependency-free (stdlib only) to keep the demo
inspectable. Production MCP servers should use the official SDK
(@modelcontextprotocol/sdk or python-sdk) which handles JSON-RPC framing,
batching, capability negotiation, and transport edge cases.

Reference: MCP spec at modelcontextprotocol.io
"""
from __future__ import annotations

import json
import math
import pickle
import sys
import urllib.request
from pathlib import Path

INDEX_PATH = Path(__file__).parent.parent / "rag-demo" / "index.pkl"
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

PROTOCOL_VERSION = "2025-03-26"
SERVER_INFO = {"name": "blog-mcp-demo", "version": "0.1.0"}

# Load index lazily so the server can start before Ollama is reachable.
_records: list[dict] | None = None


def load_index() -> list[dict]:
    global _records
    if _records is None:
        with INDEX_PATH.open("rb") as f:
            _records = pickle.load(f)
    return _records


def embed(text: str) -> list[float]:
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        EMBED_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["embedding"]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# ---- Tool implementations ----

def tool_search_blog(query: str, top_k: int = 5) -> dict:
    records = load_index()
    q_vec = embed(query)
    scored = sorted(
        ((cosine(q_vec, r["embedding"]), r) for r in records),
        key=lambda x: x[0],
        reverse=True,
    )[:top_k]
    results = [
        {
            "source": r["source"],
            "chunk_index": r["chunk_index"],
            "score": round(score, 4),
            "preview": r["text"][:160] + ("..." if len(r["text"]) > 160 else ""),
        }
        for score, r in scored
    ]
    return {"content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False, indent=2)}]}


def tool_read_chunk(source: str, chunk_index: int) -> dict:
    records = load_index()
    for r in records:
        if r["source"] == source and r["chunk_index"] == chunk_index:
            return {"content": [{"type": "text", "text": r["text"]}]}
    return {
        "content": [{"type": "text", "text": f"Not found: {source}#chunk{chunk_index}"}],
        "isError": True,
    }


TOOLS = {
    "search_blog": {
        "description": "Semantic search over blog content. Returns top-K relevant chunks with source paths.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language query"},
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
        },
        "fn": lambda args: tool_search_blog(args["query"], args.get("top_k", 5)),
    },
    "read_chunk": {
        "description": "Read the full text of a specific chunk by source path and chunk index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Markdown file path relative to content/"},
                "chunk_index": {"type": "integer", "minimum": 0},
            },
            "required": ["source", "chunk_index"],
        },
        "fn": lambda args: tool_read_chunk(args["source"], args["chunk_index"]),
    },
}


# ---- JSON-RPC handlers ----

def handle_initialize(params: dict) -> dict:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": SERVER_INFO,
    }


def handle_tools_list(_params: dict) -> dict:
    return {
        "tools": [
            {
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            }
            for name, spec in TOOLS.items()
        ]
    }


def handle_tools_call(params: dict) -> dict:
    name = params.get("name")
    args = params.get("arguments", {})
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOLS[name]["fn"](args)


HANDLERS = {
    "initialize": handle_initialize,
    "notifications/initialized": None,  # notification, no response
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def respond(rid, result=None, error=None) -> None:
    msg = {"jsonrpc": "2.0", "id": rid}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def log(*args) -> None:
    """All diagnostics MUST go to stderr — stdout is reserved for JSON-RPC."""
    print(*args, file=sys.stderr, flush=True)


def main() -> None:
    log(f"[blog-mcp-demo] starting, index={INDEX_PATH}, tools={list(TOOLS.keys())}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            log(f"  parse error: {e}")
            continue
        method = msg.get("method")
        rid = msg.get("id")
        params = msg.get("params", {})
        log(f"  → {method} (id={rid})")
        if method not in HANDLERS:
            respond(rid, error={"code": -32601, "message": f"Method not found: {method}"})
            continue
        handler = HANDLERS[method]
        if handler is None:
            # notification, no response
            continue
        try:
            result = handler(params)
            respond(rid, result=result)
        except Exception as e:
            log(f"  ✗ handler error: {e}")
            respond(rid, error={"code": -32000, "message": str(e)})


if __name__ == "__main__":
    main()
