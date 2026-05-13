---
title: "引用案例要分觀察層 / 判讀層、強化詞是錯位訊號"
date: 2026-05-13
weight: 116
description: "引用案例（特別是 rich case）時、case 內容分兩層：觀察層（具體 fact）跟判讀層（作者推論）；兩層在章節引用時要分層標明、避免把作者判讀升級成 case fact；強化詞（才是 / 必須 / 一定 / 關鍵是）通常是錯位訊號、保留 case 原文的條件性表述（取決於 / 核心瓶頸 / 主要驅動）"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Case-driven"]
---

## 結論

引用案例（特別是 rich case）時、要把 case 內容分成兩層、分層標明：

| 層別             | 來源                                                                            | 引用紀律                                                             |
| ---------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 觀察層（Fact）   | case 直接寫的具體事實、數字、設計細節                                           | 直接引用為事實、可放章節作為支撐                                     |
| 判讀層（Derive） | case 作者的推論段、「我們判讀」「這意味著」「關鍵是」「核心是」「才是」等詞引出 | 用「作者判讀」「（case 中 X 屬作者推論層、本章引用此推論）」明示分層 |

兩層在章節引用時不可混用 — 把判讀升級為 fact 會讓章節失去 case 支撐、讀者回查 case 時發現章節說的「揭露」實際是作者推論。

---

## 跟「Case 類型決定引用深度」的差別

