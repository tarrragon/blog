---
title: "Commit message vs source code doc：兩份不同職責的文件"
date: 2026-05-05
draft: false
description: "Source code doc 寫給未來讀者、commit message 寫給回顧歷史的考古者。時序敏感的資訊（為什麼這次改、考慮過什麼方案）放 commit、持續適用的契約放 source。配合 git blame 工作流讓考古路徑清楚、source 不必背所有歷史。"
tags: ["git", "documentation", "code-quality", "methodology"]
---

> **核心命題**：source code doc 寫給「未來的讀者」，commit message 寫給「想了解過去發生什麼的考古者」。兩者是不同文件，內容該分開。
> **設計原則**：時序敏感的資訊（為什麼這次改動、考慮過什麼方案）放 commit；持續適用的資訊（當前契約、不變量）放 source。

> 本篇是 [函式文件分層設計](../function-doc-layered-design/) 反模式 3「過去式 doc」的展開——把「source 跟 commit message 的時序職責邊界」拉成獨立主題討論。

---

## 起點：兩份文件的職責容易被混在一起

Source code doc 的職責是「描述當前 code 的契約跟行為」、commit message 的職責是「描述某次改動做了什麼跟為什麼做」——兩者讀者不同、時序屬性不同、本該各歸各家。實務上這兩份文件的職責經常被混在 source code doc 一處：source 變成所有歷史的垃圾桶、commit message 反而沒人認真寫。

實務上常看到的污染：

```dart
/// 修了 issue #123 的 race condition
/// 從 v2.3 開始改用 lock-free 結構
/// TODO: @alice 之後可能要改用 SkipList
void process() { ... }
```

這段 doc 混了三類資訊：

1. **過去發生什麼**（修了 issue #123）→ 屬於 commit message
2. **過去做過什麼決定**（v2.3 開始改用 lock-free）→ 屬於 commit message / changelog
3. **未來可能要改什麼**（TODO @alice 改用 SkipList）→ 屬於 issue tracker / TODO 系統

**沒有一條是「未來讀者讀這份 code 需要的資訊」**——三條都凍結在過去某一刻、source 卻被當成歷史快照在用。要釐清這個問題、得先想清楚兩種文件各自的讀者與時間性。

---

## 時序差異：當前狀態 vs 狀態轉移

| 文件            | 描述什麼                       | 寫給誰讀                  | 時間性               |
| --------------- | ------------------------------ | ------------------------- | -------------------- |
| Source code doc | 當前 code 的契約、行為、不變量 | 即將呼叫 / 修改 code 的人 | **持續適用**         |
| Commit message  | 這次改動做了什麼、為什麼做     | 想了解某個變動的考古者    | **特定時間點的決定** |

關鍵差別是**時間性**：

- Source code doc 描述「**現在**這份 code 在做什麼」——只要 code 不變，doc 就持續有效
- Commit message 描述「**那一刻**為什麼要改 code」——commit 完成的那一秒就成為歷史

把過去式的內容塞進 source code doc，會讓 doc 變成「凍結在某個歷史時點的快照」，而不是描述當前狀態。

---

## 該寫在 commit message 的內容

Commit message 的核心職責是回答「**這次改動做了什麼、為什麼做**」——所有「凍結在某次提交時點」的資訊都應該住在這裡、而不是被塞進 source 變成過時快照。下面四類是最常被誤放進 source 的內容：

### 1. 改動的動機（為什麼這次要動）

```text
fix: prevent double-charge on payment retry

Payment gateway 對同一個 transaction_id 會回傳 200 但實際扣款兩次
（incident #4521）。在 client 端加上 idempotency_key，gateway
看到重複的 key 直接回 cached response。
```

「為什麼動」幾乎永遠屬於 commit message。**source code 只需要描述「現在的行為是什麼」，不需要解釋「過去為什麼變成這樣」**——除非那個「為什麼」對未來呼叫者仍是必須知道的限制（見後面段落）。

### 2. 評估過的替代方案（why not X）

```text
refactor: replace stream with reactive value

考慮過三個方案：
- A. 改成 broadcast stream：最 minimal，但保留同樣的 payload 語義模糊問題
- B. 加新 broadcast stream 平行存在：兩條 stream 容易不同步
- C. 拆成 reactive value（採用）：與系統其他 service 一致、消除多訂閱問題

選 C 因為與 codebase 其他 service 風格對齊，雖然改動範圍最大。
```

「考慮過 A、B、C，選了 C」這類資訊對 reviewer 重要，對未來讀 code 的人多半不重要——他們看到的是 C 的結果，不關心你考慮過 A、B。**這類資訊屬於 commit message / PR description**，不屬於 source code doc。

### 3. Migration / 部署相關步驟

```text
feat: migrate user_profile from int_id to uuid

注意：
- 跑 migration 0042 之前先確認所有 client 已升到 v3.2 以上
- migration 預估 2 小時（10M rows），建議週末執行
- rollback：reverse migration 0042 然後 redeploy v3.1
```

