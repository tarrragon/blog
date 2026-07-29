---
title: "Credential Stuffing（憑證填充）"
tags: ["身分安全", "Credential Stuffing", "Security"]
date: 2026-07-29
description: "說明攻擊者如何拿別處外洩的帳密清單來登入自己的服務，以及它與暴力破解在防護上的差異"
weight: 334
---

Credential stuffing 的核心概念是「拿在別處外洩的帳號密碼組合，到這個服務逐一試登入」。它利用的是同一個人在多個服務用同一組密碼，因此攻擊者不需要猜——手上的每一組都曾經是某人的真密碼，[authentication](/backend/knowledge-cards/authentication/) 這一層因此看到的是一次完全合法的登入。

## 概念位置

這一類攻擊與暴力破解共用同一個入口（登入端點），防護手段卻不同，因為它們消耗的資源不同。暴力破解對單一帳號嘗試大量密碼，速率限制與帳號鎖定攔得住；credential stuffing 對大量帳號各試一兩組，每個帳號的失敗次數都在門檻之下，按帳號計數的限制因此看不到它。

它也定義了密碼儲存的能力邊界。[salt](/backend/knowledge-cards/salt/) 與 work factor 提高的是「猜一次要付多少代價」，而這一類攻擊的密碼是已知的、不需要猜——[7.30 使用者密碼儲存](/backend/07-security-data-protection/password-storage-and-work-factor/) 的參數調到頂也擋不住它。

## 可觀察訊號與例子

登入端點的整體失敗率上升而個別帳號的失敗次數正常，是這一類的特徵訊號。其他常見形態：登入請求的來源位址分散但行為一致（相同的請求間隔、相同的 user agent）、大量帳號在短時間內首次從陌生地區登入成功、以及「帳號不存在」與「密碼錯誤」兩種回應的比例異常——後者代表攻擊者手上的清單與自己的使用者群重疊度高。

## 設計責任

防護的著力點在密碼之外。可用的機制包括比對外洩密碼清單（註冊與變更密碼時擋下已知外洩的組合）、要求第二因子讓密碼正確也不足以登入、按來源與行為特徵而非按帳號做速率限制、以及對成功登入做異常判讀（新裝置、新地區、與平常不同的時段）。

判斷自己的暴露程度，看的是使用者群體與大型外洩事件的重疊——面向一般消費者的服務重疊度最高，因為同一批人在數十個服務用同一組密碼。相鄰概念見 [authentication](/backend/knowledge-cards/authentication/) 與 [step-up authentication](/backend/knowledge-cards/step-up-authentication/)，登入節奏的判讀與處置見 [7.2 終端使用者的登入節奏](/backend/07-security-data-protection/identity-access-boundary/#終端使用者的登入節奏)，登入方式本身的選型見 [7.31 認證方式選型](/backend/07-security-data-protection/authentication-approach-selection/)。
