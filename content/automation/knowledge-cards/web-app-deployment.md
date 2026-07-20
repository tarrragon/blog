---
title: "Web App 部署"
date: 2026-07-06
description: "把 Apps Script 專案掛成一個有公開網址、可被任何 HTTP 請求呼叫的端點時的部署模型與存取設定"
weight: 2
tags: ["automation", "apps-script", "web-app", "deployment", "knowledge-card"]
---

Web app 部署是把一段 Apps Script 程式掛成「有公開網址、可被 HTTP 呼叫」的端點的動作。部署前程式只能在編輯器裡手動執行；部署後它得到一個 `https://script.google.com/macros/s/.../exec` 網址，任何符合存取權限的請求打這個網址就會觸發 [doGet 或 doPost](/automation/knowledge-cards/doget-dopost/)。這是讓 Apps Script 能當 [beacon](/automation/knowledge-cards/beacon/) 接收端的前提。

## 概念位置

部署有兩個決定端點行為的設定。**執行身分（execute as）** 決定程式用誰的權限跑：選「我」時，匿名訪客送來的請求也用你的身分執行，才能存取你的試算表。**誰可存取（who has access）** 決定誰能呼叫這個網址：接收匿名訪客的 [beacon](/automation/knowledge-cards/beacon/) 必須選「所有人」，因為訪客沒有登入 Google。

## 可觀察訊號與例子

一個實務要點是部署與網址的關係：每次「新增部署作業」會產生一個新網址，但改完程式後應該用「管理部署作業」更新既有部署，網址才不變。用錯方式會讓前端指向舊網址、以為程式沒生效。

## 判讀方式

誰可存取設為「所有人」後，要判斷的是匿名端點被濫用的風險有多大：存取權限的安全含義見[模組五](/automation/05-deploy-quota-security/)。
