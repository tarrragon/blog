---
title: "WRAP 是寫作者的內部工具、不是文章章節結構"
date: 2026-05-20
weight: 141
description: "WRAP 框架（Anchor Check / Step 0 / Widen Options / Reality Test / Attain Distance / Prepare to be Wrong / Tripwire）是寫作者背後做 hypothesis 探索與認知偏誤防護的內部工具。當把這些 process 標籤暴露成文章章節標題、讀者會踩三個壞 effect：預設讀者認知、塞滿 meta dialogue、同論點重複預告。修法是把 WRAP 工作內嵌進教學 narrative、章節順序服從教學流程。是 #140 WRAP Widen Options 稻草人的上位原則、跟 #125 Collapse 同骨。"
tags: ["report", "事後檢討", "工程方法論", "原則", "WRAP", "Writing", "Reader-experience"]
---

## 核心原則

WRAP 框架（含 Anchor Check / Step 0 / Widen Options / Reality Test / Attain Distance / Prepare to be Wrong / Tripwire）是寫作者背後做 hypothesis space 探索與認知偏誤防護的內部工具。當把這些 process 標籤暴露成文章章節結構、讀者體驗會被三個壞 effect 破壞：

| 壞 effect                  | 症狀                                                                                                    |
| -------------------------- | ------------------------------------------------------------------------------------------------------- |
| 預設讀者認知對齊           | 開頭用「X 是這套機制的末端表象」假設讀者已有 X 的認知、但「事件本身」段還沒交代                         |
| 塞滿分析報告 meta dialogue | 章節充斥「我們不討論什麼 / 錨點問題是什麼 / 資料充足度判斷是 X」這類寫作者內部 review 對話              |
| 同論點重複預告             | 在開頭、Anchor Check、Step 0 三個段落各預告一次「本篇要拆什麼」、推進緩慢、讀者第三遍才開始接觸實質內容 |

修法是把 WRAP 工作內嵌進教學 narrative、章節順序服從「讀者最快理解事件結構」的教學流程、不是「WRAP 七步驟」的 process 順序。

---

## 情境

寫 3 篇商業 case-analyses（[Claude for Legal](/business/case-analyses/claude-for-legal/) / [FDE 軍備競賽](/business/case-analyses/fde-arms-race/) / [CoreWeave 收購 Bufstream](/business/case-analyses/bufstream-acquisition/)）第一版時、把 WRAP 七步驟全部當章節標題暴露給讀者：

```text
[開頭]
## 事件本身
## Anchor Check：要回答什麼
## Step 0：資料充足度
## Widen Options：N 個解釋路徑
## Reality Test：用實證驗證
## [結構性機制章節]
## Attain Distance：長期影響
## Prepare to be Wrong：預先設計失敗回退
## Tripwire：何時重新評估
## 結論：可遷移框架
```

3-reviewer audit + Round 2 重寫後、讀者再次 feedback 指出三個具體問題：

第一、claude-for-legal 開頭寫「『律師會被取代』是這套機制的末端表象、本篇從上游動作開始拆」—但「事件本身」段在開頭之後、讀者還不知道有「律師會被取代」這個敘事存在、開頭預設了讀者跟作者共享的 context。

第二、Anchor Check 段寫「錨點問題聚焦在結構、而非個別公司執行力」—這是「為什麼不討論某個非問題」的 disclaim、屬於分析報告 frame、不是教學 frame。讀者根本沒問「會討論個別公司執行力嗎」、預先 disclaim 反而增加閱讀成本。

第三、「這個動作對應用層 SaaS、新創、知識工作者三層分別造成什麼影響」這個論點在開頭、事件本身、Anchor Check 三段各出現一次—讀者讀到 Anchor Check 還沒接觸實質內容、只是被預告了三次同一件事。

更深層的問題是：把 WRAP 從「寫作者的內部工具」當成「文章的章節結構」。WRAP 是寫作者背後 review 自己有沒有做完 hypothesis 探索的 checklist、不是讀者要走的步驟序列。

---

## 理想做法

### 第一步：WRAP 工作在腦中或草稿跑完、不暴露到讀者

WRAP 七步驟是寫作者完稿前要做完的 internal review：

