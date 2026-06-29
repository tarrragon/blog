---
title: "WRAP Widen Options 容易塌成稻草人 framing、要改 evidence weight 結構"
date: 2026-05-20
weight: 140
description: "WRAP 框架的 Widen Options 段在案例寫作中容易塌成「列爛選項 → 打掉 → 留正解」的修辭結構、變成稻草人 setup。問題不在框架本身、在於寫作時把 Widen Options → Reality Test 當作全文 narrative 主軸。修法是把 Widen Options 從「對抗稻草人」改成「並陳合理因果鏈用 evidence 配重」、Reality Test 從 binary verdict 改成 weight assessment + Falsifier。是 #125 Collapse 在 WRAP 寫作 surface 的具體 instance、#79 多軸決策的姊妹卡。"
tags: ["report", "事後檢討", "工程方法論", "原則", "WRAP", "Writing", "Framing"]
---

## 核心原則

WRAP 框架的 Widen Options 段落是「探索本質不同的因果解釋」、不是「列出競爭性派系然後打掉錯的」。當寫作時把「Widen Options → Reality Test」當作全文 narrative 主軸、整個 hypothesis space 探索就會塌成「兩弱一強稻草人」結構—A、B 是 dummy、C 永遠預設正解、Reality Test 用來證明 C。讀者第一遍可能不發現、第二遍就會看穿是修辭、不是真實的選項擴增。

| 段落責任      | 塌成稻草人時的症狀                     | 正確的形態                                                    |
| ------------- | -------------------------------------- | ------------------------------------------------------------- |
| Widen Options | A 派 / B 派 / C 派、C 永遠正解         | 解釋 (1) / (2) / (3)、每個有 prior + testable prediction      |
| Reality Test  | 「A 不成立、B 不成立、C 成立」三連否定 | Evidence weight assessment、各配「強 / 中 / 弱」訊號 + 估佔比 |
| 結論          | 「正確解釋是 C」winner-takes-all       | 「主因 X / 次因 Y / 邊際 Z」多解釋並存配 Falsifier            |

判別問題：「刪掉 Reality Test 那段、單看 Widen Options 那段、讀者能不能猜出哪個是正解？」能猜出 = 稻草人結構、不能猜出 = 真正的 widen。

---

## 情境

寫商業 case-analyses 套 WRAP 框架時、最容易踩的陷阱是把 Widen Options 寫成派系命名 + 預設正解、然後 Reality Test 一條一條打掉。寫作者的心理路徑很自然：先有觀點 → 為了「公平」列出反方 → 為了「驗證」打掉反方 → 留下原本就要說的觀點。這個流程跑完、Widen Options 段落變成修辭裝飾、不是真正的 hypothesis space 探索。

具體 case（2026-05-20、e00253c 修法前）：blog 寫 3 篇 case-analyses（[Claude for Legal](/business/case-analyses/claude-for-legal/) / [FDE 軍備競賽](/business/case-analyses/fde-arms-race/) / [CoreWeave 收購 Bufstream](/business/case-analyses/bufstream-acquisition/)）、3 篇全部踩同一個結構：

- claude-for-legal：A「AWS 類比派」/ B「保護傘派」/ C「Enterprise Lock-in 派」、C 預設正解
- fde-arms-race：A「模仿派」/ B「策略選擇派」/ C「結構性被迫派」、C 預設正解
- bufstream：對 CoreWeave 為什麼買、X「業務擴張」/ Y「技術自主」、Y 預設正解

3-reviewer audit 平行跑、3 個 reviewer 獨立都點出「兩弱一強稻草人」結構共通—診斷一致是這個 pattern 不是個別失誤、是 WRAP 套案例寫作的系統性陷阱。e00253c 重寫後改為「解釋 (1) / (2) / (3) / (4) 並陳因果鏈、每個有 prior + prediction」、Reality Test 改為 evidence weight assessment + Falsifier、Round 2 驗證通過。

---

## 理想做法

### 第一步：Widen Options 改成「並陳的合理因果鏈」、不是派系命名

