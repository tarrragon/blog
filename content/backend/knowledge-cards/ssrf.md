---
title: "SSRF"
date: 2026-04-23
description: "說明伺服器端請求被濫用時如何存取內部網路或 metadata 服務"
weight: 123
---

SSRF 的核心概念是「攻擊者讓伺服器替他發出未授權的網路請求」。如果 API 接收 URL 並由後端抓取內容，攻擊者可能指向內部服務、metadata endpoint（雲端主機的中繼資料服務，見 [Instance Metadata Service](/devops/infra/knowledge-cards/instance-metadata-service/)）或管理介面。 可先對照 [Stakeholder Mapping](/backend/knowledge-cards/stakeholder-mapping/)。

## 跟其他概念的關係

SSRF 是伺服器端輸入驗證與網路出口控制問題。它常出現在 webhook 測試、圖片抓取、URL preview、匯入工具、PDF 產生與代理服務。 可先對照 [Stakeholder Mapping](/backend/knowledge-cards/stakeholder-mapping/)。

## 可觀察訊號與例子

系統需要 SSRF 防護的訊號是使用者可以控制後端要連到的 URL。圖片上傳功能若支援「貼 URL 匯入」，後端必須限制可連線網域、IP range、scheme 與 redirect。

## 判斷條件與後果

使用者能控制後端要連的 URL 時，請求從伺服器的網路位置發出，連得到外部使用者連不到的內部服務與 metadata endpoint，所以檢查比對的是請求最終連到的位址。只比對網域字串時，網域可以解析到內網 IP，要在 DNS 解析之後比對 IP 是否屬於內網位址才攔得到；只檢查第一個 URL 時，外部網址可以 redirect 到內網，所以 redirect 要限制或逐跳重新檢查；用列舉內網範圍代替 allowlist 時，列漏的位址照樣連得到。沒有 timeout 與 response size limit 時，指向慢回應或巨大回應的目標會佔住後端的連線與記憶體。Egress policy 在網路層限制伺服器能連出的目的地，應用層的檢查被繞過時仍有這一層限制。Log 記下目標 host 與拒絕原因時，事後查得到攻擊者嘗試過哪些目標。
