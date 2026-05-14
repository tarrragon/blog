---
title: "4.2 RAG 檢索增強：query rewriting / HyDE / multi-step / context packing"
date: 2026-05-14
description: "Query 端增強（rewriting / expansion / HyDE）、multi-step iterative retrieval、retrieve 後的 context packing（dedup / ordering / summarization）、adaptive retrieval：vanilla RAG 不夠時的下一層工具箱"
tags: ["llm", "applications", "rag", "retrieval"]
weight: 2
---

[4.1 RAG 原理](/llm/04-applications/rag-principles/) 建立了 vanilla RAG 的骨架——chunk、embed、retrieve、prompt——並列出 hybrid + reranker 的 production 兩段式。本章往上走一層、寫**當 vanilla 兩段式仍不夠時、有哪些增強技術可選**。

實務上 vanilla RAG 不夠用的場景比想像多：[query-document gap](/llm/knowledge-cards/query-document-gap/) 大、單次 retrieve 拿到的片段不足以回答完整問題、retrieve 結果太多塞爆 context、不該 retrieve 的問題被強制 retrieve。每個場景對應不同的增強技術。本章把這些技術寫成可挑選的工具箱、不是「全部都套」的最佳實踐。

## 本章目標

讀完本章後你能：

1. 區分 retrieval pipeline 的四個增強層（query 端 / retrieval 端 / context 組裝端 / 控制流端）。
2. 對 [query-document gap](/llm/knowledge-cards/query-document-gap/) 選對工具（query rewriting / expansion / HyDE）。
3. 判斷任務需要 multi-step retrieval 還是 single-step 夠用。
4. 設計 retrieve 後的 [context packing](/llm/knowledge-cards/context-packing/)（dedup、ordering、summarization）。
5. 設計 adaptive retrieval：什麼時候該 retrieve、什麼時候直接答。

## Retrieval Pipeline 的四個增強層

Vanilla RAG 是「query → retrieve → prompt」三步。增強分四層、每層解不同問題：

```text
┌─────────────────────────────────────────────────┐
│ User query                                      │
└─────────┬───────────────────────────────────────┘
          ↓
   [1. Query 端增強]
   query rewriting / expansion / HyDE / query decomposition
          ↓
   [2. Retrieval 端增強]
   hybrid search + reranker（見 4.1）
   multi-step / iterative retrieval
          ↓
   [3. Context 組裝端]
   dedup / ordering / summarization / compression
          ↓
   [4. 控制流端]
   adaptive retrieval（要不要 retrieve）/ self-RAG
          ↓
   LLM final answer
```

判讀 vanilla 不夠時、先定位失敗在哪一層、再選對應工具。盲目把四層全套上、[retrieval cost](/llm/knowledge-cards/retrieval-cost/) 跟 latency 翻倍、accuracy 不一定有對應收益。

## Query 端增強

Vanilla RAG 直接用 user query 做 embedding、但 user query 往往不是「最適合 retrieve 的形狀」。Query 端增強就是在 retrieve 前重塑 query。

### [Query rewriting](/llm/knowledge-cards/query-rewriting/)

用 LLM 把 user query 改寫成「更接近 document phrasing」的形式。

- **適用**：query 口語、document 正式（如 user：「怎麼讓 API 跑快」、document：「latency optimization techniques」）。
- **實作**：LLM call、prompt 是「把以下 query 改寫成適合 search 的查詢句、保留語意、改用技術詞彙」。
- **失效**：rewriting 把意圖改偏（user 問「為什麼慢」、改成「optimization」、答非所問）。緩解：rewriting 提示要求 preserve intent、retrieve 結果回來後讓 LLM 對照原 query 判斷。
- **Cost**：每 query 多一個 LLM call、latency 加 200–500ms，屬於 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)。

### [Query expansion](/llm/knowledge-cards/query-expansion/)

不改 query、而是**生成多個 query 變體**、一起 retrieve、合併結果。

- **適用**：query 短、有多種可能解讀（「python」可指語言 / shell / 套件）、單一 query 漏 coverage。
- **實作**：LLM 生成 3–5 個變體（同義改寫、不同角度、不同抽象層級）、每個變體獨立 retrieve、結果用 Reciprocal Rank Fusion 合併（RRF 是 RAG 文獻常見的多 [retrieval source](/llm/knowledge-cards/retrieval-source/) 合併演算法、不在本指南範圍展開）。
- **失效**：變體太發散、混入無關 doc、稀釋了 top-k 的精確度。緩解：限制變體數量（3–5）、合併時對重複出現的 doc 加權。
- **Cost**：N 倍 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)、但每次 retrieve 是平行、latency 不是 N 倍。

