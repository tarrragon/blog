---
title: "3.10 Constrained decoding 內部：grammar mask 跟性能取捨"
date: 2026-05-12
description: "Constrained decoding 的內部運作：token mask 計算、JSON schema / regex / CFG 三種 grammar、XGrammar pre-compile 機制、性能反而加速"
tags: ["llm", "theory", "sampling", "constrained-decoding", "structured-output"]
weight: 10
---

[3.5 sampling-and-decoding](/llm/03-theoretical-foundations/sampling-and-decoding/) 寫了 greedy / beam / top-p / top-k sampling、是「在合法輸出中選下一個 token」的基本機制。[4.3 application-protocols](/llm/04-applications/application-protocols/) 寫了 function calling / structured output 的應用層 — 但「為什麼 LLM 能保證輸出合法 JSON」這層原理在前兩章都沒展開。本章補 [constrained decoding](/llm/knowledge-cards/constrained-decoding/) 的內部機制：token mask 怎麼算、JSON schema / regex / CFG 三種 grammar、為什麼 XGrammar 等實作反而加速生成。

## 本章目標

讀完本章後、你應該能：

1. 解釋「grammar 強制」是在 sampling 階段哪一步做的。
2. 區分 JSON schema / regex / CFG 三種 grammar 的適用場景。
3. 看 XGrammar / outlines / llama.cpp grammar 等實作、能對應到本章 framing。
4. 判讀「constrained decoding 加速還是拖慢」的具體場景。

## Sampling 階段的位置

回顧 LLM 輸出流程（見 [3.5](/llm/03-theoretical-foundations/sampling-and-decoding/)）：

```text
[forward pass] → logits（vocab_size 維、每個 token 一個實數）
       ↓ apply temperature（logits / T）
       ↓ apply constrained decoding（本章聚焦）  ← grammar mask
       ↓ softmax → probability distribution
       ↓ top-p / top-k / sampling
       ↓ next token
```

Constrained decoding 在 softmax **之前**插入 grammar mask：

```text
For each position：
  1. Grammar 算當前位置的「合法 token 集合」（vocab 子集）
  2. 對不在合法集的 token、logit 設 -∞
  3. Softmax 後、不合法 token 機率為 0
  4. Sampling 只可能選到合法 token
```

關鍵理解：grammar 不改變模型本身、不改變 logits 數值（除了 mask 部分）、只是**限制 sampling 空間**。

## 三種主流 grammar

### JSON Schema

```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer", "minimum": 0}
  },
  "required": ["name"]
}
```

LLM 輸出必須是合法 JSON 且符合 schema。實作：

```text
當前已生：'{"name": "alice", '
  ↓ 算下一個合法 token：
  - 必須繼續產合法 JSON
  - schema 還沒填 age（optional）但 name 已填、所以 } 合法、"age" 也合法
  - 不合法：'{' / ']' / 任意其他 key
  ↓ Token mask 套用
  → 模型只能選 } 或 "age"
```

### Regex

```text
\d{3}-\d{4}-\d{4}  # 台灣 phone number 格式
```

LLM 輸出必須符合 regex。實作：

```text
當前已生：'09'
  ↓ 算下一個合法 token：
  - regex 期望 \d 接下來
  - 合法 token：'0'-'9' 開頭的 token
  - 不合法：字母、符號
  ↓ Token mask
```

### CFG（Context-Free Grammar）

用 BNF / EBNF 描述合法語法：

```text
expr   ::= term ("+" term)*
term   ::= number | "(" expr ")"
number ::= [0-9]+
```

LLM 輸出必須符合此 grammar。實作：

```text
當前已生：'(1+2'
  ↓ CFG 算當下合法 next token：
  - 已 match 部分 term + "+" + term
  - 合法：")" 或 "+" 開始新 term
  - 不合法：字母、其他符號
  ↓ Token mask
```

CFG 是最強表達力、但實作最複雜。SQL / 程式碼 generation 多用 CFG-based grammar。

## XGrammar 的 pre-compile 機制

XGrammar（Dong et al., 2024）是 2024-2025 主流的高效實作。核心優化：

```text
Naive 實作（如 outlines 早期版）：
  每次 sampling 都重算 grammar state
  每個 token 都跑一次 grammar parse
  → 開銷大、可能拖慢 generation

XGrammar 優化：
  1. Pre-compile grammar → 確定性 DFA / push-down automaton
  2. Cache 每個 grammar state 的「合法 token mask bitmap」
  3. Sampling 時 O(1) 查表得到 mask
  4. Mask 用 bitwise op 套用到 logits
```

效果：grammar 套用 overhead 趨近 0、甚至**因為跳過 boilerplate token 反而加速**：

```text
無 grammar 生 JSON：
  {     " n a m e "     : " a l i c e " ...
  ←     每個 token 都跑 forward pass    →

有 grammar 生 JSON：
  跳過固定 token（{ " : 等）、直接生關鍵字串
  forward pass 次數減少
  → 實測加速 1.5-3×
```

主流推論伺服器（vLLM、SGLang、TensorRT-LLM）2025 後預設用 XGrammar。

## 性能取捨：加速還是拖慢

常見誤解：「constrained decoding 拖慢生成」。實際看實作：

