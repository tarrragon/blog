---
title: "Riverpod 的 reactive 邊界"
date: 2026-07-16
description: "頁面用了 Riverpod 卻對某些變化沒反應、或 reactive 行為在特定時機炸掉時使用。Riverpod 的 reactive 保證只覆蓋 provider 圖的內部——排查沿著圖的邊界走：變化在圖上嗎、在哪個容器的圖上、節點還活著嗎。"
weight: 1
tags: ["flutter", "dart", "riverpod", "state-management", "reactive", "architecture"]
---

Riverpod 的 reactive 保證有明確的涵蓋範圍：**provider 圖的內部**。`ref.watch` 建立的依賴、`StreamProvider` 的推送、Notifier 的狀態轉換——這些機制在圖上的節點之間運作可靠；圖外的變化（資料庫寫入、外部容器的操作、已 dispose 節點上的寫入）不觸發任何 reactive 行為、也多半不報錯。「有用 Riverpod」跟「會對變化反應」是兩件事，中間差的就是這條邊界。

本章把邊界拆成四個方向，每個方向由一個實際踩過的 case 支撐。排查判準收成三問：**這個變化是 provider 圖上某個節點的狀態變化嗎？在哪個容器的圖上？節點還活著嗎？**

## 心智模型：配方、廚房、圖

provider 的全域宣告是**配方**——描述狀態怎麼建、怎麼變化；狀態本身活在**容器**（`ProviderContainer`／`ProviderScope`）裡，同一份配方在兩個容器裡煮出兩份互不相干的狀態。容器內的 provider 依 `ref.watch` 的依賴關係連成**圖**：節點是 provider 的狀態、邊是 watch 依賴，狀態變化沿著邊傳播、觸發下游重建。

reactive 的全部機制都建立在這張圖上。四個邊界各是圖的一個面向：圖屬於誰（空間）、圖上有什麼（涵蓋）、圖外的變化怎麼進來（接入）、節點活多久（時間）。

## 空間邊界：狀態屬於容器、不屬於宣告

`main()` 自建 `ProviderContainer` 觸發初始化、UI 跑在 `runApp` 的 `ProviderScope` 裡——兩個容器各持一份狀態，初始化改的是外部容器那份、UI 監聽的是 Scope 那份，App 永遠停在載入畫面。跨容器操作不報錯、只是安靜地作用在預期之外的地方，每段程式碼單獨看都正確。

判準：**一個 App 裡活著的容器數量應該是一**，每多一個都要能說出它為什麼必須隔離（測試的 `ProviderContainer(overrides:)` 是正當隔離）。全專案搜 `ProviderContainer(`、逐一問「它跟 UI 的 Scope 是同一個嗎」。確實需要在 `runApp` 前操作 provider 時（如讀取啟動設定），用 `UncontrolledProviderScope` 讓兩邊共用同一個容器。完整機制與修法：[App 永遠卡在載入畫面](/work-log/flutter_riverpod_dual_container_state_desync/)。

## 涵蓋邊界：圖上只有 provider 的狀態

`ref.watch(bookRepositoryProvider)` 對單例 `Provider<BookRepository>` 建立的依賴永遠不觸發——這個 provider 的狀態是「repository 物件參考」、整個生命週期不變；SQLite 寫入了一百本書，物件參考一動不動。資料庫的變化不在圖上，於是刷新被推到圖外解決：導航返回點補 `loadData()`、EventBus 橋接、多個視圖各自維護 load 時機——補償刷新的出現就是涵蓋缺口的訊號。

判準：要讓畫面對某個變化反應，**那個變化本身必須是圖上某個節點的狀態變化**。修法方向一致——把資料變更做成一級節點（repository 補 stream 出口、`StreamProvider` 包成 provider），視圖回到純 `ref.watch`。三段補償演進與判讀訊號表：[ref.watch 觀察的是 provider 圖、不是資料庫](/work-log/flutter_riverpod_reactive_boundary_ref_watch/)。

## 接入邊界：圖外的變化要立節點才進圖

