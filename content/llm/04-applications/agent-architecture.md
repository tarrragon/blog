---
title: "4.4 Agent 架構原理"
date: 2026-05-11
description: "Agent loop 結構、失敗模式、什麼任務適合 vs 不適合、跟人類審查的協作模型"
tags: ["llm", "applications", "agent"]
weight: 4
---

[Agent](/llm/knowledge-cards/agent/) 跟「對話 LLM」的根本差異在於控制流的所有權。對話 LLM 是「人類問、模型答」、每輪都由人類決定下一步；agent 是「LLM 自己決定下一步、自己呼叫工具、自己評估結果」、控制流交給模型。

這個轉變看似只是「加個 loop」、實際上帶來新的設計問題：失敗模式從「答錯」變成「跑偏」、終止條件變成設計重點、人類審查角色從「事後讀」變成「決定何時介入」。本章把 agent 的這些核心問題拆開、寫成跨 framework 都成立的原理。aider、Cline、LangGraph、各家 Agent SDK 等具體工具不在本章焦點——這些半年一個版本、原理層級更穩。

## 本章目標

讀完本章後你能：

1. 區分「LLM agent」跟「對話 LLM」的本質差異。
2. 畫出 agent loop 的核心結構、看到新 agent 工具能對應到這個骨架。
3. 看到 agent 失敗時、能診斷是哪一類失敗（context drift / 目標漂移 / tool 誤判）。
4. 判斷一個任務該用 agent 還是 single-call。

## Agent 跟「對話 LLM」的差異

| 維度     | 對話 LLM                 | Agent                                 |
| -------- | ------------------------ | ------------------------------------- |
| 控制流   | 人類驅動、每輪 turn 獨立 | LLM 自己驅動、跨多步                  |
| 上下文   | 每次 prompt 由人類組裝   | 自己累積跨步驟 context                |
| 工具呼叫 | 單次 / 偶爾              | 多次連續、串接結果                    |
| 終止     | 使用者結束對話           | 模型自己判斷「完成」                  |
| 失敗模式 | 答錯（人類能立刻 catch） | 跑偏、進入錯路、long horizon 累積誤差 |
| 人類角色 | 主導者                   | 監督者 / 審查者                       |

這個轉變對 LLM 提出新的能力要求：

- 規劃能力（把目標拆成可執行的子步驟）。
- 自我評估能力（判斷子步驟做對了沒）。
- 工具選擇能力（多個工具中挑對的）。
- 上下文管理能力（哪些 context 該帶下去、哪些可以丟）。

這幾項能力是雲端旗艦模型的明顯強項、也是本地小模型的明顯弱項。理解這個能力差距、能解釋為什麼「本地寫 code 用 Continue.dev 還行、本地跑 agent 經常失敗」、不是工具問題、是模型能力 baseline 問題——背後牽涉 [function calling](/llm/knowledge-cards/function-calling/) 訓練深度、long context [prefill](/llm/knowledge-cards/prefill/) 痛點、規劃能力差距。

## Agent Loop 的核心結構

所有 agent framework 不管實作怎麼包裝、骨架都是同一個 loop：

```text
1. 感知（Perceive）：讀當前 context、環境狀態、上一步結果
   ↓
2. 推理（Reason）：思考下一步該做什麼、選工具、決定參數
   ↓
3. 行動（Act）：呼叫工具、修改環境
   ↓
4. 觀察（Observe）：解讀工具回應、更新 context
   ↓
5. 判斷終止：done 還是回 1
```

這個 loop 跟控制系統的 sense-plan-act 同骨架、本質是「在環境中執行目標導向行為」。Agent framework 的差異主要在每一步的具體實作：

- **感知**怎麼編成 prompt？要保留多少歷史？怎麼壓縮 long context？
- **推理**用什麼模型？用 chain-of-thought 還是直接決定？要不要再拆成 plan + act？
- **行動**支援什麼 tool？怎麼防止破壞性操作？
- **觀察**怎麼把工具回應翻成 context？大 output 怎麼摘要？
- **終止**怎麼判斷？模型自己說、外部 critic 判斷、step 上限、cost 上限？

理解這個骨架的價值是：看到新 agent framework 時、按這 5 步問就能拆解它的設計取捨；agent 跑出問題時、定位是哪一步壞掉、不是「整個 agent 壞了」。

