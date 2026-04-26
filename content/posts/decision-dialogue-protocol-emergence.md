---
title: "決策對話協議的浮現：從 #74 到 #81 的多層迭代"
date: 2026-04-26
description: "前一篇 case study 紀錄了 search bug → 14 張卡的閉環、本篇紀錄這套系統在純對話場景的另一次迭代：從 user 一句「這些選擇應該被做成卡片」、到 #74-#81 八張新卡 + 一份 reference + skill v0.5 的多層 spiral 浮現過程。重點不是新卡內容、是「卡片如何在對話中浮現」這個 process pattern 本身。"
tags: ["case-study", "知識基礎建設", "Cards-Skills", "Decision Dialogue", "Knowledge Gardening"]
---

## 這篇要說什麼

[前一篇 case study](../cards-skills-system-case-study/) 紀錄的是「實作驅動」的閉環 — 從一個 bug 出發、逼出新卡片。

本篇紀錄的是 **「對話驅動」的閉環** — 不修任何 production code、純粹從對話中浮現新卡。觸發點是 user 的一句反思：「**剛剛提出很多不同方向的決策做選擇、這些選擇應該被做成卡片然後分析或者分拆細節研究**」。

接下來六輪 spiral 迭代、產生 8 張新卡（[#74-#81](/report/)）+ 1 份 SKILL reference + skill v0.5。本文紀錄這條路徑、當作 [#81 卡片系統的迭代浮現](/report/cards-as-living-system-iteration/) 的具體實例。

---

## 起點：對話中的反思訊號

對話到第 N 回合時、agent 已經在多次出現「決策呈現」的場景：

- 「Content mode 三選一」 → user 答 (a)
- 「一次 ship 全部 vs 分批」 → user 答「一次」
- 「五策略選一」 → user 答 「C 主 + D 補」
- 「ship D 還是 B/C」 → user 答 「先 D、B/C 下輪」
- 「反省選哪幾個」 → user 答 「1+2」

每次 agent 都呈現得不一樣、user 也每次回得不一樣。**反覆出現但形式各異 = 抽 meta 的訊號**（[#42 2 次門檻](/report/two-occurrence-threshold/) + [#81 迭代浮現](/report/cards-as-living-system-iteration/)）。

User 的「**這些選擇應該被做成卡片**」就是 meta-訊號的明確化 — 不是 agent 自己浮現的、是 user 點出來的。**External trigger（[#72](/report/external-trigger-for-high-roi-work/)）才能逼出抽 meta 這個高 ROI 但無觸發的工作**。

---

## 迭代過程：六輪 spiral

### 輪 1：列候選、不寫卡

User 的「應該被做成卡片」沒指定要寫幾張、寫什麼。Agent 列五個候選（A-E）+ 推薦 B+C 組合。User 回「**每個都做成卡片**」+ 給出迭代原則：「**先拓展知識庫、然後才整理成上層的抽象決策依據、最後才做決策**」。

這個原則 = [#81] 的 process explicit form：先原子卡 → 後 meta-卡 → 最後決策（套用）。

### 輪 2：寫五張原子卡（#74-#78）

每張一個維度：

- #74 呈現格式（選項表 + 推薦 + 開放修改）
- #75 主策略 + 補強疊加（不必互斥）
- #76 分批 ship（三軸切分）
- #77 「現在不決定」是合法選項
- #78 反省任務預設複選

寫的時候各自獨立、沒明確意識到「這五張其實是同一回事的五個面向」。**在第 5 張寫到一半才開始覺得「好像每張都在打開一個固定的 default」**。

訊號：[#81] 「寫第 N 張卡、發現大段內容跟前一張重複」 → 抽 meta。

### 輪 3：抽 meta-卡 #79

User 接著問「都做、用多層迭代去拓展卡片」、agent 回應時自己浮現了 meta-發現：**這五張其實對應五個獨立維度、可組合成 2^5 = 32 種對話形態**。

寫 #79 時、把五張卡的「打開的 default」歸納成五個維度 + 五步判讀。**Meta-卡讓五張原子卡從「平行五張」變成「有結構的網」**。

回頭給每張原子卡補上「跟 #79 的對應」 cross-link、迭代結束。

### 輪 4：沉澱成 reference

光有卡還不夠 — 實作中要翻 5 張卡才能完整 apply、太貴。

寫 `references/decision-dialogue.md`、把五步判讀 + 完整模板 + self-check 沉澱成一份可直接套用的 protocol。同時更新 SKILL.md 加 trigger route（「呈現決策 / 開放問 / 反省題」）+ Directory Index + 抽象層原則段。

訊號：[#81] 「實作中要回查 ≥ 3 張卡」 → 沉澱 reference。

### 輪 5：dogfood + 反向補卡（#80-#81）

User 的「我們想得到的都作、直到推演到極限」逼 agent 自查：

**自查 1**：回頭看 agent 在這輪對話的回應、找 collapse 反模式。發現 4 處：

- 「需要我繼續嗎？」 = yes/no（最隱形的 collapse）
- 「下一層候選」用 bullet 沒適配欄
- 推薦騎牆「A 比較好不過 B 也行」
- 反省題列點未明示「互不衝突」

→ 寫 #80 Yes/No 二選、把 dogfood 4 例寫進 reference 作為「Bad/Good 對照」。

**自查 2**：「這套迭代過程本身是不是 cardable？」是 — 寫 #81 卡片系統的迭代浮現、紀錄「原子 → meta → reference」的 spiral 結構。

訊號：[#81] 「meta-卡寫太早、新 case 一直破壞」的反面 — 寫得剛好、反而能容納新 case（#80、#81 自己）。

### 輪 6：跨連 + 補強

把 #75（主+補強疊加）展開到 selector pattern：[#46-#49] 看似互斥（每個元件選一個起點）、實際在同一份 code 內可疊加（document + closest 共用）。**Meta-原則的價值之一就是回頭發現舊卡之間有新關係**。

更新 #59（五策略選擇矩陣）加「並用」段落、引用 #75 + #76。

---

## 過程中的觀察

### 1. User 的 prompt 直接決定 spiral 深度

User 的三句話分別觸發三層深度：

| User 的話                              | 觸發深度                                    |
| -------------------------------------- | ------------------------------------------- |
| 「應該被做成卡片」                     | 寫原子卡（layer 1）                         |
| 「先拓展知識庫、再整理上層、最後決策」 | 抽 meta-卡（layer 2）+ reference（layer 3） |
| 「都作、推演到極限」                   | dogfood + 反向補卡（layer 4-5）             |

每句話都是 [#72] L4 外部觸發 — 沒這些話、agent 不會自己走到第 5 層。**Spiral 深度由 trigger 決定、不由 agent 紀律決定**。

### 2. Dogfood 回饋的 ROI 比新卡高

#80（yes/no）的內容比 #74 短得多、但 ROI 可能更高 — 因為它捕捉的是「最常見、最隱形」的反模式。同樣 reference 的「dogfood Bad/Good 4 例」比抽象描述有用 — 將來 agent 看到自己寫類似格式、能直接認出來。

訊號：**具體例子（特別是反例）的 ROI 通常 > 抽象描述**。

### 3. Meta-卡跟 reference 的職責不同

寫完 #79 還不夠、需要 reference — 因為：

- 卡片回答「為什麼」、reference 回答「怎麼做」
- 卡片是讀爽的、reference 是被翻的
- 卡片可選、reference 在實作中是 must

**兩者缺一不可**：只寫卡 → 知道但忘記用；只寫 reference → 知道做但不知道為什麼、難 maintain。

### 4. 真實的 spiral 不是線性

寫 #74 時不知道有 #79、寫 #79 時回頭改 #74-#78、寫 reference 時又發現 #80 漏了、寫 #80 時補 reference 的 dogfood 段。**每一層完成後都會反過來修上一層**。

線性思維（「先寫完 layer 1 才寫 layer 2」）會卡住、spiral 思維（「來回修、每輪都加深」）才能浮現完整結構。

---

## 跟既有原則的關係

| 既有原則                                                               | 在本次 spiral 中的角色                                           |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [#42 2 次門檻](/report/two-occurrence-threshold/)                      | 第 N 次出現決策呈現 = 抽 meta 的訊號                             |
| [#43 最小必要範圍](/report/minimum-necessary-scope-is-sanity-defense/) | 先窄後寬：原子卡（窄）→ meta（寬）、不要直接寫 meta              |
| [#67 寫作便利度反相關](/report/ease-of-writing-vs-intent-alignment/)   | 「直接寫 meta」容易、「迭代浮現」難 — 真實結構不對齊容易寫的格式 |
| [#72 高 ROI 無觸發](/report/external-trigger-for-high-roi-work/)       | 抽 meta + 寫 reference 沒外部觸發不會做、user 的話是 L4 觸發     |
| [#79 決策對話的五維度](/report/decision-dialogue-dimensions/)          | 本次 spiral 的 output、也是元素之一                              |
| [#81 卡片系統的迭代浮現](/report/cards-as-living-system-iteration/)    | 本次 spiral 的 process-level 抽象                                |

---

## 本次 spiral 的 output 清單

| 類型       | 數量 | 內容                                                     |
| ---------- | ---- | -------------------------------------------------------- |
| 原子卡     | 5    | #74-#78（呈現 / 疊加 / 分批 / 延後 / 複選）              |
| Meta-卡    | 1    | #79 五維度                                               |
| 反向補卡   | 2    | #80 yes/no、#81 迭代浮現                                 |
| Reference  | 1    | `decision-dialogue.md`（runtime + blog）                 |
| Skill 整合 | 2    | requirement-protocol v0.5、frontend-with-playwright v0.4 |
| 跨連       | 多處 | #59 加疊加段、#46-#49 加 #75 跨連                        |
| Case study | 1    | 本文                                                     |

**整輪迭代的成本**：純對話、無 production code 改動、無新測試。**整輪迭代的價值**：未來 agent 在每次「決策呈現」場景都有 reference 可翻、有 self-check 可用、有 dogfood 例子可對照。

---

## 結語

本系統的成型不是「用心寫文件」、是接受**「對話會浮現結構、原子卡會自我串連、meta-卡會回頭修原子卡」這個 spiral 真相**、然後讓每輪迭代都加深一點。

下一次 user 在對話中又出現「這個應該被做成卡片」訊號時、流程已經是現成的 — 套 [#81] 的三層展開 + [#72] 的 L4 觸發、就能繼續長新卡。**真正的 knowledge infrastructure 不是寫一次的文件、是長期 spiral 的 living system**。
