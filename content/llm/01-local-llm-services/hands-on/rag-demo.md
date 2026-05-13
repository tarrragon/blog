---
title: "Hands-on：用 blog content 當 corpus 跑 RAG"
date: 2026-05-12
description: "200 行 Python：embedding + cosine retrieval + Ollama chat、validating 4.0 RAG 原理"
tags: ["llm", "hands-on", "rag", "ollama", "embedding"]
weight: 4
---

本篇把 [4.1 RAG 原理](/llm/04-applications/rag-principles/) 的概念落到一個能跑的最小實作：用本 blog 的 `content/llm/` 當 corpus、Ollama 的 `nomic-embed-text` 做 embedding、`gemma3:1b` 做生成、兩個 Python 檔案完成 ingest + query 整條鏈。實作刻意保持 minimal、為的是把每一段都看清楚、跟原理對應。

> **驗證日期**：2026-05-12
> **環境**：macOS、Ollama 0.23.2、`nomic-embed-text`、`gemma3:1b`
> **Corpus**：本 blog 的 `content/llm/`、71 個 markdown 檔
> **結果**：22 秒索引 463 個 chunk、retrieval 命中率好、generation 受 1B 模型能力限制——剛好示範「retrieval 跟 generation 各自會失敗」的兩段式失敗模式

## 前置設定

| 項目           | 來源 / 指令                                                                                        |
| -------------- | -------------------------------------------------------------------------------------------------- |
| Ollama 跑著    | 見 [Ollama 安裝](/llm/01-local-llm-services/hands-on/ollama-setup/)                                |
| Embedding 模型 | `ollama pull nomic-embed-text`（274 MB、768 維）                                                   |
| Chat 模型      | `ollama pull gemma3:1b`（815 MB）。能力弱但夠驗證流程；上 31B 級才能拿到「真正能用」的 answer 品質 |
| Python         | 3.11+（標準 lib `urllib` / `pickle` 即可、不需要外部依賴）                                         |

### 驗證 embedding API 可用

```bash
curl -s http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"hello world"}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('dim:', len(r['embedding']))"
```

逐項說明：

- `curl -s`：`-s` 是 silent 模式、不顯示下載進度條（不然會混進 stdout、後面 python parse 會炸）。
- `http://localhost:11434/api/embeddings`：用 Ollama **原生** embedding endpoint。也有 `/v1/embeddings`（OpenAI 相容）、但原生回應結構較簡（直接 `{"embedding": [...]}`、不是 OpenAI 那種 `{"data": [{"embedding": [...]}]}` 巢狀）。本 demo 用原生、parse 更直接。
- `-d '{"model":"...","prompt":"..."}'`：JSON payload。`model` 是 Ollama tag、`prompt` 是要 embed 的文字。
- `python3 -c "..."`：stdin 接 curl 輸出、parse JSON、印 embedding 長度。
- **為什麼測 `dim: 768`**：`nomic-embed-text` 模型架構決定 embedding 維度是 768。每次 embed 任何文字都會回固定 768 維向量、是 retrieval 的基本資料形狀。看到 `dim: 768` 表示：API 通了、模型載入了、輸出形狀對。

## 設計取捨

實作前先對齊 [4.1 RAG 原理](/llm/04-applications/rag-principles/) 提的設計取捨、決定每段怎麼做：

| 取捨點         | 本 demo 的選擇                        | Trade-off                                                        |
| -------------- | ------------------------------------- | ---------------------------------------------------------------- |
| Chunking 粒度  | 段落感知 + 軟 token cap（~400 token） | 簡單、保留段落邊界；不做語意 chunking                            |
| Embedding 模型 | `nomic-embed-text`（768 維）          | 主流、Ollama 內建、英文為主；中文混合場景仍可運作                |
| 向量儲存       | Python pickle 檔                      | 463 chunks 用 in-memory 完全夠；production 換 vector DB          |
| Retrieval      | Cosine similarity、top-K              | 無 hybrid、無 re-ranker；夠驗證、品質受 embedding 限制           |
| Generation     | `gemma3:1b` 純 Ollama OpenAI 相容 API | 1B 模型能力弱、會編造；用來示範 retrieval 跟 generation 兩段分離 |

