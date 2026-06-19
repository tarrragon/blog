---
title: "T.C3 ANSI parser 測試資料不覆蓋真實 shell output"
date: 2026-06-19
description: "ANSI parser 只處理基本 SGR 色彩碼、unit test 用手寫乾淨字串驗證 — 真實 zsh prompt 送出 OSC 標題設定、CSI private mode 游標隱藏、括號貼上模式等數十種控制序列，全部殘留為亂碼"
weight: 3
tags: ["testing", "case-study", "ansi", "parser", "test-data", "terminal"]
---

這個案例的核心責任是說明 unit test 的輸入資料品質如何決定測試的有效性。Parser 邏輯正確、斷言正確、覆蓋率高 — 但測試資料是人工挑選的乾淨子集，跟真實環境的輸入分佈不同。

## 觀察

app_tunnel 的 `AnsiParser` 負責解析終端機輸出的 ANSI escape 序列，轉換為帶色彩的文字 token。unit test 用手寫字串驗證：

```dart
// 測試資料範例 — 乾淨的 SGR 色彩碼
test('紅色文字', () {
  final tokens = parser.parse('\x1B[31mhello\x1B[0m');
  expect(tokens.first, isA<TextToken>());
});
```

真實 zsh prompt 啟動後送出的控制序列（擷取自實機 log）：

```
\x1B]0;user@host: ~\x07          ← OSC：設定終端機視窗標題
\x1B[?2004h                      ← CSI private mode：啟用括號貼上模式
\x1B[?1h                         ← CSI private mode：啟用應用程式游標鍵
\x1B(B                           ← 字元集指定：選擇 ASCII
\x1B[?25l                        ← CSI private mode：隱藏游標
```

Parser 只認識 `\x1B[{數字;數字}{字母}` 格式的標準 CSI，其他全部殘留在輸出中。

| 指標               | 值                                                    |
| ------------------ | ----------------------------------------------------- |
| 測試案例數         | 18 個 AnsiParser test，全過                           |
| 測試覆蓋的序列類型 | SGR 色彩碼（`\x1B[31m` 等）                           |
| 真實環境的序列類型 | SGR + OSC + CSI private mode + 字元集指定 + 其他      |
| 實機表現           | 終端機畫面散佈 `]0;user@host` 等亂碼片段              |
| 修復               | 新增 3 個 RegExp 過濾 OSC / CSI private / 其他 escape |

## 判讀

1. **測試資料的代表性是隱性假設**。18 個 test 的斷言都正確 — `\x1B[31m` 確實應該產生紅色 token。但「測試輸入能代表真實輸入」是一個未經驗證的假設。真實 zsh 的輸出包含 5+ 種 escape 序列類型，測試只覆蓋了 1 種。

2. **Parser 的行為對未知序列是「透傳」而非「報錯」**。這是合理的設計 — 不認識的序列不應該讓 parser 崩潰。但透傳的後果是亂碼靜默出現在畫面上，不觸發任何錯誤或 log，開發者在 unit test 環境完全不會察覺。

3. **手寫測試資料 vs 錄製真實資料**。如果測試資料是從真實 shell session 錄製的（capture 一次真實 zsh 啟動輸出），OSC 和 CSI private mode 會自然出現在測試輸入中，parser 的透傳行為會在 test 階段就被看到。

## 策略

1. **從真實環境錄製測試資料**：用 `script` 命令或 WebSocket log 錄一次真實 shell session 的完整輸出，作為 integration test 的輸入。即使不改 parser 邏輯，至少能看到「哪些序列被透傳了」。
2. **Parser 對未知序列記 warning log**：透傳是合理的 fallback，但加一行 `developer.log('Unknown escape: ${escape.codeUnits}')` 讓開發者知道有未處理的序列。
3. **測試分兩類**：「功能正確性」用手寫乾淨字串；「環境相容性」用錄製的真實輸出。兩類測試回答不同問題。

## 下一步路由

- 想理解測試資料代表性 → [模組五：測試設計判斷](/testing/)
- 想建 protocol integration test 用真實 ttyd 輸出 → [模組三：協議整合測試](/testing/)
- 類似案例（mock 遮蔽） → [T.C1 WS frame type mock 遮蔽](/testing/cases/ws-text-binary-frame-mock-blindspot/)
