---
title: "L1 + L2 疊加時的訊號一致性：UX hint 跟自動 fallback 講的話要對齊"
date: 2026-04-26
weight: 90
description: "把 expectation alignment（L1）跟 augmenting computation（L2）疊加時、兩個 layer 給使用者的訊號可能矛盾：L1 說「請改打字」、L2 卻自動找到了；L1 說「資料可能延遲」、L2 卻 stale-while-revalidate 自動 refresh。沒對齊時使用者困惑。本卡定設計 protocol：兩個 layer 講同一個 capability gap、訊號要 layered consistent、不是 redundant 也不是 conflicting。本卡是 #75 + #86 + #79 在「使用者訊號層」的整合。"
tags: ["report", "事後檢討", "工程方法論", "Pattern", "UX", "Strategy"]
---

## 結論

把 [L1 expectation alignment + L2 augmenting computation 疊加](../capability-gap-three-layer-escalation/) 時、兩個 layer 給使用者的訊號要**對齊、不是 redundant 也不是 conflicting**：

| 兩 layer 的關係                                                                   | 使用者體驗             |
| --------------------------------------------------------------------------------- | ---------------------- |
| **Conflicting**（L1 說一回事、L2 做相反事）                                       | 困惑、不信任系統       |
| **Redundant**（L1 講 + L2 補的是同個東西）                                        | 噪音、L1 hint 失去意義 |
| **Layered consistent**（L1 講 capability、L2 自動補 + 訊號明示「這是 fallback」） | 清楚、信任             |

設計三條原則：

1. **L2 自動補時、訊號要明示「這是 fallback、不是 primary path」**
2. **L1 hint 要承認 L2 的存在**（不要假裝 L2 不存在）
3. **使用者一直能 trace「這個結果怎麼來的」**

---

## 為什麼疊加會打架

L1 跟 L2 各自設計、不協調時、訊號會相互削弱：

### Conflicting 例：search

| Layer       | 訊號                                                   |
| ----------- | ------------------------------------------------------ |
| L1 hint     | "搜尋為前綴匹配、找 backpressure 請打 backpre"         |
| L2 fallback | 自動 substring 找到 backpressure、顯示為 normal result |

User 打 "pre" → 看到 backpressure 結果 → 困惑：「不是說要打 backpre？」 → 不確定下次該怎麼搜。

### Redundant 例：retry with hint

| Layer    | 訊號                 |
| -------- | -------------------- |
| L1 hint  | "網路不穩、稍後再試" |
| L2 retry | 已經自動 retry 3 次  |

User 看到 hint → 自己 manual retry → 但 system 已經在 retry → 操作冗餘 → 不確定 retry 是 user 觸發還是 system。

### Conflicting 例：editor stale data

| Layer       | 訊號                                             |
| ----------- | ------------------------------------------------ |
| L1 banner   | "資料同步可能延遲幾秒"                           |
| L2 fallback | Stale-while-revalidate 自動 refresh、user 沒感知 |

User 看到 banner、但每次資料其實都是 fresh（refresh 完成）→ banner 變 noise。Banner 撤掉後又會在某次 revalidation 失敗時 leak 出 stale data → 信任崩潰。

---

## Layered Consistency 的三設計原則

### 原則 1：L2 自動補時、訊號明示「這是 fallback」

L2 不該無聲補強。當 L2 觸發、UI 應該標示：

| 場景                                    | Layered consistent 訊號                                                   |
| --------------------------------------- | ------------------------------------------------------------------------- |
| Search prefix-only + substring fallback | Result 上方標 "找到 substring 匹配（非標準前綴）"、user 知道這是 fallback |
| Retry on transient failure              | Spinner + "重試中（第 N 次）"、user 不需自己 retry                        |
| Stale-while-revalidate                  | "資料約 N 秒前"、user 知道是否需要 refresh                                |

關鍵：**「自動補但隱形」是 silent UX**、跟 [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/) 的「false confidence」同骨。

### 原則 2：L1 hint 要承認 L2 的存在

L1 hint 不該假裝是「全部能做的事」：

```text
壞：搜尋為前綴匹配、找 backpressure 請打 backpre
好：搜尋優先前綴匹配；找不到時會 fallback 到 substring（顯示時會標示）。
   想精準找 backpressure 直接打完整詞、或打 backpre。
```

L1 講 capability + L2 講 fallback、合在一起 = 完整的 mental model。

### 原則 3：可 trace 「結果怎麼來的」

User 能（不必、但能）看到結果的來源層：

