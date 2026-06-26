---
title: "多輪審查缺 outside-in 讀者 frame：六個系統性盲點"
date: 2026-06-26
weight: 194
description: "review 框架的所有 frame 從已寫的內容出發（inside-out），缺從讀者完整需求出發的 frame（outside-in）。六個盲點全部由使用者而非 reviewer 發現：宣導語氣、管理層資訊缺失、接手情境遺漏、工具指引缺失、深度不拆分、讀者定位未預設。"
tags: ["report", "事後檢討", "工程方法論", "原則", "寫作", "review-process"]
---

## 論述基礎與限制

本卡抽自 infra 教學模組的完整生產週期 retrospective。43 篇文章 + 21 張知識卡經歷三輪多輪審查（compliance / cadence+冷讀 / steelman+outbound），審查通過後使用者連續指出六個 review 未 catch 的問題，每個都導致大量修改。限制：evidence 來自單一教學模組的一次完整週期，盲點清單可能不窮盡。

## 核心原則

多輪審查框架的所有 frame 從「已寫的內容」出發（inside-out）：字句層看已寫的字、cadence 看已寫的結構、fact-check 看已寫的事實、steelman 看已寫的論述。缺的是從「讀者的完整需求」出發的 frame（outside-in）：讀者是誰、讀者從哪裡來、讀者讀完後要做什麼、讀者搜尋什麼問題。

inside-out 能保證已寫內容的品質，outside-in 才能發現「應該寫但沒寫」的缺口。兩者的盲區正交：inside-out 的盲區是缺口（看不到不存在的東西），outside-in 的盲區是細節（看不到已寫內容的字句問題）。完整的審查需要兩者交替。

## 六個盲點

### 一：宣導語氣通過三輪審查

三輪審查判定文章 clean，使用者指出「一台機器跑得好好的」「辦公大樓比喻」是對專業讀者的失配後，14 處需要重寫。

keyword bank 的設計對象是字面違規。宣導語氣的問題不在字面（每個字都合規）而在 register——用教導外行人的姿態對專業人士說話。reviewer 跟作者共享同一套文體直覺，都覺得「用故事帶入」是好的教學手法，同源盲區讓整批宣導語氣被合理化放行。

缺的 frame：**reader-persona register 適配**——指定具體讀者角色，問「這個人讀到這段會覺得被低估嗎」。

### 二：管理層彙報資訊缺失

所有 reviewer 檢查了技術正確性和寫作規範，沒有一個問「讀者讀完後能不能跟老闆說明為什麼要做、要花多久」。使用者提出後掃描出 10 處成本/時程缺口。

review frame 全部從「內容品質」出發，沒有從「讀者的下游任務」出發。技術文章的讀者不只要「學會怎麼做」，還要「能向上彙報為什麼做」——後者是讀者的工作流程，品質導向的 review 結構性看不到。

缺的 frame：**downstream-task 審查**——問「讀者讀完後的下一個動作是什麼？他需要什麼素材？」

### 三：接手 vs 自建是不同情境

模組負一定位為「還沒有 infra 的手動環境」，所有 reviewer 都接受了這個前提。使用者指出「接手前人的專案」是完全不同的操作情境後，獨立成一個橫切模組。

review 的 scope 是「已寫的內容對不對」，不質疑結構本身的覆蓋範圍。steelman reviewer 問的是已有文章的論述有沒有漏洞，不是教材的讀者群有沒有被遺漏的情境。

缺的 frame：**persona-coverage 審查**——列出目標讀者可能進入教材的情境，檢查每個情境是否有對應入口。

### 四：操作步驟缺工具指引

文章寫「拍下現況」「匯出資料庫」，reviewer 確認了邏輯正確性。使用者問「用什麼拍？怎麼拍？」後才發現停在 WHAT 層、沒到 HOW WITH WHAT 層。

fact-check reviewer 驗證「描述是否正確」，不是「描述是否可執行」。「用 FTP 下載整站存進 Git」事實正確，但讀者照做時需要知道用哪個 FTP client、大檔案怎麼處理。

缺的 frame：**executable-walkthrough 審查**——假裝讀者從零照做，每步問「下一個動作是打開什麼軟體、輸入什麼指令」。

### 五：概覽級深度不拆分

