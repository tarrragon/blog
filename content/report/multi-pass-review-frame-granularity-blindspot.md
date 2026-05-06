---
title: "Multi-pass review 的 frame 顆粒度盲點：抽象規則 → 具體訊號的轉譯不完整"
date: 2026-05-06
weight: 114
description: "Multi-pass review 跑了 4 輪、字句層問題（口語修辭 / 地區用語 / 依賴 code / 廢話前綴）仍漏 catch——揭露 frame 顆粒度盲點：抽象規則（如「機會成本語氣」「正向陳述」「最重要的話優先說」）沒被轉譯成具體訊號（如 grep keyword bank：「一輩子 / 碰巧 / 撞牆 / 下次 X 時 / 不是 A 而是 B」）。修法是把每條規則展開成可 grep 的 keyword bank、加 reader simulation 輪、加 self-criticism 輪。"
tags: ["report", "事後檢討", "工程方法論", "原則", "寫作", "review-process"]
---

## 論述基礎與限制

本卡的論述基於 **1 個 case**（[dart Stream 事故](../../work-log/dart_stream_controller_single_vs_broadcast/) 的 review 過程跑 4 輪後仍漏 catch 4 類字句層問題）抽出來的假說。具體限制：

- **樣本量極小**：「multi-pass review framework 顆粒度盲點」這個結論基於 1 次 review、不是多次跨主題 review 觀察到的 systematic pattern。可能是這個 reviewer（我）有特定盲點、不是 framework 本身的問題
- **三機制有效性未驗證**：keyword bank / reader simulation / self-criticism 三機制是 proposed mechanisms、未實際跑下一篇文章驗證能 catch 之前漏掉的問題類型
- **「reader simulation 由同 reviewer 執行」的根本質疑沒解決**：拿掉 code block 重讀、聽起來合理、但同一個人是否真能模擬「沒看過 code 的讀者視角」是疑問——記憶不會因為 code block 隱藏而消失。本卡提的修法是 partial fix、不是 root cause solution
- **「同一 reviewer 跑多輪 catch 高度相同」是直覺論述**：沒有實證、是直覺推論
- **跟其他卡互相 cross-link 形成迴圈論證**：本卡引 #110 / #111 / #113、但這幾張卡都源自同次事件、互相驗證有 selection bias 風險

讀者使用本卡時、把它當「**從一次 review 失誤抽出的盲點假說**」、不當「驗證過的 review framework 升級方案」。三機制是 starting point、有效性需要後續案例累積驗證。

---

## 核心原則

Multi-pass review 用「規則 frame」掃描、有效抓「結構性違反」（規則順序、論述結構、邊界段缺失）、但**這次 case 顯示對「字句層的具體訊號」覆蓋不足**——同個規則底下有大量具體訊號、reviewer 用記憶 sweep 容易漏掉一部分（這次 1 個 case 觀察、是否 systematic 有待累積）。

| 缺口類型     | Multi-pass 用「規則 frame」能抓     | Multi-pass 用「規則 frame」抓不到                    |
| ------------ | ----------------------------------- | ---------------------------------------------------- |
| 結構性違反   | 段落順序、論述結構、邊界段缺失      | —                                                    |
| 規則對齊     | 「應該 / 必須」絕對主義（明顯）     | 「碰巧 / 撞牆 / 一輩子」口語修辭（同樣違反但不明顯） |
| 用詞精度     | 術語原文錨點（contract / 領域先驗） | 地區漂移（屏 / 螢幕、默認 / 預設）                   |
| 論述自包含性 | H2 後加商業邏輯導引                 | 段落內依賴 code（「payload 第二段」）                |
| 句型結構     | 反例段落補正向錨點（明顯）          | 「不是 A 而是 B」結構（隱性違反）+ 廢話前綴 wrapper  |

關鍵差異是「規則理解」vs「具體訊號比對」：

- **規則理解**：reviewer 知道「正向陳述優先」這條規則
- **具體訊號比對**：reviewer 要逐句檢查所有可能違反該規則的具體句型

