---
title: "3.6 Tokenization：BPE、SentencePiece、Tiktoken"
date: 2026-05-11
description: "把文字切成 token 的算法：為什麼不同模型切出不同 token 數、tokenizer 選擇對能力的影響"
tags: ["llm", "theory", "tokenization"]
weight: 6
---

[Tokenization](/llm/knowledge-cards/token/) 是把文字切成模型可處理的 token 序列的過程。看似簡單的「切字」實際上有完整算法、且 tokenizer 的選擇深刻影響模型能力、context window 利用率、跨語言表現、跟一些奇怪 bug 的成因（GPT 在某些字串上表現異常的「glitch tokens」就源於 tokenizer 設計）。

本章拆開三個主流 tokenization 算法（BPE、WordPiece、SentencePiece）、解釋 vocabulary 怎麼學出來、為什麼中文 / 中日韓字幾乎一字一 token、tokenizer 為什麼影響 [speculative decoding](/llm/knowledge-cards/speculative-decoding/) 的相容性。

## 本章目標

讀完本章後、你應該能：

1. 解釋 BPE（Byte-Pair Encoding）的工作原理。
2. 看到不同 model 切同段文字得到不同 token 數時、知道原因。
3. 解釋為什麼 [drafter](/llm/knowledge-cards/drafter-model/) 跟 target 必須共用 tokenizer。
4. 看到 vocab_size = 256,000 vs 128,256 時、知道差異在哪。

## Tokenization 的設計目標

理想 tokenizer 要同時滿足：

1. **覆蓋率高**：能 encode 任何文字、不會「碰到沒見過的字壞掉」。
2. **效率高**：常見字串切成少數 token、節省 context 與計算。
3. **語意保留**：保留有意義的 sub-word 邊界（「unhappy」切成 `un` + `happy` 比 `unh` + `appy` 好）。
4. **跨語言公平**：英文跟中文 / 日文 / 阿拉伯文等都用合理數量的 token。

不同算法在這四個目標上有不同取捨。

## 早期方法：word-level 跟 char-level

### Word-level Tokenization

最簡單的方法是「用空白跟標點切」、每個 word 一個 token。

優點：直觀。

缺點：

1. Vocabulary 爆炸：英文有幾百萬個 word forms（含複數、時態、複合詞等）。
2. OOV（out-of-vocabulary）：新詞、typo、URL、混合語言完全壞掉。
3. 中文 / 日文沒有空白：要先做 word segmentation。

現代 LLM 不用 word-level。

### Char-level Tokenization

另一個極端是「每個 character 一個 token」。

優點：vocabulary 小、無 OOV。

缺點：序列變很長（一句話幾十到幾百 char、效率低）、模型要從很基礎學起、訓練不效率。

現代 LLM 也不直接用 char-level。

### 折衷：Subword Tokenization

主流方案是「subword tokenization」：常見字串當一個 token、罕見字串切成更小單位（甚至到 char 級別）。三個主流算法：

| 算法          | 模型例子                        |
| ------------- | ------------------------------- |
| BPE           | GPT-2、GPT-3、GPT-4、Llama 系列 |
| WordPiece     | BERT                            |
| SentencePiece | Gemma、PaLM、T5                 |

## BPE：Byte-Pair Encoding

BPE（Sennrich et al., 2016）的核心想法是「貪婪地合併最常出現的字元對」、迭代到 vocabulary 達到目標大小。

### 訓練流程

1. 初始 vocabulary：所有 character。
2. 統計訓練語料中、所有相鄰 character pair 的頻率。
3. 把頻率最高的 pair 合併成一個新 token、加進 vocabulary。
4. 用新 vocabulary 重新 tokenize 語料、重複 step 2-3。
5. 直到 vocabulary 達到目標大小（如 50,000、100,000）。

例：

```text
初始：l o w e r → 5 個 token
步驟 1：合併 'l' + 'o' = 'lo'、變成 lo w e r → 4 個 token
步驟 2：合併 'lo' + 'w' = 'low'、變成 low e r → 3 個 token
步驟 3：合併 'e' + 'r' = 'er'、變成 low er → 2 個 token
```

