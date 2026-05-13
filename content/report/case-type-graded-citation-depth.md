---
title: "案例引用深度跟著 case 類型走"
date: 2026-05-13
weight: 115
description: "skeleton / medium / rich case 各有不同承接深度；誤判類型 → 編造數字 / taxonomy（over-extrapolation）或漏掉 case 揭露的 mechanism（under-citation）；引用前先看 case 行數 + 內容密度判類型、決定該寫『揭露 X 方向』還是『揭露 N 個機制』還是『揭露具體數字 / 設計』"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Case-driven"]
---

## 結論

引用案例前要先判 case 類型、不同類型適合不同承接深度。誤判類型 → 編造 case 沒寫的細節 → reviewer 抓出 → 修正成本高。

| Case 類型     | 行數      | 內容密度                                 | 承接句型                                                |
| ------------- | --------- | ---------------------------------------- | ------------------------------------------------------- |
| Skeleton case | 10-30 行  | 只給方向、無具體數字 / taxonomy          | 「揭露 X 方向、以下基於通用工程知識補充」               |
| Medium case   | 30-50 行  | 結構化 mechanism + 訊號名稱、無具體數字  | 「揭露 N 個機制 — A、B、C、D」用 mechanism 名稱精準引用 |
| Rich case     | 50-200 行 | 含具體數字（RPS / 延遲 / TPS）、設計細節 | 「揭露 X 觀察 + 作者判讀 Y（明示分層）」                |

跨類型混合引用要分層處理 — 同段內若引兩類 case、先寫 rich case fact 作為支撐、再用 skeleton case 補方向、不混合成單一斷言。

---

## 為什麼這層紀律重要

LLM 從 case 反推內容時、訓練資料的「通用知識」會自動補進章節。當 case 沒寫的 mechanism / 數字 / taxonomy 被寫成「對應 [case]：揭露 X」斷言、讀者回查 case 時會發現章節說的「揭露」實際是 LLM 編造。

backend/01-07 七模組驗證（[case-first workflow](../../posts/case-first-agent-team-review-workflow/) 的 case fidelity reviewer 抓的數據）：

| 模組                   | 主要 case 類型    | Case fidelity | 主要失分類型                          |
| ---------------------- | ----------------- | ------------- | ------------------------------------- |
| backend/02 cache       | Skeleton          | 78%           | 三層 cache latency 編造、ops/sec 編造 |
| backend/03 msgq        | Skeleton          | 70%（最低）   | 三方向擴寫成「4 個誤配場景」          |
| backend/04 obs         | Skeleton          | 92.9%（最高） | 嚴守「揭露方向、通用補充」紀律        |
| backend/05 deploy      | Skeleton + Rich   | 80%           | Rich case 判讀層被當 fact 引用        |
| backend/06 reliability | Medium 全套       | 88%           | Medium case 實作層擴寫過頭            |
| backend/07 batch 1     | Medium + Skeleton | 81%           | 跨 case 合成 frame 升級成 case 揭露   |

最高的 92.9% 跟最低的 70% 差 23 個百分點 — 差別不在「案例品質」、在「引用紀律」。Skeleton case 嚴守「揭露方向」、不擴寫成 rich case 樣式、就能達到 90%+。

---

## 三類 case 的判讀條件

### Skeleton case：「揭露 X 方向、通用補充」

典型：模組內部 N.Cx 案例庫中只有 frame、無具體數字的短篇 case。內容深度 10-30 行、給「議題」「視角」、不給「實作細節」。

承接紀律：

- 引用為「揭露 X 方向」、不引用為「揭露 N 個具體場景數量」
- 後面補「以下展開基於通用工程知識補充」明示分層
- 不為了「整齊的 4 個攻擊面」「3 個攻擊向量」這種數字感、把 case 沒寫的 taxonomy 寫成 case 揭露

例：Meta Cache Consistency case 只給「promotion、shard move、故障恢復」三個方向 → 引用為「揭露三個方向」、不引用為「揭露具體 inconsistency window 數字」。

### Medium case：「揭露 N 個機制 — A、B、C」

典型：模組內部 case 庫中、含結構化「決策機制」+「可觀測訊號」表、但無具體數字的中篇 case。內容深度 30-50 行、含 mechanism 名稱 + 訊號名稱、但不給 RPS / 延遲數字。

承接紀律：

- 用 case 直接列出的 *mechanism 名稱* 精準引用、比 skeleton 精準、比 rich 保守
- 不擴寫到 case 沒提的具體實作層（會踩「實作層擴寫過頭」失分）
- 「決策機制」段通常是 fact 層、「常見陷阱」段可能含作者判讀層、引用時也要分層

例：Amazon Shuffle Sharding case 揭露 cell boundary / shuffle sharding / static stability / constant work 四機制 → 引用四機制名稱、但不擴寫到「具體 shard 數量」「具體 cell 大小」等 case 沒提的細節。

