---
title: "模組三：協議整合測試"
date: 2026-06-19
description: "對真實服務驗證 WebSocket / gRPC / HTTP 協議契約 — unit test 和 E2E test 之間的一層"
weight: 3
tags: ["testing", "integration-test", "websocket", "protocol", "contract-test"]
---

回答「我的 client 跟真實服務的互動是否正確」。這一層的關鍵是不用 mock，直接連真實服務。

## 對應 findings

| Finding | 來源                                                                                                                        | 內容                                                             |
| ------- | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| TF-8    | [T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/) + [T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/) | 自用工具 server+client 同機 → protocol integration test 成本極低 |

## 待寫章節

- [ ] Protocol integration test 定義（跟 unit test / E2E 的邊界）
- [ ] WebSocket 協議測試實作（對真實 ttyd 驗證 frame type + auth handshake）
- [ ] HTTP contract test 設計
- [ ] CI 中的服務 fixture 管理（啟動/停止真實服務的 test harness）
- [ ] 成本判斷表：什麼時候值得、什麼時候用 contract test 替代

## 跨分類引用

- → [monitoring 模組三 SDK 設計](/monitoring/03-sdk-design/)：SDK 的 transport 行為也需要 protocol test
- ← [ux-design 模組三 輸入機制](/ux-design/03-input-mechanism/)：輸入設計（整行 vs 逐字元）影響 protocol test 的斷言
