---
title: "Key Management"
date: 2026-05-22
description: "說明加密金鑰如何產生、保存、輪替，以及還原時如何依賴金鑰"
weight: 338
---

Key Management 的核心概念是管理加密金鑰的完整生命週期 — 產生、保存、存取控制與輪替 — 並承擔「加密後的資料能否還原取決於金鑰是否健在」這個責任。它是 [At-Rest Encryption](/backend/knowledge-cards/at-rest-encryption/) 能否真正保護資料的前提，金鑰本身的保存要接回 [Secret Management](/backend/knowledge-cards/secret-management/)。

## 跟其他概念的關係

Key Management 位在加密機制的底層。[At-Rest Encryption](/backend/knowledge-cards/at-rest-encryption/) 與 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 都假設金鑰存在且可用；金鑰一旦遺失，加密資料就無法還原。它和 [Secret Management](/backend/knowledge-cards/secret-management/) 相鄰但責任不同：access secret（password、API key）外洩造成存取邊界失效，data-encryption key 遺失造成資料永久無法讀取。

## 可觀察訊號與例子

需要正視 key management 的訊號是系統用了 at-rest 加密、TLS 或 application-level 加密，卻沒有明確的金鑰 owner 與輪替排程。常見失敗是 restore 演練時才發現備份的 keyring 沒有一起保存，加密的 backup 變成無法還原的資料。雲端的 envelope encryption 與 customer-managed key 把金鑰階層攤開，讓輪替與撤銷可以分層進行。

## 判斷條件與後果

Data-encryption key 遺失時，用它加密的資料永久無法讀取，金鑰管理的每一項設定都從這個後果推出。金鑰沒有 owner 與輪替週期時，輪替與到期沒有人負責，金鑰過期或被刪除之後才被發現。金鑰沒有納入 restore 演練時，備份的 keyring 沒有一起保存的情形要到真正需要還原時才看得到，加密的 backup 變成無法還原的資料。沒有金鑰階層時，輪替或撤銷一把金鑰牽動它保護的全部資料；envelope encryption 把資料金鑰與包裝它的金鑰分開，輪替與撤銷可以分層進行。data-encryption key 與 access secret 放在一起保存與稽核時，兩種失效被混在一起處理：access secret 外洩造成存取邊界失效，要撤銷與替換；data-encryption key 遺失造成資料無法讀取，要確保它不遺失。金鑰可用性、最近輪替時間與即將到期的金鑰沒有被觀測時，以上幾種失效都要到出事時才看到。
