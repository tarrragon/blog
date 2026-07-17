---
title: "模組五：平台適配"
date: 2026-06-19
description: "JS CORS / Flutter isolate / Python GIL / Go graceful shutdown — 各平台的特殊考量"
weight: 5
tags: ["monitoring", "platform", "cors", "isolate", "gil"]
---

回答「各平台有什麼特殊考量」。

## 章節

- [JS/TS 平台適配](/monitoring/05-platform-adaptation/js-ts-platform/) — CORS 限制、Service Worker 攔截、SPA 路由變換偵測
- [Flutter 平台適配](/monitoring/05-platform-adaptation/flutter-platform/) — isolate 安全、Platform channel 攔截、app lifecycle
- [Python 平台適配](/monitoring/05-platform-adaptation/python-platform/) — GIL 與 threading、atexit 可靠性、subprocess 監控
- [Go 平台適配](/monitoring/05-platform-adaptation/go-platform/) — graceful shutdown、signal handling、HTTP server 自身監控
- [跨平台 timestamp 一致性](/monitoring/05-platform-adaptation/cross-platform-timestamp/) — 時區、精度、clock drift 的跨平台一致性處理

## 跨分類引用

- → [testing 模組五 測試設計判斷](/testing/05-test-design-judgment/)：各平台 error 攔截差異影響 test 設計
