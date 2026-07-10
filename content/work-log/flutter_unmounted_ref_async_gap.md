---
title: "await 回來的時候、頁面已經關了 — UnmountedRefException 與 16 個不抽象的檢查點"
date: 2026-07-10
draft: false
description: "長 async 流程的每個 await 都是一個 gap：等待期間使用者可能離開、Notifier 被 dispose、回來再寫 state 就炸 UnmountedRefException。修法是每個 gap 後檢查 ref.mounted——而且刻意不抽成 helper：明確的檢查點讓 review 看得見哪個 gap 有守。含「評估必跑、可決定不重構」的技術債處置。"
tags: ["flutter", "dart", "riverpod", "async", "lifecycle", "state-management"]
---

> **觸發場景**：Flutter 書籍管理 App 的批量匯入——一條會跑很久的 async 流程。使用者中途離開頁面，流程裡下一個 `state = ...` 拋出 `UnmountedRefException`：ViewModel 已經被 dispose、`ref` 不能再用
> **疑問來源**：修復加了 16 個 `if (!ref.mounted) return;`——這麼多重複的檢查、不該抽成一個 helper 嗎？重構評估的答案是不該，為什麼？
> **整理目的**：記下 async gap 的生命週期機制、檢查點的擺放規則、以及「重複但刻意不抽象」的判斷
> **本文邊界**：素材是該專案 v0.25.1 的修復與 Phase 4 重構評估記錄；`ref.mounted` 是 Riverpod 的 API、「await 前後是兩個世界」的機制跨框架成立

---

## 機制：await 前後是兩個世界

同步程式碼裡「this 活著」是全程成立的前提；async 函式裡這個前提**在每個 `await` 處斷開一次**。批量匯入的流程長這樣：逐本書處理、每本有儲存的 await、批次間有讓出控制權的 await——每一個 await 都把控制權交還 event loop，而 event loop 上可能正排著「使用者按了返回、頁面 dispose、Notifier 跟著 dispose」。

await 回來之後的程式碼，跑在一個「自己可能已經死了」的世界裡。讀區域變數沒事、但碰 `ref`（寫 state、讀 provider）就是對已釋放資源的操作——Riverpod 用 `UnmountedRefException` 把這個錯誤變成显式的炸點（比靜默寫入無人監聽的狀態誠實）。修法就是在每次 await 之後、要碰 `ref` 之前重新確認世界還在：

```dart
await _saveBook(book);
if (!ref.mounted) return;          // await 後、碰 ref 前
state = state.copyWith(processedBooks: progress.processed);
```

檢查點的擺放規則可以機械化：**每個 await 之後、第一次碰 `ref` 之前**。這次修復落了 16 個檢查點——對應這條流程的 16 個 async gap，漏任何一個就留下一條「使用者恰好在那個瞬間離開」的崩潰路徑。

## 刻意不抽象：重複、但每個重複都有座標

16 個一模一樣的 `if (!ref.mounted) return;` 天然引來「抽成 helper」的重構衝動。Phase 4 評估把它列為候選、然後**否決**，理由三條照錄：

> 1. 抽取為 helper 會增加複雜度；2. 明確的檢查點有助於程式碼審查；3. 這是 Flutter 社群的推薦實踐。

第二條是核心。這種 guard 的價值不在「做了什麼」（一行 return）、在「**它在哪**」——review 一段 async 流程時，審查的問題是「每個 gap 之後有沒有守」，明確的檢查點讓這件事用眼睛掃就能驗證；包進 helper（或用 zone、攔截器之類的魔法）之後，「哪個 gap 有守」變成要追實作才知道。重複的成本（16 行樣板）換明確性的收益，這筆帳在 guard 這類「位置即語意」的程式碼上是划算的——跟 [DRY 在別處的正確性](/work-log/flutter_duplicate_service_fake_coverage/)不矛盾：那裡重複的是**行為**（兩份 API 實作會分歧）、這裡重複的是**哨位**（每個位置本來就該有一個）。

第三條也值得停一秒：社群標準模式的地位跟 [mock 基礎設施那篇](/work-log/flutter_mock_infrastructure_overengineering_deleted/)的教訓相通——生態已收斂的做法、自建「更優雅」的抽象前先想清楚要解的是誰的問題。

## 評估必跑、可決定不重構

這份記錄的第二個看點是流程形態。Phase 4 重構評估**必須執行**、但結論可以是「不重構」：本次評分 B、識別出兩筆技術債（88 行的 `_executeImport`、重複五次的錯誤處理模式）、決策是「品質達標、債務記錄、排入下個重構週期」。

這個形態把兩件常被混在一起的事分開了：**評估的義務**（每次改動後都要看一眼品質）跟**執行的判斷**（現在修還是排程修）。混在一起的版本要嘛「評估完就得修」（每張票膨脹）、要嘛「不修就不評估」（債務靜默累積）。而這裡的技術債記錄不是垃圾桶——TD-012（88 行函式）在下一個版本真的被清償了、清償的過程就是[函式分解那篇](/work-log/flutter_function_decomposition_split_vs_keep/)的拆分 case。從識別、記錄、排程到清償的完整鏈條，是「記錄技術債」這個動作有意義的前提。

## 判讀徵兆

- 崩潰 stack 指向 async 函式裡 await 之後的 state 寫入 / ref 操作——async gap 沒守，順著函式把每個 await 之後補檢查
- 流程越長、頁面越可離開（匯入、同步、批次處理），gap 風險越高——這類 ViewModel 寫完先數 await、對照數 mounted 檢查
- 想把 guard 抽成 helper——先問「review 時需不需要看見每個哨位」；位置即語意的程式碼、明確勝過 DRY
- 重構評估產出「不重構」卻沒有債務記錄——評估白跑了；「不修」的合法形式是「記錄 + 排程」

## 相關閱讀

- 債務清償的下文：[88 行拆成 13 個函式](/work-log/flutter_function_decomposition_split_vs_keep/)——本文識別的 TD-012 在下個版本的清償實錄
- 同框架的生命週期家族：[雙容器狀態脫節](/work-log/flutter_riverpod_dual_container_state_desync/)——那篇是容器的空間邊界、本文是 Notifier 的時間邊界
- build 階段的對偶：全域錯誤處理器在 widget tree 建置中改 provider 的崩潰（v0.9 的 microtask 延後修法）——await 之後太晚、build 之中太早，`ref` 的合法視窗兩頭都有界