這些選擇都對應到 4.0 章節的「會變的部分」清單——可預期半年後 embedding 模型有新選擇、chunking 有更好策略、re-ranker 變主流。但骨架（retrieval + augmentation 兩段式）不變。

## Ingest：把 corpus 變索引

完整檔案：`scripts/rag-demo/ingest.py`（本 repo 下）。三段 function：切 chunk、embed、走訪 + 持久化。

### 1. `slice_markdown`：段落感知的 chunk 切割

```python
def slice_markdown(text: str, soft_token_cap: int = 400) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    buf, buf_len = [], 0
    for p in paragraphs:
        plen = len(p) / 2  # char-count / 2 ≈ token (CJK + English heuristic)
        if buf and buf_len + plen > soft_token_cap:
            chunks.append("\n\n".join(buf))
            buf, buf_len = [], 0
        buf.append(p)
        buf_len += plen
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks
```

**每段做什麼**：

1. **`re.split(r"\n\s*\n", text)`**：用「空白行」當分隔符切段落。`\n\s*\n` 比 `\n\n` 寬一點、允許中間有 whitespace（空白、tab）。Markdown 段落的標準分隔是空白行、這個 regex 捕捉所有段落邊界。
2. **`[p.strip() for ... if p.strip()]`**：每段去除前後空白、過濾掉純空段落。
3. **`buf, buf_len = [], 0`**：累積一個正在構建的 chunk。`buf` 是段落 list、`buf_len` 是該 chunk 的 token 累計估算。
4. **`plen = len(p) / 2`**：估算這段的 token 數。
5. **`if buf and buf_len + plen > soft_token_cap`**：「greedy pack」邏輯——如果加上這段就會超過 cap、把目前 buffer flush 成一個 chunk、再開新 buffer 裝這段。
6. **`if buf: chunks.append(...)`**：迴圈結束後、最後一個 buffer 還沒 flush、補上。

**為什麼這樣設計**：

- **為什麼 paragraph-aware、不是固定 token cap**：[4.1 RAG 原理](/llm/04-applications/rag-principles/) 提的 chunking 設計取捨——固定 token cap 容易切過句子或段落中間、語意被截斷。Paragraph-aware 切在自然邊界、保留段落內語意完整。
- **為什麼 `soft` token cap（軟限制）而不是硬切**：硬切會把一個 800-token 段落切成兩半；軟切讓「目前 chunk + 下一段超過 cap」時 flush 目前 chunk、下一段獨立成新 chunk（即使超過 cap 也保留段落完整）。代價：個別 chunk 可能超過 cap、retrieval 拿到的塊較大、但內容完整。
- **為什麼 `len(p) / 2` 估 token**：英文約 4 字元 / token、中文約 1.5 字元 / token、混合平均 / 2 在兩種場景都合理。要精確用 tokenizer（如 `tiktoken`）、但 demo 不需要——這個 heuristic 在 ±20% 內、夠用來做 chunking 決策。
- **為什麼 `\n\n`.join(buf)`**：flush 成 chunk 時、段落間保留空白行分隔、讀者看到 chunk 仍是合法 markdown 結構、不是平鋪文字。

### 2. `embed`：呼叫 Ollama embedding API

```python
def embed(text: str) -> list[float]:
    payload = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["embedding"]