每個選項要滿足四個判準：

1. **有實際 prior**：誰持這論、為何合理。Prior 可以引用 VC / 創辦人 / 學者 / 業界分析師的公開立場、或從產業結構推導出的合理初始假設。
2. **有 testable prediction**：若這個解釋成立、會看到什麼具體 evidence（合約規模、客戶分布、銷售節奏、員工流向）。
3. **跟其他選項的因果鏈本質不同**：不是同一個結論的不同包裝、是不同的因果起點。
4. **不是設定就要被打爆的 dummy**：選項要站得住、要可被讀者挑戰、不是 reductio ad absurdum 的設定。

選項命名用中性編號「解釋 (1) / (2) / (3)」、避免「X 派 / Y 派 / Z 派」派系暗示—派系命名自帶「選邊」修辭框架。

### 第二步：Reality Test 改成 evidence-based weight assessment

不是「A 不成立、B 不成立、C 成立」三連否定、而是給每個解釋配 evidence 強度 + 估佔比百分比：

```text
解釋 (1)：強訊號（觀察 X、Y、Z 都支持）— 估佔比 ~50%
解釋 (2)：中等訊號（觀察 W 支持、觀察 V 部分反駁）— 估佔比 ~30%
解釋 (3)：弱訊號（難排除巧合）— 估佔比 ~20%
```

允許多選項並存、用「主因 / 次因 / 邊際」權重判讀、不是 winner-takes-all。最後綜合判讀用「主要承擔 A 功能、伴隨 B 跟 C 兩個次要動機」這類多解釋並存的措辭。

### 第三步：補 Falsifier 段、列出每個解釋的反證訊號

每個解釋配對應的 Falsifier：「若觀察到 X、解釋 (N) 主導論垮、要重評估」。這跟 Tripwire 段銜接、形成可監控的判讀結構。Falsifier 不是「整套論述崩」、是 partial revision—某個解釋的權重變化、不一定推翻整個分析框架。

### 第四步：完稿時跑「刪 Reality Test 測試」

寫完後、心裡 simulate「刪掉 Reality Test 那段、讀者單看 Widen Options 那段能不能猜出哪個是正解」。能猜出就是稻草人結構、需要重寫 Widen Options 讓選項真的並陳。

---

## 沒這樣做的麻煩

### 修辭被讀穿、信任度下降

讀者一旦看穿稻草人結構、會懷疑作者的真誠度跟結論可靠度。教學文章靠「分析嚴謹」立信、稻草人結構直接破壞這個基礎。本 blog 的 3-reviewer audit 之所以能 3 個 reviewer 獨立都 catch 到同一個 pattern、就是因為這個結構在 careful reader 眼中明顯—第一篇可能蒙混、第三篇就會被當成 systematic 修辭技倆。

### Hypothesis space 探索失效、判讀框架不可遷移

WRAP 的核心價值是「強制做 hypothesis space 探索、防止認知偏誤」、稻草人結構讓 Widen Options 退化成修辭裝飾、原本要解的「直覺接受第一個解釋」問題沒被解。讀者拿走的判讀框架也不可遷移到下次事件—因為框架的應用方式本身就是錯的、套到新事件還是會列稻草人。

### Tone 滑成 opinion piece

「我列出爛選項打掉、留下正解」的結構帶有「我來糾正你」的姿態、整篇 register 從教學滑向 opinion piece。即使每個字句都中性、整體 tone 仍會偏。本 blog case-analyses 重寫前的 register 評估是 opinion 40% / blog 30% / teaching 20% / academic 10%、重寫後翻轉到 teaching 55-60% / academic 25-35% / blog ≤ 15%—單純改 framing 結構就能整體位移 register。

---

## 跟其他抽象層原則的關係

