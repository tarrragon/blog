---
title: "apt 安裝的交易原子性"
date: 2026-07-06
description: "apt-get install 一次帶多個套件、其中一個名字沒打包卻導致整批都沒裝時回來讀 — apt 為什麼全有或全無"
weight: 45
tags: ["dotfile", "prod-parity", "debian", "knowledge-cards"]
---

apt 的安裝是一筆交易（transaction）：`apt-get install a b c` 會先把所有指定套件連同它們的依賴一起解析成一份完整的安裝計畫，全部解析成功才開始下載安裝；只要其中一個套件解析不到（名字不存在、沒打包、依賴衝突），整筆交易放棄，一個都不裝。

## 解析與安裝是兩階段

apt 把「算出要裝什麼」跟「實際裝」分成先後兩步：

```text
階段一 解析：把 a b c + 全部依賴解成一份計畫；任一個解不到 → 整筆 abort，什麼都沒動
階段二 安裝：計畫完整才下載、解包、設定
```

這是刻意的設計。系統套件之間有依賴關係，半裝的狀態（裝了 a、b 因為 c 失敗而中途停）會留下依賴不完整的系統，比「全部沒裝」更難收拾。全有或全無讓系統永遠停在一致的狀態。

## 一個爛名字全滅

實務上最容易撞到的後果：批次清單裡塞了一個該發行版沒有的套件名，整批就全部不裝。實測在 Debian bookworm 跑一份含 broot、zellij（兩者 bookworm 沒打包）的清單，apt 回 `Unable to locate package broot / zellij` 後直接中止，同批的 autojump、gh、tig 明明存在也一個都沒裝。

症狀是「我明明列了十個工具、跑完一個都沒有」，根因不是每個都失敗，是其中一兩個爛名字讓整筆交易 abort。

## 判讀訊號

批次安裝清單必須逐項對齊該發行版實際有的套件，不能從別的發行版直接抄名字過來。動手前用 dry-run 先驗：

```bash
apt-get install -s a b c    # -s 模擬，只解析不安裝，先看有沒有 Unable to locate
```

一個一個 dry-run 能精準指出哪個名字解不開，再把它移出批次清單、或換成該發行版的正確名字。

## 邊界

pacman 的批次安裝有類似的原子性。想繞過「一個失敗全滅」可以逐包安裝（迴圈裡一個一個裝、失敗的跳過），但那會失去交易的一致性保證、也讓「哪些沒裝成功」變得難追。多數情況正解是把清單修對，而不是放棄原子性。

這解釋了為什麼跨發行版的套件清單要 curate、不能照抄，跟 [Package Manager 抽象層](/linux/dotfile/knowledge-cards/package-manager-abstraction/) 的「套件名分歧要逐項吸收」是同一件事的兩面。哪些工具在保守發行版沒打包，見 [發行版打包粒度](/linux/dotfile/knowledge-cards/distro-package-granularity/)。清單 curate 的實作見 [工作站 dotfile 跨發行版落地](/linux/dotfile/10-prod-parity/workstation-cross-distro/)。
