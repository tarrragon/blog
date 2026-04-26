---
title: "Capability gap 的對策三層階梯：expectation → augment → rebuild"
date: 2026-04-26
weight: 86
description: "系統有 capability gap（功能不滿足使用者預期）時、對策有三層階梯：L1 expectation alignment（UX hint、訊息精準）、L2 augmenting computation（補一層計算 close gap）、L3 structural rebuild（換 index / engine / 演算法）。三層成本、覆蓋率、脆弱度遞增、不必每次跳到 L3。本卡是 #75 主+補強策略的「不疊加、選層級」變種、跟 #59 五策略矩陣可疊加使用。"
tags: ["report", "事後檢討", "工程方法論", "原則", "抽象層", "Strategy"]
---

## 結論

當系統能力不滿足使用者預期（capability gap）時、對策有三層階梯、依序評估：

| 層                            | 對策                                      | 例                                                                    | 成本  | 覆蓋率                 | 脆弱度                  |
| ----------------------------- | ----------------------------------------- | --------------------------------------------------------------------- | ----- | ---------------------- | ----------------------- |
| **L1 Expectation alignment**  | 用文字 / UI / 訊息對齊使用者預期          | UX hint「搜尋為前綴匹配、找 backpressure 請輸入 backpre」             | 極低  | 部分（需要使用者配合） | 0                       |
| **L2 Augmenting computation** | 在既有 engine 上加一層補強計算、close gap | Client-side substring fallback、retry with backoff、computed fallback | 低-中 | 高（自動補齊）         | 中（多一條 path）       |
| **L3 Structural rebuild**     | 換 index / engine / 演算法本身            | Build-time tokenize、換 search engine、重設計 schema                  | 中-高 | 滿（從 source 解決）   | 高（動 build pipeline） |

**預設順序**：L1 → L2 → L3、依「成本最低先解」。**不必每次跳到 L3** — L3 是最完整但也最貴、L1 在很多情境就夠。

---

## 為什麼有階梯：cost-coverage trade-off 是真實的

直覺反應遇到 capability gap 都想 L3「從根解決」。但 L3 的成本通常 10-100x 於 L1、覆蓋率提升可能只是 80% → 99%、邊際 ROI 低。

實際分布：

- 50% case：L1 就夠（gap 是「使用者誤解」、講清楚就好）
- 30% case：L2 解掉（gap 是「engine 差一步運算」、補一層 close）
- 20% case：必須 L3（gap 是「engine 模型錯位」、補不夠、要重來）

**先試 L1、再試 L2、最後 L3** = 用真實 ROI 排序、不是用「完美主義」排序。

---

## 三層的判讀

### L1：expectation alignment

**適合**：

- Gap 是「使用者預期跟 system capability 對不齊」、不是「system 算錯」
- 使用者改變行為就能 close gap（打字方式、order operation、輸入格式）
- Production 真的有 capability、只是 affordance 不明顯

**不適合**：

- Gap 在 system 算錯、不是預期錯位
- 使用者無法配合（流量大、不可能教育每個 user）
- 訊息會被忽略（A/B test 證明 hint 沒人讀）

**例**：

| 領域                          | L1 對策                                         |
| ----------------------------- | ----------------------------------------------- |
| Search prefix-match           | UX hint「搜尋是前綴匹配」+ examples             |
| Database eventual consistency | UX「資料同步可能延遲幾秒」+ refresh button      |
| LLM token limit               | UI 提醒「附件太長、預期會被截斷」               |
| Network failure               | Toast「網路不穩、稍後再試」                     |
| Concurrent edit               | Banner「另一人也在編輯、你看到的是 5 秒前版本」 |

---

### L2：augmenting computation

**適合**：

- Engine 缺一層計算就能 close gap、額外計算不貴
- Client / proxy / wrapper 層可加運算、不動 engine
- 預期 query 量在 augment 計算容量內

**不適合**：

- 補強計算成本爆炸（dataset 大、O(N) per query）
- Augmenting 跟 engine 結果語意不一致（產生 ghost results）
- 需要兩 engine 同步狀態才正確

**例**：

