---
title: "整合式 Shell vs 手動拼裝：實測足跡、失敗半徑與選型判準"
date: 2026-07-01
description: "在整合式桌面 shell（如 Caelestia）與手動拼裝 waybar+wofi+mako 之間選型、需要實測的資源足跡、失敗半徑與配色一致性數據來判斷時回來讀"
weight: 6
tags: ["dotfile", "rice", "caelestia", "waybar", "hyprland", "decision"]
---

整合式桌面 shell 與手動拼裝，是「一個大程式包辦整個桌面」與「多個小程式各司其職、由 compositor 黏起來」兩種架構。[Caelestia 總覽](/linux/dotfile/06-rice-design/caelestia-overview/) 從概念層談過它的取捨（設計鎖定、穩定性風險）；這篇補上在同一台機器上實際跑過兩種之後量到的數據——資源足跡、失敗半徑、配色一致性——把「感覺整合比較方便」變成可以拿數字判斷的選型。

這裡的數據來自一次 VM 實測：先手動拼裝一套 waybar + wofi + mako + hyprlock，再換成 Caelestia，量兩者的安裝大小、記憶體、config 結構與失敗行為。

## 資源足跡：差約一個數量級

整合式 shell 把整個桌面畫在一個程式裡，這個程式通常是重量級的 UI runtime。Caelestia 建在 Quickshell（Qt6/QML）上，實測安裝足跡如下：

| 項目           | 整合式（Caelestia）               | 手動拼裝（waybar+wofi+mako+hyprlock） |
| -------------- | --------------------------------- | ------------------------------------- |
| 安裝大小       | 約 230 MB（Quickshell 佔 213 MB） | 約 4.5 MB（waybar 3 MB，其餘 KB 級）  |
| 執行記憶體 RSS | 單一 `qs` 程式約 400 MB           | waybar 約 53 MB + 通知/啟動器（小）   |

差距的來源是 Quickshell 的 Qt6/QML runtime——那 213 MB 不是 Caelestia 的功能程式碼，是它依賴的 UI 框架。手動拼裝的 waybar、wofi、mako 都是輕量的 wlroots/GTK 程式，加起來還不到 5 MB。

這一軸在資源受限的機器上才會咬人：舊筆電、記憶體小的 VPS、或你本來就想把桌面壓到最輕。在一台記憶體充裕的桌機上，400 MB 對 60 MB 的差別多半感覺不到；在一台 2 GB RAM 的機器上，這就是「桌面吃掉五分之一記憶體」跟「幾乎不佔」的差別。

## 失敗半徑：單點 vs 各自獨立

整合式 shell 把狀態列、通知、鎖屏、啟動器畫在**同一個程式**裡，所以這個程式崩潰時，這些東西會**一起消失**。手動拼裝的每個元件是獨立行程，一個崩掉不影響其他——mako（通知）崩了，waybar（狀態列）還在。

這不只是理論。本系列的 Caelestia 實測就撞到一個具體案例：Caelestia 的鎖屏是由 Quickshell 主程式畫的，當這個持鎖的程式被中止時，Hyprland 依 `ext-session-lock` 協議保持鎖定並顯示「lockscreen app died」的死局——狀態列、通知、鎖屏因為同源，一個環節出事就連帶整個桌面 UI。手動拼裝的 hyprlock 是獨立的鎖屏程式，它崩潰同樣會觸發那個死局，但你的狀態列與通知不會跟著沒。

這一軸在穩定性敏感或無人值守的場景最關鍵。跑長時間無人盯著的任務時，「一個元件崩掉只損失那個元件」的隔離性，比「全部整合在一起」的一致性更值錢——因為沒人在旁邊立刻重啟。

## 配色一致性：最容易被低估的一軸

讓整個桌面配色一致，是整合式與手動拼裝差別最大、卻最常被忽略的地方。整合式 shell 因為所有元件在同一個程式裡，天生共用一套配色——Caelestia 的 dynamic scheme 從桌布抽一組 Material-3 palette，狀態列、通知、鎖屏、dashboard 全部同時套用，換張桌布整套 UI 跟著變。

