---
title: "Headless Browser（無頭瀏覽器）"
date: 2026-10-23
description: "用 Playwright 或 Puppeteer 測追蹤碼、分析報表裡的機器流量，或比對自建統計與商業追蹤碼的訪問數對不上時"
weight: 10
tags: ["monitoring", "playwright", "bot-detection", "user-agent", "knowledge-card"]
---

無頭瀏覽器（headless browser）是不開啟可見視窗、由程式驅動的瀏覽器：Playwright、Puppeteer 這類自動化工具預設以這種模式啟動 Chromium，頁面照常載入、JavaScript 照常執行，只是畫面不顯示出來。它與「自動化」是兩個獨立的屬性，有視窗的瀏覽器同樣可以被程式驅動。可先對照 [First-party Cookie（第一方 cookie）](/monitoring/knowledge-cards/first-party-cookie/)（無頭模式下追蹤碼照樣寫 cookie）與 [Autocapture（自動事件收集）](/monitoring/knowledge-cards/autocapture/)（自動事件同樣會被送出端的過濾攔下）；把它當成要辨識的訪客時的訊號設計，見 [辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)。

## 概念位置

無頭模式改變的是瀏覽器自己對外暴露的特徵，而接收資料的那一方據這些特徵決定要不要收。最直接的特徵是 User-Agent：一次以 Playwright 預設無頭模式啟動 Chromium 的實測裡，User-Agent 帶 `HeadlessChrome` 字樣，有視窗模式下是一般的 `Chrome`。自動化則另有自己的特徵，`navigator.webdriver` 在 Playwright、Puppeteer、Selenium 驅動的瀏覽器裡是 `true`，有沒有視窗都一樣。所以「擋無頭瀏覽器」與「擋自動化」是兩條不同的規則：比對 User-Agent 的規則換成有視窗模式就不命中，比對 `navigator.webdriver` 的規則兩種模式都命中。沒有被攔下的部分照常運作：追蹤碼一樣寫下[第一方 cookie](/monitoring/knowledge-cards/first-party-cookie/)。

## 可觀察訊號與例子

Meta Pixel 的設定檔帶來一個 `botblocking` 外掛，拿 `navigator.userAgent` 比對一份機器人規則清單，清單裡有 `HeadlessChrome/`。同一個實測頁、同一支擷取腳本，無頭模式下 `fbevents.js` 載入、`_fbp` 寫入，而 PageView、ViewContent、Purchase 一筆都沒有送出；加上 `--headed` 改用有視窗模式之後，三筆事件都送出了。頁面上的狀態訊息在兩種模式下相同，從頁面上看不出事件沒送。GA4 的 collect 請求在無頭模式下照樣送出並收到回應；GA4 在接收端預設排除已知機器人流量，依據是 Google 的研究與 IAB 的機器人清單，被排除了多少不會顯示，無頭模式的事件有沒有進報表，從擷取結果判斷不出來。

## 判讀方式

用自動化工具測試追蹤碼時，先決定要觀察的是一般使用者的瀏覽器會送出什麼，還是追蹤碼怎麼對待機器流量：觀察一般使用者時用有視窗模式，觀察機器流量時用無頭模式，兩種模式的結果並排才分得出哪些差異來自無頭模式。比對自建統計與商業追蹤碼的訪問數時，差額裡可能有一部分是無頭瀏覽器的訪問：自建的 beacon 收下並標成機器流量，商業追蹤碼在瀏覽器裡就丟掉。改 User-Agent 讓無頭模式通過過濾，觀察到的就不再是機器流量真實的待遇，所以擷取紀錄要記下這一次用的模式。

## 完整章節

無頭與有視窗兩種模式下 Meta Pixel 實際送出的請求，以及 `botblocking` 的機制 → [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/)。自建統計怎麼用 User-Agent、`navigator.webdriver` 等訊號標記機器流量 → [辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)。GA4 預設的已知機器人排除與主機名稱篩選器 → [Client-side SDK 認證的根本限制](/monitoring/07-security-privacy/client-sdk-authentication/)。
