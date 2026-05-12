---
title: "6.4 跨雲端 / 本地的資料邊界"
date: 2026-05-12
description: "個人 dev 場景下混用雲端 LLM 跟本地 LLM 時的 prompt 洩漏點：Continue.dev 多 provider 設定、隱私資料流、按敏感度分流的判讀"
tags: ["llm", "security", "privacy", "data-boundary", "continue-dev", "cloud-llm"]
weight: 5
---

寫 code 工作流常混用本地 LLM 跟雲端 LLM、混用的好處是組合兩邊優勢、代價是 prompt 在不同信任邊界之間流動。本章把「哪些 prompt 該留本機、哪些可以送雲端、怎麼配置才不會誤送」整理成可操作的分流判讀。本章是 [0.7 隱私資料流原理](/llm/00-foundations/privacy-data-flow/)「資料流 thinking + 信任邊界」的具體落地、跟 [1.3 VS Code + Continue.dev 整合](/llm/01-local-llm-services/vscode-continue-integration/) 的 multi-provider 配置直接對應。信任邊界詞彙見 backend [trust-boundary](/backend/knowledge-cards/trust-boundary/) 卡、PII 跟資料分類見 backend [pii](/backend/knowledge-cards/pii/) / [data-classification](/backend/knowledge-cards/data-classification/) 卡、API key 管理見 backend [secret-management](/backend/knowledge-cards/secret-management/) 卡。本章 framing 是個人 dev 視角；production 場景的 log / PII 治理見 [backend/07 LLM log 與 PII 治理](/backend/07-security-data-protection/llm-log-and-pii-governance/)。

讀完本章後、你應該能對自己的 IDE 工作流回答：每個 LLM provider 收到什麼 prompt、雲端服務的資料政策大致長怎樣、哪些任務該分到本地、哪些可以送雲端、配置誤送的常見路徑跟對應防護。

## 本章目標

1. 認識「prompt 邊界」在多 provider 工作流的位置。
2. 區分本地 LLM 跟雲端 LLM 在資料流上的差異。
3. 認識主流雲端 LLM 服務的資料政策大致分類。
4. 用「敏感度 × 任務類型」軸把工作流分流到本地或雲端。
5. 認識多 provider 設定下、prompt 誤送的常見路徑跟對應防護。

## prompt 邊界在哪

在多 provider 工作流下、prompt 邊界長這樣：

```text
                ┌───────────────────────────┐
                │  使用者 + 本機 codebase   │ ← trust zone A：完全本地
                └───────────────────────────┘
                            ↓ prompt
        ┌─────────────────────────────────────────┐
        │  IDE LLM client（Continue.dev）         │
        │   ↓ route by config                     │
        │   ├── 本地 model（Ollama / llama-server）│ ← trust zone B：仍在本機
        │   ├── 商業雲端（Anthropic / OpenAI）     │ ← trust zone C：雲端 vendor
        │   └── 第三方 LLM 聚合（OpenRouter etc.） │ ← trust zone D：聚合層 + 上游 vendor
        └─────────────────────────────────────────┘
```

每跨一條邊界、prompt 都會被另一個主體看到。trust zone B 是本機 process（包括其他可能 dump 流量的工具）、C 是商業 LLM vendor、D 是聚合層加上游 vendor、複雜度跟洩漏面隨層數增加。

## 本地 LLM vs 雲端 LLM 在資料流上的差異

| 維度         | 本地 LLM           | 雲端 LLM                                       |
| ------------ | ------------------ | ---------------------------------------------- |
| prompt 走向  | 留本機             | 送到 vendor、依政策可能 log / 訓練用           |
| 模型權重     | 在本機             | 在 vendor                                      |
| 帳號需求     | 無                 | 需註冊、有 API key                             |
| 監管 / 合規  | 跟本機資料保護一致 | 跟 vendor 政策（GDPR、HIPAA 等）對齊           |
| 商業機密內容 | 較適合             | 看 vendor 政策、enterprise plan 通常承諾不訓練 |
| 大模型能力   | 視本機硬體         | 較高（GPT-5、Claude 等旗艦）                   |
| 反應速度     | 視本機硬體         | 視網路 + vendor                                |
| 持續成本     | 一次硬體投入       | 按 token / call 收費                           |

混用的好處：

1. **敏感任務留本地**：機密 codebase、PII、合約等不送雲端。
2. **能力受限任務送雲端**：跨檔案重構、複雜推理用旗艦雲端模型。
3. **離線可用**：本地當 fallback、雲端不可用時仍能基本運作。

