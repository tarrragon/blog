---
title: "4.16 靜態 / serverless RAG deployment：架構選擇與資安取捨"
date: 2026-05-12
description: "沒 backend 的場景怎麼做 RAG：四種 deployment 方案、API key 暴露問題、CORS / abuse / 第三方信任、跟模組六的 routing"
tags: ["llm", "applications", "rag", "deployment", "static-site", "serverless", "security"]
weight: 16
---

[4.1 RAG](/llm/04-applications/rag-principles/) 跟 [4.12 embedding model](/llm/04-applications/embedding-model-internals/) 寫的是「RAG 在做什麼、embedding 怎麼選」、預設「有 backend server」可跑 embedding 跟 LLM。但實際大量場景是**沒 backend** — 個人 blog（Hugo / Jekyll / Astro）想加智能搜尋、docs site 想做 LLM 對話、demo 想離線跑。本章把這條「靜態 / serverless RAG」路線拆成四個方案、配合靜態場景**特有的資安議題**（這些議題模組六沒覆蓋、屬本章新增）。

## 本章目標

讀完本章後、你應該能：

1. 區分四種 RAG deployment 方案（純前端 / edge serverless / RAG SaaS / 純文字 search）。
2. 對自己場景判斷該選哪個方案、看資料量 / 隱私 / 預算。
3. 認識靜態場景特有的資安議題：API key 暴露、CORS、abuse、第三方 SaaS 供應鏈、client-side 模型完整性。
4. 知道哪些資安議題在 [模組六](/llm/06-security/) 已覆蓋、哪些是本章獨有。

## 為什麼這個議題重要

傳統 RAG 教材預設架構：

```text
User → backend server → embedding API → vector DB → LLM API → response
```

需要 backend 可執行 server-side code、藏 API key、控制 rate limit。但個人開發者場景常見的 deployment：

| 場景                          | Backend？ | 部署方式                        |
| ----------------------------- | --------- | ------------------------------- |
| 個人 Hugo blog                | 無        | GitHub Pages / Cloudflare Pages |
| 開源專案 docs site            | 無        | GitHub Pages / Netlify / Vercel |
| 商品 landing page             | 無        | CDN + S3                        |
| Static-export Next.js / Astro | 無        | 同上                            |

這些場景跟「個人 dev 跑本地 LLM」並列、是教材的合理覆蓋面。

## 四種 deployment 方案總覽

```text
                          embedding   vector       LLM call
                          搜尋          DB
方案 1 純前端            browser       browser     browser（WebLLM）或 user-key 直 call
方案 2 edge serverless   edge fn       edge DB     edge fn → LLM API
方案 3 RAG SaaS          SaaS          SaaS        SaaS（或自 call）
方案 4 純文字 search     N/A           static idx  N/A（不是 RAG）
```

四方案快速對比：

| 維度           | 1 純前端                  | 2 edge serverless      | 3 SaaS               | 4 純文字 search  |
| -------------- | ------------------------- | ---------------------- | -------------------- | ---------------- |
| 是否「真 RAG」 | 是                        | 是                     | 是                   | **否**（無 LLM） |
| 隱私           | 最強（不離 browser）      | 中（信 edge provider） | 弱（信 SaaS）        | 最強             |
| Cost           | 完全 zero（build 一次）   | 每 query 付 edge + LLM | 免費 tier / 按量計費 | Zero             |
| 規模上限       | < 10K chunks              | 1M+                    | 視服務               | 視工具           |
| 開發複雜度     | 中（要 build pipeline）   | 中高（要寫 edge fn）   | 低（API 直接用）     | 低               |
| 主要資安議題   | 模型完整性、user-key 暴露 | edge provider 信任     | SaaS 信任 + 供應鏈   | 較少（無 LLM）   |

## 方案 1：純前端 RAG（browser-side everything）

整個 RAG pipeline 都跑在使用者瀏覽器：

```text
Build time（Hugo build / CI pipeline）：
  content/*.md
    ↓ 抽段、chunk
    ↓ embedding model（Node.js 版 sentence-transformers）
  embeddings.json（每個 chunk 一個 vector）
    ↓ 跟 HTML 一起 deploy

Runtime（user browser）：
  User query
    ↓ load @xenova/transformers + embeddings.json（首訪載 ~50MB）
    ↓ embed query in browser
    ↓ cosine similarity vs embeddings.json
  top-K chunks
    ↓ LLM call（兩條子路線、見下）
  Response in browser
```

LLM 的兩條子路線：

