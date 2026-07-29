---
title: "Salt"
tags: ["密碼儲存", "Salt", "Security"]
date: 2026-07-29
description: "說明 salt 如何讓相同的密碼產生不同的雜湊值，以及它擋掉哪一類攻擊"
weight: 333
---

Salt 的核心概念是「在雜湊之前混入一段每筆紀錄各不相同的隨機值」。它讓兩個使用者即使設了相同的密碼，存下來的雜湊值也不一樣，因此它保護的是儲存於資料庫的 [credential](/backend/knowledge-cards/credential/) 在整份外洩之後的階段。

## 概念位置

Salt 與 [at-rest encryption](/backend/knowledge-cards/at-rest-encryption/) 服務的階段不同——後者讓資料在被取得時不可讀，salt 假設資料已經可讀、處理的是逐一破解的成本結構。它與 work factor 則是兩種互補的保護：work factor 決定猜一次要付多少代價，salt 決定攻擊者能不能一次猜完所有人。它不需要保密——salt 與雜湊值存在一起是標準做法，它的作用來自唯一性而非機密性。

## 可觀察訊號與例子

沒有 salt 時，同一個密碼在整份資料裡永遠對應同一個雜湊值，於是兩件事同時成立：攻擊者可以拿預先算好的對照表（rainbow table）直接反查，也可以掃出「哪些帳號用了同一個密碼」再從一個突破口推到其他帳號。加了 salt 之後這兩條路徑都要對每個帳號各算一次，攻擊成本因此隨帳號數量線性成長。

判斷一套系統有沒有 salt，看的是同一個密碼在不同帳號上存下來的值一不一樣。

## 設計責任

salt 由誰負責取決於用的是哪一層 API，而不是取決於演算法。**高階的密碼雜湊 API**（輸入密碼、輸出一串自描述字串）自己產生與管理 salt，並把它連同演算法識別與參數一起編碼進輸出，驗證時再讀回來——設計責任因此只剩下選對 API。**低階的金鑰衍生 API**（輸入密碼加 salt、輸出裸位元組）不管這件事：salt 要自己產生、儲存格式要自己設計，而參數也不會被寫進輸出，那些系統因此容易把參數寫死在程式碼裡。同一個演算法在同一個語言裡兩種形態都存在，Argon2 與 scrypt 尤其常見。

判別方法看回傳值：以 `$` 開頭的字串代表 salt 與參數已經被管理，回傳位元組陣列代表兩者都是呼叫端的責任。而自己拼接 salt 與密碼再送進一般用途的雜湊，是這一格最常見的實作錯誤——它兩層都不屬於。

Salt 保護不了弱密碼本身——它讓攻擊者無法一次攻擊全部帳號，單一帳號的破解成本仍然由 [work factor 與演算法選型](/backend/07-security-data-protection/password-storage-and-work-factor/) 決定。不可逆單向轉換在原語分類中的位置見 [7.28 密碼學原語選型](/backend/07-security-data-protection/cryptographic-primitive-selection/)。
