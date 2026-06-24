---
title: "部署光譜：從 BaaS 到自架的四條路徑"
date: 2026-06-24
description: "監控方案的部署選擇不是二元的 — BaaS + Serverless 和 PaaS 是完全自架和商業 SaaS 之間兩條常被忽略的中間路徑"
weight: 2
tags: ["monitoring", "deployment", "baas", "serverless", "paas", "self-hosted"]
---

監控方案的選擇不是「完全自架 Go collector」和「買 Sentry 訂閱」的二元決策。中間存在兩條路徑 — 用 BaaS（Supabase / Firebase）搭出託管版 collector，或用 PaaS（Railway / Fly.io）跑自架 collector 原始碼但不管 server。四條路徑的本質差異在「哪些層自己管、哪些交給平台」。

[自架 vs 商業的判斷決策表](/monitoring/06-commercial-comparison/self-hosted-vs-commercial/)用四個維度（使用者數 / 網路範圍 / 功能需求 / 合規）做二元分流。本章把光譜展開成四條路徑，讓中間的 BaaS 和 PaaS 選項浮現。Backend 選型模組已建立了完整的交付形態光譜（[交付形態選型](/backend/00-service-selection/delivery-mode-selection/)）和逐能力判斷外包深度的框架（[能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)）。本章把那個框架特化到監控場景。

## 四條路徑

| 路徑                 | 代表方案                               | Collector 是什麼                   | Storage 是什麼                   | 自己管什麼              | 平台管什麼                    |
| -------------------- | -------------------------------------- | ---------------------------------- | -------------------------------- | ----------------------- | ----------------------------- |
| A. 商業監控 SaaS     | Sentry / Datadog / Firebase Analytics  | vendor 提供                        | vendor 提供                      | SDK 埋點                | 全部                          |
| B. BaaS + Serverless | Supabase + Vercel / Cloudflare Workers | serverless function（自己寫）      | managed PostgreSQL（Supabase）   | collector 邏輯、schema  | server 維運、DB 維運、TLS、HA |
| C. PaaS              | Railway / Fly.io / Render              | Go binary（自架 collector 原始碼） | SQLite（同 binary）或 managed DB | collector 邏輯、storage | server 維運、TLS、deploy      |
| D. 完全自架          | VPS + Go binary                        | Go binary                          | SQLite 或自管 PostgreSQL         | 全部                    | 無                            |

路徑 A 和 D 分別是光譜的兩端 — [Sentry 深入](/monitoring/06-commercial-comparison/sentry-deep-dive/)、[Firebase 套件](/monitoring/06-commercial-comparison/firebase-suite/)和[模組四 Collector 設計](/monitoring/04-collector/)已完整討論。以下展開路徑 B 和 C。

## 路徑 B：BaaS + Serverless

APP 上線初期用 Supabase + Vercel（或 Cloudflare Workers）搭監控後端：serverless function 接收 SDK 送來的事件、驗證 schema 後寫入 Supabase 的 PostgreSQL。整條鏈路在免費方案額度內可以零成本運作。

### 架構差異

Serverless function 沒有常駐 process。模組四假設的 Go single binary 架構 — channel 背壓、single-writer goroutine pattern、in-memory buffer — 在 serverless 環境都不適用。每個 HTTP request 是獨立的 function invocation，沒有跨 request 的記憶體狀態。

背壓機制需要重新設計：Go collector 用 channel 容量做背壓（channel 滿回 429），serverless 版改用 DB-level 的 rate limit（PostgreSQL 的 advisory lock 或外部 rate limiter 如 Upstash Redis）或 platform-level 的 quota（Vercel 的 concurrency limit）。SDK 端的 429 處理邏輯不需要改 — 不管背壓訊號來自 channel 還是 DB quota，SDK 都是收到 429 後降採樣。

Downsample 和 purge 在 Go collector 是 background goroutine 定期執行。Serverless 沒有 background job — 需要外部 cron trigger（Vercel Cron / Supabase pg_cron / GitHub Actions scheduled workflow）。

### 免費方案限額

以下為 2026-06 查詢的各平台免費方案限額。平台定價會變動，決策前以官方定價頁為準。

