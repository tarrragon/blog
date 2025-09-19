---
title: "如何要求ai使用正確的格式撰寫md文件"
date: 2025-09-18
draft: false
description: "ai 寫的md會有許多格式上的錯誤，需要讓他先檢查再修正"
tags: ["AI協作心得"]
---

## what

ai 寫的md會有許多格式上的錯誤

## why

生成式ai只負責產出內容，當下沒辦法判斷格式要求

## how

所以我請AI找看看有沒有lint檢查工具可以跟ide一樣判斷這些問題
所以AI就執行了以下動作：

  1. 檢查項目中是否有markdown linting工具
  2. 嘗試運行常見的markdown lint工具
  3. 如果沒有，可能需要安裝或使用一些基本的檢查

  先檢查專案結構，看看是否有任何lint配置文件，然後嘗試運行一些常見的工具。

⏺ Bash(which markdownlint)
  ⎿  Error: markdownlint not found

✻ Thinking…

  markdownlint 沒有安裝。讓我檢查是否有其他的markdown linting工具可用，或者可以通過npm安裝。

⏺ Bash(which mdl)
  ⎿  Error: mdl not found

  看起來沒有預安裝的markdown
  linting工具。檢查是否可以使用npm來安裝markdownlint，或者檢查項目中是否已經有相關配置。

⏺ Bash(which npm)

  好的，npm可用。可以使用npm安裝markdownlint-cli來檢查markdown文件的格式錯誤。

  現在會安裝markdownlint-cli來檢查markdown格式錯誤。

⏺ Bash(npm install -g markdownlint-cli)

  好的，markdownlint-cli已經安裝成功。現在我可以使用它來檢查項目中的markdown文件。讓我先檢查所有的m
  arkdown文件。

⏺ Bash(find  -name "*.md" -type f)

現在會使用markdownlint來檢查這些markdown文件中的格式錯誤。
