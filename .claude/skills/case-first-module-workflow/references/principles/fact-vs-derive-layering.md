# Fact vs Derive 分層原則

> **角色**：本卡是 `case-first-module-workflow` 的支撐型原則（principle）、被 [SKILL.md](../../SKILL.md)、[stage-1-case-audit](../stage-1-case-audit.md)、[reviewer-prompts/reviewer-b-case-fidelity](../reviewer-prompts/reviewer-b-case-fidelity.md) 引用。
>
> **何時讀**：Stage 1 抽 findings 時、Stage 2 寫作引用 case 時、Stage 3 設定 case fidelity reviewer 時。

## 核心原則

引用案例（特別是 rich case）時、要把 case 內容分成兩層：

- **觀察層（Fact）**：case 直接寫的具體事實 — 數字、設計細節、引用源直接列的內容
- **判讀層（Derive）**：case 作者的推論 — 「我們判讀」「這意味著」「關鍵是」「核心是」「才是」等詞引出的段落

兩層在章節引用時要分層標明、不可混用。

## 為什麼這層紀律重要

LLM 寫作引用 rich case 時、容易把兩層壓縮成「揭露 X」、把作者判讀升級為 case fact。讀者回查 case 時會發現章節說的「fact」實際是作者判讀、章節的論述失去 case 支撐。

## 跟 Skeleton case 風險的差別

| Case 類型     | 主要失分                                     | 範例                                                                                                               |
| ------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Skeleton case | 擴寫成 case 沒提的細節（編造數字、taxonomy） | case 說「異常查詢偵測維度」、章節寫「query 體積從 1MB / 天跳到 10GB / 天」（數字編造）                             |
| Rich case     | 把作者判讀層當 case fact 引用                | case 把「35ms 延遲」放觀察、把「反推 region 部署」放判讀；章節寫「揭露 35ms latency 反推 region 部署」（合併兩層） |

## 實證案例

來自 backend/05 模組驗證、Reviewer B 抓出的 4 個 high issue 都屬此類：

### Case 1：9.C12 Riot Games

- **Case 觀察段**：「35ms 是競技遊戲（VALORANT、League）的可接受上限」
- **Case 判讀段**：「從這個門檻反推：玩家所在 region 不能跨洲、需要區域 cluster」
- **章節（錯）**：「揭露 35ms latency 反推 region 部署」← 把判讀寫成揭露
- **章節（對）**：「揭露 35ms 延遲門檻 + Local Zones / Outposts 區域部署、可推得『延遲門檻反推 region 部署數量』」← 分層標明

### Case 2：9.C34 GCP 130K

- **Case 觀察段**：「control plane 極限取決於 storage backend」+「GCP 用 Spanner 替換 etcd」（兩個分開的點）
- **Case 判讀段**：「把 storage 從瓶頸變成『showed no signs of not being able to support higher scales』」
- **章節（錯）**：「揭露 Spanner 替 etcd 才是 K8s 規模極限的關鍵」← 把判讀升級成硬性結論
- **章節（對）**：「揭露 control plane vs data plane 容量規劃要分開、storage backend（GCP 用 Spanner 替代 etcd）是 K8s 規模極限的核心瓶頸層」← 保留條件性表述

### Case 3：9.C12 Riot — 漏歷史轉折

- **Case 觀察段**：「關鍵架構決策：從 multi-tenant cluster 模型改成 single-tenant per game」
- **章節（錯）**：「揭露 single-tenant per game 的多 cluster 策略」← 漏掉轉折
- **章節（對）**：「揭露架構決策從 multi-tenant cluster 改成 single-tenant per game」← 保留 case 揭露的關鍵歷史

## 引用時的標準句型

### Skeleton case 引用

```text
對應 [X.CN case-title]：揭露 X / Y / Z 三個方向（case 直接列出）；
以下展開基於通用工程知識補充。
```

### Rich case 引用（單層）

```text
對應 [X.CN case-title]：揭露 X 具體數字 / 設計（case 觀察層）。
```

### Rich case 引用（含作者判讀）

```text
對應 [X.CN case-title]：揭露 X 觀察 + 作者判讀 Y（case 中 Y 屬判讀層、
本章引用此推論）。
```

### Rich case 引用（避免硬性結論）

避免使用「才是 / 必須 / 一定 / 關鍵是」這類強化詞。保留 case 原文的條件性表述（「取決於」「核心瓶頸」「主要驅動」）。

## 抽 findings 時的標明格式

Stage 1 抽 findings 時、rich case 的 finding 要標明來源層：

```text
Finding: 線性擴展是 OLTP 設計最高目標、coordinator 是傳統 OLTP 的擴展瓶頸
來源: 9.C10 Spanner 案例
- 觀察層：「2 nodes → 45K reads/sec, 4 nodes → 90K reads/sec」段（case fact）
- 判讀層：作者「線性擴展是最高目標」是推論（case 中標為判讀）
章節: 1.11 全球分散式 OLTP
引用方式: 觀察層直接引用、判讀層用「作者判讀」明示
```

## 跟既有原則的關係

本原則跟 [case-type-discrimination](./case-type-discrimination.md) 互補：

- case-type-discrimination 解決「該不該引用具體細節」（看 case 類型）
- fact-vs-derive-layering 解決「引用時要不要分層標明」（看 case 內部結構）

Skeleton case 主要是前者風險、Rich case 兩個風險都要防。

## 自掃描提示

寫作完後、檢查每處 rich case 引用是否：

1. 用了「才是 / 必須 / 一定」等強化詞 → 通常是把判讀升級成 fact
2. 跨越兩段 case 內容（觀察 + 判讀）卻寫成單一斷言 → 應分層
3. 引用後直接展開細節、沒給「以下基於通用工程知識補充」承接 → 容易把通用知識掛到 case 名下
