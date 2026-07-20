---
title: "Vocabulary Size"
date: 2026-05-12
description: "tokenizer 詞彙表的 token 總數、影響 embedding 大小、tokenization 粒度、多語言友善度"
weight: 1
tags: ["llm", "knowledge-cards", "tokenization"]
---

Vocabulary size（詞彙表大小）的核心概念是「**tokenizer 詞彙表中 token 的總數**」。是模型訓練時就決定的 hyperparameter、後續不能改。Vocabulary size 影響 [embedding layer](/llm/knowledge-cards/embedding-layer/) 大小、單一文字對應的 [token](/llm/knowledge-cards/token/) 數、多語言處理品質。

## 概念位置

主流 LLM 的 vocab size 演化：

| 模型        | Vocab size | 設計考量                                   |
| ----------- | ---------- | ------------------------------------------ |
| GPT-2       | 50,257     | 早期 byte-level BPE、英文為主              |
| Llama 1 / 2 | 32,000     | 緊湊、英文 + 部分多語言                    |
| Llama 3     | 128,256    | 大幅擴張、改善多語言（特別是非拉丁語系）   |
| Gemma 4     | 256,000    | 進一步擴大、強化多語言 + code tokenization |
| Qwen3       | 151,936    | 中文 + 多語言友善                          |
| DeepSeek-V3 | 129,280    | 中英 + code、跟 Llama 3 同量級             |

Vocabulary size 的取捨：

| Vocab 小（如 32K）                  | Vocab 大（如 256K）                        |
| ----------------------------------- | ------------------------------------------ |
| Embedding 矩陣小、模型參數少        | Embedding 矩陣大、模型參數多               |
| 罕見字 / 多語言被拆很細、token 數多 | 高頻多語言整詞當一 token、token 數少       |
| 推論計算每步輸出 softmax 較快       | 每步 softmax 較慢（vocab × hidden 矩陣大） |
| API 計費 token 數量較多             | API 計費 token 數量較少                    |

範例：同段中文「你好、世界」、Llama 1 (vocab 32K) 約 6 token、Gemma 4 (vocab 256K) 約 2-3 token、差距不小。多數模型的 vocab 透過 [BPE](/llm/knowledge-cards/bpe/) 或其變體訓練決定。

## 設計責任

讀 model card 看到 `vocab_size` 就是這個值。寫 code 場景的判讀：跑同個 prompt、不同模型實際處理的 token 數差很多、影響 [context window](/llm/knowledge-cards/context-window/) 利用率跟雲端 API 計費；換 tokenizer = 換 vocab = 整個 [embedding layer](/llm/knowledge-cards/embedding-layer/) 失效、所以 fine-tune 通常不動 tokenizer、想增加新語言的最簡單方式是 extend embedding（加新 row 不動既有 row、再 fine-tune）。
