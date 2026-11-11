---
title: "At-Rest Encryption"
date: 2026-05-22
description: "說明資料落到儲存媒介前的加密層，以及它對應的威脅模型"
weight: 333
---

At-Rest Encryption 的核心概念是資料寫入磁碟前先加密，保護 tablespace、log、backup 等落地資料。它對應的威脅是儲存媒介遺失或被竊 — 磁碟、快照或 backup 檔落到他人手上時，加密讓資料仍受保護。它和保護傳輸中資料的 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 解的是不同威脅，兩者互補；金鑰的保存與輪替要接回 [Secret Management](/backend/knowledge-cards/secret-management/)。

## 跟其他概念的關係

At-Rest Encryption 位在儲存層，與傳輸層的 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 形成對稱的一組保護。in-transit 加密保護資料在網路上移動的階段，at-rest 加密保護資料靜止在儲存媒介的階段；一條完整的保護鏈兩者都要有。它和 [Data Classification](/backend/knowledge-cards/data-classification/) 連動 — 資料分級決定哪些資料必須做 at-rest 加密。

## 可觀察訊號與例子

需要 at-rest encryption 的訊號是儲存 [PII](/backend/knowledge-cards/pii/)、金流或受監管資料，或合規要求磁碟與 backup 加密。常見的保護鏈破洞是主資料庫加了密，但 backup 以明文落到 object storage — 攻擊者取得 backup 就繞過了所有加密。設計時要把 backup、replica 與暫存檔都納入加密範圍。

## 判斷條件與後果

加密範圍只涵蓋主資料庫、沒有涵蓋 backup、replica 與暫存檔時，攻擊者取得任何一份明文副本，就繞過了主資料庫的加密。加密之後資料是否能還原取決於金鑰是否健在：金鑰遺失時 backup 再完整也解不開，只演練資料檔的 restore 要到真正需要還原時才發現金鑰不在，所以 restore 演練連金鑰一起測。金鑰與存取用的 credential 失敗的代價不同，金鑰遺失等於資料無法還原，credential 外洩等於存取邊界失效，所以金鑰有自己的 owner 與輪替排程，和 credential 分開管理。加密設定與金鑰可用性沒有進 observability 時，某個儲存位置的加密被關閉或金鑰被停用，要到還原失敗才看得到。