| 子路線                                                       | 機制                                    | 取捨                                         |
| ------------------------------------------------------------ | --------------------------------------- | -------------------------------------------- |
| **[Client-side LLM](/llm/knowledge-cards/client-side-llm/)** | WebLLM / wllama 跑 < 4B model           | 完全離線、首訪載 1-3GB 模型、隱私最強        |
| **User 自帶 API key**                                        | 前端讀 localStorage 的 key、直 call API | 高品質（雲端旗艦）、key 暴露、需要使用者授信 |

實作概要：

```bash
# Build time（Node.js script）
npx @xenova/transformers-cli embed content/*.md > static/embeddings.json

# Frontend（簡化版）
import { pipeline } from '@xenova/transformers';
const embedder = await pipeline('feature-extraction', 'nomic-embed-text-v1.5');
const queryVec = await embedder(userQuery, { pooling: 'mean' });
const ranked = embeddings.map(c => ({ ...c, score: cosineSim(c.vec, queryVec.data) }))
                          .sort((a,b) => b.score - a.score).slice(0, 5);
```

規模上限：

- < 1000 chunks：embeddings.json ~ 4MB（1024-dim float32）、輕鬆
- 1K-10K：~40MB、首訪載入慢但可接受
- 10K+：純前端開始勉強、考慮方案 2

**適合場景**：個人 blog、docs site、demo、隱私敏感、規模 < 10K chunks。

## 方案 2：靜態 + edge serverless

「靜態主站 + edge function 處理動態請求」：

```text
靜態前端（HTML / JS、Hugo / Astro）
   ↓ fetch /api/rag
Edge function（Cloudflare Workers / Vercel Edge / Netlify Functions）
   ↓
Embedding API（OpenAI / Voyage）
   ↓
Vector DB（Cloudflare Vectorize / Pinecone / Turso vector / Upstash Vector）
   ↓
LLM API（OpenAI / Anthropic / Cloudflare AI Gateway）
   ↓ response
靜態前端
```

對使用者體感跟「有 backend」一樣、但你不用維護 server / 不用 sysadmin。

主流元件搭配：

| 元件         | Cloudflare 全家桶            | Vercel / 其他                   |
| ------------ | ---------------------------- | ------------------------------- |
| Edge runtime | Workers                      | Vercel Edge / Netlify Functions |
| Vector DB    | Cloudflare Vectorize         | Pinecone / Turso / Upstash      |
| Embedding    | Workers AI 內建模型 / OpenAI | OpenAI / Voyage                 |
| LLM          | Workers AI / AI Gateway 轉發 | OpenAI / Anthropic              |

關鍵特性：

1. **API key 不暴露在 browser**：edge function 內讀環境變數、安全
2. **可加 rate limit**：edge function 內判斷 client IP / user agent、避免 abuse
3. **Build-time index 仍重要**：embedding ingestion 通常在 build 階段、不在 runtime
4. **Edge cold start**：第一次 query latency 略高（~100ms 額外）、後續 hot 路徑快

**適合場景**：規模 1K-100K chunks、想保留近 backend 體驗、可接受少量 cost。

## 方案 3：靜態 + RAG SaaS

把整個 RAG stack 外包：

| 服務              | 角色                                    | 免費 tier 上限                  |
| ----------------- | --------------------------------------- | ------------------------------- |
| Algolia           | 搜尋 + 向量檢索一條龍、build time 同步  | 10K records、10K search / month |
| Pinecone Cloud    | 純 vector DB、自己 call embedding + LLM | 100K vectors（starter）         |
| Weaviate Cloud    | 同上、hybrid search 內建                | 14 天 trial                     |
| MeiliSearch Cloud | BM25 + vector hybrid                    | 試用                            |

API key 設計：

- **search-only key**：只能查詢、無寫入權限、**可安全暴露在 browser**（這是設計支援的）
- **admin key**：build time CI 用、有寫入權限、必須藏 server-side

前端範例（Algolia）：

```javascript
const client = algoliasearch('APP_ID', 'SEARCH_ONLY_KEY');  // 可公開
const index = client.initIndex('my-blog');
const { hits } = await index.search(userQuery, { hitsPerPage: 5 });
```

**適合場景**：想最快上線、不在乎 vendor lock-in、規模中小、retrieval-only（不需要 LLM 對話）。

## 方案 4：靜態 + 純文字 search（不是真 RAG）

Pagefind、Stork、lunr.js、FlexSearch — build time 產靜態 search index、純前端查詢。