- **[#125 Collapse 是隱形預設](../collapse-is-implicit-default/)**：本卡是 #125 在「WRAP Widen Options」surface 的具體實例。Widen Options 塌成「兩弱一強」是把高維 hypothesis space collapse 到便利的「正解 vs 稻草人」二維。修法是預設展開多選項、選窄要 evidence 支持、不是修辭便利。

- **[#79 決策對話的五維度](../decision-dialogue-dimensions/)**：sister 卡。#79 是 decision-making 多軸、本卡是 WRAP 寫作多軸；兩者結構同骨—Widen Options 不能塌成 2 維、就像 decision dialogue 不能塌成單軸。

- **[#126 寫作 review 是多軸完整性](../writing-review-multi-axis-completeness/)**：本卡是 review 設計時要看「frame 軸」的具體 instance。寫 case-analyses 時 review 不能只看「結構是否符合 WRAP」、要看「Widen Options 是否真的並陳 hypothesis、還是塌成稻草人」。Frame 軸的覆蓋要包含 framing 結構檢查、不只是規則 check。

- **[#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)**：本卡是 #82 在「framing 層級」的具體案例。lint 規則層（字面）catch 得到「不是」「不要」等否定詞密度、但 catch 不到「整段 framing 結構是稻草人」這個行為層問題。Framing 違規屬於 #82 的「行為精煉」維度、需要 reviewer agent 跑 multi-pass 才能捕獲。

- **[#83 Writing multi-pass review](../writing-multi-pass-review/)**：本卡是 review 第 4-5 輪該掃的「framing 維度」。前幾輪掃結構 / 術語 / 規範、framing 屬於 review 後段才能看穿的層次（因為要對全文 narrative 結構評估、不是單句檢查）。

---

## 判讀徵兆

| 訊號                                                  | 該做的事                                                            |
| ----------------------------------------------------- | ------------------------------------------------------------------- |
| Widen Options 用「X 派 / Y 派 / Z 派」派系命名        | 改成「解釋 (1) / (2) / (3)」中性編號、避免派系暗示                  |
| 某個選項沒有實際 prior（沒人持這論）                  | 該選項是稻草人、改寫成有實際擁護者的版本或刪掉                      |
| Reality Test 連續用「A 不成立、B 不成立、C 成立」     | 改成 evidence-based weight assessment、給每個解釋配 estimated 比例  |
| 刪掉 Reality Test 後讀者能猜出哪個是正解              | 稻草人結構、需要重新設計 Widen Options 讓選項真的並陳               |
| 文章 opening 用「市場敘事 X、但 X 不重要、Y 才是」    | 改成「正向陳述事件 + 結構性論點」、把對他人敘事的回應降為下游表象   |
| 結論斷言「正確解釋是 X」「最強訊號是 Y」              | 改成「相容度最高 / 能解釋以下 N 項觀察」evidence-based 措辭         |
| Reviewer 報告說「兩弱一強結構」「選項都很容易被打掉」 | 框架被當修辭、不是 hypothesis 探索、改 framing pivot                |
| 多個 reviewer 獨立 catch 到同一個結構問題             | 不是個別失誤、是 systematic 陷阱、要從 framing 層改、不只 word swap |

---

## 適用範圍與邊界

- **適用範圍**：
  - 用 WRAP 框架寫商業 case-analyses、市場事件拆解、產業策略分析
  - 用其他類似「列選項 / 對比 / 收斂」框架寫案例（5W1H、5-Forces、JTBD 階段）
  - 寫「對抗主流敘事 + 提出新解釋」類型的分析文章—這類最容易踩
- **不適用**：
  - 純技術教學（無 hypothesis space 探索、Widen Options 段落本身不存在）
  - 既有 case 的事後紀錄（Outcome 已定、不需要 widen）
  - 觀察筆記（明確標為個人觀察、不假裝是結構化分析）
- **邊界**：「對抗稻草人」跟「列負面反例做對照」不同。AGENTS.md 原則二允許「反例段落、目的為對照」、本卡禁的是「把對抗稻草人當 narrative 主軸」。少量負面反例可保留、整段不可由稻草人結構主導。判別線：反例是否單獨成段並主導 narrative 結構—成段主導就違規、附句對照就可接受。