```

**每行做什麼**：

1. **`payload = json.dumps(...).encode()`**：把 dict 轉成 JSON 字串、再 encode 成 bytes。HTTP body 必須是 bytes、不能直接傳 str。
2. **`urllib.request.Request(...)`**：建立 HTTP request 物件。沒寫 `method` 預設是 GET、但有 `data` 參數會自動變 POST。
3. **`headers={"Content-Type": "application/json"}`**：告訴 server payload 是 JSON。少了這個、Ollama 可能 parse 不出 body。
4. **`urlopen(req, timeout=60)`**：發送 request、`timeout=60` 是 socket-level timeout（連線 + 讀取總共最多 60 秒）。
5. **`json.loads(resp.read())["embedding"]`**：讀回應 body、parse JSON、取 `embedding` 欄位（768 維 list of float）。

**為什麼這樣設計**：

- **為什麼用 stdlib `urllib` 而不是 `requests`**：完全沒有外部 dependency、`urllib` 是 Python stdlib 內建。`requests` 較友善但要 `pip install`、本 demo 想 minimal。
- **為什麼 timeout=60**：embed 一段文字通常 < 200ms、60 秒夠 buffer 意外（首次 model 載入記憶體可能 5-10 秒）。設無限會在 Ollama 掛掉時整個 script hang。
- **為什麼 `/api/embeddings`、不是 `/v1/embeddings`**：兩者都可。原生 endpoint 回應結構平、parse 直接（`r["embedding"]`）；OpenAI 相容回應較巢狀（`r["data"][0]["embedding"]`）。對 demo、寫法簡單較重要。

### 3. 走訪 + 持久化

```python
md_files = sorted(args.content_root.rglob("*.md"))
records = []
for md in md_files:
    text = md.read_text(encoding="utf-8")
    text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)  # 去掉 frontmatter
    chunks = slice_markdown(text)
    for j, chunk in enumerate(chunks):
        vec = embed(chunk)
        records.append({
            "source": str(md.relative_to(args.content_root.parent)),
            "chunk_index": j,
            "text": chunk,
            "embedding": vec,
        })
with open("scripts/rag-demo/index.pkl", "wb") as f:
    pickle.dump(records, f)
```

**每段做什麼**：

1. **`args.content_root.rglob("*.md")`**：recursive glob、回 `Path` iterator、找出 `content_root` 下所有 `.md` 檔（含子目錄）。
2. **`sorted(...)`**：排序、讓每次 ingest 順序穩定（git diff 比較友善、retrieval 結果可重現）。
3. **`text.read_text(encoding="utf-8")`**：讀檔、明確指定 UTF-8（中文 markdown 必要、否則 macOS / Linux 預設可能不一致）。
4. **`re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)`**：去掉 Hugo frontmatter。
    - `^---\n`：開頭 `---\n`。
    - `.*?`：non-greedy match、配到下一個 `---` 就停。
    - `\n---\n`：closing fence。
    - `count=1`：只 strip 第一個（檔案中可能有其他 `---` 是水平分隔線、不要誤殺）。
    - `flags=re.DOTALL`：讓 `.` 也匹配換行符（預設 `.` 不匹配 `\n`、規 frontmatter 跨行就吃不到）。
5. **`records.append({...})`**：每個 chunk 一個 record、含 source path、chunk index、原文、embedding。
6. **`md.relative_to(args.content_root.parent)`**：把絕對 path 變成 `llm/00-foundations/xxx.md` 形式、retrieval 顯示時短、跨機器可移植。
7. **`pickle.dump(records, f)`**：把整個 records list 序列化到 binary 檔。

**為什麼這樣設計**：

- **為什麼要 strip frontmatter**：Frontmatter 是 `title`、`date`、`tags` 等 metadata、不是文章正文。embed 進去會稀釋向量語意（讓「date」「2026-05-11」等 keyword 影響相似度計算）。Strip 後 embedding 只 capture 內容語意。
- **為什麼 records 是 list of dict 而不是 numpy array**：兩個原因。(1) 每個 record 含 source / chunk_index / text / embedding 四種異質欄位、numpy 處理不直接。(2) 463 chunks 規模、純 Python list 跑 cosine 也只是毫秒級、不需要 vectorize。十萬 chunk 以上才考慮 numpy array + batched dot product。
- **為什麼 pickle 而不是 JSON**：embedding 是 768-float list、JSON 序列化會把每個 float 變成 ASCII 字串（每個 ~20 bytes）、檔案大很多、parse 也慢。Pickle 是 binary format、保留原本資料結構、檔案小、loader 快。代價：pickle 有 Python 版本相依、跨語言不能讀——但本 demo 索引只給自家 query.py / mcp_server.py 用、可接受。
- **為什麼存 `text` 跟 `embedding`、不只 embedding**：retrieval 要回 chunk 原文給 LLM 看、不能只有 source path（不然每次 query 還要再讀檔）。Pickle 多存原文成本低（~100 byte / chunk）、查詢時方便很多。

### 跑 ingest

```bash
cd ~/Projects/blog
python3 scripts/rag-demo/ingest.py
```

- `cd ~/Projects/blog`：切到 repo 根、讓相對路徑 `content/llm` 對得到 corpus、`scripts/rag-demo/index.pkl` 對得到 output 位置。
- `python3 scripts/rag-demo/ingest.py`：跑 ingest script、預設讀 `content/llm/`、寫 `scripts/rag-demo/index.pkl`。

實測輸出：

```text
Found 71 markdown files under content/llm
  [10/71] 86 chunks in 4.5s
  [20/71] 181 chunks in 8.6s
  ...
  [70/71] 461 chunks in 22.2s
