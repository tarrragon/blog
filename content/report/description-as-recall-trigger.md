---
title: "Description 是未來自己的 recall trigger、不是文章摘要"
date: 2026-06-29
weight: 170
description: "文章的 description 欄位要讓未來的自己在掃列表時判斷「我現在遇到的問題，該不該回來讀這篇」——像 skill 的 description 讓系統決定何時載入一樣。摘要式 description 只回答「這篇在講什麼」，recall trigger 回答「你在什麼情境下需要這篇」。"
tags: ["report", "事後檢討", "工程方法論", "原則", "寫作"]
slug: "description-as-recall-trigger"
---

## 論述基礎與限制

本卡抽自一次三篇 macOS 系統管理文章的多輪審查。審查修完 32 項 finding 後，作者發現 description 雖符合格式規範（30-150 字、非空），語意卻只是摘要——未來回顧列表時無法判斷「何時該重讀」。限制：單一案例（操作型文章），其他類型（教學模組、report 卡、知識卡）的 description 可能有不同的 recall 結構。

## 核心原則

文章的 `description` 欄位是寫給**未來自己**的 recall trigger，不是寫給搜尋引擎的摘要。它要回答的問題是：「我在什麼情境下、遇到什麼問題，會需要回來讀這篇？」

類比：Claude Code skill 的 `description` 讓系統在對話中自動判斷「要不要載入這個 skill」。文章的 description 讓未來的自己在掃列表時自動判斷「要不要進去讀」。兩者目的相同——降低 recall 的認知成本。

摘要式 description 只回答「這篇**在講什麼**」（內容索引）；recall trigger 回答「**你在什麼情境下需要這篇**」（情境索引）。前者是被動的——搜尋命中後才看；後者是主動的——掃列表就能決定。

## 情境

三篇 macOS 文章（新機設定 / 磁碟診斷 / App 佔用報告）的 description 寫法：

- 原本：「從一台 30G 餘裕在幾小時內歸零的 Mac，記錄一套先看快照、再用實際佔用排查的磁碟診斷順序……」
- 問題：這是**內容摘要**——讀者已經知道要找「磁碟診斷」才會搜到它，description 只重述他已預期的內容，沒有增量資訊。
- 理想：description 應該告訴未來的自己「你什麼時候會需要回來」——例如「磁碟莫名滿載時的排查起手順序、避開 sparse 假大小陷阱、以及用 tmutil 判讀快照是否為元兇的方法」。

## 理想做法

description 撰寫時問自己三個問題：

1. **我未來會在什麼情境下需要這篇？**（觸發條件）
2. **這篇給我的關鍵判讀 / 操作是什麼？**（帶走的能力）
3. **不讀這篇我會踩什麼坑？**（省下的試錯）

三者至少涵蓋一個。格式不重要，重要的是 description 讀完後能判斷「現在要不要進去」。

反例——以下句型通常是摘要不是 trigger：

- 「記錄了 X 的過程」（日記式）
- 「介紹 X 的做法」（教科書式）
- 「從 X 事件整理出 Y」（報告式）

這些句型把 description 當後設描述（meta-description of the article），而不是情境描述（description of when you need it）。

## 沒這樣做的麻煩

- 列表頁的 description 變成一片「記錄了…」「整理出…」的重複句型，掃不出差異，每篇都要點進去才知道需不需要
- 日後同類情境再發生時，想不起來自己寫過、重新搜或重新踩坑
- blog 的知識累積效益被 recall 成本吃掉——寫了等於沒寫

## 判讀徵兆

- description 的主詞是「本文 / 這篇 / 記錄」→ 可能是摘要不是 trigger
- description 刪掉後，只看 title 就能猜出 description 的全部內容 → 沒有增量
- 掃列表時無法在 3 秒內判斷「這篇跟我現在的問題有沒有關」→ trigger 失敗

## 跟其他原則的關係

- [#169 原子筆記要有向上的議題入口](../atomic-note-needs-situational-entry/)：同根因——讀者（含未來的自己）需要「情境入口」而非「定義入口」。#169 談卡片正文的進入動機，本卡談 frontmatter description 的進入動機，是同一原則在不同 surface 的體現。
- [#131 教材完整性要用讀者旅程驗證](../teaching-completeness-by-learner-journey/)：讀者旅程的第一站是列表頁的 description——旅程驗證如果從「已進入文章」開始，就跳過了「要不要進入」的判斷點。
- [#159 入口分流要放在詞彙牆之前](../audience-fork-before-jargon-wall/)：description 是文章的入口分流欄位，分流依據應是讀者的情境而非文章的內容結構。

---
