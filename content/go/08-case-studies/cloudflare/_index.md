---
title: "8.6 Cloudflare：DNS、SSL 與長連線服務"
date: 2026-04-23
description: "看 Go 如何處理大量連線、網路邊界與高延遲環境"
weight: 6
---

Cloudflare 是理解 Go 高併發價值的最佳案例之一。官方文章提到 Go 被用在 Railgun、DNS infrastructure、SSL、load testing 與多個生產服務中。這些工作共同點都很明顯：大量 I/O、長連線、網路協調與對 latency 的敏感。

## 你應該看什麼

- [Go at CloudFlare](https://blog.cloudflare.com/go-at-cloudflare)
- [What we've been doing with Go](https://blog.cloudflare.com/what-weve-been-doing-with-go/)
- [Go Hack Nights at Cloudflare](https://blog.cloudflare.com/go-hack-nights/)

## 這個案例告訴我們什麼

1. goroutine 與 channel 很適合處理大量網路事件。
2. Go 在低延遲連線服務中特別自然。
3. 服務邊界、節奏控制與生命週期管理是關鍵，不只是 raw throughput。

## 可對照的公開原始碼

- [cloudflare/cloudflared](https://github.com/cloudflare/cloudflared)
- [cloudflare/cloudflare-go](https://github.com/cloudflare/cloudflare-go)

這兩個 repo 很適合拿來看長連線代理、API client、context 使用與依賴組裝。
