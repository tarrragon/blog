---
title: "4.6 衍生產物管理原理：什麼進 git、什麼不該"
date: 2026-05-12
description: "LLM 應用的 source / derived / external 三類產物對應 git / build cache / registry、與 production 部署的 reproducibility / cost / share 取捨"
tags: ["llm", "applications", "git", "artifacts", "deployment"]
weight: 6
---

LLM 應用的 codebase 不只 source code、還含 [embedding](/llm/knowledge-cards/embedding-model/) index、cache、model weights、prompt config、lockfile、log 等各種「衍生」或「外部」產物。每個產物該不該進 git、有沒有共通邏輯？

本章寫的是「**source / derived / external 三類產物的判讀框架**」、跟「production deployment 怎麼處理 share + reproducibility 取捨」。對應到 hands-on 系列實際遇到的問題——為什麼 [RAG](/llm/knowledge-cards/rag/) demo 的 `index.pkl` 進 `.gitignore`、Hugging Face model weights 為什麼不能塞進 repo、prompt template 該怎麼版本管理。

跟 [4.5 Production resource planning](/llm/04-applications/production-resource-planning/) 對應「production 怎麼跑」、本章對應「production 怎麼版本控制 + 部署」。

## 本章目標

讀完本章後、你應該能：

1. 用「source / derived / external」三分類判讀任何產物該不該進 git。
2. 看到 `.gitignore` 設計、能解釋每條規則的邏輯。
3. 在 reproducibility 跟 repo 大小之間做合理取捨。
4. 知道 derived / external 產物該用什麼機制 share（registry、build script、artifact storage）。

## 三類產物 framework

| 類別         | 定義                       | 例子                                                  | 該進 git？               |
| ------------ | -------------------------- | ----------------------------------------------------- | ------------------------ |
| **Source**   | 人類撰寫、是真理來源       | code、prompt template、test fixture、config schema    | ✓ 必須                   |
| **Derived**  | 從 source 自動產出、可重建 | binary、index、cache、compiled output、generated docs | ✗ 不該                   |
| **External** | 從外部下載、跟 source 解耦 | model weights、dependency package、dataset            | ✗ 用 registry / manifest |

判讀問題：「**刪掉重來、用什麼能 reconstruct 一模一樣？**」

- 用人手寫 → source、必須 commit
- 用 build script + source → derived、commit manifest（如 lockfile）不 commit output
- 用 download script + URL → external、commit URL 不 commit content

這個 framework 跨任何技術 stack 都成立（不只 LLM）、但 LLM 應用尤其放大 derived / external 比例。

## LLM 應用具體對應

### Source（進 git）

| 產物                          | 說明                                              |
| ----------------------------- | ------------------------------------------------- |
| 程式 source code              | wrapper script、framework 整合 code               |
| Prompt template               | system prompt、few-shot example、prompt structure |
| Config schema                 | 哪些參數可調、合法範圍、default value             |
| Test fixture                  | 測試輸入 / 預期輸出 pair                          |
| Markdown content（如本 blog） | 文章本身就是 source                               |
| `.gitignore` / lock file 規則 | 描述哪些不進 git 也是 source                      |
| Build script                  | `ingest.py`、`build.sh`、能從 source 重建 derived |

### Derived（不進 git、但 build path 進 git）

| 產物                                 | 為什麼不 commit                                                 | 怎麼 share                                          |
| ------------------------------------ | --------------------------------------------------------------- | --------------------------------------------------- |
| `index.pkl`（RAG embedding index）   | 從 corpus + embedding model 重建、跟 model 版本綁、3.7 MB-GB 級 | `ingest.py` script、跑一次就 reconstruct            |
| Embedding cache（per-document hash） | 跑時動態建、避免重 embed 同 chunk                               | 不 share、各自 rebuild                              |
| Python `__pycache__/`                | 跑時自動產、Python 版本敏感                                     | 不 share、各自 rebuild                              |
| Compiled binary（如 `bin/mdtools`）  | 從 Go source build、平台敏感                                    | source + build instructions、可選 release page 提供 |
| Generated docs（如 Hugo `public/`）  | 從 markdown source build、deploy 時自動生                       | source + deploy pipeline                            |
| Log files                            | runtime output、量大、有 PII 風險                               | 不 share、log retention 政策另立                    |

### External（不進 git、用 manifest / registry）

| 產物              | Manifest / registry                   | 例子                                        |
| ----------------- | ------------------------------------- | ------------------------------------------- |
| LLM model weights | Hugging Face / Ollama registry tag    | `nomic-embed-text:latest`、`sd_xl_base_1.0` |
| Python dependency | `requirements.txt` / `pyproject.toml` | `requests==2.31.0`                          |
| Node modules      | `package.json` + `package-lock.json`  | `react@18.2.0`                              |
| Dataset           | `data.dvc` / S3 URL + checksum        | training data、eval set                     |
| Docker image      | `Dockerfile` + image tag              | `python:3.11-slim`                          |