Wrote 463 records to scripts/rag-demo/index.pkl (22.3s)
```

463 chunks、22 秒、平均 ~21 chunks/sec。瓶頸是 sequential API call、用 async / batch 能快 5-10 倍、但這個量級不值得。

## Query：retrieval + augmentation + generation

完整檔案：`scripts/rag-demo/query.py`。三段。

### 1. Cosine similarity + top-K retrieval

```python
def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

def retrieve(records, query_vec, top_k):
    scored = [(cosine(query_vec, r["embedding"]), r) for r in records]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]
```

**每行做什麼**：

1. **`dot = sum(x * y for x, y in zip(a, b))`**：兩個向量的內積（dot product）。`zip(a, b)` 把兩個 list 對位配對、generator expression 算每對相乘、sum 加起來。
2. **`na = math.sqrt(sum(x * x for x in a))`**：a 的 L2 norm（歐氏範數）—— `sqrt(x1² + x2² + ... + xn²)`。
3. **`nb = math.sqrt(sum(y * y for y in b))`**：b 的 L2 norm。
4. **`return dot / (na * nb) if na and nb else 0.0`**：cosine = dot / (||a|| × ||b||)。三元運算子防 zero division——若任一向量是零向量、na 或 nb 為 0、回 0.0 而不是 crash。
5. **`scored = [(cosine(query_vec, r["embedding"]), r) for r in records]`**：對每個 record 算相似度、組成 (score, record) tuple 的 list。
6. **`scored.sort(key=lambda x: x[0], reverse=True)`**：按 score 從大到小排序。`key=lambda x: x[0]` 取 tuple 第一個元素（score）當排序 key。
7. **`return scored[:top_k]`**：取前 K 個。

**為什麼這樣設計**：

- **為什麼 cosine 而不是純 dot product**：純 dot product 受向量長度影響——長向量自動拿高分、跟「相似度」無關。Cosine 把向量正規化到單位長度、純看方向、是「語意相似」的標準衡量。語意相似 embedding 應該方向相近、長度差異不重要。
- **為什麼用 `math.sqrt` 而不是 `**0.5`**：兩者數學等價、但 `math.sqrt` 用 C-level 實作、CPython 中比 Python 級 `**0.5` 快幾倍。對 463 chunks 影響不大、但 production scale 會放大差異——習慣寫 `math.sqrt` 的好。
- **為什麼 `if na and nb else 0.0`**：防禦性程式設計。理論上 embedding 不會是零向量（模型架構保證有非零權重）、但邊界情況（空輸入、API 出錯回 placeholder）可能出現、避免 ZeroDivisionError 整個 query 失敗。回 0.0 表示「無法判斷相似度」、retrieval 排序時自然排到最後。
- **為什麼 sort 全部、不用 heap**：463 records、Python sort 是 O(n log n)、毫秒級。`heapq.nlargest(top_k, ...)` 是 O(n log k)、在 k=4、n=463 上實測幾乎沒差。十萬 record 以上才看到顯著差別。
- **為什麼用 list of tuple、不用 numpy**：跟 ingest 同樣的理由——小規模不需要 vectorize、純 Python 清楚。

### 2. 建 augmented prompt

```python
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

