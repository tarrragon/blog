---
title: "Threat Model"
tags: ["backend", "knowledge-card", "security", "threat-model"]
date: 2026-08-17
description: "說明系統如何被攤成資產、邊界與攻擊者能力，讓風險的位置可以逐項列舉"
weight: 439
---

Threat model 的核心概念是「把系統攤成資產、邊界與攻擊者能力，讓風險的位置可以逐項列舉，而不是靠印象判斷哪裡危險」。它是列舉框架，產出的是一張「哪個資產在哪條邊界上、面對什麼能力的攻擊者」的對照，具體的濫用情境由 [abuse case](/backend/knowledge-cards/abuse-case/) 承接。 可先對照 [Trust Boundary](/backend/knowledge-cards/trust-boundary/)。

## 概念位置

Threat model 位在 [attack surface](/backend/knowledge-cards/attack-surface/)、[trust boundary](/backend/knowledge-cards/trust-boundary/) 與 [abuse case](/backend/knowledge-cards/abuse-case/) 之間，三者的分工是問題不同：attack surface 問「哪裡先被看見」，trust boundary 問「哪裡開始不能沿用前一段的驗證」，threat model 問「誰會來、想拿什麼、能做到什麼程度」。列舉的結果會分配到 [authentication](/backend/knowledge-cards/authentication/)、[authorization](/backend/knowledge-cards/authorization/)、[data classification](/backend/knowledge-cards/data-classification/) 與 [defense in depth](/backend/knowledge-cards/defense-in-depth/) 各自承接。

常見的操作形式是先畫資料流（誰把資料交給誰、跨過哪些邊界），再對每個跨界點套一組固定的失效分類。公開的分類法（STRIDE 這一類）提供的是列舉的完整性，不是風險的排序——排序要靠資產價值與攻擊者能力假設。

## 可觀察訊號與例子

系統需要 threat model 的訊號是控制的取捨開始出現分歧而沒有共同的比較基準：兩個團隊對同一個端點該不該加驗證各有理由，而爭論停在「感覺不安全」與「還沒出過事」之間。另一個訊號是資產與邊界跨得多——多租戶、第三方整合、離線客戶端、代理操作——這時風險的位置無法靠單點檢查覆蓋。

一個實際的形態是端對端加密的設計討論：模型要先寫下攻擊者是誰（拿到伺服器儲存的人、拿到傳輸中的人、拿到客戶端裝置的人），三個假設對應的金鑰位置完全不同，而在假設寫下來之前，任何原語選擇都無法被驗證是否對準風險。這條推導在 [7.28 密碼學原語選型](/backend/07-security-data-protection/cryptographic-primitive-selection/) 展開。

## 設計責任

Threat model 要交出資產清單、邊界清單、攻擊者能力假設，以及每個假設對應的控制意圖。它的責任是讓風險的位置可列舉、可複查、可在條件變化時重跑；模型本身不提供保證，同一份模型在攻擊者能力假設更新之後就要重新走一次。模型的產出接 [7.21 資安如何成為服務設計輸入](/backend/07-security-data-protection/security-as-service-design-input/) 的設計輸入欄位，濫用情境的細節交給 [abuse case](/backend/knowledge-cards/abuse-case/)。
