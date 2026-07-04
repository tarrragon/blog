---
title: "持久連線推送：WebSocket、SSE、long-polling 的承諾差異"
date: 2026-07-04
description: "server 推 client 的持久連線機制對消費者承諾什麼：重連誰負責、訊息會不會漏、單向還是雙向；選型看消費者形狀"
weight: 1
tags: ["backend", "api-design", "realtime"]
---

WebSocket、SSE、long-polling 都在解同一個需求：server 有事情要主動送給 client、而不是等 client 來問。三者的差別在推的時候對消費者承諾了什麼 —— 連線斷了誰負責重連、訊息會不會漏、能不能雙向 —— 而不在能不能推。這三條承諾線決定選型、比「哪個比較新」有用得多 —— 選型看的是消費者形狀：這個 client 需要單向還是雙向、能不能容忍漏訊、網路可不可控。以下把三者的承諾攤開、對到這三個問題。webhook 這種 server 對 server 的事件推送形狀不同、收在[另一篇](/backend/11-api-design/styles/realtime/realtime-webhook-contract/)。

## 協議各給多少保證

[SSE](/backend/knowledge-cards/sse/)（Server-Sent Events）把重連寫進協議本身。WHATWG 的規範定義：連線斷掉時 user agent 自動重連、重連時把最後收到的 event id 放進 `Last-Event-ID` header 送回 server、server 據此可從斷點往後補送（見 [11.C55](/backend/11-api-design/cases/sse-whatwg-spec-reconnection/)）。所以 SSE 對消費者的承諾是「自動重連加一個補送的協商鉤子」。要注意這個承諾的邊界：spec 只保證瀏覽器會送 `Last-Event-ID`、實際補不補送由 server 有沒有實作 replay 決定；而且 SSE 是單向的、client 要傳資料回 server 得另開通道。

[WebSocket](/backend/knowledge-cards/websocket/) 走相反的路：給雙向管線、不給保證。RFC 6455 只定義 handshake 與 framing、對投遞保證、[ack](/backend/knowledge-cards/ack-nack/)（收到確認）、重連、斷點續傳全部沉默（見 [11.C56](/backend/11-api-design/cases/websocket-rfc6455-transport/)）。這個沉默是設計、不是遺漏 —— 可靠性語意留給應用層。這代表每個用 WebSocket 的服務都要自己蓋一套：Slack 的 Socket Mode 在 WebSocket 上加了 envelope ack（每則事件回一個確認）、未 ack 就 retry、多連線熱備、斷線前預警（見 [11.C57](/backend/11-api-design/cases/websocket-slack-socket-mode/)）—— 這套是 Slack 自己補的、不是 WebSocket 標準行為、換一個 vendor 補的方式又不一樣。

long-polling 是把普通 HTTP 請求 hold 住到有事件才回。RFC 6202 講清楚它的機制代價：每則訊息一次完整 request/response、帶完整 HTTP headers（payload 小時 header 佔比高）、最大延遲跨三段網路傳輸、每個 client 佔一條連線（見 [11.C58](/backend/11-api-design/cases/longpolling-rfc6202-mechanics/)）。這些重量是機制決定的、不是實作品質問題。它的價值在相容性下限：WebSocket 連線不保證每個環境都建得起來（少數受限網路 —— 舊企業 proxy、深度封包檢查 —— 仍可能擋）、所以 Socket.IO 預設先用 long-polling 建連、再嘗試 upgrade 到 WebSocket（見 [11.C59](/backend/11-api-design/cases/longpolling-socketio-negotiation/)；這是 Socket.IO 的策略、有些 vendor 反向、先試 WebSocket 再退回）。

本文聚焦這三個已成熟的主流。WebTransport（HTTP/3 之上的新興雙向 transport）正在補 WebSocket 的多 stream 與 datagram 缺口、但瀏覽器與生態支援仍在成熟；HTTP/2 Server Push 已被主流棄用退場。兩者都不進本文的選型、但值得知道它們落在光譜的哪一端。

## 承諾差異並排

把三者的承諾攤成一張表。下表依各機制的一手定義（RFC 6455、RFC 6202、WHATWG SSE spec）整理、不是單一 vendor 的對照宣傳。

| 機制         | 方向     | 重連           | 投遞保證             | 相容性                |
| ------------ | -------- | -------------- | -------------------- | --------------------- |
| SSE          | 單向     | 協議內建       | 補送靠 server replay | 一般（HTTP 之上）     |
| WebSocket    | 雙向     | 應用層自建     | 應用層自建           | 可能被 proxy 擋       |
| long-polling | 請求驅動 | 每次請求即重連 | 每則一次完整回應     | 最高（就是普通 HTTP） |

表只是索引、每一格的成立條件要回到情境判讀。以「重連」欄為例：SSE 的「協議內建」對消費者是零成本的自動重連、但補送的完整性要 server 端配合；WebSocket 的「應用層自建」意思是這件事跑不掉、Slack Socket Mode 那套 ack 加 retry 是最低成本、不是可選；long-polling 沒有「重連」這個概念、因為每則訊息本來就是一次新請求、斷線在下一次請求自然癒合、代價是延遲與 header 開銷。

## 選型：對到消費者形狀

三條承諾線對到三種消費者形狀。消費者只需要 server 單向推、又想要開箱即用的重連（儀表板、通知流、log tail）—— SSE 的承諾剛好、不必自己蓋重連。消費者需要雙向、低延遲、高頻互動（協作編輯、遊戲、互動終端）—— WebSocket 給你管線、但要接受「可靠性得自己蓋」這筆帳、參考 Slack 那套 ack 加 retry 的形狀。消費者在不可控的網路環境、WebSocket 不保證連得上 —— 要一條相容性 fallback、long-polling 是那個下限、常搭配 transport negotiation（能 upgrade 就 upgrade、方向因 library 而異）。

這三格對應 [11.2 消費者形狀軸](/backend/11-api-design/api-style-selection/) 的推送情境。共同的判讀是：這三種都不自帶「訊息一定不漏」的保證 —— SSE 的補送、WebSocket 的 ack、都要 server 或應用層主動實作。真的要「事件一定送達、可重放」的語意、那是佇列的責任、路由到 [03 訊息佇列](/backend/03-message-queue/)、不是在推送機制上硬蓋。

## 下一步路由

- server 對 server 的事件推送：[webhook 對外承諾](/backend/11-api-design/styles/realtime/realtime-webhook-contract/)
- 消費者形狀選型軸：[11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)
- 要可靠送達與重放的事件語意：[03 訊息佇列](/backend/03-message-queue/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
