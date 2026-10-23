---
title: "Vendor：各家追蹤碼的接入與驗證"
date: 2026-10-22
description: "想實測某一家商業追蹤方案（廣告平台像素、tag manager、行為分析 SDK）的設計——它的事件模型、資料路徑、實際送出的請求與 cookie——或決定這些追蹤資產該建在誰的帳號底下時，從這裡找對應的機制文、實測頁、擷取紀錄與帳號歸屬"
weight: 9
tags: ["monitoring", "vendor", "tracking", "pixel"]
---

本資料夾的目的是實測各家追蹤系統的設計：每一家有一篇機制文，寫它在頁面或 App 裡做什麼、事件送到哪裡給誰用、資料在哪些環節會掉；有一頁實測頁，讓讀者在瀏覽器裡按按鈕觸發它、對照它實際送出的內容；Playwright 擷取紀錄把同樣的操作自動化並記下擷取時間，留給 vendor 改版之後比對。另有一篇跨三家的帳號治理文章，處理這些追蹤資產建在誰的帳號底下、權限怎麼分、委託代理商與轉手時怎麼移交。本站不是要用這些追蹤碼收集讀者資料，所以實測頁是獨立的頁面、只在讀者按下按鈕時載入。[模組六：商業方案對照](/monitoring/06-commercial-comparison/) 處理的是要不要買、什麼時候從自架換過去，跟本資料夾的分工是「選型」與「設計實測」，同一家 vendor 可以兩邊各有一篇。

## 篇目

| 文章                                                                             | 類型     | 交付                                                                                              |
| -------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------- |
| [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) | 機制文   | 標準事件、被攔截的路徑、伺服器端補送、`event_id` 去重、Test Events                                |
| [Meta Pixel 實測頁](/monitoring/vendors/meta-pixel-lab/)                         | 實測頁   | 按鈕觸發 PageView / ViewContent / Purchase、`_fbp` 與 `_fbc` 的產生、載入失敗態                   |
| [Google Tag Manager](/monitoring/vendors/google-tag-manager/)                    | 機制文   | 資料層約定、預覽模式驗證、自訂 HTML 的治理、伺服器端代碼管理                                      |
| [Google Tag Manager 實測頁](/monitoring/vendors/google-tag-manager-lab/)         | 實測頁   | 容器載入、資料層內容、容器載入前推入的事件、代碼送出的請求                                        |
| [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/)    | 擷取紀錄 | 擷取方式、結果檔欄位、各次結果（標擷取時間與版本）                                                |
| [追蹤資產的歸屬](/monitoring/vendors/tracking-account-ownership/)                | 帳號治理 | Meta 組合、GTM 帳戶與容器、GA4 帳戶與資源的擁有層級、權限分級、能否換擁有者、代理商與轉手時的歸屬 |

擷取紀錄在第一次擷取完成之前維持 `draft: true`；2026-10-23 GTM 與 Meta Pixel 各完成一次擷取之後發布。

## 篇目的收錄條件

收進來的 vendor 要有一段自架方案沒有的機制可以寫：廣告平台的資料消費者是投放演算法、tag manager 把部署權交給行銷人員，這些在模組一到八的自架脈絡裡沒有對應物。只是功能清單不同的 vendor（另一家 error tracking）先在模組六的對照文補一列，累積到有獨立機制可講再開篇。

## 實測方式的決策紀錄

本站已經有一套自製的流量 beacon（`layouts/partials/custom_body.html`，說明在 [Automation 模組二：流量 beacon 實作](/automation/02-analytics-beacon/)），設計上刻意不送完整 User-Agent、識別碼是隨機值、有 opt-out。全站加上第三方追蹤碼會推翻這組設計：讀者的瀏覽紀錄送到 Meta 與 Google、頁面多出 `_fbp`、`_ga` 這類 cookie、每一頁多載入第三方 script，歐盟讀者的部分還需要同意聲明。所以不全站嵌入，採用兩種實測方式並行（2026-10-22 決定）：

