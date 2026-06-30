---
title: "模組一：管理工具與目錄結構"
date: 2026-06-29
description: "要把散落在家目錄的配置檔集中版控時，選 bare repo、stow 還是 chezmoi、目錄該怎麼組織"
weight: 1
tags: ["dotfile", "git", "stow", "chezmoi"]
---

Dotfile 管理的核心動作是把散落在家目錄各處的配置檔集中到一個 Git repo 裡版控。工具只是幫你處理「repo 裡的檔案怎麼對應到家目錄正確位置」這一層映射，選型看的是你的機器數量、OS 組合和 secret 需求。

開始之前，確認 SSH key 和 Git 已經設好、dotfile repo 已經 clone 到本機——這些前置步驟見[環境建置的操作順序](/dotfile/00-dotfile-mindset/setup-order-guide/)的階段一。

## 章節文章

| 文章                                                                                           | 主題                                                                                 |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [管理策略與選型](/dotfile/01-dotfile-management/management-strategies/)                        | bare repo / stow / chezmoi 三種策略的操作方式、優劣與選型判讀                        |
| [跨平台共用一個 Repo](/dotfile/01-dotfile-management/cross-platform-one-repo/)                 | macOS + Linux 用同一個 repo 的三層模型：stow 選擇性安裝、OS 分流、local.zsh 機器專屬 |
| [目錄結構、Git 工作流與常見陷阱](/dotfile/01-dotfile-management/directory-structure-workflow/) | stow 的目錄結構設計原則、日常 Git 操作流程、私鑰外洩等常見陷阱                       |

## 跨分類引用

- → [模組零：Dotfile 心智模型](/dotfile/00-dotfile-mindset/)：為什麼要管理、哪些東西該進 repo
- → [模組二：Shell 配置](/dotfile/02-shell-config/)：目錄結構裡 zsh package 的具體拆法
- → [模組八：同步、Bootstrap 與環境重建](/dotfile/08-sync-bootstrap/)：跨機器同步策略與 secret 管理