| 領域                | L2 對策                                             |
| ------------------- | --------------------------------------------------- |
| Search prefix-match | Client-side substring fallback（再掃 client cache） |
| Distributed sort    | Client-side merge of partial sorted streams         |
| LLM context window  | RAG 切片 + retrieval 補齊                           |
| Cache miss          | On-demand compute + write back                      |
| Stale data          | Background refresh + serve stale-while-revalidate   |

---

### L3：structural rebuild

**適合**：

- L1 / L2 都不夠、capability gap 持續引發痛苦
- Production scale 大、L1 教育成本爆 / L2 計算成本爆
- 系統還沒長太大、重 build 成本可承受
- 將來會反覆遇到同類 gap（一次重 build、長期解多個問題）

**不適合**：

- L1 / L2 還沒試
- Production scale 不可動 build pipeline / schema
- ROI 不確定（gap 影響範圍小、值得 L3 投入嗎？）

**例**：

| 領域                | L3 對策                                                    |
| ------------------- | ---------------------------------------------------------- |
| Search prefix-match | Build-time tokenize、換 search engine（Algolia / Elastic） |
| Distributed sort    | Sharded sort + index in build pipeline                     |
| LLM context window  | Larger model、custom fine-tune                             |
| Cache miss          | Schema redesign、prefetch policy                           |
| Stale data          | Event-driven invalidation、CRDT                            |

---

## 從 L1 升級到 L2 / L3 的訊號

不是「永遠先 L1」、是「依訊號逐層升級」：

| 訊號                                             | 升級到                              |
| ------------------------------------------------ | ----------------------------------- |
| L1 ship 後使用者抱怨「我看到 hint 但還是不會用」 | L2（hint 不夠、要 system 自動補強） |
| L1 + L2 ship 後 search miss 率 > X%              | L3（structural fix 必要）           |
| L1 + L2 ship 後 augment 計算成本 > Y             | L3（換結構降低 marginal cost）      |
| Use case 從 cosmetic 升級成 production-critical  | L3（風險 / SLA 提升）               |
| 同類 gap 在系統內出現第 3 次                     | L3（重 build 一次解多個）           |

**逐層升級** vs **一次跳 L3**：前者是 #76 分批 ship 的具體展現；後者是「便利驅動偏移」（[#67](../ease-of-writing-vs-intent-alignment/)） — 容易寫的選項是 L3「一勞永逸」、跟實際 ROI 不對齊。

---

## 從 L3 / L2 降級回 L1 的訊號

階梯不是只能升、也該能降 — L3 ship 後不該當「永久解」、是 ROI 動態的選擇。看到以下訊號、考慮降級：

| 訊號                                               | 降級到                            |
| -------------------------------------------------- | --------------------------------- |
| L3 transformation 每次 dependency upgrade 都要修   | L1 / L2（L3 維護成本 > 收益）     |
| Use case 變化、L3 解的問題已不存在                 | 拔掉 L3、退到 L2 或不需要         |
| L3 ship 後 close gap 率 < 10%（投入 / 受益不對等） | 可能該重設計、不只升降            |
| Pagefind / engine 升級後 native 支援了             | 拔 L3 transformation、用 native   |
| L3 引入新 bug 比解的 gap 多                        | 退回 L1 + 顯式說「不支援」更誠實  |
| L1 hint 已經教育大多數 user 改變行為               | L2 / L3 fallback 觸發率低、可降級 |

### 為什麼降級難