- **獨立實測頁**：實作是 `layouts/shortcodes/vendor-lab.html`。頁面預設不注入任何第三方 script，讀者按下載入按鈕才注入；ID 由讀者填寫，預設值取 `hugo.toml` 的 `[params.vendorLab]`。`tests/vendor-lab.spec.ts` 把 vendor 網域攔下來回 stub，守住「按下之前零請求」與 ID 格式檢查。
- **本機 Playwright 擷取**：`scripts/vendor-capture/capture.mjs` 操作實測頁並把請求、cookie、資料層寫成 JSON（`scripts/vendor-capture/results/`），每份結果帶擷取時間、瀏覽器版本、vendor script 的回應標頭與本體雜湊，因為 vendor 改版之後結果就不再適用。Meta Pixel 在無頭瀏覽器裡不送事件，擷取 Meta 要加 `--headed`（2026-10-23 實測）；腳本不改寫 User-Agent。
- **文章不寫測試 ID、實測頁不設預設值**（2026-10-23 決定）：Pixel ID、容器 ID 與評估 ID 本來就寫在網頁原始碼裡，公開它們不會讓別人登入帳號；風險在反方向，任何人都能拿 ID 往帳號送事件，而 Meta 的資料集不能刪除，被灌入假事件之後只能另建一個。這組測試帳號只放實測資產、沒有投放廣告，被灌入假事件的影響只在測試報表上，所以接受這個風險：擷取結果的 JSON 保留原始 ID（repo 是公開的，ID 因此查得到），供日後比對。文章正文不寫實際值，理由是讀者照抄別人的 ID 去測試，事件會送進別人的帳號、也學不到用自己的 ID；文章只描述 ID 的格式與查詢位置。`hugo.toml` 的 `[params.vendorLab]` 維持空白，讀者在實測頁填自己的 ID。
- **測試帳號**：Meta 商家資產管理組合「Tarragon Tech Notes」裡的資料集、GTM 帳戶 `vendor-lab-test`、GA4 帳戶 `vendor-lab-test`，都只放實測資產。建立時的檢查與預設值記在 [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/) 的〈擷取用的測試帳號〉一節，為什麼另開擁有者記在 [追蹤資產的歸屬](/monitoring/vendors/tracking-account-ownership/) 的〈本站實測資產的擁有者〉一節。

Conversions API 這類伺服器端路徑在本站有一個限制：本站的接收端是 Apps Script，而 Apps Script 的 `doPost` 讀不到請求的 HTTP header（拿不到 IP 與 User-Agent），Meta 對網站事件要求的 `client_user_agent` 只能由前端放進 payload，這又回到送完整 User-Agent 的隱私取捨上，所以伺服器端目前只寫機制、不做實測。

## Backlog

| 項目                                                                                                                                                                                                                                                                                                                      | 類型 | 前置條件             | 規模 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | -------------------- | ---- |
| GA4 網頁版的事件模型與 Measurement Protocol（機制文 + 實測頁）                                                                                                                                                                                                                                                            | 主章 | 無                   | 2    |
| Mixpanel 的接入面（identify / alias、Ingestion API）                                                                                                                                                                                                                                                                      | 主章 | 無                   | 1    |
| 實際送件驗證 Meta 管理員爭議對「唯一帳號已遺失」與「前承包商持有組合」兩種情形的處理結果；說明頁層級已查證（前承包商明列為可申請，唯一帳號遺失不在清單、送件要登入與組合有關聯的個人檔案），結果寫回追蹤資產的歸屬                                                                                                        | 案例 | 需有可申訴的實際組合 | 小   |
| 異源複核：另一個執行者（另一個工作階段或真人）用同一組 frame 獨立掃追蹤資產的歸屬與擷取紀錄，兩邊各自報數再並排                                                                                                                                                                                                           | 案例 | 有另一個執行者可用   | 小   |
| 時效複核：三家帳號規則與 fbevents.js、gtm.js 會改版，半年後重讀追蹤資產的歸屬與擷取紀錄兩篇、三張追蹤碼知識卡（first-party-cookie、headless-browser、autocapture），用 `rg "botblocking\|_fbp\|_ga\b\|SubscribedButtonClick\|管理員爭議\|主機名稱篩選" content/` 找出其他引用處一併核對，並重跑一次擷取，比對雜湊與說明頁 | 案例 | 2027-04 之後         | 小   |
