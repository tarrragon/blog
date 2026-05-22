---
title: "Corruption Recovery"
date: 2026-05-22
description: "說明資料損毀事故如何先辨識來源、保全證據，再決定修復或還原"
weight: 346
---

Corruption Recovery 的核心概念是處理資料損毀事故時，先辨識損毀來自儲存層（檔案、磁碟、檔案系統）還是應用層（寫入了錯誤資料），保全證據，再決定修復或還原。它讓損毀事故有確定的處置順序，而不是直覺地直接修。它和 [Embedded Database](/backend/knowledge-cards/embedded-database/) 特別相關，因為這類系統的檔案責任落在 application。

## 概念位置

Corruption Recovery 位在事故處理流程中、針對「資料本身壞了」這一類事故。它和一般 incident response 共用 [Evidence Package](/backend/knowledge-cards/evidence-package/)、[RCA](/backend/knowledge-cards/rca/) 的紀律，但多一個前置判斷：儲存層損毀與應用層寫錯的修法不同，前者要還原、後者要修資料也要修程式。

## 可觀察訊號與例子

需要 corruption recovery 流程的訊號是讀取時出現 checksum 錯誤、結構異常或資料明顯不合理。一個常見的處置錯誤是在疑似損毀的檔案上直接跑修復或 vacuum — 那可能把還能搶救的狀態也蓋掉。正確的第一步是先複製一份原始損毀檔案，保留它當證據與還原素材。

## 設計責任

設計時要定義損毀的偵測訊號、第一步的證據保全動作，以及修復與還原的決策分支。要事先確認 backup 與還原機制本身可用，否則損毀事故發生時沒有退路。observability 要能盡早偵測 corruption 訊號，把它和一般錯誤分開。
