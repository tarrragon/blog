---
name: blogsearch-lifecycle
description: "blogsearch 向量 index 的生命週期管理：偵測 index 過時或不存在、觸發 rebuild、驗證結果。適用於有 blogsearch 語意搜尋工具的專案。觸發詞：blogsearch、rebuild index、ingest、向量搜尋、語意搜尋、index 過時、content 變動、pull 後 rebuild、新增文章後搜尋。Trigger when content changes may have made the search index stale, or when semantic search is needed."
license: MIT
metadata:
  version: 1.2.0
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
cd scripts/blogsearch && make ingest     # build index（全量 ~4 分鐘）
```

預期輸出：逐檔列出 chunk 數、最後顯示總 chunk 數與耗時。

### 3. 驗證

```bash
cd scripts/blogsearch && make verify     # status + test query
```

驗證判準：

- `status` 顯示 chunk 數 > 0、dimensions = 768
- `query` 回傳的 top-1 結果包含相關文章（如 vector-storage-engineering）
- 無 embed error（Ollama 連線正常）

### 4. 失敗處理

| 錯誤                 | 原因                                     | 修法                                              |
| -------------------- | ---------------------------------------- | ------------------------------------------------- |
| `connection refused` | Ollama 沒跑                              | `ollama serve &`                                  |
| `model not found`    | 沒 pull 模型                             | `ollama pull nomic-embed-text`                    |
| `no records to save` | content 目錄空或路徑錯                   | 檢查 `-content` 參數                              |
| 結果品質差           | CJK chunking 問題或 embedding 模型不適合 | 先跑幾個已知 query 確認，必要時換 embedding model |

## 何時提醒 vs 何時自動執行

| 情境                            | 行為                                        |
| ------------------------------- | ------------------------------------------- |
| 用戶明確要求 rebuild            | 直接執行                                    |
| 用戶要求語意搜尋但 index 不存在 | 提示「index 不存在，要先 rebuild 嗎？」     |
| 寫完文章、對話自然結束          | 提示「新文章還沒進 index，要 rebuild 嗎？」 |
| git pull 後                     | 不主動提，除非用戶接著做語意搜尋            |

原則：rebuild 需要 Ollama 在跑（外部 dependency），不適合無條件自動執行。提示優先於自動。

## 跟其他流程的關係

- **內容查重流程**：due-diligence 查重可用 `blogsearch query` 替代手動翻 collection index
- **RAG storage 選型**：本工具的向量 index 設計（flat file + brute-force）可作為 RAG storage 選型的參考實作
- **Demo 與 production 共存**：若專案有 pickle-based RAG demo，blogsearch 是 production 升級版、兩者可共存

**Version**: 1.3.0 — SOP 改用 Makefile target（install / ingest / verify）、description 補 ingest 觸發詞
