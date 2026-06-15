---
title: "Zellij 多終端機操作指南"
date: 2026-03-09
draft: false
description: "Zellij pane 的佈局查看、內容讀取、大小調整等 CLI 操作方式，適合搭配 AI 工具使用。"
tags: ["zellij", "terminal", "pane", "cli"]
---

Zellij 是終端機多工器，能在單一畫面分割多個 pane。本文整理透過 zellij CLI 查看佈局、讀取其他 pane 內容、調整 pane 大小的操作方式 — CLI 介面既適合遠端腳本化操作，也適合搭配看不到螢幕的 AI 工具（例如 Claude）在終端機協作。本文承接 [終端機圖形化工具總覽](/cli/cli-graphical-tools-overview/) 的多工器分類；瀏覽器遠端連線見 [Zellij Web Client 外網連線教學](/cli/zellij-remote-web-client/)、tmux 的持久化基礎見 [tmux 基礎](/cli/tmux-persistence-and-basics/)。

## 查看整體佈局

```bash
zellij action dump-layout
```

會輸出完整的 KDL 格式佈局，包含所有 pane 的大小、位置、指令等資訊。

## 讀取其他終端機 pane 的內容

Claude 無法直接看到螢幕，但可以透過以下步驟讀取其他 pane 的輸出：

```bash
# 1. 切換 focus 到目標 pane（focus-next-pane 會依序切換）
# 2. dump 該 pane 的螢幕內容到檔案
# 3. 切回原本的 pane
# 4. 讀取 dump 的檔案

zellij action focus-next-pane && \
zellij action focus-next-pane && \
zellij action dump-screen /tmp/zellij-pane-output.txt && \
zellij action focus-previous-pane && \
zellij action focus-previous-pane
```

- `dump-screen` 只 dump 當前可見的內容
- `dump-screen -f` 會包含完整的 scrollback 歷史
- 切換次數取決於目標 pane 的位置，需根據 `dump-layout` 的結果判斷

## 調整 pane 大小

```bash
# 縮小當前 pane（向左縮）
zellij action resize decrease right

# 放大當前 pane（向右擴）
zellij action resize increase right

# 每次約改變 ~4-5% 寬度，可用迴圈批次調整
for i in $(seq 1 3); do zellij action resize decrease right; done
```

每次的步長是經驗值、不是固定比例 — zellij 的 resize 幅度依版本與 pane 當前尺寸而定，迴圈次數需視 `dump-layout` 的結果微調。

## 使用者的 Resize 快捷鍵

1. `Ctrl + n` 進入 Resize 模式
2. `h`/`l` 或方向鍵調整大小
3. `Esc` 退出

注意：在 Claude 互動式程式內，快捷鍵可能被吃掉，建議讓 Claude 用指令操作。

## 注意事項

- `Ctrl + p` 進入 Pane 模式，其中 `r` 用於在右邊新開 pane（調整大小是 `Ctrl + n` 的 Resize 模式）
- 使用者的典型佈局：左側 Claude（~35%），右側上下兩個終端機

---

## 下一步路由

- 把 session 分享給沒有 SSH 連線的協作者（瀏覽器連入）：[Zellij Web Client 外網連線教學](/cli/zellij-remote-web-client/)。
- 純 SSH 的多工器持久化與 tmux 對照：[tmux 基礎](/cli/tmux-persistence-and-basics/)。
- 多工器在遠端工具選型中的定位：[終端機圖形化工具總覽](/cli/cli-graphical-tools-overview/)。
