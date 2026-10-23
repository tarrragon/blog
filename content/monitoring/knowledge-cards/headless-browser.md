---
title: "Headless Browser（無頭瀏覽器）"
date: 2026-10-23
description: "用 Playwright 或 Puppeteer 測追蹤碼、分析報表裡的機器流量，或自建統計與商業追蹤碼的訪問數對不上時"
weight: 10
tags: ["monitoring", "playwright", "bot-detection", "user-agent", "knowledge-card"]
---

無頭瀏覽器（headless browser）是不開啟可見視窗的瀏覽器：頁面照常載入、JavaScript 照常執行，只是畫面不顯示出來。它多半由程式驅動，Playwright、Puppeteer 這類自動化工具預設就以無頭模式啟動 Chromium；而「被程式驅動」是另一個屬性，有視窗的瀏覽器同樣可以被程式驅動，所以無頭只是被程式驅動的瀏覽器的其中一種樣子。可先對照 [First-party Cookie（第一方 cookie）](/monitoring/knowledge-cards/first-party-cookie/)（無頭模式下追蹤碼照樣寫 cookie）與 [Autocapture（自動事件收集）](/monitoring/knowledge-cards/autocapture/)（網站沒有呼叫的事件由誰決定送出）；把無頭瀏覽器當成要辨識的訪客時的訊號設計，見 [辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)。

## 概念位置

無頭模式改變的是瀏覽器自己對外暴露的特徵，追蹤碼在訪客的瀏覽器裡、收資料的伺服器在 vendor 那一端，都可能依這些特徵決定事件送不送出、收不收下。最直接的特徵是 User-Agent（瀏覽器在每個請求裡附上的身分字串）：一次以 Playwright 預設無頭模式啟動 Chromium 的實測裡，User-Agent 帶 `HeadlessChrome` 字樣，有視窗模式下是一般的 `Chrome`。被程式驅動則另有自己的特徵，`navigator.webdriver` 在 Playwright、Puppeteer、Selenium 驅動的瀏覽器裡是 `true`，有沒有視窗都一樣。所以「擋無頭瀏覽器」與「擋自動化」是兩條不同的規則：比對 `HeadlessChrome` 字樣的規則換成有視窗模式就不命中，比對 `navigator.webdriver` 的規則兩種模式都命中。被攔下的事件裡也包括網站沒有呼叫的[自動事件](/monitoring/knowledge-cards/autocapture/)，它們走的是同一條送出路徑。

## 可觀察訊號與例子

本站用 Playwright 寫的擷取腳本（[用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/)）在實測頁上載入本站測試用的一個 Meta Pixel。`fbevents.js` 載入後會向 Meta 取得這個 Pixel 的設定檔，設定檔指定要載入的模組（plugin）裡有一個 `botblocking`，它拿 `navigator.userAgent` 比對一份含 `HeadlessChrome/` 的機器人規則清單。無頭模式下 `fbevents.js` 照樣載入、`_fbp` 照樣寫入，而 PageView、ViewContent、Purchase 一筆都沒有送出；腳本改用有視窗模式之後，三筆事件都送出了。這個模組只攔事件請求，script 的載入與[第一方 cookie](/monitoring/knowledge-cards/first-party-cookie/) 的寫入不受影響，頁面上的狀態訊息在兩種模式下也相同，從頁面上看不出事件沒送。GA4 的 collect 請求在無頭模式下照樣送出並收到回應；GA4 在接收端預設排除已知機器人流量，依據是 Google 的研究與 IAB（Interactive Advertising Bureau，網路廣告業的產業組織）的機器人清單，被排除了多少不會顯示，所以從擷取結果判斷不出無頭模式的事件是否進了報表。

## 判讀方式

兩種模式的結果差異，量的是追蹤碼對無頭特徵的反應：有視窗模式下送得出、無頭模式下送不出的事件，是被比對 User-Agent 這類無頭特徵的規則攔下的。有視窗模式的 Playwright 仍然是被程式驅動的瀏覽器（`navigator.webdriver` 為真），所以它的結果不等於真人訪客的結果；追蹤碼改成依 `navigator.webdriver` 判斷時，有視窗模式也會被攔。比對自建統計與商業追蹤碼的訪問數時，差額裡可能有一部分是無頭瀏覽器的訪問：自建統計的接收端收下並標成機器流量，Meta Pixel 在瀏覽器裡就丟掉。

## 完整章節

無頭與有視窗兩種模式下 Meta Pixel 實際送出的請求、`botblocking` 的機制與擷取紀錄要記下的模式 → [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/)。自建統計怎麼用 User-Agent、`navigator.webdriver` 等訊號標記機器流量 → [辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)。GA4 預設的已知機器人排除與主機名稱篩選器 → [Client-side SDK 認證的根本限制](/monitoring/07-security-privacy/client-sdk-authentication/)。
