---
title: "4.13 Eval 設計座標系：三軸、八象限、何時測什麼"
date: 2026-05-14
description: "Eval 設計三軸（objective↔subjective / component↔end-to-end / quantitative↔qualitative）、八象限的對應 eval 工具、軸選錯的訊號、跟 benchmarking / LLM-as-judge / tracing 的關係"
tags: ["llm", "applications", "evaluation", "evals", "methodology"]
weight: 13
---

LLM 應用的「怎麼測」問題大家都在問、但答案常常是「跑某個 benchmark」「找個 LLM judge」這類**工具層**回答。實務上工具是末端、設計重點是**先選測什麼軸、再選工具**。軸選錯了、再好的工具也測不出有用訊號——用 subjective 工具測 objective 行為（例如用 LLM judge 看金額計算對不對）、或用 end-to-end 工具測 component bug（例如看 user satisfaction 但其實是 retrieval pipeline 在漏 chunk）、都是常見的軸誤選。

本章寫 eval 設計的座標系：三個 binary 軸、八個象限、每個象限對應什麼工具、軸選錯的訊號怎麼識別。這層 framing 是 meta、不是具體 eval 方法——具體方法在 [4.14 benchmarking](/llm/04-applications/benchmarking-and-evaluation/) 跟 [4.21 LLM-as-Judge](/llm/04-applications/llm-as-judge/)。

## 本章目標

讀完本章後你能：

1. 把任何 eval 需求放到三軸座標、定位象限。
2. 對每個象限選對應的 eval 工具。
3. 識別軸誤選的訊號、避免「工具對、軸錯」的常見坑。
4. 規劃 eval 路線：初期該做哪幾個象限、規模化後再補哪些。
5. 把 eval 設計跟 [4.14 benchmarking](/llm/04-applications/benchmarking-and-evaluation/) / [4.20 tracing](/llm/04-applications/llm-tracing-and-observability/) / [4.21 LLM-as-Judge](/llm/04-applications/llm-as-judge/) 串成完整 pipeline。

## 三軸

Eval 設計的三個正交軸：

### 軸 1：Objective ↔ Subjective

- **Objective**：有明確 ground truth、檢驗可以寫成 deterministic check（金額對不對、SQL 跑得通不通、JSON schema 合不合法）。
- **Subjective**：沒有單一正確答案、需要評分或比較（語氣好不好、解釋清楚不清楚、推薦的 trip 合不合用戶）。

判讀訊號：「能不能用 Python 函數判定對錯」、能 → objective、不能 → subjective。

### 軸 2：Component ↔ End-to-End

- **Component**：測單一元件、孤立評估（retrieval 拿對 chunk 沒、tool call 參數對沒、prompt 抽出正確 entity 沒）。
- **End-to-End**：測完整流程、user 視角結果（user 問題有沒有被解決、訂單有沒有完成、conversation 滿意度）。

判讀訊號：「失敗時你想知道是哪一段壞掉」→ component；「你只在乎最終體驗」→ end-to-end。

### 軸 3：Quantitative ↔ Qualitative

- **Quantitative**：產出數字（accuracy / latency / cost / pass rate）、可以追蹤、可以比較、可以 alert。
- **Qualitative**：產出觀察（error pattern、user 抱怨、reviewer 註記）、無法直接 aggregate、但能引導 hypothesis。

判讀訊號：「結果能算平均嗎」→ quantitative；「結果是讀完才知道」→ qualitative。

### 三軸的正交性

這三軸是正交的、不是同義詞：

- 「Objective + component + quantitative」典型是 unit test（function 返回對不對）。
- 「Subjective + end-to-end + qualitative」典型是 user 訪談（user 整體滿意度）。
- 中間象限存在多種混合、各有對應工具。

## 八象限

3 個 binary 軸 = 8 象限。每個象限的常見對應工具：

| 象限                                         | 典型問題                                | 對應工具                                              |
| -------------------------------------------- | --------------------------------------- | ----------------------------------------------------- |
| Objective + Component + Quantitative         | 這個函數 / tool / RAG 元件對嗎          | Unit test、deterministic check、retrieval recall@k    |
| Objective + Component + Qualitative          | 這個元件失敗 pattern 是什麼             | Error log 分析、trace inspection                      |
| Objective + End-to-end + Quantitative        | 整套系統的 success rate / latency       | E2E test、success metric、latency p95                 |
| Objective + End-to-end + Qualitative         | 整套系統的 catastrophic 失敗 case 是什麼 | Production incident review、抽樣 trace 讀             |
| Subjective + Component + Quantitative        | 這個 step 的輸出評分                    | LLM-as-judge pairwise / rubric、human rating          |
| Subjective + Component + Qualitative         | 這個 step 的 output 哪裡讓人不舒服      | Human review、error analysis with comments           |
| Subjective + End-to-end + Quantitative       | User 整體 NPS / 滿意度評分              | CSAT、thumbs up/down、appeal rate                     |
| Subjective + End-to-end + Qualitative        | User 想要的是什麼、現在哪裡沒滿足       | User 訪談、開放問卷、social listening                 |

