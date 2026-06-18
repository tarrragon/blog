---
title: "spurious warning：linter 的偽警告"
slug: "spurious-warning"
date: 2026-06-18
description: "spurious warning 指靜態分析或編譯器報的警告，但其實沒有問題，是 linting / 編譯領域的 false positive。常因規則過嚴或分析器無法證明安全而起"
tags: ["til", "術語", "跨領域", "spurious-warning"]
---

spurious warning（偽警告）指**靜態分析、linter 或編譯器報了一條警告，但其實沒有問題**——是 linting / 編譯領域的 [false positive](../false-positive/)。

## 常見成因

- 規則訂得過嚴，把合法寫法也圈進去。
- 分析器無法**證明**某段安全，於是保守地報警（寧可誤報也不漏報）。
- 規則的比對範圍太寬，見 [over-match](../over-match/)。

## 處理

確認是偽警告後，可用 inline 抑制（如 `// nolint`、`# noqa`）關掉那一處——但要**保守**：抑制範圍越窄越好，否則容易把真問題一起關掉。抑制過頭、警告太多沒人理，就變成 [noise](../noise/)。

## 連到家族

- 上位概念：[false positive](../false-positive/)。
- 機制成因：[over-match](../over-match/)。
- 量多後的狀態：[noise](../noise/)。
