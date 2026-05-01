---
title: "8.16 Runbook Lifecycle 管理"
date: 2026-05-01
description: "把 runbook 從一次性文件變成有版本、有演練、會過期的 artifact"
weight: 16
---

## 大綱

- runbook 是會腐敗的資產：架構變更、依賴更新、人員流動都讓 runbook 失效
- runbook 生命週期：建立 → 演練 → 修訂 → 淘汰
- 有效性驗證：演練時實際跑、不是讀
- 版本對應：runbook 對應的服務版本、依賴版本
- 過期偵測：上次演練時間、上次修訂時間、上次成功使用時間
- runbook 跟 [post-incident review](/backend/08-incident-response/post-incident-review/) 的整合：每次事故後檢視 runbook
- runbook 跟 [drills](/backend/08-incident-response/drills-and-oncall-readiness/) 的整合：演練是有效性的證明
- 反模式：runbook 寫了沒人演練；事故時發現 runbook 步驟跟現實不符；runbook 無 owner、無修訂時間戳

## 判讀訊號

- 事故時 IC 找出 runbook、發現步驟過期
- runbook 上次修訂時間 > 12 個月、依賴的服務早已換版本
- 新 oncall 找不到「該事故對應的 runbook」
- runbook 數量只增不減、無淘汰流程
- runbook 質量靠 author 個人風格、無模板

## 交接路由

- 08.5 postmortem：事故後 runbook 修訂
- 08.6 drills：runbook 演練驗證
- 08.13 repeated：自動化 toil 後 runbook 退場
