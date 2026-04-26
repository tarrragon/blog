---
title: "Dataset 規模改變什麼可行：「需要 index」是 production scale 的詞、不是普世詞"
date: 2026-04-26
weight: 89
description: "工程師習慣以「production scale」為預設、自動假設「O(N) scan 不可行、需要 index」。但小 dataset 內、O(N) 甚至 O(N²) 都 trivial、不該過度工程。本卡列具體 threshold（< 1MB / < 10MB / < 100MB / > 1GB）對應的可行操作、跟「猜測 production scale 過度設計」的反模式對照。本卡是 #43 最小必要範圍在「規模假設」維度的展現。"
tags: ["report", "事後檢討", "工程方法論", "原則", "Performance", "Scale"]
---

## 結論

「需要 index、需要 cache、需要 hot path」這類設計動詞、預設是 **production scale 的語言**。Dataset 小的時候、O(N) scan 甚至 O(N²) 都可能 trivial、不需要 index。

具體 threshold：

| Dataset 大小      | 可行操作                                                  | Index / cache 必要？                 |
| ----------------- | --------------------------------------------------------- | ------------------------------------ |
| **< 1 MB**        | O(N²) 全表 scan、JS regex、無腦比對                       | 完全不需要                           |
| **1-10 MB**       | O(N) full scan per query、簡單 in-memory 處理             | 通常不需要、有 index 是 nice-to-have |
| **10-100 MB**     | O(N) 仍可、但要避免 per-keystroke；考慮 lazy load + index | 開始需要                             |
| **100 MB - 1 GB** | 必須 index / 分塊 / streaming                             | 必要                                 |
| **> 1 GB**        | 必須分散式 / DB / search engine                           | 強制                                 |

**錯誤預設**：「production scale 設計」直接套用到小 dataset = 過度工程。**修法**：先量測實際 dataset 大小、再決定要不要 index。

---

## 為什麼預設 production scale 是反模式

寫程式的習慣偏好「scalable solution」 — 但在 small dataset 情境下：

- **過度工程成本**：寫 / 維護 index、cache invalidation、tiered storage 都是 cost
- **實際收益 0**：dataset 小、O(N) scan 已經 < 1ms、index 沒帶來感知差異
- **複雜度引入新 bug**：cache invalidation 是出名難題、small dataset 直接 scan 反而對

實務上 80% 內部工具 / 個人專案 / 小型部落格的 dataset 是「< 10 MB」級別。為它寫 production-scale 設計 = 為不存在的問題付成本。

---

## 具體 threshold 跟可行操作

每段 dataset 大小都有「直覺以為需要、實際不需要」的對照：

### < 1 MB（極小）

例：個人部落格內容 metadata、小型 config、單頁 SPA state。

| 直覺以為需要 | 實際不需要、可用                   |
| ------------ | ---------------------------------- |
| Search index | `Array.filter(text.includes)` 就夠 |
| Pagination   | 全載入、CSS scroll                 |
| Lazy load    | 一次全 fetch、< 100 KB 沒差        |
| Web Worker   | 主執行緒同步處理、< 1ms 不會卡     |
| Cache        | 重算每次、< 1ms 沒差               |

### 1-10 MB（小）

例：本部落格 raw markdown（7.5 MB、135 篇）、中型 documentation site、小型 e-commerce catalog。

| 直覺以為需要                       | 實際不需要、可用                                             |
| ---------------------------------- | ------------------------------------------------------------ |
| Search index 全集                  | Title-only index（更小）+ runtime substring fallback、依場景 |
| 分頁 query                         | 全 fetch + client filter                                     |
| Server-side rendering each request | Static + client interaction                                  |
| Database indexing                  | In-memory map（如果 query pattern 簡單）                     |
| Background indexing                | Build-time 一次處理                                          |