[#115 case 類型決定引用深度](../case-type-graded-citation-depth/) 看 case 整體類型（skeleton / medium / rich）、決定承接深度。本卡看 case 內部結構（觀察 vs 判讀）、決定引用時要不要分層。

| 維度           | #115 case 類型決定引用深度            | #116 fact vs derive 分層（本卡）          |
| -------------- | ------------------------------------- | ----------------------------------------- |
| 看什麼         | case 整體（行數 + 內容密度）          | case 內部結構（觀察段 vs 判讀段）         |
| 主要風險       | Skeleton 擴寫成 rich case（編造數字） | Rich case 內判讀層被當 fact 引用          |
| 應用範圍       | 所有 case 引用都要先判類型            | 主要適用 rich case + medium case 的判讀段 |
| 對應的失分類型 | over-extrapolation（編造）            | fact-derive 錯位（強化詞 / 漏條件）       |

兩者互補：

- Skeleton case：主要是前者風險（擴寫成 fact）
- Rich case：兩個風險都要防（先判類型、再分層引用）
- Medium case：前者風險低（mechanism 名稱明確）、後者風險中（「常見陷阱」段可能含判讀）

---

## 為什麼這層紀律重要

LLM 寫作引用 rich case 時、容易把兩層壓縮成「揭露 X」、把作者判讀升級為 case fact。讀者回查 case 時會發現章節說的「fact」實際是作者判讀、章節的論述失去 case 支撐。

backend/05 deployment 模組驗證、case fidelity reviewer 抓出 4 個 high issue 都屬此類：

### 實證 1：Riot Games 35ms 延遲

- **Case 觀察段**：「35ms 是競技遊戲（VALORANT、League）的可接受上限」
- **Case 判讀段**：「從這個門檻反推：玩家所在 region 不能跨洲、需要區域 cluster」
- **章節（錯）**：「揭露 35ms latency 反推 region 部署」← 合併兩層、把判讀寫成揭露
- **章節（對）**：「揭露 35ms 延遲門檻 + Local Zones / Outposts 區域部署、可推得『延遲門檻反推 region 部署數量』」← 分層標明

### 實證 2：GCP K8s 130K scale

- **Case 觀察段**：「control plane 極限取決於 storage backend」+「GCP 用 Spanner 替換 etcd」（兩個分開的點）
- **Case 判讀段**：「把 storage 從瓶頸變成『showed no signs of not being able to support higher scales』」
- **章節（錯）**：「揭露 Spanner 替 etcd 才是 K8s 規模極限的關鍵」← 把判讀升級成硬性結論、強化詞「才是」是訊號
- **章節（對）**：「揭露 control plane vs data plane 容量規劃要分開、storage backend（GCP 用 Spanner 替代 etcd）是 K8s 規模極限的核心瓶頸層」← 保留條件性表述

### 實證 3：Riot Games 漏歷史轉折

- **Case 觀察段**：「關鍵架構決策：從 multi-tenant cluster 模型改成 single-tenant per game」
- **章節（錯）**：「揭露 single-tenant per game 的多 cluster 策略」← 漏掉轉折、只保留終態
- **章節（對）**：「揭露架構決策從 multi-tenant cluster 改成 single-tenant per game」← 保留 case 揭露的關鍵歷史

---

## 引用句型對照

### Skeleton case 引用

```text
對應 [X.CN case-title]：揭露 X / Y / Z 三個方向（case 直接列出）；
以下展開基於通用工程知識補充。
```

### Rich case 引用（單層、純觀察）

```text
對應 [X.CN case-title]：揭露 X 具體數字 / 設計（case 觀察層）。
```

### Rich case 引用（含作者判讀）

```text
對應 [X.CN case-title]：揭露 X 觀察 + 作者判讀 Y（case 中 Y 屬判讀層、
本章引用此推論）。
```

### Rich case 引用（避免硬性結論）

避免使用「才是 / 必須 / 一定 / 關鍵是」這類強化詞、保留 case 原文的條件性表述（「取決於」「核心瓶頸」「主要驅動」）。

---

## 反模式

| 反模式                                                   | 後果                                                 |
| -------------------------------------------------------- | ---------------------------------------------------- |
| 引用句含「才是 / 必須 / 一定 / 關鍵是 / 唯一」這類絕對詞 | 通常是把作者判讀升級成 fact                          |
| 跨越兩段 case 內容（觀察 + 判讀）寫成單一斷言            | 應分層、否則 reviewer B 抓 high issue                |
| 引用後直接展開細節、沒給「以下基於通用工程知識補充」承接 | 容易把通用知識掛到 case 名下                         |
| 漏掉 case 揭露的歷史轉折、只保留終態                     | 把 case 的「決策轉折」教訓抹平、讀者失去歷史 context |
| Stage 1 抽 findings 不標來源層（觀察 / 判讀）            | Stage 2 寫作時無 mark、必踩 fact-derive 錯位         |

---

## Stage 1 抽 findings 的標明格式

抽 findings 時、rich case 的 finding 要標明來源層：

```text
Finding: 線性擴展是 OLTP 設計最高目標、coordinator 是傳統 OLTP 的擴展瓶頸
來源: 9.C10 Spanner 案例
- 觀察層：「2 nodes → 45K reads/sec, 4 nodes → 90K reads/sec」段（case fact）
- 判讀層：作者「線性擴展是最高目標」是推論（case 中標為判讀）
章節: 1.11 全球分散式 OLTP
引用方式: 觀察層直接引用、判讀層用「作者判讀」明示
```

Stage 2 寫作時依照 finding 列表的層別標記決定引用句型。

---

## 自掃描提示

寫作完後、檢查每處 rich case 引用是否：

1. 用了「才是 / 必須 / 一定 / 關鍵是 / 唯一」等強化詞 → 通常是把判讀升級成 fact
2. 跨越兩段 case 內容（觀察 + 判讀）卻寫成單一斷言 → 應分層
3. 引用後直接展開細節、沒給「以下基於通用工程知識補充」承接 → 容易把通用知識掛到 case 名下
4. 漏掉 case 揭露的歷史轉折 / 條件 / 邊界 → 重讀 case「決策段」補回

---

## 跟其他抽象層原則的關係

| 原則                                                                                 | 關係                                                             |
| ------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| [#115 案例引用深度跟著 case 類型走](../case-type-graded-citation-depth/)             | 互補 — #115 看 case 整體類型、本卡看 case 內部結構               |
| [#117 跨 case 合成 frame 必須標明](../cross-case-synthesized-frame-must-be-labeled/) | 第三類失分 — 章節 derive 升級成 case 揭露（07 新發現）           |
| [#104 security citation 時效精確](../security-citation-currency-and-precision/)      | conditional → unconditional drift 的姊妹卡                       |
| [#111 口語化修辭稀釋技術精度](../colloquial-rhetoric-erodes-technical-precision/)    | 強化詞屬「結局描述代替契約描述」、跟本卡的判讀層升級為 fact 同類 |
| [#83 Writing multi-pass review](../writing-multi-pass-review/)                       | 高 stakes 內容輪 E.5 citation 精確度檢查包含本卡紀律             |

---

## 判讀徵兆

| 訊號                                      | 該做的事                                                 |
| ----------------------------------------- | -------------------------------------------------------- |
| 引用句含強化詞（才是 / 必須 / 一定）      | 回 case 原文確認是 fact 還是 derive、derive 要降級或標明 |
| 找不到 case 原文的對應段                  | 引用是 LLM 推論、不是 case 揭露、退回「揭露 X 方向」     |
| Rich case 引用沒分層、整段平鋪            | 用「揭露 X 觀察 + 作者判讀 Y」重寫                       |
| 章節 + 通用工程知識段沒明確分隔           | 補「以下基於通用工程知識補充」承接                       |
| Reviewer B 抓 high issue 集中在 rich case | 紀律失效、整章節重審所有 rich case 引用                  |

**核心**：Fact 跟 derive 的差別不是「對不對」、是「來源是 case 還是作者」。讀者回查 case 時、要能反向 trace 章節的每個斷言到 case 原文的對應段、找不到的就是錯位。
