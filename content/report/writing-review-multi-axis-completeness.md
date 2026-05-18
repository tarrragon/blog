---
title: "寫作 review 是多軸完整性、不是單軸深度"
date: 2026-05-18
weight: 126
description: "寫作 review 的完整性不是單一軸越做越深、是多軸交集都對齊；#83 frame 軸 + #121 instance 軸 + #97 surface 軸 + #95 scope 軸 + #122 cadence 軸 + #124 timing 軸 + #114 granularity 軸、七軸正交、缺任一軸都會 systematic miss；review 設計時要 enumerate 七軸覆蓋狀況、不是只跑一兩個維度做深；是 #79 五維決策對話在 review 工具設計的姊妹卡"
tags: ["report", "事後檢討", "工程方法論", "原則", "抽象層", "Review-design", "Writing"]
---

## 結論

寫作 review 完整性的本質是 *多軸交集*、不是 *單軸深度*。七個軸已經從前面卡片浮現、缺任一軸就會 systematic miss 對應類型的問題：

| 軸                  | 內容                                                  | 缺失時的盲點                                  | 對應卡                                                         |
| ------------------- | ----------------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------- |
| **Frame 軸**         | 一個 reviewer 跑 N 輪不同 frame（生成 / 意圖 / 機會成本 / grep / 反例）| 結構 OK 但意圖 / 機會成本錯              | [#83](../writing-multi-pass-review/)                          |
| **Instance 軸**      | N 個 reviewer 各自獨立、不同維度                       | 單 reviewer 處理多維度互相干擾、context 污染 | [#121](../agent-team-context-isolation/)                      |
| **Surface 軸**       | Body / title / description / heading / link label / MOC hook | Body 完美但 metadata 失準、搜尋入口失效 | [#97](../metadata-surface-in-writing-review/)                  |
| **Scope 軸**         | 同類風險區（不是改動區）                              | 抓不到 corpus 內既有同類違規                  | [#95](../multi-pass-scope-must-cover-risk-zone/)               |
| **Cadence 軸**       | 跨檔 framing 一致性 / 句型骨架 / 收尾語               | 單篇合規、連讀預期化                          | [#122](../cadence-homogenization-in-batch-writing/)            |
| **Timing 軸**        | 寫作中抽樣 vs batch 後 review                         | 違規累積到 batch 末才發現、修正成本 N 倍       | [#124](../emergence-violations-need-in-stream-sampling/)       |
| **Granularity 軸**   | 規則 frame vs 字句層信號                              | 規則 catch 結構違規、字句層（口語修辭 / 廢話前綴）漏抓 | [#114](../multi-pass-review-frame-granularity-blindspot/) |

七軸正交：每個軸獨立解一類盲點、不重疊；缺任一軸都會 systematic miss 對應類型問題。

---

## 為什麼是多軸、不是單軸越做越深

單軸越做越深的失敗模式：

1. **Frame 軸跑 10 輪、不換 instance 軸**：同一 reviewer 跑 10 輪、catch 的問題仍高度相關（#114 已點出）
2. **Instance 軸開 10 個 reviewer、不換 frame 軸**：10 個 reviewer 都跑「規則 check」這個 frame、catch 的盲點相同
3. **Frame + Instance 都做、不管 Surface 軸**：Body review 通過、但 title / description 沒被審、搜尋入口失效
4. **Surface 都做、不管 Cadence 軸**：51 篇個別合規、連讀預期化
5. **Cadence 軸有抽樣、Timing 軸放在 batch 後**：抽樣等於 batch 後 review、修正成本 N 倍

七軸缺任一條、就有對應類型違規逃過 review。

---

## 多軸是預設、單軸是 collapse

跟 [#125 Collapse 是隱形預設](../collapse-is-implicit-default/) 同骨 — 把 review 設計 collapse 到單軸是預設行為（最便利）、但 collapse 掉的軸對應的違規會 systematic miss。

| 設計時的便利選擇                  | 對應 collapse 軸    | 系統性盲點                                |
| --------------------------------- | ------------------- | ----------------------------------------- |
| 「找一個 reviewer 跑就好」        | Instance 軸 collapse | 維度盲點、context 污染                    |
| 「跑一輪就好」                    | Frame 軸 collapse    | 一個 frame 只 catch 一類問題              |
| 「body review 就夠」              | Surface 軸 collapse  | Metadata 失準                             |
| 「只 review 改動部分」            | Scope 軸 collapse    | 既有 corpus 同類違規無解                  |
| 「單篇 review」                   | Cadence 軸 collapse  | Emergence 違規漏抓                        |
| 「等寫完再 review」               | Timing 軸 collapse   | Emergence 累積、修正成本 N 倍             |
| 「跑 lint + review 就完整」       | Granularity 軸 collapse | 字句層信號漏抓                         |

預設展開七軸、選窄做要證明 — 跟 #78 / #79 / #80 / #125 同條結構。

---

## Review 設計時的 enumerate 紀律

設計新的 review 流程（人類 / agent / 自動化）時、不該只看「捕獲哪些違規」、要列七軸覆蓋狀況：

| 軸             | 預設問題                                                     |
| -------------- | ------------------------------------------------------------ |
| Frame          | 這個 review 跑幾種 frame？哪一種 frame 是預設、哪些被跳過？   |
| Instance       | Reviewer 是 1 個還是 N 個？維度怎麼分？                       |
| Surface        | Body / metadata / link label / heading 都覆蓋了嗎？           |
| Scope          | Review 的 scope 是「改動區」還是「同類風險區」？             |
| Cadence        | 跨檔 cadence 有沒有抽樣比對？                                 |
| Timing         | 是寫作中 checkpoint、還是 batch 後 review？                  |
| Granularity    | 規則 frame 跟字句 frame 都跑了嗎？                            |

七題都回答後、再判斷該不該補軸。如果某軸沒覆蓋、不一定要補（cost vs risk）、但要 *知道沒覆蓋對應什麼盲點*。

---

## 七軸不是隨機湊出來、有結構

七軸可以再 group 成三個 *上位 axis*：

| 上位 axis      | 涵蓋                       | 解什麼問題                                  |
| -------------- | -------------------------- | ------------------------------------------- |
| **誰來 review** | Instance 軸                | 維度盲點、context 污染                     |
| **怎麼 review** | Frame + Granularity 軸     | 視角單一、catch 範圍狹窄                   |
| **review 什麼** | Surface + Scope + Cadence 軸 | 範圍不全、跨檔 / metadata 漏抓             |
| **何時 review** | Timing 軸                  | 太晚 catch、修正成本爆                     |

四上位 axis 各自獨立、合起來覆蓋 review 設計的所有 surface。當 review 出問題、依四上位 axis 找根因比依七子軸快。

---

## 反模式

| 反模式                                                  | 後果                                                                |
| ------------------------------------------------------- | ------------------------------------------------------------------- |
| 「跑 mdtools lint 就完整」                              | 只覆蓋字面 frame、結構 / 行為 / cadence 全漏                       |
| 「Reviewer agent 跑一遍就完整」                         | Instance 軸覆蓋了、但 frame / surface / scope / cadence 可能漏     |
| 「Review 改動的檔就好」                                 | Scope 軸 collapse、既有 corpus 同類違規無解                         |
| 「Body review 完就 ship」                               | Surface 軸 collapse、metadata 失準                                  |
| 「Batch 完成後跑 reviewer」                             | Timing 軸 collapse、emergence 違規修正成本 N 倍                     |
| 「Review 越多輪越完整」                                 | 同 reviewer 同 frame 跑 10 輪仍 catch 同類問題、缺軸不缺深度       |
| 設計 review 流程不 enumerate 七軸                       | 預設只覆蓋 1-2 軸、其他軸盲點變 systematic                          |
| 把 review 當成「validation gate」、不是「多軸完整性」   | 心智模型錯位、把多軸問題誤解為單點 pass/fail                        |

---

## 跟其他抽象層原則的關係

| 原則                                                                                            | 關係                                                                                                                              |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| [#83 Writing multi-pass review](../writing-multi-pass-review/)                                  | 子軸（Frame）— #83 是 review 的 frame 軸 anchor                                                                                  |
| [#121 Agent team context 隔離](../agent-team-context-isolation/)                               | 子軸（Instance）— #121 是 review 的 instance 軸 anchor                                                                            |
| [#97 Metadata surface 納入寫作 review 範圍](../metadata-surface-in-writing-review/)            | 子軸（Surface）— #97 是 review 的 surface 軸 anchor                                                                              |
| [#95 Multi-pass review 的 scope 要蓋同類風險區](../multi-pass-scope-must-cover-risk-zone/)     | 子軸（Scope）— #95 是 review 的 scope 軸 anchor                                                                                  |
| [#122 Cadence 同質化是模板的隱形維度](../cadence-homogenization-in-batch-writing/)              | 子軸（Cadence）— #122 是 review 的 cadence 軸 anchor                                                                             |
| [#124 Emergence 違規要 stage 內抽樣](../emergence-violations-need-in-stream-sampling/)         | 子軸（Timing）— #124 是 review 的 timing 軸 anchor                                                                                |
| [#114 Multi-pass review frame 顆粒度盲點](../multi-pass-review-frame-granularity-blindspot/)   | 子軸（Granularity）— #114 是 review 的 granularity 軸 anchor                                                                     |
| [#79 決策對話的五維度](../decision-dialogue-dimensions/)                                       | Sibling meta-卡 — #79 是 decision 多軸 anchor、本卡是 review 多軸 anchor、兩者結構同骨                                            |
| [#125 Collapse 是隱形預設](../collapse-is-implicit-default/)                                   | 上位 driver — 把 review collapse 到單軸是 #125 在 review surface 的具體 instance                                                  |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)                  | 互補 — #82 是錯誤類型 × 工具粒度、本卡是 review 多軸；兩者交集點 = granularity 軸 + timing 軸的設計                              |

---

## 判讀徵兆

| 訊號                                              | 該做的事                                                              |
| ------------------------------------------------- | --------------------------------------------------------------------- |
| 設計新 review 流程沒 enumerate 七軸                | 預設只 1-2 軸覆蓋、補軸對照                                           |
| Review 跑完還是有 systematic 違規漏抓             | 查七軸缺哪條、不是加深 review                                         |
| 同類問題在不同批次反覆出現                        | Scope 軸 collapse、Review scope 應蓋同類風險區、不是改動區            |
| Reviewer 報告都是結構違規、沒字句層               | Granularity 軸 collapse、補字句 frame                                 |
| Batch 完成後 reviewer 抓大量 emergence 違規        | Timing 軸 collapse、補 stage 內 checkpoint                            |
| Body lint 全綠但讀者搜不到 / 看不懂入口            | Surface 軸 collapse、補 metadata review                              |
| 1 個 reviewer 跑 10 輪、catch 範圍仍狹窄          | Instance 軸 collapse、補不同 reviewer instance                       |
| 「我們 review 已經很完整」但常被 user 點漏抓問題  | 自我評估只看單軸、需要對照七軸 enumeration                            |
| 想加 review 第 11 輪                              | 警訊 — 多半是缺軸不缺深度、查七軸覆蓋而不是加輪                       |

**核心**：寫作 review 完整性是七軸交集、不是單軸深度；缺軸不缺深度。設計 review 流程時 enumerate 七軸覆蓋狀況、預設展開、選窄要證明；當 review 報告漏抓 systematic 違規、查的不是「再加一輪」、是「哪一軸沒覆蓋」。
