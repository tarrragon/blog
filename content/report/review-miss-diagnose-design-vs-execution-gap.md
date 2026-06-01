---
title: "Review 漏抓先分 design gap 與 execution gap、再決定改框架還是改執行"
date: 2026-06-01
weight: 153
description: "Review 漏抓某類問題時，有兩個不同成因：design gap（框架根本沒有對應 frame）跟 execution gap（框架有 frame、但 reviewer 沒跑）。修法相反 —— design gap 要改框架（補 frame / keyword）、execution gap 要改執行（真的跑完該跑的輪）。診斷前先分清：把 execution gap 誤判成 design gap 會 framework bloat（一直加 frame 卻沒解決偷跑子集）、把 design gap 誤判成 execution gap 會永遠漏同類。常見陷阱是『加 keyword』感覺像進步、但對沒跑的輪毫無幫助。"
tags: ["report", "事後檢討", "工程方法論", "原則", "寫作", "review-process"]
---

## 論述基礎與限制

本卡是一次 review 失誤的 self-retrospective（用 WRAP 的 Consider the Opposite 反向檢驗自己的 review 過程）抽出。具體限制：

- **樣本是 1 次 review、1 個 reviewer（我自己）**：「design gap vs execution gap」這個二分基於單次自我檢討、不是跨多次 review 觀察到的 systematic pattern。
- **「自我歸因」有 self-serving 風險**：reviewer 檢討自己漏抓時、可能傾向把責任推給「框架不足」（design gap）而非「我偷懶」（execution gap）—— 本卡的價值正是強迫拆開這兩者、但拆的人就是當事人、客觀性有限。
- **修法有效性未驗證**：診斷後的修法（改框架 vs 改執行）是否真能讓下次 catch 到、未經後續 review 驗證。

讀者使用本卡時、把它當「review 失誤歸因的一個檢查步驟」、不當「驗證過的 review 流程」。

---

## 核心原則

Review 漏抓某類問題時，先分清是 **design gap** 還是 **execution gap**，再決定修法 —— 兩者修法相反。

- **Design gap**：框架根本沒有對應的 frame / keyword 去 catch 這類問題。修法是**改框架**（補 frame、補 keyword bank、補 lens）。
- **Execution gap**：框架有對應 frame、但 reviewer 這次沒跑（跑了子集、跳過該跑的輪）。修法是**改執行**（真的跑完該跑的輪），改框架沒用。

| 成因          | 問題在哪     | 修法                      | 誤判的後果                                                                  |
| ------------- | ------------ | ------------------------- | --------------------------------------------------------------------------- |
| Design gap    | 框架缺 frame | 補 frame / keyword / lens | 誤判成 execution → 一直漏同類（以為「下次認真跑」就好、但根本沒對應 frame） |
| Execution gap | 沒跑該跑的輪 | 跑完整框架                | 誤判成 design → framework bloat（一直加 frame、卻沒解決「偷跑子集」的習慣） |

同一次漏抓**常常兩者都有** —— 要分別處理、不能只修一邊。

---

## 具體 case

這次 review 一篇技術教材、跑了「3 個臨時擬的 agent frame + 一次字句層 grep」、回報「字句層大致 clean」。結果使用者分多輪 catch 出 register/stance 類問題（安撫讀者 / 第二人稱 / 自評誇飾 / 必然框架）。用 WRAP Consider the Opposite 反向檢驗，發現**兩種 gap 都有**：

### Execution gap（我沒跑完整框架）

multi-pass review 框架定義了輪 9（reader simulation）、輪 10（self-criticism），但這次**我根本沒跑** —— 只跑了我臨時擬的 3 個 agent frame + grep。如果跑了輪 9（用讀者視角讀「這段在跟我說話嗎」），喊話類當場會 catch。這部分**不能怪框架**、是我跑了子集。

### Design gap（框架本身的 frame 不夠）

但即使跑了輪 9、現有定義是「拿掉 code block 看論述能不能 parse」（聚焦**自包含性**）、**沒有 register lens**（這段在管理 / 評價 / 絕對化讀者嗎）。而且 register 類有兩個結構特性讓 keyword bank（輪 8）抓不到：

- **無穩定關鍵詞**：第二人稱「你」誤命中 code 註解、祈使句式發散、訴諸群體形式多。
- **最依賴外部 cold-read**：這次正是**使用者（外部讀者）**才抓到 —— 同一 reviewer 模擬讀者視角有限（per multi-pass 自承的 partial fix 限制）。

這部分**要改框架**：輪 9 擴入 register lens、標明 register 類「reader-sim 主、keyword bank 輔」。

---

## 沒這樣做的麻煩

### 只改框架：framework bloat、execution 習慣沒解

