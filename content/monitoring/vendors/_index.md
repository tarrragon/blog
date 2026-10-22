---
title: "Vendor：各家追蹤碼的接入與驗證"
date: 2026-10-22
description: "要把某一家商業追蹤方案（廣告平台像素、tag manager、行為分析 SDK）接上自己的網站或 App，想知道它的事件模型、資料路徑與驗證方式時，從這裡找對應的那一家"
weight: 9
tags: ["monitoring", "vendor", "tracking", "pixel"]
---

本資料夾一家一篇，寫商業追蹤方案接上之後的機制：它在頁面或 App 裡做什麼、事件送到哪裡給誰用、資料在哪些環節會掉、以及怎麼驗證送出去的內容。[模組六：商業方案對照](/monitoring/06-commercial-comparison/) 處理的是要不要買、什麼時候從自架換過去；本資料夾接在那個決定之後，所以兩邊的分工是「選型」與「接入」，同一家 vendor 可以兩邊各有一篇。

## 篇目

| 文章                                                                             | 對象                                      | 交付                                                               |
| -------------------------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------ |
| [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) | 廣告平台的轉換追蹤（瀏覽器端 + 伺服器端） | 標準事件、被攔截的路徑、伺服器端補送、`event_id` 去重、Test Events |
| [Google Tag Manager](/monitoring/vendors/google-tag-manager/)                    | 追蹤碼的部署層                            | 資料層約定、預覽模式驗證、自訂 HTML 的治理、伺服器端代碼管理       |

## 篇目的收錄條件

收進來的 vendor 要有一段自架方案沒有的機制可以寫：廣告平台的資料消費者是投放演算法、tag manager 把部署權交給行銷人員，這些在模組一到八的自架脈絡裡沒有對應物。只是功能清單不同的 vendor（另一家 error tracking）先在模組六的對照文補一列，累積到有獨立機制可講再開篇。

## 在本站實測追蹤碼的評估

起因是想把各家的事件與追蹤碼直接埋在這個部落格上做實測。評估之前先記下現況：本站已經有一套自製的流量 beacon（`layouts/partials/custom_body.html`，說明在 [Automation 模組二：流量 beacon 實作](/automation/02-analytics-beacon/)），設計上刻意不送完整 User-Agent、識別碼是隨機值、有 opt-out。全站加上第三方追蹤碼會直接推翻這組設計：讀者的瀏覽紀錄送到 Meta 與 Google、頁面多出 `_fbp`、`_ga` 這類 cookie、每一頁多載入第三方 script，而歐盟讀者的部分需要同意聲明（consent banner）。

三個做法與各自的代價：

- **全站嵌入**：收到的是真實讀者的事件，代價是上面那整組隱私與效能成本由所有讀者承擔，而讀者來這裡是讀文章。目前不採用。
- **獨立實測頁、讀者按下按鈕才載入**：在 `vendors/` 底下開一頁實測頁，頁面預設不載入任何第三方 script，讀者按下「載入 Meta Pixel」之類的按鈕才注入，事件一律帶各家的測試模式（Meta 的 `test_event_code`、GA4 的 DebugView、GTM 的預覽模式）。影響範圍限於主動按下按鈕的人。需要各家帳號與測試用 ID。
- **不嵌入，在本機用 Playwright 攔網路請求**：瀏覽器自動化載入一個本機測試頁，記錄各家 script 實際送出的請求（網址、payload、cookie），結果寫進文章。讀者端零影響，大部分觀察不需要帳號（假的 Pixel ID 照樣會送出請求，只是後台收不到）。

建議順序是先做 Playwright 攔截，再視需要開實測頁。Conversions API 這類伺服器端路徑在本站另有一個限制：本站的接收端是 Apps Script，而 Apps Script 的 `doPost` 讀不到請求的 HTTP header（拿不到 IP 與 User-Agent），Meta 對網站事件要求的 `client_user_agent` 就只能由前端放進 payload，這又回到送完整 User-Agent 的隱私取捨上。

## Backlog

| 項目                                                 | 類型 | 前置條件                                                  | 規模 |
| ---------------------------------------------------- | ---- | --------------------------------------------------------- | ---- |
| Playwright 攔截各家追蹤碼的請求，結果回寫到兩篇文章  | 案例 | 本機測試頁與 Playwright 腳本（不需帳號）                  | 中   |
| 獨立實測頁（按鈕載入、測試模式）                     | 案例 | 作者決定是否採用；Meta Business 帳號與 Pixel ID、GTM 容器 | 中   |
| GA4 網頁版的事件模型與 Measurement Protocol          | 主章 | 無                                                        | 1    |
| Mixpanel 的接入面（identify / alias、Ingestion API） | 主章 | 無                                                        | 1    |

### 實測頁的決策條件

實測頁要動手之前，作者要先決定三件事：本站的隱私說明要不要補一段寫實測頁載入了什麼；測試用的 Pixel 與 GTM 容器開在哪個帳號底下；實測頁要不要從站內搜尋與列表排除（實測頁的讀者是來看請求內容的，搜尋落到它的讀者多半不是）。