部署時序與步驟是當下發布動作的一部分，commit / release notes 該寫；source code 不該背這個負擔。

### 4. Bug 號、ticket 連結、incident 紀錄

```bash
fix: handle empty cart in checkout button visibility

Closes #1234
Related: incident-2026-04-12 (button stuck enabled)
```

把 ticket 號 / issue 連結寫在 commit message，git blame 出來的 commit 直接帶你去原始討論。寫在 source code 反而會 outdated（issue 關了、tracker 換了、URL 改了）。

---

## 該寫在 source code doc 的內容

Source code doc 的核心職責是描述「**當前 code 的契約跟行為**」——只要 code 不變、doc 就持續有效。下面四類是「持續適用」的資訊類別、屬於 source 的家：

### 1. 當前對外契約

```dart
/// 從本地購物車移除指定商品
///
/// 找不到對應品項時不做事；不會拋例外。
void removeFromLocalCart(CartItem item);
```

這是「現在這個 function 對 caller 承諾什麼」——持續適用，跟「上週為什麼加這個 function」無關。

### 2. 隱性需求 / 必要的呼叫順序

```dart
/// 必須在 [init] 之後呼叫；否則 throw `StateError`。
void process() { ... }
```

「呼叫順序」是當前 code 的契約限制，未來呼叫者必須遵守。屬於 source code doc。

### 3. 對未來讀者仍然重要的「過去原因」

少數情況下，「為什麼以前這樣決定」對未來讀者**仍是必要資訊**——典型是「這個寫法看起來怪，但有非顯然的原因」：

```dart
void processPayment(Payment p) {
  // 刻意不 retry —— payment gateway 是非冪等，retry 會造成重複扣款
  // （見 incident-2026-04-12）。失敗一律拋給上層人工處理。
  return _gateway.charge(p);
}
```

這條註解兼具「歷史原因」和「持續適用的限制」——未來維護者看到這段 code 會想「為什麼沒 retry？」，這條註解防止他「順手加上」。**這類兼具兩種性質的內容是少數該留在 source 的歷史相關 doc**。

判斷標準：「未來讀者**不知道這條歷史會做錯決定**嗎？」

- 是 → 留 source
- 不是 → 留 commit

### 4. 不變量 / invariant

```dart
class CircularBuffer {
  /// 元素數量永遠在 [0, capacity] 之間
  int get length => ...;
}
```

不變量是「這個型別永遠成立的事實」，是契約的一部分，屬於 source。

---

## 反模式

### 反模式 1：把 commit message 內容塞進 source

**正向概念**：source code doc 描述「現在的行為」、git log 才是「歷史演進」的家。兩者各自有對應的工具（IDE 看 doc、`git log` 看演進）、各司其職就能讓兩邊都精準。

```dart
// 反：寫成歷史紀錄
/// 2024-01-15 加上 retry 邏輯
/// 2024-03-22 改用 exponential backoff
/// 2024-07-08 加上 jitter 避免 thundering herd
Future<Response> fetch(String url) { ... }

// 正：source 只寫當前行為
/// 自動 retry 失敗的請求，使用 exponential backoff + jitter
Future<Response> fetch(String url) { ... }
// 演進歷史在 git log 看
```

把所有歷史塞進 source 等於在 source code 重做一份 git log——但 git log 已經存在、且結構化、可搜尋、有 author / timestamp。重做一份在 source 只會 outdated（下次再加邏輯時忘了補日期就破功）、而 git log 永遠是同步的。

### 反模式 2：commit message 只寫 "update" / "fix"

**正向概念**：commit message 是給未來考古者的線索——`git blame` 跳到一個 commit 時、message 是讀者拿到的第一份資訊。寫得清楚、考古路徑就短；寫得模糊、考古者得繼續挖 PR / 找原作者問。

```text
- update
- fix
- wip
- final
- final v2
- final v2 真的
```

這類 commit message 當下就沒人看得懂、半年後 `git blame` 把人帶到 message 寫 "update" 的 commit、等於把讀者帶到死巷。合理 commit message 的最小單位是 `<type>: <one-line summary>`、例如 `fix: handle empty cart in checkout`——一行就好、但要說清楚做了什麼。

### 反模式 3：source code doc 寫滿 TODO / FIXME

**正向概念**：「想未來改但還沒改」屬於 issue tracker——issue tracker 有優先序、有 owner、有 due date、能被排程。source code 的 TODO 沒有這些屬性、會被慢慢遺忘。

```dart
/// TODO: refactor to use streams
/// FIXME: handle null case
/// HACK: temporary workaround for issue #234
/// XXX: this is broken under high load
void doSomething() { ... }
```

這些都是「想未來改但還沒改」的事——把它們留在 source 有三個問題：

- TODO 在 source 不會被 prioritize（產品 / 專案管理工具看不到 source 內的 TODO）
- FIXME 在 source 容易被忽略（讀的人會想「不是我寫的不是我的問題」）
- HACK / XXX 警告**只在第一次讀時有效**、第二次讀的人會麻木

