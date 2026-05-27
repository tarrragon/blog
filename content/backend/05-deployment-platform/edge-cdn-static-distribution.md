---
title: "5.9 邊緣分發與靜態資源（CDN / Origin Protection）"
date: 2026-05-27
description: "整理 CDN 與 edge cache 在部署平台中的責任邊界、origin protection、purge 與 invalidation 策略"
weight: 9
tags: ["backend", "deployment", "cdn", "edge-cache"]
---

邊緣分發的核心責任是把靜態與半靜態內容放到離使用者最近的網路節點，讓 origin 不必為每一筆讀取請求承擔流量與延遲。CDN 屬於部署平台的網路入口層，跟 [02 模組的應用層快取](/backend/02-cache-redis/) 是不同責任：CDN 解決「請求是否需要進到應用程式」，應用層快取解決「應用程式如何降低資料層讀寫成本」。這個邊界清楚後，origin 保護策略與快取一致性設計才能各自展開。

## 三層快取的責任分工

CDN、應用層快取與資料層快取串成一條快取分層。每一層各有自己的 freshness 模型、失效路徑與失敗代價，需要各自設計策略。

| 層級       | 主要載體                                                                     | 主要責任                       | 失效成本           |
| ---------- | ---------------------------------------------------------------------------- | ------------------------------ | ------------------ |
| 邊緣層     | CDN edge node、browser cache                                                 | 降低跨網延遲、保護 origin 流量 | 全球節點 purge     |
| 應用層     | Redis、in-memory cache、[cache aside](/backend/knowledge-cards/cache-aside/) | 降低資料層查詢成本             | 區域 cluster purge |
| 資料層快取 | DB buffer pool、query cache                                                  | 降低硬碟 I/O                   | 內部自動管理       |

讀者實作時要先判斷需求屬於哪一層。把使用者頭像、商品圖片、活動 banner 放邊緣層；把熱門商品價格、會員等級放應用層；DB 自身的 buffer pool 留給資料庫引擎管理。混用會造成失效路徑互相覆蓋，事故時難以判斷快取漂移來自哪一層。

## Origin Protection 的設計責任

CDN 在規模成長路徑上承擔 origin protection。當 KOL 引流或熱門活動同秒帶入大量請求時，沒有邊緣層遮蔽，origin 的應用伺服器、API gateway 與資料庫會被同步擊穿。邊緣層的責任是讓 origin 流量曲線跟使用者請求曲線解耦。

origin protection 的核心策略包含三個方向：

1. **cache hit ratio 優化**：把高頻、可共用的內容做成可快取資源（含正確的 cache-control header、ETag 跟 vary 設計）。命中率每提升 10 個百分點，origin 流量幾乎等比例下降。
2. **回源行為控制**：edge 沒命中時用 [Cache Stampede](/backend/knowledge-cards/cache-stampede/) 保護機制（origin shield 是 CDN 內部多一層中央節點集中回源、coalescing / request collapsing 把同時打進來的 N 個請求合併成一次 origin 呼叫）、避免擊穿。
3. **failure fallback**：origin 不健康時、edge 可以回傳舊版本（[stale-while-revalidate](/backend/knowledge-cards/stale-while-revalidate/) / [stale-if-error](/backend/knowledge-cards/stale-if-error/)）、避免使用者直接看到 5xx。代價是 [Stale Data](/backend/knowledge-cards/stale-data/) 風險暫時提高、需要在 freshness budget 內。

這三項決定了「能不能撐住高峰」。三項做齊才能形成保護網；缺項時邊緣層僅能發揮降低延遲的效果。

## Cacheable vs Non-Cacheable 的判讀

不是所有資源都該丟給 CDN。判讀的核心是「這個資源對所有使用者是否一樣、可不可以容忍短暫舊版」。

| 資源類型             | 適合放 CDN？ | 判讀理由                                       |
| -------------------- | ------------ | ---------------------------------------------- |
| 靜態 asset（JS/CSS） | 適合         | 內容與使用者無關，hash 命名後可長期快取        |
| 圖片、影片           | 適合         | 公開資源，跨使用者共用，命中率高               |
| 商品頁、活動頁       | 條件適合     | 對未登入者一致；對登入者需要分版本或退到應用層 |
| 訂單頁、會員中心     | 不適合       | 跟特定使用者綁定，邊緣層無法共用               |
| 個人化推薦           | 不適合       | 每個請求結果不同，命中率近於零                 |
| 寫入 API             | 不適合       | 邊緣層不該攔截狀態改變                         |

