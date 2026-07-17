---
title: "無測試 legacy 專案的起步順序"
date: 2026-07-17
description: "接手零測試的專案、有限預算下第一批測試該從哪一層開始建——按風險集中處判斷起步路徑，而非照測試金字塔從底部往上疊"
weight: 7
tags: ["testing", "legacy", "strategy", "migration", "characterization-test"]
---

接手一個沒有任何測試的專案，團隊能投入的測試時間有限。第一條測試寫什麼，決定的是接下來幾個月的投資回報走向——寫對了，每條新測試都在降低最高風險區的暴露面；寫錯了，測試數量在增長但攔截能力沒有對準系統的脆弱處。

這裡回答的是「投資順序」。值不值得在既有程式碼上加測試（相對於重寫）是更上游的判斷，[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)的「結構界限與適用判準」段有討論不同規模的取捨。

## 判斷起步層的自查

測試策略的三層——unit、protocol integration、screen state——每層的投資回報取決於風險集中在哪裡。照測試金字塔從 unit 開始往上疊是一種預設路徑，但 legacy 專案的風險分布很少均勻：某些系統的風險集中在內部邏輯、某些集中在外部互動、某些集中在流程編排。起步層對準風險集中處，每條測試的邊際收益最高。

三個自查問句幫助定位風險集中處：

### 過去半年的 bug 報告集中在「算錯」還是「連錯」？

- 算錯（金額計算、狀態轉換、資料轉換的錯誤）→ 風險在內部邏輯，unit test 的攔截面最大
- 連錯（API 回應格式改了沒跟上、認證握手失敗、訊息格式不相容）→ 風險在外部互動，protocol integration test 的攔截面最大

### 系統的正確性有多大程度取決於「我們對外部服務行為的假設」？

- 系統主要依賴自己的計算和規則 → unit test 先行
- 系統的核心價值在「跟第三方服務的互動」（支付閘道、物流 API、認證服務）→ protocol integration test 先行，確保互動契約正確

### Bug 是在哪個層面被使用者發現的？

- 使用者回報的是「按了按鈕沒反應」「畫面顯示的跟預期不同」→ 風險在 UI 行為與導航，screen state 驗證先行
- 使用者回報的是「資料不對」「扣款金額錯」→ 風險在底層邏輯，往 unit 或 protocol integration 定位

三個問句不互斥——一個系統可能同時在內部邏輯和外部互動都有高風險。此時選風險造成的業務損害更大的那一端先投資。

## 三種起步路徑

### 路徑一：Unit test 先行

**適用情境**：系統有複雜的業務邏輯（計價規則、權限判斷、狀態機轉換），而且這些邏輯的輸入輸出邊界可辨識——函式簽名清楚、依賴可注入或可隔離。

**起步策略**：從失敗代價最高的業務邏輯開始。不是從最容易測的函式開始——最容易測的通常是工具函式（字串處理、日期轉換），它們的失敗代價低。找到「算錯了會直接造成客訴或財損」的邏輯區塊，從那裡寫第一批 unit test。

**常見阻力與對策**：legacy 程式碼的依賴常常是纏結的（一個計價函式裡面直接呼叫資料庫、呼叫外部 API、讀取全域狀態）。逐步解耦是理想做法，但前幾條測試不需要完美的依賴注入——用 monkey patching、module-level mock、或 subclass override 先把依賴隔開，換到第一批測試能跑。架構層面的重構在有測試保護之後再做，順序反過來（先重構再測試）會讓重構本身失去安全網。

**接續路由**：unit test 建立起對內部邏輯的攔截後，下一步判斷是否需要 [protocol integration test](/testing/03-protocol-integration-test/definition-and-boundary/) 補上外部互動的盲區。判準：[mock 遮蔽機制](/testing/01-test-strategy-layers/mock-masking-mechanism/)描述的哪些問題在這個專案可能成立。

### 路徑二：Protocol integration test 先行

**適用情境**：系統的核心價值是整合——聚合多個外部服務的資料、轉發訊息到不同通道、對第三方 API 做操作。內部邏輯相對薄（主要是組請求和轉格式），風險集中在「跟外部服務的契約是否正確」。

