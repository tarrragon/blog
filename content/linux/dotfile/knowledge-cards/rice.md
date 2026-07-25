---
title: "Rice（桌面視覺客製化）"
date: 2026-06-29
description: "Linux 桌面文章裡看到 rice / ricing / ricer 不確定意思時回來讀"
weight: 3
tags: ["dotfile", "rice", "linux", "knowledge-cards"]
---

Rice 在 Linux 桌面社群指的是**桌面視覺客製化**——把系統外觀調教成個人化的美學呈現。動詞 ricing 是「正在美化桌面」，名詞 a rice 是「一套美化成果/配置」，做這件事的人叫 ricer，成果多半架在某個 [Compositor](/linux/dotfile/knowledge-cards/compositor/) 之上。

## 概念位置

Rice 涵蓋的元件多半跑在某個 [Compositor](/linux/dotfile/knowledge-cards/compositor/) 之上；[Quickshell](/linux/dotfile/knowledge-cards/quickshell/) 這類桌面 shell runtime 是打包式 rice 常見的實作引擎。

## 詞源

最被廣泛接受的說法是源自汽車改裝文化的 "rice burner" / "ricer"——原本指對（通常是日系的）平價車裝上浮誇外觀套件（大尾翼、炫光、貼紙），看起來拉風但實際性能沒提升。後來 Linux 社群借用這個概念：把桌面打扮得花俏好看，本質也是「外觀的炫技」。

也有人提出 "Race Inspired Cosmetic Enhancements" 的逆向縮寫，但普遍被認為是事後湊的解釋。

在 Linux 圈裡，rice 的原始貶意和種族色彩已經淡化，變成中性甚至帶自豪的自稱——r/unixporn 社群就是圍繞 ricing 成果的分享運轉的。

## Rice 涵蓋的範圍

- **配色方案**：Catppuccin、Tokyo Night、Gruvbox、Nord 等跨工具統一的色彩定義
- **狀態列**：Waybar、Eww 的模組設計和 CSS 外觀
- **啟動器**：Wofi、Rofi 的搜尋框外觀
- **通知**：Mako、Dunst 的通知氣泡樣式
- **鎖屏**：Hyprlock 的登入畫面設計
- **桌布**：靜態桌布或動態桌布（Swww）
- **終端機配色**：Alacritty / Kitty / Foot 的 ANSI 色碼
- **字型**：Nerd Font 的 icon glyph

Caelestia 這類「desktop shell」專案把上述元件統一設計出貨，是「打包好的 rice」。手動逐一挑選和調教各元件是「DIY rice」。兩者的目標相同——視覺上協調、好看、符合個人美學。

完整的 rice 配置實務見[桌面 Rice 設計](/linux/dotfile/06-rice-design/)。