| 工具       | 機制                                  |
| ---------- | ------------------------------------- |
| Pagefind   | static-first、自動 chunking、CJK 友善 |
| Stork      | Rust 寫的 keyword search、輕量        |
| lunr.js    | 純 JS、tf-idf BM25 風格               |
| FlexSearch | 同上、體積更小                        |

**這不是 RAG**：

1. **無 embedding similarity**：keyword / fuzzy match、不是語意相似
2. **無 LLM augmentation**：只列文章連結、不生成回答
3. **算 retrieval 的「字面」變體**：見 [4.1 RAG](/llm/04-applications/rag-principles/) 的「語意 vs 字面」段

**適合場景**：blog 內搜尋只需要找文章、不需要對話、極致 zero-cost。

## 規模門檻：什麼時候該升級方案

```text
< 1K chunks                    → 方案 1 純前端、最簡單
1K - 10K chunks                → 方案 1 或 方案 4
10K - 100K chunks              → 方案 2 edge serverless
100K+ chunks                   → 完整 backend RAG（不再是「靜態」場景）
非 RAG、只要找文章             → 方案 4（Pagefind 等）
```

## 靜態場景特有的資安議題

本章節最重要的部分。靜態 / serverless RAG 有些議題模組六沒覆蓋、要在本章補。

### 1. API key 暴露 — 靜態場景的根本問題

**核心衝突**：靜態網站沒 server-side runtime、藏不了 secret。任何寫在前端 JS / 編進 HTML 的東西、使用者按 F12 都看得到。

對應到 RAG：

| 元件                    | 能否前端持有 key                   | 緩解                                 |
| ----------------------- | ---------------------------------- | ------------------------------------ |
| Embedding API（生成方） | 否（admin key 不該暴露）           | build time 用、不放前端              |
| LLM API（生成方）       | 否                                 | 改方案 2 用 edge、或讓使用者自帶 key |
| Vector DB（read）       | **可**（search-only key 設計支援） | API 設計時就分權、search-only 可公開 |
| 完整 LLM 跑在前端       | N/A（無 server-side key）          | 方案 1 的 Client-side LLM 子路線     |

如果要 LLM 對話功能、三條合法路線：

1. **使用者自帶 API key**（如 Anthropic / OpenAI）、存 localStorage、前端直接 call API — 適合 power user、需要使用者授信
2. **WebLLM / wllama 跑前端 LLM** — 模型在 browser、不需 server-side key
3. **方案 2 edge serverless** — key 藏在 edge function、就不是純靜態了

寫死 API key 在前端 JS 等於把 key 公開、會被 scraper 撿走燒爆 quota — 這是 **anti-pattern**、跟 [6.4 跨雲端 / 本地資料邊界](/llm/06-security/cross-cloud-local-data-boundary/) 提到「API key 寫死 config」的延伸版（前端更嚴重、所有訪客都看得到）。

### 2. User query 隱私

靜態場景的 query 走向：

| 方案              | Query 走向                | 誰能看到                   |
| ----------------- | ------------------------- | -------------------------- |
| 1 純前端 + WebLLM | 從不離 browser            | 只有使用者本人             |
| 1 + user API key  | Browser → 雲端 vendor     | 該 vendor（依政策）        |
| 2 edge serverless | Browser → edge → 雲端 API | Edge provider + LLM vendor |
| 3 SaaS            | Browser → SaaS            | SaaS provider              |

對應 framing 跟 [0.7 隱私資料流](/llm/00-foundations/privacy-data-flow/) 同源 — 但靜態場景的特殊性是「**前端直接出去**」、不像 backend 場景可以加一層中介控制。

特別注意：

1. **方案 3 SaaS 的 query 隱私**：Algolia / Pinecone 都會 log query、依政策可能用於改進服務；對隱私敏感場景不適合
2. **Edge provider 的 region**：Cloudflare Workers 的 edge node 可能在跟使用者不同 region 處理、跨境資料法規（GDPR 等）要考慮
3. **Browser extension 偷 query**：使用者裝的 plugin 可能 access 整個頁面、包含 RAG 介面內的 query

### 3. CORS / 同源策略 — Browser 特有的安全模型

靜態前端 call 任意 API 會撞 CORS（Cross-Origin Resource Sharing）：

```text
靜態網站：https://my-blog.com
要 call：https://api.openai.com/v1/...
   ↓
Browser 檢查 OpenAI 是否在 Access-Control-Allow-Origin 含 my-blog.com
   ↓
OpenAI 預設允許所有 origin（為了讓前端 SDK 能用）→ 通過
某些 API（Anthropic 早期版本）不允許 browser 直 call → 失敗、必須走 edge
```

