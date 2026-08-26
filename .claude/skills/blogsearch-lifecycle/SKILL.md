---
name: blogsearch-lifecycle
description: "blogsearch 向量 index 的生命週期管理：偵測 index 過時或不存在、觸發 rebuild、驗證結果。適用於有 blogsearch 語意搜尋工具的專案。觸發詞：blogsearch、rebuild index、ingest、向量搜尋、語意搜尋、index 過時、content 變動、pull 後 rebuild、新增文章後搜尋。Trigger when content changes may have made the search index stale, or when semantic search is needed."
license: MIT
metadata:
  version: 1.4.1
  category: tooling-lifecycle
---

# Blogsearch Index 生命週期管理

管理 `blogsearch` 向量搜尋工具的 index rebuild 時機、流程與驗證。向量 index 是 derived artifact（不進 git），content 變動後需要 rebuild 才能反映最新內容。

## 前置條件

- `bin/blogsearch` 已 build（`cd scripts/blogsearch && go build -o ../../bin/blogsearch .`）
- Ollama 已安裝且跑著（`ollama serve`）
- `nomic-embed-text` 已 pull（`ollama pull nomic-embed-text`）

## 偵測觸發

以下情境代表 index 可能過時或不存在，需要評估 rebuild：

### 自動偵測（Claude Code 對話中判斷）

| 情境                       | 偵測方式                                      | 動作                                     |
| -------------------------- | --------------------------------------------- | ---------------------------------------- |
| Index 不存在               | `.blogsearch/` 目錄不存在                     | 提示 full rebuild                        |
| 寫完新文章                 | 對話中剛建立 `content/**/*.md`                | 提示 rebuild                             |
| git pull 拉到 content 變動 | `git diff --name-only HEAD@{1}` 含 `content/` | 提示 rebuild                             |
| 用戶要求語意搜尋           | 對話中提到搜尋相關內容                        | 先檢查 index 是否存在，不存在就提示      |
| 換 embedding model         | `embed.go` 的 Model 變數被修改                | 提示 full rebuild（舊 embedding 不相容） |

### 手動觸發

用戶在對話中說「rebuild index」「更新搜尋」「blogsearch ingest」時直接執行。

## 標準操作流程

所有指令都封裝在 `scripts/blogsearch/Makefile`。以下是對應的 make target：

### 1. 首次設定

```bash
cd scripts/blogsearch && make install    # build binary + pull embedding model
```

前提：Ollama 已在跑（`ollama serve &`）。`make install` 會檢查 Ollama 狀態、pull `nomic-embed-text`、build binary。

### 2. Full rebuild

```bash
cd scripts/blogsearch && make ingest     # 全量重建，耗時隨 content 規模線性成長
```

預期輸出：逐檔列出 chunk 數、最後顯示總 chunk 數與耗時。

**耗時要按當前規模估、不要記固定值。** 2026-08 實測 3510 個 md 檔產出 29863 chunks、耗時 3296 秒（約 55 分鐘）；早期版本的 skill 寫「約 4 分鐘」，那是 content 遠小於現在時的數字。開跑前先 `find content -name '*.md' | wc -l` 對照上次的檔數與秒數推估，免得用過時的預期把正常進度誤判成卡住。

**沒有增量模式。** `ingest` 只有全量一種，改一個檔跟改三千個檔付一樣的代價。這決定了 rebuild 的時機策略：累積一批 content 變動再跑一次，而不是每次寫完就跑。中途中斷是安全的——它在全部 embedding 完成後才寫檔，舊 index 在整個過程中保持完整可用。

**跑之前先把行程脫離 agent 的行程樹。** 這種等級的長工作放在 agent 管理的背景工作裡會連同 `ollama serve` 一起被回收，而且經管線的輸出會被緩衝到看不見進度：

