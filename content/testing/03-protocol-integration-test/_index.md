---
title: "模組三：協議整合測試"
date: 2026-06-19
description: "對真實服務驗證 WebSocket / gRPC / HTTP 協議契約 — unit test 和 E2E test 之間的一層"
weight: 3
tags: ["testing", "integration-test", "websocket", "protocol", "contract-test"]
---

回答「我的 client 跟真實服務的互動是否正確」。這一層的關鍵是不用 mock，直接連真實服務。

## 本模組回應的測試盲區

| 案例                                                                                                                        | 盲區與補位                                                       |
| --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/) + [T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/) | 自用工具 server+client 同機 → protocol integration test 成本極低 |
| [T.C7](/testing/cases/dual-semantics-attribution/)                                                                          | 雙語意歸因：畫面殘留與後端未釋放症狀相同，真實後端驗證一跑定案   |

## 章節

- [Protocol integration test 定義](/testing/03-protocol-integration-test/definition-and-boundary/) — 跟 unit test / E2E 的邊界
- [WebSocket 協議測試實作](/testing/03-protocol-integration-test/websocket-protocol-test/) — 對真實 ttyd 驗證 frame type 與 auth handshake
- [HTTP contract test 設計](/testing/03-protocol-integration-test/http-contract-test/) — status code 語意、header 契約、error body 結構的驗證
- [CI 中的服務 fixture 管理](/testing/03-protocol-integration-test/service-fixture-management/) — 啟動與停止真實服務的 test harness 設計
- [成本判斷表](/testing/03-protocol-integration-test/cost-judgment/) — 什麼時候值得、什麼時候用 contract test 替代
- [真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/) — 服務無法本機啟動、只有共用測試環境時的常駐防線；對應 T.C7 雙語意歸因

## 跨分類引用

- → [monitoring 模組三 SDK 設計](/monitoring/03-sdk-design/)：SDK 的 transport 行為也需要 protocol test
- ← [ux-design 模組三 輸入機制](/ux-design/03-input-mechanism/)：輸入設計（整行 vs 逐字元）影響 protocol test 的斷言
