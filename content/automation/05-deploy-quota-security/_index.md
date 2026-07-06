---
title: "模組五：部署、配額與安全"
date: 2026-07-06
description: "把匿名可存取的 beacon 接收端上線後，怎麼守住免費配額、擋掉濫用、保持資料乾淨、以及判斷何時該換更重的工具"
weight: 6
tags: ["automation", "deployment", "quota", "security", "privacy", "migration"]
---

回答「這套統計上線後，長期怎麼守住」。beacon 接收端設成「所有人可存取」才能接住匿名訪客，但這也意味著任何人都能打這個網址。這一章處理上線後的四件事：免費配額的實際上限與監控、匿名端點的濫用防護、資料乾淨度（過濾自己的瀏覽、擋機器人）、以及隱私邊界。最後給出「Sheets 開始撐不住時怎麼判斷、怎麼往更重的工具遷移」的訊號與路徑。

安全的重點在這套架構裡不是「防止資料外洩」——流量統計本來就不含個人資訊——而是「防止端點被灌爆、防止髒資料污染統計」。這兩個目標決定了要加哪些保護、不需要加哪些。

## 章節文章

| 文章                                                                                        | 主題                                                                             |
| ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [部署與存取權限的安全含義](/automation/05-deploy-quota-security/deployment-and-access/)     | `execute as` / `who has access` 的安全角色、公開端點的威脅模型、更新部署不換網址 |
| [配額、濫用防護、隱私與遷移訊號](/automation/05-deploy-quota-security/quota-abuse-privacy/) | 配額碰撞症狀、過濾自己瀏覽與 token、不記 PII 的立場、離開 Sheets 的訊號          |

## 跨分類引用

- → [模組零：工具選型](/automation/00-mental-model/free-tier-and-tool-choice/)：Apps Script 與 Workers 的適用邊界
- → [模組二：接收端 handler](/automation/02-analytics-beacon/receiver-handler/)：被保護的端點怎麼實作的
- → [模組三：Sheets 當資料庫](/automation/03-sheet-as-database/)：容量邊界的技術細節
