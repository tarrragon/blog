---
title: "模組二：Gate 與 Fallback 設計"
date: 2026-06-19
description: "Biometric / Network / Auth / Permission — 每個 gate 成功時做什麼、失敗時做什麼、使用者不知道發生什麼時做什麼"
weight: 2
tags: ["ux-design", "gate", "fallback", "biometric", "authentication"]
---

回答「使用者過不了關卡時怎麼辦」。

## 本模組回應的 UX 盲區

| Finding | 來源                                                 | 內容                                                    |
| ------- | ---------------------------------------------------- | ------------------------------------------------------- |
| UF-4    | [U.C2](/ux-design/cases/biometric-only-no-fallback/) | biometricOnly 安全收益 vs 可用性代價 — 本模組的核心案例 |
| UF-5    | [U.C2](/ux-design/cases/biometric-only-no-fallback/) | 開發環境遮蔽 gate 問題（模擬器行為 vs 真機）            |

## 章節

- [Gate 分類與三問設計法](/ux-design/02-gate-fallback/gate-three-questions/) — 成功時做什麼、失敗時做什麼、使用者不知道發生什麼時做什麼
- [Biometric fallback 完整設計](/ux-design/02-gate-fallback/biometric-fallback-design/) — iOS Face ID / Touch ID 和 Android BiometricPrompt 的行為差異與 fallback 策略
- [網路斷線 UX 模式](/ux-design/02-gate-fallback/network-offline-ux/) — Offline-first / retry / degraded mode 三種網路 gate 的處理策略
- [Permission 請求時機與措辭](/ux-design/02-gate-fallback/permission-request-timing/) — 使用者只有一次機會理解為什麼需要這個權限，時機選擇是設計決策
- [開發環境 vs 真機的 gate 行為差異表](/ux-design/02-gate-fallback/dev-vs-real-gate-behavior/) — 模擬器、debug build、test 環境中的 gate 行為和真機 release build 不同

## 跨分類引用

- → [testing 模組一 測試策略](/testing/01-test-strategy-layers/)：gate fallback 的 mock vs 真機行為差異需要 protocol test
- → [monitoring 模組七 資安](/monitoring/07-security-privacy/)：biometric fallback 的安全 vs 可用性取捨
