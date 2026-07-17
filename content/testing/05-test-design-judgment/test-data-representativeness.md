---
title: "Test data 代表性"
date: 2026-06-19
description: "手寫 vs 錄製 vs 生成三種測試資料來源 — 測試資料的代表性是一個隱性假設，決定了 test 能發現什麼問題"
weight: 2
tags: ["testing", "test-data", "parser", "representativeness", "ansi"]
---

測試資料的代表性是指測試輸入能多大程度反映真實環境的輸入分佈。「測試資料能代表真實環境」是每個 test 的隱性假設 — 這個假設成立時 test 有效，不成立時 test 通過但問題仍在。

## 代表性問題的案例

一個遠端終端機 app 的 ANSI parser 有 18 個 test，全部通過。測試資料是手寫的 SGR 色彩碼（`\x1B[31mhello\x1B[0m`），parser 正確解析這類序列。

真實 zsh 啟動後送出的控制序列包含 OSC 標題設定、CSI private mode、字元集指定等至少 5 種類型。Parser 只認識 SGR，其他全部透傳為亂碼（[T.C3](/testing/cases/ansi-parser-test-data-blindspot/)）。

18 個 test 覆蓋了 1 種序列類型。測試資料的代表性假設（「SGR 就是主要的序列類型」）和真實環境不符。

## 三種測試資料來源

### 手寫

開發者根據對輸入格式的理解手動建構測試字串。

優點：精確控制、容易理解、可以針對特定邊界條件設計。

缺點：受限於開發者對輸入分佈的認知。如果開發者不知道真實環境有哪些輸入類型，手寫的測試資料就是開發者認知的子集 — T.C3 就是這個模式。

適合場景：格式規格明確且有限（JSON schema、固定格式的設定檔）、邊界條件測試（空值、最大長度、特殊字元）。

### 錄製

從真實環境擷取實際的輸入資料，作為 test 的輸入。

優點：直接反映真實環境的輸入分佈，包含開發者不知道的輸入類型。

缺點：錄製的資料可能包含敏感資訊（需要脫敏）、資料量可能大（需要挑選代表性樣本）、真實環境的輸入可能隨時間改變（錄製的資料可能過時）。

適合場景：輸入格式複雜且規格不完整（終端機 escape 序列、網路封包、使用者產生的內容）、parser 類的功能（需要知道「真實輸入長什麼樣」）。

T.C3 如果用錄製的真實 zsh 啟動輸出作為測試資料，OSC 和 CSI private mode 會自然出現在輸入中。即使 parser 仍然不處理這些序列，test 至少能讓開發者看到「有 5 種序列類型，我只處理了 1 種」。

### 生成（Property-based testing）

用 generator 自動產生大量隨機或半隨機的輸入，驗證 parser 的行為是否符合通用性質（不崩潰、輸出長度 <= 輸入長度、冪等性）。

優點：覆蓋人類想不到的 edge case、發現意外的崩潰或無限迴圈。

缺點：不針對特定功能驗證（驗證的是通用性質，不是「OSC 序列是否被正確處理」）、generator 本身需要維護。

適合場景：parser、serializer、codec 等輸入格式複雜的功能。和手寫 test 互補 — 手寫驗證特定行為正確性，生成驗證通用穩定性。

## 兩類 test 的分工

T.C3 的策略建議是把 test 分成兩類：

**功能正確性 test**：用手寫乾淨字串驗證 parser 對已知序列的處理正確性。`\x1B[31mhello\x1B[0m` 應該產生紅色 token — 這是功能規格的驗證。

**環境相容性 test**：用錄製的真實輸出驗證 parser 在真實環境中的表現。不斷言「每個序列都被正確處理」，而是斷言「沒有崩潰」「沒有未處理序列殘留在可見輸出中」。

兩類 test 回答不同問題。功能正確性回答「parser 的邏輯對不對」，環境相容性回答「parser 在真實環境中夠不夠用」。

## 下一步路由

- Assertion 的品質判斷 → [Assertion 品質三問](/testing/05-test-design-judgment/assertion-quality/)
- Mock 邊界的判斷 → [Mock 邊界判斷決策表](/testing/05-test-design-judgment/mock-boundary-decision/)
- Protocol integration test 用真實服務輸出 → [testing 模組三 WebSocket 協議測試](/testing/03-protocol-integration-test/websocket-protocol-test/)
