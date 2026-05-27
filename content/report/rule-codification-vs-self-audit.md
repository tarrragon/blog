---
title: "規範化跟自審是兩種認知任務、立規範當下無法保護同批稿件"
date: 2026-05-27
weight: 147
description: "把反模式抽象成規範卡、跟在自己稿件辨識該反模式的局部實例、是兩種不同認知任務；前者用『歸納共同特徵』的視角、後者用『局部 pattern matching』的視角；用相同概念詞、走不同神經路徑；案例：#146 卡描述「看 X 如何 Y」是反模式、同 batch 5 篇章節仍有 11 處該句型未被作者察覺；修法是規範化當下立刻把規範轉成 grep keyword、對同 batch 稿件主動 sweep；不修則 #122 主題語意 attractor 跟 #124 emergence 違規會在同 batch 內持續累積"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Self-review", "Rule-codification"]
---

## 結論

把反模式抽象成規範卡、跟在自己稿件辨識該反模式的局部實例、是兩種不同認知任務。同一個作者可以清楚寫下「『看 X 如何 Y』是抽象斷言反模式」、同一個 batch 內已寫的 5 篇章節仍能有 11 處該句型未被察覺。

兩個任務對比：

| 認知任務 | 視角               | 處理動作                      | 觸發條件                           |
| -------- | ------------------ | ----------------------------- | ---------------------------------- |
| 規範化   | Outside-in（歸納） | 找 N 個 case 的共同特徵、命名 | 看到不同 case 重複出現同類問題     |
| 自審     | Inside-out（比對） | 把規範當 grep keyword、掃稿件 | 主動把卡片「判讀徵兆」套到自己文字 |

兩者用相似概念詞、走不同神經路徑。立規範時注意力放在「為什麼這 pattern 是反模式」、自審時注意力要放在「我這句話符不符合該 pattern」。前一個動作完成、不會自動觸發後一個動作。

## 為什麼立規範後仍會犯

三個認知機制讓兩者解耦：

