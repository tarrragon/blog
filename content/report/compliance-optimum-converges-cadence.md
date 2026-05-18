---
title: "多重硬規範同時生效會把 cadence 推向便利解"
date: 2026-05-18
weight: 123
description: "當 N 個硬規範同時 enforce（11 章節結構 + 表格深化 + sweet spot 行數 + lint 規則）、找到一個「都通過」的 framing 後、批量寫作會把這個 framing 複製到所有檔案；cadence 同質化不是違規、是「合規最佳解」的副作用；對策是把 framing 多樣性也納入硬規範、或拉開 constraint 讓多個 framing 都有合規路徑；是 #67 在「批量寫作」的具體機制展現"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Constraint-design", "Batch-writing"]
---

## 結論

多個 constraint 同時 enforce、批量寫作就會把 cadence 收斂到「最便利合規解」。這不是違規、是 *合規最佳解的副作用*。

機制：

1. N 個硬 constraint 同時 enforce（章節結構 / 表格深化 / 行數範圍 / lint 規則 / frontmatter 完整）
2. 寫第一篇時 Claude 找到一個 framing 同時滿足所有 N 個 constraint
3. 寫第二篇起、複製這個 framing 是 *合規 + 省 token + 風險最低* 的選擇
4. 51 篇後、cadence 已經 collapse 到一個 framing、雖然每篇都合規

backend/07 案例：「11 章節 + 表格延伸段 + 130-160 行 + 零 emoji + 案例回寫」5 個 constraint 同時 enforce 下、「四件事 → 任一缺失就是 X 邊界的待補項目」是合規最便利 framing。51/51 都用了。

---

## Constraint 越多、cadence 收斂越快

關鍵直覺：constraint 是 *過濾器*、constraint 越多、能通過所有過濾器的 framing 種類就越少；批量寫作下、Claude 會選 *第一個發現的可行 framing* 並複製。

| Constraint 數 | 可通過的 framing 種類 | 批量同質化風險 |
| ------------- | --------------------- | -------------- |
| 0-1（自由寫）| 幾乎無限              | 低             |
| 2-3           | 多種                  | 中             |
| 4-5           | 幾種                  | 高             |
| 6+            | 1-2 種                | 極高、不可避免 |

這跟 over-constraint 設計問題同骨：要求越具體、解空間越小、批量後解就會集中到少數幾個。

---

## 為什麼這個 attractor 規範擋不住

