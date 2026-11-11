---
title: "Incident Severity"
tags: ["事故等級", "Incident Severity"]
date: 2026-04-23
description: "說明事故分級如何把產品影響轉成對應處置節奏"
weight: 151
---

Incident severity 的核心概念是「用一致標準把事故影響分級」。分級描述的是產品影響範圍、持續時間、資料風險與回復緊急程度，技術細節放在其他層處理。 可先對照 [Alert](/backend/knowledge-cards/alert/)。

## 跟其他概念的關係

Incident severity 連接 [alert](/backend/knowledge-cards/alert/)、[runbook](/backend/knowledge-cards/runbook/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/)。同一類技術錯誤在不同業務場景可能有不同等級，因此分級要以產品後果為主。

影響固定、有替代做法的問題列進已知錯誤清單，由客服照清單上的替代做法答覆，不開事故，見 [Known Error（已知錯誤）](/backend/knowledge-cards/known-error/)。

## 可觀察訊號與例子

系統需要分級模型的訊號是事件發生後團隊對嚴重度判斷不一致。付款成功率下降與單一內部報表延遲都可能由 timeout 引起，但前者需要立即啟動高優先級處置，後者通常走一般排程修復。

## 判斷條件與後果

等級條件以產品後果（影響範圍、持續時間、資料風險）寫成時，付款成功率下降與內部報表延遲即使同樣由 timeout 引起，也判得出不同的等級；條件寫成技術症狀時，同一個事件被不同的人判成不同等級，啟動的處置也跟著不同。升級門檻沒有定義時，影響擴大的事故停在原本的等級，該加入的角色與通訊頻率都沒有跟著提高。每一級寫明負責角色、通訊頻率與回顧要求時，宣告等級的同時就決定了誰到場、多久更新一次、事後是否做 post-incident review。產品與流量改變之後，等級條件若長期沒有和事故紀錄對照，條件描述的是舊的產品，判出的等級跟實際後果脫節。
