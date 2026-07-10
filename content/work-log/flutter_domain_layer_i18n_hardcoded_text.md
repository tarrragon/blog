---
title: "Domain 層的 947 處硬編碼中文 — 訊息代碼跟顯示文字的分層責任"
date: 2026-07-10
draft: false
description: "domain 層的 enum 或 getter 直接回傳 UI 顯示字串時，多語言支援與分層原則同時失守。修法是 domain 只回訊息代碼與結構化資料、UI 層用 translator extension 翻譯；遷移排序從最小模組先行驗證模式。適用於盤點「這個字串屬於領域事實還是呈現」的情境。"
tags: ["flutter", "dart", "i18n", "ddd", "layered-architecture", "refactoring"]
---

> **觸發場景**：Flutter 專案要上多語言，盤點後發現 Domain 層有 947 處中文硬編碼——`enum IssueType { missingTitle('缺失標題') }` 這類寫法散在七個模組
> **疑問來源**：這些字串當初寫起來很自然（enum 帶個顯示名稱、result 物件帶個 summary），為什麼會變成架構問題？
> **整理目的**：記下「訊息內容」與「訊息文字」的分層責任劃分、以及大量硬編碼的遷移策略
> **本文邊界**：素材是一個 Flutter 書籍管理 App 的重構記錄（第一個模組完成時的狀態）；分層原則語言無關、translator extension 是 Dart 的實作載體

---

## 947 處是怎麼長出來的

硬編碼不是一次寫壞的，是每一處都很合理地長出來的。典型形態：

```dart
// Domain 層
enum IssueType {
  missingTitle('缺失標題'),   // UI 文字在 Domain 層
  ...
}
```

enum 定義同步問題的類型，順手帶上顯示名稱——單獨看每一處都是便利的選擇：呼叫端要顯示時直接取，少一層轉換。同樣模式的還有 `SyncResult.summary` 這種直接組出中文句子的 getter、以及 value object 上的 `displayName` 屬性。七個模組累積下來的分佈：synchronization 25 處、import 46、search 47、export 52、scanner 82、version_management 90、library 563。

問題在多語言需求出現時一次引爆：文字寫死在 Domain 層，翻譯就得改 Domain——而 Domain 層理應對「呈現給誰、用什麼語言」一無所知。

## 劃分判準：領域事實 vs 呈現

修法的核心是把每個字串問一次：**這是領域事實、還是呈現？**

「這筆書目缺標題」是領域事實——同步檢查的產出、業務邏輯的分支依據。「缺失標題」四個中文字是呈現——同一個事實在英文介面叫 missing title。兩者的變動理由不同（業務規則 vs 語言與文案），依變動理由分層：

```dart
// Domain 層：只有代碼
enum SyncIssueCode {
  missingTitle('MISSING_TITLE'),
  ...
}

// UI 層：translator extension
extension SyncIssueCodeTranslator on SyncIssueCode {
  String toLocalizedTitle(AppLocalizations l10n) {
    switch (this) {
      case SyncIssueCode.missingTitle:
        return l10n.syncIssueMissingTitle;   // 翻譯在 UI 層
    }
  }
}
```

exhaustive switch 讓這個橋接有編譯期保證：Domain 新增一個代碼、UI 層的 translator 沒跟上就編譯失敗——兩層的同步靠型別系統守、不靠人記得。

## 組合訊息的拆法：結構化資料取代成品字串

純代碼替換解決不了所有 947 處。有些字串是組合出來的——「同步完成，3 筆受影響」這種帶數量的訊息，Domain 層原本直接回成品字串。重構的處理是把**資料**跟**模板**拆開：

- `CheckResult.message` 改成 `messageCode`（枚舉）、新增 `affectedCount` 屬性——數量是領域事實、由 Domain 提供
- `SyncResult.summary`（回中文字串的 getter）移除、改成 `resultCode` 加 `summaryData`（結構化資料）——句子怎麼組、單複數怎麼變化，是 UI 層拿著資料跟 arb 模板的事

判讀方式：Domain 層的職責邊界劃在「提供組句需要的全部事實」，句子本身屬於呈現層。

## 遷移策略：從最小模組先行

七個模組的處理順序按硬編碼數量由少到多：synchronization（25 處）先做、library（563 處）最後。第一個模組承擔的是**驗證模式**——6 個代碼枚舉怎麼切、translator extension 怎麼組織、arb 鍵怎麼命名、測試怎麼跟著改，全套模式在最小的模組上走通（103 個相關測試全過），後面六個模組就是重複已驗證的模式。反過來從 563 處的 library 開刀，模式還沒定就得承擔最大的返工面。

測試的連動也在第一個模組現形：直接斷言中文字串的測試（`expect(issue.description, '缺失標題')`）全部要改成斷言枚舉。這類測試本來就把呈現細節烤進了斷言——重構把它們一併修正成對領域事實的斷言。

## 判讀徵兆

- Domain 層的 enum 建構子參數是給人看的自然語言（而不是代碼常數）
- value object 或 result 物件上有 `displayName`、`summary`、`message` 這類回傳成句文字的成員
- 測試斷言裡出現 UI 文案字串
- 多語言需求評估時，翻譯範圍清單裡出現 domain 目錄

四個訊號指向同一件事：呈現知識滲進了領域層，多語言只是讓它現形的第一個下游需求——文案改版、A/B 測試文案、依角色顯示不同措辭，都會撞上同一堵牆。

## 相關閱讀

- 方法論全貌：[業務層 i18n 管理方法論](/record/business-layer-i18n-management-methodology/)——本文是該方法論在 Domain 層的實機重構記錄
- 概念地基：[DDD 領域驅動設計指南](/ddd/) 的分層責任章節
- 同族判準：[copyWith 是逃生口，不是設計](/work-log/dart_copywith_entity_escape_hatch/)——兩篇的共同結構是「每一處都便利的局部選擇、累積成架構問題」，差別在洩漏方向（呈現滲入領域 vs 變更繞過領域）
