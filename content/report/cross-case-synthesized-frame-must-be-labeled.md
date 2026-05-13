---
title: "跨多個 case 合成的 frame 必須標為章節合成、非 case 原文"
date: 2026-05-13
weight: 117
description: "當段落把多個 case 的失效訊號抽象為更高層 frame（如『跨工具回查壓力』『平台責任切分』）、要 explicit 標為『本章合成、非 case 原文』；否則章節 derive 會被讀者當成 case fact、回查 case 時發現章節說的『揭露』實際是章節抽象、不是 case 原文框架"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Case-driven"]
---

## 結論

跨 case 合成 frame 是 LLM 寫教學內容時的常見模式 — 抓兩個 case 的相似訊號、抽象為更高層概念、讓章節結構更清楚。但 *標明 frame 來源* 是關鍵：

| 情境                         | 引用紀律                                                         |
| ---------------------------- | ---------------------------------------------------------------- |
| Case 原文段直接寫此 frame    | 「兩 case 共同標明 X」                                           |
| 章節從多個 case 失效訊號抽象 | 「本章把兩者抽象為 X 是 YYY 視角的合成 frame、非 case 原文框架」 |

兩種寫法的差別不只是修辭、是 case fidelity 紀律 — reviewer B 對照原文時、會抓「揭露 X」斷言是否有 case 原文支撐。

---

## 跟既有 fact-vs-derive 分層的差別

