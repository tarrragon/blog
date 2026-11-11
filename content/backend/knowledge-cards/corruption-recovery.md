---
title: "Corruption Recovery"
date: 2026-05-22
description: "說明資料損毀事故如何先辨識來源、保全證據，再決定修復或還原"
weight: 347
---

Corruption Recovery 的核心概念是處理資料損毀事故時，先辨識損毀來自儲存層（檔案、磁碟、檔案系統）還是應用層（寫入了錯誤資料），保全證據，再決定修復或還原。它讓損毀事故有確定的處置順序，而不是直覺地直接修。它和 [Embedded Database](/backend/knowledge-cards/embedded-database/) 特別相關，因為這類系統的檔案責任落在 application。

## 跟其他概念的關係

Corruption Recovery 位在事故處理流程中、針對「資料本身壞了」這一類事故。它和一般 incident response 共用 [Evidence Package](/backend/knowledge-cards/evidence-package/)、[RCA](/backend/knowledge-cards/rca/) 的紀律，但多一個前置判斷：儲存層損毀與應用層寫錯的修法不同，前者要還原、後者要修資料也要修程式。

## 可觀察訊號與例子

需要 corruption recovery 流程的訊號是讀取時出現 checksum 錯誤、結構異常或資料明顯不合理。一個常見的處置錯誤是在疑似損毀的檔案上直接跑修復或 vacuum — 那可能把還能搶救的狀態也蓋掉。正確的第一步是先複製一份原始損毀檔案，保留它當證據與還原素材。

## 判斷條件與後果

損毀事故是否有確定的處置順序，取決於事前準備了哪幾項。沒有定義損毀的偵測訊號時，observability 把 checksum 錯誤與結構異常當成一般錯誤處理，損毀被發現的時間點往後延。沒有指定第一步的證據保全動作時，處理的人在疑似損毀的檔案上直接跑修復或 vacuum，還能搶救的狀態被蓋掉，判斷損毀來自儲存層還是應用層的證據也一起消失。沒有修復與還原的決策分支時，兩種損毀走同一種修法，而儲存層損毀要還原、應用層寫錯要修資料也要修程式。backup 與還原機制事前沒有驗證過時，還原這條分支到事故當下才發現走不通，剩下的做法只有直接修那份損毀的檔案。