## 為什麼 Agent 容易失敗

Agent 跑長時間任務時、失敗率比 single-call 高很多、根因多半落在這三類：

### Context drift（上下文漂移）

每輪累積的 context 偏離原始目標、後期 LLM 「忘記」要做什麼。典型表現：開始任務是「修這個 bug」、跑了 10 步後變成「重構這個 module」、再 10 步後變成「rewrite 整個 file」。每一步看起來都合理、累積起來偏離原目標。

根因：

- 模型對 long context 後段的 attention 偏弱（middle-loss 現象、attention 在序列中段表現最弱、見 [3.2 attention 機制](/llm/03-theoretical-foundations/attention-mechanism/)）。
- 子步驟產出的中間結果會被當成「新目標」、模型沿著中間結果繼續推、原始目標被擠掉。
- 沒有定期重新引用原始目標的機制。

緩解：每隔 N 步把原始目標重新塞回 context、或用外部 critic 比對「現在這步跟原目標的距離」。緩解失敗的下一步：N 步重塞仍漂移、改換較大 model（context 處理能力跟模型大小強相關）；換 model 仍漂移、escalate human 或退回 single-call 拆解任務。

### Goal drift（目標漂移）

模型把子目標當主目標、執行完子目標就停下來、原始任務沒完成。例：原任務「實作 + 測試 + commit」、模型實作完就回「我寫完了」、忘了還要測 + commit。

根因：

- 訓練資料中「完成單一任務」的範例多、「完成複雜 multi-step 任務」的範例相對少。
- 子任務做完的「完成感」訊號比「整個任務還沒完」訊號強。

緩解：終止條件用外部驗證（test 跑通、PR 開、commit 進）、不靠模型自己說「完成了」。緩解失敗的下一步：外部驗證仍漏步、加 explicit checklist 在 system prompt、每步要求模型回報 checklist 完成狀態。

### Tool result misread（工具結果誤判）

Tool 回 error 或意外結果、模型 hallucinate「成功了」繼續推進、累積錯誤越來越深。例：`git push` 失敗、模型沒讀 error message、下一步開始寫 PR description、最終提交一個沒推上去的 branch。

根因：

- 模型對「無聲失敗」（tool 回的格式正常但內容是 error）解讀差。
- 部分 framework 對 tool error 處理弱、模型看不到完整 error message。

緩解：tool 設計時 error 用結構化、模型容易識別；agent loop 加 explicit error handling step、看到 error signal 強制 retry 或 escalate。緩解失敗的下一步：retry 仍失敗、強制呼叫 tool 重新讀狀態（如 `git status` / `git log`）確認、避免依賴模型對 tool 結果的記憶。

## 什麼任務適合 Agent vs Single-call

Agent 適用面有邊界、判讀 framework：

**適合 agent**：

- 目標可分解成明確子步驟。
- 子步驟有客觀驗證訊號（test 跑通、file 寫入、API 200）。
- 單一 call 上下文不足、需要跨多次 tool 互動。
- 失敗可以 recover（agent 跑錯一步可以糾正）。

**不適合 agent、改用 single-call**：

- 目標模糊探索性（沒有客觀驗證）。
- 緊湊推理任務（拆步驟反而失去全局視角）。
- 簡單可預測的任務（agent overhead 大於收益）。
- 失敗代價極高（agent 跑錯一步很難 recover）。

例子對照：

| 任務                         | 該用               | 為什麼                                    |
| ---------------------------- | ------------------ | ----------------------------------------- |
| 修一個 bug、跑 test 確認     | Agent              | 子步驟清楚、test 是客觀驗證               |
| 寫一個 function 的 docstring | Single-call        | 簡單、不需 multi-step                     |
| 設計新 module 架構           | Single-call + 人類 | 探索性、人類審查比 agent loop 有用        |
| 重構整個 codebase            | Agent（謹慎）      | 子步驟多但失敗代價高、需強人類監督        |
| 寫詩 / brainstorming         | Single-call        | 創意任務、沒有客觀驗證、agent loop 沒意義 |
| Migrate database schema      | Agent + 強審查     | 子步驟清楚但失敗代價極高、每步要人類確認  |