判讀：

- **能在 browser 直 call 的 API**：OpenAI、Voyage、Algolia（search-only）等明確設計 browser-friendly 的服務
- **不能 browser 直 call、要 edge proxy**：許多企業 LLM API、私有 vector DB、需要 server-only credentials 的服務

CORS 不是「資安漏洞」、是 browser 對「JS 從一個網站 call 另一個網站」的設計約束、用來保護使用者。要繞 CORS 要嗎服務商配合（設 ACAO）、要嗎用 edge function proxy。

### 4. 第三方 SaaS 信任 — 跟 6.0 同源、對象換

[6.0 模型供應鏈與信任邊界](/llm/06-security/model-supply-chain-trust/) 處理的是「**模型權重的信任**」。靜態 RAG SaaS（Algolia / Pinecone / Weaviate Cloud）引入另一條供應鏈：

```text
模型供應鏈（6.0 覆蓋）：
  原作者 → quantizer → registry → 你機器

RAG SaaS 供應鏈（本章新增）：
  你的 content → SaaS embedding service → SaaS vector DB → SaaS retrieval
    └──────── 全程在 SaaS 內、你信任 SaaS 沒做以下事 ────────┘
              - 把你 index 用於訓練他們自己的模型
              - 把你 query log 賣給第三方
              - 沒做適當 isolation（你跟其他客戶的資料）
              - 沒處理好 supply chain（他們用的 base embedding model）
```

判讀類似 [0.7 物理 vs 合約保證](/llm/00-foundations/privacy-data-flow/)：本地方案是物理保證（資料不離 browser）、SaaS 方案是合約保證（信 SaaS 的 ToS）。

### 5. Rate limit / abuse — 前端被 scrape 後濫用

靜態 RAG 的特殊 abuse 路徑：

```text
攻擊者掃到你的 demo blog
   ↓ 找到前端載入的 embedding endpoint / LLM endpoint
   ↓ 直接從攻擊者 server 重複 call（不經 browser）
   ↓ 你的 LLM API quota 燒爆 / SaaS 配額耗光
```

緩解：

1. **方案 2 edge** + 加 rate limit by IP / token bucket：edge function 內 reject 過量請求
2. **方案 1 純前端 + WebLLM**：根本沒 server-side endpoint 可被 abuse、最安全
3. **方案 3 SaaS** + 用 search-only key 並設 query 上限：SaaS 通常內建 quota
4. **CAPTCHA / Turnstile**：邊緣防護

絕對不該做：把 OpenAI / Anthropic API key 寫在前端 JS、想用 rate limit 阻擋 — 攻擊者拿到 key 後不會經過你的 rate limit。

### 6. Client-side LLM 的模型完整性

[Client-side LLM](/llm/knowledge-cards/client-side-llm/) 把幾 GB 模型權重下載到 browser、引入新的供應鏈面：

```text
你的網站
   ↓ <script> 載入 WebLLM runtime（CDN）
   ↓ runtime 從 HuggingFace CDN 抓 model weights
   ↓ 使用者 browser 跑模型
```

風險：

1. **CDN 被 compromise**：WebLLM runtime 或 model weights 在 CDN 上被換、注入 backdoor
2. **HTTPS 之外無額外驗證**：不像本地 [GGUF + hash 比對](/llm/06-security/model-supply-chain-trust/)、browser 載模型純信 CDN + HTTPS
3. **使用者本機沒 inventory 記錄**：跟 [6.0](/llm/06-security/model-supply-chain-trust/) 推薦的「下載後記 hash」對比、browser 沒這機制

緩解：

1. **Subresource Integrity（SRI）**：HTML 的 `<script integrity="sha384-...">` 屬性、browser 自動驗證 hash
2. **CSP（Content Security Policy）**：限制可載入的 script / image source、減少 supply chain attack 面
3. **挑大廠 CDN**：Cloudflare / jsdelivr / unpkg 等被 compromise 的歷史紀錄較少

跟 [6.0](/llm/06-security/model-supply-chain-trust/) 的關係：6.0 講「本機跑的 GGUF 模型供應鏈」、本章補「browser 跑的 client-side 模型供應鏈」— 兩種場景的 framing 一致、但具體威脅面跟工具不同。

## 跟模組六的 routing

本章資安段跟既有 [模組六](/llm/06-security/) 的對應：

