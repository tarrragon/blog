---
title: "跨輪 review 停止訊號是 frame 涵蓋、不是 finding 數遞減"
date: 2026-05-27
weight: 148
description: "判斷「該不該再來一輪 review」的訊號是『frame 軸是否還有未動』、不是『上一輪 finding 變少』；多輪 review 的 ROI 不是 monotonically decreasing、而是 frame 切換的質性轉換 — Round N 用新 frame 通常仍會抓出 substantial finding、但內容從 surface compliance 往深層 structural issue 走；停止訊號是「下一輪可用的新 frame 已經想不出來」、不是 finding 數遞減；本卡填補 #114 / #126 / #147 沒覆蓋的「何時夠了」判讀缺口"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Multi-round-review", "Frame-coverage"]
---

## 結論

判斷「該不該再來一輪 review」的訊號是「frame 軸是否還有未動」、不是「上一輪 finding 變少」。

兩種訊號的對比：

| 訊號軸         | 判讀方式                                        | 何時觸發停止                                                                      | 風險                                       |
| -------------- | ----------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------ |
| Finding 數遞減 | Round N 比 Round N-1 finding 少 → 邊際遞減 → 停 | finding 數明顯下降                                                                | 用錯訊號 — 多輪 review 通常 finding 不遞減 |
| Frame 涵蓋     | 想不出能 catch 新東西的新 frame → 停            | 七軸（frame / instance / surface / scope / cadence / timing / granularity）全動完 | 需要主動規劃 frame、不是 reactive 判讀     |

多輪 review 的 ROI 不是 monotonically decreasing。每輪用新 frame 通常仍會抓出 substantial finding、但內容會從 surface compliance（編號 / 連結 / 案例對應）往深層 structural issue（cadence / enumeration / 反向引用斷裂）走。停止訊號是「下一輪可用的新 frame 已經想不出來」、不是「上一輪 finding 變少」。

## 為什麼 finding 數不是停止訊號

三個原因讓「finding 遞減」誤導：

1. **每輪修法會 surface 下一輪問題**：修 cadence 1.0 會把 cadence 從位置 X 漂到位置 Y、變成 cadence 2.0；修 enumeration 不窮盡會 surface 反向引用斷裂（補完 enumeration 才看見哪些章節該引）。修 = 暴露 new surface。
2. **frame 切換等於進入新的問題空間**：Round 1 用 compliance frame catch 不到 cadence 同質化、Round 2 用 cadence frame catch 不到 enumeration 不窮盡、Round 3 用 steelman frame catch 不到 outbound impact。三輪 frame 正交、finding 互不重疊、自然不會遞減。
3. **finding 深度遞增、不是寬度遞減**：Round N 通常需要 frame 更精緻才能 catch、但 catch 到的問題更接近本質。Raw count 可能不變或增加、但每個 finding 的修正成本跟價值都更高。

把 finding 遞減當停止訊號、會在「正在進入更深層 issue」的時刻錯誤收尾。

## 跨輪 review 的質性 transition 模式

實證觀察、跨輪 review 的 finding 內容會走以下 transition：

| 階段       | 主要 frame              | finding 性質                             | 修法成本         |
| ---------- | ----------------------- | ---------------------------------------- | ---------------- |
| Surface    | Compliance / fact-check | 編號、連結、案例對應、規範違反           | 低（機械修）     |
| Cadence    | 字句層 / 模板偵測       | 句型骨架同骨、廢話前綴、地區漂移         | 中（重寫局部）   |
| Structural | Steelman / 讀者旅程     | enumeration 不窮盡、稻草人、反向引用斷裂 | 高（補實質內容） |
| Meta       | Self-application        | 規則自審、同義變體、frame 切換規劃       | 中（疊代擴張）   |

實證的階段不一定按此順序、但通常從 surface 開始、隨 frame 切換往深層走。Meta 階段在 surface / cadence / structural 都修完後仍能 surface 新問題 — 因為它檢查的是「修法過程本身」、屬另一個維度。

每個階段內、frame 用完就遞減；跨階段、新 frame 上線就重新進入「新一輪不遞減」狀態。

## 停止訊號的 4 個判讀

何時可以判定「真的夠了」？四個判讀齊備、再停：

