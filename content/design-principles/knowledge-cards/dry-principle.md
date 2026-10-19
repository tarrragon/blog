---
title: "DRY（Don't Repeat Yourself）"
date: 2026-10-19
description: "看到兩段長得一樣的程式碼想合併、或同一條規則改了一處而另一處忘了改時：DRY 管的是知識的重複，判斷兩段程式碼該不該合併要看它們是不是因為同一個理由改變"
weight: 5
tags: ["design-principles", "knowledge-card", "dry", "refactoring"]
---

DRY（Don't Repeat Yourself）出自 Andy Hunt 與 Dave Thomas 1999 年的《The Pragmatic Programmer》：「Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.」系統裡的每一份知識——一條業務規則、一個資料格式、一個設定值——只能有一個權威的表示。違反 DRY 的後果是 [Shotgun Surgery（散彈式修改）](/design-principles/knowledge-cards/shotgun-surgery/)：同一份知識的每一份複本都要找出來改，漏掉一處就不一致。

## 概念位置

DRY 管的對象是知識，不是程式碼的字面。2019 年的第二版特別說明，很多讀者把 DRY 讀成「不要複製貼上程式碼」，而 Hunt 與 Thomas 指的是知識與意圖的重複：同一件事寫在兩個地方，即使兩處的寫法完全不同（一段程式碼與描述它的文件、一份資料庫綱要與對應的資料結構），也是重複。

反方向也成立：兩段字面相同的程式碼，如果因為不同的理由改變，就不是同一份知識。[Single Responsibility Principle（單一職責原則）](/design-principles/knowledge-cards/single-responsibility-principle/)的判斷在這裡接手：兩段程式碼由不同的人、為不同的需求修改，現在相同只是碰巧，合併成一個共用函式之後，為其中一個需求做的修改會改到另一個需求依賴的行為，那個共用函式就成了 [Divergent Change（發散式變更）](/design-principles/knowledge-cards/divergent-change/)。Martin 在《Clean Architecture》的單一職責那一章把這種字面相同、理由不同的情形稱為 accidental duplication（意外的重複）。

## 可觀察訊號與例子

需要套用 DRY 的訊號，是同一份知識的變更要同時改好幾處：

- **同一條規則複製在好幾個檔案**：例如四個腳本各自寫了一份相同的 git 指令包裝函式，要改一個 git 指令選項就得改四次。四份都因同一個理由改變（呼叫 git 的方式），是同一份知識，所以抽成一個共用函式、四處改成呼叫它。Python 專案的做法與遷移順序在 [DRY 原則與共用程式庫](/python/07-refactoring/dry-principle/)。
- **同一個常數寫在好幾處**：例如逾時秒數同時寫在程式碼、設定檔與文件裡。保留一個權威來源（通常是程式執行時實際讀取的那一處，例如設定檔），程式碼讀它、文件連到它。
- **程式碼與文件描述同一件事**：文件抄了一份參數清單，程式碼改了而文件沒改。讓文件從程式碼產生，或文件只寫程式碼表達不了的部分。

判斷兩段相似的程式碼要不要合併時，Martin Fowler 在《Refactoring》引述 Don Roberts 的 Rule of Three：第一次照寫，第二次寫出相似的程式碼時先容忍重複，第三次才抽出共用的部分。Rule of Three 決定的是什麼時候判斷，要不要合併仍由下一節的判斷問句決定：等到有三份相似的程式碼，才累積得出足夠的修改紀錄，看得出它們是不是一起改。

## 設計責任

套用 DRY 的設計責任是讓每一份知識只有一個權威來源，而合併之前先確認那幾段程式碼是同一份知識。判斷問句是：這幾處過去的修改，是否每次都一起改、而且由同一個需求驅動；兩個條件都成立才是同一份知識，合併；任一個不成立，字面相同也分開保留。合併之後，函式裡開始需要一個參數來分支成兩套行為，代表那兩套行為各自由不同的理由改變，是合併錯了的訊號。