把 repository 的 stream 接成圖上節點、是涵蓋缺口的結構性修法，接入處有自己的實作契約。三個問題各有一個會靜默失效的預設答案：訂閱模型（多個視圖同時聽、`StreamController()` 預設單訂閱、第二個訂閱者執行期 throw）、初始值（broadcast 不補送歷史、不處理的話畫面空到下一次寫入）、dispose（controller 的關閉責任跟著持有者走）。三個實作點的完整落地：[StreamProvider 包 repository watch stream](/work-log/flutter_streamprovider_wraps_repository_watch/)。

其中訂閱模型的選擇值得單獨記：`StreamController()` vs `.broadcast()` 是零成本差異，選限制更高的單訂閱版本、限制在只有一個訂閱者期間完全沉默、第二個訂閱者出現才爆。在零成本差異下把「會有多個觀察者」的領域先驗寫死成單訂閱，是設計缺陷、不是需求演化。單訂閱與 broadcast 的行為差異全表（buffer、pause、重新訂閱）：[StreamController single vs broadcast](/work-log/dart_stream_controller_single_vs_broadcast/)。

## 時間邊界：節點的生命有兩頭界線

async 函式的每個 `await` 都是一個 gap：等待期間使用者可能離開頁面、Notifier 被 dispose，await 回來再碰 `ref` 就炸 `UnmountedRefException`。修法可機械化——**每個 await 之後、第一次碰 `ref` 之前**檢查 `ref.mounted`；而且刻意不抽成 helper：guard 的價值在「它在哪」，明確的檢查點讓 review 用眼睛掃就能驗證每個 gap 有沒有守。長流程、可離開的頁面（匯入、同步、批次處理）風險最高。完整機制與「評估必跑、可決定不重構」的技術債處置：[await 回來的時候、頁面已經關了](/work-log/flutter_unmounted_ref_async_gap/)。

生命週期的另一頭是 build 期間：widget tree 建置中直接改 provider 狀態同樣是非法時機，觸發點要用 `addPostFrameCallback` 延到首幀之後。`ref` 的合法視窗兩頭都有界——await 之後可能太晚、build 之中太早。

## 排查判準

reactive 失靈時沿三問走，每一問對應一個邊界：

| 問題               | 對應邊界   | 常見答案與訊號                                                                      |
| ------------------ | ---------- | ----------------------------------------------------------------------------------- |
| 變化在圖上嗎？     | 涵蓋、接入 | 資料庫寫入不在圖上——`ref.watch` 對象是單例 `Provider<Repository>` 時 watch 永不觸發 |
| 在哪個容器的圖上？ | 空間       | 狀態「永遠是初始值」指向無人操作這份實例——數容器、查操作方作用在哪份                |
| 節點還活著嗎？     | 時間       | 崩潰 stack 指向 await 之後的 state 寫入——async gap 沒守                             |

三問都過、reactive 仍不對時，回到接入層的實作契約查：訂閱模型（`Bad state` = 單訂閱撞多訂閱）、初始值（畫面空到下次寫入 = broadcast 沒補當前值）、mock 與真實實作的 stream 契約對齊。

## 邊界

本章處理 Riverpod 這個框架的 reactive 機制邊界，是實作層知識。「觀測能力該放哪一層」（契約歸 domain、機制歸 infrastructure、框架訂閱歸組裝層）是理論層的歸屬判準、與框架無關，見 [觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)；「事件與狀態流哪個當通知載體」的選擇也在理論層，見 [domain event 與狀態流](/ddd/domain-event-vs-state-stream/)。本章假設載體與分層已定、只管 Riverpod 端怎麼把它接對。

## 下一步

圖的邊界都守住之後，剩下的深化方向各有一篇 case 可讀：容器與作用域的空間問題在 [雙容器狀態脫節](/work-log/flutter_riverpod_dual_container_state_desync/)、涵蓋缺口的補償演進在 [ref.watch 觀察的是 provider 圖](/work-log/flutter_riverpod_reactive_boundary_ref_watch/)、接入實作在 [StreamProvider 包 repository watch stream](/work-log/flutter_streamprovider_wraps_repository_watch/) 與 [StreamController single vs broadcast](/work-log/dart_stream_controller_single_vs_broadcast/)、生命週期在 [await 回來的時候、頁面已經關了](/work-log/flutter_unmounted_ref_async_gap/)。理論地基從 [DDD 指南的讀側與觀測路線](/ddd/) 進。