messages = [
    {"role": "system", "content": system},
    {"role": "user", "content": user},
]
```

**每行做什麼**：

1. **`f"[來源：{...} 相似度：{score:.3f}]\n{r['text']}"`**：每個 retrieved chunk 加 header 標明出處跟相似度、再接原文。`:.3f` 是 score 格式化到三位小數。
2. **`"\n\n---\n\n".join(context_blocks)`**：用 `---` 水平分隔線分隔各 chunk、視覺上清楚。
3. **`{"role": "system", "content": system}`**：system message 給 LLM 設定角色 + 約束。
4. **`{"role": "user", "content": user}`**：user message 含 context 跟 question、是 LLM 實際讀的內容。

**為什麼這樣設計**：

- **為什麼 system prompt 約束四件事**（角色、忠於 context、資料不足時明說、引用來源）：
    - **角色**：「技術文件問答助手」框定模型行為、減少 off-topic 回應。
    - **忠於 context**：對抗 RAG 最常見的失敗模式——LLM 看到 context 但用自己訓練的 knowledge 補完、結果跟 corpus 不一致。明確要求 follow context 能降低（雖然不能完全消除、見實測 1）。
    - **資料不足時明說**：避免 LLM「硬要回答」造成 hallucination。對 weak model 這條 follow 度差、但對 large model 有效。
    - **引用來源**：traceability。讀者能回查 corpus、驗證模型答案。
- **為什麼 `## Context` / `## Question` 結構**：用 markdown heading 結構幫助 LLM 區分「我要讀什麼」「我要回答什麼」。比平鋪文字穩定（即使對小模型）。
- **為什麼把 retrieved chunks 全塞 user message、不分開**：MCP / function calling 的更現代做法是把 retrieved 結果做成 tool response、模型主動 call retrieval tool。本 demo 不引入 tool use、直接塞 prompt 較單純——能說明 RAG 核心（augmentation）不必牽扯 tool use。

### 3. 呼叫 chat completions

```python
def chat(messages, model):
    payload = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = urllib.request.Request(
        "http://localhost:11434/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]
```

**每行做什麼**：

1. **`json.dumps({"model": ..., "messages": ..., "stream": False}).encode()`**：構造 OpenAI 相容 chat completions request body。`stream: False` 讓 server 等生成完再一次回、不要 SSE 串流。
2. **`/v1/chat/completions`**：OpenAI 相容 endpoint、跟雲端 OpenAI 完全同樣 schema。
3. **`timeout=180`**：3 分鐘、給長 context + 慢模型空間。
4. **`["choices"][0]["message"]["content"]`**：parse OpenAI 標準 response 結構、取第一個 choice 的 content。

**為什麼這樣設計**：

- **為什麼 `stream: False`**：demo 要把完整 answer 印出、不需要 incremental display。`stream: True` 要寫 SSE parser、複雜。Production 互動式 UI 才需要 streaming。
- **為什麼 timeout=180、不是 60**：1B 模型 + 4 個 retrieved chunks 的 context、prefill 可能要 5-30 秒、生成 100-500 token 又要 5-20 秒、保守設 3 分鐘。embed function 用 60 是因為 embedding 是純 forward pass、單一 token 量級操作、不需要這麼長。
- **為什麼 `/v1/...` 而不是 `/api/...`**：chat completions 走 OpenAI 相容 endpoint、生態都用這個格式（Continue.dev、Cursor、各家 SDK）。embedding 用 `/api/...` 是因為原生 schema 簡單；chat 用 `/v1/...` 是因為 message-based 結構是 OpenAI 標準、跨工具互通。

## 實測結果：retrieval 對、generation 弱

### 測試 1：「什麼是 MTP？為什麼對寫 code 場景特別有效？」

```bash
python3 scripts/rag-demo/query.py --show-retrieved "什麼是 MTP？為什麼對寫 code 場景特別有效？"
```

`--show-retrieved` 是個 flag、開啟後在 stderr 印 retrieved chunks 跟 score、答案還是進 stdout。是 debug 跟教學用、不會影響 LLM 看到的 prompt。

Retrieval：

```text
0.870  llm/knowledge-cards/transformer.md#chunk2
0.825  llm/03-theoretical-foundations/sampling-and-decoding.md#chunk8
0.782  llm/knowledge-cards/ttft.md#chunk1
0.771  llm/knowledge-cards/mtp.md#chunk2
```

四個 chunk 都跟問題相關、相似度合理。MTP 卡確實被命中（雖然不是 top-1、是因為 transformer.md 該段提到 MTP）。

Generation（1B 模型）：

