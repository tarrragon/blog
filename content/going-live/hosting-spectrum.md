---
title: "主機形態光譜"
date: 2026-07-06
description: "第一次要選服務跑在哪、被 VPS / IaaS / PaaS / serverless 這些詞搞混、不知道差在哪時回來讀 — 主機形態是一道「你管多少」的光譜"
weight: 2
tags: ["going-live", "deployment", "foundations"]
---

主機形態是一道光譜，一個軸就講完：**你管多少、平台管多少。** 從「租一台空機器什麼都自己裝」到「只丟一段函式其餘全平台顧」，中間每一格都是拿「控制權」換「維運工作」。搞懂這個軸，那些名詞（VPS / IaaS / PaaS / serverless）就各就各位。

## 一道光譜，從自己管到平台管

由左（你管最多）到右（平台管最多）：

```text
你管越多 ←───────────────────────────────────────→ 平台管越多
裸機/VPS(IaaS)      PaaS              Serverless        全託管 SaaS
給你一台機器        給你跑 code 的環境  給你跑函式的環境    你只用、不部署
OS/runtime/DB       platform 管佈署    平台管一切、可縮到零 供應商全包
/web server 全自己  你只給 code
```

- **VPS / IaaS**（DigitalOcean Droplet、AWS EC2、Hetzner）：平台給你一台（虛擬）機器，OS 以上全你自己裝——runtime（語言執行環境，如 Node/PHP）、web server、DB、開機自動啟動、更新。控制權最大，維運工作也最多。
- **PaaS**（Heroku、Render、Railway、Cloud Run、App Runner）：你把 code（或 container image）交給平台，平台管佈署、擴縮、TLS（HTTPS 憑證）、健康檢查。你不碰機器。控制權少一些，省掉大量維運。
- **Serverless / FaaS**（AWS Lambda、Cloud Functions、Cloudflare Workers）：你交的是一段函式，平台按請求觸發、沒流量時縮到零、不收錢（指函式本身；後面的 DB、儲存、API gateway 仍照計費）。最省維運，但要遷就它的執行模型（[無狀態](/going-live/twelve-factor-baseline/)、有執行時間上限、[冷啟動](/backend/knowledge-cards/cold-start/)——閒置後第一個請求要等它重新起來），本地開發與除錯也比較麻煩。
- **BaaS（backend-as-a-service）**（Firebase、Supabase）：連資料庫、認證、後端邏輯層都幫你包，你主要寫前端 + 設定。部署這件事幾乎消失。（再往外就是現成的 SaaS 成品軟體——你只用、連 code 都不寫，那已經不在「部署」的範圍內。）

## 怎麼在光譜上選位置

選位置看的是「哪個匹配你現在的處境」，沒有絕對最好的一格：

- **想學底層、要完全控制、或有特殊系統依賴** → 偏左（VPS）。你會親手做完[部署的五步](/going-live/what-is-deploy/)，學最多，但半夜掛了是你的事。
- **要快速上線、團隊時間比機器費用值錢、不想當維運** → 偏中（PaaS）。丟 code 就上線，平台顧機器。多數小團隊 / 早期產品的甜蜜點；代價是 vendor lock-in、規模長大後費用可能陡升。
- **流量尖峰型或很低、想離峰不花錢** → 考慮右（serverless）。但要接受它的執行模型限制。

注意「省錢」不是單調對應這條軸——它是另一條軸。低流量時 serverless 離峰縮到零反而可能最省；高流量穩定跑時 VPS 的固定成本又划算。所以選位置先看「控制權 vs 維運」，成本另外算，別把「省錢」綁死在某一端。

同一個服務的不同部分可以落在不同位置：app 用 PaaS、DB 用[全託管](/going-live/self-host-vs-managed-db/)、靜態檔案丟 CDN——這很常見、也常是最省事的組合。

## 邊界與下一步

主機選好、code 有地方跑之後，接著要讓外面連得到——見 [域名與 HTTPS 怎麼接上](/going-live/domain-and-https/)。

延伸：「app 跑在哪種形態的主機」跟「某個具體元件（DB）要自己顧還是託管」是同一個軸的兩種切法，後者見 [自架還是託管：以資料庫為例](/going-live/self-host-vs-managed-db/)；「值不值得自建」的商業選型角度見 [Backend 交付形態選型](/backend/00-service-selection/delivery-mode-selection/)；VPS 這一端往上長成「用 IaC 管整套雲端地基」，見 [Infra 指南](/infra/)。