不是「八個都要做」、是「先看你的問題在哪個象限、用對應工具」。

## 軸誤選的訊號

軸選錯時、工具會給出「看起來合理但其實沒用」的訊號。三個常見軸誤選：

### 誤選一：用 subjective 工具測 objective 行為

例：訂單金額計算對不對、找 LLM judge 來看「這個金額合理嗎」。

- **問題**：金額計算有 ground truth、應該 deterministic check（`assert order.total == expected`）。LLM judge 對「合理」的判斷有偏差、會放過明顯錯誤、會挑剔正確但不直觀的答案。
- **訊號**：你發現自己在寫「judge prompt」描述「什麼樣的金額是合理的」、但其實該行為有客觀標準。
- **修正**：把 judge prompt 翻成 deterministic check。

### 誤選二：用 end-to-end 工具測 component bug

例：整套系統 success rate 從 90% 掉到 80%、追了一週、結果是 retrieval 漏 chunk。

- **問題**：E2E metric 告訴你「有問題」、不告訴你「在哪」。Component eval 缺失時、debug 從 trace 倒推、耗時。
- **訊號**：incident 後 root cause analysis 經常超過一天、查到的東西其實 component eval 該秒抓。
- **修正**：對 critical component（retrieval、tool 調用、parse 階段）加 component eval、production 持續跑。

### 誤選三：用 quantitative 工具找 qualitative 訊號

例：user 滿意度從 4.2 掉到 4.0、團隊看數字盯一週、不知道發生什麼。

- **問題**：Quantitative metric 只告訴你「有變化」、不告訴你「為什麼」。Qualitative 訊號（user 抱怨內容、抽樣 conversation）才能浮現 hypothesis。
- **訊號**：團隊看 dashboard 看了很久、卻沒人去讀 actual user feedback。
- **修正**：quantitative trigger（指標漂移）、qualitative 跟進（讀樣本、找 pattern）。

## Eval 演化路徑

不同階段的 LLM 應用、該優先補哪些象限不同。

### 階段 0：MVP（沒任何 eval）

問題：「能不能 demo 一下就好」、行為對不對全靠手測。

- **第一個該補的**：Objective + End-to-end + Quantitative。最少跑 10 個 representative case、能看「跑得起來率」就好。
- **不該太早做**：subjective eval、需要 judge / human rating 的東西。MVP 階段先讓系統穩定運行。

### 階段 1：有 user 在用

問題：production 偶爾有 bug、user 偶爾抱怨、不知道哪些是 systematic、哪些是 random。

- **第二個該補的**：Objective + End-to-end + Qualitative。讀 incident、讀抽樣 trace、找 pattern。
- **第三個該補的**：Objective + Component + Quantitative。對 critical component（retrieval / tool call / parse）加 component-level eval、production 跑。
- **不該做**：完整 subjective rubric。先把 objective 失敗修了再說。

### 階段 2：要持續優化品質

問題：objective 部分已經穩、user 抱怨主要在 subjective 層（語氣、helpful 程度、推薦合不合用）。

- **第四個該補的**：Subjective + Component + Quantitative。用 LLM-as-judge 給每個 step 評分、做 A/B test 比較 prompt 變動。
- **第五個該補的**：Subjective + End-to-end + Quantitative。CSAT、thumbs up/down、appeal rate。
- **要做的**：Subjective eval 跟 qualitative review 必須配合進行——quantitative 給出方向、qualitative 給出修法 hypothesis。

### 階段 3：規模化、跨團隊

問題：多個產品 / 團隊用同一套 LLM infra、eval 要 cross-cutting。

- **要做的**：標準化 eval pipeline、把象限 1-7 都 cover、qualitative review 進入 ritual（每週 incident review、每月抽樣 trace 讀）。
- **重點不是「全部都有」、而是「每個象限的 owner 清楚」**。

## Eval 跟 Trace 的閉環

Eval 不是孤立的——它跟 [4.20 LLM tracing](/llm/04-applications/llm-tracing-and-observability/) 形成閉環：