漏抓後直覺反應是「加 keyword / 加 frame」—— 因為這看得見、像進步。但若真正成因是 execution gap（沒跑輪 9）、加再多 keyword 都沒用（那些輪還是沒跑）。框架越加越胖、reviewer 還是偷跑子集。

### 只改執行：漏掉的整類永遠 catch 不到

反過來、若把 design gap 誤判成「我下次認真跑就好」、但框架根本沒有對應 frame —— 認真跑現有的輪也 catch 不到、同類問題每次都漏。

### 「加 keyword」是最誘人的假修法

加 keyword bank 條目成本低、立即有「補上了」的感覺。但它只解 design gap 的一個 sub-type（偵測層、且限有穩定關鍵詞的類）。對 execution gap（沒跑輪）、對 register 這種無關鍵詞的 design gap、它都無效 —— 容易讓人以為修好了、其實沒。

---

## 跟其他抽象層原則的關係

- **[#114 Multi-pass review 的 frame 顆粒度盲點](../multi-pass-review-frame-granularity-blindspot/)**：#114 處理的是 **design gap 的一個面向**（frame 不夠細、抽象規則沒展開成具體訊號）。本卡是上位 —— 在「改 frame 顆粒度」之前、先問「這次漏抓到底是缺 frame（design）還是沒跑 frame（execution）」。#114 預設問題在框架、本卡先驗證這個預設。
- **[#147 規範化跟自審是兩種認知任務](../rule-codification-vs-self-audit/)**：#147 是 execution 側的 sibling —— 「立了規範 ≠ 自己稿件能辨識」講的就是「有 frame 不等於有跑」。本卡把它一般化成「有 frame 不等於有跑（execution gap）」、並跟「根本沒 frame（design gap）」對立起來。
- **[#149 keyword bank 命中是候選、不是判決](../keyword-bank-hit-is-candidate-not-verdict/)**：#149 是另一個「兩層別混」的 pattern（偵測 vs 判定）。本卡（design vs execution）跟 #149（偵測 vs 判定）都在拆「review 失效的成因層」—— 修法都依賴先分層、再對症。
- **[#150-152 教材 register / framing 卡](../teaching-register-states-not-addresses-reader/)**：這三張是本卡的觸發 case（漏抓的具體內容）。本卡是它們揭露的 **review 流程層** 教訓 —— 內容卡講「該怎麼寫」、本卡講「review 為什麼沒抓到、該改框架還是改執行」。

---

## 判讀徵兆

| 徵兆                                          | 該做的行動                                                                   |
| --------------------------------------------- | ---------------------------------------------------------------------------- |
| Review 漏抓、直覺想「加 keyword / 加 frame」  | 先停 —— 問「這次有跑完該跑的輪嗎」、是 execution gap 就別加 frame            |
| 「我下次認真跑就好」                          | 檢查框架真有對應 frame 嗎 —— 沒有就是 design gap、認真跑也沒用               |
| 跑的是「臨時擬的子集」而非完整框架            | execution gap 訊號 —— 先補跑完整輪、再判斷框架夠不夠                         |
| 漏抓的類別有「無穩定關鍵詞」特性              | keyword bank 解不了（design gap 的 reader-sim 類）—— 加 lens、不是加 keyword |
| 漏抓由外部讀者 / 使用者 catch、自己多輪沒抓到 | 該類高度依賴 external cold-read —— 同 reviewer 模擬有限、標明依賴            |

---

## 適用範圍與邊界

- **適用**：review 流程的 retrospective（漏抓後檢討）、framework 演進決策（要不要加 frame / keyword）、self-review 品質檢討。
- **不適用**：一次性短文 review（沒有「框架」可言、談不上 design vs execution）。
- **邊界**：兩者不互斥、常同時存在 —— 本卡要的不是「二選一」、是「分別診斷、分別修」。誤把它當 either-or 會只修一半。

---

## Self-case：本卡的觸發來源

本卡觸發於對 [HOF / typedef 文章](../../work-log/dart_hof_typedef_readability/) 的 review 失誤做 WRAP 檢討。使用者問「多輪審查設定是否需要調整」，WRAP 的 Consider the Opposite 步驟揭露：失敗不全是框架缺陷 —— 一半是我**只跑了臨時子集、跳過框架既有的輪 9/10**（execution gap）、一半是**輪 9 定義聚焦自包含性、缺 register lens、且 register 類無穩定關鍵詞**（design gap）。

對應本卡：若沒做這個拆分、最可能的反應是「再加幾個 keyword」（只解 design gap 的偵測 sub-type）、既沒解 execution gap（下次還是偷跑子集）、也沒解 register 的 reader-sim design gap。拆開後修法清楚：execution gap 靠「review 時真的跑完該跑的輪」（紀律、不改框架）、design gap 靠「輪 9 擴 register lens + 標明 external-reader 依賴」（改框架、下一步執行）。
