# Review 多軸完整性原則

> **角色**：本卡是 `case-first-module-workflow` 的支撐型原則（principle）、被 [SKILL.md](../../SKILL.md) Stage 3、[reviewer-prompts](../reviewer-prompts/) 三個 reviewer prompt 引用。
>
> **何時讀**：Stage 3 設計 reviewer 維度時、發現 review 跑完仍漏抓 systematic 問題時、評估擴充 reviewer 數量時。

## 核心原則

Review 完整性的本質是 *多軸交集*、不是 *單軸深度*。七軸正交、缺任一軸都會 systematic miss 對應類型問題：

| 軸                | 內容                                                     | 缺失時的盲點                                |
| ----------------- | -------------------------------------------------------- | ------------------------------------------- |
| **Frame**         | 一個 reviewer 跑 N 輪不同 frame（生成 / 意圖 / 機會成本 / grep / 反例）| 結構 OK 但意圖 / 機會成本錯            |
| **Instance**      | N 個 reviewer 各自獨立、不同維度                          | 維度盲點、context 污染                      |
| **Surface**       | Body / title / description / heading / link label / MOC hook | Body 完美但 metadata 失準、搜尋入口失效  |
| **Scope**         | 同類風險區（不是只改動區）                                | 既有 corpus 同類違規無解                    |
| **Cadence**       | 跨檔 framing 一致性 / 句型骨架 / 收尾語                  | 單篇合規、連讀預期化                        |
| **Timing**        | 寫作中抽樣 vs batch 後 review                            | 違規累積、修正成本 N 倍                     |
| **Granularity**   | 規則 frame vs 字句層信號                                 | 規則 catch 結構違規、字句層信號漏抓         |

七軸正交：每軸獨立解一類盲點、不重疊；缺任一軸都會 systematic miss 對應類型問題。

## 為什麼多軸、不是單軸越做越深

單軸越做越深的失敗模式：

1. **Frame 軸跑 10 輪、不換 instance 軸**：同一 reviewer 跑 10 輪、catch 仍高度相關
2. **Instance 軸開 10 個 reviewer、不換 frame 軸**：10 個 reviewer 都跑「規則 check」、catch 的盲點相同
3. **Frame + Instance 都做、不管 Surface 軸**：body review 通過、metadata 漏抓
4. **Surface 都做、不管 Cadence 軸**：N 篇個別合規、連讀預期化
5. **Cadence 軸有抽樣、Timing 軸放在 batch 後**：抽樣等於 batch 後 review、修正成本 N 倍

七軸缺任一條、就有對應違規逃過 review。

## 四個上位 axis（簡化記憶）

七子軸可再 group 成四個上位 axis、debug 用上位 axis 比子軸快：

| 上位 axis      | 涵蓋子軸                       | 解什麼                                  |
| -------------- | ------------------------------ | --------------------------------------- |
| **誰來 review** | Instance                       | 維度盲點、context 污染                  |
| **怎麼 review** | Frame + Granularity            | 視角單一、catch 範圍狹窄                |
| **review 什麼** | Surface + Scope + Cadence      | 範圍不全、跨檔 / metadata 漏抓          |
| **何時 review** | Timing                         | 太晚 catch、修正成本爆                  |

當 review 出問題、依四上位 axis 找根因比依七子軸快。

## 預設展開七軸、選窄要證明

把 review 設計 collapse 到單軸是預設行為（最便利）、但 collapse 掉的軸對應違規會 systematic miss：

| 設計時的便利選擇                  | Collapse 的軸  | 系統性盲點                                |
| --------------------------------- | -------------- | ----------------------------------------- |
| 「找一個 reviewer 跑就好」        | Instance       | 維度盲點、context 污染                    |
| 「跑一輪就好」                    | Frame          | 一個 frame 只 catch 一類問題              |
| 「body review 就夠」              | Surface        | Metadata 失準                             |
| 「只 review 改動部分」            | Scope          | 既有 corpus 同類違規無解                  |
| 「單篇 review」                   | Cadence        | Emergence 違規漏抓                        |
| 「等寫完再 review」               | Timing         | Emergence 累積、修正成本 N 倍             |
| 「跑 lint + review 就完整」       | Granularity    | 字句層信號漏抓                            |