對應「為什麼 cadence 維度 [#122](../cadence-homogenization-in-batch-writing/) 失守」、本卡是 *機制側* 解釋：

- **每篇單看都合規**：constraint 設計成「單檔通過 / 不通過」、沒有「跨檔 framing 變異性」這個 constraint、所以 single-file lint 永遠 pass
- **複製是 Claude 的 cost optimum**：批量第 N 篇複製第 1 篇骨架 = 最少新 token、最少 risk、最快輸出；除非有反向壓力、預設行為就是複製
- **規範本身鼓勵「找一個都過的 framing」**：要求章節齊全 + 表格深化、Claude 自然會收斂到「對所有 vendor 都適用」的 framing；越通用的 framing、cadence 越單一

「對所有 vendor 都適用」跟「對每個 vendor 都到位」是兩件事 — 通用 framing 不會錯、但會 *只到位最小公分母*。批量寫作下、最小公分母 framing 大量複製就是 cadence 同質化。

---

## 對策：拉開 constraint 或加 anti-template constraint

兩條互補路徑：

| 路徑                            | 做法                                                                                     | 取捨                                                                  |
| ------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 拉開 constraint                 | 允許 framing 多樣（如「11 章節結構必、但章節內部敘事不限定 frame」）                     | 失去部分一致性、換來 cadence 多樣性                                   |
| 加 anti-template constraint     | 在硬規範裡列「同 batch 內 framing 變體至少 3 種」、「段首句句型分佈」                    | 規範複雜度上升、執行需要跨檔抽樣機制                                  |
| Pilot phase 強制               | 寫前 3 篇時刻意產出 3 種不同 framing、其他篇從這 3 種輪替                                | 前期成本上升、批量整體成本平攤後仍便宜                                |
| 切小 batch + frame 變更        | 每 ≤ 10 篇換一次 dominant frame、不要一個 batch 寫 51 篇                                 | 批次數上升、單批 review 成本下降                                      |

實務 default：**Pilot phase 強制 + 加 anti-template constraint**。先在 pilot 階段準備變體、再用規範要求跨檔抽樣、雙層防護。

---

## 不是只發生在「寫作」

同骨機制在其他批量產出任務上也成立：

- **Code generation**：用同一 LLM 一次生 N 個 service 的 boilerplate、結構會收斂到同一 framing（同樣的 error handling pattern、同樣的 log 格式）
- **Test case 批量寫**：N 個 unit test 都用同一個 setup-act-assert framing、覆蓋面看似齊但其實只測一種 axis
- **API doc 批量寫**：N 個 endpoint doc 都用同一段「方法 / 參數 / 回傳」三段式、抓不到 endpoint-specific 邊界

這些都是 constraint 設計的 collapse — 只是發生在不同 surface。

---

## 反模式

| 反模式                                                       | 後果                                                                |
| ------------------------------------------------------------ | ------------------------------------------------------------------- |
| 規範堆疊不評估 attractor 副作用                              | Constraint 越多 cadence 越單一、規範自身成為同質化 root cause       |
| 認為「合規 = 品質」                                          | 51 篇都合規但連讀預期化、合規是必要不充分                           |
| 批量寫作不切 batch、一次寫 50+ 檔                            | Cadence collapse 風險最大、修正成本 N 倍                            |
| 發現同質化後加更多 constraint                                | Over-constraint、解空間更窄、cadence 反而更收斂                     |
| Pilot phase 跳過、直接寫批量                                 | 沒準備變體、第一篇 framing 自動成 dominant                          |
| 把 cadence 問題歸因「Claude 偷懶」、不是 constraint 設計問題 | 換 model 還是會發生、根因在 constraint 設計、不是執行者              |

---

## 跟其他抽象層原則的關係

| 原則                                                                                            | 關係                                                                                                                              |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| [#122 Cadence 同質化是模板的隱形維度](../cadence-homogenization-in-batch-writing/)              | Sibling — #122 是 *症狀* 卡（cadence 同質化是模板）、本卡是 *機制* 卡（為什麼會發生）；兩張一起讀                                 |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)                       | 本卡是 #67 在「批量產出」的具體機制；複製合規 framing 最便利、跨檔意圖對齊失準                                                    |
| [#44 Single Source of Truth](../single-source-of-truth/)                                       | 互補 — SSoT 處理「值的住址只能一處」、本卡處理「framing 的住址不能只有一處」；兩者是 SSoT vs anti-SSoT 的不同 surface             |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)                  | 本卡是 #82 在 constraint 設計的具體 case — 字面合規（章節 / 表格 / 行數）+ 行為失準（cadence 同質）                              |
| [#86 Capability gap 三層對策階梯](../capability-gap-three-layer-escalation/)                   | 互補 — 同質化問題不該只用 L1（提醒 Claude 變化）、要 L2（pilot phase）或 L3（規範擴寫 anti-template）                             |

---

## 判讀徵兆

| 訊號                                              | 該做的事                                                              |
| ------------------------------------------------- | --------------------------------------------------------------------- |
| 規範條目 ≥ 5 條且 enforce 同一檔                  | 評估 attractor 風險、是否該拉開或加 anti-template constraint          |
| 一個 batch 計畫寫 ≥ 10 個同類檔                   | 切小 batch、或加 pilot phase 強制變體                                |
| Pilot phase 只寫 1-2 個就進批量                   | 沒準備 framing 變體、預設會 collapse                                  |
| 想再加新 constraint 解決品質問題                  | 警訊 — 加多會更 collapse、考慮拉開或換層                              |
| Review 報告說「都合規」                           | 不夠、加跨檔 cadence 抽樣 frame                                       |
| 批量寫完 reviewer 才發現同質化                    | Review 時機太晚、改 stage 內抽樣                                      |
| 想複用上批 framing 寫下批                         | 警訊 — 復用 dominant framing 會把同質化跨 batch 擴散                  |

**核心**：多重硬規範同時生效時、cadence 收斂到合規最便利解是預設行為、不是違規。對策不是加更多 constraint、是拉開 constraint 或強制 pilot phase 準備變體；規範設計時要評估 attractor 副作用、不是只看「單檔有沒有過」。