### HyDE（Hypothetical Document Embeddings）

[HyDE](/llm/knowledge-cards/hyde/)（[4.1 RAG 原理](/llm/04-applications/rag-principles/) 提過、這裡展開）。核心觀察：**query 跟 document 在 embedding 空間的距離、往往比 document 跟 document 之間更遠**——這是 [query-document gap](/llm/knowledge-cards/query-document-gap/) 的典型表現。

機制：

1. 用 LLM 對 user query 生成「一份假設的答案文件」（hallucinated document）。
2. 對這份假文件做 embedding、不是對原 query。
3. 用假文件 embedding 去 retrieve 真實 document。

為什麼比直接 embed query 好：假文件的 phrasing、長度、結構都更接近 document 分佈、embedding 距離更可靠。**重點是 retrieval、不是回答**——假文件的事實正確性不重要（hallucinate 出錯誤細節 OK）、但語意 / 領域要落在對的範圍、才能拉回對的 document。

- **適用**：[query-document gap](/llm/knowledge-cards/query-document-gap/) 顯著的場景（問句 vs 陳述、口語 vs 正式、抽象 vs 技術詞彙）。HyDE 原論文跨多個領域 benchmark 都有提升、不限技術 / 學術。
- **失效**：假文件偏離主題（LLM hallucinate 到別的領域）、retrieve 拿到完全不相關的東西。緩解：生成多個假文件取平均 embedding、或用 query + 假文件兩個 embedding 合併 retrieve。
- **Cost**：每 query 多一個 LLM call（生假文件）、latency 加 500ms–1s。

### [Query decomposition](/llm/knowledge-cards/query-decomposition/)

把複雜 query 拆成幾個子 query、各自 retrieve、再合併。

- **適用**：複合問題（「比較 A 跟 B 在 X 跟 Y 的差異」）、單次 retrieve 拿到的 chunk 不完整。
- **跟 multi-step retrieval 的差異**：decomposition 是「一次拆成 N 個 query 平行 retrieve」、multi-step 是「retrieve → 看結果 → decide 下一個 query」。前者快、後者貼近資料。
- **失效**：子 query 之間有依賴（後面的 query 要看前面的結果）、平行做不出來、要走 multi-step。

### 何時用哪個

| Query 問題                              | 對應技術                                                         |
| --------------------------------------- | ---------------------------------------------------------------- |
| 用詞跟 document 落差大                  | Query rewriting                                                  |
| Query 太短 / 有歧義                     | [Query expansion](/llm/knowledge-cards/query-expansion/)         |
| Query-document 形態落差（問句 vs 陳述） | HyDE                                                             |
| 複合問題、子問題彼此獨立                | [Query decomposition](/llm/knowledge-cards/query-decomposition/) |
| 子問題彼此依賴                          | Multi-step（下一節）                                             |

實務上 query rewriting 跟 HyDE 是首選——cost 低、改 prompt 即可、收益穩。Expansion 跟 decomposition 在特定 query 形態才有顯著收益、預設不開。

## [Multi-step / Iterative Retrieval](/llm/knowledge-cards/multi-step-retrieval/)

Single-step retrieve 假設「一次 retrieve 拿到所有需要的 chunk」、但多 hop 問題（要從 doc A 找到 entity X、再從 doc B 找 X 的屬性）這個假設不成立。Multi-step retrieval 是 retrieve → LLM 判斷夠不夠 → 不夠就再 retrieve、靠 LLM 的判斷決定 retrieve 路徑。

機制：

```text
Initial query
   ↓
Retrieve round 1 → top-k chunks
   ↓
LLM：「這些 chunks 夠回答嗎？若不夠、下一個該 retrieve 什麼？」
   ↓ (不夠)
Generate sub-query 2
   ↓
Retrieve round 2 → top-k chunks
   ↓
LLM 判斷
   ↓ (夠)
Final answer
```

跟 vanilla single-step 的差異：

