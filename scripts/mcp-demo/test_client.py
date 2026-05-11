#!/usr/bin/env python3
"""
Test client for blog_mcp_server.py.

Spawns the server as a child process, exchanges JSON-RPC messages over its
stdio pipes. Simulates the role a real MCP client (Claude Desktop, Cursor
with MCP support, etc.) would play.

Usage:
    python3 test_client.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).parent / "blog_mcp_server.py"


def main() -> None:
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    def send(method: str, params: dict | None = None, rid: int | None = None) -> dict | None:
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if rid is not None:
            msg["id"] = rid
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        if rid is None:
            return None  # notification
        line = proc.stdout.readline()
        return json.loads(line)

    print("=== 1. initialize ===")
    init = send(
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "0.1.0"},
        },
        rid=1,
    )
    print(json.dumps(init, ensure_ascii=False, indent=2))

    send("notifications/initialized")

    print("\n=== 2. tools/list ===")
    tools = send("tools/list", rid=2)
    print(json.dumps(tools, ensure_ascii=False, indent=2))

    print("\n=== 3. tools/call: search_blog ===")
    search = send(
        "tools/call",
        {
            "name": "search_blog",
            "arguments": {"query": "什麼是 KV cache？", "top_k": 3},
        },
        rid=3,
    )
    print(json.dumps(search, ensure_ascii=False, indent=2))

    print("\n=== 4. tools/call: read_chunk ===")
    result_text = search["result"]["content"][0]["text"]
    first_hit = json.loads(result_text)[0]
    read = send(
        "tools/call",
        {
            "name": "read_chunk",
            "arguments": {
                "source": first_hit["source"],
                "chunk_index": first_hit["chunk_index"],
            },
        },
        rid=4,
    )
    print(json.dumps(read, ensure_ascii=False, indent=2)[:600] + "\n  ... (truncated)")

    print("\n=== 5. unknown method (error path) ===")
    err = send("does/not/exist", rid=5)
    print(json.dumps(err, ensure_ascii=False, indent=2))

    proc.stdin.close()
    proc.wait(timeout=5)
    stderr = proc.stderr.read()
    print("\n=== Server stderr log ===")
    print(stderr)


if __name__ == "__main__":
    main()