問題嚴重需要立刻處理 → 開 ticket、commit fix；不嚴重可以等 → 開 backlog ticket、source 別寫。把待辦項從 source 搬到 issue tracker、會被真正當成「待辦」處理。

### 反模式 4：把 PR description 抄一份進 source

**正向概念**：PR description 是「這次提交的時空快照」、source code doc 是「持續適用的當前契約」。兩者描述的是同一段 code 在不同時序下的不同切面、各自有對應的家。

```dart
/// 這個 function 是為了支援新的 multi-currency 結帳流程。
/// 詳細需求見 PR #4521 與設計文件 https://wiki.../...
/// 業務需求：客戶可以混合多幣別商品結帳，結帳當下統一換算成 settlement currency。
/// QA 已驗證 5 種主要幣別組合 + 邊界 case。
void multiCurrencyCheckout() { ... }
```

PR description 該寫的內容（業務脈絡、設計連結、QA 範圍）抄進 source、會讓 source 凍結在「**這次新增時的時空狀態**」——半年後 PR 已經是歷史、連結可能失效、QA 範圍可能擴展、但 source 還停在那一刻。PR description 留在 PR、source 只寫 function 當前的對外契約。

---

## Git blame archaeology workflow

當 source code doc 跟 commit message 各司其職時，**考古工作流**會變得清晰：

```text
讀者看到一段 code 不懂為什麼這樣寫
  ↓
先看 source code doc
  ↓
不夠 → 跑 git blame
  ↓
找到引入這段 code 的 commit
  ↓
讀 commit message
  ↓
不夠 → 點進去看完整 PR / issue
```

這個工作流要能順利跑，前提是：

1. **commit 顆粒度合理**——一個 commit 一個邏輯改動，不要「fix typo + refactor + add feature」混在一起，否則 blame 出來看到一個改 50 個檔案的 commit，message 寫 "stuff"，等於沒線索
2. **commit message 寫清楚動機**——不是「changed X」（git diff 看得出來），而是「changed X **because Y**」
3. **重大決定用 PR 描述補充**——commit message 太長不適合塞長文，PR description 是放長文的地方

如果這三點做到，未來讀 code 的人有一條清楚的考古路徑，不必逼 source code doc 背所有歷史。

---

## 一個分配工具

決定一條資訊放哪時，問三個問題：

1. **「未來讀者不知道這條會做錯決定嗎？」**
   - 是 → source code doc
   - 不是 → commit message
2. **「這條描述的是當前的行為，還是某次轉移？」**
   - 當前行為 → source code doc
   - 某次轉移 → commit message
3. **「Code 改了，這條會不會 outdated？」**
   - 不會（描述當前狀態）→ source code doc
   - 會（描述特定時間點）→ commit message

三個問題收斂到同一個直覺：**「凍結在過去」屬於 commit、「持續適用」屬於 source**。

---

## 邊界：什麼時候 source 還是該帶歷史脈絡

「歷史進 commit、契約進 source」是預設、**但有些情境 source 還是該保留歷史脈絡**——共通特徵是「未來讀者不知道這段歷史會做錯決定」：

- **看似怪、但有非顯然原因的寫法**：「刻意不 retry、payment gateway 是非冪等」——下個維護者順手加 retry 會出事
- **跟非預期外部行為對齊的 workaround**：「拆兩步 query 避開 SQLite 32-bit Android 的 integer overflow（issue #1234）」——讀者重構時會想「為什麼不一次查」
- **保留某段 code 的合規 / 法務原因**：「依 GDPR 留 30 天可恢復、不是直接刪」——縮短到 7 天會違反法規
- **效能調優的非顯然參數**：「batch size = 32 是 production 跑出來的甜蜜點、改大會 OOM」——下次 review 看到「為什麼不開大」時得知道過去的實驗結果

判斷標準：「未來讀者**不知道這條歷史就會做錯決定**嗎？」答「是」就留在 source、答「不是」就留在 commit。

---

## 一句話 heuristic

把整個討論濃縮：

> Source code doc 寫給「**正要動這段 code 的人**」、commit message 寫給「**想知道為什麼當初這樣寫的人**」。

寫東西之前先問：我寫這段，是要幫**正要動 code 的人**做對決定，還是要幫**回顧歷史的人**理解某次改動？兩個讀者要找的資訊不同，分成兩處寫，雙方都受惠。

---

## 收束：兩份文件協同，源頭就要分清楚

很多團隊抱怨「source code doc 太亂、commit message 沒人寫」，本質是這兩份文件的職責沒分清楚。Source 想包辦所有事就會充滿過時內容；commit message 沒人寫是因為「反正歷史會寫進 source」變成默認。

把兩者的職責分清楚，兩份文件都會變健康：

- **source 變短、變精準**：只寫當前契約，doc 不會 outdated
- **commit message 被認真寫**：因為它是某些資訊的唯一家
- **考古路徑清楚**：blame → commit → PR 是可預期的回溯路徑

寫 doc / 寫 commit 是同一個技能的兩面。不要把任何一邊當成另一邊的替代品。