「先 single-call 試、不夠再 agent」是合理的預設姿勢。Agent 是「特定問題的解法」、客觀驗證訊號 + 可承擔失敗 + 多步必要、三者俱備時用；用錯地方反而增加 cost 跟失敗率。

### 灰色帶反例：判讀容易誤判的情境

實務上常見的「該用但失敗了」「不該用但成功了」灰色帶、列幾個典型情境跟判讀路徑：

- **目標可分解但子步驟驗證不夠客觀**：如「優化這段 code 的可讀性」、可以分成「重構函式 / 加註解 / rename 變數」、但「好不好」沒客觀驗證。Agent 跑完可能改成「自己覺得好」的版本、跟使用者期待差很多。判讀：改用 single-call + 人類審查、或加明確的 lint / formatter 當客觀驗證。
- **失敗代價不對稱**：如 production database migration、子步驟清楚（dump → migrate → verify）、但中間失敗可能毀資料。判讀：用 agent 但強制每步要 human-in-the-loop confirm、或拆成 agent 生 migration script + 人類執行兩階段。
- **子步驟之間有強依賴**：如「研究某 topic → 寫摘要 → 翻譯」、agent 容易在中間步驟漂掉、累積誤差傳到最後。判讀：強依賴 chain 走 single-call sequential pipeline、不走 agent loop。
- **任務在訓練分佈邊緣**：如 niche domain（特定 framework、罕見語言）的 multi-step 任務、模型對該 domain 沒看過 multi-step 範例、容易在 step transition 漏 context。判讀：先 small-scale 驗證 agent 在這個 domain 表現、再決定要不要 scale up。

## Termination 條件：怎麼讓 Agent 知道停下來

Agent 的失敗模式很多落在 termination：該停沒停（無限 loop）、不該停就停（漏做子步驟）。Termination 策略選擇是 agent 設計的核心。

主流 termination 機制：

- **明確 done signal**：tool 回 special token、模型輸出特定 phrase。最直接、但靠模型自律、不夠 robust。
- **Step 上限**：跑 N 步強制停。防止無限 loop、但 N 設不對會中途砍掉。
- **Cost 上限**：累計 token / dollar 超過 cap 強制停。實務防錢被燒掉。
- **目標達成評估**：另一個 LLM 或 deterministic check 判斷「任務完成了沒」。最 robust 但 cost 高。
- **外部訊號**：test 跑通、檔案被寫入、人類介入。客觀、用在有明確完成判準的任務。
- **人類介入**：把 termination 決定交給人類。最保守、適合不可逆任務。

實務上多重 termination 並用：step 上限當 safety net、cost 上限當預算守門、外部訊號當主要判準、人類介入當最終 fallback。

判讀 termination 設計的訊號：

- 沒有 step / cost cap → 失控風險高。
- 完全靠模型自己說「完成」→ 漂移風險高。
- 沒有客觀驗證 → 「成功」訊號可能是 hallucination。

## Agent 跟人類審查的協作模型

Agent 的自主程度跟人類審查粒度是 spectrum、不是 binary：

| 模型                                                    | 人類介入時機              | 適合任務                                |
| ------------------------------------------------------- | ------------------------- | --------------------------------------- |
| Full auto                                               | 跑完之後審結果            | 可逆任務、低風險（read-only、本地實驗） |
| Checkpoint                                              | 每隔 N 步審一次           | 中等風險、長時間任務                    |
| Step-by-step approval                                   | 每個 tool call 前審       | 不可逆任務、高風險（production change） |
| Plan first, then auto                                   | 審 plan、approve 後自動跑 | 可預測子步驟、人類確認方向後可放手      |
| Human-in-the-loop（HITL、agent 過程中插入人類審查節點） | Agent 不確定時主動問人類  | 模糊邊界、需要 domain 判斷              |

選擇依據主要是「副作用範圍」（見 [4.3 工具的副作用範圍設計](/llm/04-applications/tool-use-principles/)）：等級 1-2 工具可以 full auto、等級 3 適合 checkpoint、等級 4-5 強制 step-by-step。不同自主度對應的 HITL 時機選擇（pre-act / mid-stream / post-hoc）跟確認流程設計（避免橡皮圖章化）見 [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/)。

