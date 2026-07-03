---
title: "終端機文字圖表：gnuplot、termgraph、plotext 與 sparkline"
date: 2026-06-15
draft: false
description: "要在終端機把數值畫成文字圖表、在 gnuplot／termgraph／plotext／sparkline 之間挑工具、或遠端頻寬受限想用一次性輸出省流量時回來讀"
tags: ["cli", "ascii", "chart", "gnuplot", "termgraph", "plotext", "remote"]
---

終端機文字圖表工具是把一串數值畫成終端機裡由字元構成的圖的一類程式，承擔的責任是讓趨勢與分布可視化，而不必把資料拉回本機開試算表。在遠端情境下，它的優勢是一次性輸出、不持續重畫，所以對頻寬最友善 — 跑一次印出結果就結束，不像全螢幕 TUI 會持續佔用連線。

這類工具與 TUI 監控的分工很清楚：TUI 監控自己去抓系統即時狀態並持續刷新，文字圖表則是餵什麼畫什麼，適合畫已經到手的數值（log 抽出的延遲、監控匯出的指標、一個查詢的結果）。本文承接 [終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/) 的文字圖表分類。

## gnuplot：通用繪圖的 ASCII 後端

gnuplot 是老牌繪圖工具，設定 `set terminal dumb` 就改用 ASCII 字元輸出，責任是把函數或時間序列畫成終端機可讀的折線圖。它不需要圖形環境，在純 SSH 下直接可用。

```bash
gnuplot -e "set terminal dumb size 80,25; plot sin(x)"
```

畫資料檔時把 `plot` 指向檔案，例如 `plot 'data.dat' using 1:2 with lines`。gnuplot 的適用情境是需要正式座標軸、多條曲線疊圖、或畫數學函數時 — 它的表達力最完整，代價是設定語法較多。

## termgraph：分類長條圖

termgraph 吃一份「標籤加數值」的資料就畫出橫向長條圖，責任是讓各分類的佔比一眼可比。它用 `pip install termgraph` 安裝，適合看「哪一類佔最多」這種分布問題。

```bash
printf "Mon 120\nTue 250\nWed 90\n" | termgraph
```

每一行是一個分類與其數值，termgraph 把數值換算成等比例的長條。它的定位是快速看分布，不追求座標軸的精確 — 想看的是相對大小而非絕對讀數時最合適。

## plotext：腳本內繪圖

plotext 是 Python 函式庫，讓折線、散點、長條圖直接在腳本裡畫出來，責任是把繪圖接在資料處理流程後面。它用 `pip install plotext` 安裝，適合在既有的 Python 資料處理腳本末端加一段視覺化。

```python
import plotext as plt

plt.plot([3, 1, 4, 1, 5, 9, 2, 6])
plt.title("延遲趨勢")
plt.show()
```

plotext 的優勢是與資料處理同在一個腳本、不必把資料另存再餵給外部工具。處理完數據順手畫一張圖確認形狀，是它最自然的用法。

## sparkline 與 pipeline 即時更新

sparkline 工具把一串數字壓成一行高低起伏的點陣，責任是用最小的版面塞進一條趨勢。它不畫座標軸，只呈現形狀，適合放進狀態列、log 或窄螢幕。

```bash
spark 1 5 3 8 2 9 4
```

需要從 pipeline 即時吃資料時，`youplot`（指令名 `uplot`）能接管線畫圖，配合 `tail -f` 做出滾動更新的監控線：

```bash
tail -f metrics.log | uplot line
```

sparkline 在窄螢幕（手機、平板遠端）特別有優勢，因為一行不管螢幕多窄都塞得下。低頻率印一條 sparkline 來持續觀察某個指標，比開全螢幕儀表板省頻寬得多。

## 遠端使用判讀

文字圖表在遠端的核心優勢是輸出模式：一次性印出、不持續重畫，所以不像全螢幕 TUI 那樣持續佔用頻寬。判讀分界落在資料來源與互動需求 — 手上已有數值、只想看形狀，用文字圖表；需要系統即時狀態並隨時操作，用 TUI 監控（見 [TUI 監控工具](/linux/tools/cli/tui-monitoring-tools/)）。

慢速連線下做持續監控時，「每隔較長間隔印一次 sparkline 或長條圖」比全螢幕儀表板省頻寬：一行 sparkline 的傳輸量是固定的幾十個位元組，全螢幕儀表板則每次重送整片畫面（含 ANSI 色碼常達數 KB），兩者差一到兩個量級。

## 下一步路由

- 需要即時系統狀態而非一次性圖表：[TUI 監控工具](/linux/tools/cli/tui-monitoring-tools/)。
- 把監控與繪圖擺進可持久化的多工器：[tmux 基礎](/linux/tools/cli/tmux-persistence-and-basics/)。
- 文字圖表在整個遠端工具選型中的位置：[終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/)。
