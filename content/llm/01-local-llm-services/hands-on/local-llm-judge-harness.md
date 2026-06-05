---
title: "Hands-on：用本地 LLM 跑 judge harness（最小可行版）"
date: 2026-05-12
description: "在 Ollama / LM Studio 上跑 local reasoning model 當 judge、對自己工作流案例做 eval、JSONL in / JSONL out 最小 harness"
tags: ["llm", "hands-on", "evaluation", "llm-as-judge", "ollama"]
weight: 8
---

[4.21 LLM-as-judge](/llm/04-applications/llm-as-judge/) 寫的是原理。本篇用 Ollama / LM Studio 在本地跑一個最小可行的 judge harness、對自己工作流的真實案例做 systematic eval。隱私敏感場景特別合用 — eval 資料（user query、agent output、可能含 PII）不需要送雲端。

本篇 framing 是「**真的能跑、不只跑 demo**」、所以包含：硬體預算估算、judge model 選型、bias 緩解、calibration 流程、跟 production trace 串接的延伸；術語對應 [LLM-as-Judge](/llm/knowledge-cards/llm-as-judge/) 與 [LLM Tracing](/llm/knowledge-cards/llm-tracing/)。

> **驗證日期**：2026-05-12
> **環境**：M4 Max 64GB / 或 24GB+ VRAM PC + Ollama
> **Judge model**：DeepSeek-R1-Distill-Qwen-32B 或 QwQ-32B（reasoning model 當 judge 更穩）

## 為什麼用本地 LLM 當 judge

跟雲端 judge（GPT-5 / Claude 4）對比：

| 維度       | 本地 judge                            | 雲端 judge           |
| ---------- | ------------------------------------- | -------------------- |
| Cost       | 0（電費）                             | $0.001-0.01 per item |
| 隱私       | 完全本地、eval 資料不出機器           | 送雲端、依政策       |
| Latency    | 視硬體、reasoning model 30B 約 30-60s | API call 5-30s       |
| 品質上限   | 本地 30B reasoning 接近 2024 雲端中段 | 雲端旗艦上限高       |
| 大量 batch | 慢但 zero cost                        | 快但 cost 累積       |

判讀：

- **大量 production trace eval（千筆以上）+ 隱私敏感** → 本地 judge
- **少量 high-stake eval（< 50 筆）** → 雲端旗艦 judge
- **A/B test 快速 iterate** → 雲端（latency 重要）

## 硬體預算

Judge model 選擇看硬體：

| 硬體                       | 適合 judge model                           | 預期 latency / item           |
| -------------------------- | ------------------------------------------ | ----------------------------- |
| M4 Pro 24GB / 4090 16GB    | Qwen2.5-32B Q4 或 DeepSeek-R1-Distill-14B  | 30-60s                        |
| M4 Pro 36GB                | DeepSeek-R1-Distill-Qwen-32B Q4            | 60-120s                       |
| M4 Max 48-64GB / 5090 24GB | QwQ-32B 或 DeepSeek-R1-Distill-Qwen-32B Q6 | 60-180s（含 reasoning trace） |
| M4 Max 128GB / 多卡 PC     | Llama 3.3 70B 或 Qwen3-72B                 | 120-300s                      |

注意：reasoning model 的 thinking trace 拉長 latency、跑大量 batch 要規劃時間（100 item × 60s = 100 min）。

**何時不適合用本地 judge**：

1. **硬體低於 M4 Pro 24GB / 4090 16GB**（如 M1/M2 16GB、無獨立 GPU PC）：跑 32B reasoning model 太緊、強行跑會 swap、latency 爆 5-10×。改用 14B instruct model（如 Qwen2.5-14B Q4）作 judge、或直接走雲端 judge
2. **Batch × latency > 你可接受的等待時間**：100 item × 60s/item = 100 min；500 item × 120s = 17 hr。預估超過 4 hr 時改雲端 batch API
3. **eval 任務太 nuanced**：細粒度倫理 / 法律 / 高 stake 判讀、本地 32B distill 能力不夠、用雲端旗艦 judge 或人工 review
4. **calibration 階段**：第一次跑、要快速 iterate rubric、雲端 judge latency 短（5-30s）更適合 iterate

## 整體流程

