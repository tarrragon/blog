---
title: "4.11 Long context engineering"
date: 2026-05-12
description: "128K / 1M context 模型怎麼用：claimed vs effective context、lost-in-the-middle、context 設計策略、Long context vs RAG 取捨"
tags: ["llm", "applications", "long-context", "rag"]
weight: 11
---

長 [context window](/llm/knowledge-cards/context-window/) 模型（128K、1M、甚至更長）在 2024-2026 變成主流標配。但「聲稱 context」跟「實用 effective context」之間有顯著落差、不理解這條鴻溝會讓 long context 變成資源浪費而非能力延伸。本章把 long context 的實際運作、典型失敗模式、prompt 設計策略、跟 [RAG](/llm/knowledge-cards/rag/) 的取捨拆成可操作的判讀。

## 本章目標

讀完本章後、你應該能：

1. 區分模型「聲稱 context」、「NIH context」、「實用 effective context」三個層級。
2. 看到 [lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/) 症狀時、知道怎麼緩解。
3. 對自己工作流的任務、判斷該用 long context 還是 RAG。
4. 設計 prompt 時、把關鍵資訊放對位置。
5. 評估「升級到更長 context 模型」的實際邊際收益。

## 三層 context 概念：claimed / NIH / effective

讀 model card 看到「128K context」「1M context」時、需要區分：

| 層級              | 定義                                                                                    | 典型數字（128K 模型） |
| ----------------- | --------------------------------------------------------------------------------------- | --------------------- |
| Claimed context   | 模型架構支援的上限（RoPE scaling 配置）                                                 | 128K                  |
| NIH context       | [Needle-in-haystack](/llm/knowledge-cards/needle-in-haystack/) 通過的長度（抓單一事實） | 80K-128K              |
| Effective context | 真實任務（reasoning over context）品質可接受的長度                                      | 8K-32K                |

落差來自：

1. **RoPE scaling 是延伸、不是「免費擴展」**：訓練多在 8K-32K range、用 [RoPE](/llm/knowledge-cards/rope/) scaling 推到 128K+、實用上會 degrade
2. **訓練資料偏短**：trillion-token pretrain corpus 中、極長文件相對稀少、模型對 long context 中段不熟悉
3. **Attention 衰減**：[attention](/llm/knowledge-cards/attention/) 機制對長距離 token 的注意能力隨距離下降、雖未真正 attention to 0、但「有效訊號」減弱

實務啟示：聲稱 1M context 不代表「能塞 1M 進 prompt 解任務」、實用 effective context 多半是聲稱的 1/4-1/8。

## Lost-in-the-middle：long context 的主要失敗模式

[Lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/)（Liu et al., 2023）的核心發現：模型對 long context 中段內容的 recall 顯著低於開頭與結尾。實測：

```text
Recall accuracy vs 答案位置（10K context）：
  位置 0%（開頭）  ：85%+
  位置 25%        ：70%
  位置 50%（中段）：40-55%
  位置 75%        ：65%
  位置 100%（結尾）：80%+
```

成因細節見 [lost-in-the-middle 卡片](/llm/knowledge-cards/lost-in-the-middle/)。本章聚焦緩解：

1. **關鍵資訊放開頭 / 結尾**：system prompt、最新指示放在 prompt 開頭 / 最末段、剛好是 attention 最強的兩處
2. **重要內容重複出現**：在 prompt 開頭跟結尾各放一次摘要、提高 recall
3. **避免在中段藏 deeply nested constraint**：「請遵守附件中第 47 條規則」這類引用、長 context 中段容易被忽略
4. **拆 prompt 成多輪**：把 long context 拆成「load context」+「query」兩輪、第二輪 query 在前一輪結尾、recall 較強

## Long context vs RAG：什麼時候該選哪個

兩者解的問題重疊但**不完全替代**：

| 維度               | Long context                             | [RAG](/llm/knowledge-cards/rag/)                                                |
| ------------------ | ---------------------------------------- | ------------------------------------------------------------------------------- |
| 知識量上限         | Context window（128K-1M token）          | 無上限（向量資料庫可存任意大）                                                  |
| 知識動態更新       | 每次 query 把 context 全塞進去、可變     | Retrieval 階段可隨時更新                                                        |
| 知識來源 traceable | 整段塞、無明確「答案來自哪一段」         | 每個 chunk 有 source、可 cite                                                   |
| Prompt 成本        | 每次 query 都付 full context token 成本  | 只付 retrieved chunks 的 [retrieval cost](/llm/knowledge-cards/retrieval-cost/) |
| 適合場景           | 知識集中、< context window、需要整體理解 | 知識量大、零散、明確 retrieval key                                              |
| 失敗模式           | Lost-in-the-middle、context degradation  | Retrieval miss、chunk 邊界切壞                                                  |

判讀流程：

```text
知識總量 < 你模型的 effective context（見後文表格、典型 7B-14B 約 8-16K、30B+ 約 16-32K）？
  ├─ 是 → 直接 long context
  └─ 否 → 知識結構化、retrieval key 明確？
            ├─ 是 → RAG
            └─ 否 → 嘗試 hybrid：RAG 把相關段 retrieve 出來 + 放進 long context
```

注意「effective context」是你模型實際能 reliable 處理的範圍、不是 model card 上聲稱的 128K — 拿 7B 模型塞 16K 知識仍可能踩 lost-in-the-middle。

