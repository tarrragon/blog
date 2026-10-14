---
title: "Tiered Support（分層支援）"
date: 2026-10-14
description: "要決定使用者回報由誰處理、什麼時候往上轉，或客服一再把同一類問題轉給工程時，查分層支援怎麼切分各層、決定一則回報停在哪一層的因素，以及它與值班升級策略的差別"
weight: 482
tags: ["backend", "incident-response", "customer-support"]
---

Tiered support（分層支援）是把處理使用者回報的人分成幾層的組織方式：一線客服（Tier 1）接所有回報，能以既有資訊答覆的當場答覆；技術支援（Tier 2）處理需要讀系統資料的回報；工程（Tier 3）處理需要查 log、改程式的回報。小團隊多半只有兩層，客服直接轉給工程。一線客服答覆時用的資訊之一是 [Known Error（已知錯誤）](/backend/knowledge-cards/known-error/) 清單，各層之間累積答案的方法見 [Knowledge-Centered Service（KCS）](/backend/knowledge-cards/knowledge-centered-service/)。

## 概念位置

分層支援處理的是使用者回報，[Escalation Policy](/backend/knowledge-cards/escalation-policy/) 處理的是告警與事故：分層支援決定一則回報由哪一層的人回覆，升級策略決定一個沒有回應或沒有進展的事故轉給下一個值班的人。兩者在一個地方交會：客服判斷一則回報要立即呼叫值班時，它就從分層支援進入事故流程，由值班通知系統與升級策略接手。

分層之外另有一種做法叫 swarming（Consortium for Service Innovation 稱為 Intelligent Swarming）：回報不逐層轉，而是由能處理它的人直接協作處理。它省掉逐層轉手的等待，代價是每一則回報都要找到合適的人，適合問題種類多、單一層的資訊不夠用的組織。

## 可觀察訊號與例子

一則回報停在哪一層，由那一層手上的資訊與工具決定。短網址服務的客服手上有查詢工具，查得到短碼存在、過期或被停用，「短網址打不開」多數在一線就能答覆；客服手上沒有這個工具，同一類回報就一路轉到工程。分層運作不良的訊號是同一類回報反覆轉到上一層、而上一層每次查的都是下一層本來查得到的資料。

## 判讀方式

看到回報大量往上轉時，先問上一層這次用了什麼資訊才答出來，再問這份資訊能不能交到下一層手上：能的話補成下一層的工具或知識文章，不能的話（需要改程式、需要讀含個人資料的 log）才是該轉的回報。客服與工程之間的完整流程見 [8.24 客服回報的處理](/backend/08-incident-response/support-escalation-and-engineering-reply/)。
