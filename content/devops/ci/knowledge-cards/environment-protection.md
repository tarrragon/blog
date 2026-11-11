---
title: "Environment Protection"
date: 2026-05-06
description: "說明目標環境的審核、權限與放行條件如何保護發布"
tags: ["CD", "environment", "knowledge-card"]
weight: 5
aliases: ["/ci/knowledge-cards/environment-protection/"]
---

Environment Protection 的核心概念是「用環境層 gate 控制正式發布」。它把環境風險從 workflow 腳本外顯成可檢查規則，與 [Readiness / Health Check](/devops/ci/knowledge-cards/readiness-health-check/) 共同構成部署放行條件。

## 跟其他概念的關係

Environment Protection 位在部署 job 與目標環境之間，包含 reviewer、wait timer、[branch policy](/devops/ci/knowledge-cards/branch-protection/) 與 secret scope。

## 可觀察訊號

- 測試綠燈後仍需要人工批准才能進 production。
- 不同環境需要不同發布權限與審核規則。
- 發布失誤常來自權限配置或保護規則缺失。

## 接近真實服務的例子

GitHub Actions deploy job 指向 `production` environment，需指定 reviewer 批准後才可部署。staging 則採自動放行。

## 判斷條件與後果

Environment Protection 的規則依環境的風險分層時，staging 自動放行，production 等指定的 reviewer 批准，原因是兩個環境出錯的影響範圍不同：staging 壞掉影響內部驗證，production 壞掉影響使用者。所有環境套同一組規則時，結果是兩種之一：staging 也被人工審核拖慢，或 production 跟 staging 一樣自動放行，測試綠燈之後沒有任何關卡擋住高風險發布。審核責任沒有指定到人時，批准請求停在沒人處理的狀態，發布卡在 gate 前面；沒有例外流程時，緊急修復同樣要走完整的審核與 wait timer，修復上線的時間被拉長。