> MTP 僅指使用 Ollama 進行 Coding 模型訓練與部署、它是一種系統性的方式...
> 來源：[llm.dev](https://llm.dev/mti/)

**錯**：1B 模型編造了「MTP 僅指使用 Ollama」這個事實（不對、MTP 是 Google 為 Gemma 釋出的、跟 Ollama 沒直接關係）、來源 URL 也是 hallucination。

### 測試 2：「MCP 跟 function calling 有什麼差別？」

Retrieval：

```text
0.721  llm/04-applications/application-protocols.md#chunk2
0.704  llm/04-applications/application-protocols.md#chunk1
0.702  llm/04-applications/application-protocols.md#chunk0
0.693  llm/knowledge-cards/function-calling.md#chunk1
```

完美命中——4.3 應用層協議章節三個 chunk + function-calling 卡。

Generation：模型把幾段重複拼接、framing 跟原文有出入、但比測試 1 好（因為 context 涵蓋直接答案）。

## 觀察跟原理對應

這個 demo 剛好示範 [4.1 RAG 原理](/llm/04-applications/rag-principles/) 提的兩段式失敗模式：

| 階段       | 表現                                   | 原因                                                         |
| ---------- | -------------------------------------- | ------------------------------------------------------------ |
| Retrieval  | 命中率好、找到對的 chunks              | `nomic-embed-text` 對技術文件覆蓋好、cosine 對短 query 也 OK |
| Generation | 內容有時編造、不忠於 context、來源亂寫 | `gemma3:1b` 模型容量不足以可靠 follow system prompt          |

換 31B+ 模型 generation 會改善很多——這也是 4.0 章節提到「retrieval 跟下游 LLM 訓練分佈不一致」會放大失敗的具體例子。寫 RAG 系統時、generation 失敗不一定是「retrieval 沒給對 context」、可能是「模型不夠強」。

## 何時這份 demo 會過時

- **Ollama API 形狀**：短期內不會變（生態都依賴）。
- **`nomic-embed-text` / `gemma3:1b` 具體 tag**：預期會被新模型取代、但 retrieval + augmentation 結構不變。
- **Chunking heuristic**：簡單 char-count / 2 很粗、半年後若有便宜的 token counter 直接接會更準。
- **Pickle 儲存**：production 場景建議換 vector DB、本 demo 是教學用。

實作換代時、保留 ingest / retrieve / augment / generate 四段、各段內部換工具即可——這四段是 RAG 的骨架、跨工具世代不變。

## 跑這個 demo 的指令總結

```bash
# 一次性建索引（每次 corpus 變動才需要重建）
cd ~/Projects/blog
python3 scripts/rag-demo/ingest.py
```

- `cd`：切到 repo 根、relative path 對得到。
- `python3 ingest.py`：跑索引、預設讀 `content/llm/`、寫 `scripts/rag-demo/index.pkl`。每次 corpus 變動才需要重跑、不變的話 index 就一直用。

```bash
# 查詢（任意次）
python3 scripts/rag-demo/query.py --show-retrieved "你的問題"
python3 scripts/rag-demo/query.py --top-k 5 --model gemma3:1b "問題"
```

- `--show-retrieved`：教學 / debug 用、列 retrieved chunks 跟 score 到 stderr。
- `--top-k 5`：取 top 5 instead of 預設 4。chunks 越多 context 越長、TTFT 越久、但訊息越完整。
- `--model gemma3:1b`：指定 chat model。換 `gemma3:4b`、`gemma4:31b-coding-mtp-bf16` 等 generation 品質會大幅改善。

完整 source 在 `scripts/rag-demo/` 下、200 行 Python、無外部 dependency。

跟其他 hands-on 章節的關係：完整 hands-on 系列見 [Hands-on 章節索引](/llm/01-local-llm-services/hands-on/)、把 retrieval 包成 MCP server 暴露給 LLM application 見 [MCP demo](/llm/01-local-llm-services/hands-on/mcp-demo/)、RAG + MCP 同跑的記憶體 / 程序預算見 [RAG + MCP resource footprint](/llm/01-local-llm-services/hands-on/rag-mcp-resources/)、術語見 [RAG](/llm/knowledge-cards/rag/) 跟 [embedding model](/llm/knowledge-cards/embedding-model/)。