訓練後、`lower` 就是 2 個 token。

### Byte-level BPE

原始 BPE 在 character level 運作、但「character」依語言而異（Unicode 字元複雜）。Byte-level BPE 在 byte level 運作、任何文字都可以 encode 成 byte 序列、自然支援多語言。

GPT-2 / GPT-3 / GPT-4 / Llama 系列都用 byte-level BPE。

### Tiktoken：OpenAI 的高效實作

Tiktoken 是 OpenAI 開源的 BPE 高效實作、Python 套件。可以拿來算「這段文字在 GPT-4 上是多少 token」：

```python
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4")
tokens = enc.encode("Hello, world!")
print(len(tokens))   # 4
```

Tiktoken 是估算 OpenAI API 費用的標準工具。其他模型有各自的 tokenizer 套件（Llama 的 sentencepiece、Hugging Face 的 transformers.AutoTokenizer）。

## WordPiece：BERT 的選擇

WordPiece（Schuster & Nakajima, 2012、後來 Google 用在 BERT）跟 BPE 類似、但合併策略不同：

- BPE：合併「最頻繁出現的 pair」。
- WordPiece：合併「合併後 likelihood 最大化的 pair」（更貴的計算、但理論上更好）。

實務差異微小。BERT 系列用 WordPiece、現代 LLM 大多回到 BPE 系列。

## SentencePiece：Google 的開源實作

SentencePiece（Kudo & Richardson, 2018）是 Google 開源的 tokenization 套件、可實作 BPE 或 unigram 算法、設計上：

- **語言無關**：把輸入當 byte 流處理、不假設「word boundary 是空白」。
- **無前處理**：不用先切 word、適合中文 / 日文等無空白語言。
- **可逆**：tokenize → detokenize 完全還原原文。

Gemma 系列、PaLM、T5 用 SentencePiece。實務上跟 BPE 表現接近、差異主要在「對中日韓文等無空白語言更友善」。

## Vocabulary 大小

各 LLM 的 vocabulary 大小：

| 模型          | vocab_size | Tokenizer                 |
| ------------- | ---------- | ------------------------- |
| GPT-2         | 50,257     | byte-level BPE            |
| GPT-3 / GPT-4 | ~100K      | byte-level BPE (tiktoken) |
| Llama 2       | 32,000     | SentencePiece             |
| Llama 3       | 128,256    | tiktoken-style BPE        |
| Gemma 2       | 256,000    | SentencePiece             |
| Gemma 3       | 262,144    | SentencePiece             |
| Gemma 4       | 256,000    | SentencePiece             |
| Qwen3         | 152,064    | byte-level BPE            |

Vocabulary 大小的取捨：

| 大 vocab                                    | 小 vocab                                |
| ------------------------------------------- | --------------------------------------- |
| 同段文字切出 token 數少（context 利用率高） | 同段文字切出 token 數多（context 吃緊） |
| Embedding layer 跟 output projection 大     | Embedding 跟 output projection 小       |
| 多語言覆蓋好                                | 多語言覆蓋差、可能切成 byte 級          |
| 中文 / 日文每字一 token                     | 中文 / 日文一字可能切 2 ~ 3 個 token    |

Gemma 4 的 256K vocab 是現代 LLM 中較大的、目的之一是多語言支援。

## 同段文字在不同 tokenizer 上的差異

實測「The quick brown fox jumps over the lazy dog」：

| Tokenizer | Token 數 |
| --------- | -------- |
| GPT-4     | 9        |
| Llama 3   | 9        |
| Gemma 4   | 11       |
| Qwen3     | 10       |

差異不大。但中文「敏捷的棕色狐狸跳過懶狗」：

| Tokenizer | Token 數（估）  |
| --------- | --------------- |
| GPT-4     | 約 12           |
| Llama 2   | 約 20 (byte 級) |
| Llama 3   | 約 10           |
| Gemma 4   | 約 9            |

Llama 2 的 32K vocab 對中文支援差、Llama 3 / Gemma 4 改善很多。實務影響：中文 prompt 在 Llama 2 上吃 context 多、Gemma 4 較友善。

