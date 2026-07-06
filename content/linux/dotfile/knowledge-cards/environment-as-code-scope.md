---
title: "環境 as code 的三個尺度"
date: 2026-07-06
description: "搞不清楚 dotfile / Dockerfile / IaC 的分界、或某個 Dockerfile 到底該放個人 repo 還是專案 repo 時回來讀 — 環境 as code 的個人/應用/組織尺度與歸屬判準"
weight: 3
tags: ["dotfile", "docker", "iac", "knowledge-cards"]
---

dotfile、Dockerfile、IaC（Terraform）常被當成三個各自獨立的技術，其實是同一個思想在不同尺度的套用——把「環境應該長什麼樣」寫成宣告式、可重現、版控的代碼。差別只在**主體的尺度**：配置的是誰的環境。分清楚這條光譜，就分得清它們的邊界，也答得出「這個 Dockerfile 該放哪個 repo」。

## 三個尺度

| 尺度 | 工具             | 配置誰的環境                                     | 跟誰走        |
| ---- | ---------------- | ------------------------------------------------ | ------------- |
| 個人 | dotfile          | 你工作的環境（shell / editor / WM）              | 跟你走        |
| 應用 | Dockerfile       | 一個 app 跑的環境（base image / runtime / 依賴） | 跟那個 app 走 |
| 組織 | IaC（Terraform） | 一整個組織的基礎設施（VPC / IAM / DB）           | 跟組織走      |

三者共用宣告式、版控、可重現、可 review 的哲學（見 [Dotfile 跟 Infra IaC 的平行關係](/linux/dotfile/00-dotfile-mindset/dotfile-iac-parallel/)），差別只在「這是誰的環境」。三格是光譜上的錨點、不是窮舉：中間還有「專案 / 團隊層」——CI 設定（`.github/workflows/`）、團隊共用的 devcontainer / compose 也是 environment-as-code，落在應用與組織之間。判準仍是「配置誰的環境、跟誰走」。

## 分界判準：一個測試問句

分不清 dotfile 跟 Dockerfile 時，問一句就分開：**「如果我明天換專案 / 換公司，這個東西會跟我走嗎？」**

- 你的 zsh 設定、keybind、vim config → 會跟你走 → **dotfile**。
- 某個 client 的 PHP 7.2 runtime 定義 → 留在那個 client 的專案 → **Dockerfile，該住 app 的 repo**。

分界不在形式（兩個都是宣告式檔案），在主體：一個配置「你」、跟你走；一個配置「app」、跟 app 走。

## Dockerfile 該放哪個 repo

順著上面的判準，Dockerfile 的 repo 歸屬也清楚了：

- **綁某個 app、隨它部署的 runtime** → 進**那個 app 的 repo**。它是那個服務的一部分，跟服務一起版控、一起部署。
- **你跨專案自用的參考 / 實驗 stack**（對齊 prod 的模板、升級實驗）→ 可以放**你的個人 repo**（dotfiles 或專門的 runtimes repo）。這種 stack 跟**你**走、不綁單一 app 的部署，放個人 env repo 說得通。

判準還是那句「跟誰走」：綁 app 就跟 app、進 app repo；跨專案自用就跟你、可進個人 repo。

## 判讀：邊界最模糊的地方

三層裡最容易混的是「把你的 ergonomics（dotfile 性質）裝進 app 的 container（Dockerfile 領域）」——那是兩個尺度的交會。正解是把它們**分層**：app 的 runtime image 只放 app 需要的（Dockerfile 領域、跟 app 走），你的 shell/vim 裝進跑起來的 container 可寫層、不進 image（見 [不可變 Image](/backend/knowledge-cards/immutable-image/) 與 [dotfile 跨進 runtime container](/linux/dotfile/10-prod-parity/container-ergonomics/)）。混進一個 image 就是把兩個尺度攪在一起、失去各自的可重現性。

實作上這條光譜怎麼落地見各尺度的教材：個人 [Dotfile 管理](/linux/dotfile/)、應用 [Dockerfile 設計](/backend/05-deployment-platform/vendors/docker/dockerfile-design/)、組織 [Infra 指南](/infra/)。