- 我有沒有做 Anchor Check（搞清楚要回答什麼）？
- 我手上的 evidence 夠不夠下結論（Step 0 資料充足度）？
- 我有沒有列出所有合理因果解釋（Widen Options）？
- 每個解釋我都用 evidence 驗證了（Reality Test）？
- 我有看 5-10 年長期影響嗎（Attain Distance）？
- 我列了關鍵假設跟反證訊號嗎（Prepare to be Wrong）？
- 我設了何時重新評估的 Tripwire 嗎？

這七題自己回答完、不寫進文章。文章是教學 deliverable、不是 review process 的 paper trail。

### 第二步：章節結構服從教學流程、不是 WRAP 步驟順序

教學流程的合理順序：

```text
[開頭 1 段]                 直接描述事件 + 一句帶到本篇拆解什麼
                            無預設讀者認知、不對抗他人敘事

## 事件本身                  把事件講清楚、包括同期動作、為什麼值得拆
                            讀完讀者知道「發生了什麼」

## 為什麼 X（教學段）         把 Widen Options + Reality Test 內嵌進教學 narrative
                            含並陳因果解釋（每個有 prior + prediction）+ evidence 配重

## 結構性機制章節             把分析結果展開成讀者可吸收的結構知識
                            按層 / 維度 / 時間軸組織、不按 WRAP 步驟

## 長期影響與機會成本          Attain Distance 內容、移除 process 標籤

## 預警訊號                   Prepare to be Wrong + Tripwire 合併
                            教學語氣：「假設一 / 假設二 / 假設三 + 監控訊號」

## 可遷移的判讀框架           結論段、給讀者帶走的工具
```

### 第三步：開頭不對抗他人敘事、不預設讀者認知

開頭只做兩件事：

- 描述事件（讀者進入 context）
- 一句話帶到本篇要拆什麼（讀者知道接下來會讀到什麼）

不做這些事：

