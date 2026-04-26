---
title: "元件相對位置類指令的澄清時機"
date: 2026-04-25
weight: 17
description: "聽到「X 在 Y 旁邊」時、先用文字畫個 layout 草圖讓使用者確認、不憑直覺擺。本文展開這類指令的處理 protocol。"
tags: ["report", "事後檢討", "溝通", "工程方法論"]
---

## 核心原則

**相對位置指令（「X 在 Y 旁邊」「Y 顯示在 main 左側」）是模糊的 — 同一句話可以對應多種 layout 結構。實作前用文字描述意圖中的 layout 草圖、讓使用者確認後再寫 CSS。** 沒確認直接擺、實作出來常與使用者預期不同、要重做。

---

## 為什麼相對位置需要澄清

### 商業邏輯

「X 在 Y 旁邊」這類描述至少對應四種 layout 實作：

| 實作方式                                  | 視覺結果                 |
| ----------------------------------------- | ------------------------ |
| Y 與 X 同 row、grid / flex 並排           | 並排、Y 影響 X 寬度      |
| X absolute 浮在 Y 旁邊                    | 並排、X 不影響 Y         |
| Y 與 X 不同層、Y 在 main 內、X 在 main 外 | 跨 main 邊界、視覺感不同 |
| X fixed 永遠在 viewport 同位置            | 隨捲動固定、Y 隨內容捲動 |

執行者選哪種、結果不同。憑直覺選 ≠ 使用者意圖。

---

## 這次任務的實際情境

### 觀察

| 指令                      | 我的初次理解                  | 使用者實際意圖                   |
| ------------------------- | ----------------------------- | -------------------------------- |
| 「scope UI 在搜尋框附近」 | 放搜尋框上方                  | 應該在搜尋框下方                 |
| 「filter 在主欄左側」     | 放進 main 的 grid 左 column   | 是 main 外的 absolute sidebar    |
| 「左右兩欄獨立排版」      | 同 grid container 兩個 column | 兩個獨立 layer、用 absolute 疊層 |

每個指令都讓我選了使用者沒想要的實作。

### 判讀

問題在「相對位置」這類描述本質就是模糊的 — 沒指定座標系、沒指定相對層級、沒指定誰是 layout flow 主角。

執行前該做的：把我準備寫的 layout 用文字描述出來、讓使用者確認意圖一致。

### 執行：layout 草圖 protocol

收到相對位置指令時、先寫文字草圖：

```text
我準備這樣寫：
  - main 維持 70ch 置中（layout flow 主角）
  - filter 用 absolute 浮在 main 左外側、寬 400px、間距 2rem
  - scope UI 在 main 內、緊接 search input 下方、結果上方
  - 三者位置關係：filter 與 main 同 viewport 中段、scope 在 main 內

確認對應你的意圖嗎？或是想要不同安排？
```

把意圖中的 layout 結構攤開 — 使用者可以指正「filter 應該在 grid 內、不是 absolute」、避免實作後重做。

---

## 內在屬性比較：四種相對位置描述

| 描述方式                                       | 模糊度 | 適用情境           |
| ---------------------------------------------- | ------ | ------------------ |
| 純位置詞（「在旁邊」「在下方」）               | 高     | 初步對話、需要追問 |
| 加層級指示（「在 main 內」「跨 main 外」）     | 中     | 縮小範圍           |
| 加 layout 結構（「同 grid」「absolute 疊層」） | 低     | 接近實作           |
| 文字草圖 + 確認                                | 最低   | 實作前最後確認     |

執行者該主動把對話從「純位置詞」推到「文字草圖 + 確認」 — 縮小模糊範圍。

---

## 文字草圖的好習慣

### 1. 描述 layout 主角

哪個元素是「決定其他元素位置的 anchor」？通常是內容主體（main、article）。其他元素相對這個主角描述。

```text
Layout 主角：main（70ch 置中）
其他元素：
  - H1：main 內、第一個元素
  - filter：main 左外側 400px
  - footer：main 之後
```

### 2. 描述層級關係

哪些元素在同一 layout 流、哪些是疊層？