這張表覆蓋傳統靜態 / 動態二分情境。邊緣層演化出來的中間態超出表格範圍 — 包含 API responses with short TTL（GET、idempotent）、SSR / SSG 混合頁、signed URL / per-user 私有 asset（CloudFront / Cloudflare 可帶簽章對特定 user 快取）、i18n / 地理變體用 Vary header 處理跨 locale 共用、以及 edge personalization / edge compute（Cloudflare Workers、Lambda@Edge、Akamai EdgeWorkers）。進入這層要評估 edge compute 成本與 cache key 設計複雜度、不是簡單套表決定。

判讀後仍要再對齊 freshness：商品價格在限時活動期間每 5 分鐘改一次，10 分鐘 TTL 就會出現超賣或顯示差價。這類情境要把價格放應用層快取、頁面結構放 CDN，整頁邊緣化會超出 freshness budget。

## Purge 與 Invalidation 的操作模型

CDN 的 [Cache Invalidation](/backend/knowledge-cards/cache-invalidation/) 跟應用層的失效路徑不一樣：應用層 purge 在自家 cluster 內可控，CDN purge 要等全球節點同步。傳統 origin-pull CDN 的全球 purge 需要數秒到數十秒；現代 push-based CDN（Cloudflare、Fastly 等）的 instant purge 在 150ms 級別、語意接近同步、但這條能力依 vendor 而異、要事前驗證。

操作上的三種策略各有適用場景：

- **TTL 自然過期**：適合內容變動慢、不需要立即生效的資源。優點是不依賴 purge API，缺點是無法應對緊急下架。搭配 stale-while-revalidate 後可以兼顧低 origin 壓力與最終新鮮度、是現代 default 而非「弱版本」。
- **顯式 purge**：適合內容變動時要立刻生效的場景（價格更新、文章下架、合規移除）。要把 purge 列入發布流程，事故期能在分鐘內收回錯誤內容。
- **版本化路徑**：適合 JS/CSS 等可永久快取的資源。檔名含 hash（`app.a3f1b2.js`），新版本上線時直接換路徑、舊版本自然失效。這是命中率最高的策略，因為可以設定 `max-age=31536000, immutable`。

這三種策略以 origin pull 模型為主、是基底但不窮盡。現代 CDN 還有兩種重要策略：**[Tag-based / surrogate-key purge](/backend/knowledge-cards/cache-tag-purge/)**（Fastly cache tag、Cloudflare cache tag、Akamai surrogate key）是大型內容系統的事實標準、用一個 tag 同時 purge 多個資源；**Push-based instant purge**（Cloudflare、Fastly 規格 <150ms 全球同步）讓全球 purge 從「分鐘級」變成「準同步」。選擇策略時要按 vendor 能力跟資源更新模式組合、不只看本表三條。

選錯策略的代價會在事故時放大。把限時優惠的價格用「TTL 自然過期」策略佈在 CDN、活動結束後仍有客人看到舊價格繼續下單、客服與退款成本會壓回業務端。

## 判讀訊號

| 訊號                        | 判讀重點                                             | 對應動作                                               |
| --------------------------- | ---------------------------------------------------- | ------------------------------------------------------ |
| origin 流量隨使用者線性成長 | cache hit ratio 偏低，邊緣層沒發揮 origin protection | 檢查 cache-control header、命中率分布、coalescing 設定 |
| edge 命中率忽然下降         | purge 設定誤觸全網、或 cache key 設計過細            | 檢查近期 purge 操作、vary 與 query string 設計         |
| purge 後仍看到舊內容        | 全球節點同步延遲、或 CDN 與應用層快取沒對齊          | 確認 CDN purge 完成訊號、再追應用層快取狀態            |
| 高峰時 origin 出現 5xx 尖峰 | edge 沒做 stale-if-error，origin 過載直接打回使用者  | 啟用 stale-while-revalidate、檢查 origin shield 設定   |
| 部分區域延遲偏高            | 區域節點覆蓋不足、或回源走錯區域                     | 檢查路由策略、加開 edge POP、考慮多 CDN 策略           |

## 常見誤區

把 CDN 當成單純的「加速工具」，會忽略 origin protection 跟一致性責任。多數團隊上線後第一次撞牆，是 KOL 引流或活動高峰把 origin 直接打掛，事後才發現 CDN 只覆蓋了靜態 asset、HTML 與 API 都直接打回 origin。

