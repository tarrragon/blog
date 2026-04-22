---
title: "8.3 Dropbox：從 Python 遷移到 Go"
date: 2026-04-23
description: "看性能關鍵後端如何從 Python 逐步轉向 Go"
weight: 3
---

Dropbox 的案例是最典型的「性能關鍵服務遷移」故事之一。官方案例直接寫到，他們把 performance-critical backends 從 Python 轉到 Go，以獲得更好的 concurrency support 與更快的執行速度。

## 你應該看什麼

- [Dropbox - Open sourcing our Go libraries](https://go.dev/solutions/dropbox)

## 這個案例告訴我們什麼

1. Go 很常被選在 Python 已經不夠用的後端邊界。
2. 併發支援通常是遷移的重要原因之一。
3. 遷移不是一下子全部換掉，而是先把性能最敏感的部分換成 Go。

## 可對照的公開原始碼

- [dropbox/godropbox](https://github.com/dropbox/godropbox)
- [dropbox/dropbox-api-spec](https://github.com/dropbox/dropbox-api-spec)

Dropbox 的公開 Go libraries 與 API spec 很適合對照閱讀。你會看到一個大公司如何把 Go 用在可重用工具與服務邊界上。

