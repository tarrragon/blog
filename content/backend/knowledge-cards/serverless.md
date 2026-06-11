---
title: "Serverless"
date: 2026-06-11
description: "說明按請求 / 按用量計費、由平台管理執行環境與擴縮的運算交付模型、與其冷啟動與計價邊界"
weight: 373
---

Serverless 的核心概念是把「伺服器的存在」從開發者的責任清單移除：程式碼以函式或請求處理單元交給平台、平台負責執行環境、擴縮與閒置歸零、費用按實際用量計（請求數、執行時間、記憶體）。名稱說的是「開發者看不到 server」、伺服器本身仍然存在 — 只是由平台調度。代表形態是 FaaS（AWS Lambda、Cloud Functions）與 serverless 化的資料庫（Aurora Serverless、Cosmos DB serverless）；相對的長駐交付形態見 [container](/backend/knowledge-cards/container/)。

## 概念位置

Serverless 位在運算交付模型的光譜上：比 [container](/backend/knowledge-cards/container/) 平台更往「平台接管」靠 — container 平台管編排、執行單元仍長駐；serverless 連長駐都交給平台、執行單元隨請求出現與消失。它跟 [BaaS](/backend/knowledge-cards/baas/) 常被併用但責任不同：BaaS 提供現成的後端模組（認證、資料庫）、serverless 提供「自己的程式碼、別人的執行環境」。閒置歸零的特性接回 [cold start](/backend/knowledge-cards/cold-start/) — 歸零的另一面是喚醒延遲。

## 可觀察訊號與例子

適合 serverless 的訊號是負載間歇且事件驅動：webhook 接收、圖片上傳後的縮圖處理、定時批次 — 流量為零時費用為零、突發時平台自動拉起。一個報名系統的確認信寄送、每天觸發幾百次、每次跑兩秒：常駐主機為它待命整天是浪費、serverless 按兩秒計費。

撞到邊界的訊號有三類：執行時長上限（長任務被平台切斷）、長連線模型不合（WebSocket 類常駐需求要繞路）、以及計價曲線反轉 — 流量從間歇變成持續高檔後、按請求計費會超過長駐 instance、各家 serverless 資料庫的計價單位差異也直接影響這條曲線的位置。

## 設計責任

採用 serverless 時的設計責任是把「執行單元隨時消失」當前提：狀態放外部（資料庫、object storage）、本地檔案與記憶體只當單次請求的暫存；冷啟動延遲要量測並決定是否預熱；計價要建立用量模型、設帳單 alert — 按用量計費的服務、失控的迴圈或被打的 endpoint 會直接變成帳單事故。
