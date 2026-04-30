---
title: "Security Exception"
tags: ["治理例外", "Risk Acceptance"]
date: 2026-04-30
description: "說明資安風險例外如何以期限、補償控制與關閉條件管理"
weight: 255
---

Security exception 的核心概念是「在明確邊界內接受短期風險，並用協議管理收斂路徑」。它讓風險接受決策可追蹤、可關閉、可回寫。

## 概念位置

Security exception 位在 [Release Gate](/backend/knowledge-cards/release-gate/)、[Release Freeze](/backend/knowledge-cards/release-freeze/) 與 [Tripwire](/backend/knowledge-cards/tripwire/) 之間。它承接治理層決策，並把決策資訊交給部署與 incident workflow。

## 可觀察訊號

系統需要 security exception 的訊號是：

- 修補窗口與業務時程暫時不一致
- 高風險項目需要短期過渡方案
- 團隊需要紀錄接受範圍與期限
- 關閉條件需要跨角色共識與可驗證證據

## 接近真實網路服務的例子

新漏洞公告後，某服務在修補完成前以例外方式允許受控上線，同步啟用補償控制（流量限制、額外審計、強化告警），並設定到期日與重評估會議時間。

## 設計責任

Security exception 要定義 risk scope、expiry、compensating controls、owner、close criteria 與 write-back target。例外成立的同時，也要同步設計關閉節奏與回寫路徑。
