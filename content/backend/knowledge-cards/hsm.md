---
title: "HSM（Hardware Security Module）"
date: 2026-07-20
description: "判斷金鑰材料需不需要脫離軟體邊界、放進不可讀取明文的專用硬體時的核心術語"
weight: 410
---

HSM 是專門保存加密金鑰材料並執行加密運算的硬體裝置，金鑰只在裝置內部使用、不以明文形式離開硬體邊界。它是 [Key Management](/backend/knowledge-cards/key-management/) 光譜上最嚴格的一端——軟體層的 key store 仍存在金鑰以某種形式被讀出的可能，HSM 的設計目標是連持有裝置的服務供應商都讀不到金鑰本體。

## 概念位置

HSM 的分級來自 FIPS 140-2 標準，Level 3 是雲端服務常見的合規門檻，代表防竄改與存取控制達到特定物理與邏輯強度。雲端 HSM 服務通常提供兩種信任模型：multi-tenant managed（供應商持有金鑰託管與 API plane，如一般的 [Key Management](/backend/knowledge-cards/key-management/) 服務）與 single-tenant dedicated（客戶獨享硬體、供應商不持有金鑰、也不能重置存取密碼）。後者的代價是存取憑證遺失等於金鑰永久遺失——供應商沒有後門可以幫忙救援。

## 可觀察訊號與例子

金融、政府、醫療這類有資料主權或 PCI HSM、HIPAA 合規壓力的場景，通常明文要求 dedicated HSM；一般 web app 或 SaaS 用 multi-tenant 的 managed key service 已足夠，額外導入 dedicated HSM 反而引入存取憑證的單點失誤。高敏操作（建新的操作身份、改權限政策、金鑰匯出）常綁定多人簽核（M-of-N quorum），單一人員即使憑證外洩也不能單獨完成高風險變更——這條設計對應簽章金鑰治理的通用原則：高價值金鑰的管理操作不該是單人單憑證。

## 判讀方式

決定要不要導入 dedicated HSM，判斷的起點是合規要求有沒有明文寫死物理隔離、以及信任模型接不接受供應商持有金鑰。若答案都是否定，multi-tenant 的 managed key service 通常已經滿足同等的 FIPS 等級，且運維成本低得多。已經導入的部署要檢查跨可用區的叢集拓樸、管理身份與操作身份是否分離、備份是否定期演練還原——任一項缺失都是待補項目。
