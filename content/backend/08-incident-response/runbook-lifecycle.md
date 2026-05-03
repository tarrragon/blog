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
- runbook 跟 [post-incident review](/backend/knowledge-cards/post-incident-review/) 的整合：每次事故後檢視 runbook
- runbook 跟 [drills](/backend/08-incident-response/drills-and-oncall-readiness/) 的整合：演練是有效性的證明
- 反模式：runbook 寫了沒人演練；事故時發現 runbook 步驟跟現實不符；runbook 無 owner、無修訂時間戳

## 概念定位

Runbook lifecycle 管理是把 runbook 當成會老化的工程 artifact 來治理，責任是讓文件內容持續對齊服務現況與事故實務。

這一頁處理的是文件壽命。沒有 lifecycle，runbook 很快會變成看起來完整、實際失效的紙上流程。

## 核心判讀

判讀 runbook 時，先看是否有使用與演練記錄，再看是否有明確淘汰條件。

重點訊號包括：

- runbook 是否有 owner、版本與修訂時間
- 是否有演練證明其可執行性
- 過期或無法使用的 runbook 是否有淘汰流程
- 每次事故後是否回寫修訂

## 案例對照

- [Atlassian](/backend/08-incident-response/cases/atlassian/_index.md)：協作工具事故很依賴 runbook 的版本同步。
- [GitHub](/backend/08-incident-response/cases/github/_index.md)：平台型服務的 runbook 常要跟著架構快速更新。
- [Slack](/backend/08-incident-response/cases/slack/_index.md)：通訊平台的 runbook 若過期，事故時會直接放大混亂。

## 下一步路由

- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：事故後 runbook 修訂
- 08.6 drills：runbook 演練驗證
- 08.13 repeated：[toil](/backend/knowledge-cards/toil/) 後 runbook 退場

## 判讀訊號

- 事故時 [incident command system](/backend/knowledge-cards/incident-command-system/) 找出 runbook、發現步驟過期
- runbook 上次修訂時間 > 12 個月、依賴的服務早已換版本
- 新 oncall 找不到「該事故對應的 runbook」
- runbook 數量只增不減、無淘汰流程
- runbook 質量靠 author 個人風格、無模板

## 交接路由

- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：事故後 runbook 修訂
- 08.6 drills：runbook 演練驗證
- 08.13 repeated：[toil](/backend/knowledge-cards/toil/) 後 runbook 退場