### Rich case：「揭露具體 X 數字 / 設計」

典型：跨模組 case 庫中含具體數字、設計細節、遷移路徑的長篇 case。內容深度 50-200 行、含具體 fact + 引用源。

承接紀律：

- 可直接引用為事實、case 揭露的具體數字（RPS、延遲、TPS、stale window）可放進章節
- 但 rich case 內常含「觀察層」（具體 fact）跟「判讀層」（作者推論）、引用時要分層（見 [#116 fact-vs-derive 分層引用](../fact-vs-derive-citation-layering/)）
- 引用判讀層時用「揭露 X 觀察 + 作者判讀 Y」明示分層、避免把推論寫成 fact

例：Amazon Ads case「90M RPS + 5M writes/sec + 99.999%」 → 可直接寫進 KV 章節作為 reference。

---

## 反模式

| 反模式                                           | 後果                                                                    |
| ------------------------------------------------ | ----------------------------------------------------------------------- |
| Skeleton case 引用寫成「揭露 4 個具體場景」      | 編造 case 沒寫的 taxonomy、reviewer B 抓 critical                       |
| Skeleton case 引用補具體數字（從通用知識補進去） | 「Tubi 三層 cache L1 < 1ms / L2 < 10ms / L3 10-100ms」這類編造數字      |
| Medium case 引用擴寫到 case 沒提的實作細節       | 「具體 shard 數量」「具體 partition key 數量」這類 over-extrapolation   |
| Rich case 引用合併觀察 + 判讀層                  | 「揭露 35ms latency 反推 region 部署」（35ms 是觀察、reasoning 是判讀） |
| 引用時不標 case 類型、寫稿時憑感覺承接深度       | 跨章累積失分、reviewer 抓出後修正成本高                                 |

---

## Stage 1 抽 findings 時的判讀步驟

寫教學內容前、stage 1 audit case 庫時要 *標明 case 類型*：

1. 看 case 行數 + 內容密度、初判類型
2. 看是否有具體數字 / 設計細節、確認 Rich case
3. 看是否只給方向 / 議題、確認 Skeleton case
4. 介於中間時、傾向保守判讀為 Skeleton（避免過度承接）
5. 把類型寫進 findings 列表、stage 2 寫作時依類型決定承接深度

跨類型混合引用：

- 同一段內若引兩類 case、先寫 rich case fact 作為支撐、再用 skeleton case 補方向
- 不要把 skeleton case 的方向跟 rich case 的數字混合成單一斷言
- 跨類型引用時 disclaimer 要明示哪段屬通用、哪段屬 case fact

---

## 跟其他抽象層原則的關係

| 原則                                                                                 | 關係                                                                        |
| ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| [#116 Fact vs Derive 分層引用](../fact-vs-derive-citation-layering/)                 | case 內部 fact / derive 分層 — 本卡看 case 整體類型、#116 看 case 內部結構  |
| [#117 跨 case 合成 frame 必須標明](../cross-case-synthesized-frame-must-be-labeled/) | 第三類失分 — 章節抽象 frame 不能升級成 case 揭露                            |
| [#104 security citation 時效精確](../security-citation-currency-and-precision/)      | citation 紀律的姊妹卡 — 一個管 case、一個管 standard                        |
| [#83 Writing multi-pass review](../writing-multi-pass-review/)                       | case fidelity 是輪 5（反例 / 邊界）+ stakes 軸（輪 E.5 citation）的具體實作 |
| [#44 Single Source of Truth](../single-source-of-truth/)                             | 引用要求引用「住址」、本卡是 SSoT 在 case 引用情境的具體實例                |

---

## 判讀徵兆

| 訊號                                                  | 該做的事                                                     |
| ----------------------------------------------------- | ------------------------------------------------------------ |
| 寫到「揭露 N 個」時不確定 N 是不是 case 真的列了      | 回 case 原文 grep、不確定就降級為「揭露 X 方向」             |
| Skeleton case 引用突然出現具體數字（從 LLM 記憶湧現） | 數字幾乎一定是編造、立即刪掉或標 disclaimer                  |
| Rich case 引用句含「才是 / 必須 / 一定 / 關鍵是」     | 通常是把作者判讀升級成 fact、退回 case 原文找條件性表述      |
| 同段引用兩類 case 但語氣一致                          | 分層遺失、重寫成「rich case 補 fact + skeleton case 補方向」 |
| Findings 列表沒標 case 類型                           | Stage 1 紀律失效、回 case 補類型再寫                         |

**核心**：誤判 case 類型 = 引用深度錯位 = case fidelity 失分。Stage 1 抽 findings 時花 30 秒判類型、能省 stage 4 修正 5-10 分鐘 / 案例。
