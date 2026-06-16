---
title: "Fencing Token"
date: 2026-06-16
description: "說明用單調遞增的 token 讓下游拒絕過期持鎖者的寫入，把互斥正確性下沉到資料層"
weight: 383
---

Fencing token 的核心概念是「每次取鎖發一個單調遞增的編號，持鎖者對下游的每個寫入都帶上它，下游記住見過的最大編號並拒絕比它小的寫入」。它把互斥的正確性從鎖本身下沉到擁有正式狀態的那一層。 可先對照 [Distributed Lock](/backend/knowledge-cards/distributed-lock/)。

## 概念位置

Fencing token 是 [distributed lock](/backend/knowledge-cards/distributed-lock/) 在「鎖可能因 GC 暫停、網路分割而失效」這個固有時序窗口下的補強機制。鎖只負責減少競爭，fencing token 讓下游成為最終仲裁者，與 [idempotency](/backend/knowledge-cards/idempotency/) 同屬「即使協調層失效，結果仍正確」的防線。 可先對照 [Distributed Lock](/backend/knowledge-cards/distributed-lock/)。

## 可觀察訊號與例子

需要 fencing token 的訊號是「鎖牽涉正確性、雙寫會造成金錢或資料損壞」。節點 A 取得鎖後發生長 GC 暫停、租約到期被 B 接手，A 醒來仍以為持鎖而寫入：A 帶 token 33、B 帶 token 34，下游接受過 34 後就拒絕 33。ZooKeeper 的 zxid、etcd 的 revision、資料庫的版本欄位都可以充當 fencing token。

## 設計責任

設計時要確認下游有能力驗證 token（記住最大值並拒絕較小者）。下游若無法條件寫入（例如第三方 API），fencing token 無法成立，這時要把互斥下沉到資料層的唯一約束或條件更新。token 的生成要保證取鎖動作本身嚴格遞增，用原子計數器或鎖服務序號實作。