抽象規則 → 具體訊號的轉譯沒做完整、就會 systematic miss 一整類字句層問題。

---

## 為什麼「規則 frame」抓不到字句層問題

### 問題 1：抽象規則沒展開成具體訊號清單

每條規則有大量可能的違反句型——例如「規則五：最重要的話優先說」可能違反句型：

| 違反句型           | 具體案例                        | 在哪裡常見           |
| ------------------ | ------------------------------- | -------------------- |
| 廢話前綴 / wrapper | 「下次看到 X 時、做 Y」         | 結尾段、heuristic 段 |
| 觀察先 / 定義後    | 「實務上常看到：[code]」        | 起點段               |
| 否定先 / 肯定後    | 「不要先想 A、先想 B」          | 除錯思維、check list |
| 條件先 / 結論後    | 「在 X、Y、Z 條件下、結論是 W」 | 推導段               |
| 修飾先 / 主詞後    | 「考慮所有可能後、做 X」        | 提案段               |

reviewer 用「規則五」這個 frame 掃描、靠記憶找「這段有沒有違反規則五」——多半只 catch「觀察先 / 定義後」這個明顯 case、漏 catch 廢話前綴跟否定先行。

### 問題 2：缺乏 grep keyword bank

字句層問題有大量可 grep 的具體詞——但 reviewer 沒有 keyword bank、靠肉眼掃。例如：

| 規則類別  | 可 grep 的具體詞                                        |
| --------- | ------------------------------------------------------- |
| 口語修辭  | 一輩子 / 永遠 / 碰巧 / 剛好 / 撞牆 / 炸 / 鎖死 / 啊原來 |
| 廢話前綴  | 下次看到 / 下次寫 / 下次面對 / 下次遇到 / 之後再        |
| 否定先行  | 不要先 / 不是 A 而是 B / 不該 / 不能                    |
| 地區漂移  | 屏 / 默認 / 質量 / 視頻 / 文件（當 file 用）            |
| 依賴 code | 那個 / 這個 / 剛才的 / 上面的 / 第 X 段 / 就好 / 就能   |

每輪 review 用 grep 比對固定 keyword list、不靠 reviewer 記憶——能消除「靠記憶找違規」的 systematic miss。

### 問題 3：reviewer 自我審查的視角盲點

reviewer 讀自己寫的東西、會自動 fill in 上下文、感受不到讀者的真實閱讀體驗。例如：

- 「事件 payload 第二段帶了 X」——reviewer 寫的時候腦中有 code、知道「第二段」是什麼、感覺通順
- 讀者讀的時候沒有 code 在腦中、「第二段」是空的 reference、卡住

這個視角差異是 multi-pass review 的結構性盲點——同一個 reviewer 跑多輪、視角始終是寫作者視角、不是讀者視角。

### 問題 4：Multi-pass 缺 self-criticism 輪

每輪 review 都是 forward checking（這篇對齊規則嗎？）、沒做 backward critique（規則本身在這個情境是否夠細？有沒有 miss 的 frame？）。

如果規則框架本身不夠細、跑再多輪都掃不到 frame 之外的問題。

---

## 多面向：四類 missed 問題的分類

這次跑完 4 輪 multi-pass review、漏 catch 的 4 類問題：

### Miss 類型 1：口語修辭（規則七 / 規則五的字句層子場景）

漏 catch 的具體訊號:「一輩子只能 listen 一次」「碰巧能用」「立刻撞牆」「啊原來」「炸了」

**為什麼漏**：「規則七：機會成本語氣」掃了「應該/必須/不行」、沒掃「一輩子/碰巧/撞牆」這類修辭詞。修辭詞跟絕對主義詞屬於不同 keyword set、reviewer 沒同時掃。

**修法**：建立「口語修辭 keyword bank」、輪 4「術語精度」加掃。

### Miss 類型 2：地區漂移（規則四「術語」的子場景）

