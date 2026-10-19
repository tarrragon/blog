---
title: "Divergent Change（發散式變更）"
date: 2026-10-19
description: "同一個模組總是因為不相干的需求被修改、或並行開發的人一直在同一個檔案上等待彼此時：這是違反單一職責原則在修改紀錄上的樣子"
weight: 2
tags: ["design-principles", "knowledge-card", "code-smell", "refactoring"]
---

Divergent Change（發散式變更，其他中文資料常寫作「發散式變化」）是 Martin Fowler 在《Refactoring》列出的程式碼壞味道：一個模組因為不同的理由、以不同的方式反覆被修改。它是 [Single Responsibility Principle（單一職責原則）](/design-principles/knowledge-cards/single-responsibility-principle/) 被違反時在修改紀錄上留下的形態——模組有幾個改變的理由，就會被幾種不相干的需求輪流修改。與它方向相反的壞味道是 [Shotgun Surgery（散彈式修改）](/design-principles/knowledge-cards/shotgun-surgery/)。

## 概念位置

Divergent Change 與 Shotgun Surgery 描述的是同一組對應關係的兩種失衡：改變的理由與模組之間應該一對一。同一個理由的好幾個需求都改同一個模組是正常的[內聚](/design-principles/knowledge-cards/cohesion/)；屬於不同理由的需求改同一個模組是 Divergent Change，同一個理由的一個需求要改好幾個模組是 [Shotgun Surgery](/design-principles/knowledge-cards/shotgun-surgery/)。[單一職責原則](/design-principles/knowledge-cards/single-responsibility-principle/)的兩句指示各自對應一種：「把因不同理由改變的程式碼分開」修的是 Divergent Change，「把因同一個理由改變的程式碼放在一起」修的是 Shotgun Surgery。

## 可觀察訊號與例子

Fowler 給的辨識方式是：修改某個模組時，心裡想的是「加一種資料庫要改這三個函式，加一種金融商品要改那四個函式」——兩種變更各自集中在模組裡的幾個函式，卻共用同一個模組。可以觀察到的訊號有三種：

- **修改紀錄**：同一個檔案在一段時間內被好幾個不相干的需求修改。以需求編號統計每個檔案被幾個不同需求改過，再逐個 commit 歸類，做法在[從修改競爭判斷拆檔](/python/07-refactoring/file-split-by-contention/)。
- **並行開發的等待**：處理不相干需求的人反覆在同一個檔案上解合併衝突、或等對方合併之後重跑測試。
- **檔案內的分群**：模組裡的函式可以分成幾群，每一群只被某一類需求修改，群與群之間很少一起改。

站內偵測規則（以方法分組數判斷）與 Extract Class 的操作範例在 [Code Smell 檢查清單](/record/code_smell/)。

## 設計責任

修正 Divergent Change 的方向是依改變的理由把模組切開：先找出每一類需求各自會改的那一群函式與資料，再用 Extract Class（拆出類別）或把模組改成套件、每一群移到一個子模組。切開之前先用測試鎖住現有行為，切開之後確認同一類需求的變更只需要改一個新模組；若同一類需求要同時改好幾個新模組，代表切過頭，產生了 [Shotgun Surgery](/design-principles/knowledge-cards/shotgun-surgery/)。
