---
title: "1.7 排錯方法論：用三層架構做故障定位"
date: 2026-05-11
description: "故障定位的分層思考、症狀到層級的對應反射、log 在三層的角色差異、最小可重現的縮減策略"
tags: ["llm", "local-llm-services", "troubleshooting"]
weight: 7
---

本地 LLM 工作流出問題時、第一個本能反應常是「重啟試試看」。本章建立另一種反射：用[三層架構](/llm/00-foundations/three-layer-architecture/)（介面 / [推論伺服器](/llm/knowledge-cards/inference-server/) / 模型）的視角先確認「哪一層壞」、再針對該層做具體診斷。這個方法不依賴記住每個工具的具體錯誤訊息、跨工具世代都成立。

具體錯誤訊息對照表（「`address already in use` 要這樣修」「`model not found` 要那樣修」）不在本章——這些隨工具版本變、查 release notes 跟 GitHub issue 更快。本章寫的是「換工具之後仍成立」的排錯思維。

## 本章目標

讀完本章後、你應該能：

1. 看到症狀時、先定位是介面 / 伺服器 / 模型哪一層的問題。
2. 知道在每一層該看什麼 log。
3. 用「最小可重現」策略快速縮減問題範圍。
4. 識別「跨層級的誤判」常見模式、把 server 層問題正確歸位、避開瞎調 model 的繞路。

## 故障定位的核心原則：先確認哪一層壞

模組零 [三層架構](/llm/00-foundations/three-layer-architecture/) 的視角延伸到排錯：故障可能落在介面層（Continue.dev / Cursor 等 IDE 整合）、伺服器層（Ollama / LM Studio / llama.cpp）、或模型層（權重檔本身的能力 / 量化選擇）。在不知道哪一層壞之前、任何修法都是亂槍打鳥——重啟 Continue.dev 解不了模型量化太激進的問題、重 pull 模型解不了 IDE 設定錯的問題。

先定位再修補的 ROI 高於直接修補、因為沒有定位的修法常常掃過正確答案還不知道是哪個動作生效。定位用的工具不複雜：

- **直接 curl 伺服器 API**：繞過介面層、直接驗證伺服器是否回應正常。
- **`ollama ps` / 等價指令**：看伺服器層 model 狀態、確認 model 真的載入。
- **換 model 試試**：同樣 prompt、不同 model 表現一致就是介面 / 伺服器層、不一致就是 model 層。
- **換 prompt 試試**：簡單 prompt OK、複雜 prompt 崩、可能是 context 長度或 model 容量問題。

這四個動作能 cover 90% 的定位需求。學會這個反射、排錯時間大幅縮短。

## 症狀到層級的對應反射

不同症狀對應到不同最有可能的故障層、建立對應反射能省下大量試錯時間。下表是寫 code 場景常見症狀的對應：

| 症狀                                  | 最可能層級        | 第一步驗證                                                 |
| ------------------------------------- | ----------------- | ---------------------------------------------------------- |
| Continue.dev 完全沒回應               | 介面層 / 伺服器層 | curl 伺服器、看伺服器是否正常                              |
| Continue.dev 報「connection refused」 | 伺服器層          | 伺服器沒在跑 / port 不對                                   |
| Continue.dev 顯示請求送出但無回應     | 介面層 / 伺服器層 | curl 同 prompt、比較行為                                   |
| 回答內容亂碼 / 一直重複               | 模型層            | 換[量化](/llm/knowledge-cards/quantization/)等級或換模型試 |
| 回答邏輯離譜 / 答非所問               | 模型層            | model 能力不足、考慮換大一點 model                         |
| TTFT 異常變長                         | 模型層 / 推論機制 | prompt 變長了？KV cache 失效？                             |
| 整台 Mac 變慢、Ollama 沒崩            | 伺服器層 / 系統   | 記憶體 swap、看 Activity Monitor                           |
| Ollama 自己 crash                     | 伺服器層          | 看 server log、通常 OOM 或 bug                             |
| 跨 session 設定遺失                   | 介面層            | IDE 設定沒存或被 reset                                     |
| Tab autocomplete 完全不觸發           | 介面層            | autocomplete model 沒配對 / 沒 pull                        |

