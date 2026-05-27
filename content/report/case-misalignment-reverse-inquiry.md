---
title: "案例庫不對齊章節主題時用反向追問取代強掛"
date: 2026-05-27
weight: 146
description: "當案例庫主軸跟章節主題不在同一維度時、引用框架要從『正向掛入』切換到『反向追問』；強掛 case 的根因是『想填滿案例段』的模板配額、而非『想讓讀者看到證據』；反向追問把案例庫的限制當 first-class 訊息傳給讀者、case 變成『沒做 X 的後果』的反證、不是 X 的示範；reviewer 第一輪 fact-check 就能抓出強掛、修正成本高；判讀徵兆是引用句寫不出 case 具體段落 / 多個 case 句型雷同 / 章節主題跟 case 庫主軸不同維度"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Case-driven", "Case-first-workflow"]
---

## 結論

案例庫主軸跟章節主題不在同一維度時、引用框架要從「正向掛入」切換到「反向追問」。正向掛入適用於「案例直接示範章節主題」、反向追問適用於「案例庫主軸是 A、章節主題是 B、A 與 B 雖正交但 A 可作為 B 重要性的反證」。

| 引用框架 | 適用情境                       | 句型骨架                                                         | 典型風險                       |
| -------- | ------------------------------ | ---------------------------------------------------------------- | ------------------------------ |
| 正向掛入 | 案例直接示範章節主題           | 「[case]：看 X 如何展示 Y、對照本章 Z 段」                       | 對齊時無風險                   |
| 反向追問 | 案例主軸不對應、有反向對照價值 | 「[case] 主軸是 A、不直接示範 B；反問『這條撞牆是否被 B 放大』」 | 仍可能像強掛、要明示分層       |
| 強掛     | 不對齊時硬用正向句型（誤用）   | 「[case]：看 X 如何決定 Y」、X、Y 在 case 中無具體段落支撐       | reviewer fact-check 一查就抓出 |

不對齊情境下若硬用正向句型、就會落到強掛。Reviewer 第一輪 audit 抓出後、修正成本是「全段重寫 + 重做案例對照」。先判讀對不對齊、再決定框架、比事後重寫便宜。

## 為什麼強掛會發生

寫作者面對「案例回寫」段時、預設「每章都該有 3-5 個 case 引用」、案例庫實際只有 1-2 個直接相關時、剩下會用 stretch 句型硬掛。stretch 的徵兆通常有三個：

- 用案例提到的 vendor / 服務名稱掛、不用案例揭露的機制掛
- 描述句型抽象、避免具體斷言：「看 X 如何決定 Y」、回查 case 找不到「怎麼決定」
- 把案例次要訊息當主軸：case 主軸是 A、引用句只提 B、B 在 case 是一筆帶過