混用情境：

1. **Codebase 理解**：codebase 整體用 RAG retrieve、單檔 deep dive 用 long context（讀整個檔案）
2. **文件問答**：文件用 RAG retrieve 相關段、塞進 32K context、模型可看到「retrieve 結果 + 自己的對話歷史」
3. **長對話**：對話歷史進 long context、新指令在最末段（避免 lost-in-the-middle）

## Context 設計策略

具體 prompt 結構建議（適用 long context 場景）：

```text
[1. System prompt 開頭]         ← attention 強、放核心指令
  你的角色 / 主要任務 / 不變的約束

[2. Few-shot examples（若需）]   ← attention 仍強、放示範

[3. 大段 context]                ← 中段、可能 lost-in-the-middle
  - 把最重要的內容也放這段開頭跟結尾、別只放中間
  - 若有多段 context、各段都帶明確 heading

[4. 當前查詢]                    ← attention 強、放使用者問題

[5. 重述關鍵約束（若需）]         ← 末段、attention 強、再次強調 critical rule
```

典型反例（容易踩 lost-in-the-middle）：

```text
[1. 重要約束「使用者付費等級 = premium、回應應該詳細」]
[2. 100K 文件全文]
[3. 「請回答上述文件相關問題」]
```

→ 改成：

```text
[1. 重要約束（同上）]
[2. 文件摘要 + 「以下是完整文件、若需細節請參考」]
[3. 100K 文件全文]
[4. 重述「使用者付費等級 = premium、提供詳細答案」]
[5. 「使用者問題：X」]
```

第二版有兩處可靠出現核心指令、長 context 中段含有完整文件、但模型 recall instruction 時兩處任選一處都行、品質提升。

## Reasoning model + long context 的特殊互動

[Reasoning models](/llm/03-theoretical-foundations/reasoning-models/) 的 reasoning trace 跟 long context 有兩個衝突點：

1. **Reasoning trace 擠 context budget**：1000-10000 token reasoning trace 直接吃進 context、本來 effective 32K 的模型可能只剩 22K 給輸入
2. **Long thinking traces 自己也踩 lost-in-the-middle**：reasoning trace 變長時、reasoning 過程中段也會「忘記前面想到的」

緩解：

1. **Reasoning model 配長 context 模型**：DeepSeek-R1 distill 64K context 是合理 baseline
2. **Reasoning 階段引導模型「定期重述目標」**：prompt 加「請每隔幾步重新確認任務目標」
3. **複雜任務拆步**：別把整個任務丟給 reasoning model 一輪解、拆成多個 sub-task

## 量測自己模型的 effective context

不要相信 model card 上的數字、自己跑：

```bash
# 1. 跑 needle-in-haystack（lower bound、寬鬆指標）
# 用 ggerganov/llama.cpp 或 RULER 工具
# 看模型在 8K / 16K / 32K / 64K / 128K 各自的 NIH accuracy

# 2. 自己工作流的 real-task 評估
# 拿實際的長 prompt（如完整 codebase + 任務）
# 對不同 context 長度比較輸出品質、找到 degradation 點

# 3. lost-in-the-middle 測試
# 同個 prompt 把關鍵指令分別放在開頭、中段、結尾
# 對比模型回答準確度
```

實務上、寫 code 場景的 effective context 通常落在：

| 模型大小                      | 聲稱 context | 實用 effective context（寫 code） |
| ----------------------------- | ------------ | --------------------------------- |
| 7B-14B（如 Qwen3-Coder-14B）  | 32K-128K     | 8K-16K                            |
| 30B-32B（如 Qwen3-Coder-30B） | 64K-128K     | 16K-32K                           |
| 雲端旗艦（Claude / GPT-5）    | 200K-1M      | 64K-200K                          |

## 升級到更長 context 模型的判讀

讀 model card 看到「context 從 128K 提升到 1M」、判斷對自己的價值：

1. **看 RULER benchmark、不只看 NIH**：RULER 有 multi-needle、aggregation、reasoning 等任務、更貼近實用
2. **看 effective context（如 LongBench 數字）**：聲稱 1M 但 effective 64K vs 聲稱 200K 但 effective 100K — 後者更有用
3. **看自己任務真實長度**：如果你的任務 prompt 多在 8K 內、聲稱 128K → 1M 對你無收益
4. **看推論成本**：long context 的 [KV cache](/llm/knowledge-cards/kv-cache/) 跟 prefill 時間都隨長度增加、effective 64K 模型實用上比聲稱 1M 模型更快

## 何時過時 / 何時不過時

**不會過時的部分**：

- Claimed / NIH / Effective context 三層概念
- Lost-in-the-middle 的存在跟基本緩解策略
- Long context vs RAG 的判讀框架
- 「關鍵資訊放開頭結尾」的 prompt 設計原則

**會變的部分**：

- 各模型的聲稱 / effective context 數字（每代會推進）
- Long context 訓練技術（RoPE scaling 變體、long-context fine-tuning 方法會演化）
- Lost-in-the-middle 的減緩進展（可能透過新訓練方法部分解決）
- Benchmark 工具（NIH → RULER → 未來新 benchmark）

## 下一章

下一章：[4.12 Embedding model 內部](/llm/04-applications/embedding-model-internals/)、看 RAG retrieval 階段背後的 embedding 是怎麼運作。
