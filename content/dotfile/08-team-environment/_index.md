---
title: "模組八：從個人到團隊"
date: 2026-06-29
description: "個人 dotfile 管理的思想要延伸到團隊開發環境標準化時回來讀 — devcontainer、nix、商業環境配置管理"
weight: 8
tags: ["dotfile", "devcontainer", "nix", "team"]
---

個人 dotfile 管理解決的是「一個人的環境可重現性」。當同樣的需求擴展到團隊——新人 onboarding 要多久能開始寫 code、團隊成員的開發環境差異造成「在我電腦上能跑」的問題、CI 環境跟本機環境不一致——就進入了「團隊開發環境標準化」的範疇。這個模組教的是個人 dotfile 的思想怎麼往上延伸，以及在商業環境中有哪些成熟的做法。

## 章節文章

| 文章                                                                               | 主題                                                                              |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [Devcontainer 與 Nix](/dotfile/08-team-environment/devcontainer-nix/)              | 容器化和宣告式的開發環境、devcontainer 跟個人 dotfile 的互動、Home Manager        |
| [商業環境的開發環境配置管理](/dotfile/08-team-environment/commercial-environment/) | 四個層級的做法（README → 腳本化 → Devcontainer → MDM）、跟 Infra 的銜接、推進判讀 |

## 跨分類引用

- → [模組零：Dotfile 心智模型](/dotfile/00-dotfile-mindset/)：個人環境 as code 跟組織 IaC 的平行
- → [模組七：同步、Bootstrap 與環境重建](/dotfile/07-sync-bootstrap/)：bootstrap script 是團隊腳本化層級的基礎
- → [Infra 基礎設施建置指南](/infra/)：Infra IaC 是組織層的環境 as code
- → [Infra 斷網模組](/infra/air-gapped/)：離線環境的 devcontainer 限制