漏 catch 的具體訊號：「副屏」（中國用語、繁中應該用「副螢幕」）

**為什麼漏**：輪 4「術語檢查」聚焦在「中文 / 原文錨點」、沒掃「繁中 / 簡中漂移」。reviewer 預設「讀者地區」是台灣、但沒 explicit 用 keyword bank 比對。

**修法**：建立「地區用語對齊 keyword bank」（屏 / 默認 / 質量 / 視頻 / 文件 / 函數 / 介面 / 內存）、輪 4 加掃。

### Miss 類型 3：依賴 code 論述（規則二商業邏輯先於 CASE 的延伸）

漏 catch 的具體訊號：「事件 payload 第二段帶了 X」「就好 / 就能」

**為什麼漏**：規則二被理解成「H2 後加商業邏輯導引」、沒延伸到「論述本身不依賴 code」。reviewer 寫的時候腦中有 code、感受不到「依賴 code」的閱讀體驗。

**修法**：加「reader simulation」frame——拿掉所有 code block、再讀一次論述、看是否仍能理解。

### Miss 類型 4：廢話前綴 + 否定先行（規則五 + 規則六的字句層子場景）

漏 catch 的具體訊號：「下次看到 X 時、不要先想 Y」這類 hortative 結尾段

**為什麼漏**：規則五「最重要的話優先說」被理解成「核心原則先 / 例子後」、沒延伸到「廢話前綴 wrapper 句子」。規則六「正向陳述」被理解成「反例段落補正向錨點」、沒延伸到「『不是 A 而是 B』結構」。

**修法**：建立「廢話前綴 + 否定先行 keyword bank」、輪 5 加掃。

---

## 修補 multi-pass review 框架的三個機制

### 機制 1：Keyword bank（具體訊號清單）

每條規則展開成可 grep 的 keyword list、每輪 review 用 grep 比對、不靠 reviewer 記憶。

範例 keyword bank（節選）：

```text
口語修辭：
  一輩子 / 永遠 / 碰巧 / 剛好 / 撞牆 / 炸 / 鎖死 / 啊原來 / 沒事 / 乾淨

廢話前綴 / 否定先行：
  下次看到 / 下次寫 / 下次面對 / 下次遇到 / 不要先 / 不是 X 而是 Y

地區漂移（繁中讀者）：
  屏 / 默認 / 質量 / 視頻 / 文件（當 file）/ 函數 / 接口 / 內存 / 視頻

依賴 code 訊號：
  那個 / 這個 / 剛才的 / 上面的 / 第 X 段 / 就好 / 就能 / 就行
```

每篇文章 review 時跑這些 grep、把 hit 列出來、決定保留或修補。

### 機制 2：Reader simulation 輪

加一輪「假設讀者沒有上下文、能不能讀懂這段論述」、嘗試換視角。具體做法：

- **拿掉所有 code block 後重讀**：論述是否 self-contained？
- **跳到段落中間直接讀**：不依賴前文、能不能 parse？
- **隨機抽段給陌生讀者讀**：cold-read 能不能拿到關鍵資訊？

**已知限制**：同一 reviewer 即使拿掉 code block、記憶仍在、無法完全模擬「沒看過 code 的讀者視角」。這個機制是 partial fix——能 catch 部分上下文依賴、但不是 root cause solution。最終解法仍需引入外部讀者反饋（cold-read by 真實讀者）。

### 機制 3：Self-criticism 輪

加一輪「我這份規則本身在這個情境是否夠細、有沒有 miss 的 frame？」、強迫 reviewer 反向審視框架本身。具體 prompt：

- 「我跑的 N 輪、catch 的問題類型有哪些？」
- 「同個規則底下、還有哪些可能違反句型沒被掃到？」
- 「如果讀者報告 X 類問題、是哪輪該 catch 但沒 catch？」
- 「framework 本身是否有 known blind spot？」