## Tokenizer 跟模型相容性

[Speculative decoding](/llm/knowledge-cards/speculative-decoding/) 要 target 跟 [drafter](/llm/knowledge-cards/drafter-model/) 共用 tokenizer、因為兩者必須對「下個 token」的概念一致：

- Gemma 4 31B + Gemma 4 E4B：同 tokenizer、可以配對。
- Gemma 4 + Llama：不同 tokenizer、配不起來。

理解這點、能解釋為什麼 LM Studio 的 draft model UI 自動過濾相容候選、為什麼 Ollama 的 `gemma4:31b-coding-mtp-bf16` model tag 內含 drafter 而不能自己組合不同家族。

## Special Tokens

除了 vocabulary 中的「正常」token、還有特殊 token：

| Special Token     | 用途                               |        |        |        |                           |     |                |
| ----------------- | ---------------------------------- | ------ | ------ | ------ | ------------------------- | --- | -------------- |
| `<BOS>` / `<bos>` | Beginning of sequence、prompt 起點 |        |        |        |                           |     |                |
| `<EOS>` / `<eos>` | End of sequence、生成結束          |        |        |        |                           |     |                |
| `<PAD>`           | Padding、batch 訓練時補齊長度      |        |        |        |                           |     |                |
| `<UNK>`           | Unknown token（現代 BPE 少用）     |        |        |        |                           |     |                |
| `<                | im_start                           | >`、`< | im_end | >`     | Chat template 中區隔 role |     |                |
| `<                | system                             | >`、`< | user   | >`、`< | assistant                 | >`  | Chat role 標記 |

聊天 LLM 的 prompt 實際長相不是純文字、而是用 special tokens 標記 role 跟訊息邊界：

```text
<|im_start|>system
You are a helpful assistant.<|im_end|>
<|im_start|>user
Hello!<|im_end|>
<|im_start|>assistant
```

不同模型的 chat template 不同、Ollama / Continue.dev 等工具自動處理、但若自己呼叫 API 要注意 template 對不對。

## Tokenization 引發的 bug

Tokenizer 設計的副作用：

### Glitch Tokens

某些 token 在訓練資料中很少出現、模型對它們的行為怪異。Reddit 上著名的 `SolidGoldMagikarp` 就是 GPT-2 / GPT-3 的 glitch token、模型遇到會出現奇怪反應。原因：tokenizer 學了這個 token、但訓練資料中幾乎沒上下文、模型沒學到它的語意。

### 數字 tokenization

早期 BPE 對數字的處理不一致：`1234` 可能切成 `123` + `4`、`1235` 可能切成 `12` + `35`。模型對「數字加法」表現差跟這個有關。

現代 LLM 多半把每個 digit 各自當一個 token（一致 tokenization）、改善數學能力。

### Code 的 indentation

寫 code 場景的 tokenizer 要妥善處理 indentation。早期 LLM 把多個空白合併成一個 token、code 結構壞掉；現代 LLM（特別是 coding-specialized）把 4 空白 / 8 空白等常見 indentation 各自當一個 token。

## 跟 context window 的關係

[Context window](/llm/knowledge-cards/context-window/) 的單位是 token、不是字。1M token 的 context window 在英文約等於 750K 字、在中文約 1M 字（看 tokenizer）。

實務啟示：

- 「128K context」在不同 tokenizer 上實際容量不同。
- 計算 API 費用要用該模型的 tokenizer 算 token 數。
- 中文 prompt 用 Llama 2 比 Llama 3 / Gemma 4 吃 context 多。

## 小結

Tokenization 是把文字切成模型可處理的 token 序列、主流算法是 byte-level BPE 跟 SentencePiece。Vocabulary 大小決定 context 利用效率與跨語言支援。Tokenizer 是 model identity 的一部分、影響 speculative decoding 配對、chat template 解析、glitch token 行為。同段文字在不同 tokenizer 上的 token 數可能差 2 倍、影響 API 費用與 context window 利用。

下一章：[3.7 想學更深：推薦公開課程](/llm/03-theoretical-foundations/going-deeper-theory/)。
