---
title: "9.C13 Disney+ Hotstar：IPL 板球決賽 1860 萬人同時直播"
date: 2026-05-12
description: "Hotstar 在 IPL 板球決賽創下 1860 萬同時觀看的全球直播紀錄、CDN 與全球邊緣容量極限"
weight: 13
tags: ["backend", "performance", "capacity", "case-study", "global-edge", "aws", "predictable-peak"]
---

這個案例的核心責任是說明「全球大型直播」的容量設計 — 跟 Prime Day 同屬「可預期極端峰值」、但形狀完全不同：Prime Day 是分散全球的購物峰值、Hotstar IPL 是 *單一時間點 + 高度集中地理區* 的直播峰值。容量規劃的挑戰在於 CDN、串流伺服器、live encoder、message queue 同時 saturate。

## 觀察

Hotstar IPL 直播的關鍵數字（引自 [Hotstar global record](https://aws.amazon.com/blogs/media/in-the-news-hotstar-sets-new-global-record-for-live-viewership/)）：

| 指標         | 數字                                |
| ------------ | ----------------------------------- |
| 同時觀看峰值 | 1860 萬 人（2021-03 IPL 決賽）      |
| 全球記錄     | 該時點全球同時觀看直播的最高記錄    |
| 服務組合     | AWS Media Services + AWS CloudFront |
| 客戶基礎     | 印度為主、跨亞洲                    |

AWS Media Services 在大型事件的歷史記錄：Olympics、Super Bowl、IPL Cricket（引自 [AWS large-scale streaming events](https://aws.amazon.com/developer/application-security-performance/articles/large-scale-video-streaming-events/)）。

## 判讀

Hotstar 案例揭露三個全球直播容量重點。

1. **集中地理區 = CDN 壓力集中**：Prime Day 的流量分散全球、單一地區 CDN 不會 saturate；IPL 主要觀眾在印度、所有印度 PoP 同一時間 saturate。CDN 容量規劃必須按地區獨立做、不能用「全球總容量」當保證。對應 [04 可觀測性模組](/backend/04-observability/) 的 cardinality 與地區訊號治理、跟 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的「地理分片容量」。
2. **直播跟 VoD 是不同容量問題**：VoD 觀眾分散時間、CDN 可預先 cache；直播觀眾集中時間、每一個 manifest / segment 都是 live 拉取、cache hit 反而是危險（拉到舊的 segment）。對應 [02 快取模組](/backend/02-cache-redis/) 的 cache freshness boundary、跟 [03 訊息佇列](/backend/03-message-queue/) 的 fan-out 設計。
3. **多 bitrate 動態切換 = 真實容量是 bitrate 加權**：1860 萬觀眾不是都看 1080p — 印度行動網路下大多看 720p 或 480p、bitrate 加權後的 total bandwidth 可能比想像低。對應 [9.2 Workload Modeling](/backend/09-performance-capacity/) 的真實 workload shape。

需要警惕：「1860 萬同時觀看」是 *峰值瞬間*、不是全程平均。決賽 4 小時、觀眾數呈鐘形曲線、峰值維持時間可能只有 10-30 分鐘（比賽關鍵時刻）。容量規劃要看峰值持續時間、不只看峰值高度。

## 策略

可重用的工程做法：

1. **CDN 容量規劃按地理區分割**：不要假設「全球 CDN 總量」夠用、要按主要觀眾分布的地區做容量保證。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/)。
2. **直播必須 pre-scaling、不能依賴 reactive**：直播開始之後 CDN reactive 擴容已經太晚、觀眾體驗已壞。事件型 scheduled scaling + over-provisioning 是必須。對應 [9.11 高峰事件準備](/backend/09-performance-capacity/)。
3. **multi-bitrate / ABR streaming 是容量緩衝**：當網路擁塞、player 自動降 bitrate、總頻寬壓力下降。這層降級是隱性容量緩衝、要在壓測時驗證。對應 [9.4 Saturation Discovery](/backend/09-performance-capacity/) 的 saturation 行為。

跨平台等效：GCP CDN + Media CDN、Azure Front Door + Media Services、Akamai / Cloudflare / Fastly 等 multi-CDN 都是對等候選。差異是 PoP 地理分布跟 manifest 處理能力。

## 下一步路由

- 想規劃全球直播 → [9.11 高峰事件準備](/backend/09-performance-capacity/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想做 CDN 容量設計 → [05 部署平台模組](/backend/05-deployment-platform/) + [04 可觀測性模組](/backend/04-observability/)
- 想理解 cache freshness 在直播的影響 → [02.4 cache copy freshness boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)
- 對照其他可預期峰值 → [9.C1 AWS Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)（分散全球的峰值）

## 引用源

- [In the news: Hotstar sets new global record for live viewership](https://aws.amazon.com/blogs/media/in-the-news-hotstar-sets-new-global-record-for-live-viewership/)
- [Large scale streaming events on AWS](https://aws.amazon.com/developer/application-security-performance/articles/large-scale-video-streaming-events/)
- [Direct to Consumer & Streaming on AWS](https://aws.amazon.com/media/direct-to-consumer-d2c-streaming/)