手動拼裝要達到同樣的一致，得自己解決一個跨程式的問題：每個元件用不同的設定格式與主題引擎，它們之間不會自動共享顏色。本系列 step 2 手動拼裝時就撞到這點——waybar 的 GTK CSS 引擎讀不到 Hyprland 的 `$` 顏色變數，結果 waybar 的 `style.css` 裡得**手抄一份跟 Hyprland `colors.conf` 相同的 hex 色碼**。換一次配色，就要在 waybar CSS、wofi CSS、mako config、hyprland colors 好幾個地方各改一遍。

解這個手工問題的標準做法，是加一層**模板工具**（matugen、pywal、wallust 之類）：從一張桌布或一套色票，自動生成每個元件的設定檔（例如 `matugen/templates/rofi-colors.rasi` 就是給 rofi 用的顏色模板）。這等於是手動重建 Caelestia 內建的那套 dynamic theming pipeline。所以配色一致這件事的真正取捨是：Caelestia 開箱就有「換桌布全套跟著變」，手動拼裝要嘛手抄 hex、要嘛自己搭一條 templating pipeline。

## config 結構

配色一致的差別，也反映在 config 的形狀上。Caelestia 的使用者設定集中在一個 `shell.json`（實測約 24 行就涵蓋狀態列、通知、idle 行為）。手動拼裝的設定散在各元件目錄、各用各的格式：waybar 的 `config.jsonc` + `style.css`、wofi 的 `config` + `style.css`、mako 的 `config`、hypr 的數個 `.conf`。集中的好處是好懂好改；散開的好處是每個元件可以獨立替換（把 waybar 換成 ironbar 不影響其他），代價是你要管更多檔案、更多格式。

## 選型判準

沒有一種在所有軸上都贏。依你的情境對照：

| 你的情境                                  | 偏向                                                 |
| ----------------------------------------- | ---------------------------------------------------- |
| 資源受限（舊機、小 RAM VPS）              | 手動拼裝（省下那 ~340 MB 記憶體）                    |
| 想要開箱即用、換桌布全套變色              | 整合式（Caelestia 的 dynamic 原生就有）              |
| 穩定性敏感、無人值守                      | 手動拼裝（元件獨立、失敗半徑小）                     |
| 想要結構性客製（狀態列位置、換 launcher） | 手動拼裝（整合式的結構是 shell 決定的）              |
| 想少管檔案、快速有一套設計一致的成品      | 整合式（一個 config、一套配色）                      |
| 已經在跑 templating 工具（matugen/pywal） | 手動拼裝（你已經有一致配色的機制、少了整合式的理由） |

### 重新評估的訊號（tripwire）

選了之後，出現這些訊號時值得回頭重新評估：

- 選了整合式，卻發現一直在跟它的設計決策對抗（想改的結構它不讓你改）——你要的其實是手動拼裝的自由度。
- 選了手動拼裝，卻發現配色維護（每次改色手抄多個檔案）吃掉大量時間——該加 templating 工具，或重新考慮整合式。
- 記憶體壓力浮現（整合式的 Qt runtime 在小機器上排擠其他程式）——往手動拼裝退。
- 整合式的一次更新靜默破壞了你的自訂設定（[Caelestia README 明言 config 可能無預警變動](/linux/dotfile/06-rice-design/caelestia-overview/)）——評估這層快速移動的依賴值不值得。

## 下一步

- 整合式 shell 的概念定位、跟 AGS/Eww 的比較、三個 repo 的分工，見 [Caelestia 總覽](/linux/dotfile/06-rice-design/caelestia-overview/)。
- 手動拼裝那幾個元件（狀態列、啟動器、通知）各自怎麼配置，見 [桌面 Shell 元件](/linux/dotfile/06-rice-design/desktop-shell-components/)。
- 配色系統本身（不管哪條路線）怎麼設計，見 [配色系統、鎖屏與 GTK 主題](/linux/dotfile/06-rice-design/color-system-theming/)。

這篇的足跡數字（安裝 230 MB vs 4.5 MB、RSS ~400 MB vs ~60 MB）與 lock-died 失敗案例，來自本系列在 Apple Silicon UTM VM 上實際跑過兩種桌面棧的量測。
