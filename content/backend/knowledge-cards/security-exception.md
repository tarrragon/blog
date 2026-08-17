---
title: "Security Exception"
tags: ["治理例外", "Risk Acceptance"]
date: 2026-04-30
description: "說明資安風險例外如何以期限、補償控制與關閉條件管理"
weight: 255
---


Security exception 的核心概念是「在明確邊界內接受短期風險，並用協議管理收斂路徑」。它讓風險接受決策可追蹤、可關閉、可回寫。 可先對照 [Release Gate](/backend/knowledge-cards/release-gate/)。

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

每筆 security exception 要定義六個欄位，這張卡是它們的定義處：

1. **risk scope（風險範圍）**：接受風險的資產與邊界，以及誰批准。
2. **expiry（到期日）**：失效日與下次審查時間。
3. **compensating controls（補償控制）**：過渡期間額外的監測、限制或人工檢查。
4. **owner（負責人）**：業務側與技術側各一名，兩者由同一人擔任時延期沒有阻力。
5. **exit criteria（關閉條件）**：什麼條件成立才算收斂完成，要可驗證而不是「風險降低」這種敘述。
6. **write-back target（回寫目標）**：關閉後把知識與控制面改進寫回哪裡。

例外成立的同時要同步設計關閉節奏與回寫路徑。[Tripwire](/backend/knowledge-cards/tripwire/) 不是這六欄之一——它是掛在例外上的並列物件、自帶訊號與門檻，一筆例外可以掛零個或多個 tripwire。填寫協議與可套用的模板見 [7.17 例外、凍結與 Tripwire](/backend/07-security-data-protection/security-exception-freeze-tripwire/)、治理責任的分工見 [7.14 資安治理例外與 Tripwire](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)。