| 平台               | 免費方案限額                                                  | 對監控場景的意義                                                                    |
| ------------------ | ------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Supabase Free      | 500MB DB、50K MAU、500K Edge Function invocations/月          | 500MB 約 50-100 萬筆事件（每筆 ~500 bytes）、自用場景可用數月                       |
| Vercel Hobby       | 100GB bandwidth、10s function timeout、無明確 invocation 上限 | 瓶頸在 bandwidth 和 execution duration、非 invocation 數；timeout 對 ingestion 足夠 |
| Cloudflare Workers | 100K requests/天（免費）、D1 5GB                              | 100K requests/天 x 100 筆/batch = 10M events/天、D1 的 SQLite 可替代 Supabase       |

Audit date: 2026-06。平台免費方案限額可能調整，決策前以官方定價頁為準。

### 適合情境

路徑 B 適合以下組合：APP 上線初期（使用者數 < 100）、團隊熟悉前端和 SQL 但不想管 server、想保留自訂 schema 和查詢彈性（商業 SaaS 的 schema 是 vendor 定義的）、零成本起步但未來可能遷到自架。

### 撞牆訊號

以下訊號出現時，代表路徑 B 的天花板已到、該評估遷到路徑 C 或 D：

**連線數瓶頸**：Supabase Free 的 PostgreSQL 約 20 個 concurrent connection。Serverless function 每次 invocation 開新連線，高併發時可能耗盡連線池。Supabase 內建 PgBouncer 做 connection pooling 可緩解，但免費方案的 pooler 有自己的連線上限。

**Cold start 延遲**：Vercel serverless function 的 cold start 約 200ms、Supabase Edge Function 約 100ms。對監控 ingestion（不是使用者面向 API）通常可接受，但如果 SDK 的 flush timeout 設得很短（< 1s），cold start 可能造成偶發超時。

**Background job 限制**：Downsample 和 purge 需要外部 cron。Vercel Hobby 支援最多 2 個 cron job、每個最頻繁每天觸發 1 次 — 如果需要每小時 downsample，要用 Supabase pg_cron（Free 方案支援）或外部 scheduler。

**免費額度耗盡**：Supabase 的 500K Edge Function invocations/月 ≈ 每天 16K requests。如果每個 request 攢批 100 筆事件，可處理每天 160 萬筆事件。超過後進入按量付費。Vercel Hobby 無明確 invocation 上限、瓶頸在 bandwidth（100GB/月）和 execution duration。

**合規限制**：Supabase Free 的 PostgreSQL 部署在特定 region。有 GDPR data residency 需求的 app（歐盟使用者的資料必須留在 EU）需確認 vendor 的 region 支援 — 免費方案的 region 選擇可能有限。

## 路徑 C：PaaS

PaaS 跑的是和完全自架相同的 Go collector 原始碼，差異只在部署方式。`git push` 觸發自動 build 和 deploy，平台管 server provisioning、TLS 憑證、process supervision。Collector 的 channel 背壓、single-writer pattern、SQLite storage 全部適用 — 和本機開發環境的行為一致。

Railway 和 Fly.io 都支援 persistent volume — Railway Hobby 含 1GB、Fly.io Free 含 1GB（限單 region）。SQLite 的 WAL 檔案需要持久化，persistent volume 是必要條件。Render 的免費方案沒有 persistent disk — SQLite 在每次 deploy 後重置，不適合需要保留歷史事件的場景。PaaS 平台以 container 形式運行 collector，SQLite 在 container 中的 I/O 和持久化考量見 [Container 部署設計](/monitoring/04-collector/container-deployment/)。

路徑 C 適合：想用自架 collector 但不想管 server / TLS / systemd 的團隊。程式碼完全相同，遷到自架（路徑 D）的成本接近零 — 把 binary 複製到 VPS、設定 systemd service 就完成。

路徑 C 的天花板在平台定價 — Railway Hobby 有 $5/月的資源上限、Fly.io Free 有 3 個 shared VM。流量成長到免費額度不夠時，PaaS 的按量付費和 VPS 月租費的交叉點是遷到自架的判讀訊號。

## 路徑間的遷移

遷移成本取決於起點和終點之間有多少層需要重寫。