- Search result 標 "prefix match" / "substring fallback"
- API response 標 `from_cache: true` 或 `freshness_seconds: 30`
- LLM response 標「來自 RAG retrieval / 來自 base model knowledge」

可 trace ≠ 強制顯示、是「想知道時可以知道」。預設可隱藏、debug / 進階 user 可展開。

---

## 反模式

| 反模式                              | 後果                                                                                                 |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------- |
| L2 隱形補強、L1 hint 沒提 L2        | 使用者不知道有 fallback、抱怨 hint 不準                                                              |
| L1 hint + L2 自動 retry 都顯示      | Redundant、user 重複動作                                                                             |
| L2 失敗時退回 L1 但訊號沒切換       | User 看到舊 hint、實際 system 在另一狀態                                                             |
| 「不要讓 user 看到 fallback」當原則 | Silent fallback 是 [#56 視覺完成 vs 功能完成](../visual-completion-vs-functional-completion/) 的反例 |
| L1 / L2 是不同 team 設計、沒協調    | 訊號自然衝突、需要 cross-team review                                                                 |
| Telemetry 沒分 L1 / L2 觸發比例     | 不知道哪 layer 真的解 gap                                                                            |

---

## 何時 conflicting / redundant 是合理的

少數情境：

| 情境                                    | 為什麼 conflicting / redundant 可接受 |
| --------------------------------------- | ------------------------------------- |
| L1 是 legal disclaimer（必要法律文字）  | 法律要求、不能因 L2 拿掉              |
| L2 是 emergency fallback、L1 是 primary | 各自負責不同 case、訊號可重疊         |
| 安全 critical 多重提醒                  | 重要訊號值得 redundant                |

三類共通：**訊號重複的成本 < 訊號漏掉的成本**。其他情境追求 layered consistent。

---

## 跟其他抽象層原則的關係

| 原則                                                                          | 關係                                                                |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [#75 主策略 + 補強疊加](../main-strategy-plus-supplementary/)                 | #75 講疊加可行、本卡講疊加後 UX 訊號層怎麼設計                      |
| [#86 Capability gap 三層階梯](../capability-gap-three-layer-escalation/)      | #86 講選哪層、本卡講疊加多層時訊號                                  |
| [#79 決策對話的五維度](../decision-dialogue-dimensions/)                      | 「使用者看到什麼」是 decision dialogue 的「呈現」維度、本卡是其特化 |
| [#56 視覺完成 vs 功能完成](../visual-completion-vs-functional-completion/)    | Silent L2 fallback 是「視覺完成、功能不誠實」的變種                 |
| [#62 誠實進度 UI](../pattern-honest-progress-ui/)                             | 本卡的「fallback 訊號明示」原則跟誠實進度同骨                       |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/) | 「自動補但隱形」是 false confidence 的 UX 變種                      |

---

## 套用到當前 search planning case

D + C1 疊加 case：

**Bad**（conflicting）：

```text
D hint: "搜尋為前綴匹配、找 backpressure 請打 backpre"
C1 fallback: 打 "pre" 自動 substring 找到 backpressure、跟其他 prefix result 混排
```

**Good**（layered consistent）：

```text
D hint: "搜尋優先前綴匹配。找不到時自動 fallback 到 substring（會標示）。"
C1 fallback UI:
  - Prefix matches（標準）：[後跟前綴匹配 results]
  - Substring matches（fallback）：[標示後跟 fallback results]
```

User 看到的：

- 打 "pre" → 立刻看到 prefix matches（如「prefetch」）
- 同頁標 "Substring fallback" 段、列「backpressure」等 substring 命中
- 看 hint 也知道為什麼有兩段

訊號對齊、user mental model 完整。

---

## 判讀徵兆

| 訊號                                  | 該做的事                              |
| ------------------------------------- | ------------------------------------- |
| L1 hint 寫完才寫 L2、沒重 review L1   | 退回重看 L1 是否承認 L2               |
| L2 自動補但 UI 看不出來               | 加 fallback 訊號                      |
| User 抱怨「hint 跟實際不一致」        | Layered consistency 沒做、補上        |
| L1 / L2 telemetry 沒分                | 不知道誰實際 close gap、補            |
| Hint 越寫越長                         | 可能 L2 沒 surface、L1 在補 L2 該講的 |
| 「user 看不到 fallback 比較單純」直覺 | Silent UX 反模式、 fallback 該明示    |

**核心**：L1 + L2 疊加不是「兩個獨立 layer 各自做事」、是**一個 capability gap 上的兩個訊號**。訊號要對齊、否則使用者收到的 mental model 是 broken。**Silent fallback 看起來簡潔、實際是 false confidence**。
