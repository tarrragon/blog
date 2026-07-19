---
title: "有狀態假後端用真實模型序列化回應：手寫 JSON fixture 會重踩產品已解決的問題"
date: 2026-07-17
draft: false
description: "流程測試的假後端持有 freezed 模型物件、以 toJson 序列化回應，讓服務層走完整的反序列化鏈。對照組是手寫 JSON fixture——同一批測試裡的 raw 寫法重踩了一次產品早已內建處理的分頁包裝，證明「回應形狀的知識」應該只存在一份。"
tags: ["flutter", "dart", "test", "freezed", "fixture", "fake-backend", "serialization"]
---

> **核心議題**：假後端的回應資料從哪來？手寫 JSON 字串、還是建構真實模型物件再 `toJson()`？POS App 的[流程測試](/testing/knowledge-cards/flow-test/)選了後者，理由不是美觀——是「後端回應形狀的知識」在專案裡應該只有一份（產品的模型解析層），fixture 自己再寫一份就會分岔。
> **案例骨幹**：有狀態假後端以 freezed 模型（單據、明細、記錄）持有狀態、handler 用 `copyWith` 演變狀態、出口一律 `toJson()`。同一時期另一批用 raw JSON 手刻請求的測試，重踩了「列表回應帶分頁包裝」的問題——產品的回應信封解析早就內建了這層 unwrap，手刻等於把已解決的問題再解一次。

---

## 1. 假後端的回應出口：物件 → toJson，不是字串樣板

有狀態假後端攔在 HTTP adapter 層，對每個端點回放狀態。回應的組裝方式：

```dart
// 狀態就是真實模型物件
List<Cart> carts;
List<Record> records;

// 出口統一序列化——服務層拿到的 JSON 與真實後端同構
if (isCartList(request)) {
  return envelope([for (final c in carts) c.toJson()]);
}
```

freezed 模型天生雙向（`fromJson`/`toJson`），這保證了一個閉環：**假後端 seed 的物件 → toJson → 服務層 fromJson → 前端邏輯**，服務層走的解析路徑與生產環境完全相同。手寫 JSON 樣板跳過的正是這個閉環的前半段——樣板對不對，靠人眼比對 API 文件。

## 2. 對照組事故：raw 手刻重踩分頁包裝

同一時期，另一批對真實後端發請求的測試最初用 raw JSON 手刻（自組請求、手挖回應欄位）。首跑失敗：

```text
type '_Map<String, dynamic>' is not a subtype of type 'List<dynamic>'
```

真實後端的列表端點帶分頁包裝——`data` 不是陣列，是 `{ data: [...], previousPage, nextPage, ... }`。而產品的回應信封模型**早就內建**了「嘗試解分頁包裝」的邏輯，生產 App 天天在正確處理這個形狀。raw 寫法等於把一個已解決的問題重新發現、重新修補（在測試裡加了一個 `_listData` helper）——直到改用產品的 API client 與模型解析，這個 helper 連同它代表的重複知識一起刪除。

教訓一句話：**回應形狀的知識只該存在一份**。fixture 或測試裡出現第二份（手寫 JSON、手挖欄位），它與第一份的分岔只是時間問題。

## 3. 狀態演變用 copyWith，行為住在 handler

有狀態假後端與「回放固定回應的 stub」的分水嶺在於它模擬後端動詞的效果。freezed 的 `copyWith` 讓這件事保持宣告式：

```dart
// 「合併」的效果：明細全部換新 id、記錄改掛新單據
final newDetails = [for (final d in old.details) d.copyWith(id: newId())];
records = [for (final r in records) r.copyWith(parentId: mergedId)];
```

每個 handler 頭上一句話描述它模擬的後端行為（來源是實測證實，不是猜測）；測試 seed 初始物件、跑真實服務鏈、斷言假後端的狀態變化與前端的對齊結果。方法論層的完整討論見[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)。

## 4. 邊界：toJson 回放的前提是模型忠實

這個做法有一個隱含前提：**產品模型的 `fromJson`/`toJson` 對真實後端是忠實的**。若模型本身漏了欄位、轉換器不對稱，假後端的閉環會把錯誤一起閉進去——測試綠、對真實後端壞。補這個洞的是配對的[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)：它走同一套模型打真實環境，模型與後端的形狀分岔會在那裡現形（分頁包裝那次事故正是被它抓到的）。

## 5. 可複用的判準

1. 假後端／fixture 的回應一律「建構模型物件 → toJson」，不手寫 JSON 字串。
2. 測試裡出現「手挖回應欄位」的 helper（`data['data']` 之類）＝重複知識的訊號，改走產品解析層。
3. 有狀態假後端的狀態演變用 `copyWith` 在 handler 裡宣告式完成，一個 handler 對應一條已證實的後端行為。
4. toJson 回放閉環的忠實性由真實後端驗證測試把關——兩者是配對關係，不是二選一。

## 下一步

- 方法論層 → [語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)
- 配對的驗證層 → [真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)
- freezed 模型設計的機制層 → [Freezed 三層結構解剖](/work-log/dart_freezed_anatomy/)
