---
title: "Sampling Constraint"
date: 2026-05-14
description: "推論時限制下一個 token 候選集合的控制手段，用來把模型生成導向合法格式或特定選項"
weight: 1
tags: ["llm", "knowledge-cards", "sampling", "decoding"]
---

Sampling constraint（sampling 約束）的核心概念是「**在模型選下一個 token 時，限制哪些 token 可以被選到**」。模型 forward pass 產生每個 token 的 [logit](/llm/knowledge-cards/logit/)，sampling 約束在取樣前調整候選集合或機率，讓輸出符合格式、選項或安全邊界。

## 概念位置

Sampling 約束屬於推論階段，不修改模型權重，也不等於模型真的理解規則。常見控制手段有 temperature、top-p / top-k、logit bias、grammar mask、JSON mode 與 [constrained decoding](/llm/knowledge-cards/constrained-decoding/)；其中 grammar mask 是 structured output 最關鍵的一類。

```text
prompt → model forward pass → logits
  ↓
sampling constraint：調整候選 token / logit / 機率
  ↓
sample next token → append → 下一輪
```

## 可觀察訊號與例子

看到「低 temperature 讓答案更穩」「top-p 過濾長尾 token」「logit bias 禁止某個 token」「grammar mask 只允許合法 JSON token」就是 sampling 約束。例子是 enum 分類：如果合法答案只有 `billing`、`technical`、`other`，推論伺服器可以在輸出欄位值的位置只允許這幾組 token 的路徑。

Sampling 約束的風險是把模型逼到錯誤但合法的輸出。當 grammar 太窄、enum 缺少 `unknown`、schema 沒有容納例外狀態時，模型可能輸出看似可解析但語意不可信的值；這時要加 fallback、confidence 或人工覆核路由。

## 設計責任

Sampling 約束適合處理格式合法性與候選空間控制，不適合單獨承擔事實正確性。設計時先問三件事：合法 token 集合能否完整表示業務狀態、約束失敗時要 retry 還是回退、下游 validator 如何分辨「格式合法但語意可疑」。下一步路由是 [Structured Output](/llm/knowledge-cards/structured-output/) 與 [Top-K / Top-P / Min-P Sampling](/llm/knowledge-cards/top-p-sampling/)。
