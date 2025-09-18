---
title: "如果mac多桌面錯置如何重置"
date: 2025-09-18
draft: false
description: "因為我會用並行裝置連接平板當成額外的螢幕，但是如果中斷再連接有時候會造成MACOS辨識多桌面出錯"
tags: [ "macos"]
---

## What happen ?

Macos 不同螢幕的多桌面跑到錯誤的螢幕。

## Why ?

因為我會用並行裝置連接平板當成額外的螢幕，但是如果中斷再連接有時候會造成MACOS辨識多桌面出錯，導致無法正常切換桌面。

## How to solve this ?

### 方法一：重置 Mission Control 偏好設定

這會清除所有顯示器的 Spaces 配置（等於重置多桌面設定）。

打開 終端機（Terminal）

輸入以下指令並按 Enter：

```bash
defaults delete com.apple.spaces
killall Dock
```

Dock 重啟後，Mission Control 的桌面配置會被重置，所有螢幕會只剩下「一個桌面」。
注意：這會刪除所有已建立的桌面（Spaces），但不會影響 App 或檔案。

### 方法二：暫時停用「顯示器有單獨的空間」

macOS 會為每個螢幕建立自己的桌面空間，這個設定有時會造成錯亂。

前往 系統設定 > 桌面與 Dock

找到 「顯示器有單獨的空間」（英文為 Displays have separate Spaces）

取消勾選

登出並重新登入你的帳號

重新勾選回來（如果你平常需要它）
