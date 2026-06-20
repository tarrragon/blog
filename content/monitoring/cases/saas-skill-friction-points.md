---
title: "SaaS Skill 摩擦點：Monitor 專案訪談記錄"
date: 2026-06-20
draft: true
description: "用 saas-tech-selection skill 對 monitor 專案跑完整訪談，記錄 11 個摩擦點 — 多數指向「開源自架工具」產品形態在 skill 中缺席"
tags: ["monitoring", "case-study", "saas-skill", "friction"]
---

本文記錄用 saas-tech-selection skill v0.7.0 對 tarrragon/monitor 專案跑完整訪談（Stage 0-5）時發現的 11 個摩擦點。Monitor 是開源自架的客戶端監控工具（SDK + Collector），產品形態是「自用起步、開源讓別人也能自架」— 這個形態在 skill 的設計中缺席。

## 專案定錨

| 維度     | 答案                      |
| -------- | ------------------------- |
| 產品形態 | 開源自架工具              |
| 使用者   | 自己先用、可能擴展        |
| 第一目標 | Flutter app（app_tunnel） |
| 網路拓撲 | 同區網（Tailscale / LAN） |
| 開源定位 | 接受 issue 和 PR          |

## 摩擦點

### Stage 0：交付形態 gate

**#1 Gate 選項無「開源自架工具」**。六個選項（託管平台 / 垂直 SaaS / 辦公生態自動化 / BaaS / 半託管 CMS / 自建）假設商業意圖。「開源自架」的設計約束和「自建 SaaS」不同 — 多了部署彈性需求、少了多租戶和付費。

**#2 自建 vs 現有開源替代品未在 gate 判讀**。市面上有 Plausible、GlitchTip、Umami 等自架監控方案。Commodity domain check 在 Stage 2 才做，但「整個產品是 commodity」應該在 gate 階段就問。

### Stage 1：操作盤點

**#3 操作主體表為 SaaS 設計**。四類（終端使用者 / 組織角色 / 營運角色 / 機器角色）中，開發者工具的主要主體是「開發者自己」和「機器角色」（SDK 實例、Collector）。Skill 把機器角色當補充面，但 monitor 的操作清單中機器操作佔 7/15。

**#4 保留期問法應從查詢反推**。原本的問法預設「天數」或「容量」二擇一，但保留策略的真正驅動力是查詢需求 — debug 需要逐筆原始（天級）、趨勢分析需要小時聚合（季級）、留存分析需要天聚合（年級）。正確的問法是「你需要跑哪些查詢、每個查詢需要回溯多遠、回溯時需要逐筆還是聚合」，答案推導出分層保留 + 降採樣策略。已修正：state-storage 維度加了查詢驅動的保留期問題、user-operations-bdd 的保留段同步更新。

**#5 風險表的「前端引導 / 後端防護」不適用機器操作**。機器角色的風險對應是「API 契約 / error response / retry 策略」，不是 UI 引導。

**#6 失敗情境需要基本率但要到 Stage 3 才查**。開發者工具的操作盤點經常需要查「業界怎麼處理 SDK init 失敗」才能寫出合理的失敗情境。

### Stage 1.5：畫面狀態矩陣

**#7 唯讀 dashboard ≤ 3 頁做矩陣無 insight**。只有 1-2 個畫面、沒有 gate、退出路徑全是「關閉瀏覽器」。矩陣填完的 insight 接近零。

### Stage 2：Domain / Event 切分

**#8 Commodity check 問題集全是 SaaS 場景**。「認證問 hash 可攜與企業 SSO」對開發者工具不適用。開發者工具的 commodity 問題是「要不要 HTTP auth」「要不要 TLS」。

### Stage 3：核心問題

**#9 缺「開源自架工具」中間流程**。有「個人自架工具極縮減流程」（跳過 domain/event 切分），也有完整 SaaS 流程。但 monitor 需要 domain/event 切分（有多元件協作）卻不需要多租戶 — 卡在中間。

### Stage 4：技術維度

**#10 Observability 維度沒覆蓋自我監控 meta 問題**。Monitor 是 observability 工具 — 它掛了誰監控它？Bootstrapping problem 是 observability 工具特有的。

**#11 State-storage 候選無「檔案系統」**。JSONL 檔案不在任何候選類型中。自架工具經常用檔案系統作為儲存。

## 判讀

11 個摩擦點的共同根因：skill 假設產品是「有使用者、有付費、有前端 UI 的 SaaS」。開源自架開發者工具在這個假設中缺席 — 主要操作者是機器、沒有前端 UI（或只有 dashboard）、沒有付費模型、部署在使用者自己的環境。

修改方向：在每個受影響的 reference 中加「開源自架工具」的分支路徑，而非另開一套獨立流程 — 這類工具仍然受益於 BDD 操作盤點和 domain/event 切分，只是部分步驟需要調整。
