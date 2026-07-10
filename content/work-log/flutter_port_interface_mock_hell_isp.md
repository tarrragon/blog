---
title: "mock 要配置 55 個方法、實際只用 5 個 — 測試痛是介面設計痛的探針"
date: 2026-07-10
draft: false
description: "service 測試的 mock 負擔正比於它依賴的介面寬度：依賴四個大介面共 55 個方法、實際呼叫 5 個，91% 的 mock 配置是純浪費、還會炸 MissingStubError。修法是介面隔離——抽出只含實際使用方法的 Port，讓 mock 縮到跟真實依賴一樣窄；為未來預留的方法用 TODO 標記啟用時機。"
tags: ["flutter", "dart", "ddd", "isp", "testing", "mock", "repository", "port"]
---

> **觸發場景**：Flutter 書籍管理 App 要幫 `SyncReadinessService` 寫測試，mock 設置一路撞牆：四個依賴共 55 個方法要配置、漏配就 MissingStubError、mockito 的嵌套 when 又有語法限制——而這個 service 實際呼叫的方法只有 5 個
> **疑問來源**：測試這麼難寫，是測試工具的問題、還是被測物的問題？
> **整理目的**：記下「mock 負擔」作為介面設計探針的判讀方式、以及 Port 介面（ISP）的落地步驟
> **本文邊界**：素材是該專案 v0.18.6 的重構計畫（含依賴盤點數字與 wave 拆分）；Port 是 hexagonal architecture 的用語、這裡取其「消費端定義的窄介面」語意

---

## 依賴盤點：91% 的 mock 配置是浪費

寫不動測試的第一步是把依賴攤開來數。`SyncReadinessService` 的建構子收四個依賴，逐一盤點方法數與實際使用：

| 依賴             | 介面方法數 | 實際呼叫                  |
| ---------------- | ---------- | ------------------------- |
| `SyncRepository` | 23         | 2（待同步變更、待解衝突） |
| `BookRepository` | 16         | 1（getAllBooks）          |
| `ChangeTracker`  | 10         | **0**                     |
| `EventBus`       | 6          | 2                         |

合計 55 個方法、用 5 個。mock 這個 service 的依賴，等於為 50 個永遠不會被呼叫的方法做配置決策——每個都可能漏（MissingStubError）、每個都是測試檔的噪音。`ChangeTracker` 更直接：10 個方法、零使用，這個依賴純粹是建構子沿著前例複製來的。

數字本身就是診斷：**mock 負擔正比於介面寬度、不正比於被測物的複雜度**。測試難寫的根因不在 mockito、在被測物宣告的依賴遠寬於它需要的能力。

## 往上追：一個 Repository、五種職責

`SyncRepository` 的 23 個方法拆開看是五種職責：變更記錄管理（6）、同步任務管理（6、預留給 UC-08）、衝突解決（5）、離線佇列（4、預留 UC-09）、同步統計（2、預留 UC-10）。五分之三是**為未來 use case 預留的投機式方法**——現在沒有人呼叫、但每個消費者都被迫認識它們。

這是介面隔離原則（ISP）教科書式的違反現場，而它的第一個受害者是測試：生產程式碼呼叫方法時不在乎介面還有幾個方法、mock 卻要面對整個介面。**測試是第一個被迫「完整消費」介面的客戶**，所以介面過寬的痛總是先在測試爆。

## 修法：消費端定義的窄介面

重構的核心動作是抽 Port——從消費者的實際需求出發定義介面、而不是從資料來源的能力出發：

```dart
/// 從 SyncRepository 的 23 個方法中抽取實際需要的 2 個
abstract class SyncQueryPort {
  Future<List<ChangeRecord>> getPendingChanges({int? limit});
  Future<List<ConflictResolution>> getPendingConflicts({int? limit});
}

/// 從 BookRepository 的 16 個方法中抽取實際需要的 1 個
abstract class BookQueryPort {
  Future<List<Book>> getAllBooks();
}
```

三個配套讓改動保持小：

- **Repository 實作 Port、原介面不動**：`abstract class SyncRepository implements SyncQueryPort`——既有實作自動滿足新介面、其他消費者不受影響
- **Service 建構子改收 Port**：依賴從 55 個方法縮到 5 個、`ChangeTracker` 直接移除；測試 mock 的對象變成 2 方法與 1 方法的小介面
- **預留方法標記啟用時機**：`// TODO(UC-08): 實際同步功能時啟用`——投機式方法不刪（設計已評估過）、但每個都有名字跟啟用條件，下次盤點時「這是預留還是死碼」有據可查

值得注意方向性：Port 放在**消費端的 domain 目錄**（`synchronization/ports/`、`library/ports/`），因為它表達的是「這個 domain 需要什麼能力」、不是「Repository 提供什麼」。同一個 Repository 未來可以實作多個不同消費者的 Port，各自窄、互不牽連。

## 判讀徵兆

- mock 設置的行數超過測試本體——先數被測物依賴的介面方法數 vs 實際呼叫數
- MissingStubError 反覆出現——每一次都是「介面要求你認識的方法」跟「你實際關心的方法」的差距
- 建構子的某個依賴在整個 class 內零呼叫——複製前例的沉積、直接刪
- 介面裡一半以上的方法標著「未來會用」——預留可以，但要有 TODO 加啟用條件，否則每個消費者與 mock 永遠陪葬

「測試很難寫」在這個 case 裡是禮物：它比任何架構審查都早、都具體地量化了介面設計的問題（91% 這個數字就是證據）。把測試痛當成噪音硬吞（寫更肥的 mock helper）、跟把它當探針回頭修介面，是兩條分岔路——同專案的 [mock 基礎設施過度工程](/work-log/flutter_mock_infrastructure_overengineering_deleted/)正是前一條路的下場。

## 相關閱讀

- 概念地基：[DDD 領域驅動設計指南](/ddd/)——service 與 repository 的邊界、以及分工表裡「domain 持有的是能力需求」
- 硬吞測試痛的反面教材：[1101 行自建測試基礎設施](/work-log/flutter_mock_infrastructure_overengineering_deleted/)——mock 難寫的兩種回應：修介面（本文）vs 蓋更大的 mock 系統（該篇）
- 投機式預留的另一形態：[過度設計震盪](/work-log/flutter_async_query_overdesign_oscillation/)——那篇的迭代期沉積跟本文的預留方法同源，差別是 Port 案例的預留有 TODO 加啟用條件、不是無主地放著
