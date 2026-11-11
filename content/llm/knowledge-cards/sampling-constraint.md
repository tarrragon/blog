---
title: "Sampling Constraint"
date: 2026-05-14
description: "推論時限制下一個 token 候選集合的控制手段，用來把模型生成導向合法格式或特定選項"
weight: 1
tags: ["llm", "knowledge-cards", "sampling", "decoding"]
---

Sampling constraint（sampling 約束）的核心概念是「**在模型選下一個 token 時，限制哪些 token 可以被選到**」。模型 forward pass 產生每個 token 的 [logit](/llm/knowledge-cards/logit/)，sampling 約束在取樣前調整候選集合或機率，讓輸出符合格式、選項或安全邊界。

## 跟其他概念的關係

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

## 判斷條件與後果

Sampling 約束保證被選出的 token 屬於合法集合，不保證值的事實正確；合法集合畫得不對時，約束反而把模型推向錯誤但合法的輸出。這個風險有多大，看三個條件：

- **合法 token 集合表示不了某個業務狀態時**（enum 只有 `billing`、`technical`、`other`，沒有 `unknown`），模型遇到不屬於任何一類的輸入也只能選其中一個，輸出可以解析，語意卻不可信。
- **約束失敗時沒有定義處置時**（retry，或回退到人工覆核），解析失敗或可疑的輸出沒有去處，下游只能照單接收，或讓整個請求失敗。
- **下游 validator 只檢查格式時**，「格式合法但語意可疑」的值跟正確的值看起來一樣，錯誤直接流到執行端；validator 另外看 confidence 或業務規則才分得出來。

下一步路由是 [Structured Output](/llm/knowledge-cards/structured-output/) 與 [Top-K / Top-P / Min-P Sampling](/llm/knowledge-cards/top-p-sampling/)。
