---
title: "設計階段的品質閘門：C1/C2/C3 在寫程式之前擋下來"
slug: "code-smell-quality-gate-methodology"
date: 2026-03-04
draft: false
description: "Ticket 的職責不清與範圍過大要到實作階段才浮現時，用來在文字階段就判定過大、模糊、不完整三種缺陷"
tags: ["AI協作心得","Ticket","方法論"]
---

Ticket 的職責不清、範圍過大這兩種缺陷，在文字階段修正的動作是改幾行描述，在實作階段修正的動作是改已經寫好的程式碼與測試。同一個缺陷，兩個階段的修正成本差在被它影響的產出量。

設計階段品質閘門把判定移到前面：**Ticket 進入 Phase 2 之前強制執行 C1/C2/C3 三項檢測。**

<!--more-->

## 三層檢測標準

**C1 God Ticket**：超過 10 個檔案、跨越超過 2 個架構層、或預估超過 16 小時，判定過大，必須拆分。

**C2 Incomplete Ticket**：驗收條件少於 3 個可量化項目、缺少測試規劃、未定義工作日誌名稱、無參考文件連結——任一缺失，Ticket 不完整。

**C3 Ambiguous Responsibility**：標題缺少層級標示（如 `[Layer 5]`）、目標含複合職責（出現「和」或「或」）、步驟寫「相關檔案」而非具體路徑、驗收條件跨層——任一模糊，需重新定義。

## 檢測順序由作廢關係決定

固定執行順序：**C1 → C3 → C2**。

C1 最先，因為判定為 God Ticket 之後拆分會產生多張新 Ticket，先做的 C2/C3 分析全部作廢。C3 排第二：職責不清的 Ticket，補出來的驗收條件也會是模糊的。C2 最後，在範圍合理、職責明確的基礎上確認必要元素齊全。

## 執行流程

### Step 1：C1 God Ticket 檢測

從 Ticket 的步驟章節提取所有檔案路徑，計算檔案數量。接著用檔案路徑判斷每個檔案所屬的架構層：

- `lib/presentation/widgets/`、`lib/presentation/pages/` 屬於 Layer 1（UI 層）
- `lib/presentation/controllers/`、`lib/presentation/view_models/` 屬於 Layer 2（行為層）
- `lib/application/use_cases/`、`lib/application/services/` 屬於 Layer 3（UseCase 層）
- `lib/domain/repositories/`（介面）、`lib/domain/events/` 屬於 Layer 4（Domain 介面層）
- `lib/domain/entities/`、`lib/domain/value_objects/`、`lib/infrastructure/` 屬於 Layer 5（Domain 實作層）

層級跨度是最高層減最低層。檔案分佈在 Layer 1 到 Layer 5 時跨度為 4，超過上限 2。

預估工時由步驟數量與複雜度係數估算：步驟數 × 平均每步時間 × 複雜度係數（1.0 到 2.0）。

檢測失敗時依序嘗試三種拆分策略：

1. 按層級拆分（優先）：跨層的 Ticket 按架構層拆成多張
2. 按職責拆分（次要）：工時過長的 Ticket 按職責邊界拆
3. 按功能模組拆分（最終）：職責過多的 Ticket 按功能模組拆

拆分後的每張子 Ticket 重新執行 C1 檢測。

### Step 2：C3 Ambiguous Responsibility 檢測

確認四個要素：

- **層級標示**：標題包含 `[Layer X]` 標籤
- **職責描述**：目標章節沒有「和」或「或」的複合描述
- **檔案範圍**：步驟列出具體路徑，而非「相關檔案」
- **驗收限定**：驗收條件不出現跨層項目

任一不符，依序修正：明確層級 → 重寫職責 → 列出具體檔案 → 限定驗收範圍。

### Step 3：C2 Incomplete Ticket 檢測

確認四個必要元素都存在：

- **驗收條件**：3 個以上可量化、可驗證的項目（「程式碼品質提升」這種描述不算）
- **測試規劃**：明確的測試檔案路徑與對應的測試項目
- **工作日誌**：定義好工作日誌的檔案名稱（而非「待填寫」）
- **參考文件**：至少 1 個有效的文件連結

缺哪個補哪個。

### Step 4：提交審查

所有 Ticket 通過 C1/C2/C3 之後，生成品質閘門檢測報告，作為進入 Phase 2 的依據。

## 阻斷機制與執行時機

任何 Ticket 未通過 C1/C2/C3，**禁止進入 Phase 2**。判定結果與修正過程寫入工作日誌。

執行時機有三個：設計完成後立即檢測、分派前確認報告、審查時以報告作依據。三個時機缺一不可——缺任何一個，未檢測的 Ticket 就有一條路徑可以進到實作。

## 這個位置換到的是什麼

Ticket 進入實作時已經有明確範圍、清楚職責、具體驗收標準，實作階段不必再回頭確認這些。

閘門本身也因為位置而更容易被遵守：修正成本低的時候，照規則修是最省事的選項；修正成本一旦高起來，繞過規則、局部修正、把問題記成待辦，每一個都比照做便宜——閘門會在那個時候開始失效。

C1 判定要拆分之後怎麼拆，走 [Atomic Ticket 方法論](../atomic-ticket-methodology/)；閘門的判定何時該由 hook 自動執行，走 [用 Hook 把開發規範變成自動執行的基礎設施](../agile-hook/)。
