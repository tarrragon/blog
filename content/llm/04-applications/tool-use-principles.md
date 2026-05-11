---
title: "4.1 Tool use 原理：LLM 跟外部世界互動"
date: 2026-05-11
description: "Structured output 是 LLM 跨入工程系統的橋、function calling 取捨、為什麼本地小模型 tool use 表現崩潰"
tags: ["llm", "applications", "tool-use", "function-calling"]
weight: 1
---

Tool use 把 LLM 從「會生成文字的模型」延伸到「能參與工程系統的元件」。它的核心機制是 structured output——把 LLM 的機率分佈約束到工程系統可解析的格式、讓下游程式能對 LLM 的輸出做確定性處理。[Function calling](/llm/knowledge-cards/function-calling/) 是 structured output 的工程化形態、由模型訓練端跟推論端共同支撐。

本章寫的是「為什麼需要 tool use」「structured output 怎麼運作」「設計工具時該如何思考副作用」這類跟具體 framework 無關的原理。OpenAI function calling spec、Anthropic tools API、JSON Schema constrained sampling 等具體格式半年一變、不在本章焦點；本章寫的是「換 spec 之後仍然成立」的設計取捨。

## 本章目標

讀完本章後、你應該能：

1. 解釋為什麼 LLM 需要呼叫工具、純生成解不了什麼問題。
2. 看到 structured output / JSON mode 設定時、知道它在限制 sampling 的哪一層。
3. 判讀「這個模型 tool use 為什麼表現崩」的常見根因。
4. 設計工具時用「副作用範圍 + 信任邊界」思考、不只看「功能對不對」。

## 為什麼 LLM 需要呼叫工具

LLM 的能力邊界決定了什麼任務「光靠生成解不了」：

- **即時資料**：模型訓練後不知道現在發生的事。「查今天天氣」「現在股價」必須拉外部資料。
- **精確計算**：模型對大數運算、長乘法、開根號等表現不穩、calculator 一行解決。
- **副作用**：把檔案寫到磁碟、發 email、call API——這些是「動作」、生成文字本身產生不了。
- **持久化狀態**：模型本身無狀態、需要外部資料庫 / vector store / file system 儲存跨對話的資料。
- **規模化操作**：搜尋一千個 file、處理 batch、跑 SQL——這些是 deterministic、用程式跑比讓模型「逐字模擬」快幾個量級。

Tool use 解的不只是「能力延伸」、更是「把 LLM 跟確定性系統接起來」。沒有 tool use、LLM 只能在自己的文字宇宙裡跑；有了 tool use、它變成可以呼叫資料庫、寫檔、發網路請求的「會說話的 agent」。

這個跨界本身帶來新的問題：模型輸出必須能被工程系統消費。自然語言對人類友善、對程式不友善——下一節要解的就是這個橋。

## Structured Output 是 LLM 跨入工程系統的橋

自然語言對下游 parser 不友善：同一個意思有無限種表達、模型可能加 prefix、加 disclaimer、加 markdown 格式、漏關鍵欄位。如果直接 regex 解析、會 case by case 補例外、最終 parser 比 LLM 還複雜。

Structured output 解這個問題：把 LLM 的輸出約束到預定義的結構（JSON、YAML、XML、特定 schema）。實作機制有幾種：

- **Prompt-level**：在 prompt 裡明確要求「請輸出 JSON、schema 是 X」。靠模型 follow instruction 的能力、不保證 100% 合法。
- **JSON mode / response_format**：推論伺服器在 sampling 階段強制每個 token 都讓 output 維持合法 JSON。每生一個 token、用 grammar 約束過濾 logits。
- **Grammar-constrained sampling**：用 BNF / regex / context-free grammar 描述合法輸出形狀、推論時逐 [token](/llm/knowledge-cards/token/) 過濾。可以約束到任意嚴格的結構。
- **Function calling 訓練**：模型訓練階段就教「該怎麼呼叫工具」、輸出格式內建在模型行為裡。

四種機制的層級不同：prompt-level 是「請模型自律」、JSON mode 跟 grammar 是「sampling 階段強制」、function calling 是「訓練讓模型自然」。越下層越穩、但實作越複雜。

理解這個 stack 的價值是：看到「模型輸出 JSON 不穩」時、知道該往哪一層下手。Prompt 寫得清楚不夠的話、要動 sampling 約束；sampling 約束打開了還不穩、要看模型本身的 tool use 訓練覆蓋度。