升級有「使用者抱怨」當外部觸發、降級沒有 — 沒人抱怨「我們的 transformation 太多」。所以降級是典型的 [#72 高 ROI 無觸發](../external-trigger-for-high-roi-work/) 工作、需要結構性 trigger：

- Periodic review（每季 review「我們還需要這個 L3 嗎」）
- Dependency upgrade event（升級觸發「L3 還相容嗎、還必要嗎」）
- Maintenance cost log（紀錄 L3 修了 N 次、累積到 threshold 觸發 review）

### Pruning 不是失敗

降級不是「我們之前做錯」、是「ROI 變化、調整」。L3 在 ship 當下是最佳解、現在不是了 — 接受 capability gap 對策也會過時、跟其他工程決策同。

---

## 階梯 vs 疊加：跟 #75 的差別

[#75 主策略 + 補強策略](../main-strategy-plus-supplementary/) 講的是**多策略疊加在不同層**（structural + UX 並用）。本卡講的是**同一個 gap 上、選哪一層**（L1 vs L2 vs L3 通常選一個）。

兩卡互補：

- #75：選了 L3 後、要不要再加 L1 UX hint 當補強？（疊加維度）
- #86（本卡）：先試 L1 還是直接 L3？（階梯維度）

實際 case 通常兩條都用：先 #86 選層級、再 #75 看要不要疊加。

---

## 反模式

| 反模式                                   | 後果                          |
| ---------------------------------------- | ----------------------------- |
| 跳過 L1 直接 L3                          | 過度工程、ROI 邊際            |
| L1 ship 後不評估、預設要繼續 L3          | 缺數據、可能 L1 已夠          |
| 「L1 是 hack、L3 才是 real fix」道德判斷 | 阻止 L1 的價值、使用者多受苦  |
| L2 augmenting 沒邊界、dataset 變大時 OOM | L2 該升 L3 了沒升             |
| L1 hint 寫滿但 production 沒監測有沒有用 | 不知道 hint 有沒有 close gap  |
| 同類 gap 每次都 L3 一次                  | 缺 #75 疊加思維、每次重 build |

---

## 何時直接跳 L3

| 情境                                      | 為什麼                      |
| ----------------------------------------- | --------------------------- |
| Gap 是 security / data integrity          | L1 / L2 不夠、必須 root fix |
| 已 L1 / L2 過 N 次、gap 還在              | 證據累積、L3 ROI 已正       |
| Production scale 不允許 L1 教育 / L2 計算 | 跨過 L1 / L2 的可行區       |
| 重 build 成本當前最低（系統還小）         | 越早 L3 越便宜              |

四類共通：**L1 / L2 已知不夠、或 L3 真的最便宜**。其他情境都該先試 L1。

---

## 跟其他抽象層原則的關係

| 原則                                                                          | 關係                                                                  |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [#75 主策略 + 補強疊加](../main-strategy-plus-supplementary/)                 | #75 是「同 gap 上選不選疊加」、本卡是「先選哪層」 — 互補              |
| [#76 分批 ship](../incremental-shipping-criteria/)                            | L1 → L2 → L3 升級 = 分批 ship 在 capability 維度的展現                |
| [#73 search 匹配模式](../search-engine-matching-mode-mismatch/)               | search prefix-match 是本卡 L1 / L2 / L3 三層的具體 case               |
| [#59 五策略選擇矩陣](../filter-source-composition-strategies/)                | #59 的五策略可重新映射到本卡三層（A 推進 query = L3、D UX hint = L1） |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/) | L1 / L2 多偏字面層、L3 動結構、選層需 multi-pass review               |

---

## 判讀徵兆

| 訊號                              | 該做的事                                  |
| --------------------------------- | ----------------------------------------- |
| 寫到「直接 L3」沒講為什麼不 L1    | 補 L1 評估、確認真不夠                    |
| L1 ship 後沒監測 close gap 率     | 補 telemetry、決定要不要升 L2             |
| 「這個 hint 沒用、user 不讀」抱怨 | 確認是真不讀還是 hint 寫不對、不直接跳 L3 |
| L2 augmenting 成本越來越高        | 升 L3 的訊號、不是 L2 寫得不夠好          |
| 同類 gap 第 3 次 L1 解掉          | 抽 pattern、可能該寫成 reusable component |
| L3 ship 後 L1 hint 沒拔           | 三層共存反而冗餘、清理                    |

**核心**：Capability gap 不是只有 L3 一條路 — L1 / L2 / L3 是 ROI 不同的三層階梯、依「成本最低先解」順序評估。**「直接 L3」的便利感跟實際 ROI 反相關**（[#67](../ease-of-writing-vs-intent-alignment/)）— 寫 L3 在白板上很爽、但通常 L1 / L2 已夠。