[#116 fact vs derive 分層](../fact-vs-derive-citation-layering/) 處理 *單一 case 內部* 的觀察層 vs 判讀層分層。本卡處理 *跨多個 case* 抽象出更高層 frame 的失分類型 — 屬於 fact-derive 紀律的第三類風險：

| 類型                           | 風險                                                                                       | 範例                                                                        |
| ------------------------------ | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| Skeleton 擴寫                  | case 沒提的細節（具體數字、taxonomy）被寫成 case 揭露                                      | case 說「異常查詢偵測維度」、章節寫「query 體積 1MB → 10GB / 天」（編造）   |
| Rich case fact-derive 混淆     | case 有提、但屬作者判讀層的內容被寫成 case fact                                            | case 把「35ms」放觀察、「反推 region 部署」放判讀；章節合併（升級判讀）     |
| **跨 case 合成 frame**（本卡） | case *單獨* 寫的訊號被章節 *跨 case 合成* 抽象為更高層 frame、frame 本身不在任一 case 原文 | Uber 寫「告警串接不足」、Slack 寫「訊號未匯流」、章節合成「跨工具回查壓力」 |

---

## 為什麼這層紀律重要

LLM 寫教學內容時容易把多個 case 的相似訊號抽象成 frame、讓段落結構更清楚。但 *標明 frame 來源* 直接決定 case fidelity：

- **Case 真的揭露 frame**：case 原文段直接寫此 frame、可寫「兩 case 共同標明 X」（屬合法 fact 引用）
- **章節從 case 失效訊號抽象**：case 寫的是 *單獨* 訊號、章節把多個訊號抽象成更高層 frame、要明示「本章合成、非 case 原文」

漏掉這層 disclaimer、讀者把章節 derive 當成 case fact、回查 case 時會找不到 frame、章節失去 case 支撐。

---

## 實證案例

backend/07 batch 1 模組驗證、case fidelity reviewer 抓的 2 個 high issue 都屬此類：

### 實證 1：7.7 跨工具回查壓力

- **章節（錯）**：「對應 [Uber 2022] 跟 [Slack 2022]：兩個案例都揭露『身分事件後的跨工具回查壓力』」
- **Case 原文**：Uber 失效控制面寫「身分異常事件與值班告警串接不足」、Slack 寫「程式碼資產存取異常訊號未快速匯流」— 都是 *單工具內* 的訊號失效、「跨工具」這個 axis 是章節合成
- **章節（對）**：「兩個案例分別在身分監控層揭露同類失效訊號 — Uber 標明 X、Slack 標明 Y。本章把兩者抽象為『跨工具回查壓力』是稽核視角的合成 frame、非 case 原文框架。」

### 實證 2：7.7 平台責任切分

- **章節（錯）**：「對應 [SolarWinds 2020]：揭露的『供應鏈事件中的平台責任切分』是稽核層的代表壓力場景」
- **Case 原文**：失效控制面寫「更新來源信任過於單點」「行為監測難以區分合法元件」「供應鏈異常缺隔離流程」— 都是供應鏈信任議題、不是「平台 vs 產品的 audit 責任分離」
- **章節（對）**：「案例的失效控制面標明 X / Y / Z。本章把這幾條失效面從供應鏈信任視角延伸到稽核視角、抽象為『平台 vs 產品的責任邊界判讀壓力』— 此 frame 為本章合成、非 case 原文。」

---

## 反例：case 真的揭露 frame（不需 disclaimer）

不是所有跨 case 引用都要標「本章合成」。當 case 原文段直接寫此 frame、可直接引用：

### 反例 1：邊界設備三同步 mechanism

- **章節**：「對應 [Citrix Bleed 2023] 跟 [PAN-OS 2024]：兩個案例的『mechanism 總綱』段共同標明這個三同步原則」
- **Case 原文**：兩個 case 文末「mechanism 總綱」段確實寫「邊界事件的核心是讓『漏洞修補』『會話 / 憑證失效』『異常痕跡清查』三件事同步發生」
- **判讀**：frame 在 case 原文、可引用「兩 case 共同標明」、不需 disclaimer

差別判斷：

| 訊號                               | 該怎麼寫                                    |
| ---------------------------------- | ------------------------------------------- |
| Frame 文字在 case 原文 grep 找得到 | 「兩 case 共同標明 X」                      |
| Frame 是章節從 case 失效訊號抽象出 | 「本章把 X 抽象為 Y 是 Z 視角的合成 frame」 |
| 部分 case 揭露 frame、部分章節抽象 | 兩段拆開、各自標明                          |

---

## 為什麼 LLM 容易踩

從 LLM 寫教學內容的視角看、跨 case 合成 frame 是「自然湧現」的模式：

1. LLM 讀完多個 case 後、會自動抽象出共通 pattern（這是 LLM 的訓練優勢）
2. 寫章節時、章節結構需要 frame 把多個 case 組織起來（教學結構需求）
3. 合成 frame 寫成「兩 case 都揭露 X」最順、不寫 disclaimer 最省字數
4. 結果是 *frame 本身不在 case 原文*、但章節寫得像 case 揭露

LLM 沒辦法 self-detect 這個盲點 — 因為從 LLM 視角、「合成」跟「揭露」在語意上很接近、需要對照 case 原文才能分辨。

---

## 防範路徑

### Stage 2 寫作時主動防範

每寫一個跨 case 合成 frame、跑「frame 在 case 原文 grep 得到嗎」檢查：

```bash
rg "<frame 文字>" <case file>
```

抓不到 → 用「本章合成、非 case 原文」disclaimer
抓得到 → 直接引用「兩 case 共同標明」

### Stage 3 reviewer B prompt 補強

設計 reviewer B prompt 時、要明示「跨 case 合成 frame 必須標為本章合成、非 case 原文」是 high 級 issue 抓取項。沒明示時、reviewer B 容易把這類問題降級為 medium、累積失分。

prompt 應包含：

```text
特別檢查：當引用句說「兩個 case 都揭露 X」時、確認 X 是 case 原文寫的、
還是章節跨 case 合成的。後者要在引用句明示「本章合成 / 非 case 原文框架」。
```

---

## 反模式

| 反模式                                                                 | 後果                                                   |
| ---------------------------------------------------------------------- | ------------------------------------------------------ |
| 「兩個案例都揭露 X」但 X 在原文 grep 不到                              | 章節 derive 升級成 case fact、reviewer B 抓 high issue |
| 跨 case 引用沒 disclaimer、直接寫「揭露」                              | 讀者回查 case 找不到對應、章節失去支撐                 |
| Case 失效訊號是單獨 mechanism、章節抽象成上位 frame 但寫得像 case 揭露 | 把「合成」包裝成「揭露」、案例驅動寫作的紀律失效       |
| Stage 3 reviewer B prompt 沒明示此類為 high                            | reviewer 容易降級為 medium、累積失分不被優先處理       |

---

## 跟其他抽象層原則的關係

| 原則                                                                                  | 關係                                                                         |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [#115 案例引用深度跟著 case 類型走](../case-type-graded-citation-depth/)              | 上游卡 — 先判 case 類型、再判跨 case 合成 frame 是否成立                     |
| [#116 Fact vs Derive 分層引用](../fact-vs-derive-citation-layering/)                  | 同類紀律 — case 內部 fact-derive 分層的延伸、應用到跨 case 情境              |
| [#83 Writing multi-pass review](../writing-multi-pass-review/)                        | 輪 5（反例 / 邊界）跟輪 E.2（claim → evidence 推論鏈完整）的具體實作         |
| [#114 Multi-pass frame 顆粒度盲點](../multi-pass-review-frame-granularity-blindspot/) | 同類盲點 — 一個是同 reviewer 多輪 catch 同類錯、本卡是跨 case 合成的章節盲點 |
| [#104 security citation 時效精確](../security-citation-currency-and-precision/)       | conditional → unconditional drift 的姊妹卡                                   |

---

## 判讀徵兆

| 訊號                                               | 該做的事                                                         |
| -------------------------------------------------- | ---------------------------------------------------------------- |
| 引用句說「兩個 case 都揭露 X」                     | grep case 原文、X 沒寫的話補「本章合成」disclaimer               |
| Frame 寫得很順但 case 原文沒這個詞                 | 章節 derive、改成「本章把 X 抽象為 Y」                           |
| Reviewer B 抓 high issue 集中在「跨 case 引用」    | 紀律失效、整章節重審跨 case 引用                                 |
| 寫多 case 比較時想用「兩個都揭露 X」結構           | 先 grep 確認、抓不到的話改用「兩個分別揭露 X1 / X2、本章合成 Y」 |
| Case 是 medium / rich 類型但「揭露 frame」是抽象詞 | 通常是合成、不是 case 原文 frame                                 |

**核心**：跨 case 合成 frame 本身是合法的寫作技巧、問題在 *不標明*。一句 disclaimer（「本章合成、非 case 原文」）就能把 fact-derive 紀律補回來、修法成本極低。
