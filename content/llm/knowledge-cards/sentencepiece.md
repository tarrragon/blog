---
title: "SentencePiece"
date: 2026-05-12
description: "Google 開源的多語言 tokenization 框架、支援 BPE 跟 unigram 演算法、處理空白統一"
weight: 1
tags: ["llm", "knowledge-cards", "tokenization"]
---

SentencePiece（Kudo & Richardson, 2018）的核心概念是「**Google 開源的 tokenization 框架、把『空白也當一個字元』處理、原生支援 [BPE](/llm/knowledge-cards/bpe/) 跟 unigram 兩種演算法**」。Llama、Gemma、Mistral、T5 等模型用 SentencePiece 作為 tokenizer 實作；它的 multilingual 友善度跟「不依賴語言預處理」是被選擇的主因。

## 概念位置

SentencePiece 跟其他 tokenization 路線的對比：

| 框架 / 路線                                  | 機制                                            | 處理多語言 / 空白                | 出現在                |
| -------------------------------------------- | ----------------------------------------------- | -------------------------------- | --------------------- |
| [WordPiece](/llm/knowledge-cards/wordpiece/) | 類似 BPE、Google 早期方案                       | 需語言預處理（如英文 lowercase） | BERT、DistilBERT      |
| **SentencePiece BPE**                        | BPE 演算法、空白當特殊字符 `▁` 處理             | 統一處理、不需語言預設           | Llama、Gemma、Mistral |
| **SentencePiece Unigram**                    | 機率模型、選一組讓 corpus likelihood 最大的子詞 | 同上、機率視角                   | T5、XLNet、ALBERT     |
| tiktoken（OpenAI）                           | Byte-level BPE                                  | 統一處理                         | GPT-3.5、GPT-4、GPT-5 |

關鍵特性：

1. **`▁` 表示空白**：SentencePiece 把空白編碼成 `▁`（Unicode U+2581）、所以「Hello world」會被 tokenize 成 `["Hello", "▁world"]`、保留空白資訊在 token 內。
2. **不依賴語言預處理**：傳統 NLP 要先做 lowercasing、word segmentation；SentencePiece 直接從 raw bytes 開始學、跨語言通用。
3. **原生 multilingual**：訓練 corpus 包含多語言時、tokenizer 自動學會跨語言的子詞單元、不需要為每種語言設定不同 tokenizer。

## 設計責任

讀 model card / repo 看到 `tokenizer.model` 檔案（不是 `tokenizer.json` 或 `vocab.txt`）就是 SentencePiece 用的 protobuf 格式。寫 code 場景的意涵：SentencePiece tokenizer 在中文 / 多語言任務上比 WordPiece 友好；換 tokenizer 等於整個 [embedding layer](/llm/knowledge-cards/embedding-layer/) 失效、所以 fine-tune 時不會動 tokenizer。