External 跟 derived 的差別：external 來自 git 外的 source、derived 來自 git 內的 source。但**機制上都不該直接 commit**——manifest 進 git、實際 bytes 進 registry。

## 為什麼 derived / external 不該進 git

每條限制有具體技術理由：

### Size

Git 設計給 source code（小、純文字、頻繁 diff）。Derived / external 通常大、binary、不適合：

- Git 對 large binary 沒有有效 delta 演算法、每次小改 → 完整 copy 進 history
- Repo size 線性漲、clone 變慢、CI cache 爆炸
- GitHub 等服務有 file size 上限（GitHub 100 MB / file）

實例：`scripts/rag-demo/index.pkl` 3.7 MB、每次 corpus 改 → 重 ingest → 整檔變。Commit 100 次 = git history 多 370 MB。Clone 痛。

### Reproducibility（反直覺）

直覺：「commit derived 保證每個 clone 都拿到一樣的 output」——錯。

實際：

- Derived 跟 build env 綁（Python 3.13 build 的 pickle 在 3.14 不一定能 load）
- Embedding index 跟 model version 綁（pull 不同 model 結果不同）
- 用舊 commit 的 derived 跑在新 env 反而比 rebuild 更脆弱

正確 reproducibility 機制：commit **build instruction + lockfile**、別人 rebuild 時用同樣輸入產同樣 output。

### Update frequency mismatch

Source 改慢、derived 改快。`content/` 加一句話、`index.pkl` 整個重建。如果都進 git：

- 90% 的 commit 是「rebuild artifact」、語意上不是真正的「source change」
- git log 看不出真正 source 改動
- diff review 被 derived noise 淹沒

### Cost / Performance

CI / CD pipeline 通常自動 rebuild derived。不 commit 反而：

- Source-only PR 較易 review（沒 generated diff）
- CI build cache 重用、不需從 git 拉 derived
- Deploy artifact registry 跟 git 分離、各自 scale

## .gitignore 設計模式

LLM 應用典型 `.gitignore` 結構：

```gitignore
# === Source-side build output (derived) ===
# Compiled binaries
bin/
dist/
build/
*.pyc
__pycache__/

# Hugo / static site generators
public/
.hugo_build.lock
resources/

# RAG / vector indexes (regenerable)
scripts/rag-demo/index.pkl
*.pkl
*.index

# Embedding caches
.embedding_cache/
.vector_cache/

# === External-bound (don't commit, use manifest) ===
# Python deps (commit requirements.txt instead)
.venv/
venv/
env/

# Node deps
node_modules/

# Model weights / large files
*.safetensors
*.gguf
*.onnx
*.bin

# Datasets
data/raw/
data/processed/

# === Runtime / Local ===
# Logs
*.log
logs/

# OS / IDE
.DS_Store
.vscode/
.idea/

# Local secrets / API keys
.env
.env.local
*.key

# Temp / cache
*.tmp
.cache/
```

### 邊界 case 思考

幾個容易誤判的：

| 產物                                | 該不該 commit                        | 為什麼                                |
| ----------------------------------- | ------------------------------------ | ------------------------------------- |
| `package-lock.json` / `poetry.lock` | ✓ commit                             | 是 manifest、保證 reproducibility     |
| `node_modules/`                     | ✗ 不 commit                          | 是 derived、可從 lockfile 重建        |
| 小型 fixture data（< 1 MB）         | ✓ commit（作 source）                | 是 test 的一部分、不 reconstruct      |
| 大型 eval dataset（> 100 MB）       | ✗ 用 dvc / S3 manifest               | 量大、不該進 git history              |
| Pre-built model 用於 demo           | ✗ 用 release artifact / Hugging Face | 量大、版本要可追蹤                    |
| Prompt template (markdown / yaml)   | ✓ commit                             | 是 source、影響行為、要 diff          |
| 從 LLM 生的 sample output           | ✗ 不 commit（除非當 fixture）        | 是 demo artifact、不 reconstruct 來源 |

判讀 heuristic：

```text
這個檔案、半年後 production deploy 時要不要存在？
├─ 要：source 或 manifest 進 git
└─ 不要：runtime / 開發環境 only、用 .gitignore
```

## Source / Derived / External 的 share 機制

不 commit 不代表不 share、只是用對的 channel。

### Source share = git

直接 clone 即可。

### Derived share 三種模式

1. **Build script in repo**：別人 clone 後跑 script 重建（本 blog 用這條：`ingest.py` 重建 index）
   - 優點：無外部依賴、self-contained
   - 缺點：每個 clone 都要重跑、累積 compute time