```bash
SP=/tmp/blogsearch-run                      # 任一可寫的暫存路徑
mkdir -p "$SP"
( nohup ollama serve > "$SP/ollama.log" 2>&1 < /dev/null & )
sleep 4 && curl -s -m 3 http://localhost:11434/api/tags >/dev/null && echo ok
cd scripts/blogsearch
( nohup make ingest > "$SP/ingest.log" 2>&1 < /dev/null & )
```

雙重 fork 讓行程 reparent 到 init、不受 agent session 回收影響；輸出直接寫檔而非經管線，進度隨時可讀（`grep -c 'chunks$' "$SP/ingest.log"` 得已處理檔數）。

### 3. 驗證

```bash
cd scripts/blogsearch && make verify     # status + test query
```

驗證標準：

- `status` 顯示 chunk 數 > 0、dimensions = 768
- `query` 回傳的 top-1 結果包含相關文章（如 vector-storage-engineering）
- 無 embed error（Ollama 連線正常）

### 4. 失敗處理

| 錯誤                       | 原因                                     | 修法                                              |
| -------------------------- | ---------------------------------------- | ------------------------------------------------- |
| `connection refused`       | Ollama 沒跑                              | `ollama serve &`                                  |
| `model not found`          | 沒 pull 模型                             | `ollama pull nomic-embed-text`                    |
| `no records to save`       | content 目錄空或路徑錯                   | 檢查 `-content` 參數                              |
| 結果品質差                 | CJK chunking 問題或 embedding 模型不適合 | 先跑幾個已知 query 確認，必要時換 embedding model |
| 跑到一半整個消失、log 空白 | 行程掛在 agent 的背景工作下、被一起回收  | 用上面的雙重 fork 重跑；舊 index 未被破壞、可照用 |
| 長時間零輸出               | `make ingest \| tail` 把輸出緩衝住了     | 輸出直接導檔、不經管線，再 `grep -c` 讀進度       |

## 何時提醒 vs 何時自動執行

| 情境                            | 行為                                        |
| ------------------------------- | ------------------------------------------- |
| 用戶明確要求 rebuild            | 直接執行                                    |
| 用戶要求語意搜尋但 index 不存在 | 提示「index 不存在，要先 rebuild 嗎？」     |
| 寫完文章、對話自然結束          | 提示「新文章還沒進 index，要 rebuild 嗎？」 |
| git pull 後                     | 不主動提，除非用戶接著做語意搜尋            |

原則：rebuild 需要 Ollama 在跑（外部 dependency），不適合無條件自動執行。提示優先於自動。

全量重建無增量選項這件事會改變提示的內容。單篇文章觸發的 rebuild 要一併說出當前規模的耗時量級，讓對方拿得到「現在跑 vs 累積幾篇再跑」這個取捨；只說「要 rebuild 嗎」而不說成本，答應的人不知道自己答應了什麼。

## 跟其他流程的關係

- **內容查重流程**：due-diligence 查重可用 `blogsearch query` 替代手動翻 collection index
- **RAG storage 選型**：本工具的向量 index 設計（flat file + brute-force）可作為 RAG storage 選型的參考實作
- **Demo 與 production 共存**：若專案有 pickle-based RAG demo，blogsearch 是 production 升級版、兩者可共存

**Version**: 1.4.1 — 術語校正：判準全數改為判斷標準（動作修飾語縮為「X 標準」、狀態義改為「X 條件」）。判準的語域在哲學與教育評量、工程讀者解析不了——五份低階模型探針一致回報非通用

**Version**: 1.4.0 — 全量 rebuild 的真實成本進 SOP：耗時改為按當前規模推估（2026-08 實測 3510 檔 / 29863 chunks / 3296 秒，取代過時的「約 4 分鐘」）、明寫無增量模式與它對 rebuild 時機的影響、補雙重 fork 的脫離跑法（掛在 agent 背景工作下會連同 ollama 一起被回收、經管線的輸出會被緩衝到看不見進度）；失敗處理表加這兩種形態；提示規則補「說出耗時量級再問要不要跑」

**Version**: 1.3.0 — SOP 改用 Makefile target（install / ingest / verify）、description 補 ingest 觸發詞