但有時候已經值得 index — 視 query 頻率、複雜度、UX 需求而定（看 [#87](../build-time-vs-runtime-computation-spectrum/) 四軸）。

### 10-100 MB（中）

例：中型公司內部工具的 user list、開源 project 全 repo、中型 dataset analytics。

| 直覺以為需要          | 實際                                                 |
| --------------------- | ---------------------------------------------------- |
| Index for everything  | 主要 query patterns 加 index、cold path runtime 仍可 |
| Aggressive pagination | 分頁 + filter pushdown                               |
| Server-side scan      | 通常仍可、加 cache 即可                              |
| 分散式處理            | 通常單機夠                                           |

### 100 MB - 1 GB（中-大）

例：中型 SaaS 的 user data、search engine over medium corpus、ML feature store。

| 直覺以為需要         | 實際                                       |
| -------------------- | ------------------------------------------ |
| Sharding             | 通常單機 SSD / RAM 還夠、先垂直擴展        |
| Distributed system   | Single-node DB（PostgreSQL）+ index 多半夠 |
| Custom search engine | Postgres FTS / SQLite FTS5 通常足夠        |
| Caching layer        | 必要、但簡單 LRU 即可                      |

### > 1 GB（大）

例：大型 SaaS、社交網路、search engine over web。

這個 scale 才真的需要 production-scale 設計：分散式、shard、index 嚴格設計、cache 多層、async pipeline。

---

## 「我以後會長大」的迷思

常見藉口：「現在 dataset 小、但以後會長大、所以該為以後設計」。

這個邏輯有兩個漏洞：

### 漏洞 1：未來成長不確定

多數內部工具 / 個人專案 / 中小企業 dataset **不會** 長到 production scale。為「以後可能爆炸」設計、多半是為不存在的未來付當下成本。

### 漏洞 2：成長前重 design 比現在 design 容易

當 dataset 真的長大、你會有：

- 真實的 query pattern（vs 現在猜的）
- 真實的 hot spots（vs 現在猜的）
- 真實的 budget（vs 現在估的）

**等需要時 redesign 比現在 over-design 划算**。當前 simple design 也比較容易被 redesign（複雜結構難動）。

---

## 反模式

| 反模式                                   | 後果                                                        |
| ---------------------------------------- | ----------------------------------------------------------- |
| 預設「需要 index」沒量 dataset           | 過度工程、抽象 leak                                         |
| 「production-grade」當設計詞、不分場景套 | 內部工具 over-engineered                                    |
| Big-O 思維直接套小 dataset               | 漏掉 constant factor、實際 O(N²) 比 O(N log N) 還快（小 N） |
| Cache 在 dataset < 1 MB 場景             | Cache invalidation 引入 bug、收益 0                         |
| 分散式設計在 single-node 夠用場景        | 維運複雜度爆炸                                              |
| 「scale 萬一爆」當預設                   | 機率低事件主導設計                                          |

---

## 何時應該照 production-scale 設計

| 情境                                                | 為什麼                     |
| --------------------------------------------------- | -------------------------- |
| 已知會在 6 個月內 grow 10x+                         | 證據明確、提前 design 划算 |
| 公開服務、流量不可控                                | 防爆炸、必要               |
| User-generated content（dataset size 由使用者決定） | 上限不可控                 |
| Real-time / SLA 嚴格                                | constant factor 也重要     |
| 已經慢了、有實證                                    | Bottleneck 已浮現          |

五類共通：**有證據 dataset 會大 / 已大 / 不可控**。其他情境用當前 dataset size 設計。

---

## 跟其他抽象層原則的關係

| 原則                                                                        | 關係                                                                  |
| --------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [#43 最小必要範圍](../minimum-necessary-scope-is-sanity-defense/)           | 本卡是 #43 在「規模假設」維度的展現 — 不該 over-claim 規模            |
| [#87 Build-time vs Runtime](../build-time-vs-runtime-computation-spectrum/) | #87 的「dataset 大小」軸跟本卡同骨                                    |
| [#86 Capability gap 三層階梯](../capability-gap-three-layer-escalation/)    | 小 dataset 內 L2 augmenting 通常足夠、不必跳 L3                       |
| [#67 寫作便利度](../ease-of-writing-vs-intent-alignment/)                   | 「寫 production-scale」比「量 dataset 再決定」容易、跟實際 ROI 反相關 |
| [#42 2 次門檻](../two-occurrence-threshold/)                                | 真實 production 問題 ≥ 2 次再升級設計、不為「萬一」設計               |

---

## 判讀徵兆

| 訊號                                 | 該做的事                                |
| ------------------------------------ | --------------------------------------- |
| 寫到「需要 index」沒先量 dataset     | 量、可能不需要                          |
| 寫到「production-scale」當形容詞     | 確認真的是 production scale、否則拿掉   |
| Cache 設計、dataset 卻 < 1 MB        | 拿掉 cache、直接重算                    |
| 分散式、卻是個人 project             | 退回 single-node                        |
| 「以後會長大」當理由                 | 等真的長大、現在用 simple               |
| Big-O 焦慮、卻沒量實際 latency       | 量了再決、constant factor 可能主導      |
| 「lazy load 是必要」沒看 bundle size | 確認 bundle 真的大、< 200 KB 全載入即可 |

**核心**：「需要 index / cache / 分散式 / lazy load」這類動詞**不是普世真理、是 production scale 的詞**。預設套用到小 dataset = 過度工程。**先量再決**、跟「猜的 scale」對齊不如跟「實際 dataset」對齊。