```text
Layout flow 內：H1、search input、results
疊層：
  - filter：absolute、浮在 main 左外
  - scope UI：absolute、浮在 search input 下方
```

### 3. 描述 viewport 行為

不同 viewport 下、layout 怎麼變？

```text
Desktop ≥ 1400：filter 顯示在左外、scope UI 浮在 input 下方
Mobile < 1400：filter 移到 pagefind drawer 內、scope UI 維持原位
```

---

## 對使用者描述 layout 的格式

### Inline ASCII 草圖

文字環境下、ASCII 比 PNG 圖更實用：

```text
┌────────────┬──────────────────┐
│            │ H1 搜尋           │
│ filter     ├──────────────────┤
│ (sticky)   │ Search input     │
│            ├──────────────────┤
│            │ Scope UI         │
│            ├──────────────────┤
│            │ Results          │
└────────────┴──────────────────┘
```

幾秒鐘畫出來、使用者一眼看出意圖、可以指正特定區域。

### 敘述列表

不畫圖也可以列：

```text
從上到下、從左到右：
  1. 左欄：filter（400px、main 外、sticky）
  2. 右欄：
     a. H1 搜尋
     b. Search input（中央欄）
     c. Scope UI（input 下、results 上）
     d. Results
```

兩種格式選一種、確認後再寫 CSS。

---

## 設計取捨：相對位置指令的處理策略

四種做法、各自機會成本不同。這個專案選 A（文字草圖確認）當預設、其他做法在特定情境合理。

### A：文字 layout 草圖 + 主角/疊層說明確認（這個專案的預設）

- **機制**：把意圖翻成「main 70ch 置中、filter absolute 浮在 main 左外、scope 在 main 內 absolute 浮在 input 下」這類具體描述、使用者確認
- **選 A 的理由**：草圖 30 秒打完、使用者 30 秒內 yes/no、避免寫完 CSS 才被指正
- **適合**：相對位置指令的多數情境
- **代價**：多 30 秒對話成本

### B：ASCII 圖更詳細

- **機制**：用 box-drawing 字元畫實際 layout 草圖
- **跟 A 的取捨**：B 視覺直觀、A 文字描述更精確；B 對複雜 layout 表達力強
- **B 比 A 好的情境**：layout 涉及 ≥ 4 個區塊、文字描述容易混淆

### C：加層級指示（中間步驟）

- **機制**：「filter 在 main 外的 sidebar」（不是「在 main 旁邊」）
- **跟 A 的取捨**：C 比純位置詞具體、比草圖簡略；用於初步對話
- **C 比 A 好的情境**：對話初期、還沒到實作決策的階段

### D：純位置詞直接實作

- **機制**：照「filter 在 main 旁邊」字面意思挑一種實作
- **成本特別高的原因**：同一句話對應多種 layout 結構、選錯就重做
- **D 才合理的情境**：實務上幾乎不存在 — 「相對位置」永遠模糊、不該跳過確認

---

## 判讀徵兆

| 訊號                   | 應該觸發澄清的指令                                  | 第一個該確認的                 |
| ---------------------- | --------------------------------------------------- | ------------------------------ |
| 「X 在 Y 旁邊」        | 同 row 還是疊層？X 影響 Y 的位置嗎？                | Layout 結構（grid / absolute） |
| 「Y 顯示在 main 左側」 | 在 main 內的 column 還是 main 外的 sidebar？        | 跨界與否                       |
| 「左右兩欄獨立」       | 「獨立」是 DOM 獨立、layout 獨立、還是 state 獨立？ | 隔離程度                       |
| 「跟 Z 對齊」          | Z 的哪個邊（top / bottom / left / right）？         | 對齊基準                       |

**核心原則**：相對位置描述只是意圖、不是實作藍圖。實作前先把意圖畫成 layout 草圖、確認後再開工。

第三輪指令類型現有五類：空間（[#16](../spatial-instruction-clarification/)）/ 相對位置（本卡）/ 隔離（[#18](../isolation-instruction-clarification/)）/ 決定權（[#21](../decide-vs-confirm-boundary/)）/ 篩選（[#58](../filter-instruction-clarification/)）。
