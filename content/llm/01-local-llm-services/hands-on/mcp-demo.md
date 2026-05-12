---
title: "Hands-on：用 blog content 寫一個最小 MCP server"
date: 2026-05-12
description: "stdio JSON-RPC、stdlib-only Python、暴露 blog content 給 LLM 用、validating 4.3 應用層協議"
tags: ["llm", "hands-on", "mcp", "rag"]
weight: 5
---

本篇把 [4.3 應用層協議](/llm/04-applications/application-protocols/) 的 MCP 概念落到一個可跑的最小實作：用 stdio JSON-RPC 暴露兩個 tool（`search_blog`、`read_chunk`）、客戶端 spawn server 跟它對話、驗證 protocol initialize / tools/list / tools/call / error 四個基本流程。實作刻意只用 Python stdlib、不依賴 MCP SDK、為的是把 wire protocol 看清楚、跟 4.3 的「server 協議層」framing 對應。

> **驗證日期**：2026-05-12
> **環境**：Python 3.11+、stdlib only（json / subprocess / urllib）
> **依賴**：RAG demo 的 `index.pkl`（[見 RAG demo](/llm/01-local-llm-services/hands-on/rag-demo/)）
> **協議版本**：MCP `2025-03-26`

## MCP 是什麼層的東西

回顧 [4.3 應用層協議](/llm/04-applications/application-protocols/) 的層級劃分：

- **Function calling**：模型訓練建立的能力（模型層）。
- **Structured output**：sampling 階段約束（推論層）。
- **MCP**：LLM application ↔ 外部 tool server 的協議（架構層）。

MCP 不管「模型怎麼呼叫工具」、它管「工具怎麼被暴露給 application」。本 demo 寫的是 server 端：server 不知道是哪個 LLM 在用它、不假設客戶端用 function calling 還是 structured output、它只專注「把 tool 透過 JSON-RPC 暴露出去」。

這跟 [OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/) 的設計哲學一致：定義最小可用標準、讓生態繞著標準長。

## 前置設定

| 項目                        | 來源                                                                       |
| --------------------------- | -------------------------------------------------------------------------- |
| Ollama + `nomic-embed-text` | [Ollama 安裝](/llm/01-local-llm-services/hands-on/ollama-setup/)           |
| RAG index（`index.pkl`）    | [RAG demo](/llm/01-local-llm-services/hands-on/rag-demo/) 跑過 `ingest.py` |
| Python                      | 3.11+                                                                      |

