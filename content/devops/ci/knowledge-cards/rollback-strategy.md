---
title: "Release Rollback（發布物回滾）"
date: 2026-05-06
description: "設計部署流程時，要決定靜態站、後端服務與 App 各自怎麼撤回前一版、哪些步驟要跟回滾一起做"
tags: ["CD", "rollback", "發布物回滾", "knowledge-card"]
weight: 8
aliases: ["/ci/knowledge-cards/rollback-strategy/"]
---

Release Rollback 在部署流程裡指的是把每一種發布物（靜態站的 artifact、後端服務的 image、App 的版本與遠端設定）撤回前一版的做法，以及回滾時要一起做的步驟，是新版本推出的方式（[Rollout Strategy](/devops/ci/knowledge-cards/rollout-strategy/)）失敗時的對應動作，要在發布之前設計好。這張卡的回滾指部署回滾（deployment rollback）：把已上線的發布物撤回前一版；資料庫撤銷交易裡變更的 `ROLLBACK` 是交易回滾（transaction rollback），是另一件事，寫在 backend 的 [Transaction（交易）](/backend/knowledge-cards/transaction/) 卡。事故當下判斷要不要回滾（回滾能不能比其他做法更快降低影響、新舊版本的資料相容、停止條件與回滾後的驗證）寫在 backend 的 [Rollback Strategy（回滾策略）](/backend/knowledge-cards/rollback-strategy/) 卡，本卡寫判斷成立之後，部署流程拿什麼撤回；兩張卡講的是同一件部署回滾的兩個面向，名稱分開是為了讓連結文字指得出是哪一張。

## 跟其他概念的關係

Release Rollback 位在 deploy、rollout 與 incident handling 之間：回滾的手段取決於 [Rollout Strategy](/devops/ci/knowledge-cards/rollout-strategy/) 用什麼方式把新版推出去，後端服務的回滾要跟資料遷移（[Migration](/devops/ci/knowledge-cards/migration/)）的順序一起排，App 的回滾要靠 feature flag 或 remote config。要不要回滾的判斷見 backend 的 [Rollback Strategy（回滾策略）](/backend/knowledge-cards/rollback-strategy/)，回滾步驟在發布前的演練（[Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/)）是另一張卡。

## 可觀察訊號

- 部署流程只有往前推的步驟，沒有一個步驟能把上一版的發布物重新部署回去。
- 上一版的 artifact 或 image 沒有保留，或沒有標上能找回的版本號。
- 後端的 migration 跟應用程式在同一個步驟執行，回滾 image 時 migration 沒有對應的處理。

## 接近真實服務的例子

靜態站可回滾到前一版 artifact。後端服務可回滾 image tag 並暫停新 migration。App 場域可先用 remote config 關閉新功能，再走 hotfix 發版；remote config 的生效時間取決於 App 多久重新讀一次設定（Firebase 預設 12 小時），各種回滾手段對已安裝版本的作用見 [11.15 自家行動 App 與後端的 API 契約：版本回報、最低支援版本、商店審核下的上線順序、分階段發布、熱更新與回退手段](/backend/11-api-design/mobile-client-api-contract/)。

## 判斷條件與後果

回滾的手段依發布物的形態而不同。靜態站的發布物是一組檔案，保留了前一版 artifact 時，重新部署那一版就完成回滾；沒有保留時，要從原始碼重新建置前一版，建置的時間加進錯誤持續的時間。後端服務回滾 image 時，新版本附帶的 migration 已經改過 schema，舊版本的程式要讀得懂改過的 schema 才能回滾，所以新的 migration 要一併暫停，schema 的變更拆成先加新結構、舊版程式不再使用之後才刪舊結構的兩次發布（[Expand / Contract](/backend/knowledge-cards/expand-contract/)）；migration 跟應用程式綁在同一個部署步驟時，回滾 image 不會撤回 schema。App 已經安裝在使用者裝置上的版本收不回，部署流程能撤回的只有後端與 remote config：用 remote config 關掉新功能，生效時間取決於 App 多久重新讀一次設定，在那之前使用者仍然用著新功能。