| 實作                     | 性能                                                   |
| ------------------------ | ------------------------------------------------------ |
| XGrammar（vLLM 等預設）  | **加速 1.5-3×**（跳過固定 token、forward pass 次數減） |
| outlines（pre-compiled） | 略加速到中性                                           |
| outlines（lazy compile） | 略拖慢                                                 |
| guidance（高階 API）     | 中性到略拖慢                                           |
| llama.cpp grammar        | 中性                                                   |
| Lazy / naive 實作        | 拖慢                                                   |

判讀：用主流推論伺服器（vLLM / SGLang）+ XGrammar 路線、constrained decoding 通常加速；自己寫 naive 實作可能拖慢。

## 跟 [function calling](/llm/knowledge-cards/function-calling/) 的關係

兩個概念可獨立、也可疊用：

| 路線                                                  | 機制                                               |
| ----------------------------------------------------- | -------------------------------------------------- |
| Pure function calling（無 constrained decoding）      | 靠模型訓練、不強制合法、可能有解析失敗             |
| Pure constrained decoding（無 function calling 訓練） | 推論時強制合法、但模型不一定知道「何時該呼叫工具」 |
| Function calling + constrained decoding               | 訓練教模型何時呼叫、grammar 強制呼叫格式合法       |

主流商業 API（Anthropic / OpenAI / Gemini）的 function calling 通常**內部已用 constrained decoding**、開發者無感。本地推論用 vLLM / SGLang + XGrammar 也是預設組合。

## 失敗模式

### 1. Grammar 太嚴讓模型「該說的話說不出來」

```text
Schema 強制 type 是 enum ["A", "B", "C"]
但真實答案是「none of the above」
→ 模型強制選 A/B/C、輸出語義錯誤
```

**緩解**：enum 加 fallback option（"unknown" / "none"）、schema 別過度約束

### 2. CFG 太複雜、編譯失敗 / 慢

```text
復雜 CFG（如完整 SQL grammar）pre-compile 數秒
production cold start 多花這數秒
```

**緩解**：cache compiled grammar、用較簡單 grammar 版本（如「INSERT only」而非完整 SQL）

### 3. Grammar 跟 model 訓練分佈不符

```text
Schema 要求很罕見的 JSON 結構
模型訓練沒見過這結構
即使 grammar 強制合法、語義可能空洞
```

**緩解**：grammar 用模型訓練過的形態（function call spec、common JSON）、自定義 schema 加 few-shot example

### 4. Streaming 跟 grammar 衝突

```text
Streaming 邊生邊輸出
Grammar 中段 token 可能要 backtrack 修正
streaming UX 跳字
```

**緩解**：用 incremental-parsing grammar（XGrammar 支援）、避免 backtrack 場景

### 5. Constrained decoding 蓋過 function calling 訓練

```text
模型訓練用 OpenAI function spec、應用強制套 Anthropic tools 的 grammar
模型輸出「合法但語意空洞」（schema 對、欄位胡亂填）
```

**緩解**：grammar spec 跟模型訓練 spec 一致、別人工維護兩份不同 schema

## 何時不該用 constrained decoding

1. **自由 / 創意輸出**：寫作、brainstorming、grammar 限制模型表達
2. **可靠的 model + simple format**：模型本身能穩定輸出 JSON、grammar overhead 不必要
3. **Grammar 太嚴有語義錯**：見失敗模式 1
4. **Streaming + 複雜 grammar**：streaming UX 受影響

## 主流實作詳細

| 實作                          | 適合場景                                               |
| ----------------------------- | ------------------------------------------------------ |
| **XGrammar**                  | Production 高吞吐（vLLM / SGLang / TensorRT-LLM 預設） |
| **outlines**                  | Python script、開發 / 實驗、HF Transformers 用         |
| **lm-format-enforcer**        | 動態 grammar、運行時切 schema                          |
| **guidance**                  | Microsoft 系、想要 high-level API                      |
| **llama.cpp grammar**         | 本地 GGUF 模型、GBNF 語法                              |
| **OpenAI Structured Outputs** | OpenAI API、JSON schema、開發者無感                    |
| **Anthropic JSON mode**       | Anthropic API、簡化版                                  |

## 何時過時 / 何時不過時

**不會過時的部分**：

- Constrained decoding 在 sampling 哪一步插入（softmax 之前）的 framing
- 三種 grammar 類型（JSON schema / regex / CFG）的分類
- Token mask 機制（不合法 token logit 設 -∞）
- 「正確實作下加速、不是拖慢」的反直覺結論
- 5 大失敗模式分類

**會變的部分**：

- XGrammar / outlines 等實作的具體效能跟功能
- 主流推論伺服器的預設 grammar engine
- JSON schema spec 標準化（新版會出）
- Function calling + constrained decoding 是否會被 native multimodal 取代

## 小結

Constrained decoding 在 sampling 階段（softmax 之前）用 grammar 算合法 token mask、把不合法 token 機率歸零。三種 grammar：JSON schema（最常見、function calling 用）、regex（受限文字格式）、CFG（最強表達力、SQL / code）。XGrammar 等 pre-compile 實作把 overhead 趨近 0、跳過 boilerplate token 反而**加速** 1.5-3×。跟 function calling 是獨立但常疊用的兩條軸：function calling 是訓練、constrained decoding 是推論。失敗模式以「grammar 太嚴」「grammar 跟訓練分佈不符」為主。

下一章：[3.11 想學更深](/llm/03-theoretical-foundations/going-deeper-theory/)、整個模組三理論基礎走完。