```text
1. 蒐集 eval dataset    → JSONL：每行一個 (input, output) 待評
2. 設計 rubric         → 評分維度、scale、明確 anti-pattern
3. 寫 judge prompt     → 4 段式（task / input-output / rubric / format）
4. 跑 harness          → 對每筆 input call judge、parse JSON output
5. Aggregate 結果      → 算平均分數、找 outlier、看 reasoning
6. Calibration（可選）  → 跟 human eval 比對、調 rubric
7. 跟 production trace 串接 → 定期跑 production sample
```

## Step 1：蒐集 eval dataset

JSONL format（每行一筆）：

```json
{"id": "001", "input": "用 Python 寫 fibonacci function", "output": "def fib(n):\n    if n <= 1:\n        return n\n    return fib(n-1) + fib(n-2)"}
{"id": "002", "input": "解釋這段 code 在做什麼：[code]", "output": "這段 code 實作了 ..."}
{"id": "003", "input": "[bug 描述]", "output": "[suggested fix]"}
```

來源：

- 過往 Continue.dev / Cursor 跟 LLM 的對話 log
- Production agent 的 trace（手動 export 或 LangSmith / Phoenix dump）
- 自己 hand-craft 30-100 個典型 case

放在 `data/eval.jsonl`。

## Step 2：設計 rubric

依任務類型設計、coding 任務的範例 rubric：

```text
評分維度：
1. Correctness（程式碼能否運作、邏輯是否正確）：1-5
2. Style（是否符合 codebase convention、習慣命名）：1-5
3. Completeness（是否完整解決 user request）：1-5

評分規則：
- 5：完美無瑕、可直接 merge
- 4：小修可用、整體正確
- 3：方向正確、需 substantial 修改
- 2：部分對、主要邏輯有錯
- 1：完全錯、誤導使用者

明確不加分（緩解 verbosity bias）：
- 冗長 / verbose（同樣正確的短答 = 長答）
- 道歉 / 開場白
- 「我希望這有幫助」這類禮貌話
- 過多 markdown 修飾（不加分）
```

## Step 3：Judge prompt 模板

寫成 file `prompts/judge.txt`：

```text
你是 LLM 輸出品質評估員、要評估 coding assistant 對使用者請求的回答品質。
重要：請保持公正、忽略風格偏好、聚焦在實質品質。

User request:
{input}

Assistant response:
{output}

評分維度（每維 1-5、加總用 overall）：

1. Correctness：程式碼能否運作、邏輯正確
   5: 完美無瑕
   4: 小修可用
   3: 方向正確、需 substantial 修改
   2: 部分對、主要邏輯有錯
   1: 完全錯

2. Style：符合 codebase convention
   1-5 同 scale

3. Completeness：完整解決 user request
   1-5 同 scale

明確不加分項：
- 冗長 / verbose（同樣正確的短答 = 長答）
- 道歉 / 開場白
- 「我希望這有幫助」這類禮貌話
- 過多 markdown 修飾

請依下列 JSON 輸出（不要加額外文字、不要 markdown code fence）：
{
  "correctness": <1-5>,
  "style": <1-5>,
  "completeness": <1-5>,
  "reasoning": "<簡短解釋、< 100 字>",
  "overall": <1-5>
}
```

## Step 4：跑 harness

Python 最小可行版：

```python
# judge_harness.py
import json
import requests
from pathlib import Path

JUDGE_MODEL = "deepseek-r1:32b"  # 或 qwq:32b
OLLAMA_URL = "http://localhost:11434/v1/chat/completions"

def load_dataset(path):
    """Load JSONL eval dataset."""
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]

def load_prompt_template(path):
    return Path(path).read_text()

def call_judge(prompt):
    """Call Ollama judge model、回 raw response text."""
    resp = requests.post(OLLAMA_URL, json={
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,  # judge 用低 temperature 穩定
        "stream": False,
    }, timeout=600)
    return resp.json()["choices"][0]["message"]["content"]

def parse_judge_output(text):
    """Parse judge 回的 JSON、容錯處理（reasoning model 可能加 <think> 標記）。"""
    # 跳過 reasoning trace
    if "</think>" in text:
        text = text.split("</think>")[-1]

    # 找 JSON 區塊
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None

def run_harness(dataset_path, prompt_template_path, output_path):
    dataset = load_dataset(dataset_path)
    template = load_prompt_template(prompt_template_path)

    results = []
    for i, item in enumerate(dataset):
        prompt = template.format(input=item["input"], output=item["output"])
        raw = call_judge(prompt)
        parsed = parse_judge_output(raw)

        result = {
            "id": item["id"],
            "scores": parsed,
            "raw_judge_output": raw[:500],  # 保留前 500 字便於 debug
        }
        results.append(result)
        print(f"[{i+1}/{len(dataset)}] id={item['id']} overall={parsed.get('overall') if parsed else 'FAIL'}")

    # 寫出 JSONL
    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Aggregate
    valid = [r for r in results if r["scores"]]
    if valid:
        avg = sum(r["scores"]["overall"] for r in valid) / len(valid)
        print(f"\nAggregate: {len(valid)}/{len(results)} valid、avg overall = {avg:.2f}")

if __name__ == "__main__":
    run_harness("data/eval.jsonl", "prompts/judge.txt", "results/eval.jsonl")
```