預設展開七軸、選窄做要證明 — 跟 [cadence-sampling](./cadence-sampling-in-batch-writing.md) 一樣是 *便利驅動 collapse* 的反向設計。

## Stage 3 設計 reviewer 時的 enumerate 紀律

設計新的 reviewer 維度時、不只看「捕獲哪些違規」、列七軸覆蓋狀況：

| 軸             | 設計時要回答的問題                                            |
| -------------- | ------------------------------------------------------------- |
| Frame          | 這個 review 跑幾種 frame？哪一種是預設、哪些被跳過？           |
| Instance       | Reviewer 是 1 個還是 N 個？維度怎麼分？                       |
| Surface        | Body / metadata / link label / heading 都覆蓋了嗎？           |
| Scope          | Review 的 scope 是「改動區」還是「同類風險區」？              |
| Cadence        | 跨檔 cadence 有沒有抽樣比對？                                 |
| Timing         | 是寫作中 checkpoint、還是 batch 後 review？                  |
| Granularity    | 規則 frame 跟字句 frame 都跑了嗎？                            |

七題回答後、再判斷該不該補軸。某軸沒覆蓋不一定要補（cost vs risk）、但要 *知道沒覆蓋對應什麼盲點*。

## 既有 3-reviewer 設計的七軸對照

本 skill 既有 [reviewer-a-standards](../reviewer-prompts/reviewer-a-standards.md) / [reviewer-b-case-fidelity](../reviewer-prompts/reviewer-b-case-fidelity.md) / [reviewer-c-consistency](../reviewer-prompts/reviewer-c-consistency.md) 三個 reviewer 對七軸的覆蓋：

| 軸             | 覆蓋者                                | 缺口                                          |
| -------------- | ------------------------------------- | --------------------------------------------- |
| Frame          | Reviewer A / B / C 各跑一個 frame      | 單一 reviewer 內未跑多輪                      |
| Instance       | A / B / C 三個獨立 instance            | 覆蓋良好                                      |
| Surface        | C 部分（cross-link）、A / B 未明確列  | Metadata / heading / MOC 未明確涵蓋          |
| Scope          | B 對 case 引用、A / C 未明示           | 改動 scope vs 同類風險區 scope 未明示         |
| **Cadence**    | **無 reviewer 對應**                  | 跨檔 cadence 抽樣 — 由寫作者 Stage 2 補抽樣 |
| **Timing**     | **三 reviewer 都跑在 Stage 3**         | 寫作中 checkpoint — 由 Stage 2 進度 10-20% 補 |
| Granularity    | A 規則 frame、字句層未明示             | 字句層信號（口語修辭等）需擴充                |

結論：Cadence 軸跟 Timing 軸不是靠 reviewer 補、是靠 *Stage 2 寫作流程內抽樣*（詳見 [cadence-sampling-in-batch-writing](./cadence-sampling-in-batch-writing.md)）；不是「加第 4 個 reviewer」、是「補 stage 內 checkpoint」。

## 反模式

| 反模式                                                  | 後果                                                                |
| ------------------------------------------------------- | ------------------------------------------------------------------- |
| 「跑 mdtools lint 就完整」                              | 只覆蓋字面 frame、結構 / 行為 / cadence 全漏                       |
| 「Reviewer agent 跑一遍就完整」                         | Instance 軸覆蓋了、但 frame / surface / scope / cadence 可能漏     |
| 「Review 改動的檔就好」                                 | Scope collapse、既有 corpus 同類違規無解                            |
| 「Body review 完就 ship」                               | Surface collapse、metadata 失準                                     |
| 「Batch 完成後跑 reviewer」                             | Timing collapse、emergence 違規修正成本 N 倍                        |
| 「Review 越多輪越完整」                                 | 同 reviewer 同 frame 跑 10 輪仍 catch 同類問題、缺軸不缺深度       |
| 設計 review 流程不 enumerate 七軸                       | 預設只覆蓋 1-2 軸、其他軸盲點變 systematic                          |
| 把 review 當「validation gate」、不是「多軸完整性」     | 心智模型錯位、把多軸問題誤解為單點 pass/fail                        |

