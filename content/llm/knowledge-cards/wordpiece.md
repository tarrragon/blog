---
title: "WordPiece"
date: 2026-05-14
description: "以 likelihood improvement 選擇子詞合併的 tokenizer 演算法，BERT 系列代表性使用"
weight: 1
tags: ["llm", "knowledge-cards", "tokenization"]
---

WordPiece 的核心概念是「**用語料 likelihood 改善量選擇子詞合併的 tokenization 演算法**」。它跟 [BPE](/llm/knowledge-cards/bpe/) 一樣把文字拆成 subword，但選擇 merge 的準則不同。

## 概念位置

WordPiece 屬於 subword tokenizer 家族，BERT 系列是代表。BPE 偏向合併高頻相鄰片段；WordPiece 偏向選擇能最大化語言模型 likelihood 的片段；[SentencePiece](/llm/knowledge-cards/sentencepiece/) 則是 tokenizer framework，可支援 BPE 或 unigram。

## 可觀察訊號與例子

看到 `##ing`、`##ed` 這類 continuation marker，通常是 WordPiece 風格 vocabulary。它讓模型能處理未見過的詞，因為陌生詞仍可拆成已知 subword。

## 設計責任

比較 tokenizer 時，WordPiece 主要作為 BERT/encoder 系統的背景知識。寫 LLM 推論與本地 serving 時更常遇到 BPE、SentencePiece、vocab size 與 special tokens。
