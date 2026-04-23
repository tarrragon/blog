---
title: "SSRF"
date: 2026-04-23
description: "說明伺服器端請求被濫用時如何存取內部網路或 metadata 服務"
weight: 122
---

SSRF 的核心概念是「攻擊者讓伺服器替他發出未授權的網路請求」。如果 API 接收 URL 並由後端抓取內容，攻擊者可能指向內部服務、metadata endpoint 或管理介面。

## 概念位置

SSRF 是伺服器端輸入驗證與網路出口控制問題。它常出現在 webhook 測試、圖片抓取、URL preview、匯入工具、PDF 產生與代理服務。

## 可觀察訊號與例子

系統需要 SSRF 防護的訊號是使用者可以控制後端要連到的 URL。圖片上傳功能若支援「貼 URL 匯入」，後端必須限制可連線網域、IP range、scheme 與 redirect。

## 設計責任

防護要包含 allowlist、DNS/IP 檢查、禁止內網位址、限制 redirect、timeout、response size limit 與 egress policy。Log 要記錄目標 host 與拒絕原因。
