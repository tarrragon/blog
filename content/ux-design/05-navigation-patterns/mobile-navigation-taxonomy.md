---
title: "Mobile 導航模式分類"
date: 2026-06-19
description: "Push/pop stack / declarative router / tab bar / drawer — 四種 mobile 導航模式各自的適用場景和使用者心理模型"
weight: 1
tags: ["ux-design", "navigation", "mobile", "push-pop", "tab-bar", "drawer"]
---

Mobile 導航模式決定使用者如何在畫面之間移動。每種模式對應不同的使用者心理模型 — 使用者期望按 back 會發生什麼、期望首頁在哪裡、期望平行功能如何切換。選擇導航模式的依據是 app 的資訊架構和使用者的操作路徑。

## Push/pop stack（堆疊導航）

堆疊導航是最基本的模式。每次導航把新畫面推入堆疊頂端，按 back 彈出頂端畫面回到前一頁。使用者的心理模型是「深入 → 返回」的線性路徑。

適合場景：層級式的資訊結構（列表 → 詳細 → 編輯）、步驟式流程（填表 → 確認 → 完成）。

堆疊導航的限制是「只有一條軸」— 使用者只能在深度方向移動（往下鑽或往上回），無法在同層級的平行功能之間橫向切換。

## Declarative router（宣告式路由）

Declarative router 用 URL 或路由路徑表示畫面狀態。Flutter 的 GoRouter、React Router、Vue Router 都屬於這個模式。導航操作是「把 URL 設成 /settings」而非「push SettingsScreen」。

Declarative router 的優勢是路由狀態和畫面狀態分離 — 路由邏輯集中管理，支援 deep link，支援動態重建導航堆疊（例如從 deep link 恢復完整的 back 堆疊）。

適合場景：需要 deep link 支援的 app、URL 驅動的 web app、複雜的條件式導航（根據使用者狀態決定顯示哪個畫面）。

## Tab bar（標籤列導航）

畫面底部的標籤列讓使用者在平行的頂層功能之間橫向切換。每個 tab 是獨立的導航堆疊 — 在 tab A 深入到第三層，切換到 tab B 再切回 tab A，回到 tab A 的第三層。

適合場景：3-5 個平行的主要功能（首頁、搜尋、通知、個人檔案）。使用者頻繁在這些功能之間切換。

Tab bar 的限制是 tab 數量。超過 5 個 tab 在手機螢幕上過於擁擠。超過 5 個頂層功能時，次要功能放進「更多」tab 或改用 drawer。

## Drawer（抽屜導航）

從螢幕邊緣滑出的側邊選單，列出所有導航選項。使用者需要打開 drawer 才能看到選項，日常操作中 drawer 是隱藏的。

適合場景：頂層功能超過 5 個、功能之間的切換頻率低、或需要顯示使用者資訊（帳號、設定）。

Drawer 的缺點是功能的可見性低 — 隱藏在側邊的功能不如 tab bar 上的功能容易被發現。不常用的功能適合放 drawer，核心功能應該放在更可見的位置。

## 組合使用

多數 app 組合使用多種導航模式。Tab bar 做頂層橫向導航，每個 tab 內部用 push/pop 做縱向深入，drawer 放使用者設定和次要功能。

組合使用時的注意點：back 按鈕的行為在不同模式下需要一致。在 tab A 的第三層按 back 應該回到第二層（push/pop 行為），而非切換到上一個 tab。

## 下一步路由

- Flutter GoRouter 的具體實作 → [Flutter GoRouter 導航設計](/ux-design/05-navigation-patterns/flutter-gorouter/)
- go vs push 的 UX 語意差異 → [go vs push vs pushReplacement 語意表](/ux-design/05-navigation-patterns/go-push-semantics/)
- 路由可達性檢查 → [ux-design 模組一 路由可達性](/ux-design/01-screen-state-machine/route-reachability/)