| 遷移方向 | 成本 | 主要工作                                                                |
| -------- | ---- | ----------------------------------------------------------------------- |
| B → C    | 中   | Serverless function → Go binary（重寫 collector 邏輯）；DB 可保留或遷移 |
| B → D    | 中   | 同上 + 自己管 server                                                    |
| C → D    | 低   | 同程式碼不同部署（複製 binary + systemd）                               |
| D → C    | 低   | 同程式碼推到 PaaS                                                       |
| D → A    | 低   | SDK 改 endpoint 指向商業方案、不改 SDK 程式碼                           |
| A → D    | 高   | 從零建 collector + storage + dashboard                                  |
| A → B    | 高   | 從零寫 serverless collector + 設定 managed DB                           |
| A → C    | 高   | 從零寫 Go collector + 推到 PaaS                                         |

路徑 B → C 或 B → D 的遷移代價主要在 collector 邏輯的重寫 — serverless function 的 request-level 處理和 Go binary 的 channel-based pipeline 是不同的架構，不能直接搬。資料層的遷移代價較低 — Supabase 的 PostgreSQL 資料可以用 `pg_dump` 匯出、匯入自管 PostgreSQL。

交付形態遷出的通用框架（資產線盤點、並行期設計、回切窗口）見 [託管形態遷出](/backend/10-system-evolution/managed-platform-exit/)。

## 外包深度對照

用 [外包深度](/backend/knowledge-cards/capability-outsourcing-depth/) 的三層框架（managed 基礎設施 / feature SaaS / BaaS bundle）看四條路徑：

| 路徑                 | 外包深度                                 | 控制權                                     | 遷出代價 |
| -------------------- | ---------------------------------------- | ------------------------------------------ | -------- |
| A. 商業監控 SaaS     | feature SaaS（最深）                     | SDK 埋點 API、vendor 定義 schema 和查詢    | 高       |
| B. BaaS + Serverless | managed 基礎設施 + 自寫 function（中間） | 自訂 schema、自訂查詢、自訂 collector 邏輯 | 中       |
| C. PaaS              | managed 基礎設施（淺）                   | 和自架相同、只有部署平台交出去             | 低       |
| D. 完全自架          | 不外包                                   | 完全控制                                   | 無       |

路徑 B 在外包深度上介於 managed 基礎設施和 BaaS bundle 之間 — DB 和 runtime 交給平台，但 collector 邏輯和 schema 仍由開發者控制。這和 [BaaS](/backend/knowledge-cards/baas/) 的「前端 SDK 直連平台資料庫」模式不同 — 監控場景的路徑 B 仍然有一個自己寫的中間層（serverless function），只是這個中間層跑在平台上而非自己的 server。

## 選擇建議

| 情境                                          | 建議路徑 | 理由                             |
| --------------------------------------------- | -------- | -------------------------------- |
| 自用工具、同機或同網段                        | D        | 成本最低、複雜度最低             |
| APP 上線初期、使用者 < 100、零成本起步        | B 或 A   | B 保留自訂彈性、A 開箱即用       |
| 小型團隊、想用自架 collector 但不想管 server  | C        | 程式碼相同、部署簡單、遷出成本低 |
| 使用者 > 1000、需要 dashboard + 告警 + replay | A        | 商業方案的功能完成度遠高於自建   |
| 合規要求資料不離開自有設施                    | D        | 完全控制資料位置                 |

APP 上線初期選 B 或 A 取決於自訂需求 — 需要自訂 schema 和查詢邏輯（例如自定義 error fingerprint、行為事件命名規範）選 B，只需要開箱即用的 error tracking 或行為分析選 A。B 保留遷到自架的彈性（資料在自己的 PostgreSQL），A 的功能完成度更高（dashboard、告警、session replay 開箱即用）。

## 下一步路由

- 自架 vs 商業的詳細決策 → [自架 vs 商業的判斷決策表](/monitoring/06-commercial-comparison/self-hosted-vs-commercial/)
- 自架 collector 的完整設計 → [模組四 Collector 設計](/monitoring/04-collector/)
- Backend 交付形態光譜 → [交付形態選型](/backend/00-service-selection/delivery-mode-selection/)
- 能力級買 vs 建判斷 → [能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)
- 外包深度概念 → [外包深度](/backend/knowledge-cards/capability-outsourcing-depth/)
- BaaS 概念 → [BaaS](/backend/knowledge-cards/baas/)
- 遷出劇本 → [託管形態遷出](/backend/10-system-evolution/managed-platform-exit/)
- Vendor lock-in 概念 → [Vendor Lock-In](/backend/knowledge-cards/vendor-lock-in/)
