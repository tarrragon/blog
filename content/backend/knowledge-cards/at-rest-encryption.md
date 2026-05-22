---
title: "At-Rest Encryption"
date: 2026-05-22
description: "說明資料落到儲存媒介前的加密層，以及它對應的威脅模型"
weight: 332
---

At-Rest Encryption 的核心概念是資料寫入磁碟前先加密，保護 tablespace、log、backup 等落地資料。它對應的威脅是儲存媒介遺失或被竊 — 磁碟、快照或 backup 檔落到他人手上時，加密讓資料仍受保護。它和保護傳輸中資料的 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 解的是不同威脅，兩者互補；金鑰的保存與輪替要接回 [Secret Management](/backend/knowledge-cards/secret-management/)。

## 概念位置

At-Rest Encryption 位在儲存層，與傳輸層的 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 形成對稱的一組保護。in-transit 加密保護資料在網路上移動的階段，at-rest 加密保護資料靜止在儲存媒介的階段；一條完整的保護鏈兩者都要有。它和 [Data Classification](/backend/knowledge-cards/data-classification/) 連動 — 資料分級決定哪些資料必須做 at-rest 加密。

## 可觀察訊號與例子

需要 at-rest encryption 的訊號是儲存 [PII](/backend/knowledge-cards/pii/)、金流或受監管資料，或合規要求磁碟與 backup 加密。常見的保護鏈破洞是主資料庫加了密，但 backup 以明文落到 object storage — 攻擊者取得 backup 就繞過了所有加密。設計時要把 backup、replica 與暫存檔都納入加密範圍。

## 設計責任

設計時要決定加密範圍、金鑰管理方式與金鑰輪替策略。加密後資料能否還原取決於金鑰是否健在，因此 restore 演練要連金鑰一起測。金鑰要有 owner 與輪替排程，並和存取用的 credential 分開管理 — 兩者失敗代價不同：金鑰遺失等於資料無法還原，credential 外洩等於存取邊界失效。observability 要能確認加密設定狀態與金鑰可用性。
