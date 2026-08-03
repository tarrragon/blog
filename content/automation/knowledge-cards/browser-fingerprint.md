---
title: "Browser Fingerprint（瀏覽器指紋）"
date: 2026-08-03
description: "由多個單獨無害的瀏覽器環境屬性組合而成、足以在不使用 cookie 的情況下辨識出特定裝置的特徵集合"
weight: 6
tags: ["automation", "privacy", "fingerprint", "analytics", "knowledge-card"]
---

瀏覽器指紋是由多個環境屬性組合而成、足以辨識出特定裝置的特徵集合。單獨看每一項都不足以識別任何人——螢幕解析度、時區、語言偏好、已安裝字型、`userAgent` 字串各自都被大量使用者共享；組合起來之後唯一性急遽上升，少數幾項就能把一台裝置從數百萬台中分出來，而且不需要寫入任何 cookie。這是在自建流量統計裡蒐集判別訊號時的能力上限，與 [beacon](/automation/knowledge-cards/beacon/) 送出什麼欄位直接相關。

## 概念位置

指紋與識別碼是兩種不同的識別途徑。識別碼（存在 `localStorage` 的隨機值）由網站產生、使用者可以清除、內容不從個人推導；指紋由使用者的環境被動產生、清除不掉、也不需要對方同意就能取得。這個差別決定了設計取向：**自建統計要辨識「是不是同一個瀏覽器」時用識別碼，用指紋做同一件事會在使用者無法拒絕的前提下達成，兩者的技術效果相近而性質不同**。指紋的另一個用途是分辨自動化環境，而這在 Apps Script 這類接收端上是唯一可行的途徑——[doPost](/automation/knowledge-cards/doget-dopost/) 拿不到任何 HTTP 標頭，判別素材只能由前端蒐集後隨 beacon 送出。做法與邊界見[辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)。

## 可觀察訊號與例子

高熵的屬性包括完整 `userAgent`（含版本與作業系統細節）、螢幕解析度與色彩深度、時區、字型清單、WebGL 渲染器名稱。低熵而仍有分析價值的替代品是把這些降維成分類標籤——`mobile` / `tablet` / `desktop` 三選一的裝置類別由 `userAgent` 推導而來，但送出的是分類結果而非原始字串，唯一性大幅下降而排版決策所需的資訊仍然保留。

## 判讀方式

判斷一個欄位該不該送，問它「單獨無害，但與已送出的欄位組合後唯一性有多高」。答案是「組合後接近唯一」時，改送降維後的分類標籤而非原始值。這條界線在[訪客識別與 opt-out](/automation/06-reading-the-data/visitor-identity/)的隱私邊界段有完整的取捨說明，配額與 PII 的整體討論見 [execution quota](/automation/knowledge-cards/execution-quota/) 所在的[模組五](/automation/05-deploy-quota-security/quota-abuse-privacy/)。
