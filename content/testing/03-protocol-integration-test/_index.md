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
| T.C7    | [T.C7 症狀相同、成因兩種](/testing/cases/dual-semantics-attribution/)                                                       | 雙語意歸因：畫面殘留與後端未釋放症狀相同，真實後端驗證一跑定案   |

T.C5–T.C9 是後補案例批次、尚未編入 TF 系列，模組頁直接以案例編號引用。

## 待寫章節

- [x] Protocol integration test 定義（跟 unit test / E2E 的邊界）
- [x] WebSocket 協議測試實作（對真實 ttyd 驗證 frame type + auth handshake）
- [x] HTTP contract test 設計
- [x] CI 中的服務 fixture 管理（啟動/停止真實服務的 test harness）
- [x] 成本判斷表：什麼時候值得、什麼時候用 contract test 替代
- [x] [真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)（服務無法本機啟動、只有共用測試環境時的常駐防線；對應 T.C7 雙語意歸因）

## 跨分類引用

- → [monitoring 模組三 SDK 設計](/monitoring/03-sdk-design/)：SDK 的 transport 行為也需要 protocol test
- ← [ux-design 模組三 輸入機制](/ux-design/03-input-mechanism/)：輸入設計（整行 vs 逐字元）影響 protocol test 的斷言
