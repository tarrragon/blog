---
title: "Pseudonymization（假名化）"
date: 2026-10-22
description: "要把含個人資料的明細交給分析、跨租戶彙整或測試環境使用，判斷換成代碼之後還算不算個人資料、代碼會不會被回推時，查假名化與匿名化的差別與金鑰的保管方式"
weight: 489
tags: ["backend", "security", "privacy", "data-protection"]
---

假名化（pseudonymization）是用一個代碼取代姓名、電話、Email 這類直接識別欄位，而代碼要靠另外保管的金鑰或對照表才連得回原本的值：對照表直接查回，帶金鑰的雜湊則是對每個可能值重算一次再比對。對持有金鑰或對照表、能把代碼連回當事人的一方，假名化的資料在 GDPR 這類法規下仍屬個人資料；與它相對的是匿名化（anonymization），處理後的資料無法再連回個人。可先對照 [Tenant Boundary（租戶邊界）](/backend/knowledge-cards/tenant-boundary/) 與 [Message Authentication](/backend/knowledge-cards/message-authentication/)。

## 概念位置

常見的做法是帶金鑰的雜湊（HMAC，構造見 [Message Authentication](/backend/knowledge-cards/message-authentication/)）：同一個電話號碼在同一把金鑰下得到同一個代碼，所以分析時仍能把同一個人的多筆紀錄串起來，而沒有金鑰的人算不出代碼對應的號碼。不帶金鑰的直接雜湊做不到這一點：電話、Email 的可能值有限，攻擊者把所有可能值都算一次雜湊就能回推。金鑰的保管位置決定了誰能串接、誰能還原：金鑰按租戶或 cell 分開保管時，同一個人在不同租戶的代碼不同，跨租戶串接不了；用一把跨租戶共用的金鑰時可以串接，而那把金鑰被拿走時，全部被串接租戶的代碼都能被窮舉回推；讓雜湊運算在保管金鑰的服務內執行、金鑰不離開服務，攻擊者要持續呼叫服務才算得出代碼，可以限流並稽核。

## 可觀察訊號與例子

平台把訂單明細匯出到中央資料倉儲做購買行為分析，離開資料庫之前把會員的電話與 Email 換成 HMAC 代碼。代碼本身換不回電話號碼，而去識別化仍有兩種常見的不完整：電話或地址殘留在備註這類自由文字欄位裡，以及郵遞區號、生日、下單時間這類欄位彼此組合之後仍能認出個人。

## 設計責任

假名化要寫清楚三件事：哪些欄位被換掉、金鑰存在哪裡由誰能讀、自由文字與準識別欄位怎麼處理。跨租戶的資料整合選擇哪一種形態、彙整之後碰得到幾個租戶，見 [7.44 多租戶平台的隔離層級](/backend/07-security-data-protection/multi-tenant-platform-isolation-tiers/)；資料遮罩的治理見 [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)。
