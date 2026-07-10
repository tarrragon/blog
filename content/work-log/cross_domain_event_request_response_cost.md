---
title: "用事件做同步查詢、等於手工重建 RPC — 跨 domain 解耦的完整帳單"
date: 2026-07-10
draft: false
description: "domain 直接查另一個 domain 的 repository 違反依賴方向；改事件驅動的 request/response 解了耦、但帳單具體：correlation id 配對並發、timeout 機制、三條錯誤路徑——都是同步呼叫免費附贈的東西。判準是需要解耦「依賴方向」還是「時間與部署」：前者用消費端 Port 就夠、後者才值得付事件的價。"
tags: ["ddd", "domain-event", "event-driven", "dip", "architecture", "dart", "flutter"]
---

> **觸發場景**：Flutter 書籍管理 App 的借閱功能（Loan domain）建立借閱記錄前要查書籍資訊，流程圖直白地畫著 `LoanService --> BookRepository`——Loan domain 直接摸進 Library domain 的 repository
> **疑問來源**：架構修正把它改成事件驅動的 request/response（`BookInfoRequested` / `BookInfoProvided`）。解耦成立了，但設計規格裡多出 requestId、waitFor、timeout、三條錯誤路徑——這些複雜度是必要代價、還是選錯工具的訊號？
> **整理目的**：把「事件驅動解耦」的帳單攤開、跟替代選項（消費端 Port）比價、收斂出選擇判準
> **本文邊界**：素材是該專案 v0.12-C.2 的設計規格（流程圖與事件介面層級、未及實作）——本文是架構決策推導、不是實測事故

---

## 問題：依賴方向錯了

`LoanService` 直接呼叫 `BookRepository`（Library domain 的資產）的問題有三層：Library 的變更會波及 Loan、Loan 的測試被迫載入 Library 的實作、兩個 domain 的邊界在這條呼叫上糊掉。這是依賴倒置（DIP）的標準違反現場——高層的業務流程直接抓住了別人家的低層實作。

要修的東西很明確。值得慢下來的是**修法的選項空間**，因為這次選的路線把帳單放大了。

## 事件驅動版：每一項都是同步呼叫免費附贈的

修正設計把一次查詢改成一趟事件往返：

```text
LoanService  --> EventBus: 發布 BookInfoRequested(bookId, requestId)
EventBus     --> LibraryService: 訂閱並處理
LibraryService --> EventBus: 發布 BookInfoProvided(bookInfo, requestId)
EventBus     --> LoanService: waitFor 收到回應（5 秒 timeout）
```

耦合確實消失了——Library 完全不知道 Loan 存在。但設計規格裡跟著出現的機制、逐項對照同步呼叫：

| 事件版要自己做的         | 同步呼叫的對應物                  |
| ------------------------ | --------------------------------- |
| `requestId`（UUID）配對  | 呼叫堆疊天然對應請求與回傳        |
| `waitFor` + 5 秒 timeout | 函式 return（要等多久是呼叫語意） |
| 書籍不存在的錯誤事件     | 回傳 null / 拋例外                |
| 超時路徑                 | 不存在（同步呼叫不會「沒人接」）  |
| EventBus 故障路徑        | 不存在                            |

這張表的形狀有個名字：**用事件通道手工重建 RPC**。事件的天然語意是通知——「事情發生了」、fire and forget、任意多訂閱者、無所謂回應；request/response 的語意是對話——一問一答、有超時、有失敗。把對話硬放上通知通道，correlation、timeout、錯誤回傳這些 RPC 基礎設施就得自己蓋一遍，而且每個跨 domain 查詢點都要再蓋一遍。

## 便宜的替代：消費端 Port

解「依賴方向」有更便宜的工具、而且同專案後來自己用過——[Port 介面](/work-log/flutter_port_interface_mock_hell_isp/)：Loan domain 宣告自己需要的能力、Library 提供實作、組裝層接線：

```dart
// Loan domain 內：宣告需求（依賴方向：Library 實作向 Loan 的介面靠）
abstract class BookInfoPort {
  Future<BookInfo?> getBookInfo(String bookId);
}
```

DIP 同樣成立（Loan 不認識 Library、只認識自己定義的 Port）、測試同樣乾淨（mock 一個單方法介面）、而呼叫還是一次普通的 await——requestId、timeout、事件錯誤路徑全部不需要。

那事件版買到的是什麼？兩樣 Port 給不了的：**時間解耦**（發布者不等回應、雙方可以不同時在線——分散式或背景處理的前提）跟**基數解耦**（一個事件任意多訂閱者）。判準因此收得很乾淨：

- 要解的是**依賴方向**（單機、同進程、一問一答）→ Port，付介面一張的價
- 要解的是**時間或部署**（跨進程、離線佇列、多方反應）→ 事件，correlation 與 timeout 是這個量級問題的合理成本

這個 case 的查詢是同進程、一對一、呼叫端必須等到答案才能往下走——三個特徵全部指向 Port。事件版不是錯（它也真的解了耦）、是**用了下一個量級的工具付了下一個量級的帳**。

## 判讀徵兆

- 事件名成對出現 `XxxRequested` / `XxxProvided` 且帶 correlation id——你在事件通道上做 RPC，先問「需要時間解耦嗎」
- 發布事件之後 `waitFor` / await 回應才能繼續——呼叫端語意上是同步的，事件只是繞路
- 跨 domain 呼叫的替代方案清單裡沒有「消費端 Port」——選項空間漏了最便宜的一格
- 反向確認：訂閱者不只一個、或處理可以離線 / 延後——這時事件才是本命，別退回 Port

## 相關閱讀

- 便宜選項的實戰：[mock 55 個方法只用 5 個：Port 介面](/work-log/flutter_port_interface_mock_hell_isp/)——同專案後期用 Port 解依賴的完整記錄
- 事件的正確場合：[Domain Event 命名的過去式](/work-log/domain_event_naming_past_tense/)——事件是已發生的事實、`BookInfoRequested` 這個名字本身就洩漏了它其實是請求不是事實
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——跨領域邊界與事件建模；工具量級的選擇也是「從操作推導」的一部分