混用的風險：**配置稍微錯一步、原本想留本地的 prompt 被誤送到雲端**。

## 主流雲端 LLM 服務的資料政策（大致分類）

各家雲端 LLM 服務的資料政策依方案跟版本變化、大致可以分成幾類：

| 政策類別                    | 典型描述                                          | 個人 dev 視角                                     |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------- |
| Enterprise / API 預設不訓練 | 透過 API 送的內容不用於訓練、僅依條款保留         | 商業 API 的常見預設、個人 dev 用 API key 通常套用 |
| Consumer 預設可能用於訓練   | ChatGPT.com、Claude.ai 等網頁版、預設可能用於訓練 | 看清楚當前條款跟 opt-out 開關                     |
| 30 天 abuse log 保留        | 為了 abuse detection 保留 30 天、之後刪除         | 多數商業 API 的常見做法                           |
| Zero retention（特殊方案）  | enterprise 或特殊申請、不保留任何內容             | 個人 dev 通常用不到                               |

> **事實查核註**：上面是 2026 年 5 月主流商業 LLM 服務的常見政策分類、具體條款依 vendor、地區、方案、版本快速變化、且各家詞彙不一致（如「training」「improve our services」「abuse review」可能指不同範圍）。引用前以對應 vendor 的當前官方[資料政策頁面](https://www.anthropic.com/legal/privacy)、[OpenAI Data Policy](https://openai.com/policies/) 等為準。

判讀重點不是「哪家最嚴」、是「我送進去的內容、貼合我的預期嗎」。

## 按敏感度 × 任務類型分流

把工作流分流到本地或雲端的兩軸：

```text
敏感度軸：
  公開 / 一般 / 機密 / 高機密（PII、合約、未公開 codebase）

任務類型軸：
  補完 / 解釋 / 重構 / 設計討論 / 端到端 agent
```

對應的分流建議：

| 任務 \ 敏感度 | 公開 / 一般            | 機密                         | 高機密（PII、合約、未公開核心）   |
| ------------- | ---------------------- | ---------------------------- | --------------------------------- |
| 補完          | 雲端或本地皆可、看速度 | 本地優先                     | 本地、且 disable codebase RAG     |
| 解釋程式碼    | 雲端較流暢             | 本地、視內容                 | 本地、避免送整檔                  |
| 跨檔案重構    | 雲端旗艦能力較強       | 看 enterprise plan 的政策    | 本地、或人工切片送雲端            |
| 設計討論      | 雲端較流暢             | enterprise plan 或本地       | 本地、且過濾掉具體 entity 名稱    |
| 端到端 agent  | 雲端旗艦               | 本地、且降低 tool 副作用範圍 | 不適合 agent、改用 chat-only 本地 |

實務上的常見模式：

1. **預設本地、特定任務開雲端**：日常工作走本地、需要旗艦能力時手動切。
2. **預設雲端、敏感任務切本地**：日常走雲端旗艦、開機密 repo 時切本地。
3. **依 repo 切**：用 Continue.dev / IDE 工具的「per-workspace config」、每個 repo 自己決定。

選哪種模式取決於工作流的敏感度分布。多數寫 code 個人 dev 屬於「一般 / 機密混合」、值得用模式 1 或模式 3。「哪個任務適合本地、哪個適合雲端」的任務面判讀見 [1.5 期望管理](/llm/01-local-llm-services/expectation-management/)、本章補上「分流之後的資料邊界」面。

## Continue.dev 多 provider 配置範例

Continue.dev 基礎安裝跟單一 provider config 見 [1.3 VS Code + Continue.dev 整合](/llm/01-local-llm-services/vscode-continue-integration/)、本節聚焦多 provider 共存下的安全性設計。下面是一個合理的 Continue.dev 配置範例、把本地 + 雲端混用、清楚標出每個 model 的走向：

```json
{
  "models": [
    {
      "title": "Local 30B MoE (default)",
      "provider": "ollama",
      "model": "qwen3-30b-a3b",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "Local 14B (fast)",
      "provider": "ollama",
      "model": "qwen3-14b",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "Cloud Claude (premium only)",
      "provider": "anthropic",
      "model": "claude-sonnet-4-6",
      "apiKey": "${env:ANTHROPIC_API_KEY}"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Local autocomplete",
    "provider": "ollama",
    "model": "qwen3-14b"
  }
}
```

關鍵設計：

1. **預設模型是本地**：list 第一個是 local、tabAutocomplete 也是 local。
2. **雲端模型 title 明確標記**：「Cloud Claude」開頭、避免選錯。
3. **autocomplete 永遠本地**：補完的 prompt 流量大、autocomplete 屬於高頻、留本地。
4. **API key 從環境變數**：不寫死在 config 裡、避免 commit 進 git。

> **事實查核註**：Continue.dev 的 config 格式跟 provider 支援度依版本變化、本範例為示意、實際引用以當前 Continue.dev 官方文件為準。

## prompt 誤送的常見路徑

個人 dev 場景下常見的 prompt 誤送路徑：

1. **預設 model 設成雲端、按了 hotkey 沒看到當前 model**：把寫到一半的機密 prompt 送到雲端。對應防護：預設改本地、雲端 model 用名稱前綴明確。
2. **autocomplete 設成雲端**：補完每幾秒就觸發、prompt 包含當前游標附近 code、流量大且持續。對應防護：autocomplete 必定本地。
3. **codebase RAG 索引到 `.env` / secrets**：RAG 把 secret 加進 prompt、再送雲端。對應防護：IDE search exclude 加上 `.env`、`*.key`、`secrets/`、`.aws/`。RAG 把外部內容引入 prompt 的整體機制與失敗模式見 [4.0 RAG 原理](/llm/04-applications/rag-principles/)。
4. **多 client 同時跑、key 共用**：Cursor / Continue.dev / Claude Code 等多 client 共用 API key、難追是哪個 client 的流量。對應防護：給每個 client 各自的 API key、有問題能追溯。
5. **聚合服務不知道實際送到哪**：用 OpenRouter / together.ai 等聚合層、prompt 經過聚合層後送到上游 vendor、上游可能是不同 region 不同政策。對應防護：個人 dev 場景傾向不用聚合、直接接 vendor。
6. **forgot prompt history 含 sensitive content**：某次貼了機密內容後、後續同 conversation 都帶著、不知不覺重複送。對應防護：機密 prompt 用獨立 conversation、用完清空。

## 個人 dev 場景的最低防護建議

1. **預設模型設成本地**：避免誤觸發雲端。
2. **autocomplete 必定本地**：流量大、持續、適合本機處理。
3. **API key 從環境變數讀、不寫死 config**：dotfile commit 不會洩漏。
4. **codebase search exclude `.env` / secrets 路徑**：避免 RAG 索引到 secret。
5. **看完 prompt 內容再送雲端**：對重要任務、value 不大但風險高時 prefer 本地。
6. **不同 client 用不同 API key**：流量追溯。
7. **機密 prompt 用獨立 conversation**：用完清空、不污染後續。

## 雲端 vendor 的 enterprise plan 選擇

當個人 dev 工作流穩定後、若要把雲端 LLM 用得更深、可以評估 enterprise plan：

| Plan 類型                | 典型差異                             | 個人 dev 適用性     |
| ------------------------ | ------------------------------------ | ------------------- |
| Consumer / Free          | 預設可能用於訓練、有 opt-out         | 不適合機密內容      |
| API key（pay-as-you-go） | 通常預設不訓練、保留 30 天 abuse log | 多數個人 dev 用這個 |
| Team / Pro 訂閱          | 多人共用、可能有額外 data control    | 個人或小團隊適用    |
| Enterprise               | zero retention、SLA、客製合約        | 個人 dev 通常用不到 |

選擇判讀：個人 dev 主要看「API key 預設政策」、若不夠用、再評估升級。

## 給讀者的跨邊界判讀流程

每次設新工作流 / 換 LLM client / 加新 model 時的判讀流程：

1. **盤點 model 列表**：每個 model 是本地還是雲端、走哪家 vendor。
2. **看 vendor 的當前政策**：別憑印象、看當前官方文件。
3. **設定 default model + autocomplete model**：default 跟 autocomplete 是高頻路徑、優先本地。
4. **加 codebase RAG exclude**：把 secret / sensitive path 排除。
5. **跑簡單測試**：開個假機密 prompt（如「我的 SSH key 是 fake-key-test」）、觀察 client log 跟 vendor dashboard、確認流量去向符合預期。

## 小結

跨雲端 / 本地的混用是個人 dev 場景的常見模式、能力跟隱私的平衡靠分流。風險主要在「配置稍微錯一步、prompt 被誤送」、防護重點是「預設本地、雲端明確標記、autocomplete 必定本地、RAG exclude secret」。雲端 vendor 的政策依方案跟時間變化、引用前以當前官方文件為準。production 場景的 log / PII 治理跟 vendor 合約管理見 backend/07。

下一章：[6.5 跨進 production 的 routing 中樞](/llm/06-security/routing-to-production-security/)、整合本模組到 backend/07 production 場景的路由。