## 跟其他原則的關係

| 原則                                                                  | 關係                                                                                                 |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [cadence-sampling-in-batch-writing](./cadence-sampling-in-batch-writing.md) | 子軸（Cadence + Timing）— 本原則是 review 多軸 anchor、該卡是 cadence + timing 兩軸的 Stage 2 實作 |
| [case-citation-three-part](./case-citation-three-part.md)              | 子軸 — 補 granularity 軸（規則 frame）跟 cadence 軸（單一句構同質化）                                |
| [fact-vs-derive-layering](./fact-vs-derive-layering.md)                | 子軸 — 補 frame 軸（不同 frame 看 case 內部不同層）                                                  |
| [ssot-correspondence](./ssot-correspondence.md)                        | 子軸 — 補 scope 軸（同類 frame 在不同章節是否一致）                                                  |

四張 principle 卡都是 review 多軸的具體軸對應、本原則是 meta-anchor。

## Stage 3 自查清單

設計或審查 reviewer 維度時：

1. **七軸 enumerate 過了嗎**？（不能跳過任一軸的設計選擇）
2. **每個 reviewer 對應哪幾個軸**？（不能 1 reviewer 處理 7 軸）
3. **跨 reviewer 覆蓋是否互斥 + 完整**？（避免重疊或漏抓）
4. **Timing 軸：有 stage 內抽樣還是只 batch 後**？
5. **Cadence 軸：reviewer prompt 有明示跨檔比對嗎、還是靠 Stage 2 抽樣**？
6. **Surface 軸：metadata / heading / link label 有覆蓋嗎**？
7. **Scope 軸：reviewer 跑同類風險區還是只改動區**？

設計新 reviewer 時先列七軸對照表、不是直接寫 prompt。

## Reviewer 數量設計

七軸不代表七個 reviewer — 一個 reviewer 可以 cover 多軸、但要 explicit 標明：

| 審查對象                            | Reviewer 數 | 七軸分配建議                                                                                                                                              |
| ----------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Case-driven 章節擴章               | 3 個        | A 規範（Frame + Granularity）/ B 案例（Scope + Cadence-case子集）/ C 跨章（Surface + Instance）— Timing 由 Stage 2 抽樣補、Cadence 全 surface 由 Stage 2 補 |
| 方法論 / 自我審查                  | 4 個        | 加 D 跨 surface 一致性（Cadence + Granularity 加深）                                                                                                       |
| 一般 PR review                     | 1-2 個      | 規範 + correctness、不需 Cadence + Surface                                                                                                                |
| 高 stakes 內容（資安 / financial） | 4-5 個      | 加 epistemic rigor reviewer（Frame 軸加深、claim / evidence / threats）                                                                                  |

維度設計要對審查對象客製、不是固定一套。

## 判斷 review 漏抓的根因

當 review 跑完發現仍有 systematic 違規漏抓、依七軸 audit 找根因：

| 漏抓現象                          | 缺的軸           |
| --------------------------------- | ---------------- |
| 結構違規漏（章節缺 / link 斷）    | Frame / Granularity |
| 跨檔同類違規漏                    | Scope             |
| Metadata 失準                     | Surface           |
| 連讀預期化                        | Cadence           |
| Batch 末才浮現的問題              | Timing            |
| 一個 reviewer 處理太多盲點        | Instance          |
| 字句層信號漏（口語修辭 / 廢話前綴）| Granularity      |

對策不是「再加一輪」、是「補缺的軸」。