設計 agent 時、先設想最差情況：「agent 跑偏到底會發生什麼」、再決定該用哪一級協作模型。完全自動跑 production migration 通常是 over-trust、step-by-step 跑 search 通常是 under-trust。個人 dev 把這個協作模型從本機 wrapper 演化到團隊 / production 服務時的 routing 判讀見 [6.5 跨進 production 的 routing 中樞](/llm/06-security/routing-to-production-security/)。

## 本地 LLM 跑 Agent 的特殊挑戰

本地 LLM 跑 agent 現階段（2026/5）失敗率明顯高於雲端、根因不只一條：

- **Tool use 訓練不足**（見 [4.3](/llm/04-applications/tool-use-principles/)）：小模型 tool use 本來就崩、agent 需要多次穩定 tool use、失敗率複合放大。
- **Long context prefill 痛點**（見 [0.1 為什麼 LLM 生字慢](/llm/00-foundations/why-llm-feels-slow/)）：Agent 每步都重新 prefill 累積 context、TTFT 越跑越長。
- **規劃能力弱**：雲端旗艦在 multi-step planning 上的優勢是公認的；本地 model SFT 規模有限、規劃能力跟雲端有明顯差距。
- **失敗 recovery 弱**：模型發現走錯路時、本地模型較容易繼續錯下去、雲端模型較會自我修正。

實務啟示：本地 agent 在 2026/5 屬於「值得試、但不一定留下」的階段。對寫 code 場景的多數使用者、agent loop 的複雜任務交給雲端旗艦更划算；本地保留給 single-call 跟簡單 tool use 場景。在以下條件成立前、雲端仍占優、可作為 tripwire 重新評估：

- 30B+ 本地模型 SWE-bench tool-use 子集達雲端旗艦的 80% 以上、且推論成本可接受
- 本地推論伺服器（Ollama / LM Studio / oMLX）穩定支援 function calling spec、跨框架行為一致
- Apple Silicon Mac 記憶體預算夠跑「主 model + drafter + KV cache」整套 agent loop 不 swap

任一條件達標時、本地 agent 的成本效益就可能翻轉、值得重新評估。

## 何時過時 / 何時不過時

**不會過時的部分**：

- Agent vs 對話 LLM 的控制流差異 framing。
- Agent loop 五步骨架（感知 / 推理 / 行動 / 觀察 / 終止）。
- 三類失敗模式（context drift / 目標漂移 / tool 誤判）的分類。
- 「適合 agent vs single-call」的判讀框架。
- Termination 策略的 trade-off。
- 人類審查協作 spectrum。

**會變的部分**：

- 具體 agent framework（aider / Cline / LangGraph / OpenAI Assistants 等會持續演化）。
- 模型 agent 能力（本地模型會逐步追上雲端、平衡點會移動）。
- Tool ecosystem 跟 MCP server 普及度（見 [4.6 應用層協議](/llm/04-applications/application-protocols/)）。
- 各家 agent 的最佳 prompt / system prompt（屬於 prompt engineering、本指南不展開）。

看到新 agent framework 時、回到本章的 5 步骨架、3 類失敗模式、5 種人類審查協作模型——這些 dimension 不變、看新工具能很快理解它的定位跟限制。

## 小結

Agent 把控制流的所有權從人類交給 LLM、帶來新的設計問題：失敗從「答錯」變「跑偏」、終止從「使用者結束」變「模型自判」、人類角色從「主導」變「監督」。Agent loop 五步骨架是骨架、context drift / 目標漂移 / tool 誤判是三類典型失敗、「適合 agent vs single-call」要看客觀驗證訊號跟失敗代價、人類審查協作模型要看副作用範圍。本地 LLM 跑 agent 現階段受訓練 + context + 規劃三方面限制、雲端仍是主場。

下一章：[4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/)、把上文的人類審查 spectrum 落到「人類什麼時候介入、怎麼介入」的三時機設計。應用層協議（function calling / structured output / MCP）的層級差異見 [4.6](/llm/04-applications/application-protocols/)。Agent 對本機資源副作用的個人 dev 權限判讀見 [6.2](/llm/06-security/tool-use-permission-model/)、個人工作流跨進 production 服務時的 routing 中樞見 [6.5](/llm/06-security/routing-to-production-security/)。