**起步策略**：盤點系統連接的所有外部服務，按兩個維度排序——變動頻率和失敗影響。變動頻率高（API 版本升級快、回應格式常改）且失敗影響大（付款、認證、核心資料同步）的服務，優先寫 protocol integration test。

**可行性前提**：外部服務需要一個可測試的環境——sandbox、staging、或可在本機啟動的服務實例。如果外部服務沒有測試環境（某些第三方 API 只提供生產環境），protocol integration test 的成本會大幅上升；這時候先用 [HTTP contract test](/testing/03-protocol-integration-test/http-contract-test/) 對著 API 文件寫 schema 驗證，以契約測試替代。

**接續路由**：protocol integration test 確認外部契約後，回頭用 unit test 補內部邏輯的覆蓋。測試策略的[三層定義](/testing/01-test-strategy-layers/three-layer-definition/)描述了每層的職責與盲區。

### 路徑三：流程測試先行

**適用情境**：系統的風險集中在「多個服務的接力」——前端收到使用者輸入後，經過多個服務處理（驗證、計算、外部呼叫、狀態更新、通知），最終結果正確要求整條鏈都正確。單獨測任何一層，攔截率都偏低。

**起步策略**：找到一條「出錯頻率最高」或「出錯後果最嚴重」的業務流程，把它寫成一個端到端的流程測試——從編排入口驅動整條服務鏈。如果被測編排可以從 UI 層抽離（[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)的「可測性閘門」段描述了判定方法），走 subcutaneous test 形態；抽不出來就走 E2E。

**代價意識**：流程測試的建置和維護成本高於 unit test 和 protocol integration test。Legacy 專案的編排通常跟 UI 框架、全域狀態、平台依賴交織在一起，拆開接縫的前置工程量大。如果第一條流程測試的建置超過預估時間的兩倍，回到路徑一或路徑二先建低成本的攔截——有部分覆蓋比沒有覆蓋好。

**接續路由**：流程測試建立後，用 unit test 覆蓋流程中各段服務的內部邏輯——流程測試紅燈時，有 unit test 才能快速定位是哪一段出問題。定位成本的討論見[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)的「結構界限與適用判準」段。

## 遷移安全網：先有 characterization test 再改

三種路徑都涉及一個共同的操作風險：在沒有測試保護的程式碼上做改動（加測試本身常常需要調整程式碼結構——提取函式、注入依賴、暴露接縫）。Characterization test 是這個操作的安全網。

Characterization test 鎖住的是「現在的行為」，不關心行為是否正確。寫法是對著現有程式碼跑一次、把輸出記錄下來當預期值。改動後全綠代表「行為沒變」，紅燈代表「行為改了」——紅燈不一定是 bug，但它告訴你改動的影響範圍。

這個工具在 legacy 專案起步階段的價值在於降低重構風險：要把纏結的依賴拆開才能寫 unit test，但拆的過程可能改壞現有行為——characterization test 先鎖住行為，讓拆解有安全網。拆完、unit test 寫好後，characterization test 的歷史使命完成，可以視重疊程度逐步移除。兩者的職責分界：characterization test 斷言「行為不變」，unit test 斷言「行為正確」——混在一起會讓紅燈無法歸因是「行為改了」還是「行為本來就錯」。實作經驗與平台依賴的處理見 [characterization test 當遷移安全網](/work-log/flutter_characterization_test_migration_safety_net/)。

## 下一步路由

- 測試三層各自的職責與盲區 → [測試策略三層定義](/testing/01-test-strategy-layers/three-layer-definition/)
- Mock 遮蔽機制（為什麼 unit test 有結構性盲區）→ [Mock 遮蔽機制](/testing/01-test-strategy-layers/mock-masking-mechanism/)
- 語意級假後端的適用判準 → [語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)
- Characterization test 實作經驗 → [characterization test 當遷移安全網](/work-log/flutter_characterization_test_migration_safety_net/)
- Protocol integration test 的定義與邊界 → [Protocol integration test 定義](/testing/03-protocol-integration-test/definition-and-boundary/)
