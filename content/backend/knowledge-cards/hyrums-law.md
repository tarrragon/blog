---
title: "Hyrum's Law"
date: 2026-07-04
description: "使用者夠多時、介面的一切可觀察行為都會被依賴 — 不管你承諾了什麼；契約設計要主動給機器可讀欄位、否則人類可讀欄位會被迫變成契約"
weight: 50
tags: ["backend", "knowledge-card", "api-design"]
---

Hyrum's Law：當一個介面的使用者夠多、介面的**一切可觀察行為**都會被某個使用者依賴 —— 不管你在 [API contract](/backend/knowledge-cards/api-contract/) 裡承諾了什麼。名字來自 Google 工程師 Hyrum Wright 的觀察：文件寫「這個欄位格式可能變動」沒有用、只要行為可觀察、就有人寫死它。

## 工程意義

這條定律把「承諾」與「實際契約」拆開：你承諾的是文件寫的、你實際扛的是被依賴的。常見形態：consumer parse 錯誤 message 的文字做分支、provider 改個錯字就是 breaking change；consumer 依賴回應欄位的順序、序列化庫升級就壞；consumer 依賴未文件化的 timing 行為、優化反而炸鏈。

防禦方向是收窄可觀察面、並主動給該依賴的東西：機器分支要用的資訊放進顯式的機器可讀欄位（type / code / reason）、人類可讀欄位明文標示可變動；能加隨機化的地方加（如 Go map 迭代順序刻意隨機、讓「依賴順序」在第一天就壞掉、而不是三年後）。介面的變更紀律（什麼算 breaking）由此擴大：被廣泛依賴的未承諾行為、實務上跟承諾過的一樣貴。

## 概念位置

它是 [API contract](/backend/knowledge-cards/api-contract/) 的邊界條款：contract 定義你想承諾的、Hyrum's Law 提醒你實際被依賴的比那更多。錯誤回應的機器可讀欄位設計（避免 message 被當契約）是它在錯誤契約上的應用、見 [11.11 Status 與錯誤的雙向契約](/backend/11-api-design/error-bidirectional-contract/)。