- **靈活**：retrieve 路徑是 query-dependent、不是固定。
- **昂貴**：每 round 加一個 LLM call + retrieve、latency 跟 cost 線性疊加。
- **失敗模式**：LLM 判斷「不夠」的能力差、無限 retrieve；或判斷「夠了」太樂觀、缺資訊還是答。

對應 [4.4 agent 架構](/llm/04-applications/agent-architecture/) 的失敗模式分類：multi-step retrieval 是 agent loop 的特例、context drift / goal drift 一樣會發生。

### Multi-hop 推理的核心模式

Multi-hop 問題的典型 pattern：「A 跟 B 有什麼共同點」、需要先 retrieve A 的屬性、再 retrieve B 的屬性、再 compare。Single-step retrieve 不會自動把這兩組 chunk 都抓回來。

Multi-step retrieval 在這類問題上的 accuracy 提升明顯、但 trade-off 是 latency 翻倍以上、cost 翻倍以上。

### Multi-step 划算的三條件

三條件全滿足才走 multi-step、任一不滿足就停在 single-step：

- **問題確實 multi-hop**：需要 retrieve A → 推 X → retrieve B 的形態。Single-hop 問題硬套 multi-step 純增加 cost。
- **Latency budget 允許**：每 round 加 1-2 秒、即時 chatbot 場景通常不容許、batch 場景才行。
- **有客觀停止訊號**：可用 deterministic check 判斷「夠了」、不是純靠 LLM 自評。沒有停止訊號容易無限 loop。

## [Context packing](/llm/knowledge-cards/context-packing/)：retrieve 拿到後怎麼塞進 prompt

Retrieve 拿到 top-k chunks 後、怎麼塞進 prompt 不是「直接 concat」這麼簡單。Context 組裝端的決策影響最終 accuracy 跟 cost。

### Dedup

不同 chunk 可能涵蓋同樣內容（同段文字被多個版本切到、或不同 doc 引用同一個事實）。直接 concat 浪費 context budget。

- **實作**：semantic dedup（embedding 距離小於 threshold 視為重複）、或字面 dedup（hash 比對）。
- **失敗**：dedup 太激進、誤殺有用 chunk；dedup 不夠、context 塞重複內容。

### Ordering

塞進 prompt 的 chunk 順序影響 LLM 注意力。LLM 對 context 開頭跟結尾的注意力比中間強（[lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/) 現象、深度討論見 [4.11 long context engineering](/llm/04-applications/long-context-engineering/)）。

- **策略一：relevance ordering**：最相關的 chunk 放最前 / 最後、不重要的放中間。Trade-off：依賴 retrieval 的 ranking 準。
- **策略二：document order**：按原文順序排（同一 doc 的 chunk 連起來）。Trade-off：保留邏輯流、但相關性散落。
- **策略三：mixed**：top-3 放最前、top-4 到 top-K 按 document order 放後面。

### Summarization / compression

Retrieve 拿到的 chunk 太多、塞不進 context。兩條路：

- **Summarization**：用 LLM 把 chunks 摘要成更短的版本、再餵主 LLM。
- **Compression**：用較小模型抽出 chunks 中跟 query 相關的句子、丟掉無關部分。

Trade-off：

| 路線                 | 收益                       | 代價                                     |
| -------------------- | -------------------------- | ---------------------------------------- |
| Summarization        | Context 大幅縮、保留意義   | 多一個 LLM call、可能漏細節              |
| Compression          | 保留原文片段、可 traceable | 抽錯關鍵句、漏關鍵資訊                   |
| Naïve concat（全塞） | 實作最簡、不漏資訊         | Token cost 高、lost-in-the-middle 風險高 |

### [Source attribution](/llm/knowledge-cards/retrieval-source/)

Retrieve 拿到的 chunk 進 prompt 時、要不要標來源，是 retrieval source 的追溯責任問題。

- **標**：LLM 可以引用、提升可信度、user 可以 verify。Cost：每 chunk 加幾十 token。
- **不標**：context 短、但 LLM 沒法引用、user 沒法追溯。

實務多半標、特別是法律 / 醫療 / 學術場景。

## 控制流端：要不要 retrieve

Vanilla RAG 對每個 query 都 retrieve、不問該不該。實務上有些 query 不需要外部資料（「現在幾點」「2+2 等於多少」「翻譯這段文字」）、強制 retrieve 反而塞無關 chunk 干擾，也會浪費 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)。

