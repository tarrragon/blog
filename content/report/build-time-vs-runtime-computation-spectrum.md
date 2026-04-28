---
title: "Build-time 預處理 vs Runtime 計算的光譜：何時把成本前置"
date: 2026-04-26
weight: 87
description: "計算可放 build-time（預處理一次、runtime 0）或 runtime（per query 算）— 兩極之間有 hybrid 段（hot path 預算、cold path runtime）。判準四軸：query 頻率 / dataset 大小 / freshness 需求 / build pipeline 複雜度。Build-time 不是「永遠較好」、freshness / 多樣性高時 runtime 反而對。本卡把 #59 五策略中「query-side pushdown vs client-side fallback」的取捨抽象化、跨領域適用。"
tags: ["report", "事後檢討", "工程方法論", "原則", "抽象層", "Performance", "Architecture"]
---

## 結論

計算放哪裡有光譜、不是二元：

| 位置                | 預付成本                      | Runtime 成本                   | 儲存成本              | Freshness                   | 適合                           |
| ------------------- | ----------------------------- | ------------------------------ | --------------------- | --------------------------- | ------------------------------ |
| **Pure build-time** | 高（pipeline + 一次計算全部） | ~0                             | 高（存 N 種預算結果） | 差（每次 build 才 refresh） | 高頻 query、少變動、closed-set |
| **Hybrid hot-path** | 中（預算 top X%）             | 低（hot 命中 0、cold runtime） | 中                    | 中（hot stale 風險）        | 長尾分布、可分 hot/cold        |
| **Pure runtime**    | 0                             | 高（per query）                | 0                     | 即時                        | 低頻、高變動、open-ended query |

光譜兩端都有合理場景、不是「build-time 永遠贏」。**選哪個位置依四軸：query 頻率 / dataset 大小 / freshness 需求 / build pipeline 複雜度**。

---

## build-time 的三個成本維度

直覺反應：「能 precompute 就 precompute、runtime 0 最好」。但這個直覺漏了三個維度：

### 1. Freshness 成本

Build-time 結果是 build 那一刻的 snapshot。dataset 改變後、結果直到下次 build 才 refresh。

- **適合 build-time**：靜態 / 慢變的內容（blog post、product catalog）
- **不適合 build-time**：頻繁更新（user posts、live data、search index over user content）

### 2. 儲存成本

Precompute N 種 query 的結果 = 存 N 份。當 query 是 open-ended（任意組合 filter / sort / search term）、N 是組合爆炸。

- **適合 build-time**：closed-set（fixed list of routes、pre-defined search terms）
- **不適合 build-time**：open-ended（任意 user input）

### 3. Pipeline 複雜度

Build-time 計算需要 build pipeline 配合 — 加一條規則 = 加一份 artifact、需要 CI 跑、版本管理、deployment 同步。

- **適合 build-time**：已有 build pipeline、加一條規則便宜
- **不適合 build-time**：純 dynamic system、加 build step = 引入新 infrastructure

---

## 四軸判準

評估某個計算該放哪一端：

### 軸 1：Query 頻率

- **高頻**（同一 query 每秒被 call N 次）→ build-time 划算（一次算、N 次受益）
- **低頻**（query 多樣、每個 query 唯一）→ runtime 划算（precompute 全部 = 浪費）

### 軸 2：Dataset 大小

- **小 dataset** → 兩端都可以、依其他軸
- **大 dataset** → build-time 的儲存成本爆炸、傾向 runtime / hybrid
- **超大** → 幾乎強制 runtime（即使 hot path 也 partial precompute）

### 軸 3：Freshness 需求

- **可接受 stale**（小時 / 天） → build-time 可行
- **要近即時**（分鐘級） → runtime 或 hybrid + invalidation
- **強即時**（秒級） → 強制 runtime

### 軸 4：Build pipeline 複雜度

- **既有 pipeline 成熟** → 加 build-time step 便宜
- **沒 pipeline 或脆弱** → runtime 更實際（不引入新 infrastructure）

---

## 三段光譜的實例對照

### Pure build-time

| 領域          | 例子                                         |
| ------------- | -------------------------------------------- |
| 靜態網站      | Hugo / Jekyll generate HTML                  |
| Search index  | Pagefind build-time index、Algolia indexer   |
| Image 變體    | sharp / imagemin pre-generate sizes          |
| Route table   | Compile-time routes（Next.js static export） |
| ML model      | Train once、serve trained weights            |
| Sitemap / RSS | Build-time generate                          |

### Hybrid hot-path

| 領域                | 例子                                                |
| ------------------- | --------------------------------------------------- |
| Cache (Redis)       | Hot keys precompute、cold keys runtime + write-back |
| CDN                 | Hot routes cached、cold routes hit origin           |
| LLM RAG             | Hot embeddings precompute、cold runtime embed       |
| Search autocomplete | Top N suggestions precompute、tail runtime          |
| Image responsive    | Hot sizes precompute、edge cases runtime resize     |