## Function Calling 跟 Free-form Generation 的取捨

「讓 LLM 呼叫工具」有兩條路：

**Function calling**（模型訓練支撐）：

- 模型訓練時看過大量「使用者問題 → 工具呼叫格式」的範例、知道該怎麼決定要不要呼叫、傳什麼參數。
- 優點：呼叫格式穩、模型「自然」知道何時該呼叫；不需要 prompt 工程寫很長。
- 缺點：受訓練資料分佈影響大、跨模型行為不一致；只支援模型訓練過的協議格式。
- 適合：主流 / 大型模型、想用最少 prompt 工程拿穩定行為。

**Free-form + structured output**（推論時約束）：

- 寫 prompt 描述工具、用 grammar / JSON mode 約束輸出。
- 優點：跨模型可移植、不依賴模型 fine-tune；支援任意自訂協議格式。
- 缺點：模型可能不知道「何時該呼叫」、需要 prompt 工程描述觸發條件；嚴格約束下品質可能受影響。
- 適合：跨多家 LLM 都要用同一套程式、或用較弱的模型不能依賴 function calling 訓練。

實際應用常混用：主流模型走 function calling、fallback 模型走 free-form。但混用增加維護成本、小型應用挑一條走通常更簡單。

判讀「該用哪一條」的訊號：

- 目標模型主流 + 規模大（>30B）→ function calling、開箱即用。
- 目標模型小或非主流 → free-form + structured output、跨模型較穩。
- 想跨 LLM 供應商可移植 → free-form + 標準化 schema、不綁特定 provider 的 function spec。

## 為什麼本地小模型 Tool use 表現崩

寫 code 場景的本地小模型（7B、14B 級）跑 tool use 經常崩、表現訊號清楚：

- 呼叫格式錯（JSON 不合法、欄位拼錯）。
- 參數胡亂填（type 不對、value 超出 schema 範圍）。
- 不該呼叫時呼叫（簡單問題硬要叫 calculator）。
- 該呼叫時不呼叫（複雜計算自己算錯）。
- 連續呼叫 loop（一直叫同一個工具不收斂）。

根因是訓練資料分佈：

- Tool use 範例在預訓練資料中比例低（網路文字主要是「人類對話」、不是「人類 + 工具 trace」）。
- SFT 階段才大量加 tool use 資料、但 SFT 規模相對小、小模型容量有限、學不全。
- 大模型（70B+）SFT 學得進、能 generalize；小模型 SFT 容量不夠、tool use 只在訓練過的 narrow 場景表現好。

緩解策略：

- **限制 tool 數量**：把可用 tool 控制在 3-5 個內、小模型較能 handle。
- **詳細 prompt 描述每個 tool**：補模型訓練的不足。
- **強 structured output 約束**：用 grammar 強制輸出合法、即使模型「想」出錯也被 sampling 擋下。
- **重試 + fallback**：第一次失敗的話、加 error feedback 重試；多次失敗 fallback 到「不用 tool」的 free-form。
- **接受能力限制**：複雜 multi-step tool use 本地小模型現階段做不好、切到雲端。

判讀「該不該本地跑 tool use」的反射：先看任務的 tool 複雜度，單 tool / 簡單呼叫本地堪用，multi-step / 跨多 tool 通常需要 30B+ 模型，否則失敗率高到不實用。

## 工具的「副作用範圍」設計

設計給 LLM 用的工具時、不能只想「功能對不對」、要把「副作用範圍 + 可逆性」也納入設計。

可逆性 spectrum、由低風險到高風險：

| 等級 | 副作用               | 例子                                    | 適合的審查模型       |
| ---- | -------------------- | --------------------------------------- | -------------------- |
| 1    | 純讀、無副作用       | search、read file、query DB             | 完全自動             |
| 2    | 寫 sandbox / staging | write to scratch file、test environment | 完全自動 + 事後審    |
| 3    | 寫本地持久化         | edit code file、modify config           | step-by-step 審查    |
| 4    | 寫共享 / production  | git push、deploy、modify DB production  | 強制人類確認         |
| 5    | 操作真實世界         | 發 email、買股票、控制硬體              | 強制人類確認 + audit |

每升一級、人類審查的需求越高、agent 的自主度越低。設計工具時、把同樣功能切到不同等級可以大幅降風險：

