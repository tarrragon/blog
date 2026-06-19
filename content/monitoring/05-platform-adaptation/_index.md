---
title: "模組五：平台適配"
date: 2026-06-19
description: "JS CORS / Flutter isolate / Python GIL / Go graceful shutdown — 各平台的特殊考量"
weight: 5
tags: ["monitoring", "platform", "cors", "isolate", "gil"]
---

回答「各平台有什麼特殊考量」。

## 待寫章節

- [ ] JS/TS 平台：CORS 限制、Service Worker 攔截、SPA 路由變換偵測
- [ ] Flutter 平台：isolate 安全、Platform channel 攔截、app lifecycle
- [ ] Python 平台：GIL 與 threading、atexit 可靠性、subprocess 監控
- [ ] Go 平台：graceful shutdown、signal handling、HTTP server 自身監控
- [ ] 跨平台 timestamp 一致性（時區、精度、clock drift）

## 跨分類引用

- → [testing 模組五 測試設計判斷](/testing/05-test-design-judgment/)：各平台 error 攔截差異影響 test 設計