1. **七軸 frame 全動完**：per [#126 review 七軸](/report/writing-review-multi-axis-completeness/)、frame / instance / surface / scope / cadence / timing / granularity 七軸都用過、沒有遺漏的觀察維度
2. **新 frame 想不出來**：團隊腦力激盪後想不出「能 catch 上一輪 frame 抓不到的東西」的新 frame、代表問題空間已涵蓋
3. **Finding 性質回到 surface**：若新 frame catch 到的 finding 又退回到 surface（編號、連結、低密度 cadence）、代表 structural / meta 維度已穩定
4. **修法成本反轉**：若修一個 finding 的成本超過讀者實際感受的價值、繼續修不划算 — 用 [#125 collapse](/report/collapse-is-implicit-default/) 的提醒、避免完美主義 collapse 到無止境疊代

四個訊號齊備、停的判讀是 evidence-based 而非 finding 數驅動。

## Case

本次 backend 5 章 + 1 report 卡的 3 輪 review 實證：

- **Round 1**（compliance / 案例 / 跨章 frame）：12 個 finding、surface 層為主、編號 mis-cite + case mis-citation
- **Round 2**（cadence / 旅程 / title frame）：10 個 finding、cadence 同骨化 + 影片詞彙橋斷裂 + 時序總表缺失
- **Round 3**（self-application / steelman / outbound frame）：**16 個 finding**（比 Round 1 / 2 還多）、三段式 cadence 從位置漂移 + enumeration 稻草人 + 單向反向引用斷裂

Total 38 個 finding、9 個 reviewer instance、零重疊。Round 3 finding 數反而比 Round 1 / 2 多、但 Round 3 是 review 自然停下的點 — 因為「想不出能 catch Round 3 frame 抓不到的東西的 Round 4 frame」。

判讀停止的依據是 frame 涵蓋（七軸動完、Round 4 frame 想不出來），不是 finding 數遞減（Round 3 數還在升）。若按 finding 遞減判讀、Round 1 → Round 2（12 → 10）就該停、會錯過 Round 3 抓出的 16 個結構性問題。

## 跟其他卡的關係

本卡跟以下卡片正交、處理「多輪 review 何時停」這個 #114 / #126 / #147 沒覆蓋的問題：

- [#114 Multi-pass review 的 frame 顆粒度盲點](/report/multi-pass-review-frame-granularity-blindspot/) — 說明「需要不同 frame」。本卡補完：知道需要不同 frame 後、判讀「何時 frame 涵蓋夠」的訊號。
- [#126 寫作 review 是多軸完整性、不是單軸深度](/report/writing-review-multi-axis-completeness/) — 列七軸。本卡用七軸作為停止判讀的具體 checklist、補強 #126 在「執行收尾」這層的判讀工具。
- [#147 規範化跟自審是兩種認知任務](/report/rule-codification-vs-self-audit/) — 說明「規範化第一次落地不可能完整、需要疊代」。本卡補完：疊代到什麼時候停？停止訊號跟疊代啟動訊號是不同維度。
- [#125 Collapse 是隱形預設](/report/collapse-is-implicit-default/) — 「無止境疊代」是 collapse 的另一個極端（從「規範化單軸 collapse」反向到「review 過度 collapse 完美主義」）。本卡用「修法成本反轉」訊號避免這個反向 collapse。

## 判讀徵兆

跨輪 review 中、出現以下訊號時要重新評估「該繼續還是該停」：

- **新 frame 卡住訊號**：規劃下一輪 review 時、想了 30 分鐘想不出「能 catch 新東西的 frame」— 是「frame 涵蓋已足」的強訊號
- **Finding 性質退化訊號**：新一輪 finding 退回 surface 層（編號 / 連結這類低密度議題）、structural / meta 層沒新東西 — 代表深層 issue 已穩定
- **修法成本超過邊際價值訊號**：修一個 finding 要動 50+ 行、但讀者實際感受改善有限 — 修法 ROI 已下降
- **Frame 重複訊號**：新一輪 reviewer 的 finding 跟上一輪有重疊（per [#114](/report/multi-pass-review-frame-granularity-blindspot/) 同 frame 多輪 catch 高度相同）— 代表 frame 軸沒換、再跑無增益

四個訊號中出現任二、可以判定「真的夠了」。出現任一、繼續但要規劃 frame 切換。沒有任一、按七軸繼續推進。

「夠了」的判讀本身是 evidence-based、不是直覺 — 用上面四個訊號當 checklist、比「finding 變少就停」可靠。
