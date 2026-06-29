---
title: "Dotfile 跟 Infra IaC 的平行關係"
date: 2026-06-29
description: "想理解 dotfile 管理在工程實踐裡的定位、或釐清「重建指令」跟「備份」的差異時回來讀"
weight: 2
tags: ["dotfile", "iac", "workflow"]
---

[Infra 基礎設施建置指南](/infra/)教的是用 Terraform 或 OpenTofu 把雲端資源（VPC、IAM role、EC2 instance）寫成代碼，讓基礎設施可重現、可 review、可回滾。Dotfile 做的事在概念上完全平行：把個人工作環境（shell、editor、terminal、window manager）寫成代碼，達成同樣的可重現性。

## 共用的核心原則

- **宣告式**：描述「環境應該長什麼樣」，而非「操作了哪些步驟」。Terraform 宣告「要有一個 VPC、CIDR 是 10.0.0.0/16」；dotfile 宣告「zsh 的 prompt 格式是這樣、alias ll 對應 ls -la」。
- **版控下的變更歷史**：誰改了什麼、什麼時候改的、為什麼改，都在 Git log 裡。環境出問題時可以回溯到「上一次正常的狀態」是哪個 commit。
- **可 review**：改了一個 shell function，diff 清楚可讀。跟在 terminal 裡直接 export 一個變數、下次重開就忘了相比，版控下的改動有跡可循。

## 差異

| 維度       | Infra IaC                                 | Dotfile                                      |
| ---------- | ----------------------------------------- | -------------------------------------------- |
| 管理對象   | 組織的雲端資源                            | 個人的工作桌面                               |
| State 管理 | Remote backend + lock 機制（防並行衝突）  | 通常只用 Git，沒有額外 state file            |
| 生效方式   | `terraform plan` → `terraform apply` 兩步 | 多數改完 source 即生效，或重開 terminal 生效 |
| 影響範圍   | 改錯可能影響 production 服務              | 改錯最多影響自己的工作環境                   |
| 協作需求   | 團隊共用、需要 PR review                  | 通常個人維護，PR review 是可選的             |

這個平行不只是比喻。[模組八：從個人到團隊](/dotfile/08-team-environment/)會教怎麼把 dotfile 的思想正式擴展到團隊環境——devcontainer 把「開發環境應該長什麼樣」寫成宣告式配置，讓新人 clone repo 就能拿到一致的開發環境，這正是 IaC 思想從組織 infra 往個人工作桌面延伸的具體產物。

## Dotfile 是重建指令，不是備份

這是最重要的心智模型區分。Dotfile repo 的目標不是「把舊電腦的所有檔案搬到新電腦」（那是備份工具的工作），而是「一份能在空白機器上重建工作環境的指令集」。

這個思維跟 Docker 的哲學一致：Docker image 透過 Dockerfile「描述如何重建」環境，而不是「對一台跑著的伺服器拍快照」。Dotfile repo 也是——它記錄的是「你的環境應該長什麼樣」的宣告，不是「你的機器上現在有什麼」的快照。

這個區分決定了 repo 裡該放什麼：

- 放進去的：**宣告式的配置檔**（shell config、editor config、WM config）、**套件清單**（Brewfile、pacman list）、**安裝腳本**（`install.sh`，用來在新機器上自動化部署流程）。
- 不放的：**暫存狀態**（shell history、undo file、session file）、**generated 產物**（plugin 的 compiled cache）、**大型二進位檔**（字型檔案可以用套件管理器裝，不用放 repo）。

維持「重建指令」的純度，repo 才能保持輕量、diff 可讀、跨機器部署不會帶進不必要的狀態。