把 purge 當成同步操作也容易出事。緊急下架觸發 purge 後立刻通知公關「已下線」，但全球節點還沒收斂，仍有區域看到原內容。這類風險要把「purge 已完成」當成可觀測訊號處理，不是 API 回 200 就視為完成。

把 CDN 當成應用層快取替代品則是另一個極端。商品價格、會員等級這類「跟使用者狀態相關」的資料放邊緣層，會在用戶切帳號、優惠變更時暴露其他人的資料或舊狀態，是 [Stale Read](/backend/knowledge-cards/stale-read/) 的擴大版。

## 定位邊界

CDN 專注「靜態與半靜態內容的網路層分發」。當問題進入動態 API 的延遲、跨服務一致性、寫入路徑保護，責任分別交給 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)、[02 cache aside](/backend/02-cache-redis/cache-aside/) 與 [03 message queue](/backend/03-message-queue/) 模組。

跟 [07 入口治理](/backend/07-security-data-protection/entrypoint-and-server-protection/) 的交接：CDN 同時是公網入口，需要承接 WAF、bot mitigation、TLS termination 等資安責任。邊緣層的安全設定不可遺漏，否則 origin 被繞過直接攻擊。

## 案例回寫

邊緣分發策略可用以下案例回寫：

- [9.C13 Hotstar：1800 萬同時觀眾的 IPL 直播](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/) — 極端峰值靠多 CDN + origin shield 把 origin 流量壓在容量範圍內。Hotstar 的具體做法是把 hot content（live stream segment）跟 warm content（VOD）分配到不同 CDN provider、利用「edge cache miss 時不是同時打 origin」這條 cache stampede 防禦機制讓 origin 流量曲線跟使用者請求曲線解耦。對照本章「origin protection」段三大策略落地。
- [9.C18 Zoom：COVID 30 倍突發](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) — 30 倍突發中，登入頁、會議連結頁這類靜態資源由邊緣層吸收絕大部分讀取流量，API 叢集只面對真實的會議建立 / 結束請求。對照本章「Cacheable vs Non-Cacheable 判讀」段：登入頁屬未登入者一致、適合邊緣化；會議內互動屬寫入 API、保持在 origin。
- [2.C7 Cloudflare Cache Reserve 與 Tiered Storage](/backend/02-cache-redis/cases/cloudflare-cache-reserve-tiered-storage/) — Cloudflare 在 CDN 內部再分一層 Cache Reserve（持久層）、把 warm 內容從 origin 卸下、避免 edge LRU 淘汰後又回到 origin。對照本章「三層快取」段：邊緣層內部本身也能有 hot / warm 分層、是同一概念的遞迴應用。

三個案例依規模從外向內展開：Hotstar 是極端峰值下 origin protection 防禦的天花板測試、Zoom 是把非交易流量（登入 / 連結頁）分流降低 API 集群壓力的標準應用、Cloudflare Cache Reserve 則展示 CDN vendor 自身把 hot / warm 內容再分層的內部架構。讀者可串著讀理解規模光譜、也可以挑一條深入。

## 跨模組路由

1. 與 [02 cache aside](/backend/02-cache-redis/cache-aside/) 的交接：應用層快取與邊緣層的失效路徑要對齊，避免兩層 stale 同時發生。
2. 與 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/) 的交接：edge miss 後流量進到 origin LB，超時與重試設定要協調。
3. 與 [7.3 入口治理](/backend/07-security-data-protection/entrypoint-and-server-protection/) 的交接：CDN 是公網入口，WAF、TLS 與 bot mitigation 在邊緣層落地。
4. 與 [9.6 容量規劃](/backend/09-performance-capacity/capacity-planning/) 的交接：cache hit ratio 是 origin 容量規劃的核心輸入，命中率假設失準會直接撞牆。

## 下一步路由

**規模成長路線下一站 → [03 模組訊息佇列](/backend/03-message-queue/)**：邊緣層擋住讀流量後、寫流量與事務鏈的下一塊是非同步化。

其他延伸方向：

- 邊緣失效跟應用層失效串成 invalidation pipeline → [2.2 cache aside 與失效策略](/backend/02-cache-redis/cache-aside/)
- 高峰活動把 CDN 跟排隊機制組合成保護網 → [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)
- Origin 端的入口流量合約 → [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)