### [Adaptive retrieval](/llm/knowledge-cards/adaptive-retrieval/)

讓 LLM 自己決定 retrieve 與否。

- **路線一：predict-then-retrieve**：先用小模型 / 規則判斷 query 類型（factual / reasoning / chitchat）、factual 才 retrieve。
- **路線二：self-RAG**：LLM 在生成過程中、輸出特殊 token 「我需要 retrieve」、觸發 retrieve、整合結果繼續生成。需要訓練過或 prompt engineered 的模型支援。

判讀 adaptive retrieval 是否有用：

- Query 分佈：若 80% query 都需要 retrieve、adaptive 收益小、固定 retrieve 就好。
- Query 分佈：若 query 一半 chitchat 一半 factual、adaptive 減半 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)、收益大。

### Confidence-based retrieval

LLM 先嘗試直接答、若 confidence 低（self-report 或 logits 機率）、再 retrieve。

- **適用**：模型對部分 query 有把握、部分沒、想省 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)。
- **失敗**：模型過度自信、low-confidence 訊號不準、該 retrieve 沒 retrieve。

## 失敗模式：增強堆疊出反效果

不同層的增強可以堆、但堆過頭會反效果：

- **Query rewriting + HyDE + expansion 全開**：query 端 noise 過多、retrieve 結果稀釋、accuracy 反降。
- **Multi-step + reranker + summarization 全開**：每 round latency 累積到使用者不能忍受。
- **Adaptive + multi-step 混亂**：adaptive 說「不 retrieve」、但 multi-step 又觸發 retrieve、控制流互打。

設計反射動作：先確認 vanilla RAG（hybrid + reranker）的失敗在哪一層、針對性加一個增強、看是否有收益、有再加下一個。**不要四層全套**。

## 跟相鄰章節的邊界

- **vs [4.1 RAG 原理](/llm/04-applications/rag-principles/)**：4.1 寫 vanilla 骨架跟 production 兩段式（hybrid + reranker），這章寫進一步增強。
- **vs [4.11 long context engineering](/llm/04-applications/long-context-engineering/)**：long context 是「context 大到能塞」、RAG 是「context 不夠要 retrieve」、兩者是不同 regime 的策略。本章 [context packing](/llm/knowledge-cards/context-packing/) 段的 lost-in-the-middle 是兩個 regime 的共通議題。
- **vs [4.7 workflow patterns](/llm/04-applications/workflow-patterns/)**：multi-step retrieval 是 workflow pattern 在 RAG 場景的特例。

## 何時過時 / 何時不過時

**不會過時的部分**：

- 四層增強分類（query / retrieval / context 組裝 / 控制流）的座標。
- 各 query 端技術解的核心問題（用詞落差 / 歧義 / 形態落差 / 複合問題）。
- Multi-step retrieval 跟 single-step 的 trade-off 結構。
- Context 組裝的三個議題（dedup / ordering / compression）。
- 「先 vanilla、再針對失敗加增強」的設計反射。

**會變的部分**：

- HyDE 等特定方法的最佳實作（隨 embedding 模型演化、效果會變）。
- Self-RAG 等需要訓練的方法（隨 base model alignment 訓練成熟、可能變預設能力）。
- 各家 reranker 跟 embedding 模型的選型（半年一個世代）。

## 小結

Vanilla RAG 不夠時、增強分四層：query 端（rewriting / expansion / HyDE / decomposition）、retrieval 端（multi-step）、context 組裝端（dedup / ordering / summarization）、控制流端（adaptive retrieval）。每層解不同問題、各有 [retrieval cost](/llm/knowledge-cards/retrieval-cost/) / latency / accuracy trade-off。設計反射動作是「先 vanilla 兩段式、找出失敗在哪一層、針對性加一個增強」、不是預設四層全套。Multi-step retrieval 是 agent loop 的特例、失敗模式跟 agent 共通。

下一章：[4.3 Tool use 原理](/llm/04-applications/tool-use-principles/)、從「LLM 讀外部資料」延伸到「LLM 對外部世界做事」。Vanilla RAG 的骨架見 [4.1](/llm/04-applications/rag-principles/)、long context 跟 RAG 的取捨見 [4.11](/llm/04-applications/long-context-engineering/)、multi-step 跟 reflection 的失敗模式比對見 [4.7](/llm/04-applications/workflow-patterns/)。