2. **Release artifact**：把 build output 上傳 GitHub Releases / S3、clone 後下載
   - 優點：clone 快、不用各自 rebuild
   - 缺點：要 maintain release pipeline、artifact 版本管理另立
3. **Artifact registry**：用 OCI registry、Docker registry、artifact storage（如 GitHub Packages / JFrog Artifactory）
   - 優點：production-grade、跨 team / 跨 org share
   - 缺點：複雜、配 auth、cost

選擇：小專案用 script、中型用 release、大型 / 多人 collaboration 用 registry。

### External share = manifest

把「**從哪下載 + checksum**」commit 進 git、實際 content 不進。常見 manifest format：

| Manifest                              | 描述                                       |
| ------------------------------------- | ------------------------------------------ |
| `requirements.txt` / `pyproject.toml` | Python deps + version                      |
| `package.json` + `package-lock.json`  | Node deps + exact version + integrity hash |
| `Dockerfile`                          | OS + 環境 + 依賴 + entrypoint              |
| `dvc.yaml` + `dvc.lock`               | dataset + model version                    |
| Ollama Modelfile（如果寫了）          | LLM model + system prompt 組合             |
| `Cargo.lock` / `go.sum`               | Rust / Go 的 dep checksum                  |

Manifest 自己是 source（人寫、進 git）、它指向的 external content 不進 git（用 download script 取回）。

## Prompt 跟 config 的版本控制

LLM 應用特有的問題：**prompt template 是 source、但 prompt 改變影響行為跟 derived 改變不同**。

| Prompt 操作             | git 行為      | 影響                          |
| ----------------------- | ------------- | ----------------------------- |
| 改一個字                | 一個 commit   | 模型行為可能大變、要重跑 eval |
| 加 few-shot example     | 一個 commit   | 同上                          |
| 換不同模型（在 config） | config commit | 用 prompt 沒變、行為變        |

Prompt + model 是一對組合、行為相依、改一個都要重 test。建議在 commit message / PR description 描述「這個 prompt 改動的 expected behavior change」、不要當 trivial 小改 review。

### Prompt 跟 evaluation 一起管理

進階做法：每個 prompt 配 evaluation set、commit 在同 PR：

```text
prompts/
├── code_review.md           ← prompt template
├── code_review_eval.json    ← input + expected output pair
└── code_review_history.md   ← 改動記錄 + 對應 eval score
```

每次改 prompt、跑 eval、比較 score、進 commit message。這比「改完 push 看看效果」可控很多、是 prompt engineering 的基本姿勢。

## Production deployment 的對接

本地 hands-on 跟 production 對應：

| 本地 hands-on                  | Production                                               |
| ------------------------------ | -------------------------------------------------------- |
| `python ingest.py` build index | Build pipeline 跑同樣 script、output 進 artifact storage |
| `ollama pull nomic-embed-text` | Container image 預載 model 或 mount volume               |
| `.gitignore` 排除 index.pkl    | CI 自動 rebuild、deploy 時讀 artifact storage            |
| Source code 進 git             | Source 觸發 CI、build & deploy                           |

成熟的 LLM 應用部署 pipeline：

```text
Source change → git push
              → CI triggered
              → Build derived artifacts (index, container image)
              → Run evaluation suite (prompt + model behavior tests)
              → Push artifacts to registry
              → Deploy with manifest pointing to specific artifact version
              → Smoke test against production data
              → Auto-rollback if metrics regress
```

每一步都要 commit-able 的 manifest、不能有「手動 build 完 ssh 進 prod scp」這種 ad-hoc 流程。Manifest 是 reproducibility 跟 audit 的基礎。

## 何時這篇會過時

**不會過時的部分**：

- Source / derived / external 三分類 framework
- 「commit manifest、不 commit content」核心原則
- `.gitignore` 通用模式
- Reproducibility 來自 build instruction、不來自 commit derived

**會變的部分**：

- 具體 manifest format（半年一個新 lockfile 格式）
- Artifact registry 主流（OCI / Conda / npm 等都會演化）
- LLM model registry（Hugging Face / Ollama 都會演化）

新 lock 格式 / registry 出來時、回到三分類問：它解的是哪類產物？我能用它 commit manifest 不 commit content 嗎？通常答案 yes。

## 跟其他章節的關係

- [scripts/README.md](https://github.com/tarrragon/blog/blob/main/scripts/README.md)：本章原理的實作 reference
- [Hands-on quickstart](/llm/01-local-llm-services/hands-on/quickstart/)：跑通 demo 步驟、為什麼要 rebuild `index.pkl`
- [4.5 Production resource planning](/llm/04-applications/production-resource-planning/)：production runtime 視角、本章是 deployment 視角
- [0.7 隱私資料流原理](/llm/00-foundations/privacy-data-flow/)：什麼可以離開機器、本章是「什麼可以進 git」的 sibling