- 「edit file」分成「propose diff」（等級 2）+「apply diff」（等級 3）、前者自動、後者要確認。
- 「query DB」分成「SELECT」（等級 1）+「INSERT / UPDATE」（等級 4）、前者自動、後者強制確認。
- 「run shell command」是 spectrum 上分佈最廣的工具——讓 LLM 自由跑 shell 等於開放等級 1-5 全部、是常見的 over-permissioned 設計。

這個 framing 跟 OS 的權限模型同概念：least privilege 套用到 LLM tool use。每個工具設計時、先問「最差情況是什麼」、再決定該不該全自動。

## 結構化輸出的失敗模式

Structured output 用得好的時候、parser 不用寫 error handling；用得不好的時候、會撞到幾種典型失敗：

- **Schema 太嚴**：模型「失敗」次數多、流程卡住。例如要求 enum 只能是 5 個值、但實際 query 有第 6 種情境、模型只能硬選一個錯的。
- **Schema 太寬**：模型輸出歧義、下游解析失敗。例如欄位定義成 `string`、模型可能輸出空字串、null、`"N/A"`、`"none"`、各種變體。
- **Free-form 跟 structured 混合**：要求 JSON 但同時要求「reasoning 寫在 markdown」、模型容易把 markdown 寫進 JSON string 亂掉 escape。
- **巢狀太深**：超過 3 層的 JSON 巢狀、模型容易在中間漏 `}` 或 `,`。Grammar-constrained sampling 可解、純 prompt 控制就脆弱。

緩解模式：

- **Schema 寬度配合 retry**：先用較寬 schema、解析失敗時 retry + 把錯誤訊息餵回模型修正。
- **拆步驟**：把複雜 structured output 拆成多個小步驟、每步驟一個簡單 schema、累積成完整結果。
- **Few-shot 範例**：在 prompt 裡放 3-5 個正確輸出範例、比文字描述 schema 更穩。

## 何時不需要 Tool use

不是所有 LLM 應用都需要 tool use。下列情境純生成已足夠、加 tool use 反而增加成本與失敗點：

- **純文字產出任務**：寫文章、改寫、翻譯、摘要——輸出本身是文字、不需要副作用、tool use 沒戲。
- **單一回應對話**：使用者問問題、模型答問題、不需要去 fetch 外部資料時。模型參數記憶覆蓋的範圍直接回答即可。
- **靠 prompt + 模型內知識能解的任務**：簡單 reasoning、code generation 不需要 file I/O、解釋程式碼——這些 tool use 加進去 overhead 大於收益。
- **小型 in-process 應用、tool 數量極少（1-2 個）**：可能直接 if-else 比 function calling 更簡單。

判讀反射：先問「不用 tool use 能不能做到」、能做就別加。Tool use 是 LLM 能力延伸、不是「應用變高級」的必要條件。過度設計把 single-call 解的問題包進 tool 是常見浪費。

## 何時過時 / 何時不過時

**不會過時的部分**：

- 「LLM 輸出需要被工程系統消費」這個 framing。
- Structured output 是 LLM 跟工程接軌的底層機制。
- Function calling vs free-form 的取捨判讀。
- 訓練資料分佈如何影響 tool use 能力（小模型崩的根因）。
- 副作用範圍 / 可逆性 spectrum 的設計框架。

**會變的部分**：

- 具體 schema spec（OpenAI function spec → Anthropic tools API → 未來的標準化）。
- 各 framework 的 tool 註冊 API。
- 哪些模型 function calling 訓練得好（會隨新模型更新）。
- Grammar-constrained sampling 的具體實作（llama.cpp / vLLM / Outlines 等會持續演化）。

看到新 tool use 介面或新 framework 時、回到本章的 framing 評估：它支援哪一層的 structured output、訓練過哪些 protocol、對副作用範圍有沒有設計——這些問題的答案決定它在你的場景能不能用。

## 小結

Tool use 把 LLM 從文字生成器變成可跟工程系統互動的元件。Structured output 是底層機制、function calling 是工程化形態、訓練分佈決定模型能不能穩定 tool use、副作用範圍決定該全自動或強制人類審查。本地小模型 tool use 現階段受訓練資料限制、多 tool / multi-step 場景需要雲端旗艦。

下一章：[4.2 Agent 架構原理](/llm/04-applications/agent-architecture/)、看 LLM 自主決策的設計取捨。
