---
title: "GDPR 最小化原則的工程落地"
date: 2026-06-19
description: "資料最小化、目的限制、儲存限制 — GDPR 三個核心原則在監控系統的工程實作方式"
weight: 5
tags: ["monitoring", "security", "privacy", "gdpr", "compliance", "data-minimization"]
---

GDPR 的資料最小化原則要求「只收集達成特定目的所需的最少資料」。這個法律原則轉譯到監控系統的工程實作，影響三個設計決策：收集什麼欄位、保留多久、誰可以存取。

## 資料最小化：只收集需要的欄位

資料最小化的工程落地是「每個收集的欄位都要能回答：這個欄位用來做什麼決策？」。如果一個欄位只是「可能有用」但沒有明確的消費場景，就不應該收集。

### 正面表列 vs 負面排除

正面表列（allowlist）是列出「收集哪些欄位」— 只收集清單上的欄位，其他全部不收。

負面排除（denylist）是列出「不收集哪些欄位」— 預設收集所有欄位，排除清單上的。

GDPR 的精神更接近正面表列 — 每個收集行為需要有正當理由（lawful basis）。工程上的實作方式是：事件 schema 定義哪些欄位是允許的，不在 schema 中的欄位在 collector 端丟棄。

### SDK 端的最小化

SDK 端的最小化更主動 — 在事件產生時就只包含必要的欄位，而非送到 collector 再過濾。

設計 SDK 的 event API 時，不提供「送任意 key-value」的 free-form API，而是提供結構化的 API：

```text
// free-form（難以控制收集了什麼）
monitor.event('login', data: {'email': email, 'ip': ip, 'device': device, ...})

// 結構化（schema 控制收集範圍）
monitor.event('login', loginMethod: 'biometric', success: true)
```

結構化 API 的參數在 SDK 設計時就決定了收集範圍，code review 時可以檢查「為什麼這個 event 需要這個參數」。

## 目的限制：收集的資料只用於聲明的目的

目的限制要求資料只用於收集時聲明的目的。監控系統收集事件的目的通常是 debug 和效能監控 — 如果之後要用同一份資料做行為分析或廣告投放，需要額外的法律基礎（通常是使用者同意）。

### 工程落地

目的限制在工程上的實作是「不同目的的資料分開儲存、分開授權」。

Debug 用的 error 事件和行為分析用的 event 事件存在不同的儲存位置（不同的 JSONL 檔案或不同的資料庫 table）。Debug 用途的 access 不需要使用者同意（legitimate interest）；行為分析用途的 access 需要使用者同意。

分開儲存讓「使用者撤回行為分析同意」的工程操作變簡單 — 刪除行為分析的儲存，不影響 debug 儲存。

## 儲存限制：不保留超過必要期間的資料

儲存限制要求資料只保留達成目的所需的最短期間。監控資料的合理保留期間依用途不同：

| 用途     | 合理保留期間              | 理由                              |
| -------- | ------------------------- | --------------------------------- |
| Debug    | 30-90 天                  | 大部分 bug 在 30 天內被發現和修復 |
| 效能趨勢 | 6-12 個月                 | 季節性趨勢需要至少一年的資料      |
| 行為分析 | 依同意期間                | 使用者同意到期就刪除              |
| 合規審計 | 依法規要求（通常 1-7 年） | 法規指定的最短保留期間            |

### 自動清理

Collector 的儲存清理應該自動化 — 手動清理依賴人記得執行，最終會被遺忘。

JSONL 儲存用「一天一檔」的命名（`events-2026-06-19.jsonl`），清理腳本每天刪除超過保留期限的檔案。Cron job 或 systemd timer 定期執行。

## 下一步路由

- 去識別化技術 → [去識別化策略](/monitoring/07-security-privacy/anonymization-strategy/)
- 監控資料洩漏的威脅分析 → [監控資料洩漏的 threat model](/monitoring/07-security-privacy/monitoring-data-threat-model/)
- Collector 的儲存設計 → [模組四 Collector 設計](/monitoring/04-collector/)