self-criticism 輪不是「再跑一次規則 frame」、是「**檢視 frame 本身的覆蓋度**」。

---

## 為什麼這些機制不能被「再仔細一輪」取代

### 「再仔細一輪」的同 frame 盲點

reviewer 跑同一個 frame 兩次、catch 的東西**多半**高度相同——因為視角、知識、注意力分配相同。（這是直覺論述、未做受控實驗驗證；但跟「換 frame」的設計動機一致——multi-pass 的核心就是「同 frame 重看 catch 不到新問題」）Multi-pass review 的核心是「每輪換 frame」、不是「同 frame 多跑幾次」。

但**換 frame ≠ 換規則**——reviewer 可能換規則但用同樣的視角、同樣的記憶 sweep、catch 的東西相同。要真正換 frame、需要：

- **換工具**：keyword bank 取代肉眼掃（機制 1）
- **換視角**：模擬讀者取代 reviewer 視角（機制 2）
- **換層次**：審視 framework 取代套用 framework（機制 3）

三個機制各自處理「同一 reviewer 跑多輪仍 miss」的不同來源。

### Hindsight 視角的反向印證

[#110 設計檢討用當下三軸論證、不依賴 hindsight](../design-flaw-by-current-axes-not-hindsight/) 的核心議題是「事後諸葛論述」會混淆「設計缺陷 vs 需求演化」。同樣的 hindsight 風險也存在於 review 流程：

- **Hindsight 視角**：「讀者反饋了 → 補進規則」——把規則當成「事故後補的 patch」
- **當下三軸視角**：「framework 本身是否夠細到 catch 這類問題？」——把 framework 當成預設工具、用 self-criticism 反向審視

兩種視角的差別跟 #110 的差別同骨：前者依賴結局（讀者反饋）、後者用當下框架審視（self-criticism）。

---

## 識別訊號：什麼時候你的 review framework 不夠細

### 訊號 1：讀者反饋的問題類型在 framework 裡找不到對應 frame

讀者指出「廢話前綴」問題、reviewer 翻 framework 找對應 frame——找到「規則五最重要的話優先說」、但這條規則沒展開到「廢話前綴」這個具體子場景。

修法：把問題類型加進 framework 的 keyword bank、下次同類問題能被 grep catch。

### 訊號 2：跑了 N 輪、相同類型的問題仍重複出現

字句層問題（口語修辭、地區漂移）跑了 4 輪 review 仍漏——表示 framework 沒 catch 這個層次。

修法：加 keyword bank（機制 1）、不靠 reviewer 記憶。

### 訊號 3：reviewer 自我審查感覺通順、讀者反映卡住

「事件 payload 第二段」對 reviewer 通順、對讀者卡住——視角差異。

修法：加 reader simulation 輪（機制 2）。

### 訊號 4：相同 framework 跑不同主題、catch 的問題類型差異不大

framework 不會自我批判——跑 100 篇文章、catch 的都是 framework 內的 frame、framework 外的問題永遠看不見。

修法：加 self-criticism 輪（機制 3）、定期審視 framework 本身的覆蓋度。

---

## 何時不需要這些補強機制

「multi-pass review 需要 keyword bank + reader simulation + self-criticism」這條原則在 production 教學文章 / 設計檢討文章成立、但有合理例外：

| 情境                              | 為什麼不需要                                                      |
| --------------------------------- | ----------------------------------------------------------------- |
| 短篇 note / 即時更新              | 預期讀者群小、不擴散、字句層問題影響有限                          |
| 個人筆記                          | reviewer = reader、視角差異不存在                                 |
| Review framework 已成熟、團隊內化 | keyword bank 已經內化成 reviewer 的反射、不需要 explicit 工具     |
| Framework 規模太小                | framework 只有 3-5 條規則時、self-criticism 容易出 false positive |

判讀：寫之前自問「這篇文章的讀者群有多大？字句層問題擴散的代價有多高？」——大 / 高 → 嚴格用三機制；小 / 低 → 可放寬。

---

## 跟其他抽象層原則的關係

| 原則                                                                                           | 跟本卡的關係                                                                                            |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| [#83 Multi-pass review](../writing-multi-pass-review/)                                         | 本卡是 #83 的延伸——#83 講「每輪換 frame」、本卡講「frame 本身要夠細、且需要工具 / 視角 / 層次三軸補強」 |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)                      | 用「規則 frame 掃描」是 reviewer 的寫作便利、用「keyword bank + reader simulation」是費力但精準         |
| [#95 Multi-pass review 的 scope 要蓋同類風險區](../multi-pass-scope-must-cover-risk-zone/)     | #95 處理「scope 軸」（review 多廣）、本卡處理「frame 顆粒度軸」（規則展開多細）、兩軸正交               |
| [#110 設計檢討用當下三軸論證、不依賴 hindsight](../design-flaw-by-current-axes-not-hindsight/) | hindsight 視角會把 review framework 當「補丁」、self-criticism 用當下框架審視、跟 #110 同骨             |
| [#111 口語化修辭會稀釋技術精度](../colloquial-rhetoric-erodes-technical-precision/)            | #111 是字句層的「具體訊號」之一、本卡是「為什麼字句層訊號被 framework 漏 catch」的 meta 層              |

---

## 判讀徵兆

| 訊號                                    | 該做的行動                                                         |
| --------------------------------------- | ------------------------------------------------------------------ |
| 讀者反饋了 framework 裡找不到對應 frame | 加進 keyword bank、補進 framework 的 frame 列表                    |
| 跑 N 輪後同類問題仍出現                 | framework 不夠細、加機制 1（keyword bank）                         |
| reviewer 通順 / 讀者卡住                | 加機制 2（reader simulation 輪）                                   |
| framework 從來沒被質疑過                | 加機制 3（self-criticism 輪）、定期審視 framework 本身             |
| 多輪 review 跑完還是同 reviewer         | 引入外部讀者反饋、或刻意換視角（不同 IDE / 不同字體 / 跳段順序讀） |

**核心原則**：multi-pass review 用「規則 frame」掃描有效抓結構性違反、抓不到字句層具體訊號。要 catch 字句層、需要把規則展開成 keyword bank、加 reader simulation 視角、加 self-criticism 反向審視 framework 本身——三個機制各自處理同 reviewer 跑多輪仍 miss 的不同來源。

---

## Self-case：本卡的觸發來源

本卡的觸發是修 [Dart StreamController：single-subscription vs broadcast 的踩坑實錄](../../work-log/dart_stream_controller_single_vs_broadcast/) 時、跑了 4 輪 multi-pass review 後仍漏 catch 4 類字句層問題、由讀者點出。

讀者反饋的問題類型：

1. 口語化修辭（「一輩子只能 listen 一次」「立刻撞牆」「啊原來」「碰巧能用」）
2. 地區用語漂移（「副屏」是中國用語、台灣用「副螢幕」）
3. 依賴 code 論述（「事件 payload 第二段帶了」預設讀者看過 code）
4. 廢話前綴 + 否定先行（「下次看到 X 時、不要先想 Y、先問 Z」）

這 4 類問題對應的 frame 在 framework 裡都有（規則七機會成本、輪 4 術語、規則二商業邏輯、規則五最重要的話優先說）——但都沒展開到具體訊號層、所以 reviewer 跑了 4 輪都漏 catch。

對應本卡：**framework 的覆蓋度盲點不能靠「再仔細一輪」修補——同一 reviewer 跑同 framework 多輪、catch 的東西高度相同。要真正擴大覆蓋度、需要 keyword bank（換工具）+ reader simulation（換視角）+ self-criticism（換層次）三個機制**。

對 multi-pass review framework 的修補方向：把這 4 類問題加進對應 frame 的 keyword bank、加 reader simulation 輪當輪 8、加 self-criticism 輪當輪 9（或在每輪結尾加 self-criticism 子段）。