| 議題                            | 06 對應章節                                              | 本章補的角度                           |
| ------------------------------- | -------------------------------------------------------- | -------------------------------------- |
| 模型 / 供應鏈信任               | [6.0](/llm/06-security/model-supply-chain-trust/)        | client-side 模型分發新形態             |
| Server 綁定                     | [6.1](/llm/06-security/inference-server-binding/)        | 靜態場景無 server、議題消失            |
| Tool use 權限                   | [6.2](/llm/06-security/tool-use-permission-model/)       | browser-side tool use（少數場景）      |
| Prompt injection                | [6.3](/llm/06-security/prompt-injection-in-ide/)         | 靜態 RAG 仍適用、source 變 web fetched |
| 跨雲端 / 本地資料邊界           | [6.4](/llm/06-security/cross-cloud-local-data-boundary/) | 靜態場景 query 走向跟 backend 場景不同 |
| Production routing              | [6.5](/llm/06-security/routing-to-production-security/)  | 從個人靜態 RAG 升級到 production       |
| **API key 暴露 / browser**      | （無）                                                   | **本章獨有**                           |
| **CORS / 同源策略**             | （無）                                                   | **本章獨有**                           |
| **靜態場景 abuse / rate limit** | （無、跟 6.1 server 議題不同）                           | **本章獨有**                           |

## 判讀流程

```text
你的場景：
  ├─ 有 backend？
  │    └─ 是 → 用 4.0 RAG + 4.8 embedding 主章節、本章不適用
  │    └─ 否 → 繼續
  │
  ├─ 規模？
  │    ├─ < 1K chunks → 方案 1 純前端
  │    ├─ 1K-10K → 方案 1（embeddings.json ~ 40MB 仍可接受）
  │    ├─ 10K-100K → 方案 2 edge serverless
  │    └─ 100K+ → 不再是靜態場景、回 backend
  │
  ├─ 需要 LLM 對話、不只 retrieval？
  │    ├─ 是 + 隱私第一 → 方案 1 + WebLLM
  │    ├─ 是 + 品質第一 → 方案 1 + user-key 或 方案 2
  │    └─ 否（只要找文章） → 方案 4 純文字 search
  │
  └─ 預算 / vendor lock-in 容忍度？
       ├─ 完全 zero-cost、無 vendor → 方案 1 純前端
       ├─ 接受少量 cost、不想自己寫太多 → 方案 3 SaaS
       └─ 接受少量 cost、想自己控 → 方案 2 edge
```

## 不在本章內的主題

1. **完整 backend RAG**：see [4.1 RAG 原理](/llm/04-applications/rag-principles/) 跟 [4.12 embedding model](/llm/04-applications/embedding-model-internals/)
2. **具體 SaaS API 教學**：Algolia / Pinecone 等 API 細節隨版本變、見各 SaaS 文件
3. **WebGPU 內部細節**：GPU shader、WebGPU API 設計屬 web platform 議題、不在 LLM 教材範圍
4. **Production 多租戶 RAG 服務**：屬 backend/07、本章 framing 是「個人 / 小團隊靜態網站」
5. **企業合規 deployment**：HIPAA / GDPR / SOC 2 跟具體 SaaS / cloud provider 強相關、見 [backend/07 合規卡片](/backend/07-security-data-protection/) 跟 [6.4 跨雲端](/llm/06-security/cross-cloud-local-data-boundary/)

## 何時過時 / 何時不過時

**不會過時的部分**：

- 四方案分類（純前端 / edge / SaaS / 純文字 search）
- 「靜態場景藏不了 secret」這個根本特性
- API key 暴露 / CORS / abuse / 供應鏈 / 模型完整性 五大資安議題分類
- 跟 [模組六](/llm/06-security/) 的 routing 關係

**會變的部分**：

- 具體 SaaS / edge provider（Cloudflare Vectorize / Pinecone / Algolia 等持續演化）
- Client-side LLM runtime（WebLLM / wllama / transformers.js）的能力上限
- WebGPU 支援度跟 browser 標準
- 哪些 LLM vendor 允許 browser 直 call（CORS 政策會變）
- 純文字 search 工具（Pagefind 等持續改進）

## 下一步

本章是 [模組四](/llm/04-applications/) 最後一章。讀完整個模組四、完整覆蓋 LLM 作為系統元件的設計取捨。下一步可進入 [模組五 PC 獨立 GPU](/llm/05-discrete-gpu/) 或 [模組六 安全](/llm/06-security/) 補本地 dev 視角的安全議題。