1. **抽象化耗用認知頻寬**：寫下「N+1 query 反模式」這個概念時、作者的工作記憶被 pattern 的本質、對比、邊界佔滿、不會同時掃描自己已寫過的稿件
2. **規範化視角是 outside-in**：規範化把 N 個實例抽象成 1 個模式、看的是「共同特徵」；自審視角是 inside-out、從自己具體句子往外比對、看的是「這句屬不屬於這個 pattern」
3. **同 batch 主題語意 attractor**（見 [#122 Cadence 同質化是模板的隱形維度](/report/cadence-homogenization-in-batch-writing/)）：規範化之前寫的稿件、受同主題 / 同 constraint 拉到相似句型；規範化動作本身不會 retroactive 修這些句型、需要主動 sweep

這三個機制累積起來、「我剛寫完反模式定義」不等於「我能在自己稿件抓出該反模式的所有實例」。

## Case

backend 模組 5 篇章節（5.9 / 0.18 / 0.19 / 9.13 / 1.13）的修正過程：

1. **Round 1 reviewer audit** 抓出 1.13 章節案例引用 mis-cite、修正後寫成 [#146 案例庫不對齊章節主題時用反向追問](/report/case-misalignment-reverse-inquiry/) 卡片。#146 明確列出「抽象斷言訊號：『看 X 如何 Y』這類無具體斷言的句型是反模式」、並作為「判讀徵兆」的四訊號之一。
2. **#146 卡寫完當下**、作者同 batch 已寫的 5 篇章節 case 段內仍有 11 處「看 X 如何 Y」句型未被察覺、未被修正。
3. **Round 2 reviewer** 用 cadence frame 跑 grep（直接拿 #146 描述的反模式當 keyword）、抓出全部 11 處、Round 2 修正後用具體事實 / 數字 / 機制斷言取代。

這個案例的諷刺感正是本卡的核心：作者剛寫完規範、自審能力卻沒同步提升。中間缺的是「規範化 → grep 自審」這條主動觸發路徑。Round 2 reviewer 補上的就是這條路徑、但理想上規範作者自己當下就該做。

## 修法

三種觸發機制可以接在規範化動作後：

### 1. 立規範後立刻跑 keyword grep

把新立的規範轉成 `rg` 可掃的 pattern、對所有同 batch（甚至既有）稿件跑一次 grep：

```bash
# 例：#146 立下後的 keyword grep
rg "看 .{1,20}如何|看 .{1,20}的決|看 .{1,30}的策略|看 .{1,30}的差異" content/<scope>/
```

不對齊就修。這條 routine 應該寫進規範卡本身的「修法」段、作為規範 enforcement 的標準步驟。

### 2. 把規範卡的「判讀徵兆」當 self-audit checklist

每張 report 卡的「判讀徵兆」段（如 #146 列的 4 訊號：抽象句型 / 句型雷同 / 維度錯位 / 配額膨脹）就是現成的 self-audit checklist。立規範當下、作者應該主動把這 checklist 套到自己同 batch 稿件 — 而非預設「我剛寫完應該不會犯」。

### 3. 用 reviewer 跑 in-stream sampling

如 [#124 emergence-class 違規 enforcement 時機](/report/emergence-violations-need-in-stream-sampling/) 描述、emergence-class 違規（cadence 同質、抽象斷言這類）字面 hook 抓不到、要 reviewer in-stream 才能發現。本案 Round 2 cadence reviewer 是這個機制的應用、但理想上規範作者自己應該先做、reviewer 是補位。

三種機制按介入點分層：grep 是字面層、checklist 是結構層、reviewer 是 frame 層。立規範後三層都跑一次、覆蓋率最完整。

## 跟其他卡的關係

- [#122 Cadence 同質化是模板的隱形維度](/report/cadence-homogenization-in-batch-writing/) — 解釋「為什麼同 batch 會有 systemic 違規」的成因機制（主題語意 attractor）。本卡補完：規範化動作本身無法解這個 attractor、需要主動 sweep 才能切斷。
- [#124 Emergence-class 違規規則化不了、要 stage 內抽樣](/report/emergence-violations-need-in-stream-sampling/) — 解釋「什麼時候 enforcement 最有效」（batch 進度 10-20%）。本卡補一個更早的時機點：立規範當下立刻 sweep 同 batch、不必等 batch 進度推進。
- [#114 Multi-pass review 的 frame 顆粒度盲點](/report/multi-pass-review-frame-granularity-blindspot/) — 解釋「為什麼同 reviewer 多輪抓不到不同東西」、提出 keyword bank / reader simulation / self-criticism 三機制。本卡是 #114 在「規範作者本人」這個 reviewer 角色的具體實例：作者剛寫完規範、仍需主動換 frame 才能自審。
- [#146 案例庫不對齊章節主題時用反向追問取代強掛](/report/case-misalignment-reverse-inquiry/) — 本卡的 case 來源。#146 才剛立規範、同 batch 仍犯該規範、是「規範化 ≠ 自審」最直接的諷刺證據。本卡跟 #146 互為驗證關係：#146 給出規範本身、本卡解釋為什麼立完規範還需要主動 sweep。

## 判讀徵兆

立規範後若不主動 sweep 同 batch、會出現以下訊號：

- **諷刺對映訊號**：規範卡描述的「反模式」可以一字不改貼回自己稿件、自己仍意識不到。最強訊號、出現代表 inside-out 視角完全沒啟動。
- **跨稿件 catch 訊號**：該規範立下後一週內 reviewer audit 跨稿件、catch 出該規範的多處違規（≥ 3 處）。代表規範化跟自審之間斷層。
- **自審盲區訊號**：自己 review 自己稿件時、卡片描述跟稿件實例之間的「相似度」感官弱（明明 textbook 案例、自己讀不出來）。代表規範化耗光認知頻寬、自審視角沒上線。
- **品質非單調訊號**：同 batch 多篇文章在規範化前後寫的、品質沒有顯著差異。代表規範化未轉換成執行力。

出現任一訊號、表示「規範化 → 自審」這條路徑沒接通。立刻跑修法的三層機制（grep / checklist / reviewer）對自己稿件做 sweep。
