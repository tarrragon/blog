---
title: "Devcontainer 與 Nix：容器化和宣告式的開發環境"
date: 2026-06-29
description: "團隊開發環境要標準化、或評估 devcontainer 和 nix 跟個人 dotfile 怎麼共存時回來讀"
weight: 1
tags: ["dotfile", "devcontainer", "nix", "team"]
---

個人 dotfile 管理解決的是「一個人的環境可重現性」。當同樣的需求擴展到團隊——新人 onboarding 要多久能開始寫 code、團隊成員的開發環境差異造成「在我電腦上能跑」的問題、CI 環境跟本機環境不一致——就進入了「團隊開發環境標準化」的範疇。

## 個人 Dotfile 跟團隊環境的邊界

| 維度     | 個人 Dotfile                     | 團隊環境標準化                               |
| -------- | -------------------------------- | -------------------------------------------- |
| 管理對象 | 個人偏好（alias、keybind、配色） | 專案依賴（runtime 版本、系統套件、服務容器） |
| 目標     | 個人效率和舒適度                 | 環境一致性和 onboarding 速度                 |
| 儲存位置 | 個人 dotfile repo                | 專案 repo 內（.devcontainer/、flake.nix）    |
| 強制程度 | 完全個人自由                     | 團隊約定或強制                               |
| 變動頻率 | 高（個人隨時調整）               | 低（跟專案版本走）                           |

兩者共用同一個核心思想（環境 as code、版控、可重現），但管理的對象和約定的範圍不同。個人 dotfile 是「我喜歡怎麼工作」，團隊環境是「這個專案需要什麼才能跑」。

## Devcontainer：容器化的開發環境

Devcontainer 是微軟提出的開放規格（devcontainers.org），定義了怎麼用 Docker 容器作為開發環境。VS Code、GitHub Codespaces、JetBrains 都支援。

### 核心概念

專案 repo 裡放一個 `.devcontainer/devcontainer.json`，描述這個專案的開發環境需要什麼：

```json
{
    "name": "My Project",
    "image": "mcr.microsoft.com/devcontainers/base:ubuntu",
    "features": {
        "ghcr.io/devcontainers/features/go:1": {
            "version": "1.22"
        },
        "ghcr.io/devcontainers/features/node:1": {
            "version": "20"
        }
    },
    "postCreateCommand": "go mod download && npm install",
    "customizations": {
        "vscode": {
            "extensions": [
                "golang.go",
                "esbenp.prettier-vscode"
            ]
        }
    },
    "forwardPorts": [8080, 3000]
}
```

打開專案時，IDE 自動啟動這個容器、在裡面安裝指定版本的 Go 和 Node、跑 dependency install、裝 VS Code extension。新人 clone repo → 打開 → 等容器建好 → 直接開始寫 code。

### 跟個人 Dotfile 的互動

Devcontainer 管的是「專案需要什麼」，但你在容器裡工作時還是會想要自己的 shell alias、Git 設定、editor keybind。兩者的整合方式：

- **dotfiles repo 自動部署**：devcontainer.json 支援 `"dotfiles.repository"` 欄位，容器啟動時自動 clone 你的 dotfile repo 並執行 install script
- **個人 vs 團隊設定分離**：`.devcontainer/` 裡放團隊共用的環境定義，個人偏好透過 dotfiles 機制注入，不互相干擾

```json
{
    "dotfiles.repository": "https://github.com/you/dotfiles",
    "dotfiles.installCommand": "scripts/install.sh",
    "dotfiles.targetPath": "~/dotfiles"
}
```

這是個人 dotfile 和團隊環境標準化最乾淨的接合點——團隊定義「環境長什麼樣」，個人 dotfile 定義「在這個環境裡我怎麼操作」。

### Devcontainer 的限制

- **Docker 是前提**：團隊每個人的機器都要裝 Docker，macOS 上要跑 Docker Desktop 或 OrbStack
- **GUI 應用不適合**：devcontainer 定位是 headless 開發環境，不處理圖形桌面
- **效能折扣**：檔案系統操作在 macOS 上的 Docker volume 有效能折扣（Linux 上幾乎沒差）
- **離線環境**：建容器需要拉 image 和 feature，斷網環境要另外處理（見 [Infra 斷網模組](/infra/air-gapped/)）
- **管的是 dev image、不是線上 runtime**：devcontainer 對齊的是「團隊成員之間的開發環境一致」，不保證這個 image 等於 client 的線上 runtime。當目標是讓本機逐項對齊一個凍結的線上舊環境（PHP 7.2 / MySQL 5.7），那是另一件事，見 [Prod Parity 對齊](/linux/dotfile/10-prod-parity/)——兩者都用 container，但對齊的對象不同。

## Nix：宣告式的環境管理

Nix 是另一條技術路線，用宣告式的方式描述整個開發環境，不依賴 Docker。

### 核心概念

Nix 的 `flake.nix`（或 `shell.nix`）宣告了開發環境需要哪些套件，`nix develop` 進入這個環境：

```nix
# flake.nix
{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { nixpkgs, ... }:
    let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
    in {
      devShells.default = pkgs.mkShell {
        packages = with pkgs; [
          go_1_22
          nodejs_20
          postgresql_16
          redis
        ];
        shellHook = ''
          echo "Dev environment ready"
        '';
      };
    };
}
```

跟 Devcontainer 的差異：Nix 不用容器，直接在宿主機上建立隔離的環境（透過 Nix store 的路徑隔離）。優點是沒有 Docker 的效能折扣和額外層級；缺點是 Nix 的學習曲線陡峭、語法不直覺。

### Home Manager：Nix 管理 Dotfile

Nix 生態裡的 Home Manager 可以用 Nix 語言宣告式地管理整個家目錄的配置——等於用 Nix 取代 stow/chezmoi 做 dotfile 管理：

```nix
# home.nix
{ config, pkgs, ... }:
{
  programs.git = {
    enable = true;
    userName = "Your Name";
    userEmail = "you@example.com";
    extraConfig = {
      init.defaultBranch = "main";
      pull.rebase = true;
    };
  };

  programs.zsh = {
    enable = true;
    shellAliases = {
      ll = "ls -alF";
      gs = "git status";
    };
  };

  programs.neovim = {
    enable = true;
    defaultEditor = true;
  };
}
```

Home Manager 把「安裝軟體」和「寫配置」統一成一份宣告——改完 `home-manager switch` 就同時更新套件和配置。這是 dotfile 管理的極致形式，但代價是整個技術棧鎖定在 Nix 生態裡。