350 行文章涵蓋四個面向，reviewer 認為「結構完整」。使用者指出「資料庫備份和安全管理其實都是大問題」後拆成 5 篇。後續又在 8 個模組發生同樣的拆分。

reviewer 評估「這篇文章本身好不好」，不是「搜尋特定問題的讀者能不能找到足夠深度的內容」。一篇涵蓋四面向的文章通讀體驗良好，但搜尋「共享主機 MySQL 備份」的讀者需要專題文章。

缺的 frame：**search-landing 審查**——列出讀者可能搜尋的具體問題，檢查每個問題能不能落在聚焦的文章上。跟 cold-read (B') 相關但不同——B' 看「落地後讀不讀得懂」，這裡看「能不能落地到足夠聚焦的內容」。

### 六：讀者定位未預設

「讀者是缺經驗的專業人士」這個原則在文章寫完、審查完、使用者反饋後才抽出來。它影響了語氣、比喻策略、管理層溝通——幾乎所有後續大修都源自這個原則。但它不在任何 reviewer prompt 裡。

寫作規範定義了「怎麼寫」的規則，沒有定義「寫給誰」——讀者定位被當成隱性決定。LLM 預設用「教外行人」的姿態寫教學內容，這個預設不被 review 挑戰，因為 reviewer 也共享同一個預設。

這不是 review frame 的問題——是**生成端的前提缺失**。每個教學模組在第一篇文章生成前就應該顯式聲明讀者定位。

## 理想做法

在現有 inside-out review 框架之外，補五個 outside-in frame：

| Frame                     | 問什麼                             | 在哪個 Round 跑           |
| ------------------------- | ---------------------------------- | ------------------------- |
| Reader persona + register | 讀者讀到這段會覺得被低估嗎？       | Round 2（讀者旅程）       |
| Downstream task           | 讀者讀完後要做什麼、需要什麼素材？ | Round 1（基線 audit）     |
| Persona coverage          | 所有讀者情境都有入口嗎？           | Round 3（outbound）       |
| Executable walkthrough    | 讀者能從零照做嗎？每步的工具在嗎？ | Round 2（操作型文章專用） |
| Search landing            | 搜尋特定問題能落在聚焦文章嗎？     | Round 3（outbound）       |

生成端的修正：每個教學模組在撰寫前顯式聲明「讀者定位文件」（一段話描述目標讀者的背景、已有能力、缺的經驗），讓生成和 review 都有可檢查的基準。

## 沒這樣做的麻煩

六個盲點的修法總工程量遠超預防成本：14 處宣導語氣重寫 + 10 處管理層資訊補充 + 11 篇接手維運新文章 + 全模組工具補充 + 12 篇子文章拆分 + 3 篇入門/溝通層重寫。如果讀者定位在第一篇文章前就聲明、outside-in frame 在 Round 1 就跑，多數修改可以在初稿階段就避免。

## 判讀徵兆

review 完成後如果使用者的第一個反饋是關於「內容缺口」而非「內容品質」，代表 review 框架偏向 inside-out。inside-out 的 review 報告 clean 只代表「已寫的內容沒問題」，不代表「該寫的都寫了」。

## 跟其他抽象層原則的關係

- → [讀者是缺經驗的專業人士、不是外行人](/report/audience-is-professional-not-layperson/)：盲點一和六的直接修法
- → [技術教材要內嵌管理層可彙報的資訊](/report/technical-content-needs-management-reportable-info/)：盲點二的直接修法
- → [跨專業溝通用情境遞進、不用比喻堆疊](/report/cross-expertise-communication-scenario-not-analogy/)：盲點一的溝通層修法
- → [#148 跨輪 review 停止訊號](/report/cross-round-review-stopping-signal/)：本卡揭露的是「停止訊號齊備但覆蓋不完整」的情境——frame 涵蓋度的判斷要包含 outside-in frame
- → [#153 Review 漏抓先分 design gap 與 execution gap](/report/review-miss-diagnose-design-vs-execution-gap/)：六個盲點全部是 design gap（框架缺 frame），不是 execution gap（有 frame 沒跑）
- → [#168 多輪審查要有冷讀者 frame](/report/cold-reader-frame-vs-informed-reviewer/)：cold-read 是 outside-in 的一個實例（從零脈絡讀者出發），本卡把這個方向擴展到五個 frame