不需要安裝 MCP SDK——本 demo 手寫 JSON-RPC 處理、為了 inspection 透明度。Production server 建議改用 [官方 SDK](https://github.com/modelcontextprotocol)（Python / TypeScript 都有）、處理 framing、capability negotiation、transport edge cases。

## MCP 協議的最小子集

MCP server 要 handle 的核心 method：

| Method                      | 角色                                                      |
| --------------------------- | --------------------------------------------------------- |
| `initialize`                | Client 跟 server 握手、交換 protocol version + capability |
| `notifications/initialized` | Client 通知 handshake 完成（notification、無 response）   |
| `tools/list`                | Client 問 server 有哪些 tool                              |
| `tools/call`                | Client 呼叫某 tool、傳 arguments                          |

四個 method 之外、還可以暴露 resources / prompts / sampling、本 demo 只做 tools。

## Server 實作

完整檔案：`scripts/mcp-demo/blog_mcp_server.py`、約 150 行。

### 主迴圈：讀 stdin、分派 method、寫 stdout

```python
def main():
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
            continue  # notification, no response expected
        try:
            result = handler(params)
            respond(rid, result=result)
        except Exception as e:
            log(f"  ✗ handler error: {e}")
            respond(rid, error={"code": -32000, "message": str(e)})
```

**每段做什麼**：

1. **`log(...)` 開機訊息**：印到 stderr（不是 stdout）、讓人類能看到 server 啟動了、什麼 tools 可用。stdout 完全保留給 JSON-RPC 用。
2. **`for line in sys.stdin`**：MCP 的 stdio transport 是 line-delimited JSON—— 每個 message 一行、`\n` 結束。Python 的 file iteration 自動按行切。
3. **`line.strip()` + `if not line`**：空行 skip（不是 protocol error、只是 idle）。
4. **`json.loads(line)`** with `try / except`：parse 失敗（malformed input）不 crash、log error 繼續下一行。Protocol 訊息該是合法 JSON、parse error 表示 client 出錯。
5. **`msg.get("method")` / `msg.get("id")` / `msg.get("params", {})`**：JSON-RPC 2.0 標準三個欄位。`get` 而不是 `[]`、避免 KeyError；params 預設空 dict、後面 handler 可以安全 `.get("xxx")`。
6. **`if method not in HANDLERS: respond(rid, error={"code": -32601, ...})`**：未知 method 回標準 JSON-RPC error `-32601`（Method not found）。Client 知道這個 method 不能用、但 server 不死。
7. **`if handler is None: continue`**：notification（如 `notifications/initialized`）對應的 handler 是 `None`、不該回 response。
8. **`try: result = handler(params); respond(rid, result=result)`**：呼叫 handler、把結果回給 client。
9. **`except Exception as e: ... respond(rid, error={"code": -32000, ...})`**：handler 內部錯誤回 `-32000`（generic server error）。確保 server 任何時候都不 crash、即使工具 bug 也讓 client 拿到 error response。

**為什麼這樣設計**：

- **為什麼用 line-delimited JSON、不是 length-prefixed**：MCP spec 規定 stdio transport 是 newline-delimited。length-prefixed 是 LSP 的做法、解析複雜（要先讀 Content-Length header 再讀 N bytes）；newline-delimited 用 `for line in sys.stdin` 一行解決。
- **為什麼 stderr 不能寫 stdout**：stdio transport 的 invariant——stdout 是 protocol channel、只能寫 JSON-RPC message。任何 stray print() / debug output 進 stdout、會被 client parse JSON 時炸（「multiple JSON values on one line」或 invalid JSON）。所有 log / debug / progress message 必須走 stderr。寫錯這條 server 看起來不工作、debug 很久才找到。
- **為什麼 dispatch 用 dict-of-handlers 而不是 if/elif chain**：擴充性。加新 method 只要往 `HANDLERS` dict 加一項、不用改 main loop。也讓 dispatch logic 跟 method 實作分離、容易測試。
- **為什麼每個 handler 都用 try/except 包**：「single point of failure」設計——任何 handler 例外不影響其他 method。Server 應該是 long-running daemon、不能因為一個 tool bug 死掉。
- **為什麼 errors 用 JSON-RPC error code 而不是 HTTP-style status**：JSON-RPC 2.0 標準。`-32700` parse error、`-32600` invalid request、`-32601` method not found、`-32602` invalid params、`-32603` internal error、`-32000` to `-32099` 留給應用層自訂。

### 工具：search_blog

```python
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
```

**每段做什麼**：

1. **`records = load_index()`**：lazy load `index.pkl`、第一次 call 載入記憶體、後續直接用 cached。Server 啟動時 lazy load 而不是 import 時 load、讓 server 即使在 Ollama 還沒起 / index 不存在時也能 boot（之後 call 才會報 error）。
2. **`q_vec = embed(query)`**：把 query 轉成 768 維向量、呼叫 Ollama embedding API、跟 RAG demo 的 `embed` 是同一個 function。
3. **`sorted((...) for r in records, key=lambda x: x[0], reverse=True)[:top_k]`**：generator expression + sorted 一次完成「算分 → 排序 → 取 top-K」。
4. **`results = [{...} for score, r in scored]`**：把 top-K 整理成 client 友善的 dict 結構、含 source、chunk_index、score、preview（前 160 字 + 省略號）。
5. **`{"content": [{"type": "text", "text": json.dumps(...)}]}`**：MCP `tools/call` 標準 response 格式——`content` 是 array、每個元素 type + payload。`type: "text"` 是文字 content、`text` 是實際內容（這裡是 JSON 字串、讓 LLM 可以 parse）。

**為什麼這樣設計**：

- **為什麼 generator expression 而非 list comprehension**：`(... for r in records)` 是 generator、`sorted` 直接消費、不會在記憶體中建中間 list。對 463 records 影響不大、但展現 memory-efficient pattern。
- **為什麼 preview 切到 160 字**：兩件事的平衡——讓 LLM 看到的 search result 短（不淹沒 LLM 的 context）、但夠判讀（160 中文字約 80 token、能看出 chunk 是不是相關）。如果 LLM 要完整內容、再 call `read_chunk`。
- **為什麼回傳 JSON 字串、不是 nested object**：MCP `content` 規定每個 element 是 `{type, payload}`、`type: "text"` 的 `text` 必須是 string、不能直接放 nested object。要傳結構化資料、就把它 `json.dumps` 成字串。LLM 看到後可以自己 parse。
- **為什麼 `ensure_ascii=False`**：預設 `json.dumps` 把非 ASCII 字元（如中文）轉成 `\uXXXX`、難讀。`ensure_ascii=False` 直接輸出 UTF-8、LLM 也能直接讀懂、節省 token 數（一個中文字 1 token vs 6 token 的 `中`）。
- **為什麼 `round(score, 4)`**：score 是 float、原始可能是 `0.7497284598827362`、長且無意義。`round(score, 4)` 保留 4 位小數、`0.7497`、夠精確、wire size 短。

### 工具：read_chunk

```python
def tool_read_chunk(source: str, chunk_index: int) -> dict:
    records = load_index()
    for r in records:
        if r["source"] == source and r["chunk_index"] == chunk_index:
            return {"content": [{"type": "text", "text": r["text"]}]}
    return {
        "content": [{"type": "text", "text": f"Not found: {source}#chunk{chunk_index}"}],
        "isError": True,
    }
```

**每段做什麼**：

1. **`for r in records: if r["source"] == source and r["chunk_index"] == chunk_index: return ...`**：linear scan 找匹配的 record、找到回完整 text。
2. **找不到時 `return {... "isError": True}`**：MCP 標準的「tool 內部失敗」訊號。`isError: True` 告訴 client「這個 tool call 失敗了」、`content` 內是 human-readable error message。

**為什麼這樣設計**：

- **為什麼 linear scan 而不是 dict lookup**：可以改用 `{(source, chunk_index): record}` dict 變 O(1)。但 463 records 的 linear scan 是 < 1ms、optimize 不值得。Production 跟 vector DB 整合時、retrieval 系統自帶 indexing。
- **為什麼 `isError: True` 而不是 JSON-RPC error**：分兩種錯誤：
    - **Protocol error**：method 不存在、params 不合法、JSON parse 失敗——回 JSON-RPC `error` 物件。
    - **Tool semantic error**：method OK、params OK、但 tool 邏輯上不能 complete（找不到資料、外部 service down）——回 normal response 加 `isError: True`。
    MCP 設計這層分離、讓 client / LLM 區分「我做錯了」（協議層）跟「資料不存在」（語意層）。Production 設計工具時要仔細區分。

### Tool 描述用 JSON Schema

```python
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
```

**每個 field 角色**：

1. **`description`**：給 LLM 看的、解釋這個 tool 解什麼問題。LLM 看 description 決定何時 call。**這是模型 follow tool 的最主要訊號**——寫得清晰具體、模型用得對。
2. **`inputSchema`**：JSON Schema、描述 tool 接受的參數結構。LLM application 用這個 schema 約束 LLM 生成「合法的呼叫」。
3. **`properties`**：每個參數的型別 + 約束。
4. **`required`**：必填參數清單。LLM 漏掉時、client 端可以 reject、不會浪費 round-trip。
5. **`default`**：可選參數的預設值。傳的時候不給、tool 就用 default。
6. **`minimum` / `maximum`**：數值約束。`top_k` 設 1-20 是因為 < 1 沒意義、> 20 浪費 retrieval。
7. **`fn`**：實際 dispatch 用的 callable。本 demo 用 lambda 把 `args` dict 轉成 positional / keyword call。

**為什麼這樣設計**：

- **為什麼 description 要具體**：LLM 看 description 決定 call 時機。「search the blog」對 LLM 來說太模糊（搜什麼？找什麼？）、改成「Semantic search over blog content. Returns top-K relevant chunks with source paths.」明確描述輸入跟輸出形狀、LLM 能判讀「使用者問技術問題時該 call 這個」。
- **為什麼 schema 用 JSON Schema、不是自訂格式**：JSON Schema 是 web 標準、所有 LLM application 都認識、跨 framework 可移植。也是 [function calling](/llm/knowledge-cards/function-calling/) 跟 [Tool use 原理](/llm/04-applications/tool-use-principles/) 的 schema 描述語言。
- **為什麼 `required` 跟 `default` 兩個機制**：對 LLM 看的 prompt 越清楚越好。`required` 告訴 LLM「不傳這個會錯」、`default` 告訴 LLM「可不傳、預設值是 X」。沒分清的話、LLM 可能總是傳所有參數、雜訊多。
- **為什麼 `fn` 用 lambda 包**：實際 tool function 是 positional args、但 client 送的是 dict。lambda 把 dict 拆成 function call 的 args。也方便將來如果 tool function signature 變、只要改 lambda 不用改 dispatcher。

## Client 實作（測試用）

完整檔案：`scripts/mcp-demo/test_client.py`。實際 production 用 Claude Desktop / Cursor 等 MCP-capable application。本 demo 寫一個 stdio client、模擬 application 行為：

```python
proc = subprocess.Popen(
    [sys.executable, str(SERVER)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
)

def send(method, params=None, rid=None):
    msg = {"jsonrpc": "2.0", "method": method}
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
```

**每個參數做什麼**：

1. **`subprocess.Popen([sys.executable, str(SERVER)], ...)`**：spawn server 當 child process。用 `sys.executable` 確保用同一個 Python interpreter（避免 venv 跟系統 Python 混用）。
2. **`stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE`**：三條 pipe 都接到 client、讓我們能讀寫 server 的 stdio。
3. **`text=True`**：自動處理 str ↔ bytes 編碼、直接讀寫字串、不用手動 encode/decode。預設是 binary mode。
4. **`bufsize=1`**：line buffering、每寫一行就 flush。沒這個的話、Python 預設 block buffering（4KB 才 flush）、client 寫的 message server 看不到、整個卡住。
5. **`proc.stdin.write(json.dumps(msg) + "\n")`**：寫 JSON 訊息、結尾加 `\n`（line-delimited）。
6. **`proc.stdin.flush()`**：強制立刻送出。即使有 `bufsize=1`、明確 flush 是好習慣、避免任何 buffer 累積。
7. **`if rid is None: return None`**：notification 不該等 response。
8. **`line = proc.stdout.readline()` + `json.loads(line)`**：讀一行 response、parse。

**為什麼這樣設計**：

- **為什麼 stdio 而不是 socket / HTTP**：MCP stdio transport 的主要場景是「application spawn server」(Claude Desktop 開 Python 進程當 MCP server)。Stdio 自然形成 1-to-1 ownership、不需要 port allocation、不需要 auth。HTTP transport 也存在、用在 multi-client 場景。
- **為什麼 `bufsize=1` 這麼關鍵**：Python 預設 stdio buffer 4KB。如果 server / client 任一邊寫了 short message 但沒 fill 4KB、message 不會被另一邊看到、protocol 卡死。看起來是 hang、debug 困難。`bufsize=1` 強制 line buffering、解決這個 deadlock。
- **為什麼 `text=True`**：JSON-RPC 都是文字、binary mode 要手動 `.encode()` / `.decode()`、增加複雜度。`text=True` 自動處理 UTF-8。

## 跑通整條流程

```bash
cd ~/Projects/blog
python3 scripts/mcp-demo/test_client.py
```

- `cd ~/Projects/blog`：切到 repo 根、讓 SERVER 路徑相對解析正確。
- `python3 scripts/mcp-demo/test_client.py`：跑 test client、它會 spawn server 跟它對話。

預期看到五個階段：

### 1. initialize（握手）

```json
=== 1. initialize ===
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-03-26",
    "capabilities": {"tools": {}},
    "serverInfo": {"name": "blog-mcp-demo", "version": "0.1.0"}
  }
}
```

**Protocol 意義**：

- `protocolVersion`：server 支援的 MCP 版本。Client 要 negotiate（自己 cap 較新時要 downgrade）。
- `capabilities.tools: {}`：server 宣告「我支援 tools 功能」、空 object 表示沒額外 sub-feature。Client 拿到後知道可以 call `tools/list`。
- `serverInfo`：server 識別資訊、給 client 顯示用（debug、logging）。
- `id: 1`：對應 client 送的 request id、讓 client 知道這個 response 是哪個 request 的。

### 2. tools/list

Server 回兩個 tool 的完整 schema：

```json
{
  "tools": [
    {
      "name": "search_blog",
      "description": "Semantic search over blog content...",
      "inputSchema": {...JSON Schema...}
    },
    {
      "name": "read_chunk",
      "description": "Read the full text of a specific chunk...",
      "inputSchema": {...}
    }
  ]
}
```

**Protocol 意義**：這個輸出就是 LLM application 會塞給 LLM 的 tool 描述。LLM application 把這份 schema 用 [function calling](/llm/knowledge-cards/function-calling/) 機制給模型看、模型決定何時呼叫、傳什麼參數。Server 跟模型之間靠這層 schema 對齊、模型不直接呼叫 server、是經 application 中介。

### 3. tools/call: search_blog

Client 送：

```json
{
  "method": "tools/call",
  "params": {
    "name": "search_blog",
    "arguments": {"query": "什麼是 KV cache？", "top_k": 3}
  },
  "id": 3
}
```

`params` 包兩件事：

- `name`：要 call 的 tool 名（matches `tools/list` 內某個 tool）。
- `arguments`：實際傳給 tool 的 dict、結構符合該 tool 的 `inputSchema`。

Server 回 cosine 搜尋結果（preview）：

```json
[
  {"source": "llm/00-foundations/hardware-memory-budget.md", "chunk_index": 5, "score": 0.7497, "preview": "| Context 長度 | KV cache 估算..."},
  {"source": "llm/00-foundations/why-llm-feels-slow.md", "chunk_index": 4, "score": 0.7212, "preview": "..."},
  {"source": "llm/03-theoretical-foundations/attention-mechanism.md", "chunk_index": 7, "score": 0.7176, "preview": "..."}
]
```

實測命中合理——KV cache 相關段落都被找到。

### 4. tools/call: read_chunk

Client 用 search 拿到的 source + chunk_index、call `read_chunk` 拿完整內容：

```json
{
  "method": "tools/call",
  "params": {
    "name": "read_chunk",
    "arguments": {
      "source": "llm/00-foundations/hardware-memory-budget.md",
      "chunk_index": 5
    }
  }
}
```

Server 回該 chunk 的完整 markdown 文字。這實現了「search → read」的兩段流程——避免 search 一次就把所有 chunk 完整內容塞給 LLM（context 暴炸）、讓 LLM 自己看 preview 決定要 deep dive 哪個。

### 5. 錯誤路徑

```json
=== 5. unknown method (error path) ===
{"jsonrpc": "2.0", "id": 5, "error": {"code": -32601, "message": "Method not found: does/not/exist"}}
```

`-32601` 是 JSON-RPC 標準 error code for unknown method。Server 對未知 method 回標準 error、不 crash。Client 知道這個 method 不能用、繼續其他操作。

## 跟 Claude Desktop / Cursor 整合

把這個 server 接到實際 MCP-capable application：

### Claude Desktop

編輯 `~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "blog-search": {
      "command": "/path/to/python3",
      "args": ["<absolute-path-to-blog>/scripts/mcp-demo/blog_mcp_server.py"]
    }
  }
}
```

**每個 field 做什麼**：

- `mcpServers`：MCP server 註冊表、key 是任意名稱（client 識別用）。
- `command`：spawn 用的 executable path。要寫絕對路徑、Claude Desktop 啟動時的 PATH 可能不含 `python3`。
- `args`：傳給 command 的 args list。第一個是 script path。

**為什麼這樣設計**：Claude Desktop 啟動時讀這個 config、對每個 server 用 `subprocess.spawn(command, args)` 起 child process、用 stdio 跟它對話。跟本 demo 的 `test_client.py` 做的事完全一樣、只是改成 GUI application 而已。

重啟 Claude Desktop 後、在對話框問「用 search_blog 找 KV cache 相關段落」、Claude 會自動 call tool 並用結果回答。

### Cursor

`.cursor/mcp.json`（per-project）或全域設定類似結構。具體欄位看當下版本文件。

兩種整合的共通點：**MCP server 自己不變**、只要 application 端配置 path 跟 args、整合就完成。這正是 4.3 章節 N×M → N+M 的具體展現——本 server 不為任何特定 application 客製化、就能被多個 application 接到。

## 觀察跟原理對應

回到 [4.3 應用層協議](/llm/04-applications/application-protocols/) 的三層 framing：

| 層級          | 本 demo 是否實作 | 怎麼實作                                      |
| ------------- | ---------------- | --------------------------------------------- |
| 模型能力      | 不在本 demo 範圍 | LLM application 自己決定用 GPT/Claude/Gemma   |
| Sampling 約束 | 不在本 demo 範圍 | application + 推論伺服器配合                  |
| Server 協議   | **本 demo 焦點** | JSON-RPC over stdio + tools/list / tools/call |

這個分離正是 MCP 的核心收益：server 寫好之後、用什麼 LLM 跟它互動跟 server 無關。換掉 LLM、換掉 application、server code 完全不動。

## 何時這份 demo 會過時

- **MCP protocol version**：目前用 `2025-03-26`、未來會更新、但「server 暴露 tool 給 application」的 framing 不變。
- **JSON-RPC 細節**：可能 transport 形式增加（HTTP / WebSocket）、stdio 不會消失。
- **Tool 描述格式**：JSON Schema 是 web 通用標準、不會被換掉。

實作換代時、可以把手寫 JSON-RPC 換成官方 SDK、tool 內部邏輯（embedding / cosine / pickle）依需求換、但 protocol 骨架（initialize / tools/list / tools/call）會保留。

## 跑這個 demo 的指令總結

```bash
# 前置：確認 Ollama 跑著、index.pkl 存在
ollama list | grep nomic-embed-text
ls scripts/rag-demo/index.pkl
```

- `ollama list`：列已下載 model、`grep` 過濾出 embedding model。沒看到表示要先 `ollama pull nomic-embed-text`。
- `ls scripts/rag-demo/index.pkl`：確認 RAG ingest 跑過、index 存在。沒看到要先跑 `python3 scripts/rag-demo/ingest.py`。

```bash
# 自動測試 MCP server
python3 scripts/mcp-demo/test_client.py
```

- 跑 test_client、spawn server、依序送 5 個 request 驗證 protocol。stdout 印 protocol 對話、stderr 印 server log。看到全部 5 階段 OK 就成功。

```bash
# 手動跟 server 互動（看 protocol 原始 wire format）
python3 scripts/mcp-demo/blog_mcp_server.py
# 然後手打：{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
```

- 直接 invoke server、它讀 stdin 等 request。手打 JSON-RPC 訊息、看 server 回。是學 protocol 最直接的方式——你會看到 wire format 真實長相、跟自動 client 包裝後不一樣。

完整 source 在 `scripts/mcp-demo/`、約 250 行 Python、stdlib only。

跟其他 hands-on 章節的關係：完整 hands-on 系列見 [Hands-on 章節索引](/llm/01-local-llm-services/hands-on/)、本 demo 依賴的索引由 [RAG demo](/llm/01-local-llm-services/hands-on/rag-demo/) ingest 產生、MCP + RAG 同跑的記憶體 / 程序預算見 [RAG + MCP resource footprint](/llm/01-local-llm-services/hands-on/rag-mcp-resources/)、術語見 [MCP](/llm/knowledge-cards/mcp/)。
