---
title: "CD Pipeline"
date: 2026-05-06
description: "說明持續交付如何把已驗證產物推進到目標環境"
tags: ["CD", "pipeline", "knowledge-card"]
weight: 2
aliases: ["/ci/knowledge-cards/cd-pipeline/"]
---

CD Pipeline 的核心概念是「把已驗證產物安全交付到目標環境」。它把 build、[artifact](/devops/ci/knowledge-cards/artifact/)、deploy 與 release gate 串成可重播流程。

## 跟其他概念的關係

CD Pipeline 位在 [CI](/devops/ci/knowledge-cards/ci-pipeline/) 驗證之後，負責 artifact promotion、部署執行、環境保護與回復路徑。

## 可觀察訊號

- 同一份 artifact 需要在多個環境推進。
- 發布步驟需要審核、權限或時間窗控制。
- 發布失敗時需要可回退或可修復路徑。

## 接近真實服務的例子

靜態站會在 CI 成功後上傳 artifact 到 hosting。後端服務會推進同一個 image tag 到 staging 與 production，並以 rollout strategy 控制風險。

## 判斷條件與後果

CD Pipeline 的放行條件、部署順序、例外流程與回復策略，各自決定一次發布在哪個位置停得下來。放行條件沒有明確定義時，artifact 是否進 production 只取決於有人按下部署；部署順序沒有固定時，production 可能先於 staging 拿到新版本，staging 的驗證結果來不及擋下問題；沒有例外流程時，緊急修復繞過整條 pipeline，那一次部署沒有審核紀錄；沒有回復策略時，發布失敗只能往前修，修復期間服務停在壞版本上。