- 「市場敘事是 X、但 X 不重要、Y 才是」（contrarian framing、見 [#140](../wrap-widen-options-strawman-risk/)）
- 「X 是這套機制的末端表象、本篇從上游動作開始拆」（預設讀者已有 X 的認知）
- 「我們不討論個別公司執行力」（分析報告 frame、不是教學 frame）

對其他敘事的回應、放到「事件本身」段、有 context 後才提：「公開討論集中在 X—這是這個動作的下游表象、本篇焦點在觸發它的上游機制」。讀者讀完「事件本身」段、才有 context 理解 X 是什麼、預設讀者認知的問題自然消失。

### 第四步：完稿時跑「process metadata 掃描」

寫完後、grep 文章章節標題、檢查有沒有殘留：

```bash
grep -E "^## (Anchor Check|Step 0|Widen Options|Reality Test|Attain Distance|Prepare to be Wrong|Tripwire)" *.md
```

任何命中、都是 WRAP process metadata 暴露給讀者。改成教學標題：

| WRAP 標題           | 教學標題                            |
| ------------------- | ----------------------------------- |
| Anchor Check        | （刪除、放開頭段或事件本身段）      |
| Step 0 資料充足度   | （刪除、放在「為什麼 X」段內）      |
| Widen Options       | 為什麼供應商選擇 X / 為什麼買方出手 |
| Reality Test        | （同上段、不單獨成段）              |
| Attain Distance     | 長期影響與機會成本                  |
| Prepare to be Wrong | 預警訊號：何時重新評估這個分析      |
| Tripwire            | （同上段、用表格列訊號）            |

---

## 沒這樣做的麻煩

### 讀者預期被預設、認知門檻不對齊

開頭「X 是末端表象、本篇拆上游」要求讀者已經知道 X 是什麼。如果 X 在後文才介紹、讀者在開頭就被 confused、之後讀「事件本身」段才搞懂、回去重讀開頭—閱讀成本翻倍。

### Register 從教學滑成分析報告

「Anchor Check」「Step 0 資料充足度」「Reality Test」這類詞屬於 analyst 內部對 own work 的 review 對話、不是給讀者看的章節標題。把這些暴露給讀者、整篇 register 從「教學知識庫」滑成「給同行看的分析報告」、讀者輪廓變成「已經懂 WRAP 框架的分析師」而非「想學商業分析的工程師」。

### 同論點重複預告、推進緩慢

WRAP 七步驟本來就有「先講要回答什麼、再講資料、再講選項、再驗證」的內在重複—每一步都會提到核心論點一次。如果七個步驟全部變章節、核心論點會在前三段被預告三次（開頭、Anchor Check、Step 0 都會講「本篇要拆什麼」）、讀者讀到 Reality Test 才接觸實質內容。

### WRAP 框架的價值被當成修辭裝飾

WRAP 的真正價值是讓寫作者做 hypothesis 探索、防認知偏誤。當 WRAP 變章節結構、讀者跟寫作者都會把它當成「應該照走的 process」、原本的 hypothesis 探索變成「填表」、防認知偏誤的功能失效。

---

## 跟其他抽象層原則的關係

- **[#140 WRAP Widen Options 容易塌成稻草人 framing](../wrap-widen-options-strawman-risk/)**：本卡是 #140 的上位原則。#140 處理 Widen Options 段落的內容違規（兩弱一強稻草人）、本卡處理 WRAP 整套被當章節結構暴露的 surface 違規。兩卡互補—改 Widen Options 內容不夠、還要改 surface presentation。

- **[#125 Collapse 是隱形預設](../collapse-is-implicit-default/)**：本卡是 #125 在「寫作 process 透明度」surface 的具體 instance。Process metadata 暴露給讀者是「省去設計教學流程的便利選擇」的後果—不思考章節順序、直接把 WRAP 步驟當章節是最便利、但 collapse 掉了「為讀者設計閱讀順序」這個維度。

- **[#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)**：本卡是 #82 在「process metadata 暴露」維度的具體案例。lint 規則層 catch 不到「章節標題是 Anchor Check 還是『為什麼 X』」、要靠 reviewer / 讀者 feedback 才能發現—屬於 #82 的「行為精煉」維度。

- **[#97 Metadata surface 要納入寫作 review 範圍](../metadata-surface-in-writing-review/)**：本卡擴 #97 的 metadata surface 概念。#97 處理 title / description / heading 是讀者入口的 metadata；本卡指出 *章節結構本身* 也是 metadata surface—章節標題傳達「文章是什麼類型」、process 標題傳達「這是分析報告」、教學標題傳達「這是教學文章」。

- **[#126 寫作 review 是多軸完整性](../writing-review-multi-axis-completeness/)**：本卡是 review 設計時要看的「surface 軸」的具體 instance。Review 不能只看「內容是否正確」、要看「章節結構傳達的 register 是否跟目標讀者對齊」。

---

## 判讀徵兆

| 訊號                                                                 | 該做的事                                                                 |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 章節標題出現「Anchor Check / Step 0 / Widen Options / Reality Test」 | 改成教學標題、把 WRAP 內容融進教學段                                     |
| 開頭預設讀者已有某個敘事的認知（例如「X 是末端表象」）               | 把對該敘事的回應移到「事件本身」段、開頭只描述事件 + 帶到本篇主題        |
| 文章有「我們不討論 X」這類分析報告 disclaim                          | 刪、教學文章不需要預先排除某些議題、讀者沒問                             |
| 同一論點在開頭、Anchor Check、Step 0 各預告一次                      | 改成只在開頭預告一次、後續直接推進                                       |
| 章節順序嚴格按 WRAP 步驟                                             | 改成按教學流程：開頭 → 事件 → 為什麼 X → 結構性機制 → 長期 → 預警 → 框架 |
| 讀者反饋「文章像分析報告、不像教學」                                 | Register 漂移、check 是不是 WRAP process metadata 暴露                   |
| Reviewer 報告「文章預設讀者已有某種認知」                            | 開頭結構有問題、修法見本卡「開頭不對抗他人敘事、不預設讀者認知」段       |

---

## 適用範圍與邊界

- **適用範圍**：
  - 用 WRAP 框架寫商業 case-analyses、市場事件拆解、產業策略分析
  - 用其他「先列 process、再走 process」框架寫教學文章（5W1H、5-Forces 分步、JTBD 階段、case method 步驟）
  - 任何「寫作者內部 review tool」跟「讀者教學 narrative」混淆的情境
- **不適用**：
  - 給同行看的分析報告（analyst-to-analyst、process metadata 是正當的）
  - 學術論文（IMRaD 結構有正當性、process 標題是學術慣例）
  - 純技術 reference 文件（process metadata 反而幫助快速定位）
- **邊界**：本卡禁的是「把 WRAP 整套步驟當文章章節結構」、不是禁所有 process 詞彙。在合適的位置提一句「以下用 WRAP 框架背後的 hypothesis 探索方法拆」是 OK 的、整篇用 WRAP 步驟當章節就違規。判別線：章節標題是描述「讀者會學到什麼」（教學）還是「作者在做什麼分析步驟」（process）。