背後動機是「想讓段落看起來完整」、而非「想讓讀者看到證據」。3-5 個 bullet 變成內在配額、引用變成填空、不是工具。這條動機跟 [#122 Cadence 同質化是模板的隱形維度](/report/cadence-homogenization-in-batch-writing/) 的成因同源 — 模板從「輔助結構」滑落為「強制配額」。

## 反向追問的三步驟

不對齊時、反向追問的標準操作分三步：

1. **誠實標示案例庫主軸差異**：開段直接寫明「本案例庫主軸是 A、直接以 B 為主題的案例較少」、把案例庫的限制當 first-class 訊息傳給讀者。讀者知道後續引用會用反向讀法、而非把它當成直接示範。
2. **把案例當「沒做 B 的後果」**：每個 case 改寫成「在沒有先用 B 收回壓力的前提下、團隊走了哪條路（遷移 / scale-out / vendor 升級）」、case 因此變成 B 重要性的反證。寫作意圖從「示範 B」轉成「示範沒做 B 的代價」。
3. **明示分層追問**：在引用描述句裡寫明追問 — 讀者讀完 case 應主動問「這條撞牆是否被 B 放大」。把追問句寫進引用、讓讀者知道這是反向讀法、而非把 case 當對齊。

三步驟做完、案例段仍保留同樣多的引用、但語意誠實、reviewer fact-check 不會抓出不符。

## Case

backend/01.13 [查詢反模式章節](/backend/01-database/query-anti-patterns/) 在 reviewer audit 階段的具體經驗：

原寫法：3 個 09 模組 case（DoorDash / Zomato / Standard Chartered）被強掛在「Long-Running Transaction」「Query 預算」這類 application-layer query 反模式主題上。

Reviewer fact-check 結果：

- DoorDash case 主軸是 single-primary 寫入吞吐瓶頸、跟 long transaction 無關
- Zomato case 主軸是 TiDB → DynamoDB 遷移、case 完全沒有 query budget 討論
- Standard Chartered case 主軸是合規驅動容量規劃、跟 N+1 / query 預算 stretch

2.5 / 3 case 的引用描述跟 case 原文不符。

修正：改用反向追問框架。開段標示「09 案例庫主軸是規模、vendor 與容量壓力、直接以 query 反模式為主題的案例較少」、三個 case 重寫成「遷移 / scale-out / 合規容量規劃前、是否該先用 query 反模式收回單機容量」的反向追問。Reviewer 二輪通過、3 個 case 全保留、語意誠實。

這個 case 揭露的核心：reviewer 抓到的不是「引用太多」、是「引用方向錯」。改框架後同樣 3 個 case、reviewer 滿意。

## 跟其他卡的關係

本卡跟以下三張卡正交、各自處理 case 引用的不同層問題：

- [#115 案例引用深度跟著 case 類型走](/report/case-type-graded-citation-depth/) — 處理「case 類型決定引用深度」（skeleton / medium / rich）。本卡處理「case 主軸不對應時的引用框架選擇」、是更上游的問題：先判斷對不對齊、再決定引用深度。
- [#120 案例引用三段式段落結構](/report/case-citation-three-part-structure/) — 處理「段落結構順序」（概念 → case → 通用展開）。本卡補 #120 的特殊情境：當 case 主軸不對應時、第二段位置的 case 引用該寫什麼。
- [#122 Cadence 同質化是模板的隱形維度](/report/cadence-homogenization-in-batch-writing/) — 處理「cadence 模板化」。本卡的「強掛」現象背後就是 cadence 模板化的內在動機之一 — 想讓每段都「看起來合規」、結果犧牲語意誠實度。本卡是 #122 在「案例引用」surface 的具體成因 + 修法。

跟 [#116 引用案例要分觀察層 / 判讀層](/report/fact-vs-derive-citation-layering/) 也有張力：#116 強調觀察層 / 判讀層分明、本卡的反向追問可以視為一種「明示分層」的特殊型 — 把整個引用標為「反向讀法」、相當於把整段都歸到判讀層。

補兩張上位卡：

- [#114 Multi-pass review 的 frame 顆粒度盲點](/report/multi-pass-review-frame-granularity-blindspot/) — #146 的「抽象斷言訊號」（「看 X 如何 Y」）就是 #114「keyword bank」機制的具體 keyword 條目。本卡是 #114 機制 1 的應用實例 — 給作者一份可直接 grep 的關鍵字清單。
- [#117 跨多 case 合成的 frame 必須標為章節合成](/report/cross-case-synthesized-frame-must-be-labeled/) — #117 處理「合成必須明示標示」、本卡的「反向追問」也是明示標示的一種 — 把「我用反向讀法解釋案例」明確告知讀者、避免讀者誤以為 case 直接示範了主題。兩者都處理引用層的誠實標示、是姊妹卡。

## 沒這樣做的麻煩

強掛 case 在以下節點會引爆：

- **Reviewer 第一輪 audit**：fact-check 案例內容 vs 引用描述、不對齊馬上抓出。修正要全段重寫。
- **讀者回頭追查**：讀者點進 case 看不到引用句宣稱的內容、會懷疑整章其他斷言的可信度。
- **長期 SSoT 漂移**：案例 case 內容後續更新時、強掛的引用不會跟著更新、變成 stale reference。

更深的代價：強掛 case 違反 AGENTS.md 原則八「情境優先於模板」— 把不同案例塞進同一段落模板、抹平案例的真實主軸。Reviewer 抓到的是表面（描述不符）、根因是寫作者讓模板配額凌駕語意誠實度。

## 判讀徵兆

寫完案例段時、用以下訊號自檢、出現任一就考慮切換到反向追問：

- **抽象句型訊號**：引用句寫成「看 X 如何決定 Y」這種無具體斷言的句型、回查 case 找不到「怎麼決定」的具體段落。
- **句型雷同訊號**：多個 case 引用句型雷同（都是「看 X、對照 Y 段」）、跟 [#122 cadence 同質化](/report/cadence-homogenization-in-batch-writing/) 重疊。
- **維度錯位訊號**：章節主題是 application-layer（query 反模式 / 應用層快取設計）、case 庫主軸是 vendor / 規模 / 容量壓力 — 兩者在不同抽象維度。
- **配額膨脹訊號**：引用句數 ≥ 3 但每個都「邊際相關」、沒有任一個「直接相關」。

四個訊號中出現任一、優先切換到反向追問、別把不對齊強寫成對齊。寫作意圖從「填滿段落」轉成「給讀者誠實證據」、case 段才能撐住 reviewer fact-check。