### Pure runtime

| 領域                                               | 例子                   |
| -------------------------------------------------- | ---------------------- |
| Live search over user data                         | 每 query 掃 DB         |
| User-specific compute（dashboard、recommendation） | 每 user 每次 reload 算 |
| Real-time analytics                                | per-event 處理         |
| Open-ended NLP query                               | LLM call per query     |
| Crypto / hash signature                            | Per-request 算         |

---

## 兩極之間的決策：當不確定該選哪端

### 步驟 1：列「query frequency × dataset size」象限

|                | 小 dataset | 大 dataset               |
| -------------- | ---------- | ------------------------ |
| **高頻 query** | Build-time | Hybrid（hot precompute） |
| **低頻 query** | 兩端都可   | Runtime                  |

### 步驟 2：套 freshness 限制

如果 freshness 需求高、把 build-time 列從候選移除（除非有 incremental build / invalidation 機制）。

### 步驟 3：看 build pipeline cost

如果 build-time 成本（新 step、新 artifact、新 deploy 流程）大於 runtime 成本（per query CPU）、選 runtime。

### 步驟 4：留 escape hatch

選了一端不代表永遠 — 設計 invalidation hook / runtime fallback、未來能重新平衡。

---

## 反模式

| 反模式                                            | 後果                                                                     |
| ------------------------------------------------- | ------------------------------------------------------------------------ |
| 「能 precompute 就 precompute」當預設             | freshness / 儲存爆炸                                                     |
| 「runtime 比較動態」當預設                        | 高頻 query 浪費 CPU                                                      |
| Build-time 沒留 invalidation hook                 | dataset 改了無法 refresh                                                 |
| Hybrid 沒明示 hot 邊界                            | 運作不穩、cold path 突然爆量                                             |
| 把 freshness 假設成「不變」                       | 真實 dataset 會變、blowup                                                |
| Pre-build 全部 + runtime 又再算一次               | 雙倍成本、無增益                                                         |
| 「先 runtime、之後 optimize 成 build-time」當口號 | optimize 那次永遠不發生（[#72](../external-trigger-for-high-roi-work/)） |

---

## 何時是「兩端都不對、要重思 problem」

| 訊號                                       | 該做的事                                  |
| ------------------------------------------ | ----------------------------------------- |
| Build-time 結果 stale、runtime 又太慢      | Hybrid + invalidation 設計                |
| Hybrid hot 一直 miss、cold path 是常態     | 重排 hot 邊界、可能整個翻成 pure runtime  |
| Open-ended query 試圖 build-time           | Reformulate problem、可能要分 query class |
| 加了 invalidation 後 build pipeline 太複雜 | 改成 runtime + cache、別再強行 build-time |

---

## 跟其他抽象層原則的關係

| 原則                                                                     | 關係                                                                                            |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| [#86 Capability gap 三層階梯](../capability-gap-three-layer-escalation/) | L3 structural rebuild 通常是「動 build-time 計算」、本卡是 L3 內部的具體取捨                    |
| [#59 五策略選擇矩陣](../filter-source-composition-strategies/)           | A 推進 query（runtime）vs C 預先建 index（build-time）vs B 自動續抓（hybrid）— 五策略的本卡映射 |
| [#75 主策略 + 補強疊加](../main-strategy-plus-supplementary/)            | Hybrid hot-path 是 build-time + runtime 疊加的具體 case                                         |
| [#43 最小必要範圍](../minimum-necessary-scope-is-sanity-defense/)        | Hybrid 的 hot 邊界 = 最小必要範圍、有證據再擴張                                                 |
| [#73 search 匹配模式](../search-engine-matching-mode-mismatch/)          | Build-time tokenize（B 策略）vs client-side fallback（C 策略）就是本卡兩極的具體 case           |

---

## 判讀徵兆

| 訊號                                  | 該做的事                                      |
| ------------------------------------- | --------------------------------------------- |
| 「能 precompute 就 precompute」沒列軸 | 套四軸（頻率 / 大小 / freshness / pipeline）  |
| Build-time artifact 越來越大          | 檢查 query frequency 分布、可能該移到 hybrid  |
| Runtime 計算成本爆                    | 找 hot path、考慮 hybrid                      |
| Freshness 抱怨                        | Build-time 已不適用、改 hybrid + invalidation |
| 加了 build step 後 deploy 變慢        | Build pipeline 成本不可忽略、評估是否仍划算   |
| Hybrid 邊界從沒重新 review            | hot / cold 比例會漂移、定期重 baseline        |

**核心**：Build-time vs runtime 是光譜、不是二元 — 中間 hybrid 段是多數實務情境的最佳位置。**「能 precompute 就 precompute」是便利驅動（[#67](../ease-of-writing-vs-intent-alignment/)）的口號**、實際要套四軸（頻率 / 大小 / freshness / pipeline）才知道該放哪。