跑：

```bash
# 先確認 judge model 已 pull
ollama pull deepseek-r1:32b

# 跑 harness
python judge_harness.py
```

## Step 5：Aggregate 跟看 outlier

跑完後 results/eval.jsonl 含每筆評分跟 reasoning。看哪些是 outlier：

```bash
# 找 overall < 3 的 case（低分、值得 review）
jq 'select(.scores.overall < 3)' results/eval.jsonl

# 看 reasoning 找系統性問題
jq '.scores.reasoning' results/eval.jsonl | sort -u
```

判讀：

- **多數 score 4-5、少數 1-2**：整體品質好、focus 在低分 case 找 fix
- **多數 score 2-3**：系統性問題、改 prompt / model / agent design
- **分數分佈兩極（很多 5 很多 1）**：可能是 task difficulty 分群、stratified analysis

## Step 6：Calibration（可選但推薦）

跟 human eval 比對、確認 judge 對齊：

```text
1. 從 dataset 抽 30 個（覆蓋 difficulty / score 分佈）
2. 自己 human eval（依同樣 rubric）
3. 對比 judge 跟 human 的 overall score
4. 算 Spearman correlation
   - > 0.7：judge 對齊夠好、可信
   - 0.5-0.7：部分問題、改 rubric
   - < 0.5：judge 不可信、換 model 或重寫 rubric
```

低 correlation 的常見原因：

- Rubric 太 vague、judge 自由發揮
- Judge model 能力不夠（換更強 judge）
- Verbosity / position bias 沒緩解
- Eval task 跟 judge 訓練分佈差距大

## Step 7：跟 production trace 串接（延伸）

把 [4.20 LLM tracing](/llm/04-applications/llm-tracing-and-observability/) 蒐集的 production trace export 成 JSONL、定期跑 judge：

```bash
# 假設用 Langfuse self-host
langfuse export --filter "user_feedback=negative" --output traces.jsonl

# 轉成 eval format
python convert_trace_to_eval.py traces.jsonl > data/eval-from-prod.jsonl

# 跑 judge
python judge_harness.py
```

這是 production quality engineering 閉環的本地版本、隱私敏感場景的 cost-free alternative。

## 失敗模式

1. **Judge 不輸出合法 JSON**：reasoning model 可能在 `<think>...</think>` 後仍加 markdown / 解釋

**緩解**：parse 時跳 `<think>` 段、容錯處理、或開 [constrained decoding](/llm/knowledge-cards/constrained-decoding/)（llama.cpp grammar）

2. **Latency 太長、batch 跑不完**：reasoning model 32B 每 item 60-120s、100 item 要 2 小時

**緩解**：用較小 judge model（如 Qwen2.5-32B instruct、非 reasoning）、或拆 batch 並行

3. **Judge bias 沒緩解**：本地 judge 跟雲端 judge 都會有 verbosity / position bias

**緩解**：rubric 寫明、pairwise 換位置跑 2 次

4. **本地 judge 能力上限**：30B distill 對 nuanced case 判讀不如雲端旗艦

**緩解**：critical case 加 spot human review、或混用本地（量大）+ 雲端（精選 sample）

## 跟其他章節的關係

- 原理層的 LLM-as-judge 設計見 [4.21](/llm/04-applications/llm-as-judge/)
- Production trace 串接見 [4.20 tracing](/llm/04-applications/llm-tracing-and-observability/)
- Reasoning model 選型見 [3.8](/llm/03-theoretical-foundations/reasoning-models/)
- 隱私 / 跨雲端邊界判讀見 [6.4](/llm/06-security/cross-cloud-local-data-boundary/)
- Benchmark 跟 in-house eval 的層次見 [4.14](/llm/04-applications/benchmarking-and-evaluation/)