```text
[Production traffic]
       ↓
   [LLM trace]  ← 每次 call / agent step / tool 都記錄
       ↓
   ├── 即時 monitoring（latency / cost / error rate）
   ├── 抽樣進 eval set（人工標 + LLM judge）
   └── failed case 進 regression set（防止改 prompt 又壞同樣 case）
       ↓
   [Eval pipeline]
       ↓
   ├── Component eval（單元件 accuracy）
   ├── E2E eval（整套 success rate）
   └── Subjective eval（judge / human rating）
       ↓
   [Insights]
       ↓
   ├── Quantitative：metric 漂移 alert
   └── Qualitative：error pattern → hypothesis → 修 prompt / tool / RAG
       ↓
   [改動進 production]
       ↓
   [回到 production traffic、看 metric 收斂]
```

Production trace 不只是 debug 工具、是 eval set 的活泉。Trace + eval 閉環的設計細節見 [4.20](/llm/04-applications/llm-tracing-and-observability/)。

## 跟其他 Eval 章節的分工

| 章節                                                             | 焦點                                                            |
| ---------------------------------------------------------------- | --------------------------------------------------------------- |
| [4.13 本章](/llm/04-applications/eval-design-framework/)         | **Meta**：先選軸、再選工具的設計座標系                          |
| [4.14 Benchmarking](/llm/04-applications/benchmarking-and-evaluation/) | 具體 benchmark 跟自家 eval set 的方法論                          |
| [4.20 LLM tracing](/llm/04-applications/llm-tracing-and-observability/) | Trace 怎麼接 eval、production observability                     |
| [4.21 LLM-as-Judge](/llm/04-applications/llm-as-judge/)          | Subjective eval 的核心工具、rubric / pairwise / bias 緩解        |

讀法建議：先讀本章建立座標系、再依當前痛點往對應章節展開。Subjective eval 痛點 → 4.21；自家 benchmark 設計 → 4.14；production observability → 4.20。

## 常見反模式

### 反模式一：「只有 LLM-as-judge」

LLM-as-judge 紅了之後、團隊把所有 eval 都做成 judge——包括 objective 行為。Judge 對 objective 行為的判斷不如 deterministic check 準確、cost / latency 還更高。

修正：先 deterministic check、judge 留給真正 subjective 的軸。

### 反模式二：「眾多 metric、無人看」

每個 component 都有 metric、dashboard 上 50 個圖、實際上沒人看、bug 還是靠 user 抱怨才知道。

修正：每個 metric 都要有 owner、有 alert threshold、有對應 action。沒人看的 metric 是 noise、刪掉。

### 反模式三：「eval set 不更新、跟 production 脫節」

Eval set 是兩年前定的、production traffic 已經漂得很遠、eval 通過不代表 user 滿意。

修正：production trace 持續抽樣補進 eval set、每季 review eval set 跟 traffic 分佈是否一致。

### 反模式四：「跟 baseline 不對齊」

新 prompt / 新 model 比舊的好嗎？沒有 frozen baseline、每次 A/B 都用「最新的當對照」、長期看不見漂移。

修正：保留 frozen baseline（特定 prompt + 特定 model）、新版本始終跟它比、定期 refresh baseline 並標明時點。

## 何時過時 / 何時不過時

**不會過時的部分**：

- 三軸座標（objective / component / quantitative 三個 binary 軸）。
- 八象限對應工具的結構分類。
- 三類軸誤選的識別訊號跟修正。
- Eval 演化路徑（MVP → user → 優化 → 規模化）。
- Eval / trace 閉環的設計。
- 四個常見反模式。

**會變的部分**：

- 具體 eval framework（OpenAI Evals、Promptfoo、Braintrust、Langfuse 等會持續演化）。
- LLM-as-judge 的具體 prompt 模板跟 bias 緩解技巧。
- 各 benchmark 的權威性（半年一換）。

## 小結

Eval 設計先選軸、再選工具——這是 meta 層的設計反射。三軸（objective↔subjective、component↔end-to-end、quantitative↔qualitative）正交、八象限各有對應工具。軸選錯時、工具會給出「看似合理但無用」的訊號、最常見三類誤選是 subjective 測 objective、e2e 測 component、quantitative 找 qualitative。Eval 演化按階段補：MVP 先 E2E objective quantitative、user 階段補 component objective、優化階段才上 subjective、規模化標準化。Eval 跟 trace 形成閉環、production 流量是 eval set 的活泉。

下一章：[4.14 Benchmarking 與評估方法論](/llm/04-applications/benchmarking-and-evaluation/)、把座標系落到具體 benchmark 設計。Subjective eval 的工具見 [4.21 LLM-as-Judge](/llm/04-applications/llm-as-judge/)、production trace 怎麼接 eval 見 [4.20 LLM tracing](/llm/04-applications/llm-tracing-and-observability/)、跟 fuzzy engineering 典範的關係見 [0.8](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)（fuzzy 行為的測試本質就是 distribution metric）。
