---
title: "模組二：Gate 與 Fallback 設計"
date: 2026-06-19
description: "Biometric / Network / Auth / Permission — 每個 gate 成功時做什麼、失敗時做什麼、使用者不知道發生什麼時做什麼"
weight: 2
tags: ["ux-design", "gate", "fallback", "biometric", "authentication"]
---

回答「使用者過不了關卡時怎麼辦」。

## 對應 findings

| Finding | 來源                                                 | 內容                                                  |
| ------- | ---------------------------------------------------- | ----------------------------------------------------- |
| UF-4    | [U.C2](/ux-design/cases/biometric-only-no-fallback/) | biometricOnly 安全收益 vs 可用性代價 — **本模組主寫** |
| UF-5    | [U.C2](/ux-design/cases/biometric-only-no-fallback/) | 開發環境遮蔽 gate 問題（模擬器行為 vs 真機）          |

## 待寫章節

- [ ] Gate 分類與三問設計法（成功 / 失敗 / 使用者不知道發生什麼）
- [ ] Biometric fallback 完整設計（iOS/Android 差異）
- [ ] 網路斷線 UX 模式（offline-first / retry / degraded mode）
- [ ] Permission 請求時機與措辭
- [ ] 開發環境 vs 真機的 gate 行為差異表

## 跨分類引用

- → [testing 模組一 測試策略](/testing/01-test-strategy-layers/)：gate fallback 的 mock vs 真機行為差異需要 protocol test
- → [monitoring 模組七 資安](/monitoring/07-security-privacy/)：biometric fallback 的安全 vs 可用性取捨
