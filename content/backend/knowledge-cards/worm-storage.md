---
title: "WORM Storage（不可變儲存）"
date: 2026-10-14
description: "要讓備份或稽核紀錄在寫入它的憑證外洩之後仍然刪不掉、改不了時，查一次寫入多次讀取的儲存怎麼做到、物件鎖定的兩種模式差在哪裡，以及版本保留與它的差別"
weight: 479
tags: ["backend", "security", "backup", "audit"]
---

WORM（write once, read many）儲存是寫入之後在保留期間內不能被修改、也不能被刪除的儲存：資料可以一再讀取，而任何人（包括持有完整權限的帳號）都改不了已經寫入的內容。它要防的是持有寫入權限的那一方本身被入侵或作惡：一般的權限控制擋得住沒有權限的人，擋不住拿到權限的攻擊者，而 WORM 讓「刪除」與「覆寫」在保留期間內不存在。用在備份上時常被稱為不可變備份（immutable backup）。它與 [Audit Log](/backend/knowledge-cards/audit-log/) 的完整性要求、以及 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的異地備份段直接相關。部署的 [Immutable Image](/backend/knowledge-cards/immutable-image/) 是另一件事：那是部署產物建好之後不在原地修改，與儲存能不能被刪無關。

## 概念位置

WORM 是防「寫入[憑證](/backend/knowledge-cards/credential/)外洩」的最後一層。前面幾層各有它擋不住的情形：只給寫入權限的憑證，在物件儲存裡通常仍能以同名上傳覆寫既有的物件；版本保留（versioning）讓覆寫與刪除只產生新版本，而持有完整權限的帳號能把舊版本一起刪掉，舊版本到期的生命週期規則也會在設定的天數之後自動刪掉它們。WORM 把保留變成儲存本身的性質，不再依賴誰持有什麼權限。代價是保留期間內任何人都刪不掉：寫錯的資料、攻擊者灌進來的垃圾，都會佔用空間並計費到保留期滿。

## 可觀察訊號與例子

S3 的物件鎖定（Object Lock）有兩種模式。compliance 模式在保留期間內連帳號的 root 都刪不掉、也縮短不了保留期間；governance 模式下，持有繞過權限（`s3:BypassGovernanceRetention`）的帳號仍刪得掉（[S3 Object Lock 文件](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)）。所以只開 governance 模式的備份，對「那把有繞過權限的金鑰外洩」這種情形不構成 WORM。其他業者與自架工具有各自的等價物，例如 restic 的備份伺服器 rest-server 的 `--append-only` 模式只接受新增、拒絕刪除與修改；它的保證由那一台伺服器提供，那台伺服器本身的權限與可達範圍要另外評估。

## 判讀方式

判斷一份資料是否不可變，問一句：持有寫入它的憑證的人、以及持有那個儲存帳號完整權限的人，在保留期間內能不能讓它消失或改變。答案要逐項查：覆寫同名物件、刪除舊版本、縮短保留期間、關閉鎖定、刪除整個 bucket 或帳號。保留期間要長過從入侵發生到被發現所需的時間，否則攻擊者等保留期滿再刪。WORM 擋的是刪除與修改，擋不了寫入：被入侵的來源仍可以寫入被竄改或已加密的新資料，所以舊的版本要保留多份，還原前要驗證。