對應的具體驗證指令範例：

- **回答亂碼 / 重複**：`ollama list` 確認當前 model tag、改跑 `ollama run <較高量化版本>`（例如 Q4 → Q5）；同 prompt 換 model 確認是不是 model 本身能力問題、不是伺服器。
- **TTFT 異常變長**：`ollama ps` 看 model 是否被 unload 又重載（[keep_alive](/llm/01-local-llm-services/ollama/#模型常駐keep_alive) 太短）；檢查 prompt 字數是否暴增（10K+ tokens 進入 [prefill](/llm/knowledge-cards/prefill/) 痛點區）。
- **Ollama 自己 crash**：[launchd service](/llm/knowledge-cards/launchd-service/) 模式看 `/opt/homebrew/var/log/ollama.log`、前景模式看啟動 terminal 的 stderr。

這張表的核心訊號：

- 「沒回應」「connection 系」→ 通常 server 層。
- 「內容怪」「答非所問」「重複」→ 通常 model 層。
- 「設定怪」「快捷鍵不對」→ 通常介面層。
- 「整機卡」→ 系統資源、不一定哪層的「bug」、可能是規格不夠。

把這個 mapping 內化、看症狀立刻有第一手猜測、不用每次從零思考。

## Log 在三層的角色差異

每一層的 log 看的東西不同、用法不同：

### 介面層 log

- **位置**：IDE plugin 的 console（VS Code Developer Tools、JetBrains 的 plugin log）。
- **看什麼**：請求是否發出、發到哪個 endpoint、回應 status code、parse error。
- **常見訊號**：請求根本沒發 → 介面層配置錯；請求發了但伺服器拒 → 伺服器層；請求成功但 parse 失敗 → 介面層或伺服器層回應格式不對。

### 伺服器層 log

- **位置**：Ollama 在 `~/.ollama/logs/server.log` 或類似位置、LM Studio 在 console 輸出、llama.cpp 在啟動 terminal。
- **看什麼**：模型載入過程、推論進度、error trace、記憶體狀態。
- **常見訊號**：載入 model 卡住 / 失敗 → model file 損壞或記憶體不足；推論時 OOM → 量化太激進或 context 太長；連線錯誤 → port 配置或 host binding。

### 模型層的觀察訊號

模型層通常沒有獨立的 log——權重檔本身不會 log、行為要透過伺服器層觀察。判讀模型問題的訊號通常是：

- 「載入成功、推論時崩」→ 量化等級或記憶體配對問題。
- 「載入成功、推論結果差」→ 模型能力或量化品質問題。
- 「不同 prompt 表現不一致」→ 可能是 model 對特定 pattern 弱、不是 bug。

模型層問題多半不是「壞了」、是「能力上限」——換更大模型或調量化是主要解法、不是「修 bug」。

### log level 預設夠用、針對性提升

實務上 default log level 提供的訊息已涵蓋多數排錯需要；全部開 verbose 反而把 noise 蓋過 signal、要找的關鍵錯誤被淹沒。有問題時針對該層提升 log level（其他層保持 default）、定位完再降回來。

## 最小可重現的縮減策略

症狀複雜時、把問題縮到最小、再逐步加回來。這個方法在所有軟體 debug 都通用、套用到 LLM 場景的具體流程：

1. **直接 curl 伺服器、用最簡 prompt 復現**：
    - 繞過介面層、確認伺服器本身行為。
    - prompt 用 `"Hello"` 這種最短的、排除 prompt 複雜度因素。
    - 如果這步就崩 → 伺服器 / 模型層問題、可以排除介面層。

2. **換不同 model 試**：
    - 同樣 prompt、換 `gemma4:e4b` 或 `llama3.2:1b`。
    - 不同 model 都正常 → 原 model 問題。
    - 不同 model 也崩 → 伺服器層問題。

3. **換不同伺服器試**：
    - Ollama 接不上、用 LM Studio 同模型試。
    - 兩個都崩 → 模型或系統層問題。
    - 一個好一個壞 → 該伺服器特有問題。

4. **改變一個變數一次**：
    - 每次只改一個變數（設定 / model / IDE 重啟三選一）、確保行為變化能對應到具體動作。
    - 每次只改一項、觀察行為變化。

5. **記錄每一步**：
    - 排錯 30 分鐘還沒解時、開始會忘記試過什麼。
    - 簡單 notebook 記錄「改了什麼、行為怎麼變」、避免轉圈。

這個方法看起來慢、實際上比「亂試一通」快很多。亂試的代價是「以為改了 A 沒效、其實改 A 跟改 B 互相抵銷、不知道」。最小可重現是 disciplined approach、值得花時間建立習慣。

## 跨層級的常見誤判

排錯時常踩的陷阱是「把某層的問題誤判成另一層」、修錯方向白費力氣。常見誤判模式：

### 把伺服器問題誤當模型問題

例：Ollama 因為 port 被佔啟動失敗、IDE 看到 connection refused、誤以為「model 載不起來、需要換 model」。實際上換 model 也救不了、要看 server log 才知道是 port 問題。

判讀：connection 系問題 → server 層、不是 model 層。

### 把模型問題誤當伺服器問題

例：用 Q3 量化跑 7B 模型、輸出全是亂碼、誤以為「Ollama bug」、開 issue 報。實際上是量化太激進、模型本身輸出崩、換 Q4 就好。

判讀：「server 看起來正常、輸出怪」→ 通常 model 層、改量化或換 model。

### 把介面問題誤當伺服器問題

例：Continue.dev 的 `config.json` 寫錯 `apiBase`、IDE 顯示 connection error、誤以為「Ollama 掛了」。實際上 Ollama 正常、curl 過得去、IDE 配置錯。

判讀：curl 過得去、IDE 過不去 → 介面層配置問題。

### 把系統資源問題誤當軟體 bug

例：32GB Mac 跑 31B + 同時開大量 app、Mac 整體變慢、誤以為「Ollama 越來越慢」。實際上是記憶體 swap、Ollama 沒問題。

判讀：Activity Monitor 看 Memory Pressure 變紅 / swap 大量、是系統資源、不是軟體 bug。

### 把 prompt 問題誤當模型問題

例：給 model 超長 [context](/llm/knowledge-cards/context-window/)（30K token）、[TTFT](/llm/knowledge-cards/ttft/) 30 秒、誤以為「model 變慢了」。實際上是 [prefill](/llm/knowledge-cards/prefill/) 階段需要時間、跟 model 沒變慢無關。

判讀：短 prompt 正常、長 prompt 慢 → prefill 問題、可預期、不是 bug。

每種誤判的根因都是「症狀對應到錯的層級」。內化「症狀 → 層級」對應反射、能避開多數誤判。

## 排錯工具箱

四個基本工具能 cover 90% 的排錯場景：

### curl

- **角色**：直接打伺服器 API、繞過介面層。
- **用法**：`curl http://localhost:11434/api/version` 看伺服器是否回應、`curl http://localhost:11434/v1/chat/completions` 帶最簡 prompt 試完整流程（11434 是 Ollama 預設 [port](/llm/knowledge-cards/port-and-localhost/)、見 [1.0 Ollama](/llm/01-local-llm-services/ollama/)）。
- **價值**：排除介面層、確認伺服器層行為。

### `ollama ps` / 等價指令

- **角色**：看伺服器層當前 model 狀態。
- **用法**：`ollama ps` 列出載入記憶體的 model、看 size、idle timer。
- **價值**：確認「我以為載入了」跟「真的載入了」是否一致；看記憶體佔用是否合理。

### Activity Monitor / system monitor

- **角色**：看系統資源狀態。
- **用法**：Memory Pressure 是否變紅、CPU / GPU 使用率、swap 量、過熱降頻。
- **價值**：區分「軟體 bug」跟「規格不夠」。多數本地 LLM 慢的問題是規格、不是 bug。

### IDE 開發者工具

- **角色**：看介面層請求 / 回應。
- **用法**：VS Code 的 Help → Toggle Developer Tools、看 Network tab、看 Console。
- **價值**：確認介面層真的把請求發出去、看 server 回什麼。

這四個工具學會用、寫 code 場景 90% 的排錯都能處理。剩 10% 的 deep issue（如 driver 問題、模型權重檔損壞、framework 內部 bug）需要更專業的工具、但這 10% 對寫 code 使用者來說、通常該求助社群或回報 maintainer、不是自己 debug。

## 排錯流程的決策樹

把上面的內容整合成一個流程：

```text
症狀出現
  ↓
curl 伺服器（伺服器層活著嗎）
  ├─ curl 失敗 → 看 server log（伺服器層問題）
  │   ├─ port 衝突 → 改 port 或 kill 舊 instance
  │   ├─ model 載入失敗 → 看 file / 記憶體
  │   └─ crash → bug report、看版本是否最新
  └─ curl 成功 → 介面層或 model 層問題
      ↓
      換最簡 prompt 試（model 在簡單 prompt 上正常嗎）
      ├─ 簡單 prompt 也崩 → model 層問題
      │   ├─ 換 model 試 → 不同 model 都崩 → 系統或伺服器
      │   └─ 同 model 換量化等級 → 量化太激進
      └─ 簡單 prompt OK、複雜 prompt 崩
          ↓
          看 prompt 長度跟 context 限制
          ├─ context 超出 → 縮短 prompt 或換 long-context model
          └─ context 在範圍內 → model 能力上限、考慮換大 model
              ↓
              （如果伺服器、prompt、model 都檢查過還是壞）
              介面層配置問題
              ├─ 看 IDE plugin developer console
              ├─ 比對 config.json 跟最簡 working example
              └─ reset 設定後重試
```

這棵樹不是「按順序跑完」、是「定位後對應到具體分支」。學會用症狀直接 jump 到對應分支、不必每次從根跑起。

## 何時不適用本章方法論

本章「三層架構定位」假設「單機、單 user、單一伺服器實例、人在駕駛位」的個人開發場景。以下情境的方法論需要擴充：

| 情境                       | 為什麼三層定位失效 / 需要擴充                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Multi-tenant 共用伺服器    | 多個 user 共用 Ollama instance、症狀可能是「不同 user 的請求互相干擾」、單純三層定位看不出、需加 user / session 層                       |
| 容器化部署（Docker / k8s） | 介面 / 伺服器之間多一層網路命名空間、connection refused 可能是 container network 配置、不是伺服器層                                      |
| 跨機器分散式 inference     | 伺服器層拆成多 process / 多 node、單一 `ollama ps` 看不到全貌、需 cluster-level observability                                            |
| 後端 production 服務       | 排錯依賴 SLI / SLO + 監控告警支撐、而非「重啟試試」的探索式做法；本章方法論偏個人開發、production 場景需另尋資料中心 SRE 教材            |
| Agent loop 內部失敗        | 失敗可能在 LLM 規劃 / tool execution / state machine 任一處、超出三層定位、見 [4.4 Agent 架構](/llm/04-applications/agent-architecture/) |

本章方法論的甜蜜點是「個人 Mac、一個 IDE、一個 Ollama instance」的場景。離開這個甜蜜點、要把「三層」擴充成更多層（user / network / cluster）、或改用 production-grade 觀察工具。

## 何時過時 / 何時不過時

**不會過時的部分**：

- 三層架構視角排錯（介面 / 伺服器 / 模型）。
- 「先定位、再修補」的反射。
- 最小可重現的縮減策略。
- 五類跨層級誤判模式的識別。
- 四個基本工具的概念（curl / process status / system monitor / dev tools）。

**會變的部分**：

- 具體錯誤訊息文字（隨 Ollama / LM Studio / Continue.dev 版本變）。
- log 檔位置（隨工具更新可能調整）。
- 特定指令名稱（如 `ollama ps` 將來可能改名）。
- 特定工具的開發者面板路徑。

換工具或工具升級之後、本章的方法仍適用、只需要重新對應到「新工具的對應指令在哪」。看到新錯誤訊息時、回到三層架構定位、用最小可重現縮減——這比 google 錯誤訊息字面快得多、也比「重啟一次再試」可靠得多。

## 下一章

下一章：[模組二 LLM 的數學基礎](/llm/02-math-foundations/)、或回到 [模組一首頁](/llm/01-local-llm-services/) 看其他章節。
